using System;
using System.Collections.Generic;
using System.Drawing;
using GH_IO.Serialization;
using Grasshopper.Kernel;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbStressComponent : GH_Component, IStbDropDownOwner
    {
        private const string ModeKey = "StressMode";

        private static readonly StressMode[] Modes =
        {
            new StressMode("Combined |N/A|+|My/Wy|+|Mz/Wz|", "Combined \u03c3 [N/mm2]"),
            new StressMode("Axial N/A", "Axial \u03c3 = N/A [N/mm2]"),
            new StressMode("Bending y My/Wy", "Bending \u03c3 = My/Wy [N/mm2]"),
            new StressMode("Bending z Mz/Wz", "Bending \u03c3 = Mz/Wz [N/mm2]"),
        };

        private readonly List<StressSegment> _segments = new List<StressSegment>();
        private BoundingBox _clippingBox = BoundingBox.Empty;
        private double _legendMaximum;
        private bool _showLegend = true;
        private int _mode;

        public StbStressComponent()
            : base(
                "STB Stress",
                "STB Stress",
                "Preview member normal stress: the combined extreme-fiber value or its axial and bending components.",
                StbCategories.Tab,
                StbCategories.Post)
        {
        }

        public override Guid ComponentGuid =>
            new Guid("2e602955-531a-4bc3-b6a4-a9b7a2e517ad");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.Stress;

        public override BoundingBox ClippingBox => _clippingBox;

        int IStbDropDownOwner.DropDownCount => Modes.Length;
        int IStbDropDownOwner.DropDownSelection => _mode;
        string IStbDropDownOwner.DropDownName(int index) => Modes[index].Name;

        void IStbDropDownOwner.SetDropDownSelection(int index)
        {
            if (index == _mode || index < 0 || index >= Modes.Length)
            {
                return;
            }

            RecordUndoEvent("Change stress component");
            _mode = index;
            ExpireSolution(true);
        }

        public override void CreateAttributes()
        {
            m_attributes = new StbDropDownAttributes(this, this);
        }

        protected override void AppendAdditionalComponentMenuItems(System.Windows.Forms.ToolStripDropDown menu)
        {
            Menu_AppendSeparator(menu);
            StbDropDownAttributes.AppendChoices(menu, this);
        }

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(
                new StbModelParameter(),
                "STb Model",
                "STb Model",
                "STb Model containing parsed results.",
                GH_ParamAccess.item);
            pManager.AddIntegerParameter(
                "Load Case",
                "LC",
                "Load case to display.",
                GH_ParamAccess.item,
                0);
            pManager.AddIntegerParameter(
                "Divisions",
                "D",
                "Colored segments per element.",
                GH_ParamAccess.item,
                12);
            pManager.AddNumberParameter(
                "Maximum",
                "Max",
                "Legend maximum stress in N/mm2. Use 0 for automatic.",
                GH_ParamAccess.item,
                0.0);
            pManager.AddBooleanParameter(
                "Legend",
                "Legend",
                "Draw the stress legend in the Rhino viewport.",
                GH_ParamAccess.item,
                true);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddLineParameter(
                "Segments",
                "L",
                "Colored member segments.",
                GH_ParamAccess.list);
            pManager.AddNumberParameter(
                "Stress",
                "S",
                "Absolute stress of the selected component at each segment in N/mm2.",
                GH_ParamAccess.list);
            pManager.AddColourParameter(
                "Colors",
                "C",
                "Preview color for each segment.",
                GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            _segments.Clear();
            _clippingBox = BoundingBox.Empty;
            _legendMaximum = 0.0;

            StbParsedResults results;
            int loadCase = 0;
            int divisions = 12;
            double requestedMaximum = 0.0;

            if (!StbModelGooUtil.TryGetResults(da, 0, out results))
            {
                return;
            }

            da.GetData(1, ref loadCase);
            da.GetData(2, ref divisions);
            da.GetData(3, ref requestedMaximum);
            da.GetData(4, ref _showLegend);
            divisions = Math.Max(1, Math.Min(100, divisions));
            Message = Modes[_mode].Name;

            if (results.Sections.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Error,
                    "Results contain no SPRP section properties. Re-run STB Analyze.");
                return;
            }

            var nodes = new Dictionary<int, Point3d>();
            foreach (var node in results.Nodes)
            {
                nodes[node.NodeId] = node.Point;
            }

            var elements = new Dictionary<int, StbElementGeometry>();
            foreach (var element in results.Elements)
            {
                elements[element.ElementId] = element;
            }

            var sections = new Dictionary<int, StbSectionProperties>();
            foreach (var section in results.Sections)
            {
                sections[section.SectionId] = section;
            }

            var rawSegments = new List<RawStressSegment>();
            foreach (var force in results.ElementForces)
            {
                if (!StbLoadCaseFilter.Matches(loadCase, force.LoadCase))
                {
                    continue;
                }

                if (!elements.TryGetValue(force.ElementId, out var element)
                    || !nodes.TryGetValue(element.NodeI, out var start)
                    || !nodes.TryGetValue(element.NodeJ, out var end)
                    || !sections.TryGetValue(element.SectionId, out var section))
                {
                    continue;
                }

                if (section.Area <= 0.0 || section.Wy <= 0.0 || section.Wz <= 0.0)
                {
                    continue;
                }

                for (var i = 0; i < divisions; i++)
                {
                    var t0 = (double)i / divisions;
                    var t1 = (double)(i + 1) / divisions;
                    var stress = StressAt(force, section, 0.5 * (t0 + t1));
                    if (!IsFinite(stress))
                    {
                        continue;
                    }

                    var line = new Line(
                        Interpolate(start, end, t0),
                        Interpolate(start, end, t1));

                    rawSegments.Add(new RawStressSegment(line, stress));
                    _legendMaximum = Math.Max(_legendMaximum, stress);
                    _clippingBox.Union(line.BoundingBox);
                }
            }

            if (rawSegments.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    "No stress data could be created for load case " + loadCase + ".");
                return;
            }

            if (IsFinite(requestedMaximum) && requestedMaximum > 0.0)
            {
                _legendMaximum = requestedMaximum;
            }

            if (_legendMaximum <= 0.0)
            {
                _legendMaximum = 1.0;
            }

            var outputLines = new List<Line>();
            var outputStress = new List<double>();
            var outputColors = new List<Color>();

            foreach (var segment in rawSegments)
            {
                var color = StbLegend.ColorFor(segment.Stress / _legendMaximum);
                _segments.Add(new StressSegment(segment.Line, color));
                outputLines.Add(segment.Line);
                outputStress.Add(segment.Stress);
                outputColors.Add(color);
            }

            da.SetDataList(0, outputLines);
            da.SetDataList(1, outputStress);
            da.SetDataList(2, outputColors);
        }

        public override void DrawViewportWires(IGH_PreviewArgs args)
        {
            foreach (var segment in _segments)
            {
                args.Display.DrawLine(segment.Line, segment.Color, 5);
            }

            if (_showLegend && _segments.Count > 0)
            {
                StbLegend.Draw(args, Modes[_mode].LegendTitle, _legendMaximum);
            }
        }

        public override bool Write(GH_IWriter writer)
        {
            writer.SetInt32(ModeKey, _mode);
            return base.Write(writer);
        }

        public override bool Read(GH_IReader reader)
        {
            if (reader.ItemExists(ModeKey))
            {
                var mode = reader.GetInt32(ModeKey);
                _mode = mode >= 0 && mode < Modes.Length ? mode : 0;
            }

            return base.Read(reader);
        }

        private double StressAt(ElementForce force, StbSectionProperties section, double t)
        {
            // Section forces follow the member sign convention, so interpolate the
            // signed values first and take magnitudes afterwards; that keeps the
            // bending stress at zero where the moment changes sign.
            var axial = Math.Abs(force.Ni + (force.Nj - force.Ni) * t) * 1e3 / section.Area;
            var bendingY = Math.Abs(Quadratic(force.Myi, force.Myc, force.Myj, t)) * 1e6 / section.Wy;
            var bendingZ = Math.Abs(Quadratic(force.Mzi, force.Mzc, force.Mzj, t)) * 1e6 / section.Wz;

            switch (_mode)
            {
                case 1: return axial;
                case 2: return bendingY;
                case 3: return bendingZ;
                default: return axial + bendingY + bendingZ;
            }
        }

        private static double Quadratic(double value0, double center, double value1, double t)
        {
            var l0 = 2.0 * (t - 0.5) * (t - 1.0);
            var lc = 4.0 * t * (1.0 - t);
            var l1 = 2.0 * t * (t - 0.5);
            return value0 * l0 + center * lc + value1 * l1;
        }

        private static Point3d Interpolate(Point3d start, Point3d end, double t)
        {
            return start + (end - start) * t;
        }

        private static bool IsFinite(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value);
        }

        private sealed class StressMode
        {
            public StressMode(string name, string legendTitle)
            {
                Name = name;
                LegendTitle = legendTitle;
            }

            public string Name { get; }
            public string LegendTitle { get; }
        }

        private sealed class RawStressSegment
        {
            public RawStressSegment(Line line, double stress)
            {
                Line = line;
                Stress = stress;
            }

            public Line Line { get; }
            public double Stress { get; }
        }

        private sealed class StressSegment
        {
            public StressSegment(Line line, Color color)
            {
                Line = line;
                Color = color;
            }

            public Line Line { get; }
            public Color Color { get; }
        }
    }
}
