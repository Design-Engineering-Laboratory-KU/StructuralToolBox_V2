using System.Collections.Generic;
using System.Linq;
using Grasshopper.Kernel.Data;

namespace StbGrasshopper
{
    internal static class StbLoadCaseFilter
    {
        /// <summary>
        /// Negative loadCase means all load cases.
        /// </summary>
        public static bool Matches(int loadCase, int rowLoadCase)
        {
            return loadCase < 0 || loadCase == rowLoadCase;
        }

        /// <summary>
        /// Output branch for one element: {Element ID}, or {LC;Element ID} when the
        /// output spans several load cases.
        /// </summary>
        public static GH_Path ElementPath(bool withLoadCase, int loadCase, int elementId)
        {
            return withLoadCase ? new GH_Path(loadCase, elementId) : new GH_Path(elementId);
        }

        public static List<int> GetLoadCases(StbParsedResults results)
        {
            if (results == null)
            {
                return new List<int>();
            }

            var values = new HashSet<int>();
            foreach (var row in results.Displacements)
            {
                values.Add(row.LoadCase);
            }

            foreach (var row in results.Reactions)
            {
                values.Add(row.LoadCase);
            }

            foreach (var row in results.ElementForces)
            {
                values.Add(row.LoadCase);
            }

            return values.OrderBy(v => v).ToList();
        }
    }
}
