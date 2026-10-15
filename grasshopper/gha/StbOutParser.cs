using System;
using System.Globalization;
using System.IO;

namespace StbGrasshopper
{
    public static class StbOutParser
    {
        public static StbParsedResults ParseFile(string path, int? loadCase = null)
        {
            var results = new StbParsedResults();

            foreach (var rawLine in File.ReadLines(path))
            {
                var line = rawLine.Trim();
                if (line.Length == 0 || line.StartsWith("#", StringComparison.Ordinal))
                {
                    continue;
                }

                var parts = line.Split(',');
                for (var i = 0; i < parts.Length; i++)
                {
                    parts[i] = parts[i].Trim();
                }

                if (parts[0] == "SPRP" && parts.Length >= 10)
                {
                    results.Sections.Add(new StbSectionProperties
                    {
                        SectionId = ParseInt(parts[1]),
                        Area = ParseDouble(parts[2]),
                        Wy = ParseDouble(parts[8]),
                        Wz = ParseDouble(parts[9]),
                    });
                }
                else if (parts[0] == "NDSP" && parts.Length >= 9)
                {
                    var lc = ParseInt(parts[1]);
                    if (loadCase.HasValue && lc != loadCase.Value)
                    {
                        continue;
                    }

                    results.Displacements.Add(new NodalDisplacement
                    {
                        LoadCase = lc,
                        NodeId = ParseInt(parts[2]),
                        X = ParseDouble(parts[3]),
                        Y = ParseDouble(parts[4]),
                        Z = ParseDouble(parts[5]),
                        ThetaX = ParseDouble(parts[6]),
                        ThetaY = ParseDouble(parts[7]),
                        ThetaZ = ParseDouble(parts[8])
                    });
                }
                else if (parts[0] == "REAC" && parts.Length >= 9)
                {
                    var lc = ParseInt(parts[1]);
                    if (loadCase.HasValue && lc != loadCase.Value)
                    {
                        continue;
                    }

                    results.Reactions.Add(new ReactionForce
                    {
                        LoadCase = lc,
                        NodeId = ParseInt(parts[2]),
                        Tx = ParseDouble(parts[3]),
                        Ty = ParseDouble(parts[4]),
                        Tz = ParseDouble(parts[5]),
                        Rx = ParseDouble(parts[6]),
                        Ry = ParseDouble(parts[7]),
                        Rz = ParseDouble(parts[8])
                    });
                }
                else if (parts[0] == "EFRC" && parts.Length >= 17)
                {
                    var lc = ParseInt(parts[1]);
                    if (loadCase.HasValue && lc != loadCase.Value)
                    {
                        continue;
                    }

                    results.ElementForces.Add(new ElementForce
                    {
                        LoadCase = lc,
                        ElementId = ParseInt(parts[2]),
                        Ni = ParseDouble(parts[3]),
                        Qyi = ParseDouble(parts[4]),
                        Qzi = ParseDouble(parts[5]),
                        Mxi = ParseDouble(parts[6]),
                        Myi = ParseDouble(parts[7]),
                        Mzi = ParseDouble(parts[8]),
                        Nj = ParseDouble(parts[9]),
                        Qyj = ParseDouble(parts[10]),
                        Qzj = ParseDouble(parts[11]),
                        Mxj = ParseDouble(parts[12]),
                        Myj = ParseDouble(parts[13]),
                        Mzj = ParseDouble(parts[14]),
                        Myc = ParseDouble(parts[15]),
                        Mzc = ParseDouble(parts[16])
                    });
                }
                else if (parts[0] == "EWLD" && parts.Length >= 11)
                {
                    var lc = ParseInt(parts[1]);
                    if (loadCase.HasValue && lc != loadCase.Value)
                    {
                        continue;
                    }

                    results.ElementLoadSegments.Add(new ElementLoadSegment
                    {
                        LoadCase = lc,
                        ElementId = ParseInt(parts[2]),
                        T0 = ParseDouble(parts[3]),
                        T1 = ParseDouble(parts[4]),
                        WXi = ParseDouble(parts[5]),
                        WYi = ParseDouble(parts[6]),
                        WZi = ParseDouble(parts[7]),
                        WXj = ParseDouble(parts[8]),
                        WYj = ParseDouble(parts[9]),
                        WZj = ParseDouble(parts[10])
                    });
                }
            }

            return results;
        }

        private static int ParseInt(string value)
        {
            return int.Parse(value, CultureInfo.InvariantCulture);
        }

        private static double ParseDouble(string value)
        {
            return double.Parse(value, CultureInfo.InvariantCulture);
        }
    }
}
