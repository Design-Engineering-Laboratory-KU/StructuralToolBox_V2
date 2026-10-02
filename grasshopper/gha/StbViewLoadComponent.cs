using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Linq;
using Grasshopper.Kernel;
using Rhino;
using Rhino.Display;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbViewLoadComponent : GH_Component
    {
        private const double Zero = 1e-9;

        private static readonly Color PointColor = Color.FromArgb(215, 60, 60);
        private static readonly Color MomentColor = Color.FromArgb(160, 40, 120);
        private static readonly Color LineColor = Color.FromArgb(230, 140, 20);
        private static readonly Color AreaColor = Color.FromArgb(45, 95, 215);
        private static readonly Color GravityColor = Color.FromArgb(110, 80, 170);

        private readonly List<LoadArrow> _arrows = new List<LoadArrow>();
        private readonly List<(Polyline Line, Color Color)> _outlines = new List<(Polyline Line, Color Color)>();
        private readonly List<Mesh> _panels = new List<Mesh>();
        private readonly List<LoadLabel> _labels = new List<LoadLabel>();
        private BoundingBox _clippingBox = BoundingBox.Empty;
        private bool _showValues = true;

        public StbViewLoadComponent()
            : base(
                "View Load",
                "View Ld",
                "Display STB point, line, area and gravity loads as arrows in the Rhino viewport.",
                StbCategories.Tab,
                StbCategories.Info)
        {
        }

        public override Guid ComponentGuid => new Guid("3c9d6e21-48a7-4f0b-b5e3-7a1f2c8d9e64");
        protected override Bitmap Icon => StbIcons.ViewLoad;
        public override BoundingBox ClippingBox => _clippingBox;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "STb Model whose loads are displayed.", GH_ParamAccess.item);
            pManager.AddParameter(new StbLoadParameter(), "Load", "Ld", "Additional STb Load objects, e.g. before assembling the model.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Load Case", "LC", "Load case to display. Negative means all. A combination LC shows its factored load cases.", GH_ParamAccess.item, -1);
            pManager.AddNumberParameter("Scale", "S", "Length of the largest arrow of each load kind in model units. 0 = automatic.", GH_ParamAccess.item, 0.0);
            pManager.AddBooleanParameter("Values", "V", "Show load values in the Rhino viewport.", GH_ParamAccess.item, true);
            pManager[0].Optional = true;
            pManager[1].Optional = true;
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddIntegerParameter("Load Cases", "LCs", "Load case ids found in the loads, combinations included.", GH_ParamAccess.list);
            pManager.AddLineParameter("Arrows", "A", "Load arrows; each ends at the point where the load acts.", GH_ParamAccess.list);
            pManager.AddTextParameter("Descriptions", "D", "One description per displayed load.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            _arrows.Clear();
            _outlines.Clear();
            _panels.Clear();
            _labels.Clear();
            _clippingBox = BoundingBox.Empty;

            StbModelModel model = null;
            StbModelGoo modelGoo = null;
            if (da.GetData(0, ref modelGoo))
            {
                model = modelGoo?.Value;
            }

            var loadGoos = new List<StbLoadGoo>();
            da.GetDataList(1, loadGoos);

            var loadCase = -1;
            var scale = 0.0;
            var showValues = true;
            da.GetData(2, ref loadCase);
            da.GetData(3, ref scale);
            da.GetData(4, ref showValues);
            _showValues = showValues;

            var loads = new List<StbLoadModel>();
            if (model != null)
            {
                loads.AddRange(model.Loads.Where(l => l != null));
            }

            loads.AddRange(loadGoos.Where(g => g?.Value != null).Select(g => g.Value));
            if (loads.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Connect an STb Model or STb Load objects.");
                return;
            }

            da.SetDataList(0, loads.Select(l => l.LoadCase).Distinct().OrderBy(v => v));

            var factors = CaseFactors(loads, loadCase);
            var selected = new List<StbLoadModel>();
            foreach (var load in loads)
            {
                if (load.Kind == StbLoadKind.Combination)
                {
                    continue;
                }

                if (loadCase < 0)
                {
                    selected.Add(load);
                }
                else if (factors.TryGetValue(load.LoadCase, out var factor) && Math.Abs(factor) > Zero)
                {
                    selected.Add(Factored(load, factor));
                }
            }

            if (selected.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "No loads found for load case " + loadCase + ".");
                return;
            }

            if (loadCase >= 0 && factors.Count > 1)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Remark,
                    "LC" + loadCase + " is a combination: " + string.Join(" + ", factors.Select(p => Number(p.Value) + "×LC" + p.Key)) + ".");
            }

            var tolerance = RhinoDoc.ActiveDoc?.ModelAbsoluteTolerance ?? 0.001;
            var modelBox = ModelBox(model, selected, tolerance);
            var arrowLength = scale > 0.0
                ? scale
                : (modelBox.IsValid ? Math.Max(modelBox.Diagonal.Length * 0.12, 0.1) : 1.0);
            var spacing = modelBox.IsValid ? Math.Max(modelBox.Diagonal.Length / 40.0, tolerance * 10.0) : arrowLength * 0.3;

            var descriptions = new List<string>();
            AddPointLoads(selected, arrowLength, descriptions);
            AddLineLoads(selected, model, arrowLength, spacing, descriptions);
            AddAreaLoads(selected, arrowLength, spacing, tolerance, descriptions);
            AddGravityLoads(selected, modelBox, arrowLength, descriptions);

            if (selected.Any(l => l.Kind == StbLoadKind.Line && !l.IsGlobal) && model == null)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, "Local line loads use Beta = 0 without an STb Model.");
            }

            da.SetDataList(1, _arrows.Select(a => a.Line));
            da.SetDataList(2, descriptions);
        }

        public override void DrawViewportMeshes(IGH_PreviewArgs args)
        {
            var material = new DisplayMaterial(AreaColor, 0.75);
            foreach (var panel in _panels)
            {
                args.Display.DrawMeshShaded(panel, material);
            }
        }

        public override void DrawViewportWires(IGH_PreviewArgs args)
        {
            foreach (var (outline, color) in _outlines)
            {
                args.Display.DrawPolyline(outline, color, 1);
            }

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
            }

            if (!_showValues)
            {
                return;
            }

            foreach (var label in _labels)
            {
                args.Display.Draw2dText(label.Text, label.Color, label.Point, true, 14);
            }
        }

        /// <summary>
        /// Factor per basic load case for the selected LC. A combination LC expands
        /// through LCMB records (nested combinations included); any other LC is itself × 1.
        /// </summary>
        private static SortedDictionary<int, double> CaseFactors(List<StbLoadModel> loads, int loadCase)
        {
            var factors = new SortedDictionary<int, double>();
            if (loadCase < 0)
            {
                return factors;
            }

            var combinations = new Dictionary<int, StbLoadModel>();
            foreach (var load in loads)
            {
                if (load.Kind == StbLoadKind.Combination && !combinations.ContainsKey(load.LoadCase))
                {
                    combinations[load.LoadCase] = load;
                }
            }

            Expand(loadCase, 1.0, combinations, factors, new HashSet<int>());
            return factors;
        }

        private static void Expand(int loadCase, double factor, Dictionary<int, StbLoadModel> combinations, SortedDictionary<int, double> factors, HashSet<int> visiting)
        {
            if (!combinations.TryGetValue(loadCase, out var combination) || !visiting.Add(loadCase))
            {
                factors.TryGetValue(loadCase, out var existing);
                factors[loadCase] = existing + factor;
                return;
            }

            var count = Math.Min(combination.CombinationCases.Count, combination.CombinationFactors.Count);
            for (var i = 0; i < count; i++)
            {
                Expand(combination.CombinationCases[i], factor * combination.CombinationFactors[i], combinations, factors, visiting);
            }

            visiting.Remove(loadCase);
        }

        private static StbLoadModel Factored(StbLoadModel load, double factor)
        {
            if (Math.Abs(factor - 1.0) <= Zero)
            {
                return load;
            }

            var copy = load.Duplicate();
            copy.Force *= factor;
            copy.Moment *= factor;
            copy.LoadAtI *= factor;
            copy.LoadAtJ *= factor;
            copy.Pressure *= factor;
            copy.Acceleration *= factor;
            return copy;
        }

        private void AddPointLoads(List<StbLoadModel> loads, double maxLength, List<string> descriptions)
        {
            var points = loads.Where(l => l.Kind == StbLoadKind.Point && l.Point.IsValid).ToList();
            var maxForce = points.Count == 0 ? 0.0 : points.Max(l => l.Force.Length);
            var maxMoment = points.Count == 0 ? 0.0 : points.Max(l => l.Moment.Length);
            var minLength = maxLength * 0.25;

            foreach (var load in points)
            {
                var forceLength = 0.0;
                if (load.Force.Length > Zero)
                {
                    var direction = load.Force;
                    direction.Unitize();
                    forceLength = minLength + (maxLength - minLength) * load.Force.Length / maxForce;
                    var tail = load.Point - direction * forceLength;
                    AddArrow(new LoadArrow { Line = new Line(tail, load.Point), Color = PointColor });
                    AddLabel(Number(load.Force.Length) + " kN", tail, PointColor);
                }

                if (load.Moment.Length > Zero)
                {
                    // Placed on the side opposite the force tail so both stay readable.
                    var direction = load.Moment;
                    direction.Unitize();
                    var length = minLength + (maxLength - minLength) * load.Moment.Length / maxMoment;
                    var start = load.Point + direction * (maxLength * 0.08);
                    var end = start + direction * length;
                    AddArrow(new LoadArrow
                    {
                        Line = new Line(start, end),
                        Color = MomentColor,
                        IsMoment = true,
                        HeadSize = Math.Min(maxLength * 0.1, length * 0.45),
                    });
                    AddLabel(Number(load.Moment.Length) + " kNm", end, MomentColor);
                }

                descriptions.Add("Point LC" + load.LoadCase + " @ " + Format(load.Point)
                    + ": F=" + Format(load.Force) + " kN, M=" + Format(load.Moment) + " kNm");
            }
        }

        private void AddLineLoads(List<StbLoadModel> loads, StbModelModel model, double maxLength, double spacing, List<string> descriptions)
        {
            var lines = new List<(StbLoadModel Load, Vector3d Wi, Vector3d Wj)>();
            foreach (var load in loads)
            {
                if (load.Kind != StbLoadKind.Line || !load.ElementLine.IsValid || load.ElementLine.Length <= Zero)
                {
                    continue;
                }

                var wi = load.LoadAtI;
                var wj = load.LoadAtJ;
                if (!load.IsGlobal)
                {
                    StbMemberAxes.Compute(load.ElementLine, FindBeta(model, load.ElementLine), out var x, out var y, out var z);
                    wi = x * wi.X + y * wi.Y + z * wi.Z;
                    wj = x * wj.X + y * wj.Y + z * wj.Z;
                }

                lines.Add((load, wi, wj));
            }

            var maxW = lines.Count == 0 ? 0.0 : lines.Max(l => Math.Max(l.Wi.Length, l.Wj.Length));
            if (maxW <= Zero)
            {
                maxW = 1.0;
            }

            var factor = maxLength * 0.6 / maxW;
            foreach (var (load, wi, wj) in lines)
            {
                var line = load.ElementLine;
                AddDistributed(line, wi, wj, factor, spacing, LineColor);

                var label = Number(wi.Length) + (Math.Abs(wi.Length - wj.Length) > Zero ? " – " + Number(wj.Length) : string.Empty) + " kN/m";
                var mid = (wi + wj) * 0.5;
                AddLabel(label, line.PointAt(0.5) - mid * factor, LineColor);
                descriptions.Add("Line LC" + load.LoadCase + (load.IsGlobal ? " global" : " local")
                    + ": wi=" + Format(load.LoadAtI) + ", wj=" + Format(load.LoadAtJ) + " kN/m");
            }
        }

        /// <summary>Trapezoidal arrow row along a line; tails are joined by an outline.</summary>
        private void AddDistributed(Line line, Vector3d wi, Vector3d wj, double factor, double spacing, Color color)
        {
            var count = Math.Max(2, Math.Min(30, (int)Math.Ceiling(line.Length / spacing)));
            var outline = new Polyline { line.From };
            for (var k = 0; k <= count; k++)
            {
                var t = (double)k / count;
                var at = line.PointAt(t);
                var w = wi + (wj - wi) * t;
                var tail = at - w * factor;
                outline.Add(tail);
                if (w.Length * factor > spacing * 0.05)
                {
                    AddArrow(new LoadArrow { Line = new Line(tail, at), Color = color });
                }
            }

            outline.Add(line.To);
            AddOutline(outline, color);
        }

        private void AddAreaLoads(List<StbLoadModel> loads, double maxLength, double spacing, double tolerance, List<string> descriptions)
        {
            var areas = loads.Where(l => l.Kind == StbLoadKind.Area).ToList();
            var maxP = areas.Count == 0 ? 0.0 : areas.Max(l => l.Pressure.Length);
            if (maxP <= Zero)
            {
                maxP = 1.0;
            }

            var factor = maxLength * 0.5 / maxP;
            foreach (var load in areas)
            {
                var corners = StbAreaLoadDistributor.BoundaryPolygon(load.BoundaryLines, tolerance);
                if (corners == null)
                {
                    AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Area load LC" + load.LoadCase + " boundary is not one closed loop.");
                    continue;
                }

                var polygon = new Polyline(corners) { corners[0] };
                var mesh = Mesh.CreateFromClosedPolyline(polygon);
                if (mesh != null)
                {
                    _panels.Add(mesh);
                    _clippingBox.Union(mesh.GetBoundingBox(true));
                }

                var offset = -load.Pressure * factor;
                var raised = new Polyline(polygon.Select(p => p + offset));
                AddOutline(raised, AreaColor);

                if (Plane.FitPlaneToPoints(corners, out var plane) == PlaneFitResult.Success)
                {
                    var curve = polygon.ToPolylineCurve();
                    var box = new BoundingBox(corners.Select(p => plane.RemapToPlaneSpace(p, out var q) ? q : Point3d.Origin));
                    var step = Math.Max(spacing * 1.5, Math.Max(box.Diagonal.X, box.Diagonal.Y) / 12.0);
                    if (load.Pressure.Length > Zero)
                    {
                        for (var u = box.Min.X + step * 0.5; u < box.Max.X; u += step)
                        {
                            for (var v = box.Min.Y + step * 0.5; v < box.Max.Y; v += step)
                            {
                                var at = plane.PointAt(u, v);
                                if (curve.Contains(at, plane, tolerance) == PointContainment.Inside)
                                {
                                    AddArrow(new LoadArrow { Line = new Line(at + offset, at), Color = AreaColor });
                                }
                            }
                        }
                    }
                }

                var centre = new Point3d(corners.Average(p => p.X), corners.Average(p => p.Y), corners.Average(p => p.Z));
                AddLabel(Number(load.Pressure.Length) + " kN/m²", centre + offset, AreaColor);
                descriptions.Add("Area LC" + load.LoadCase + ": P=" + Format(load.Pressure) + " kN/m²");
            }
        }

        private void AddGravityLoads(List<StbLoadModel> loads, BoundingBox modelBox, double maxLength, List<string> descriptions)
        {
            if (!modelBox.IsValid)
            {
                return;
            }

            var gravity = loads.Where(l => l.Kind == StbLoadKind.Gravity && l.Acceleration.Length > Zero).ToList();
            for (var i = 0; i < gravity.Count; i++)
            {
                var load = gravity[i];
                var direction = load.Acceleration;
                direction.Unitize();

                // One symbolic arrow per GLOD beside the model: self weight has no single location.
                var anchor = new Point3d(modelBox.Max.X, modelBox.Center.Y, modelBox.Center.Z)
                    + Vector3d.XAxis * maxLength * (0.5 + 0.4 * i);
                var tail = anchor - direction * maxLength;
                AddArrow(new LoadArrow { Line = new Line(tail, anchor), Color = GravityColor });
                AddLabel("Self weight LC" + load.LoadCase + " " + Number(load.Acceleration.Length) + " m/s²", tail, GravityColor);
                descriptions.Add("Gravity LC" + load.LoadCase + ": G=" + Format(load.Acceleration) + " m/s²");
            }
        }

        private static BoundingBox ModelBox(StbModelModel model, List<StbLoadModel> loads, double tolerance)
        {
            var box = BoundingBox.Empty;
            if (model != null)
            {
                foreach (var element in model.Elements.Where(e => e != null && e.Line.IsValid))
                {
                    box.Union(element.Line.From);
                    box.Union(element.Line.To);
                }

                foreach (var support in model.Supports.Where(s => s != null && s.Point.IsValid))
                {
                    box.Union(support.Point);
                }
            }

            foreach (var load in loads)
            {
                if (load.Point.IsValid) box.Union(load.Point);
                if (load.ElementLine.IsValid)
                {
                    box.Union(load.ElementLine.From);
                    box.Union(load.ElementLine.To);
                }

                foreach (var line in load.BoundaryLines)
                {
                    box.Union(line.From);
                    box.Union(line.To);
                }
            }

            return box;
        }

        private static double FindBeta(StbModelModel model, Line line)
        {
            if (model == null)
            {
                return 0.0;
            }

            var tolerance = RhinoDoc.ActiveDoc?.ModelAbsoluteTolerance ?? 0.001;
            foreach (var element in model.Elements)
            {
                if (element == null)
                {
                    continue;
                }

                var e = element.Line;
                if ((e.From.DistanceTo(line.From) <= tolerance && e.To.DistanceTo(line.To) <= tolerance)
                    || (e.From.DistanceTo(line.To) <= tolerance && e.To.DistanceTo(line.From) <= tolerance))
                {
                    return element.Beta;
                }
            }

            return 0.0;
        }

        private void AddArrow(LoadArrow arrow)
        {
            _arrows.Add(arrow);
            _clippingBox.Union(arrow.Line.From);
            _clippingBox.Union(arrow.Line.To);
        }

        private void AddOutline(Polyline outline, Color color)
        {
            _outlines.Add((outline, color));
            _clippingBox.Union(outline.BoundingBox);
        }

        private void AddLabel(string text, Point3d point, Color color)
        {
            _labels.Add(new LoadLabel { Text = text, Point = point, Color = color });
        }

        private static string Number(double value)
        {
            return value.ToString("0.##", CultureInfo.InvariantCulture);
        }

        private static string Format(Vector3d v)
        {
            return "(" + Number(v.X) + ", " + Number(v.Y) + ", " + Number(v.Z) + ")";
        }

        private static string Format(Point3d p)
        {
            return "(" + Number(p.X) + ", " + Number(p.Y) + ", " + Number(p.Z) + ")";
        }

        private sealed class LoadArrow
        {
            public Line Line { get; set; }
            public Color Color { get; set; }
            public bool IsMoment { get; set; }
            public double HeadSize { get; set; }
        }

        private sealed class LoadLabel
        {
            public string Text { get; set; } = string.Empty;
            public Point3d Point { get; set; }
            public Color Color { get; set; }
        }
    }
}
