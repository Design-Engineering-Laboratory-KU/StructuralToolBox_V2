using System;
using System.Collections.Generic;
using Grasshopper.Kernel;
using Rhino.Geometry;

namespace StbGrasshopper
{
    /// <summary>
    /// Selects solved members by STb Element name. Results carry only element ids,
    /// so members are matched to the named model elements by their end points.
    /// </summary>
    internal sealed class StbElementNameFilter
    {
        private readonly List<Line> _lines;
        private readonly double _tolerance;

        private StbElementNameFilter(List<Line> lines, double tolerance)
        {
            _lines = lines;
            _tolerance = tolerance;
        }

        /// <summary>Returns null when every member should be shown.</summary>
        public static StbElementNameFilter Create(IEnumerable<string> names, IGH_DataAccess da, int modelIndex, GH_Component owner)
        {
            var wanted = new HashSet<string>(StringComparer.Ordinal);
            foreach (var name in names)
            {
                if (!string.IsNullOrWhiteSpace(name)) wanted.Add(name.Trim());
            }

            if (wanted.Count == 0)
            {
                return null;
            }

            if (!StbModelGooUtil.TryGetModel(da, modelIndex, out var model) || model.Elements.Count == 0)
            {
                owner.AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Name needs an STb Model with elements; showing every element.");
                return null;
            }

            var lines = new List<Line>();
            var found = new HashSet<string>(StringComparer.Ordinal);
            foreach (var element in model.Elements)
            {
                var name = element?.Name?.Trim();
                if (name == null || !wanted.Contains(name)) continue;
                lines.Add(element.Line);
                found.Add(name);
            }

            var missing = new List<string>();
            foreach (var name in wanted)
            {
                if (!found.Contains(name)) missing.Add(name);
            }

            if (missing.Count > 0)
            {
                owner.AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "No element named: " + string.Join(", ", missing) + ".");
            }

            // Assembly merges nodes within the document tolerance, so solved
            // end points may sit up to that distance from the input lines.
            var tolerance = 1.5 * (Rhino.RhinoDoc.ActiveDoc?.ModelAbsoluteTolerance ?? 0.001);
            return new StbElementNameFilter(lines, tolerance);
        }

        public bool Includes(Line member)
        {
            foreach (var line in _lines)
            {
                if ((member.From.DistanceTo(line.From) <= _tolerance && member.To.DistanceTo(line.To) <= _tolerance)
                    || (member.From.DistanceTo(line.To) <= _tolerance && member.To.DistanceTo(line.From) <= _tolerance))
                {
                    return true;
                }
            }

            return false;
        }
    }
}
