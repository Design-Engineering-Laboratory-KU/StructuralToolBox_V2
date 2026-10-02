using System;
using System.Collections.Generic;
using Rhino.Geometry;

namespace StbGrasshopper
{
    internal sealed class StbTributaryMemberLoad
    {
        public Line Line { get; set; }
        public Vector3d LoadAtI { get; set; }
        public Vector3d LoadAtJ { get; set; }
        public double TributaryArea { get; set; }
        public double CentroidFromI { get; set; }
        public int LoadCase { get; set; }
    }

    /// <summary>
    /// Distributes an ALOD panel pressure onto its boundary members using the
    /// same nearest-edge tributary partition as classes/ld.py ALd.SetMemberAreaLoads,
    /// then converts each tributary into the equivalent trapezoidal line load
    /// used by classes/solve.py CreateLoadMx.
    /// </summary>
    internal static class StbAreaLoadDistributor
    {
        public const int DefaultGridN = 240;
        private const double Zero = 1e-12;

        public static List<StbTributaryMemberLoad> Distribute(StbLoadModel load, double tolerance)
        {
            if (load == null || load.Kind != StbLoadKind.Area)
            {
                throw new InvalidOperationException("An STB area load is required.");
            }

            var loop = BuildBoundaryLoop(load.BoundaryLines, tolerance);
            if (loop == null)
            {
                throw new InvalidOperationException(
                    "Area-load boundary elements do not form a single closed loop.");
            }

            var verts3d = new Point3d[loop.Count];
            for (var i = 0; i < loop.Count; i++)
            {
                verts3d[i] = loop[i].V0;
            }

            var centroid = new Point3d(0.0, 0.0, 0.0);
            foreach (var vertex in verts3d)
            {
                centroid += vertex;
            }

            centroid /= loop.Count;

            if (Plane.FitPlaneToPoints(verts3d, out var plane) != PlaneFitResult.Success)
            {
                throw new InvalidOperationException("Area-load panel does not define a plane.");
            }

            plane.Origin = centroid;

            var verts2d = new Point2d[loop.Count];
            for (var i = 0; i < loop.Count; i++)
            {
                var rel = verts3d[i] - plane.Origin;
                verts2d[i] = new Point2d(rel * plane.XAxis, rel * plane.YAxis);
            }

            var polyArea = PolygonArea(verts2d);
            if (polyArea < Zero)
            {
                throw new InvalidOperationException("Area-load panel has (near) zero area.");
            }

            TributaryByEdge(
                verts2d,
                DefaultGridN,
                out var areas,
                out var centroidsFromV0);

            var total = 0.0;
            foreach (var area in areas)
            {
                total += area;
            }

            if (total > Zero)
            {
                var scale = polyArea / total;
                for (var i = 0; i < areas.Length; i++)
                {
                    areas[i] *= scale;
                }
            }

            var results = new List<StbTributaryMemberLoad>(loop.Count);
            for (var i = 0; i < loop.Count; i++)
            {
                var original = loop[i].Original;
                var length = original.Length;
                if (length <= Zero)
                {
                    continue;
                }

                var dcFromV0 = centroidsFromV0[i];
                var dcFromI = original.From.DistanceTo(loop[i].V0) <= tolerance
                    ? dcFromV0
                    : length - dcFromV0;

                var s = 2.0 * areas[i] / length;
                var widthI = s * (2.0 - 3.0 * dcFromI / length);
                var widthJ = s * (3.0 * dcFromI / length - 1.0);

                results.Add(new StbTributaryMemberLoad
                {
                    Line = original,
                    LoadAtI = widthI * load.Pressure,
                    LoadAtJ = widthJ * load.Pressure,
                    TributaryArea = areas[i],
                    CentroidFromI = dcFromI,
                    LoadCase = load.LoadCase,
                });
            }

            return results;
        }

        private sealed class LoopEdge
        {
            public Line Original;
            public Point3d V0;
            public Point3d V1;
        }

        /// <summary>Panel corners in loop order, or null when the boundary is not one closed loop.</summary>
        public static List<Point3d> BoundaryPolygon(IReadOnlyList<Line> lines, double tolerance)
        {
            var loop = BuildBoundaryLoop(lines, tolerance);
            if (loop == null)
            {
                return null;
            }

            var corners = new List<Point3d>(loop.Count);
            foreach (var edge in loop)
            {
                corners.Add(edge.V0);
            }

            return corners;
        }

