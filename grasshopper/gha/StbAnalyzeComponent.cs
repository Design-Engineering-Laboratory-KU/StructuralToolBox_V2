using System;
using System.Drawing;
using Grasshopper.Kernel;

namespace StbGrasshopper
{
    public sealed class StbAnalyzeComponent : GH_Component
    {
        public StbAnalyzeComponent()
            : base("STb Analyze", "STb Analyze", "Analyze an STb Model and output the analyzed STb Model.", "STB", "Analyze")
        {
        }

        public override Guid ComponentGuid => new Guid("04bd3b60-c622-46f8-8156-afd1f6db5cf5");
        protected override Bitmap Icon => StbIcons.Analyze;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "Assembled STb Model to analyze.", GH_ParamAccess.item);
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
            StbModelModel model;
            if (!StbModelGooUtil.TryGetModel(da, 0, out model)) return;

            string pythonExe = string.Empty;
            string repoRoot = string.Empty;
            bool run = false;
            string outPath = string.Empty;
            int loadCase = -1;
            da.GetData(1, ref pythonExe);
            da.GetData(2, ref repoRoot);
            da.GetData(3, ref run);
            da.GetData(4, ref outPath);
            da.GetData(5, ref loadCase);

            var datPath = model.DatPath;
            if (string.IsNullOrWhiteSpace(datPath) && !string.IsNullOrWhiteSpace(model.DatText))
            {
                datPath = StbPathUtil.WriteTextFile(
                    System.IO.Path.Combine(System.IO.Path.GetTempPath(), "stb_model_" + Guid.NewGuid().ToString("N") + ".dat"),
                    model.DatText);
            }

            var result = StbAnalyzeCommon.Run(this, datPath, pythonExe, repoRoot, run, outPath, loadCase);
            StbAnalyzeCommon.SetOutputs(da, result, model, datPath);
        }
    }
}
