using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using Grasshopper.Kernel;
using Rhino.Geometry;

namespace StbGrasshopper
{
    /// <summary>
    /// Creates one STb area load from a mesh. STB Assemble Model splits it into
    /// panels: the model elements lying on the mesh divide it, and each panel
    /// bounded by 3 or 4 elements becomes one area load (ALOD).
    /// </summary>
    public sealed class StbAreaLoadFromMeshComponent : GH_Component
    {
        public StbAreaLoadFromMeshComponent()
            : base(
                "STb Area Load from Mesh",
                "STb ALoadM",
                "Create an STb area load from a mesh. STB Assemble Model splits it into panels: model elements lying "
                + "on the mesh divide it, and each panel bounded by 3 or 4 elements gets one area load. "
                + "Openings in the mesh get no load.",
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
            pManager[1].Optional = true;
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(
                new StbLoadParameter(),
                "STb Load",
                "Ld",
                "Area load from the mesh. Connect it to STB Assemble Model, which splits it into one ALOD per panel.",
                GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var meshes = new List<Mesh>();
            da.GetDataList(0, meshes);
            meshes = meshes.Where(m => m != null && m.IsValid && m.Faces.Count > 0).ToList();
            if (meshes.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Connect a mesh.");
                return;
            }

            var names = new List<string>();
            da.GetDataList(1, names);
            int loadCase = 0;
            var pressure = Vector3d.Zero;
            double tolerance = 0.0;
            da.GetData(2, ref loadCase);
            da.GetData(3, ref pressure);
            da.GetData(4, ref tolerance);

            var load = new StbLoadModel
            {
                Kind = StbLoadKind.MeshArea,
                LoadCase = loadCase,
                Pressure = pressure,
                MeshTolerance = Math.Max(tolerance, 0.0),
            };
            load.Meshes.AddRange(meshes);
            load.ElementNames.AddRange(names.Where(n => !string.IsNullOrWhiteSpace(n)).Select(n => n.Trim()));
            da.SetData(0, new StbLoadGoo(load));
        }
    }
}
