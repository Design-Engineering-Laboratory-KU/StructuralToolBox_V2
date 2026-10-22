using System;
using System.Collections.Generic;
using Rhino.Geometry;

namespace StbGrasshopper
{
    internal readonly struct StbLineLoadSegment
    {
        public StbLineLoadSegment(double t0, double t1, Vector3d wi, Vector3d wj)
        {
            T0 = t0;
            T1 = t1;
            Wi = wi;
            Wj = wj;
        }

        public double T0 { get; }
        public double T1 { get; }
        public Vector3d Wi { get; }
        public Vector3d Wj { get; }
    }

    internal sealed class StbLineLoadShapeInput
    {
        public StbLineLoadShapeInput(
            string name,
            string nickName,
            string description,
            bool isVector,
            double numberDefault,
            Vector3d vectorDefault)
        {
            Name = name;
            NickName = nickName;
            Description = description;
            IsVector = isVector;
            NumberDefault = numberDefault;
            VectorDefault = vectorDefault;
        }

        public string Name { get; }
        public string NickName { get; }
        public string Description { get; }
        public bool IsVector { get; }
        public double NumberDefault { get; }
        public Vector3d VectorDefault { get; }
    }

    internal static class StbLineLoadShapes
    {
        private const double LengthTol = 1e-9;

        private static readonly string[] ModeNames = { "Linear", "Partial", "Triangle", "Trapezoid" };

        public static int ModeCount => ModeNames.Length;

        public static string ModeName(int mode)
        {
            if (mode < 0 || mode >= ModeNames.Length)
            {
                throw new ArgumentOutOfRangeException(nameof(mode));
            }

            return ModeNames[mode];
        }

        public static IReadOnlyList<StbLineLoadShapeInput> ExtraInputs(int mode)
        {
            switch (mode)
            {
                case 0:
                    return new[]
                    {
                        Vector("Load i", "Wi", "Distributed load at the element i-end in kN/m.", Vector3d.Zero),
                        Vector("Load j", "Wj", "Distributed load at the element j-end in kN/m.", Vector3d.Zero),
                    };
                case 1:
                    return new[]
                    {
                        Number("T0", "T0", "Start of the loaded segment (0 = i-end, 1 = j-end).", 0.2),
                        Number("T1", "T1", "End of the loaded segment (0 = i-end, 1 = j-end).", 0.4),
                        Vector("Load i", "Wi", "Distributed load at T0 in kN/m.", Vector3d.Zero),
                        Vector("Load j", "Wj", "Distributed load at T1 in kN/m.", Vector3d.Zero),
                    };
                case 2:
                    return new[]
                    {
                        Number("T0", "T0", "Start of the triangle base (0 = i-end, 1 = j-end).", 0.0),
                        Number("Tp", "Tp", "Peak location along the member (0 = i-end, 1 = j-end).", 0.5),
                        Number("T1", "T1", "End of the triangle base (0 = i-end, 1 = j-end).", 1.0),
                        Vector("W", "W", "Peak distributed load in kN/m.", Vector3d.Zero),
                    };
                case 3:
                    return new[]
                    {
                        Number("T0", "T0", "Start of the trapezoid (0 = i-end, 1 = j-end).", 0.0),
                        Number("T1", "T1", "End of the rising edge.", 0.25),
                        Number("T2", "T2", "End of the flat top.", 0.75),
                        Number("T3", "T3", "End of the trapezoid (0 = i-end, 1 = j-end).", 1.0),
                        Vector("W", "W", "Plateau distributed load in kN/m.", Vector3d.Zero),
                    };
                default:
                    throw new ArgumentOutOfRangeException(nameof(mode));
            }
        }

