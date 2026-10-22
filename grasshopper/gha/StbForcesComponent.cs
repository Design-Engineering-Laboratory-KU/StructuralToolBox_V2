using System;
using System.Collections.Generic;
using Grasshopper.Kernel;
using System.Drawing;

namespace StbGrasshopper
{
    public sealed class StbForcesComponent : GH_Component
    {
        public StbForcesComponent()
            : base(
                "STB Forces",
                "STB Forces",
                "Extract element force rows from an STB result object.",
                StbCategories.Tab,
                StbCategories.Post)
        {
        }

        public override Guid ComponentGuid => new Guid("f9c17ef0-3886-4142-9beb-a583438489ec");

        protected override Bitmap Icon => StbIcons.Forces;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "STb Model containing parsed results.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("Load Case", "LC", "Load case to extract. Negative means all.", GH_ParamAccess.item, 0);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddIntegerParameter("Load Case", "LC", "Load case id for each row.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Element ID", "E", "Element id for each row.", GH_ParamAccess.list);
            pManager.AddNumberParameter("Ni", "Ni", "Axial force at i end in kN.", GH_ParamAccess.list);
            pManager.AddNumberParameter("Nj", "Nj", "Axial force at j end in kN.", GH_ParamAccess.list);
            pManager.AddNumberParameter("Myi", "Myi", "Moment y at i end in kNm.", GH_ParamAccess.list);
            pManager.AddNumberParameter("Myj", "Myj", "Moment y at j end in kNm.", GH_ParamAccess.list);
            pManager.AddNumberParameter("Mzi", "Mzi", "Moment z at i end in kNm.", GH_ParamAccess.list);
            pManager.AddNumberParameter("Mzj", "Mzj", "Moment z at j end in kNm.", GH_ParamAccess.list);
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
            var elementIds = new List<int>();
            var ni = new List<double>();
            var nj = new List<double>();
            var myi = new List<double>();
            var myj = new List<double>();
            var mzi = new List<double>();
            var mzj = new List<double>();

            foreach (var row in results.ElementForces)
            {
                if (!StbLoadCaseFilter.Matches(loadCase, row.LoadCase))
                {
                    continue;
                }

                loadCases.Add(row.LoadCase);
                elementIds.Add(row.ElementId);
                ni.Add(row.Ni);
                nj.Add(row.Nj);
                myi.Add(row.Myi);
                myj.Add(row.Myj);
                mzi.Add(row.Mzi);
                mzj.Add(row.Mzj);
            }

            if (loadCase >= 0 && loadCases.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    "No element force rows found for load case " + loadCase + ".");
            }

            da.SetDataList(0, loadCases);
            da.SetDataList(1, elementIds);
            da.SetDataList(2, ni);
            da.SetDataList(3, nj);
            da.SetDataList(4, myi);
            da.SetDataList(5, myj);
            da.SetDataList(6, mzi);
            da.SetDataList(7, mzj);
        }
    }
}
