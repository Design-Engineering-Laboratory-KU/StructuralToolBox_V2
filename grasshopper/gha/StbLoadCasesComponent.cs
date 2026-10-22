using System;
using System.Collections.Generic;
using System.Drawing;
using Grasshopper.Kernel;

namespace StbGrasshopper
{
    public sealed class StbLoadCasesComponent : GH_Component
    {
        public StbLoadCasesComponent()
            : base(
                "STB Load Cases",
                "STB LC",
                "List available load cases in parsed STB results.",
                StbCategories.Tab,
                StbCategories.Info)
        {
        }

        public override Guid ComponentGuid => new Guid("b1a8e2f4-5c91-4d0a-9b6e-3f2c8d1a4e70");

        protected override Bitmap Icon => StbIcons.LoadCases;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "STb Model containing parsed results.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddIntegerParameter("Load Cases", "LC", "Available load case ids.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbParsedResults results;
            if (!StbModelGooUtil.TryGetResults(da, 0, out results))
            {
                return;
            }

            da.SetDataList(0, StbLoadCaseFilter.GetLoadCases(results));
        }
    }
}
