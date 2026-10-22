using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbNodeGeometry
    {
        public int NodeId { get; set; }
        public Point3d Point { get; set; }
    }

    public sealed class StbElementGeometry
    {
        public int ElementId { get; set; }
        public int NodeI { get; set; }
        public int NodeJ { get; set; }
        public int SectionId { get; set; }
        public double Beta { get; set; }
    }

    public static class StbDatParser
    {
        public static void ReadGeometry(
            string datPath,
            out List<StbNodeGeometry> nodes,
            out List<StbElementGeometry> elements)
        {
            nodes = new List<StbNodeGeometry>();
            elements = new List<StbElementGeometry>();

            if (string.IsNullOrWhiteSpace(datPath) || !File.Exists(datPath))
            {
                return;
            }

            foreach (var rawLine in File.ReadLines(datPath))
            {
                var line = rawLine.Trim();
                if (line.Length == 0 || line.StartsWith("#", StringComparison.Ordinal))
                {
                    continue;
                }

                var parts = line.Split(',');
                if (parts.Length < 5)
                {
                    continue;
                }

                var record = parts[0].Trim();
                if (record == "NODE")
                {
                    if (TryParseNode(parts, out var node))
                    {
                        nodes.Add(node);
                    }
                }
                else if (record == "ELEM")
                {
                    if (TryParseElement(parts, out var element))
                    {
                        elements.Add(element);
                    }
                }
            }
        }

        private static bool TryParseNode(string[] parts, out StbNodeGeometry node)
        {
            node = null;
            try
            {
                var id = int.Parse(parts[1].Trim(), CultureInfo.InvariantCulture);
                var x = double.Parse(parts[2].Trim(), CultureInfo.InvariantCulture);
                var y = double.Parse(parts[3].Trim(), CultureInfo.InvariantCulture);
                var zText = parts[4].Trim().TrimEnd('*').Trim();
                var z = double.Parse(zText, CultureInfo.InvariantCulture);
                node = new StbNodeGeometry
                {
                    NodeId = id,
                    Point = new Point3d(x, y, z),
                };
                return true;
            }
            catch (FormatException)
            {
                return false;
            }
        }

        private static bool TryParseElement(string[] parts, out StbElementGeometry element)
        {
            element = null;
            try
            {
                element = new StbElementGeometry
                {
                    ElementId = int.Parse(parts[1].Trim(), CultureInfo.InvariantCulture),
                    NodeI = int.Parse(parts[2].Trim(), CultureInfo.InvariantCulture),
                    NodeJ = int.Parse(parts[3].Trim(), CultureInfo.InvariantCulture),
                    SectionId = int.Parse(parts[4].Trim(), CultureInfo.InvariantCulture),
                };
                if (parts.Length > 5
                    && double.TryParse(parts[5].Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out var beta))
                {
                    element.Beta = beta;
                }
                return true;
            }
            catch (FormatException)
            {
                return false;
            }
        }
    }
}
