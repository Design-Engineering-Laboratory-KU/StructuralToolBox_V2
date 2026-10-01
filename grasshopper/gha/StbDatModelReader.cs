using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using Rhino.Geometry;

namespace StbGrasshopper
{
    internal static class StbDatModelReader
    {
        public static StbModelModel Read(string datPath)
        {
            if (string.IsNullOrWhiteSpace(datPath) || !File.Exists(datPath))
            {
                throw new FileNotFoundException("STB DAT file was not found.", datPath);
            }

            var materials = new Dictionary<int, StbMaterialModel>();
            var sections = new Dictionary<int, StbSectionModel>();
            var nodes = new Dictionary<int, Point3d>();
            var elementRecords = new List<ElementRecord>();
            var supportRecords = new List<SupportRecord>();
            var pointLoadRecords = new List<PointLoadRecord>();
            var lineLoadRecords = new List<LineLoadRecord>();
            var areaLoadRecords = new List<AreaLoadRecord>();
            var jointRecords = new Dictionary<int, double?[]>();
            var typedLoads = new List<StbLoadModel>();
            var untyped = new SortedDictionary<string, int>();

            foreach (var rawLine in File.ReadLines(datPath))
            {
                var line = rawLine.Trim();
                if (line.Length == 0 || line.StartsWith("#", StringComparison.Ordinal))
                {
                    continue;
                }

                var parts = line.Split(',');
                var record = parts[0].Trim().ToUpperInvariant();
                switch (record)
                {
                    case "MATE":
                        materials[Integer(parts, 1)] = new StbMaterialModel
                        {
                            Name = Text(parts, 2, "MAT"),
                            E = Number(parts, 3),
                            G = Number(parts, 4),
                            Gamma = Number(parts, 5),
                            Alpha = Number(parts, 6),
                            Fy = Number(parts, 7),
                        };
                        break;
                    case "SECT":
                        var section = new StbSectionModel
                        {
                            Name = Text(parts, 2, "SEC"),
                            Type = Integer(parts, 4),
                            Material = materials[Integer(parts, 3)],
                        };
                        for (var i = 5; i < parts.Length; i++)
                        {
                            section.Dimensions.Add(Number(parts, i));
                        }

                        sections[Integer(parts, 1)] = section;
                        break;
                    case "NODE":
                        nodes[Integer(parts, 1)] = new Point3d(
                            Number(parts, 2),
                            Number(parts, 3),
                            Number(parts, 4, true));
                        break;
                    case "ELEM":
                        elementRecords.Add(new ElementRecord(
                            Integer(parts, 1),
                            Integer(parts, 2),
                            Integer(parts, 3),
                            Integer(parts, 4),
                            Number(parts, 5, true, 0.0)));
                        break;
                    case "CONS":
                        supportRecords.Add(new SupportRecord(
                            Integer(parts, 1),
                            Integer(parts, 2) != 0,
                            Integer(parts, 3) != 0,
                            Integer(parts, 4) != 0,
                            Integer(parts, 5) != 0,
                            Integer(parts, 6) != 0,
                            Integer(parts, 7) != 0));
                        break;
                    case "PLOD":
                        pointLoadRecords.Add(new PointLoadRecord(
                            Integer(parts, 1),
                            Integer(parts, 2),
                            new Vector3d(Number(parts, 3), Number(parts, 4), Number(parts, 5)),
                            new Vector3d(Number(parts, 6), Number(parts, 7), Number(parts, 8))));
                        break;
                    case "ELOD":
                        lineLoadRecords.Add(new LineLoadRecord(
                            Integer(parts, 1),
                            Integer(parts, 2),
                            Integer(parts, 3) != 0,
                            new Vector3d(Number(parts, 4), Number(parts, 5), Number(parts, 6)),
                            new Vector3d(Number(parts, 7), Number(parts, 8), Number(parts, 9))));
                        break;
                    case "ALOD":
                        var boundaryIds = new List<int>();
                        for (var i = 5; i < parts.Length && boundaryIds.Count < 4; i++)
                        {
                            if (!string.IsNullOrWhiteSpace(parts[i])) boundaryIds.Add(Integer(parts, i));
                        }

                        areaLoadRecords.Add(new AreaLoadRecord(
                            Integer(parts, 1),
                            new Vector3d(Number(parts, 2), Number(parts, 3), Number(parts, 4)),
                            boundaryIds));
                        break;
                    case "GLOD":
                        typedLoads.Add(new StbLoadModel
                        {
                            Kind = StbLoadKind.Gravity,
                            LoadCase = Integer(parts, 1),
                            Acceleration = new Vector3d(Number(parts, 2), Number(parts, 3), Number(parts, 4)),
                        });
                        break;
                    case "EJNT":
                        var springs = new double?[4];
                        for (var i = 0; i < 4; i++)
                        {
                            springs[i] = OptionalNumber(parts, i + 2);
                        }

                        jointRecords[Integer(parts, 1)] = springs;
                        break;
                    case "LCMB":
                        var combination = new StbLoadModel
                        {
                            Kind = StbLoadKind.Combination,
                            LoadCase = Integer(parts, 1),
                            CombinationName = Text(parts, 2, string.Empty),
                        };
                        for (var i = 3; i + 1 < parts.Length; i += 2)
                        {
                            if (string.IsNullOrWhiteSpace(parts[i]) || string.IsNullOrWhiteSpace(parts[i + 1])) continue;
                            combination.CombinationFactors.Add(Number(parts, i));
                            combination.CombinationCases.Add(Integer(parts, i + 1));
                        }

                        typedLoads.Add(combination);
                        break;
                    default:
                        untyped[record] = untyped.TryGetValue(record, out var count) ? count + 1 : 1;
                        break;
                }
            }

            var model = new StbModelModel
            {
                DatPath = Path.GetFullPath(datPath),
                DatText = File.ReadAllText(datPath),
            };
            foreach (var pair in untyped) model.UntypedRecordCounts[pair.Key] = pair.Value;

            var elementsById = new Dictionary<int, StbElementModel>();
            foreach (var record in elementRecords)
            {
                if (!nodes.TryGetValue(record.NodeI, out var start)
                    || !nodes.TryGetValue(record.NodeJ, out var end)
                    || !sections.TryGetValue(record.SectionId, out var section))
                {
                    continue;
                }

                var element = new StbElementModel
                {
                    Name = "ELEM " + record.ElementId.ToString(CultureInfo.InvariantCulture),
                    Line = new Line(start, end),
                    Section = section,
                    Beta = record.Beta,
                };
                if (jointRecords.TryGetValue(record.ElementId, out var springs))
                {
                    element.JointRyi = springs[0];
                    element.JointRzi = springs[1];
                    element.JointRyj = springs[2];
                    element.JointRzj = springs[3];
                }

                model.Elements.Add(element);
                elementsById[record.ElementId] = element;
            }

            foreach (var record in supportRecords)
            {
                if (nodes.TryGetValue(record.NodeId, out var point))
                {
                    model.Supports.Add(new StbSupportModel
                    {
                        Point = point,
                        Tx = record.Tx,
                        Ty = record.Ty,
                        Tz = record.Tz,
                        Rx = record.Rx,
                        Ry = record.Ry,
                        Rz = record.Rz,
                    });
                }
            }

            foreach (var record in pointLoadRecords)
            {
                if (nodes.TryGetValue(record.NodeId, out var point))
                {
                    model.Loads.Add(new StbLoadModel
                    {
                        Kind = StbLoadKind.Point,
                        Point = point,
                        LoadCase = record.LoadCase,
                        Force = record.Force,
                        Moment = record.Moment,
                    });
                }
            }

            foreach (var record in lineLoadRecords)
            {
                if (elementsById.TryGetValue(record.ElementId, out var element))
                {
                    model.Loads.Add(new StbLoadModel
                    {
                        Kind = StbLoadKind.Line,
                        ElementLine = element.Line,
                        LoadCase = record.LoadCase,
                        IsGlobal = record.IsGlobal,
                        LoadAtI = record.LoadAtI,
                        LoadAtJ = record.LoadAtJ,
                    });
                }
            }

            foreach (var record in areaLoadRecords)
            {
                var load = new StbLoadModel
                {
                    Kind = StbLoadKind.Area,
                    LoadCase = record.LoadCase,
                    Pressure = record.Pressure,
                };
                foreach (var elementId in record.ElementIds)
                {
                    if (elementsById.TryGetValue(elementId, out var element))
                    {
                        load.BoundaryLines.Add(element.Line);
                    }
                }

                if (load.BoundaryLines.Count > 0)
                {
                    model.Loads.Add(load);
                }
            }

            model.Loads.AddRange(typedLoads);
            return model;
        }

