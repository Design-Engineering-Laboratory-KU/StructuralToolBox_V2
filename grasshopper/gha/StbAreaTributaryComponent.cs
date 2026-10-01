using System;
using System.Collections.Generic;
using System.Drawing;
using Grasshopper.Kernel;
using Rhino;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbAreaTributaryComponent : GH_Component
    {
        private static readonly Color PreviewColor = Color.FromArgb(0, 174, 227);
        private readonly List<Line> _previewLines = new List<Line>();
        private BoundingBox _previewBox = BoundingBox.Empty;

        public StbAreaTributaryComponent()
            : base(
                "STB Area Tributary",
                "STB ATrib",
                "Distribute an STB area load onto its boundary members as equivalent trapezoidal line loads.",
                StbCategories.Tab,
                StbCategories.Load)
        {
        }

        public override Guid ComponentGuid => new Guid("a7c4e2d1-8b3f-4a91-9c2e-5d6f1a0b8c47");
        public override GH_Exposure Exposure => GH_Exposure.tertiary;

        protected override Bitmap Icon => StbIcons.AreaTributary;

        public override BoundingBox ClippingBox
        {
            get
            {
                var box = base.ClippingBox;
                if (_previewBox.IsValid)
                {
                    box.Union(_previewBox);
                }

                return box;
            }
        }

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(
                new StbLoadParameter(),
                "Area Load",
                "ALd",
                "STB area load objects from STB Area Load.",
                GH_ParamAccess.list);
            pManager.AddNumberParameter(
                "Scale",
                "S",
                "Viewport preview scale in meters per kN/m.",
                GH_ParamAccess.item,
                0.2);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddLineParameter(
                "Line",
                "L",
                "Boundary member lines in the original element orientation.",
                GH_ParamAccess.list);
            pManager.AddVectorParameter(
                "Load i",
                "Wi",
                "Equivalent distributed load at the member i-end in global kN/m.",
                GH_ParamAccess.list);
            pManager.AddVectorParameter(
                "Load j",
                "Wj",
                "Equivalent distributed load at the member j-end in global kN/m.",
                GH_ParamAccess.list);
            pManager.AddNumberParameter(
                "Area",
                "A",
                "Tributary area assigned to each member in m2.",
                GH_ParamAccess.list);
            pManager.AddParameter(
                new StbLoadParameter(),
                "Line Load",
                "Ld",
                "Equivalent STB line-load objects for display. Do not also send these to Assemble if the original Area Load is already connected.",
                GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            _previewLines.Clear();
            _previewBox = BoundingBox.Empty;

            var loads = StbModelGooUtil.GetLoads(da, 0);
            double scale = 0.2;
            da.GetData(1, ref scale);

            if (loads.Count == 0)
            {
                return;
            }

            var tolerance = RhinoDoc.ActiveDoc?.ModelAbsoluteTolerance ?? 0.001;
            var lines = new List<Line>();
            var loadAtI = new List<Vector3d>();
            var loadAtJ = new List<Vector3d>();
            var areas = new List<double>();
            var lineLoads = new List<StbLoadGoo>();
            var skipped = 0;

            foreach (var load in loads)
            {
                if (load.Kind != StbLoadKind.Area)
                {
                    skipped++;
                    continue;
                }

                List<StbTributaryMemberLoad> distributed;
                try
                {
                    distributed = StbAreaLoadDistributor.Distribute(load, tolerance);
                }
                catch (InvalidOperationException ex)
                {
                    AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ex.Message);
                    return;
                }

                foreach (var member in distributed)
                {
                    lines.Add(member.Line);
                    loadAtI.Add(member.LoadAtI);
                    loadAtJ.Add(member.LoadAtJ);
                    areas.Add(member.TributaryArea);
                    lineLoads.Add(new StbLoadGoo(new StbLoadModel
                    {
                        Kind = StbLoadKind.Line,
                        ElementLine = member.Line,
                        LoadCase = member.LoadCase,
                        IsGlobal = true,
                        LoadAtI = member.LoadAtI,
                        LoadAtJ = member.LoadAtJ,
                    }));
                    AddPreviewArrows(member, scale);
                }
            }

            if (skipped > 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    "Skipped "
                    + skipped
                    + " non-area load(s). Connect STB Area Load.");
            }

            if (lineLoads.Count > 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Remark,
                    "These line loads visualize the ALOD tributary split. Do not send both Area Load and these Line Loads to STB Assemble Model.");
            }

            da.SetDataList(0, lines);
            da.SetDataList(1, loadAtI);
            da.SetDataList(2, loadAtJ);
            da.SetDataList(3, areas);
            da.SetDataList(4, lineLoads);
        }

        public override void DrawViewportWires(IGH_PreviewArgs args)
        {
            foreach (var line in _previewLines)
            {
                args.Display.DrawLine(line, PreviewColor, 2);
                args.Display.DrawArrow(line, PreviewColor);
            }
        }

        private void AddPreviewArrows(StbTributaryMemberLoad member, double scale)
        {
            if (Math.Abs(scale) < 1e-12 || !member.Line.IsValid)
            {
                return;
            }

            const int stations = 5;
            for (var i = 0; i < stations; i++)
            {
                var t = stations == 1 ? 0.5 : (double)i / (stations - 1);
                var origin = member.Line.PointAt(t);
                var load = (1.0 - t) * member.LoadAtI + t * member.LoadAtJ;
                var tip = origin + load * scale;
                if (origin.DistanceTo(tip) < 1e-9)
                {
                    continue;
                }

                var arrow = new Line(origin, tip);
                _previewLines.Add(arrow);
                _previewBox.Union(origin);
                _previewBox.Union(tip);
            }
        }
    }
}
