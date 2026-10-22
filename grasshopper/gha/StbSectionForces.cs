using System;
using System.Collections.Generic;

namespace StbGrasshopper
{
    internal static class StbSectionForces
    {
        private const double MergeTolerance = 1e-9;

        internal static SectionForceValues Evaluate(
            ElementForce force,
            double length,
            IReadOnlyList<ElementLoadSegment> segments,
            double t)
        {
            t = Math.Max(0.0, Math.Min(1.0, t));
            var x = length * t;
            var wx = Integrate(segments, t, length, 0);
            var wy = Integrate(segments, t, length, 1);
            var wz = Integrate(segments, t, length, 2);

            return new SectionForceValues(
                force.Ni - wx.Resultant,
                force.Qyi + wy.Resultant,
                force.Qzi + wz.Resultant,
                force.Mxi,
                force.Myi + force.Qzi * x + wz.FirstMoment,
                force.Mzi - force.Qyi * x - wy.FirstMoment);
        }

        internal static List<double> Breakpoints(IReadOnlyList<ElementLoadSegment> segments)
        {
            var values = new List<double>();
            if (segments != null)
            {
                foreach (var segment in segments)
                {
                    if (segment.T0 > MergeTolerance && segment.T0 < 1.0 - MergeTolerance)
                    {
                        values.Add(segment.T0);
                    }
                    if (segment.T1 > MergeTolerance && segment.T1 < 1.0 - MergeTolerance)
                    {
                        values.Add(segment.T1);
                    }
                }
            }
            return SortAndMerge(values);
        }

        internal static List<double> Stations(int divisions, IReadOnlyList<ElementLoadSegment> segments)
        {
            divisions = Math.Max(1, divisions);
            var values = Breakpoints(segments);
            for (var i = 0; i <= divisions; i++)
            {
                values.Add((double)i / divisions);
            }
            return SortAndMerge(values);
        }

        private static LoadIntegrals Integrate(
            IReadOnlyList<ElementLoadSegment> segments,
            double t,
            double length,
            int component)
        {
            var resultant = 0.0;
            var firstMoment = 0.0;
            if (segments == null)
            {
                return new LoadIntegrals(resultant, firstMoment);
            }

            foreach (var segment in segments)
            {
                var a = Math.Max(0.0, segment.T0);
                var b = Math.Min(t, segment.T1);
                var span = segment.T1 - segment.T0;
                if (b <= a || span <= 0.0)
                {
                    continue;
                }

                GetLoads(segment, component, out var wi, out var wj);
                var slope = (wj - wi) / span;
                var intercept = wi - slope * segment.T0;
                var integralW = intercept * (b - a) + 0.5 * slope * (b * b - a * a);
                var integralUW = 0.5 * intercept * (b * b - a * a)
                    + slope * (b * b * b - a * a * a) / 3.0;
                resultant += length * integralW;
                firstMoment += length * length * (t * integralW - integralUW);
            }

            return new LoadIntegrals(resultant, firstMoment);
        }

        private static void GetLoads(
            ElementLoadSegment segment,
            int component,
            out double wi,
            out double wj)
        {
            switch (component)
            {
                case 0:
                    wi = segment.WXi;
                    wj = segment.WXj;
                    break;
                case 1:
                    wi = segment.WYi;
                    wj = segment.WYj;
                    break;
                default:
                    wi = segment.WZi;
                    wj = segment.WZj;
                    break;
            }
        }

        private static List<double> SortAndMerge(List<double> values)
        {
            values.Sort();
            var merged = new List<double>();
            foreach (var value in values)
            {
                if (merged.Count == 0 || value - merged[merged.Count - 1] > MergeTolerance)
                {
                    merged.Add(value);
                }
            }
            return merged;
        }

        private readonly struct LoadIntegrals
        {
            internal LoadIntegrals(double resultant, double firstMoment)
            {
                Resultant = resultant;
                FirstMoment = firstMoment;
            }

            internal double Resultant { get; }
            internal double FirstMoment { get; }
        }
    }

    internal readonly struct SectionForceValues
    {
        internal SectionForceValues(double n, double qy, double qz, double mx, double my, double mz)
        {
            N = n;
            Qy = qy;
            Qz = qz;
            Mx = mx;
            My = my;
            Mz = mz;
        }

        internal double N { get; }
        internal double Qy { get; }
        internal double Qz { get; }
        internal double Mx { get; }
        internal double My { get; }
        internal double Mz { get; }
    }
}