        private static double? OptionalNumber(string[] parts, int index)
        {
            if (index >= parts.Length || string.IsNullOrWhiteSpace(parts[index]))
            {
                return null;
            }

            return double.Parse(parts[index].Trim(), CultureInfo.InvariantCulture);
        }

        private static string Text(string[] parts, int index, string fallback)
        {
            return index < parts.Length && !string.IsNullOrWhiteSpace(parts[index])
                ? parts[index].Trim()
                : fallback;
        }

        private static int Integer(string[] parts, int index)
        {
            return int.Parse(parts[index].Trim(), CultureInfo.InvariantCulture);
        }

        private static double Number(string[] parts, int index, bool trimMarker = false, double fallback = double.NaN)
        {
            if (index >= parts.Length || string.IsNullOrWhiteSpace(parts[index]))
            {
                if (!double.IsNaN(fallback)) return fallback;
                throw new FormatException("Missing numeric field at column " + index + ".");
            }

            var value = parts[index].Trim();
            if (trimMarker) value = value.TrimEnd('*').Trim();
            return double.Parse(value, CultureInfo.InvariantCulture);
        }

        private sealed class ElementRecord
        {
            public ElementRecord(int elementId, int nodeI, int nodeJ, int sectionId, double beta)
            {
                ElementId = elementId;
                NodeI = nodeI;
                NodeJ = nodeJ;
                SectionId = sectionId;
                Beta = beta;
            }

