using System;
using System.Collections.Generic;
using Rhino.Geometry;

namespace StbGrasshopper
{
    /// <summary>
    /// Low-poly closed member solid: a section profile swept straight from the
    /// start node to the end node. The profile lies in the member y-z plane with
    /// B along local y and H along local z, as in the web viewer and the solver
    /// (Iy = B*H^3/12 is the strong axis).
    /// </summary>
    internal sealed class StbSectionSolid
    {
        private const double MillimetersToMeters = 0.001;

        // Profile corners in meters: X = local y, Y = local z.
        private readonly Point2d[] _points;

        // Outer loops run counter-clockwise seen from the end node, holes clockwise,
        // so every side quad faces away from the material.
        private readonly List<ProfileLoop> _loops;

        // Cap triangles / quads, counter-clockwise seen from the end node.
        private readonly List<int[]> _capFaces;

        private StbSectionSolid(Point2d[] points, List<ProfileLoop> loops, List<int[]> capFaces, bool isSimplified)
        {
            _points = points;
            _loops = loops;
            _capFaces = capFaces;
            IsSimplified = isSimplified;
        }

        /// <summary>True when a hollow section is too thick-walled for its hole and is drawn solid.</summary>
        public bool IsSimplified { get; }

        /// <summary>Profile for a SECT type and its dimensions in mm, or null when they are invalid.</summary>
        public static StbSectionSolid Create(int type, IReadOnlyList<double> dims, int segments)
        {
            if (dims == null)
            {
                return null;
            }

            var d = new double[dims.Count];
            for (var i = 0; i < d.Length; i++)
            {
                var value = dims[i] * MillimetersToMeters;
                if (!(value > 0.0) || double.IsInfinity(value))
                {
                    return null;
                }

                d[i] = value;
            }

            switch (type)
            {
                case 0:
                    return d.Length >= 2 ? Rectangle(d[0], d[1], false) : null;
                case 1:
                    return d.Length >= 1 ? Circle(d[0] * 0.5, segments, false) : null;
                case 2:
                    if (d.Length < 4) return null;
                    return d[2] < d[1] && 2.0 * d[3] < d[0]
                        ? ISection(d[0], d[1], d[2], d[3])
                        : Rectangle(d[1], d[0], true);
                case 3:
                    if (d.Length < 2) return null;
                    return 2.0 * d[1] < d[0]
                        ? Tube(d[0] * 0.5, d[0] * 0.5 - d[1], segments)
                        : Circle(d[0] * 0.5, segments, true);
                case 4:
                    if (d.Length < 4) return null;
                    return 2.0 * d[2] < d[1] && 2.0 * d[3] < d[0]
                        ? HollowRectangle(d[1], d[0], d[2], d[3])
                        : Rectangle(d[1], d[0], true);
                default:
                    return null;
            }
        }

