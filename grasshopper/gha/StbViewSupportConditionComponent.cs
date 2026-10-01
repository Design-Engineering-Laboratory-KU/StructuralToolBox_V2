using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using Grasshopper.Kernel;
using Rhino.Display;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbViewSupportConditionComponent : GH_Component
    {
        private static readonly Vector3d[] Axes = { Vector3d.XAxis, Vector3d.YAxis, Vector3d.ZAxis };
        private static readonly Color RigidColor = Color.FromArgb(35, 105, 65);
        private static readonly Color HingeColor = Color.FromArgb(40, 105, 175);
        private static readonly Color PinColor = Color.FromArgb(220, 145, 30);
        private static readonly Color RollerColor = Color.FromArgb(205, 210, 215);
        private static readonly Color GroundColor = Color.FromArgb(75, 82, 90);

        private readonly List<SupportGlyph> _glyphs = new List<SupportGlyph>();
        private BoundingBox _clippingBox = BoundingBox.Empty;
        private double _size = 0.35;

        public StbViewSupportConditionComponent()
            : base(
                "View Support Condition",
                "View Sup",
                "Display STB support conditions as consistent 3D symbols.",
                StbCategories.Tab,
                StbCategories.Info)
        {
        }

        public override Guid ComponentGuid => new Guid("f7a8b9c0-1234-4456-0789-abcdef012345");
        protected override Bitmap Icon => StbIcons.ViewSupport;
        public override BoundingBox ClippingBox => _clippingBox;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "Assembled STb Model.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Size", "S", "Support symbol size in model units.", GH_ParamAccess.item, 0.35);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddPointParameter("Points", "P", "Support locations.", GH_ParamAccess.list);
            pManager.AddBrepParameter("Symbols", "B", "Support symbol Breps.", GH_ParamAccess.list);
            pManager.AddTextParameter("Conditions", "C", "Support condition descriptions.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbModelModel model;
            if (!StbModelGooUtil.TryGetModel(da, 0, out model))
            {
                return;
            }

            var size = _size;
            da.GetData(1, ref size);
            _size = Math.Max(0.01, size);
            _glyphs.Clear();
            _clippingBox = BoundingBox.Empty;

            var points = new List<Point3d>();
            var symbols = new List<Brep>();
            var conditions = new List<string>();
            foreach (var support in model.Supports)
            {
                if (support == null || !support.Point.IsValid)
                {
                    continue;
                }

                var glyph = BuildGlyph(support, _size);
                _glyphs.Add(glyph);
                points.Add(support.Point);
                symbols.AddRange(glyph.Breps);
                conditions.Add(glyph.Description);
                foreach (var brep in glyph.Breps)
                {
                    _clippingBox.Union(brep.GetBoundingBox(true));
                }

                foreach (var rail in glyph.Rails)
                {
                    _clippingBox.Union(rail.From);
                    _clippingBox.Union(rail.To);
                }
            }

            da.SetDataList(0, points);
            da.SetDataList(1, symbols);
            da.SetDataList(2, conditions);
        }

        public override void DrawViewportMeshes(IGH_PreviewArgs args)
        {
            foreach (var glyph in _glyphs)
            {
                for (var i = 0; i < glyph.Breps.Count; i++)
                {
                    args.Display.DrawBrepShaded(glyph.Breps[i], new DisplayMaterial(glyph.Colors[i]));
                }
            }
        }

        public override void DrawViewportWires(IGH_PreviewArgs args)
        {
            foreach (var glyph in _glyphs)
            {
                foreach (var brep in glyph.Breps)
                {
                    args.Display.DrawBrepWires(brep, Color.FromArgb(45, 50, 55), 1);
                }

                foreach (var rail in glyph.Rails)
                {
                    args.Display.DrawLine(rail, Color.FromArgb(55, 65, 70), 2);
                }
            }
        }

        /// <summary>
        /// Two independent cues, so every combination stays readable:
        /// the body shape is the rotational condition (flat top = rigid,
        /// ridge = hinge line, apex = ball joint) and what carries the body
        /// is the translational condition (ground = fixed, rollers = free).
        /// </summary>
        private static SupportGlyph BuildGlyph(StbSupportModel support, double size)
        {
            var glyph = new SupportGlyph();
            AddBody(glyph, support, size);
            AddTranslationBase(glyph, support, size);
            glyph.Description = ConditionText(support);
            return glyph;
        }

        private static void AddBody(SupportGlyph glyph, StbSupportModel support, double size)
        {
            var top = support.Point;
            var height = size * 0.9;
            var half = size * 0.6;
            var xFree = !support.Rx;
            var yFree = !support.Ry;
            var zFree = !support.Rz;
            var freeCount = (xFree ? 1 : 0) + (yFree ? 1 : 0) + (zFree ? 1 : 0);

            if (freeCount == 0)
            {
                glyph.Add(Prism(top, half, half, height), RigidColor);
                return;
            }

            if (freeCount == 3)
            {
                glyph.Add(Pyramid(top, half, height), HingeColor);
                return;
            }

            if (xFree && yFree)
            {
                glyph.Add(Pyramid(top, half, height), HingeColor);
            }
            else if (xFree || yFree)
            {
                glyph.Add(Wedge(top, xFree ? 0 : 1, half, half, height), HingeColor);
            }
            else
            {
                glyph.Add(Prism(top, half, half, height), HingeColor);
            }

            // Only mixed conditions need pins: a plain box or pyramid already
            // says "no rotation free" or "every rotation free".
            var pinLength = size * 1.8;
            var pinRadius = size * 0.12;
            if (xFree) glyph.Add(Rod(top, Vector3d.XAxis, pinRadius, pinLength), PinColor);
            if (yFree) glyph.Add(Rod(top, Vector3d.YAxis, pinRadius, pinLength), PinColor);
            if (zFree) glyph.Add(Rod(top, Vector3d.ZAxis, pinRadius, pinLength), PinColor);
        }

        private static void AddTranslationBase(SupportGlyph glyph, StbSupportModel support, double size)
        {
            var bodyBottom = support.Point - Vector3d.ZAxis * size * 0.9;
            var freeHorizontal = new List<int>();
            if (!support.Tx) freeHorizontal.Add(0);
            if (!support.Ty) freeHorizontal.Add(1);

            if (!support.Tz)
            {
                AddVerticalSlider(glyph, support, size);
                return;
            }

            var radius = size * 0.17;
            var plateTop = bodyBottom;

            if (freeHorizontal.Count == 1)
            {
                var along = Axes[freeHorizontal[0]];
                var across = Axes[1 - freeHorizontal[0]];
                var centre = bodyBottom - Vector3d.ZAxis * radius;
                for (var side = -1; side <= 1; side += 2)
                {
                    glyph.Add(Rod(centre + along * (size * 0.42 * side), across, radius, size * 0.9), RollerColor);
                }

                plateTop = centre - Vector3d.ZAxis * radius;
                for (var side = -1; side <= 1; side += 2)
                {
                    var offset = plateTop + across * (size * 0.5 * side);
                    glyph.Rails.Add(new Line(offset - along * size * 0.95, offset + along * size * 0.95));
                }
            }
            else if (freeHorizontal.Count == 2)
            {
                var centre = bodyBottom - Vector3d.ZAxis * radius;
                foreach (var dx in new[] { -1, 1 })
                {
                    foreach (var dy in new[] { -1, 1 })
                    {
                        glyph.Add(Ball(centre + new Vector3d(size * 0.42 * dx, size * 0.42 * dy, 0.0), radius), RollerColor);
                    }
                }

                plateTop = centre - Vector3d.ZAxis * radius;
            }

            glyph.Add(Prism(plateTop, size * 0.95, size * 0.95, size * 0.12), GroundColor);
        }

        /// <summary>
        /// Tz free: the body is held by guide bars instead of resting on the ground.
        /// </summary>
        private static void AddVerticalSlider(SupportGlyph glyph, StbSupportModel support, double size)
        {
            if (!support.Tx && !support.Ty)
            {
                return;
            }

            var guide = support.Tx ? Vector3d.XAxis : Vector3d.YAxis;
            var rollerAxis = support.Tx ? Vector3d.YAxis : Vector3d.XAxis;
            var radius = size * 0.13;
            var mid = support.Point - Vector3d.ZAxis * size * 0.45;

            for (var side = -1; side <= 1; side += 2)
            {
                var barTop = support.Point + guide * (size * 0.92 * side) + Vector3d.ZAxis * size * 0.45;
                glyph.Add(Prism(barTop, size * 0.1, size * 0.5, size * 1.8, guide), GroundColor);
                glyph.Add(Rod(mid + guide * (size * 0.73 * side), rollerAxis, radius, size * 0.7), RollerColor);
                var railBase = support.Point + guide * (size * 1.02 * side);
                glyph.Rails.Add(new Line(railBase + Vector3d.ZAxis * size * 0.45, railBase - Vector3d.ZAxis * size * 1.35));
            }
        }

        private static string ConditionText(StbSupportModel support)
        {
            var translationFixed = support.Tx && support.Ty && support.Tz;
            var rotationFixed = support.Rx && support.Ry && support.Rz;
            var rotationFree = !support.Rx && !support.Ry && !support.Rz;
            var freeRotationAxes = (support.Rx ? "" : "X") + (support.Ry ? "" : "Y") + (support.Rz ? "" : "Z");

            string name;
            if (translationFixed)
            {
                name = rotationFixed ? "Fixed" : rotationFree ? "Pin" : "Hinge about " + freeRotationAxes;
            }
            else if (support.Tz)
            {
                name = "Roller along " + (!support.Tx && !support.Ty ? "XY" : support.Tx ? "Y" : "X");
            }
            else if (support.Tx || support.Ty)
            {
                name = "Vertical slider";
            }
            else
            {
                name = "Free translation";
            }

            var free = (support.Tx ? "" : "Tx ") + (support.Ty ? "" : "Ty ") + (support.Tz ? "" : "Tz ")
                + (support.Rx ? "" : "Rx ") + (support.Ry ? "" : "Ry ") + (support.Rz ? "" : "Rz");
            return name + " [free: " + (free.Length == 0 ? "none" : free.Trim()) + "]";
        }

        /// <summary>Box whose top face is centred on <paramref name="top"/>.</summary>
        private static Brep Prism(Point3d top, double halfX, double halfY, double height)
        {
            return Prism(top, halfX, halfY, height, Vector3d.XAxis);
        }

        private static Brep Prism(Point3d top, double halfX, double halfY, double height, Vector3d xAxis)
        {
            var plane = new Plane(top - Vector3d.ZAxis * height, xAxis, Vector3d.CrossProduct(Vector3d.ZAxis, xAxis));
            var box = new Box(plane, new Interval(-halfX, halfX), new Interval(-halfY, halfY), new Interval(0.0, height));
            return box.ToBrep();
        }

        private static Brep Pyramid(Point3d apex, double half, double height)
        {
            var bottom = apex - Vector3d.ZAxis * height;
            var mesh = new Mesh();
            var a = mesh.Vertices.Add(bottom + new Vector3d(-half, -half, 0));
            var b = mesh.Vertices.Add(bottom + new Vector3d(half, -half, 0));
            var c = mesh.Vertices.Add(bottom + new Vector3d(half, half, 0));
            var d = mesh.Vertices.Add(bottom + new Vector3d(-half, half, 0));
            var tip = mesh.Vertices.Add(apex);
            mesh.Faces.AddFace(a, b, tip);
            mesh.Faces.AddFace(b, c, tip);
            mesh.Faces.AddFace(c, d, tip);
            mesh.Faces.AddFace(d, a, tip);
            mesh.Faces.AddFace(d, c, b, a);
            mesh.Normals.ComputeNormals();
            return Brep.CreateFromMesh(mesh, true);
        }

        /// <summary>Triangular prism whose top ridge runs along the X or Y axis through <paramref name="ridge"/>.</summary>
        private static Brep Wedge(Point3d ridge, int axis, double halfLength, double halfWidth, double height)
        {
            var along = Axes[axis];
            var across = Axes[1 - axis];
            var drop = Vector3d.ZAxis * height;
            var vertices = new[]
            {
                ridge - along * halfLength,
                ridge - along * halfLength + across * halfWidth - drop,
                ridge - along * halfLength - across * halfWidth - drop,
                ridge + along * halfLength,
                ridge + along * halfLength + across * halfWidth - drop,
                ridge + along * halfLength - across * halfWidth - drop,
            };

            var mesh = new Mesh();
            foreach (var vertex in vertices) mesh.Vertices.Add(vertex);
            mesh.Faces.AddFace(0, 1, 2);
            mesh.Faces.AddFace(3, 5, 4);
            mesh.Faces.AddFace(0, 3, 4, 1);
            mesh.Faces.AddFace(1, 4, 5, 2);
            mesh.Faces.AddFace(2, 5, 3, 0);
            mesh.Normals.ComputeNormals();
            return Brep.CreateFromMesh(mesh, true);
        }

        private static Brep Rod(Point3d centre, Vector3d axis, double radius, double length)
        {
            var plane = new Plane(centre - axis * (length * 0.5), axis);
            return new Cylinder(new Circle(plane, radius), length).ToBrep(true, true);
        }

        private static Brep Ball(Point3d centre, double radius)
        {
            return new Sphere(centre, radius).ToBrep();
        }

        private sealed class SupportGlyph
        {
            public List<Brep> Breps { get; } = new List<Brep>();
            public List<Color> Colors { get; } = new List<Color>();
            public List<Line> Rails { get; } = new List<Line>();
            public string Description { get; set; } = string.Empty;

            public void Add(Brep brep, Color color)
            {
                if (brep != null)
                {
                    Breps.Add(brep);
                    Colors.Add(color);
                }
            }
        }
    }
}
