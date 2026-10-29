using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using Grasshopper.Kernel;
using Rhino;
using Rhino.Geometry;

namespace StbGrasshopper
{
    /// <summary>
    /// Creates STb area loads from a mesh: the frame elements lying on the mesh
    /// divide it into panels, and each panel bounded by 3 or 4 elements becomes
    /// one area load (ALOD), as if built with STb Area Load.
    /// </summary>
    public sealed class StbAreaLoadFromMeshComponent : GH_Component
    {
        public StbAreaLoadFromMeshComponent()
            : base(
                "STb Area Load from Mesh",
                "STb ALoadM",
                "Create STb area loads from a mesh. Frame elements lying on the mesh divide it into panels; "
                + "each panel bounded by 3 or 4 elements gets one area load. Openings in the mesh get no load.",
                StbCategories.Tab,
                StbCategories.Load)
        {
        }

        public override Guid ComponentGuid => new Guid("6f2d8a41-3c9e-4b17-a5d0-8e4b1c7f9a23");

        protected override Bitmap Icon => StbIcons.AreaLoad;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddMeshParameter(
                "Mesh",
                "M",
                "Loaded area, e.g. a floor or roof. Its faces need not match the panels.",
                GH_ParamAccess.list);
            pManager.AddParameter(
                new StbElementParameter(),
                "STb Element",
                "Elem",
                "Candidate boundary elements, e.g. the same list connected to STB Assemble Model.",
                GH_ParamAccess.list);
            pManager.AddTextParameter(
                "Elem Name",
                "Name",
                "Optional. Only elements with these names (STb Element Name) may bound a panel. "
                + "Empty uses every element on the mesh.",
                GH_ParamAccess.list);
            pManager.AddIntegerParameter("LC", "LC", "Load case id.", GH_ParamAccess.item, 0);
            pManager.AddVectorParameter(
                "Pressure",
                "P",
                "Area-load vector in global coordinates in kN/m2.",
                GH_ParamAccess.item,
                Vector3d.Zero);
            pManager.AddNumberParameter(
                "Tolerance",
                "Tol",
                "Distance within which an element end lies on the mesh, in model units. 0 = document tolerance.",
                GH_ParamAccess.item,
                0.0);
            pManager[2].Optional = true;
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(
                new StbLoadParameter(),
                "STb Load",
                "Ld",
                "One STB area load per panel.",
                GH_ParamAccess.list);
            pManager.AddCurveParameter("Panels", "Pnl", "Outline of each loaded panel.", GH_ParamAccess.list);
            pManager.AddCurveParameter(
                "Skipped",
                "Skp",
                "Panels with more than 4 boundary elements; ALOD takes 3 or 4, so they get no load.",
                GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var meshes = new List<Mesh>();
            da.GetDataList(0, meshes);
            meshes = meshes.Where(m => m != null && m.IsValid && m.Faces.Count > 0).Select(PrepareMesh).ToList();
            if (meshes.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Connect a mesh.");
                return;
            }

            var elements = StbModelGooUtil.GetElements(da, 1);
            if (elements.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Connect STb Element objects.");
                return;
            }

            var names = new List<string>();
            da.GetDataList(2, names);
            int loadCase = 0;
            var pressure = Vector3d.Zero;
            double tolerance = 0.0;
            da.GetData(3, ref loadCase);
            da.GetData(4, ref pressure);
            da.GetData(5, ref tolerance);
            if (!(tolerance > 0.0))
            {
                tolerance = RhinoDoc.ActiveDoc?.ModelAbsoluteTolerance ?? 0.001;
            }

            var wanted = new HashSet<string>(
                names.Where(n => !string.IsNullOrWhiteSpace(n)).Select(n => n.Trim()),
                StringComparer.Ordinal);
            var found = new HashSet<string>(StringComparer.Ordinal);
            var lines = new List<Line>();
            foreach (var element in elements)
            {
                if (!element.Line.IsValid)
                {
                    continue;
                }

                var name = element.Name?.Trim() ?? string.Empty;
                if (wanted.Count == 0 || wanted.Contains(name))
                {
                    lines.Add(element.Line);
                    found.Add(name);
                }
            }

            var missing = wanted.Where(n => !found.Contains(n)).ToList();
            if (missing.Count > 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "No element named: " + string.Join(", ", missing) + ".");
            }

            var panels = new List<StbPanel>();
            var skipped = new List<StbPanel>();
            StbPanelFinder.Find(lines, p => NormalOnMeshes(meshes, p, tolerance), tolerance, panels, skipped);

            var loads = new List<StbLoadGoo>();
            foreach (var panel in panels)
            {
                var load = new StbLoadModel
                {
                    Kind = StbLoadKind.Area,
                    LoadCase = loadCase,
                    Pressure = pressure,
                };
                foreach (var index in panel.LineIndices)
                {
                    load.BoundaryLines.Add(lines[index]);
                }

                loads.Add(new StbLoadGoo(load));
            }

            if (panels.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    "No panel found. Check that the elements lie on the mesh (Tolerance) and form closed loops.");
            }
            else
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, panels.Count + " panel(s) loaded.");
            }

            if (skipped.Count > 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    skipped.Count + " panel(s) have more than 4 boundary elements and get no load (see Skipped). "
                    + "Split them with an extra element, or load them with STb Line Load.");
            }

            da.SetDataList(0, loads);
            da.SetDataList(1, panels.Select(p => new PolylineCurve(p.Outline)));
            da.SetDataList(2, skipped.Select(p => new PolylineCurve(p.Outline)));
        }

        private static Mesh PrepareMesh(Mesh source)
        {
            var mesh = source.DuplicateMesh();
            mesh.FaceNormals.ComputeFaceNormals();
            return mesh;
        }

        private static Vector3d NormalOnMeshes(List<Mesh> meshes, Point3d point, double tolerance)
        {
            foreach (var mesh in meshes)
            {
                var hit = mesh.ClosestMeshPoint(point, tolerance);
                if (hit != null && hit.FaceIndex >= 0)
                {
                    return new Vector3d(mesh.FaceNormals[hit.FaceIndex]);
                }
            }

            return Vector3d.Unset;
        }
    }
}
