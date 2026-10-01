using System;
using System.Collections.Generic;
using Grasshopper.Kernel;
using Rhino.Geometry;
using System.Drawing;

namespace StbGrasshopper
{
    public sealed class StbDisplacementsComponent : GH_Component
    {
        public StbDisplacementsComponent()
            : base(
                "STB Displacements",
                "STB Disp",
                "Extract nodal displacement rows from an STB result object.",
                StbCategories.Tab,
                StbCategories.Post)
        {
        }

        public override Guid ComponentGuid => new Guid("66d7c601-fd24-4520-a478-c2095f3f23b8");

        protected override Bitmap Icon => StbIcons.Displacements;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "STb Model containing parsed results.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("Load Case", "LC", "Load case to extract. Negative means all.", GH_ParamAccess.item, 0);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddIntegerParameter("Load Case", "LC", "Load case id for each row.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Node ID", "N", "Node id for each row.", GH_ParamAccess.list);
            pManager.AddVectorParameter("Translation", "U", "Translational displacement vector in meters.", GH_ParamAccess.list);
            pManager.AddVectorParameter("Rotation", "Rot", "Rotational displacement vector in radians.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbParsedResults results;
            int loadCase = 0;
            if (!StbModelGooUtil.TryGetResults(da, 0, out results))
            {
                return;
            }

            da.GetData(1, ref loadCase);

            var loadCases = new List<int>();
            var nodeIds = new List<int>();
            var translations = new List<Vector3d>();
            var rotations = new List<Vector3d>();

            foreach (var row in results.Displacements)
            {
                if (!StbLoadCaseFilter.Matches(loadCase, row.LoadCase))
                {
                    continue;
                }

                loadCases.Add(row.LoadCase);
                nodeIds.Add(row.NodeId);
                translations.Add(new Vector3d(row.X, row.Y, row.Z));
                rotations.Add(new Vector3d(row.ThetaX, row.ThetaY, row.ThetaZ));
            }

            if (loadCase >= 0 && loadCases.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    "No displacement rows found for load case " + loadCase + ".");
            }

            da.SetDataList(0, loadCases);
            da.SetDataList(1, nodeIds);
            da.SetDataList(2, translations);
            da.SetDataList(3, rotations);
        }
    }
}
