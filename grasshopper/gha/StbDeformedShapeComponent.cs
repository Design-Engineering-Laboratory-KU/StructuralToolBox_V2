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
    public sealed class StbDeformedShapeComponent : GH_Component
    {
        private const int CurveDivisions = 12;
        private const double MetresToMillimetres = 1000.0;
        private readonly List<DeformedSegment> _segments = new List<DeformedSegment>();
        private BoundingBox _clippingBox = BoundingBox.Empty;
        private double _scale = 1.0;
        private double _scaleMinimum = 0.0;
        private double _scaleMaximum = 10.0;
        private double _legendMaximum;
        private bool _showLegend = true;

        public StbDeformedShapeComponent()
            : base(
                "STB Deformed Shape",
                "STB Def",
                "Create deformed points and member line segments from STB results.",
                StbCategories.Tab,
                StbCategories.Post)
        {
        }

        public override Guid ComponentGuid => new Guid("da5d7290-dd2e-4e49-a21a-db2420f7f59a");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.DeformedShape;

        public override BoundingBox ClippingBox => _clippingBox;

        public override void CreateAttributes()
        {
            m_attributes = new StbDeformedShapeAttributes(this);
        }

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "STb Model containing parsed results.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("Load Case", "LC", "Load case to display. Negative means all load cases.", GH_ParamAccess.item, 0);
            pManager.AddBooleanParameter("Legend", "Legend", "Draw the displacement legend in the Rhino viewport.", GH_ParamAccess.item, true);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddPointParameter("Initial Points", "Pi", "Original node points.", GH_ParamAccess.list);
            pManager.AddPointParameter("Deformed Points", "Pd", "Deformed node points.", GH_ParamAccess.list);
            pManager.AddLineParameter("Deformed Lines", "Ld", "Deformed member chords (straight line between the deformed end nodes).", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Node IDs", "N", "Node ids for deformed points.", GH_ParamAccess.list);
            pManager.AddCurveParameter("Deformed Curves", "Cd", "Deformed member axes interpolated from nodal translations and rotations.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            _segments.Clear();
            _clippingBox = BoundingBox.Empty;
            _legendMaximum = 0.0;

            StbParsedResults results;
            int loadCase = 0;

            if (!StbModelGooUtil.TryGetResults(da, 0, out results))
            {
                return;
            }

            da.GetData(1, ref loadCase);
            da.GetData(2, ref _showLegend);

            if (results.Nodes.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Error,
                    "Results contain no node geometry. Re-run STB Analyze with the same .dat file.");
                return;
            }

            var translationById = BuildTranslationLookup(results, loadCase, out var rotationById);
            if (loadCase >= 0 && translationById.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    "No displacement rows found for load case " + loadCase + ".");
            }

            var pointById = new Dictionary<int, Point3d>();
            var initialPoints = new List<Point3d>();
            var deformedPoints = new List<Point3d>();
            var nodeIds = new List<int>();

            foreach (var node in results.Nodes)
            {
                translationById.TryGetValue(node.NodeId, out var translation);
                var deformed = node.Point + translation * _scale;
                pointById[node.NodeId] = node.Point;
                initialPoints.Add(node.Point);
                deformedPoints.Add(deformed);
                nodeIds.Add(node.NodeId);
                _legendMaximum = Math.Max(_legendMaximum, translation.Length);
                _clippingBox.Union(node.Point);
                _clippingBox.Union(deformed);
            }

            var outputLines = new List<Line>();
            var outputCurves = new List<Polyline>();
            foreach (var element in results.Elements)
            {
                if (!pointById.TryGetValue(element.NodeI, out var p0) || !pointById.TryGetValue(element.NodeJ, out var p1))
                {
                    continue;
                }

                translationById.TryGetValue(element.NodeI, out var d0);
                translationById.TryGetValue(element.NodeJ, out var d1);
                rotationById.TryGetValue(element.NodeI, out var r0);
                rotationById.TryGetValue(element.NodeJ, out var r1);

                var curve = new Polyline(CurveDivisions + 1);
                var previous = Point3d.Unset;
                var previousDisplacement = 0.0;
                for (var k = 0; k <= CurveDivisions; k++)
                {
                    var t = (double)k / CurveDivisions;
                    var u = MemberDisplacement(p0, p1, d0, d1, r0, r1, t);
                    var point = p0 + (p1 - p0) * t + u * _scale;
                    var displacement = u.Length;
                    curve.Add(point);
                    _legendMaximum = Math.Max(_legendMaximum, displacement);
                    _clippingBox.Union(point);
                    if (k > 0)
                    {
                        _segments.Add(new DeformedSegment(new Line(previous, point), 0.5 * (previousDisplacement + displacement)));
                    }

                    previous = point;
                    previousDisplacement = displacement;
                }

                outputLines.Add(new Line(curve[0], curve[curve.Count - 1]));
                outputCurves.Add(curve);
            }

            if (_legendMaximum <= 0.0)
            {
                _legendMaximum = 1.0;
            }

            da.SetDataList(0, initialPoints);
            da.SetDataList(1, deformedPoints);
            da.SetDataList(2, outputLines);
            da.SetDataList(3, nodeIds);
            da.SetDataList(4, outputCurves);
        }

        /// <summary>
        /// Displacement of the member axis at t in [0, 1]: linear along the axis,
        /// cubic Hermite across it with end slopes θ × e taken from the nodal
        /// rotations. Deflection caused by loads between the nodes is not included.
        /// </summary>
        private static Vector3d MemberDisplacement(Point3d p0, Point3d p1, Vector3d d0, Vector3d d1, Vector3d r0, Vector3d r1, double t)
        {
            var axis = p1 - p0;
            var length = axis.Length;
            if (length <= 0.0)
            {
                return d0 * (1.0 - t) + d1 * t;
            }

            axis /= length;
            var a0 = d0 * axis;
            var a1 = d1 * axis;
            var v0 = d0 - axis * a0;
            var v1 = d1 - axis * a1;
            var s0 = Vector3d.CrossProduct(r0, axis);
            var s1 = Vector3d.CrossProduct(r1, axis);

            var t2 = t * t;
            var t3 = t2 * t;
            var h1 = 1.0 - 3.0 * t2 + 2.0 * t3;
            var h2 = t - 2.0 * t2 + t3;
            var h3 = 3.0 * t2 - 2.0 * t3;
            var h4 = t3 - t2;
            return axis * (a0 * (1.0 - t) + a1 * t) + v0 * h1 + s0 * (h2 * length) + v1 * h3 + s1 * (h4 * length);
        }

        internal double Scale => _scale;
        internal double ScaleMinimum => _scaleMinimum;
        internal double ScaleMaximum => _scaleMaximum;

        internal void SetScale(double value)
        {
            _scale = Math.Max(_scaleMinimum, Math.Min(_scaleMaximum, value));
            ExpireSolution(true);
        }

        internal void EditScaleRange()
        {
            var minimum = _scaleMinimum;
            if (!Rhino.UI.Dialogs.ShowNumberBox("Deformed shape scale range", "Minimum value", ref minimum, 0.0, _scaleMaximum - 0.01))
            {
                return;
            }

            var maximum = _scaleMaximum;
            if (Rhino.UI.Dialogs.ShowNumberBox("Deformed shape scale range", "Maximum value", ref maximum, minimum + 0.01, 100000.0))
            {
                _scaleMinimum = minimum;
                _scaleMaximum = maximum;
                _scale = Math.Max(minimum, Math.Min(_scale, maximum));
                ExpireSolution(true);
            }
        }

        public override bool Write(GH_IWriter writer)
        {
            writer.SetDouble("Scale", _scale);
            writer.SetDouble("ScaleMinimum", _scaleMinimum);
            writer.SetDouble("ScaleMaximum", _scaleMaximum);
            return base.Write(writer);
        }

        public override bool Read(GH_IReader reader)
        {
            if (reader.ItemExists("Scale")) _scale = reader.GetDouble("Scale");
            if (reader.ItemExists("ScaleMinimum")) _scaleMinimum = reader.GetDouble("ScaleMinimum");
            if (reader.ItemExists("ScaleMaximum")) _scaleMaximum = reader.GetDouble("ScaleMaximum");
            _scale = Math.Max(_scaleMinimum, Math.Min(_scaleMaximum, _scale));
            return base.Read(reader);
        }

        public override void DrawViewportWires(IGH_PreviewArgs args)
        {
            foreach (var segment in _segments)
            {
                args.Display.DrawLine(segment.Line, StbLegend.ColorFor(segment.Displacement / _legendMaximum), 3);
            }

            if (_showLegend && _segments.Count > 0)
            {
                StbLegend.Draw(args, "Displacement [mm]", _legendMaximum * MetresToMillimetres);
            }
        }

        private static Dictionary<int, Vector3d> BuildTranslationLookup(
            StbParsedResults results,
            int loadCase,
            out Dictionary<int, Vector3d> rotationById)
        {
            var translationById = new Dictionary<int, Vector3d>();
            rotationById = new Dictionary<int, Vector3d>();

            foreach (var row in results.Displacements)
            {
                if (!StbLoadCaseFilter.Matches(loadCase, row.LoadCase))
                {
                    continue;
                }

                translationById[row.NodeId] = new Vector3d(row.X, row.Y, row.Z);
                rotationById[row.NodeId] = new Vector3d(row.ThetaX, row.ThetaY, row.ThetaZ);
            }

            return translationById;
        }

        private sealed class DeformedSegment
        {
            public DeformedSegment(Line line, double displacement)
            {
                Line = line;
                Displacement = displacement;
            }

            public Line Line { get; }
            public double Displacement { get; }
        }
    }

    internal sealed class StbDeformedShapeAttributes : GH_ComponentAttributes
    {
        private static readonly Color TrackColor = Color.FromArgb(70, 76, 82);
        private static readonly Color FillColor = Color.FromArgb(45, 170, 210);
        private readonly StbDeformedShapeComponent _owner;
        private RectangleF _scaleBounds;
        private int _draggingSlider;

        public StbDeformedShapeAttributes(StbDeformedShapeComponent owner)
            : base(owner)
        {
            _owner = owner;
        }

        protected override void Layout()
        {
            base.Layout();
            const float stripHeight = 24f;
            const float margin = 4f;
            var original = Bounds;
            var width = Math.Max(original.Width, 210f);
            var left = original.X - (width - original.Width) * 0.5f;
            Bounds = new RectangleF(left, original.Y, width, original.Height + stripHeight);
            var offset = Bounds.Left - original.Left;
            foreach (var input in _owner.Params.Input)
            {
                if (input.Attributes == null) continue;
                var bounds = input.Attributes.Bounds;
                bounds.Offset(offset, 0f);
                input.Attributes.Bounds = bounds;
                var pivot = input.Attributes.Pivot;
                input.Attributes.Pivot = new PointF(pivot.X + offset, pivot.Y);
            }

            var outputOffset = Bounds.Right - original.Right;
            foreach (var output in _owner.Params.Output)
            {
                if (output.Attributes == null) continue;
                var bounds = output.Attributes.Bounds;
                bounds.Offset(outputOffset, 0f);
                output.Attributes.Bounds = bounds;
                var pivot = output.Attributes.Pivot;
                output.Attributes.Pivot = new PointF(pivot.X + outputOffset, pivot.Y);
            }

            _scaleBounds = new RectangleF(Bounds.Left + margin, original.Bottom + 3f, Bounds.Width - 2f * margin, 18f);
        }

        protected override void Render(GH_Canvas canvas, Graphics graphics, GH_CanvasChannel channel)
        {
            base.Render(canvas, graphics, channel);
            if (channel == GH_CanvasChannel.Objects)
            {
                DrawSlider(graphics, _scaleBounds, "Scale", _owner.Scale, _owner.ScaleMinimum, _owner.ScaleMaximum);
            }
        }

        public override GH_ObjectResponse RespondToMouseDown(GH_Canvas sender, GH_CanvasMouseEvent e)
        {
            if (e.Button == MouseButtons.Left && _scaleBounds.Contains(e.CanvasLocation))
            {
                _draggingSlider = 1;
                UpdateSlider(e.CanvasLocation);
                return GH_ObjectResponse.Capture;
            }

            return base.RespondToMouseDown(sender, e);
        }

        public override GH_ObjectResponse RespondToMouseMove(GH_Canvas sender, GH_CanvasMouseEvent e)
        {
            if (_draggingSlider == 1)
            {
                UpdateSlider(e.CanvasLocation);
                return GH_ObjectResponse.Handled;
            }

            return base.RespondToMouseMove(sender, e);
        }

        public override GH_ObjectResponse RespondToMouseUp(GH_Canvas sender, GH_CanvasMouseEvent e)
        {
            if (_draggingSlider != 0)
            {
                _draggingSlider = 0;
                return GH_ObjectResponse.Release;
            }

            return base.RespondToMouseUp(sender, e);
        }

        public override GH_ObjectResponse RespondToMouseDoubleClick(GH_Canvas sender, GH_CanvasMouseEvent e)
        {
            if (e.Button == MouseButtons.Left && _scaleBounds.Contains(e.CanvasLocation))
            {
                _owner.EditScaleRange();
                return GH_ObjectResponse.Handled;
            }

            return base.RespondToMouseDoubleClick(sender, e);
        }

        private static void DrawSlider(Graphics graphics, RectangleF bounds, string label, double value, double minimum, double maximum)
        {
            using (var textBrush = new SolidBrush(Color.White))
            using (var trackBrush = new SolidBrush(TrackColor))
            using (var fillBrush = new SolidBrush(FillColor))
            {
                graphics.DrawString(label, SystemFonts.MessageBoxFont, textBrush, bounds);
                var track = new RectangleF(bounds.Left + 82f, bounds.Top + 7f, Math.Max(20f, bounds.Width - 126f), 4f);
                graphics.FillRectangle(trackBrush, track);
                var normalized = (float)((value - minimum) / (maximum - minimum));
                normalized = Math.Max(0f, Math.Min(1f, normalized));
                graphics.FillRectangle(fillBrush, track.Left, track.Top, track.Width * normalized, track.Height);
                var knobX = track.Left + track.Width * normalized;
                graphics.FillEllipse(fillBrush, knobX - 5f, track.Top - 4f, 10f, 12f);
                var valueBounds = bounds;
                valueBounds.X = bounds.Right - 40f;
                valueBounds.Width = 40f;
                using (var format = new StringFormat { Alignment = StringAlignment.Far, LineAlignment = StringAlignment.Center })
                {
                    graphics.DrawString(value.ToString("0.###", CultureInfo.InvariantCulture), SystemFonts.MessageBoxFont, textBrush, valueBounds, format);
                }
            }
        }

        private void UpdateSlider(PointF location)
        {
            var trackLeft = _scaleBounds.Left + 82f;
            var trackRight = _scaleBounds.Right - 44f;
            var normalized = (location.X - trackLeft) / Math.Max(1f, trackRight - trackLeft);
            normalized = Math.Max(0f, Math.Min(1f, normalized));
            _owner.SetScale(_owner.ScaleMinimum + (_owner.ScaleMaximum - _owner.ScaleMinimum) * normalized);
        }
    }
}
