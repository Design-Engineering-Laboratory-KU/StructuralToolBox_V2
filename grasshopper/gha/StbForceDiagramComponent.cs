using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Windows.Forms;
using Grasshopper.GUI;
using Grasshopper.GUI.Canvas;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Attributes;
using GH_IO.Serialization;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbForceDiagramComponent : GH_Component
    {
        private readonly List<DiagramSegment> _segments = new List<DiagramSegment>();
        private readonly List<GuideLine> _constructionLines = new List<GuideLine>();
        private readonly List<ValueLabel> _valueLabels = new List<ValueLabel>();
        private BoundingBox _clippingBox = BoundingBox.Empty;
        private double _legendMaximum;
        private double _legendLimit;
        private double _legendMinimum = 0.0;
        private double _legendRangeMaximum = 100.0;
        private string _componentLabel = "Nx";
        private string _unitLabel = "kN";
        private bool _showValues = true;
        private bool _showLegend = true;
        private double _diagramScale = 0.015;
        private double _diagramScaleMinimum = 0.0;
        private double _diagramScaleMaximum = 0.03;
        private double _textSize = 0.075;
        private double _textSizeMinimum = 0.05;
        private double _textSizeMaximum = 0.1;
        private int _componentIndex = 1;

        public StbForceDiagramComponent()
            : base(
                "STB Force Diagram",
                "STB FDiagram",
                "Draw a selected member force diagram and output its values in kN or kNm.",
                StbCategories.Tab,
                StbCategories.Post)
        {
        }

        public override Guid ComponentGuid =>
            new Guid("7a7f6f8c-62a2-4e07-9ef3-0b1c8d6e4f51");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.ForceDiagram;

        public override BoundingBox ClippingBox => _clippingBox;

        public override void CreateAttributes()
        {
            m_attributes = new StbForceDiagramAttributes(this);
        }

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "STb Model containing parsed results.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("Load Case", "LC", "Load case to display. Negative means all load cases.", GH_ParamAccess.item, 0);
            pManager.AddIntegerParameter("Divisions", "D", "Diagram segments per element.", GH_ParamAccess.item, 8);
            pManager.AddBooleanParameter("Values", "V", "Show value labels in the Rhino viewport.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("Legend", "Legend", "Draw the force legend in the Rhino viewport.", GH_ParamAccess.item, true);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddLineParameter("Diagram", "D", "Force diagram segments.", GH_ParamAccess.list);
            pManager.AddNumberParameter("Values", "V", "Signed force value at the start of each diagram segment in kN or kNm.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Element IDs", "E", "Element id for each diagram segment.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            _segments.Clear();
            _constructionLines.Clear();
            _valueLabels.Clear();
            _clippingBox = BoundingBox.Empty;
            _legendMaximum = 0.0;

            StbParsedResults results;
            int loadCase = 0;
            int component = _componentIndex;
            int divisions = 8;

            if (!StbModelGooUtil.TryGetResults(da, 0, out results))
            {
                return;
            }

            da.GetData(1, ref loadCase);
            da.GetData(2, ref divisions);
            var showValues = true;
            var showLegend = true;
            ReadInput(da, "Values", ref showValues);
            ReadInput(da, "Legend", ref showLegend);
            _showValues = showValues;
            _showLegend = showLegend;

            if (!TryGetComponent(component, out var componentInfo))
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Component must be 1=Nx, 2=Vy, 3=Vz, 4=Mx, 5=My, or 6=Mz.");
                return;
            }

            divisions = Math.Max(1, Math.Min(100, divisions));
            _componentLabel = componentInfo.Label;
            _unitLabel = componentInfo.Unit;
            _componentIndex = component;

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

            var rawSegments = new List<RawDiagramSegment>();
            foreach (var force in results.ElementForces)
            {
                if (!StbLoadCaseFilter.Matches(loadCase, force.LoadCase)
                    || !elements.TryGetValue(force.ElementId, out var element)
                    || !nodes.TryGetValue(element.NodeI, out var start)
                    || !nodes.TryGetValue(element.NodeJ, out var end))
                {
                    continue;
                }

                var memberLine = new Line(start, end);
                if (memberLine.Length <= 1e-9)
                {
                    continue;
                }

                StbMemberAxes.Compute(memberLine, element.Beta, out var axis, out var localY, out var localZ);
                var diagramDirection = DiagramDirection(
                    componentInfo.Label,
                    axis,
                    localY,
                    localZ,
                    StbMemberAxes.IsVertical(memberLine));
                var textNormal = Vector3d.CrossProduct(axis, diagramDirection);
                textNormal.Unitize();
                GetForceValues(force, componentInfo, out var valueI, out var valueCenter, out var valueJ);
                if (!IsFinite(valueI) || !IsFinite(valueCenter) || !IsFinite(valueJ))
                {
                    continue;
                }
                _legendMaximum = Math.Max(_legendMaximum, Math.Max(Math.Abs(valueI), Math.Max(Math.Abs(valueCenter), Math.Abs(valueJ))));

                var points = new List<Point3d>();
                for (var i = 0; i <= divisions; i++)
                {
                    var t = (double)i / divisions;
                    var basePoint = start + (end - start) * t;
                    var value = InterpolateForce(valueI, valueCenter, valueJ, t);
                    points.Add(basePoint + diagramDirection * (value * _diagramScale));
                }

                for (var i = 0; i < divisions; i++)
                {
                    var t0 = (double)i / divisions;
                    var t1 = (double)(i + 1) / divisions;
                    var value = InterpolateForce(valueI, valueCenter, valueJ, t0);
                    var centerValue = InterpolateForce(valueI, valueCenter, valueJ, 0.5 * (t0 + t1));
                    var line = new Line(points[i], points[i + 1]);
                    rawSegments.Add(new RawDiagramSegment(
                        line,
                        value,
                        centerValue,
                        force.ElementId,
                        textNormal,
                        points[i] + diagramDirection * LabelOffset(value),
                        points[i + 1] + diagramDirection * LabelOffset(InterpolateForce(valueI, valueCenter, valueJ, t1)),
                        i == divisions - 1,
                        InterpolateForce(valueI, valueCenter, valueJ, t1)));
                    ExtendClippingBox(line.BoundingBox);

                    var baseline = new Line(
                        start + (end - start) * t0,
                        start + (end - start) * t1);
                    _constructionLines.Add(new GuideLine(baseline, centerValue));
                    _constructionLines.Add(new GuideLine(new Line(baseline.From, line.From), value));
                    if (i == divisions - 1)
                    {
                        _constructionLines.Add(new GuideLine(new Line(baseline.To, line.To), centerValue));
                    }
                    ExtendClippingBox(baseline.BoundingBox);
                }
            }

            if (rawSegments.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "No force data could be created for load case " + loadCase + ".");
                return;
            }

            if (_legendLimit > 0.0)
            {
                _legendMaximum = _legendLimit;
            }

            if (_legendMaximum <= 0.0)
            {
                _legendMaximum = 1.0;
            }

            var outputLines = new List<Line>();
            var outputValues = new List<double>();
            var outputElementIds = new List<int>();
            foreach (var segment in rawSegments)
            {
                var color = StbLegend.ColorFor(Math.Abs(segment.CenterValue) / _legendMaximum);
                _segments.Add(new DiagramSegment(segment.Line, segment.Value, segment.ElementId, segment.TextNormal, color));
                _valueLabels.Add(new ValueLabel(segment.StartPoint, segment.Value, segment.TextNormal, color));
                if (segment.IsLast)
                {
                    _valueLabels.Add(new ValueLabel(segment.EndPoint, segment.EndValue, segment.TextNormal, color));
                }
                outputLines.Add(segment.Line);
                outputValues.Add(segment.Value);
                outputElementIds.Add(segment.ElementId);
            }

            da.SetDataList(0, outputLines);
            da.SetDataList(1, outputValues);
            da.SetDataList(2, outputElementIds);
        }

        internal double DiagramScale => _diagramScale;

        internal double DiagramScaleMinimum => _diagramScaleMinimum;

        internal double DiagramScaleMaximum => _diagramScaleMaximum;

        internal double TextSize => _textSize;

        internal double TextSizeMinimum => _textSizeMinimum;

        internal double TextSizeMaximum => _textSizeMaximum;

        internal double LegendValue => _legendLimit > 0.0 ? _legendLimit : _legendMaximum;

        internal double LegendMinimum => _legendMinimum;

        internal double LegendMaximum => _legendRangeMaximum;

        internal string ComponentLabel => _componentLabel;

        internal int ComponentIndex => _componentIndex;

        internal void SetComponent(int component)
        {
            if (component < 1 || component > 6 || component == _componentIndex)
            {
                return;
            }

            _componentIndex = component;
            ExpireSolution(true);
        }

        internal void SetDiagramScale(double value)
        {
            _diagramScale = Math.Max(_diagramScaleMinimum, Math.Min(_diagramScaleMaximum, value));
            ExpireSolution(true);
        }

        internal void SetTextSize(double value)
        {
            _textSize = Math.Max(_textSizeMinimum, Math.Min(_textSizeMaximum, value));
            ExpireSolution(true);
        }

        internal void SetLegendValue(double value)
        {
            _legendLimit = Math.Max(_legendMinimum, Math.Min(_legendRangeMaximum, value));
            ExpireSolution(true);
        }

        internal void EditDiagramScaleRange()
        {
            var minimum = _diagramScaleMinimum;
            if (!Rhino.UI.Dialogs.ShowNumberBox(
                "Diagram scale range",
                "Minimum value",
                ref minimum,
                0.0,
                _diagramScaleMaximum - 0.01))
            {
                return;
            }

            var maximum = _diagramScaleMaximum;
            if (Rhino.UI.Dialogs.ShowNumberBox(
                "Diagram scale range",
                "Maximum value",
                ref maximum,
                minimum + 0.01,
                100.0))
            {
                _diagramScaleMinimum = minimum;
                _diagramScaleMaximum = maximum;
                _diagramScale = Math.Max(minimum, Math.Min(_diagramScale, maximum));
                ExpireSolution(true);
            }
        }

        internal void EditTextSizeRange()
        {
            var minimum = _textSizeMinimum;
            if (!Rhino.UI.Dialogs.ShowNumberBox(
                "Text size range",
                "Minimum value",
                ref minimum,
                0.1,
                _textSizeMaximum - 0.1))
            {
                return;
            }

            var maximum = _textSizeMaximum;
            if (Rhino.UI.Dialogs.ShowNumberBox(
                "Text size range",
                "Maximum value",
                ref maximum,
                minimum + 0.1,
                100.0))
            {
                _textSizeMinimum = minimum;
                _textSizeMaximum = maximum;
                _textSize = Math.Max(minimum, Math.Min(_textSize, maximum));
                ExpireSolution(true);
            }
        }

        internal void EditLegendRange()
        {
            var minimum = _legendMinimum;
            if (!Rhino.UI.Dialogs.ShowNumberBox(
                "Legend range",
                "Minimum value",
                ref minimum,
                0.0,
                _legendRangeMaximum - 0.01))
            {
                return;
            }

            var maximum = _legendRangeMaximum;
            if (Rhino.UI.Dialogs.ShowNumberBox(
                "Legend range",
                "Maximum value",
                ref maximum,
                minimum + 0.01,
                100000.0))
            {
                _legendMinimum = minimum;
                _legendRangeMaximum = maximum;
                _legendLimit = Math.Max(minimum, Math.Min(_legendLimit, maximum));
                ExpireSolution(true);
            }
        }

        public override bool Write(GH_IWriter writer)
        {
            writer.SetDouble("DiagramScale", _diagramScale);
            writer.SetDouble("DiagramScaleMinimum", _diagramScaleMinimum);
            writer.SetDouble("DiagramScaleMaximum", _diagramScaleMaximum);
            writer.SetDouble("TextSize", _textSize);
            writer.SetDouble("TextSizeMinimum", _textSizeMinimum);
            writer.SetDouble("TextSizeMaximum", _textSizeMaximum);
            writer.SetInt32("ComponentIndex", _componentIndex);
            writer.SetDouble("LegendLimit", _legendLimit);
            writer.SetDouble("LegendMinimum", _legendMinimum);
            writer.SetDouble("LegendRangeMaximum", _legendRangeMaximum);
            return base.Write(writer);
        }

        public override bool Read(GH_IReader reader)
        {
            if (reader.ItemExists("DiagramScale"))
            {
                _diagramScale = reader.GetDouble("DiagramScale");
            }

            if (reader.ItemExists("TextSize"))
            {
                _textSize = reader.GetDouble("TextSize");
            }

            if (reader.ItemExists("DiagramScaleMaximum"))
            {
                _diagramScaleMaximum = reader.GetDouble("DiagramScaleMaximum");
            }

            if (reader.ItemExists("DiagramScaleMinimum"))
            {
                _diagramScaleMinimum = reader.GetDouble("DiagramScaleMinimum");
            }

            if (reader.ItemExists("TextSizeMaximum"))
            {
                _textSizeMaximum = reader.GetDouble("TextSizeMaximum");
            }

            if (reader.ItemExists("TextSizeMinimum"))
            {
                _textSizeMinimum = reader.GetDouble("TextSizeMinimum");
            }

            if (reader.ItemExists("ComponentIndex")) _componentIndex = reader.GetInt32("ComponentIndex");
            if (reader.ItemExists("LegendLimit")) _legendLimit = reader.GetDouble("LegendLimit");
            if (reader.ItemExists("LegendMinimum")) _legendMinimum = reader.GetDouble("LegendMinimum");
            if (reader.ItemExists("LegendRangeMaximum")) _legendRangeMaximum = reader.GetDouble("LegendRangeMaximum");

            return base.Read(reader);
        }

        public override void DrawViewportWires(IGH_PreviewArgs args)
        {
            foreach (var guide in _constructionLines)
            {
                args.Display.DrawLine(
                    guide.Line,
                    StbLegend.ColorFor(Math.Abs(guide.Value) / _legendMaximum),
                    2);
            }

            foreach (var segment in _segments)
            {
                args.Display.DrawLine(segment.Line, segment.Color, 2);
            }

            if (_showValues)
            {
                foreach (var label in _valueLabels)
                {
                    if (Math.Abs(label.Value) < 0.05)
                    {
                        continue;
                    }

                    args.Display.Draw3dText(
                        label.Value.ToString("0.0", CultureInfo.InvariantCulture),
                        label.Color,
                        new Plane(label.Point, args.Viewport.CameraX, args.Viewport.CameraY),
                        _textSize,
                        "Arial",
                        false,
                        false,
                        Rhino.DocObjects.TextHorizontalAlignment.Center,
                        Rhino.DocObjects.TextVerticalAlignment.Middle);
                }
            }

            if (_showLegend && _segments.Count > 0)
            {
                StbLegend.Draw(args, "|" + _componentLabel + "| [" + _unitLabel + "]", _legendMaximum);
            }
        }

        private void ExtendClippingBox(BoundingBox box)
        {
            if (!_clippingBox.IsValid)
            {
                _clippingBox = box;
                return;
            }

            _clippingBox.Union(box);
        }

        private bool ReadInput<T>(IGH_DataAccess dataAccess, string name, ref T value)
        {
            for (var index = 0; index < Params.Input.Count; index++)
            {
                if (string.Equals(Params.Input[index].Name, name, StringComparison.Ordinal))
                {
                    return dataAccess.GetData(index, ref value);
                }
            }

            return false;
        }

        private double LabelOffset(double value)
        {
            return (value < 0.0 ? -1.0 : 1.0) * _textSize * 0.5;
        }

        /// <summary>
        /// Offset direction for a positive value, matching the browser GUI
        /// (stb_gui/static/viewer.js buildForceDiagrams). The solver reports
        /// vertical members with flipped moment signs, so their My and Mz
        /// directions flip to keep moments on the tension side.
        /// </summary>
        private static Vector3d DiagramDirection(string label, Vector3d axis, Vector3d localY, Vector3d localZ, bool vertical)
        {
            switch (label)
            {
                case "Vy":
                    return localY;
                case "Vz":
                    return localZ;
                case "My":
                    return vertical ? localZ : -localZ;
                case "Mz":
                    return vertical ? -localY : localY;
                case "Nx":
                    return vertical && axis.Z < 0.0 ? -localZ : localZ;
                case "Mx":
                default:
                    return localZ;
            }
        }

        private static bool TryGetComponent(int component, out ForceComponentInfo info)
        {
            switch (component)
            {
                case 1: info = new ForceComponentInfo("Nx", "kN", (f, end) => end ? f.Nj : f.Ni); return true;
                case 2: info = new ForceComponentInfo("Vy", "kN", (f, end) => end ? f.Qyj : f.Qyi); return true;
                case 3: info = new ForceComponentInfo("Vz", "kN", (f, end) => end ? f.Qzj : f.Qzi); return true;
                case 4: info = new ForceComponentInfo("Mx", "kNm", (f, end) => end ? f.Mxj : f.Mxi); return true;
                case 5: info = new ForceComponentInfo("My", "kNm", (f, end) => end ? f.Myj : f.Myi); return true;
                case 6: info = new ForceComponentInfo("Mz", "kNm", (f, end) => end ? f.Mzj : f.Mzi); return true;
                default: info = null; return false;
            }
        }

        private static void GetForceValues(ElementForce force, ForceComponentInfo info, out double valueI, out double valueCenter, out double valueJ)
        {
            valueI = info.Value(force, false);
            valueJ = info.Value(force, true);
            valueCenter = valueI + 0.5 * (valueJ - valueI);
            if (info.Label == "My") valueCenter = force.Myc;
            if (info.Label == "Mz") valueCenter = force.Mzc;
        }

        private static double InterpolateForce(double valueI, double valueCenter, double valueJ, double t)
        {
            var l0 = 2.0 * (t - 0.5) * (t - 1.0);
            var lc = 4.0 * t * (1.0 - t);
            var l1 = 2.0 * t * (t - 0.5);
            return valueI * l0 + valueCenter * lc + valueJ * l1;
        }

        private static bool IsFinite(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value);
        }

        private sealed class ForceComponentInfo
        {
            public ForceComponentInfo(string label, string unit, Func<ElementForce, bool, double> value)
            {
                Label = label;
                Unit = unit;
                Value = value;
            }

            public string Label { get; }
            public string Unit { get; }
            public Func<ElementForce, bool, double> Value { get; }
        }

        private sealed class RawDiagramSegment
        {
            public RawDiagramSegment(
                Line line,
                double value,
                double centerValue,
                int elementId,
                Vector3d textNormal,
                Point3d startPoint,
                Point3d endPoint,
                bool isLast,
                double endValue)
            {
                Line = line;
                Value = value;
                CenterValue = centerValue;
                ElementId = elementId;
                TextNormal = textNormal;
                StartPoint = startPoint;
                EndPoint = endPoint;
                IsLast = isLast;
                EndValue = endValue;
            }

            public Line Line { get; }
            public double Value { get; }
            public double CenterValue { get; }
            public int ElementId { get; }
            public Vector3d TextNormal { get; }
            public Point3d StartPoint { get; }
            public Point3d EndPoint { get; }
            public bool IsLast { get; }
            public double EndValue { get; }
        }

        private sealed class ValueLabel
        {
            public ValueLabel(Point3d point, double value, Vector3d textNormal, Color color)
            {
                Point = point;
                Value = value;
                TextNormal = textNormal;
                Color = color;
            }

            public Point3d Point { get; }
            public double Value { get; }
            public Vector3d TextNormal { get; }
            public Color Color { get; }
        }

        private sealed class GuideLine
        {
            public GuideLine(Line line, double value)
            {
                Line = line;
                Value = value;
            }

            public Line Line { get; }
            public double Value { get; }
        }

        private sealed class DiagramSegment
        {
            public DiagramSegment(Line line, double value, int elementId, Vector3d textNormal, Color color)
            {
                Line = line;
                Value = value;
                ElementId = elementId;
                TextNormal = textNormal;
                Color = color;
            }

            public Line Line { get; }
            public double Value { get; }
            public int ElementId { get; }
            public Vector3d TextNormal { get; }
            public Color Color { get; }
        }
    }

    internal sealed class StbForceDiagramAttributes : GH_ComponentAttributes
    {
        private static readonly Color TrackColor = Color.FromArgb(70, 76, 82);
        private static readonly Color FillColor = Color.FromArgb(45, 170, 210);
        private readonly StbForceDiagramComponent _owner;
        private readonly RectangleF[] _componentButtons = new RectangleF[6];
        private RectangleF _scaleBounds;
        private RectangleF _textBounds;
        private RectangleF _legendBounds;
        private int _draggingSlider;

        public StbForceDiagramAttributes(StbForceDiagramComponent owner)
            : base(owner)
        {
            _owner = owner;
        }

        protected override void Layout()
        {
            base.Layout();

            const float stripHeight = 78f;
            const float margin = 4f;
            var original = Bounds;
            const float minimumWidth = 210f;
            var width = Math.Max(original.Width, minimumWidth);
            var left = original.X - (width - original.Width) * 0.5f;
            Bounds = new RectangleF(
                left,
                original.Y,
                width,
                original.Height + stripHeight);

            var inputOffset = Bounds.Left - original.Left;
            foreach (var input in _owner.Params.Input)
            {
                if (input.Attributes == null)
                {
                    continue;
                }

                var parameterBounds = input.Attributes.Bounds;
                parameterBounds.Offset(inputOffset, 0f);
                input.Attributes.Bounds = parameterBounds;
                var pivot = input.Attributes.Pivot;
                input.Attributes.Pivot = new PointF(pivot.X + inputOffset, pivot.Y);
            }

            var outputOffset = Bounds.Right - original.Right;
            foreach (var output in _owner.Params.Output)
            {
                if (output.Attributes == null)
                {
                    continue;
                }

                var parameterBounds = output.Attributes.Bounds;
                parameterBounds.Offset(outputOffset, 0f);
                output.Attributes.Bounds = parameterBounds;
                var pivot = output.Attributes.Pivot;
                output.Attributes.Pivot = new PointF(pivot.X + outputOffset, pivot.Y);
            }

            var rowWidth = Bounds.Width - 2f * margin;
            var buttonWidth = (rowWidth - 10f) / 6f;
            for (var i = 0; i < _componentButtons.Length; i++)
            {
                _componentButtons[i] = new RectangleF(
                    Bounds.Left + margin + i * (buttonWidth + 2f),
                    original.Bottom + 3f,
                    buttonWidth,
                    17f);
            }
            _scaleBounds = new RectangleF(
                Bounds.Left + margin,
                original.Bottom + 24f,
                rowWidth,
                18f);
            _textBounds = new RectangleF(
                Bounds.Left + margin,
                original.Bottom + 42f,
                rowWidth,
                18f);
            _legendBounds = new RectangleF(
                Bounds.Left + margin,
                original.Bottom + 60f,
                rowWidth,
                18f);
        }

        protected override void Render(
            GH_Canvas canvas,
            Graphics graphics,
            GH_CanvasChannel channel)
        {
            base.Render(canvas, graphics, channel);
            if (channel != GH_CanvasChannel.Objects)
            {
                return;
            }

            DrawSlider(graphics, _scaleBounds, "Scale", _owner.DiagramScale, _owner.DiagramScaleMinimum, _owner.DiagramScaleMaximum, "0.###");
            DrawSlider(graphics, _textBounds, "Text size", _owner.TextSize, _owner.TextSizeMinimum, _owner.TextSizeMaximum, "0.00");
            DrawSlider(graphics, _legendBounds, "Legend", _owner.LegendValue, _owner.LegendMinimum, _owner.LegendMaximum, "0.0");
            DrawComponentButtons(graphics);
        }

        public override GH_ObjectResponse RespondToMouseDown(
            GH_Canvas sender,
            GH_CanvasMouseEvent e)
        {
            if (e.Button == MouseButtons.Left)
            {
                for (var i = 0; i < _componentButtons.Length; i++)
                {
                    if (_componentButtons[i].Contains(e.CanvasLocation))
                    {
                        _owner.SetComponent(i + 1);
                        return GH_ObjectResponse.Handled;
                    }
                }

                if (_scaleBounds.Contains(e.CanvasLocation))
                {
                    _draggingSlider = 1;
                    UpdateSlider(e.CanvasLocation, _scaleBounds, _owner.DiagramScaleMinimum, _owner.DiagramScaleMaximum);
                    return GH_ObjectResponse.Capture;
                }

                if (_textBounds.Contains(e.CanvasLocation))
                {
                    _draggingSlider = 2;
                    UpdateSlider(e.CanvasLocation, _textBounds, _owner.TextSizeMinimum, _owner.TextSizeMaximum);
                    return GH_ObjectResponse.Capture;
                }

                if (_legendBounds.Contains(e.CanvasLocation))
                {
                    _draggingSlider = 3;
                    UpdateSlider(e.CanvasLocation, _legendBounds, _owner.LegendMinimum, _owner.LegendMaximum);
                    return GH_ObjectResponse.Capture;
                }
            }

            return base.RespondToMouseDown(sender, e);
        }

        public override GH_ObjectResponse RespondToMouseMove(
            GH_Canvas sender,
            GH_CanvasMouseEvent e)
        {
            if (_draggingSlider == 1)
            {
                UpdateSlider(e.CanvasLocation, _scaleBounds, _owner.DiagramScaleMinimum, _owner.DiagramScaleMaximum);
                return GH_ObjectResponse.Handled;
            }

            if (_draggingSlider == 2)
            {
                UpdateSlider(e.CanvasLocation, _textBounds, _owner.TextSizeMinimum, _owner.TextSizeMaximum);
                return GH_ObjectResponse.Handled;
            }

            if (_draggingSlider == 3)
            {
                UpdateSlider(e.CanvasLocation, _legendBounds, _owner.LegendMinimum, _owner.LegendMaximum);
                return GH_ObjectResponse.Handled;
            }

            return base.RespondToMouseMove(sender, e);
        }

        public override GH_ObjectResponse RespondToMouseUp(
            GH_Canvas sender,
            GH_CanvasMouseEvent e)
        {
            if (_draggingSlider != 0)
            {
                _draggingSlider = 0;
                return GH_ObjectResponse.Release;
            }

            return base.RespondToMouseUp(sender, e);
        }

        public override GH_ObjectResponse RespondToMouseDoubleClick(
            GH_Canvas sender,
            GH_CanvasMouseEvent e)
        {
            if (e.Button == MouseButtons.Left && _scaleBounds.Contains(e.CanvasLocation))
            {
                _owner.EditDiagramScaleRange();
                return GH_ObjectResponse.Handled;
            }

            if (e.Button == MouseButtons.Left && _textBounds.Contains(e.CanvasLocation))
            {
                _owner.EditTextSizeRange();
                return GH_ObjectResponse.Handled;
            }

            if (e.Button == MouseButtons.Left && _legendBounds.Contains(e.CanvasLocation))
            {
                _owner.EditLegendRange();
                return GH_ObjectResponse.Handled;
            }

            return base.RespondToMouseDoubleClick(sender, e);
        }

        private void DrawSlider(
            Graphics graphics,
            RectangleF bounds,
            string label,
            double value,
            double minimum,
            double maximum,
            string format)
        {
            var labelBounds = bounds;
            labelBounds.Width = 78f;
            using (var textBrush = new SolidBrush(Color.White))
            using (var trackBrush = new SolidBrush(TrackColor))
            using (var fillBrush = new SolidBrush(FillColor))
            using (var valueBrush = new SolidBrush(Color.White))
            {
                graphics.DrawString(label, SystemFonts.MessageBoxFont, textBrush, labelBounds);

                var track = new RectangleF(
                    bounds.Left + 82f,
                    bounds.Top + 7f,
                    Math.Max(20f, bounds.Width - 126f),
                    4f);
                graphics.FillRectangle(trackBrush, track);
                var normalized = (float)((value - minimum) / (maximum - minimum));
                normalized = Math.Max(0f, Math.Min(1f, normalized));
                graphics.FillRectangle(fillBrush, track.Left, track.Top, track.Width * normalized, track.Height);
                var knobX = track.Left + track.Width * normalized;
                graphics.FillEllipse(fillBrush, knobX - 5f, track.Top - 4f, 10f, 12f);

                var valueText = value.ToString(format, CultureInfo.InvariantCulture);
                var valueBounds = bounds;
                valueBounds.X = bounds.Right - 40f;
                valueBounds.Width = 40f;
                using (var formatInfo = new StringFormat
                {
                    Alignment = StringAlignment.Far,
                    LineAlignment = StringAlignment.Center,
                })
                {
                    graphics.DrawString(valueText, SystemFonts.MessageBoxFont, valueBrush, valueBounds, formatInfo);
                }
            }
        }

        private void DrawComponentButtons(Graphics graphics)
        {
            var labels = new[] { "Nx", "Vy", "Vz", "Mx", "My", "Mz" };
            using (var border = new Pen(Color.FromArgb(75, 80, 85), 1f))
            using (var textBrush = new SolidBrush(Color.White))
            using (var format = new StringFormat
            {
                Alignment = StringAlignment.Center,
                LineAlignment = StringAlignment.Center,
            })
            {
                for (var i = 0; i < labels.Length; i++)
                {
                    var fillColor = i + 1 == _owner.ComponentIndex
                        ? FillColor
                        : TrackColor;
                    using (var fill = new SolidBrush(fillColor))
                    {
                        graphics.FillRectangle(fill, _componentButtons[i]);
                    }

                    graphics.DrawRectangle(border, _componentButtons[i].X, _componentButtons[i].Y, _componentButtons[i].Width, _componentButtons[i].Height);
                    graphics.DrawString(labels[i], SystemFonts.MessageBoxFont, textBrush, _componentButtons[i], format);
                }
            }
        }

        private void UpdateSlider(PointF location, RectangleF bounds, double minimum, double maximum)
        {
            var trackLeft = bounds.Left + 82f;
            var trackRight = bounds.Right - 44f;
            var normalized = (double)(location.X - trackLeft) / Math.Max(1f, trackRight - trackLeft);
            normalized = Math.Max(0.0, Math.Min(1.0, normalized));
            var value = minimum + (maximum - minimum) * normalized;

            if (_draggingSlider == 1)
            {
                _owner.SetDiagramScale(value);
            }
            else if (_draggingSlider == 2)
            {
                _owner.SetTextSize(value);
            }
            else if (_draggingSlider == 3)
            {
                _owner.SetLegendValue(value);
            }
        }
    }
}