            public int ElementId { get; }
            public int NodeI { get; }
            public int NodeJ { get; }
            public int SectionId { get; }
            public double Beta { get; }
        }

        private sealed class SupportRecord
        {
            public SupportRecord(int nodeId, bool tx, bool ty, bool tz, bool rx, bool ry, bool rz)
            {
                NodeId = nodeId;
                Tx = tx;
                Ty = ty;
                Tz = tz;
                Rx = rx;
                Ry = ry;
                Rz = rz;
            }

            public int NodeId { get; }
            public bool Tx { get; }
            public bool Ty { get; }
            public bool Tz { get; }
            public bool Rx { get; }
            public bool Ry { get; }
            public bool Rz { get; }
        }

        private sealed class PointLoadRecord
        {
            public PointLoadRecord(int nodeId, int loadCase, Vector3d force, Vector3d moment)
            {
                NodeId = nodeId;
                LoadCase = loadCase;
                Force = force;
                Moment = moment;
            }

            public int NodeId { get; }
            public int LoadCase { get; }
            public Vector3d Force { get; }
            public Vector3d Moment { get; }
        }

        private sealed class LineLoadRecord
        {
            public LineLoadRecord(int elementId, int loadCase, bool isGlobal, Vector3d loadAtI, Vector3d loadAtJ)
            {
                ElementId = elementId;
                LoadCase = loadCase;
                IsGlobal = isGlobal;
                LoadAtI = loadAtI;
                LoadAtJ = loadAtJ;
            }

            public int ElementId { get; }
            public int LoadCase { get; }
            public bool IsGlobal { get; }
            public Vector3d LoadAtI { get; }
            public Vector3d LoadAtJ { get; }
        }

        private sealed class AreaLoadRecord
        {
            public AreaLoadRecord(int loadCase, Vector3d pressure, List<int> elementIds)
            {
                LoadCase = loadCase;
                Pressure = pressure;
                ElementIds = elementIds;
            }

            public int LoadCase { get; }
            public Vector3d Pressure { get; }
            public List<int> ElementIds { get; }
        }
    }
}