        /// <summary>
        /// Appends the solid of a member from <paramref name="origin"/> along
        /// <paramref name="axis"/> (full member length) to the vertex and face lists.
        /// Corners are not welded between faces so flat faces shade flat; the
        /// solid is still closed because coincident vertices share mesh topology.
        /// </summary>
        public void Append(
            Point3d origin,
            Vector3d axis,
            Vector3d y,
            Vector3d z,
            List<Point3f> vertices,
            List<MeshFace> faces,
            List<Line> edges)
        {
            var count = _points.Length;
            var start = new Point3d[count];
            var end = new Point3d[count];
            for (var i = 0; i < count; i++)
            {
                start[i] = origin + y * _points[i].X + z * _points[i].Y;
                end[i] = start[i] + axis;
            }

            var s0 = AddVertices(vertices, start);
            var e0 = AddVertices(vertices, end);
            foreach (var cap in _capFaces)
            {
                if (cap.Length == 3)
                {
                    faces.Add(new MeshFace(e0 + cap[0], e0 + cap[1], e0 + cap[2]));
                    faces.Add(new MeshFace(s0 + cap[2], s0 + cap[1], s0 + cap[0]));
                }
                else
                {
                    faces.Add(new MeshFace(e0 + cap[0], e0 + cap[1], e0 + cap[2], e0 + cap[3]));
                    faces.Add(new MeshFace(s0 + cap[3], s0 + cap[2], s0 + cap[1], s0 + cap[0]));
                }
            }

            foreach (var loop in _loops)
            {
                var indices = loop.Indices;
                var n = indices.Length;
                if (loop.Smooth)
                {
                    var ls = vertices.Count;
                    for (var k = 0; k < n; k++) vertices.Add(ToFloat(start[indices[k]]));
                    var le = vertices.Count;
                    for (var k = 0; k < n; k++) vertices.Add(ToFloat(end[indices[k]]));
                    for (var k = 0; k < n; k++)
                    {
                        var next = (k + 1) % n;
                        faces.Add(new MeshFace(ls + k, ls + next, le + next, le + k));
                    }
                }
                else
                {
                    for (var k = 0; k < n; k++)
                    {
                        var a = indices[k];
                        var b = indices[(k + 1) % n];
                        var v = vertices.Count;
                        vertices.Add(ToFloat(start[a]));
                        vertices.Add(ToFloat(start[b]));
                        vertices.Add(ToFloat(end[b]));
                        vertices.Add(ToFloat(end[a]));
                        faces.Add(new MeshFace(v, v + 1, v + 2, v + 3));
                    }
                }

                if (edges == null)
                {
                    continue;
                }

                for (var k = 0; k < n; k++)
                {
                    var a = indices[k];
                    var b = indices[(k + 1) % n];
                    edges.Add(new Line(start[a], start[b]));
                    edges.Add(new Line(end[a], end[b]));
                    if (!loop.Smooth)
                    {
                        edges.Add(new Line(start[a], end[a]));
                    }
                }
            }
        }

        /// <summary>Closed mesh of one member; local axes follow <see cref="StbMemberAxes"/>.</summary>
        public Mesh BuildMesh(Line line, double betaDegrees, List<Line> edges)
        {
            StbMemberAxes.Compute(line, betaDegrees, out _, out var y, out var z);
            var vertices = new List<Point3f>();
            var faces = new List<MeshFace>();
            Append(line.From, line.Direction, y, z, vertices, faces, edges);

            var mesh = new Mesh();
            mesh.Vertices.AddVertices(vertices);
            mesh.Faces.AddFaces(faces);
            mesh.Normals.ComputeNormals();
            mesh.FaceNormals.ComputeFaceNormals();
            return mesh;
        }

        private static int AddVertices(List<Point3f> vertices, Point3d[] points)
        {
            var first = vertices.Count;
            foreach (var point in points)
            {
                vertices.Add(ToFloat(point));
            }

            return first;
        }

        private static Point3f ToFloat(Point3d point)
        {
            return new Point3f((float)point.X, (float)point.Y, (float)point.Z);
        }

        private static StbSectionSolid Rectangle(double width, double height, bool isSimplified)
        {
            var points = RectanglePoints(width, height);
            return new StbSectionSolid(
                points,
                new List<ProfileLoop> { new ProfileLoop(new[] { 0, 1, 2, 3 }, false) },
                new List<int[]> { new[] { 0, 1, 2, 3 } },
                isSimplified);
        }

        private static StbSectionSolid HollowRectangle(double width, double height, double tw, double tf)
        {
            var points = new Point2d[8];
            RectanglePoints(width, height).CopyTo(points, 0);
            RectanglePoints(width - 2.0 * tw, height - 2.0 * tf).CopyTo(points, 4);
            var loops = new List<ProfileLoop>
            {
                new ProfileLoop(new[] { 0, 1, 2, 3 }, false),
                new ProfileLoop(new[] { 4, 7, 6, 5 }, false),
            };
            return new StbSectionSolid(points, loops, RingCaps(4), false);
        }

