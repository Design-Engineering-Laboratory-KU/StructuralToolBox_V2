using System;
using System.Collections.Generic;
using Grasshopper.Kernel;

namespace StbGrasshopper
{
    public sealed class StbLoadContainerComponent : GH_Component
    {
        public StbLoadContainerComponent()
            : base("STb Load Container", "STb Load", "Collect STb loads into one typed list.", StbCategories.Tab, StbCategories.Param) { }

        public override Guid ComponentGuid => new Guid("f4b6e6b9-7d4d-4b31-8f7c-1d0e5d9a6c01");
        protected override System.Drawing.Bitmap Icon => StbIcons.LoadContainer;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbLoadParameter(), "STb Loads", "Ld", "STb loads to contain.", GH_ParamAccess.list);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbLoadParameter(), "STb Loads", "Ld", "Contained STb loads.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var loads = new List<StbLoadGoo>();
            if (da.GetDataList(0, loads)) da.SetDataList(0, loads);
        }
    }

    public sealed class StbMaterialContainerComponent : GH_Component
    {
        public StbMaterialContainerComponent()
            : base("STb Mat Container", "STb Mat", "Collect STb materials into one typed list.", StbCategories.Tab, StbCategories.Param) { }

        public override Guid ComponentGuid => new Guid("f4b6e6b9-7d4d-4b31-8f7c-1d0e5d9a6c02");
        protected override System.Drawing.Bitmap Icon => StbIcons.MaterialContainer;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbMaterialParameter(), "STb Materials", "Mat", "STb materials to contain.", GH_ParamAccess.list);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbMaterialParameter(), "STb Materials", "Mat", "Contained STb materials.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var materials = new List<StbMaterialGoo>();
            if (da.GetDataList(0, materials)) da.SetDataList(0, materials);
        }
    }

    public sealed class StbSectionContainerComponent : GH_Component
    {
        public StbSectionContainerComponent()
            : base("STb Section Container", "STb Sec", "Collect STb sections into one typed list.", StbCategories.Tab, StbCategories.Param) { }

        public override Guid ComponentGuid => new Guid("f4b6e6b9-7d4d-4b31-8f7c-1d0e5d9a6c03");
        protected override System.Drawing.Bitmap Icon => StbIcons.SectionContainer;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbSectionParameter(), "STb Sections", "Sec", "STb sections to contain.", GH_ParamAccess.list);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbSectionParameter(), "STb Sections", "Sec", "Contained STb sections.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var sections = new List<StbSectionGoo>();
            if (da.GetDataList(0, sections)) da.SetDataList(0, sections);
        }
    }

    public sealed class StbModelContainerComponent : GH_Component
    {
        public StbModelContainerComponent()
            : base("STb Model Container", "STb Model", "Contain one STb model.", StbCategories.Tab, StbCategories.Param) { }

        public override Guid ComponentGuid => new Guid("f4b6e6b9-7d4d-4b31-8f7c-1d0e5d9a6c04");
        protected override System.Drawing.Bitmap Icon => StbIcons.ModelContainer;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "Model", "STb model to contain.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "Model", "Contained STb model.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbModelGoo model = null;
            if (da.GetData(0, ref model)) da.SetData(0, model);
        }
    }

    public sealed class StbElementContainerComponent : GH_Component
    {
        public StbElementContainerComponent()
            : base("STb Elem Container", "STb Elem", "Collect STb elements into one typed list.", StbCategories.Tab, StbCategories.Param) { }

        public override Guid ComponentGuid => new Guid("f4b6e6b9-7d4d-4b31-8f7c-1d0e5d9a6c05");
        protected override System.Drawing.Bitmap Icon => StbIcons.ElementContainer;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbElementParameter(), "STb Elements", "Elem", "STb elements to contain.", GH_ParamAccess.list);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbElementParameter(), "STb Elements", "Elem", "Contained STb elements.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var elements = new List<StbElementGoo>();
            if (da.GetDataList(0, elements)) da.SetDataList(0, elements);
        }
    }

    public sealed class StbSupportContainerComponent : GH_Component
    {
        public StbSupportContainerComponent()
            : base("STb Support Container", "STb Sup", "Collect STb supports into one typed list.", StbCategories.Tab, StbCategories.Param) { }

        public override Guid ComponentGuid => new Guid("f4b6e6b9-7d4d-4b31-8f7c-1d0e5d9a6c06");
        protected override System.Drawing.Bitmap Icon => StbIcons.SupportContainer;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbSupportParameter(), "STb Supports", "Sup", "STb supports to contain.", GH_ParamAccess.list);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbSupportParameter(), "STb Supports", "Sup", "Contained STb supports.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var supports = new List<StbSupportGoo>();
            if (da.GetDataList(0, supports)) da.SetDataList(0, supports);
        }
    }
}