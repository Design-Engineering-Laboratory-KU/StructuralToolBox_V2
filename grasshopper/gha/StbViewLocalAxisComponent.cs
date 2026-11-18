using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using Grasshopper.Kernel;
using Rhino.Display;
using Rhino.Geometry;

namespace StbGrasshopper
{
    /// <summary>
    /// Previews the local member axes (x along the member from start to end node,
    /// y and z from Beta) with the same rule the solver uses (StbMemberAxes).
    /// </summary>
    public sealed class StbViewLocalAxisComponent : GH_Component
    {
        private const double Zero = 1e-9;
        private const double AutoSizeRatio = 0.2;

        // Rhino's own axis colours: x red, y green, z blue.
        private static readonly Color XColor = Color.FromArgb(205, 55, 45);
        private static readonly Color YColor = Color.FromArgb(45, 150, 70);
        private static readonly Color ZColor = Color.FromArgb(40, 105, 200);
        private static readonly Color MemberColor = Color.FromArgb(150, 155, 160);
        private static readonly Color NameColor = Color.FromArgb(45, 50, 55);

        private readonly List<Triad> _triads = new List<Triad>();
        private BoundingBox _clippingBox = BoundingBox.Empty;
        private int _textSize = StbPreviewStyle.DefaultTextSize;
        private double _arrowSize = StbPreviewStyle.DefaultArrowSize;
        private bool _showLabels = true;
        private bool _showNames;

        public StbViewLocalAxisComponent()
            : base(
                "View Local Axis",
                "View Axis",
                "Display the local x / y / z axes of STB members at mid-span (x red, y green, z blue). "
                + "x runs from the start node to the end node; y and z follow Beta as in the solver.",
                StbCategories.Tab,
                StbCategories.Info)
        {
        }