        public static List<StbLineLoadSegment> BuildSegments(
            int mode,
            IReadOnlyList<double> numbers,
            IReadOnlyList<Vector3d> vectors)
        {
            if (numbers == null)
            {
                throw new ArgumentNullException(nameof(numbers));
            }

            if (vectors == null)
            {
                throw new ArgumentNullException(nameof(vectors));
            }

            List<StbLineLoadSegment> raw;
            switch (mode)
            {
                case 0:
                    ExpectCount(numbers, 0, vectors, 2, mode);
                    raw = new List<StbLineLoadSegment> { new StbLineLoadSegment(0.0, 1.0, vectors[0], vectors[1]) };
                    break;
                case 1:
                    ExpectCount(numbers, 2, vectors, 2, mode);
                    ValidateParameters(numbers[0], numbers[1], mode);
                    raw = new List<StbLineLoadSegment>
                    {
                        new StbLineLoadSegment(numbers[0], numbers[1], vectors[0], vectors[1]),
                    };
                    break;
                case 2:
                    ExpectCount(numbers, 3, vectors, 1, mode);
                    ValidateParameters(numbers[0], numbers[1], numbers[2], mode);
                    raw = new List<StbLineLoadSegment>
                    {
                        new StbLineLoadSegment(numbers[0], numbers[1], Vector3d.Zero, vectors[0]),
                        new StbLineLoadSegment(numbers[1], numbers[2], vectors[0], Vector3d.Zero),
                    };
                    break;
                case 3:
                    ExpectCount(numbers, 4, vectors, 1, mode);
                    ValidateParameters(numbers[0], numbers[1], numbers[2], numbers[3], mode);
                    raw = new List<StbLineLoadSegment>
                    {
                        new StbLineLoadSegment(numbers[0], numbers[1], Vector3d.Zero, vectors[0]),
                        new StbLineLoadSegment(numbers[1], numbers[2], vectors[0], vectors[0]),
                        new StbLineLoadSegment(numbers[2], numbers[3], vectors[0], Vector3d.Zero),
                    };
                    break;
                default:
                    throw new ArgumentOutOfRangeException(nameof(mode));
            }

            return DropZeroLength(raw);
        }

        private static StbLineLoadShapeInput Number(string name, string nickName, string description, double value)
        {
            return new StbLineLoadShapeInput(name, nickName, description, false, value, Vector3d.Zero);
        }

        private static StbLineLoadShapeInput Vector(string name, string nickName, string description, Vector3d value)
        {
            return new StbLineLoadShapeInput(name, nickName, description, true, 0.0, value);
        }

        private static void ExpectCount(
            IReadOnlyList<double> numbers,
            int numberCount,
            IReadOnlyList<Vector3d> vectors,
            int vectorCount,
            int mode)
        {
            if (numbers.Count != numberCount || vectors.Count != vectorCount)
            {
                throw new InvalidOperationException(
                    ModeName(mode) + " line load expects " + numberCount + " scalar and " + vectorCount
                    + " vector parameters.");
            }
        }

        private static void ValidateParameters(double t0, double t1, int mode)
        {
            ValidateParameters(new[] { t0, t1 }, mode);
        }

        private static void ValidateParameters(double t0, double tp, double t1, int mode)
        {
            ValidateParameters(new[] { t0, tp, t1 }, mode);
        }

        private static void ValidateParameters(double t0, double t1, double t2, double t3, int mode)
        {
            ValidateParameters(new[] { t0, t1, t2, t3 }, mode);
        }

        private static void ValidateParameters(IReadOnlyList<double> values, int mode)
        {
            for (var i = 0; i < values.Count; i++)
            {
                if (values[i] < 0.0 || values[i] > 1.0)
                {
                    throw new InvalidOperationException(
                        ModeName(mode) + " line load parameter at index " + i + " must satisfy 0 <= t <= 1.");
                }
            }

            for (var i = 0; i + 1 < values.Count; i++)
            {
                if (values[i] > values[i + 1])
                {
                    throw new InvalidOperationException(
                        ModeName(mode) + " line load parameters must be non-decreasing along the member.");
                }
            }
        }

        private static List<StbLineLoadSegment> DropZeroLength(IReadOnlyList<StbLineLoadSegment> segments)
        {
            var kept = new List<StbLineLoadSegment>();
            foreach (var segment in segments)
            {
                if (Math.Abs(segment.T1 - segment.T0) > LengthTol)
                {
                    kept.Add(segment);
                }
            }

            if (kept.Count == 0)
            {
                throw new InvalidOperationException("Line load has no non-zero segments after validation.");
            }

            return kept;
        }
    }
}
