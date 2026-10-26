using System;
using System.Collections.Generic;
using Rhino.Geometry;

namespace StbGrasshopper
{
    /// <summary>
    /// One closed panel of frame elements found on a surface.
    /// </summary>
    internal sealed class StbPanel
    {
        /// <summary>Indices into the line list given to <see cref="StbPanelFinder.Find"/>, in loop order.</summary>
        public List<int> LineIndices { get; } = new List<int>();

        public Polyline Outline { get; } = new Polyline();
    }

    /// <summary>
    /// Finds the panels (smallest closed loops) that frame elements lying on a
    /// surface divide it into. The surface is given as a probe so the search
    /// stays independent of Rhino's native mesh code.
    /// </summary>
    internal static class StbPanelFinder
    {
        /// <param name="lines">Element lines; each is a candidate panel edge.</param>
        /// <param name="probe">
        /// Surface normal at a point, or <see cref="Vector3d.Unset"/> when the
        /// point is not on the surface. Normals must be consistently oriented.
        /// </param>
        /// <param name="tolerance">Distance within which end points are the same node.</param>
        /// <param name="panels">Receives panels with 3 or 4 edges.</param>
        /// <param name="tooManyEdges">Receives panels with more than 4 edges.</param>
        public static void Find(
            IReadOnlyList<Line> lines,
            Func<Point3d, Vector3d> probe,
            double tolerance,
            List<StbPanel> panels,
            List<StbPanel> tooManyEdges)
        {
            var nodes = new List<Point3d>();
            var edgeNodes = new List<(int From, int To)>();
            var edgeLines = new List<int>();
            var seen = new HashSet<(int, int)>();

            for (var i = 0; i < lines.Count; i++)
            {
                var line = lines[i];
                if (!line.IsValid || line.Length <= tolerance)
                {
                    continue;
                }

                if (!probe(line.From).IsValid || !probe(line.To).IsValid || !probe(line.PointAt(0.5)).IsValid)
                {
                    continue;
                }

                var a = NodeOf(line.From, nodes, tolerance);
                var b = NodeOf(line.To, nodes, tolerance);
                if (a == b || !seen.Add((Math.Min(a, b), Math.Max(a, b))))
                {
                    // Zero-length after merging, or an overlapping duplicate element.
                    continue;
                }

                edgeNodes.Add((a, b));
                edgeLines.Add(i);
            }

            // Half-edge h runs Origin(h) -> Origin(h ^ 1); edge e owns 2e (a->b) and 2e+1 (b->a).
            int Origin(int h) => (h & 1) == 0 ? edgeNodes[h >> 1].From : edgeNodes[h >> 1].To;

            var outgoing = new List<int>[nodes.Count];
            for (var n = 0; n < nodes.Count; n++)
            {
                outgoing[n] = new List<int>();
            }

            for (var h = 0; h < edgeNodes.Count * 2; h++)
            {
                outgoing[Origin(h)].Add(h);
            }

            // Sort each node's outgoing edges counter-clockwise about the surface normal.
            // The normal is averaged over the edges' midpoints, so a node on a ridge or
            // valley uses the mean of the faces meeting there rather than one of them.
            var position = new int[edgeNodes.Count * 2];
            for (var n = 0; n < nodes.Count; n++)
            {
                var normal = Vector3d.Zero;
                foreach (var h in outgoing[n])
                {
                    var probed = probe(lines[edgeLines[h >> 1]].PointAt(0.5));
                    normal += probed / Math.Sqrt(probed * probed);
                }
                var x = PerpendicularTo(normal);
                var y = Vector3d.CrossProduct(normal, x);
                var origin = nodes[n];
                outgoing[n].Sort((h1, h2) =>
                    Angle(nodes[Origin(h1 ^ 1)] - origin, x, y).CompareTo(Angle(nodes[Origin(h2 ^ 1)] - origin, x, y)));
                for (var k = 0; k < outgoing[n].Count; k++)
                {
                    position[outgoing[n][k]] = k;
                }
            }

            // Walking with the next edge clockwise from the way back keeps each face on
            // the left, so bounded panels run counter-clockwise about the normal.
            int Next(int h)
            {
                var back = h ^ 1;
                var around = outgoing[Origin(back)];
                return around[(position[back] - 1 + around.Count) % around.Count];
            }

            var visited = new bool[edgeNodes.Count * 2];
            for (var start = 0; start < visited.Length; start++)
            {
                if (visited[start])
                {
                    continue;
                }

                var loop = new List<int>();
                var h = start;
                do
                {
                    visited[h] = true;
                    loop.Add(h);
                    h = Next(h);
                }
                while (h != start && loop.Count <= visited.Length);

                var panel = ToPanel(loop, nodes, edgeLines, Origin, probe);
                if (panel == null)
                {
                    continue;
                }

                if (panel.LineIndices.Count <= 4)
                {
                    panels.Add(panel);
                }
                else
                {
                    tooManyEdges.Add(panel);
                }
            }
        }

        private static StbPanel ToPanel(
            List<int> loop,
            List<Point3d> nodes,
            List<int> edgeLines,
            Func<int, int> origin,
            Func<Point3d, Vector3d> probe)
        {
            if (loop.Count < 3)
            {
                return null;
            }

            var edges = new HashSet<int>();
            var panel = new StbPanel();
            var centroid = Point3d.Origin;
            foreach (var h in loop)
            {
                if (!edges.Add(h >> 1))
                {
                    // An edge walked in both directions: a dangling element, not a panel.
                    return null;
                }

                var point = nodes[origin(h)];
                panel.LineIndices.Add(edgeLines[h >> 1]);
                panel.Outline.Add(point);
                centroid += point;
            }

            panel.Outline.Add(panel.Outline[0]);
            centroid /= loop.Count;

            // The outer boundary runs clockwise; openings in the surface have no surface inside.
            var surfaceNormal = probe(centroid);
            if (!surfaceNormal.IsValid || NewellNormal(panel.Outline) * surfaceNormal <= 0.0)
            {
                return null;
            }

            return panel;
        }

        private static int NodeOf(Point3d point, List<Point3d> nodes, double tolerance)
        {
            for (var i = 0; i < nodes.Count; i++)
            {
                if (nodes[i].DistanceTo(point) <= tolerance)
                {
                    return i;
                }
            }

            nodes.Add(point);
            return nodes.Count - 1;
        }

        private static Vector3d PerpendicularTo(Vector3d normal)
        {
            // Normalized by hand: Vector3d.Unitize needs Rhino's native library,
            // and this class stays testable outside Rhino.
            var length = Math.Sqrt(normal * normal);
            var unit = normal / length;
            var x = Vector3d.CrossProduct(unit, Math.Abs(unit.Z) < 0.9 ? Vector3d.ZAxis : Vector3d.XAxis);
            return x / Math.Sqrt(x * x);
        }

        private static double Angle(Vector3d direction, Vector3d x, Vector3d y)
        {
            return Math.Atan2(direction * y, direction * x);
        }

        private static Vector3d NewellNormal(Polyline closed)
        {
            var normal = Vector3d.Zero;
            for (var i = 0; i < closed.Count - 1; i++)
            {
                var a = closed[i];
                var b = closed[i + 1];
                normal.X += (a.Y - b.Y) * (a.Z + b.Z);
                normal.Y += (a.Z - b.Z) * (a.X + b.X);
                normal.Z += (a.X - b.X) * (a.Y + b.Y);
            }

            return normal;
        }
    }
}