        public override Guid ComponentGuid => new Guid("3c6f0e52-9d1a-4b7e-a2c4-5e81d07b9f36");
        protected override Bitmap Icon => StbIcons.ViewLocalAxis;
        public override BoundingBox ClippingBox => _clippingBox;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "STb Model whose members are displayed.", GH_ParamAccess.item);
            pManager.AddParameter(new StbElementParameter(), "Element", "Elem", "Additional STb Element objects, e.g. before assembling the model.", GH_ParamAccess.list);
            pManager.AddTextParameter("Name", "Name", "Element names (STb Element Name) to display. Empty shows every element.", GH_ParamAccess.list);
            pManager.AddNumberParameter(
                "Size",
                "S",
                "Axis length in model units. 0 = automatic (" + AutoSizeRatio + " x the median member length).",
                GH_ParamAccess.item,
                0.0);
            pManager.AddBooleanParameter("Labels", "L", "Draw x / y / z labels at the arrow tips.", GH_ParamAccess.item, true);
            pManager.AddBooleanParameter("Names", "N", "Draw the element name at each member.", GH_ParamAccess.item, false);
            pManager.AddIntegerParameter("Text Size", "TS", StbPreviewStyle.TextSizeDescription, GH_ParamAccess.item, StbPreviewStyle.DefaultTextSize);
            pManager.AddNumberParameter("Arrow Size", "AS", StbPreviewStyle.ArrowSizeDescription, GH_ParamAccess.item, StbPreviewStyle.DefaultArrowSize);
            pManager[0].Optional = true;
            pManager[1].Optional = true;
            pManager[2].Optional = true;
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddPlaneParameter("Planes", "P", "Local plane of each member at mid-span (X = local x, Y = local y, Z = local z).", GH_ParamAccess.list);
            pManager.AddVectorParameter("x", "x", "Local x axis (start node to end node).", GH_ParamAccess.list);
            pManager.AddVectorParameter("y", "y", "Local y axis.", GH_ParamAccess.list);
            pManager.AddVectorParameter("z", "z", "Local z axis.", GH_ParamAccess.list);
            pManager.AddTextParameter("Names", "Names", "Element name of each plane.", GH_ParamAccess.list);
        }

        protected override void BeforeSolveInstance()
        {
            _triads.Clear();
            _clippingBox = BoundingBox.Empty;
            base.BeforeSolveInstance();
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var elements = new List<StbElementModel>();
            StbModelGoo modelGoo = null;
            if (da.GetData(0, ref modelGoo) && modelGoo?.Value != null)
            {
                elements.AddRange(modelGoo.Value.Elements.Where(e => e != null));
            }

            var elementGoos = new List<StbElementGoo>();
            da.GetDataList(1, elementGoos);
            elements.AddRange(elementGoos.Where(g => g?.Value != null).Select(g => g.Value));
            if (elements.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Connect an STb Model or STb Element objects.");
                return;
            }

            var names = new List<string>();
            da.GetDataList(2, names);
            elements = FilterByName(elements, names);

            var size = 0.0;
            da.GetData(3, ref size);
            da.GetData(4, ref _showLabels);
            da.GetData(5, ref _showNames);
            _textSize = StbPreviewStyle.ReadTextSize(da, 6, this);
            _arrowSize = StbPreviewStyle.ReadArrowSize(da, 7, this);

            var valid = elements.Where(e => e.Line.IsValid && e.Line.Length > Zero).ToList();
            var skipped = elements.Count - valid.Count;
            if (skipped > 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, skipped + " zero-length or invalid member(s) skipped.");
            }

            if (valid.Count == 0)
            {
                return;
            }

            if (size < 0.0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Size must not be negative; using automatic size.");
                size = 0.0;
            }

            if (size <= Zero)
            {
                size = AutoSizeRatio * Median(valid.Select(e => e.Line.Length));
            }

            var planes = new List<Plane>();
            var xs = new List<Vector3d>();
            var ys = new List<Vector3d>();
            var zs = new List<Vector3d>();
            var outNames = new List<string>();
            foreach (var element in valid)
            {
                var line = element.Line;
                StbMemberAxes.Compute(line, element.Beta, out var x, out var y, out var z);
                var origin = line.PointAt(0.5);
                var triad = new Triad
                {
                    Member = line,
                    Origin = origin,
                    X = new Line(origin, origin + x * size),
                    Y = new Line(origin, origin + y * size),
                    Z = new Line(origin, origin + z * size),
                    Name = element.Name ?? string.Empty,
                };
                _triads.Add(triad);
                _clippingBox.Union(line.BoundingBox);
                _clippingBox.Union(triad.X.To);
                _clippingBox.Union(triad.Y.To);
                _clippingBox.Union(triad.Z.To);

                planes.Add(new Plane(origin, x, y));
                xs.Add(x);
                ys.Add(y);
                zs.Add(z);
                outNames.Add(triad.Name);
            }

            da.SetDataList(0, planes);
            da.SetDataList(1, xs);
            da.SetDataList(2, ys);
            da.SetDataList(3, zs);
            da.SetDataList(4, outNames);
        }

        public override void DrawViewportWires(IGH_PreviewArgs args)
        {
            var selected = Attributes.Selected;
            var display = args.Display;
            foreach (var triad in _triads)
            {
                display.DrawLine(triad.Member, selected ? args.WireColour_Selected : MemberColor, 1);
                StbPreviewStyle.DrawArrow(display, triad.X, XColor, _arrowSize);
                StbPreviewStyle.DrawArrow(display, triad.Y, YColor, _arrowSize);
                StbPreviewStyle.DrawArrow(display, triad.Z, ZColor, _arrowSize);

                if (_showLabels)
                {
                    StbPreviewStyle.DrawText(display, "x", XColor, triad.X.To, _textSize);
                    StbPreviewStyle.DrawText(display, "y", YColor, triad.Y.To, _textSize);
                    StbPreviewStyle.DrawText(display, "z", ZColor, triad.Z.To, _textSize);
                }

                if (_showNames && triad.Name.Length > 0)
                {
                    // Opposite the z arrow so the name does not sit on a label.
                    var at = triad.Origin - triad.Z.Direction * 0.35;
                    StbPreviewStyle.DrawText(display, triad.Name, NameColor, at, _textSize);
                }
            }
        }

        private List<StbElementModel> FilterByName(List<StbElementModel> elements, List<string> names)
        {
            var wanted = new HashSet<string>(
                names.Where(n => !string.IsNullOrWhiteSpace(n)).Select(n => n.Trim()),
                StringComparer.Ordinal);
            if (wanted.Count == 0)
            {
                return elements;
            }

            var result = elements.Where(e => e.Name != null && wanted.Contains(e.Name.Trim())).ToList();
            var found = new HashSet<string>(result.Select(e => e.Name.Trim()), StringComparer.Ordinal);
            var missing = wanted.Where(n => !found.Contains(n)).ToList();
            if (missing.Count > 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "No element named: " + string.Join(", ", missing) + ".");
            }

            return result;
        }

        private static double Median(IEnumerable<double> values)
        {
            var sorted = values.OrderBy(v => v).ToList();
            var mid = sorted.Count / 2;
            return sorted.Count % 2 == 1 ? sorted[mid] : 0.5 * (sorted[mid - 1] + sorted[mid]);
        }

        private sealed class Triad
        {
            public Line Member { get; set; }
            public Point3d Origin { get; set; }
            public Line X { get; set; }
            public Line Y { get; set; }
            public Line Z { get; set; }
            public string Name { get; set; }
        }
    }
}
