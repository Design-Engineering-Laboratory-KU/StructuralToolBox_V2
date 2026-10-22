using System;
using System.Drawing;
using Grasshopper.Kernel;

namespace StbGrasshopper
{
    public sealed class StbAssemblyFromFileComponent : GH_Component
    {
        public StbAssemblyFromFileComponent()
            : base(
                "STb Assembly from file",
                "STb File",
                "Read an existing STB DAT file and create a typed STb Model.",
                StbCategories.Tab,
                StbCategories.Assemble)
        {
        }

        public override Guid ComponentGuid => new Guid("a8b9c0d1-2345-4567-89ab-cdef01234567");
        public override GH_Exposure Exposure => GH_Exposure.secondary;
        protected override Bitmap Icon => StbIcons.AssemblyFromFile;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("DAT Path", "DAT", "Path to an existing STB .dat file.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "Typed STb Model read from the DAT file.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string datPath = null;
            if (!da.GetData(0, ref datPath))
            {
                return;
            }

            try
            {
                var model = StbDatModelReader.Read(datPath);
                if (model.UntypedRecordCounts.Count > 0)
                {
                    var names = new System.Collections.Generic.List<string>();
                    foreach (var pair in model.UntypedRecordCounts)
                    {
                        names.Add(pair.Key + " x" + pair.Value);
                    }

                    AddRuntimeMessage(
                        GH_RuntimeMessageLevel.Remark,
                        "Kept only in the original file (no typed object): "
                        + string.Join(", ", names)
                        + ". STb Analyze uses the original file, so these are still analyzed.");
                }

                da.SetData(0, new StbModelGoo(model));
            }
            catch (Exception ex)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Failed to read STB DAT file: " + ex.Message);
            }
        }
    }
}
