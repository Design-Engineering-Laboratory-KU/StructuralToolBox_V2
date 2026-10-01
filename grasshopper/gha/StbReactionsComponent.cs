using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using Grasshopper.Kernel;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbReactionsComponent : GH_Component
    {
        private const double ZeroForce = 1e-6;

        private static readonly Color[] AxisColors =
        {
            Color.FromArgb(215, 60, 60),
            Color.FromArgb(40, 160, 70),
            Color.FromArgb(45, 95, 215),
        };

        private readonly List<ReactionArrow> _arrows = new List<ReactionArrow>();
        private BoundingBox _clippingBox = BoundingBox.Empty;
        private bool _showValues = true;

        public StbReactionsComponent()
            : base(
                "STB Reactions",
                "STB React",
                "Extract support reactions from STB results and preview them as arrows.",
                StbCategories.Tab,
                StbCategories.Post)
        {
        }

        public override Guid ComponentGuid => new Guid("b47e2c19-6a0d-4e85-9c3f-d815a2f7e640");

        protected override Bitmap Icon => StbIcons.Reactions;

        public override BoundingBox ClippingBox => _clippingBox;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "STb Model containing parsed results.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("Load Case", "LC", "Load case to extract. Negative means all (preview needs one load case).", GH_ParamAccess.item, 0);
            pManager.AddNumberParameter("Scale", "S", "Preview length of the largest reaction arrow in model units. 0 = automatic.", GH_ParamAccess.item, 0.0);
            pManager.AddBooleanParameter("Values", "V", "Show reaction values in the Rhino viewport.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("Moments", "Mo", "Preview reaction moments as double-headed arrows (right-hand rule) behind the force arrows.", GH_ParamAccess.item, true);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddIntegerParameter("Load Case", "LC", "Load case id for each row.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Node ID", "N", "Support node id for each row.", GH_ParamAccess.list);
            pManager.AddPointParameter("Point", "P", "Support node location.", GH_ParamAccess.list);
            pManager.AddVectorParameter("Force", "F", "Reaction force (Tx, Ty, Tz) in kN.", GH_ParamAccess.list);
            pManager.AddVectorParameter("Moment", "M", "Reaction moment (Rx, Ry, Rz) in kNm.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            _arrows.Clear();
            _clippingBox = BoundingBox.Empty;

            if (!StbModelGooUtil.TryGetResults(da, 0, out var results))
            {
                return;
            }

            int loadCase = 0;
            double scale = 0.0;
            bool showValues = true;
            bool showMoments = true;
            da.GetData(1, ref loadCase);
            da.GetData(2, ref scale);
            da.GetData(3, ref showValues);
            da.GetData(4, ref showMoments);
            _showValues = showValues;

            var nodePoints = new Dictionary<int, Point3d>();
            var modelBox = BoundingBox.Empty;
            foreach (var node in results.Nodes)
            {
                nodePoints[node.NodeId] = node.Point;
                modelBox.Union(node.Point);
            }

            var loadCases = new List<int>();
            var nodeIds = new List<int>();
            var points = new List<Point3d>();
            var forces = new List<Vector3d>();
            var moments = new List<Vector3d>();
            var missingNodes = 0;

            foreach (var row in results.Reactions)
            {
                if (!StbLoadCaseFilter.Matches(loadCase, row.LoadCase))
                {
                    continue;
                }

                var point = Point3d.Unset;
                if (!nodePoints.TryGetValue(row.NodeId, out point))
                {
                    missingNodes++;
                }

                loadCases.Add(row.LoadCase);
                nodeIds.Add(row.NodeId);
                points.Add(point);
                forces.Add(new Vector3d(row.Tx, row.Ty, row.Tz));
                moments.Add(new Vector3d(row.Rx, row.Ry, row.Rz));
            }

            if (loadCases.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    loadCase >= 0
                        ? "No reaction rows found for load case " + loadCase + "."
                        : "No reaction rows found.");
            }

            if (missingNodes > 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, missingNodes + " reaction node(s) have no coordinates.");
            }

            da.SetDataList(0, loadCases);
            da.SetDataList(1, nodeIds);
            da.SetDataList(2, points);
            da.SetDataList(3, forces);
            da.SetDataList(4, moments);

            if (loadCase < 0)
            {
                if (loadCases.Count > 0)
                {
                    AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, "Preview is off when all load cases are selected.");
                }

                return;
            }

            BuildArrows(points, forces, showMoments ? moments : null, scale, modelBox);
        }

        public override void DrawViewportWires(IGH_PreviewArgs args)
        {
            foreach (var arrow in _arrows)
            {
                if (arrow.IsMoment)
                {
                    var direction = arrow.Line.Direction;
                    direction.Unitize();
                    args.Display.DrawLine(arrow.Line, arrow.Color, 2);
                    args.Display.DrawArrowHead(arrow.Line.To, direction, arrow.Color, 0.0, arrow.HeadSize);
                    args.Display.DrawArrowHead(arrow.Line.To - direction * arrow.HeadSize * 0.6, direction, arrow.Color, 0.0, arrow.HeadSize);
                }
                else
                {
                    args.Display.DrawArrow(arrow.Line, arrow.Color);
                }

                if (_showValues)
                {
                    args.Display.Draw2dText(arrow.Label, arrow.Color, arrow.LabelPoint, true, 14);
                }
            }
        }

        private void BuildArrows(List<Point3d> points, List<Vector3d> forces, List<Vector3d> moments, double scale, BoundingBox modelBox)
        {
            var maxForce = MaxComponent(forces);
            var maxMoment = moments == null ? 0.0 : MaxComponent(moments);
            if (maxForce <= ZeroForce && maxMoment <= ZeroForce)
            {
                return;
            }

            var maxLength = scale > 0.0
                ? scale
                : (modelBox.IsValid ? Math.Max(modelBox.Diagonal.Length * 0.12, 0.1) : 1.0);
            var minLength = maxLength * 0.25;
            var gap = maxLength * 0.08;
            var headSize = maxLength * 0.1;
            var axes = new[] { Vector3d.XAxis, Vector3d.YAxis, Vector3d.ZAxis };

            for (var i = 0; i < forces.Count; i++)
            {
                if (!points[i].IsValid)
                {
                    continue;
                }

                var forceComponents = new[] { forces[i].X, forces[i].Y, forces[i].Z };
                var momentComponents = moments == null
                    ? new[] { 0.0, 0.0, 0.0 }
                    : new[] { moments[i].X, moments[i].Y, moments[i].Z };
                for (var axis = 0; axis < 3; axis++)
                {
                    var force = forceComponents[axis];
                    var moment = momentComponents[axis];
                    var hasForce = Math.Abs(force) > ZeroForce;
                    var hasMoment = Math.Abs(moment) > ZeroForce;
                    if (!hasForce && !hasMoment)
                    {
                        continue;
                    }

                    // Arrows for one axis sit on the side of the node the force arrow comes from.
                    var outward = axes[axis] * (hasForce ? -Math.Sign(force) : -Math.Sign(moment));
                    var offset = 0.0;
                    if (hasForce)
                    {
                        var length = minLength + (maxLength - minLength) * Math.Abs(force) / maxForce;
                        var tail = points[i] + outward * length;
                        Add(new ReactionArrow
                        {
                            Line = new Line(tail, points[i]),
                            LabelPoint = tail,
                            Color = AxisColors[axis],
                            Label = force.ToString("0.##", CultureInfo.InvariantCulture) + " kN",
                        });
                        offset = length + gap;
                    }

                    if (hasMoment)
                    {
                        var length = minLength + (maxLength - minLength) * Math.Abs(moment) / maxMoment;
                        var near = points[i] + outward * offset;
                        var far = points[i] + outward * (offset + length);
                        var pointsOutward = axes[axis] * Math.Sign(moment) * outward > 0.0;
                        Add(new ReactionArrow
                        {
                            Line = pointsOutward ? new Line(near, far) : new Line(far, near),
                            LabelPoint = far,
                            Color = AxisColors[axis],
                            Label = moment.ToString("0.##", CultureInfo.InvariantCulture) + " kNm",
                            IsMoment = true,
                            HeadSize = Math.Min(headSize, length * 0.45),
                        });
                    }
                }
            }
        }

        private void Add(ReactionArrow arrow)
        {
            _arrows.Add(arrow);
            _clippingBox.Union(arrow.Line.From);
            _clippingBox.Union(arrow.Line.To);
        }

        private static double MaxComponent(List<Vector3d> vectors)
        {
            var max = 0.0;
            foreach (var v in vectors)
            {
                max = Math.Max(max, Math.Max(Math.Abs(v.X), Math.Max(Math.Abs(v.Y), Math.Abs(v.Z))));
            }

            return max;
        }

        private sealed class ReactionArrow
        {
            public Line Line { get; set; }
            public Point3d LabelPoint { get; set; }
            public Color Color { get; set; }
            public string Label { get; set; } = string.Empty;
            public bool IsMoment { get; set; }
            public double HeadSize { get; set; }
        }
    }
}
