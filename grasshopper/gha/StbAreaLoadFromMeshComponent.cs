using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Data;
using Grasshopper.Kernel.Types;
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
                "Candidate boundary elements: connect the same list, in the same order, as STB Assemble Model "
                + "so Elem IDs match the assembled ELEM ids.",
                GH_ParamAccess.list);
            pManager.AddParameter(
                new StbModelParameter(),
                "STb Model",
                "STb Model",
                "Alternative to STb Element, e.g. from STb Assembly from file. Do not use the STb Model of the "
                + "Assemble component these loads go into; that would be a loop.",
                GH_ParamAccess.item);
            pManager.AddIntegerParameter(
                "Elem IDs",
                "ID",
                "Optional. Only these elements may bound a panel (1-based ELEM ids, as STB Assemble Model numbers them). "
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
            pManager[1].Optional = true;
            pManager[2].Optional = true;
            pManager[3].Optional = true;
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(
                new StbLoadParameter(),
                "STb Load",
                "Ld",
                "One STB area load per panel.",
                GH_ParamAccess.list);
            pManager.AddIntegerParameter(
                "Boundary IDs",
                "ID",
                "ELEM ids bounding each panel; one branch per load.",
                GH_ParamAccess.tree);
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
            StbModelGoo modelGoo = null;
            if (elements.Count == 0 && da.GetData(2, ref modelGoo) && modelGoo?.Value != null)
            {
                elements = modelGoo.Value.Elements.Where(e => e != null).ToList();
            }

            if (elements.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Connect STb Element objects or an STb Model.");
                return;
            }

            var ids = new List<int>();
            da.GetDataList(3, ids);
            int loadCase = 0;
            var pressure = Vector3d.Zero;
            double tolerance = 0.0;
            da.GetData(4, ref loadCase);
            da.GetData(5, ref pressure);
            da.GetData(6, ref tolerance);
            if (!(tolerance > 0.0))
            {
                tolerance = RhinoDoc.ActiveDoc?.ModelAbsoluteTolerance ?? 0.001;
            }

            // STB Assemble Model numbers the valid elements 1, 2, ... in input order.
            var allowed = new HashSet<int>(ids);
            var lines = new List<Line>();
            var lineIds = new List<int>();
            var nextId = 1;
            foreach (var element in elements)
            {
                if (!element.Line.IsValid)
                {
                    continue;
                }

                var id = nextId++;
                if (allowed.Count == 0 || allowed.Contains(id))
                {
                    lines.Add(element.Line);
                    lineIds.Add(id);
                }
            }

            var unknown = allowed.Where(id => id < 1 || id >= nextId).OrderBy(id => id).ToList();
            if (unknown.Count > 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    "No element with Elem ID " + string.Join(", ", unknown) + " (valid ids are 1 to " + (nextId - 1) + ").");
            }

            var panels = new List<StbPanel>();
            var skipped = new List<StbPanel>();
            StbPanelFinder.Find(lines, p => NormalOnMeshes(meshes, p, tolerance), tolerance, panels, skipped);

            var loads = new List<StbLoadGoo>();
            var boundaryIds = new GH_Structure<GH_Integer>();
            for (var i = 0; i < panels.Count; i++)
            {
                var load = new StbLoadModel
                {
                    Kind = StbLoadKind.Area,
                    LoadCase = loadCase,
                    Pressure = pressure,
                };
                var path = new GH_Path(i);
                foreach (var index in panels[i].LineIndices)
                {
                    load.BoundaryLines.Add(lines[index]);
                    boundaryIds.Append(new GH_Integer(lineIds[index]), path);
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
            da.SetDataTree(1, boundaryIds);
            da.SetDataList(2, panels.Select(p => new PolylineCurve(p.Outline)));
            da.SetDataList(3, skipped.Select(p => new PolylineCurve(p.Outline)));
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