        private static List<LoopEdge> BuildBoundaryLoop(IReadOnlyList<Line> lines, double tolerance)
        {
            if (lines == null || lines.Count < 3 || lines.Count > 4)
            {
                return null;
            }

            var remaining = new List<Line>(lines);
            var first = remaining[0];
            remaining.RemoveAt(0);
            var loop = new List<LoopEdge>
            {
                new LoopEdge { Original = first, V0 = first.From, V1 = first.To },
            };
            var start = first.From;
            var current = first.To;

            while (remaining.Count > 0)
            {
                var nextIndex = -1;
                LoopEdge next = null;
                for (var i = 0; i < remaining.Count; i++)
                {
                    if (remaining[i].From.DistanceTo(current) <= tolerance)
                    {
                        nextIndex = i;
                        next = new LoopEdge
                        {
                            Original = remaining[i],
                            V0 = remaining[i].From,
                            V1 = remaining[i].To,
                        };
                        break;
                    }

                    if (remaining[i].To.DistanceTo(current) <= tolerance)
                    {
                        nextIndex = i;
                        next = new LoopEdge
                        {
                            Original = remaining[i],
                            V0 = remaining[i].To,
                            V1 = remaining[i].From,
                        };
                        break;
                    }
                }

                if (nextIndex < 0 || next == null)
                {
                    return null;
                }

                remaining.RemoveAt(nextIndex);
                loop.Add(next);
                current = next.V1;
            }

            if (current.DistanceTo(start) > tolerance)
            {
                return null;
            }

            return loop;
        }

        private static double PolygonArea(Point2d[] pts)
        {
            var sum = 0.0;
            for (var i = 0; i < pts.Length; i++)
            {
                var j = (i + 1) % pts.Length;
                sum += pts[i].X * pts[j].Y - pts[j].X * pts[i].Y;
            }

            return 0.5 * Math.Abs(sum);
        }

        private static bool PointInPolygon(double px, double py, Point2d[] poly)
        {
            var inside = false;
            var j = poly.Length - 1;
            for (var i = 0; i < poly.Length; i++)
            {
                var xi = poly[i].X;
                var yi = poly[i].Y;
                var xj = poly[j].X;
                var yj = poly[j].Y;
                if ((yi > py) != (yj > py)
                    && px < (xj - xi) * (py - yi) / (yj - yi + 1e-300) + xi)
                {
                    inside = !inside;
                }

                j = i;
            }

            return inside;
        }

        private static void TributaryByEdge(
            Point2d[] verts,
            int gridN,
            out double[] areas,
            out double[] centroidsFromV0)
        {
            var nEdge = verts.Length;
            var minX = verts[0].X;
            var minY = verts[0].Y;
            var maxX = verts[0].X;
            var maxY = verts[0].Y;
            foreach (var vertex in verts)
            {
                minX = Math.Min(minX, vertex.X);
                minY = Math.Min(minY, vertex.Y);
                maxX = Math.Max(maxX, vertex.X);
                maxY = Math.Max(maxY, vertex.Y);
            }

            var span = Math.Max(maxX - minX, maxY - minY);
            var h = span / gridN;
            var cellArea = h * h;

            var samples = new List<Point2d>();
            for (var y = minY + 0.5 * h; y < maxY; y += h)
            {
                for (var x = minX + 0.5 * h; x < maxX; x += h)
                {
                    if (PointInPolygon(x, y, verts))
                    {
                        samples.Add(new Point2d(x, y));
                    }
                }
            }

            areas = new double[nEdge];
            centroidsFromV0 = new double[nEdge];
            var counts = new int[nEdge];
            var centroidSum = new double[nEdge];
            var lengths = new double[nEdge];

            for (var k = 0; k < nEdge; k++)
            {
                lengths[k] = verts[k].DistanceTo(verts[(k + 1) % nEdge]);
            }

            foreach (var sample in samples)
            {
                var bestEdge = 0;
                var bestDist = double.MaxValue;
                var bestTParam = 0.0;
                for (var k = 0; k < nEdge; k++)
                {
                    var a = verts[k];
                    var b = verts[(k + 1) % nEdge];
                    var abx = b.X - a.X;
                    var aby = b.Y - a.Y;
                    var lengthSquared = abx * abx + aby * aby;
                    if (lengthSquared <= Zero)
                    {
                        continue;
                    }

                    var t = ((sample.X - a.X) * abx + (sample.Y - a.Y) * aby) / lengthSquared;
                    var tc = Math.Max(0.0, Math.Min(1.0, t));
                    var dx = sample.X - (a.X + tc * abx);
                    var dy = sample.Y - (a.Y + tc * aby);
                    var dist = Math.Sqrt(dx * dx + dy * dy);
                    if (dist < bestDist)
                    {
                        bestDist = dist;
                        bestEdge = k;
                        bestTParam = t * Math.Sqrt(lengthSquared);
                    }
                }

                counts[bestEdge]++;
                centroidSum[bestEdge] += bestTParam;
            }

            for (var k = 0; k < nEdge; k++)
            {
                areas[k] = counts[k] * cellArea;
                centroidsFromV0[k] = counts[k] > 0
                    ? centroidSum[k] / counts[k]
                    : 0.5 * lengths[k];
            }
        }
    }
}