        /// <summary>
        /// Twelve-corner I outline. The caps are split into fans from the outer
        /// flange corners plus the web quad so no cap edge has a T-junction.
        /// </summary>
        private static StbSectionSolid ISection(double h, double b, double tw, double tf)
        {
            var hw = b * 0.5;
            var hh = h * 0.5;
            var a = tw * 0.5;
            var c = hh - tf;
            var points = new[]
            {
                new Point2d(-hw, -hh),
                new Point2d(hw, -hh),
                new Point2d(hw, -c),
                new Point2d(a, -c),
                new Point2d(a, c),
                new Point2d(hw, c),
                new Point2d(hw, hh),
                new Point2d(-hw, hh),
                new Point2d(-hw, c),
                new Point2d(-a, c),
                new Point2d(-a, -c),
                new Point2d(-hw, -c),
            };
            var caps = new List<int[]>
            {
                new[] { 0, 1, 2 },
                new[] { 0, 2, 3 },
                new[] { 0, 3, 10 },
                new[] { 0, 10, 11 },
                new[] { 10, 3, 4, 9 },
                new[] { 6, 7, 8 },
                new[] { 6, 8, 9 },
                new[] { 6, 9, 4 },
                new[] { 6, 4, 5 },
            };
            return new StbSectionSolid(
                points,
                new List<ProfileLoop> { new ProfileLoop(Sequence(0, 12), false) },
                caps,
                false);
        }

        private static StbSectionSolid Circle(double radius, int segments, bool isSimplified)
        {
            var caps = new List<int[]>();
            for (var i = 1; i < segments - 1; i++)
            {
                caps.Add(new[] { 0, i, i + 1 });
            }

            return new StbSectionSolid(
                CirclePoints(radius, segments),
                new List<ProfileLoop> { new ProfileLoop(Sequence(0, segments), true) },
                caps,
                isSimplified);
        }

        private static StbSectionSolid Tube(double outer, double inner, int segments)
        {
            var points = new Point2d[2 * segments];
            CirclePoints(outer, segments).CopyTo(points, 0);
            CirclePoints(inner, segments).CopyTo(points, segments);
            var hole = new int[segments];
            for (var k = 0; k < segments; k++)
            {
                hole[k] = segments + (segments - k) % segments;
            }

            var loops = new List<ProfileLoop>
            {
                new ProfileLoop(Sequence(0, segments), true),
                new ProfileLoop(hole, true),
            };
            return new StbSectionSolid(points, loops, RingCaps(segments), false);
        }

        /// <summary>Quads between an outer loop 0..n-1 and an inner loop n..2n-1 of matching corners.</summary>
        private static List<int[]> RingCaps(int n)
        {
            var caps = new List<int[]>(n);
            for (var i = 0; i < n; i++)
            {
                var next = (i + 1) % n;
                caps.Add(new[] { i, next, n + next, n + i });
            }

            return caps;
        }

        private static Point2d[] RectanglePoints(double width, double height)
        {
            var hw = width * 0.5;
            var hh = height * 0.5;
            return new[]
            {
                new Point2d(-hw, -hh),
                new Point2d(hw, -hh),
                new Point2d(hw, hh),
                new Point2d(-hw, hh),
            };
        }

        private static Point2d[] CirclePoints(double radius, int segments)
        {
            var points = new Point2d[segments];
            for (var i = 0; i < segments; i++)
            {
                var angle = 2.0 * Math.PI * i / segments;
                points[i] = new Point2d(radius * Math.Cos(angle), radius * Math.Sin(angle));
            }

            return points;
        }

        private static int[] Sequence(int first, int count)
        {
            var indices = new int[count];
            for (var i = 0; i < count; i++)
            {
                indices[i] = first + i;
            }

            return indices;
        }

        private sealed class ProfileLoop
        {
            public ProfileLoop(int[] indices, bool smooth)
            {
                Indices = indices;
                Smooth = smooth;
            }

            public int[] Indices { get; }

            // Curved loops share vertices between side quads so they shade round.
            public bool Smooth { get; }
        }
    }
}
