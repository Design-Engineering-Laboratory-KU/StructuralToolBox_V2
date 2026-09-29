using System;
using System.Drawing;
using Grasshopper.Kernel;

namespace StbGrasshopper
{
    public sealed class StbAnalyzeFromFileComponent : GH_Component
    {
        public StbAnalyzeFromFileComponent()
            : base("STb Analyze from file", "STb Analyze File", "Analyze an existing STB DAT file and output an STb Model.", "STB", "Analyze")
        {
        }

        public override Guid ComponentGuid => new Guid("b9c0d1e2-3456-4789-abcd-ef0123456789");
        protected override Bitmap Icon => StbIcons.Analyze;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("DAT Path", "DAT", "Path to an existing STB .dat file.", GH_ParamAccess.item);
            pManager.AddTextParameter("Python Exe", "Py", "Path to the Structural Toolbox .venv Python. Leave empty to auto-detect.", GH_ParamAccess.item, string.Empty);
            pManager.AddTextParameter("Repo Root", "Root", "Install or repository folder. Leave empty to auto-detect.", GH_ParamAccess.item, string.Empty);
            pManager.AddBooleanParameter("Run", "Run", "Set true to run the solver.", GH_ParamAccess.item, false);
            pManager.AddTextParameter("Out Path", "Out", "Optional .out path. Empty uses the temp folder.", GH_ParamAccess.item, string.Empty);
            pManager.AddIntegerParameter("Load Case", "LC", "Use -1 to keep all load cases in Results.", GH_ParamAccess.item, -1);
            pManager[2].Optional = true;
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddBooleanParameter("Success", "S", "True when the solver returns exit code 0.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("Exit Code", "Code", "STB CLI exit code.", GH_ParamAccess.item);
            pManager.AddTextParameter("Out Path", "Out", "Written .out file path.", GH_ParamAccess.item);
            pManager.AddTextParameter("Stdout", "Stdout", "CLI standard output.", GH_ParamAccess.item);
            pManager.AddTextParameter("Stderr", "Stderr", "CLI standard error.", GH_ParamAccess.item);
            pManager.AddTextParameter("Summary", "Summary", "Short status summary.", GH_ParamAccess.item);
            pManager.AddGenericParameter("Results", "R", "Parsed STB result object.", GH_ParamAccess.item);
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "Analyzed STb Model containing Results.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string datPath = null;
            string pythonExe = string.Empty;
            string repoRoot = string.Empty;
            bool run = false;
            string outPath = string.Empty;
            int loadCase = -1;
            if (!da.GetData(0, ref datPath)) return;
            da.GetData(1, ref pythonExe);
            da.GetData(2, ref repoRoot);
            da.GetData(3, ref run);
            da.GetData(4, ref outPath);
            da.GetData(5, ref loadCase);

            StbModelModel model;
            try
            {
                model = StbDatModelReader.Read(datPath);
            }
            catch (Exception ex)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Failed to read STB DAT model: " + ex.Message);
                return;
            }

            var result = StbAnalyzeCommon.Run(this, datPath, pythonExe, repoRoot, run, outPath, loadCase);
            StbAnalyzeCommon.SetOutputs(da, result, model, datPath);
        }
    }
}
