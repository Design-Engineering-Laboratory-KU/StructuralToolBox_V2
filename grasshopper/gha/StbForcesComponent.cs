using System;
using System.Collections.Generic;
using System.Drawing;
using Grasshopper;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Data;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbForcesComponent : GH_Component
    {
        public StbForcesComponent()
            : base(
                "STB Forces",
                "STB Forces",
                "Extract the six member forces at the start, at parameters t, and at the end of each element.",
                StbCategories.Tab,
                StbCategories.Post)
        {
        }

        public override Guid ComponentGuid => new Guid("f9c17ef0-3886-4142-9beb-a583438489ec");

        protected override Bitmap Icon => StbIcons.Forces;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "STb Model containing parsed results.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("Load Case", "LC", "Load case to extract. Negative means all.", GH_ParamAccess.item, 0);
            pManager.AddTextParameter("Name", "Name", "Element names (STb Element Name) to extract. Empty extracts every element.", GH_ParamAccess.list);
            pManager.AddNumberParameter("t", "t", "Parameters along the member (0 = start, 1 = end) evaluated between the start and end values.", GH_ParamAccess.list, 0.5);
            pManager[2].Optional = true;
            pManager[3].Optional = true;
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            const string order = " Each branch {Element ID} ({LC;Element ID} for several load cases) lists start, t, end.";
            pManager.AddIntegerParameter("Element ID", "E", "Element id of each branch.", GH_ParamAccess.tree);
            pManager.AddNumberParameter("N", "N", "Axial force in kN." + order, GH_ParamAccess.tree);
            pManager.AddNumberParameter("Vy", "Vy", "Shear force along local y in kN." + order, GH_ParamAccess.tree);
            pManager.AddNumberParameter("Vz", "Vz", "Shear force along local z in kN." + order, GH_ParamAccess.tree);
            pManager.AddNumberParameter("Mx", "Mx", "Torsional moment in kNm." + order, GH_ParamAccess.tree);
            pManager.AddNumberParameter("My", "My", "Bending moment about local y in kNm." + order, GH_ParamAccess.tree);
            pManager.AddNumberParameter("Mz", "Mz", "Bending moment about local z in kNm." + order, GH_ParamAccess.tree);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            if (!StbModelGooUtil.TryGetResults(da, 0, out var results))
            {
                return;
            }

            int loadCase = 0;
            var names = new List<string>();
            var parameters = new List<double>();
            da.GetData(1, ref loadCase);
            da.GetDataList(2, names);
            da.GetDataList(3, parameters);

            var stations = new List<double> { 0.0 };
            var clamped = false;
            foreach (var t in parameters)
            {
                if (double.IsNaN(t) || double.IsInfinity(t)) continue;
                var value = Math.Max(0.0, Math.Min(1.0, t));
                clamped |= value != t;
                stations.Add(value);
            }

            stations.Add(1.0);
            if (clamped)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "t values outside 0-1 were clamped.");
            }

            var nodes = new Dictionary<int, Point3d>();
            foreach (var node in results.Nodes)
            {
                nodes[node.NodeId] = node.Point;
            }

            var elements = new Dictionary<int, StbElementGeometry>();
            foreach (var element in results.Elements)
            {
                elements[element.ElementId] = element;
            }

            var nameFilter = StbElementNameFilter.Create(names, da, 0, this);
            var hasElementLoadSegments = results.ElementLoadSegments.Count > 0;

            var rows = new List<ElementForce>();
            var lengths = new List<double>();
            var loadCases = new HashSet<int>();
            foreach (var force in results.ElementForces)
            {
                if (!StbLoadCaseFilter.Matches(loadCase, force.LoadCase))
                {
                    continue;
                }

                var length = 0.0;
                if (elements.TryGetValue(force.ElementId, out var element)
                    && nodes.TryGetValue(element.NodeI, out var start)
                    && nodes.TryGetValue(element.NodeJ, out var end))
                {
                    length = start.DistanceTo(end);
                    if (nameFilter != null && !nameFilter.Includes(new Line(start, end)))
                    {
                        continue;
                    }
                }
                else if (nameFilter != null)
                {
                    continue;
                }

                rows.Add(force);
                lengths.Add(length);
                loadCases.Add(force.LoadCase);
            }

            if (rows.Count == 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    "No element force rows found for load case " + loadCase + ".");
                return;
            }

            var withCase = loadCases.Count > 1;
            var ids = new DataTree<int>();
            var outputs = new DataTree<double>[6];
            for (var k = 0; k < outputs.Length; k++)
            {
                outputs[k] = new DataTree<double>();
            }

            for (var r = 0; r < rows.Count; r++)
            {
                var force = rows[r];
                var path = StbLoadCaseFilter.ElementPath(withCase, force.LoadCase, force.ElementId);
                ids.Add(force.ElementId, path);
                var loadSegments = hasElementLoadSegments
                    ? results.GetElementLoadSegments(force.LoadCase, force.ElementId)
                    : null;

                for (var s = 0; s < stations.Count; s++)
                {
                    var values = ValuesAt(force, stations[s], s == 0, s == stations.Count - 1, lengths[r], loadSegments, hasElementLoadSegments);
                    for (var k = 0; k < outputs.Length; k++)
                    {
                        outputs[k].Add(values[k], path);
                    }
                }
            }

            da.SetDataTree(0, ids);
            for (var k = 0; k < outputs.Length; k++)
            {
                da.SetDataTree(k + 1, outputs[k]);
            }
        }

        // Same values as STB Force Diagram: solver end values at the ends, the exact
        // section forces when EWLD rows exist, otherwise the diagram's interpolation.
        private static double[] ValuesAt(
            ElementForce force,
            double t,
            bool isStart,
            bool isEnd,
            double length,
            IReadOnlyList<ElementLoadSegment> loadSegments,
            bool exact)
        {
            if (isStart)
            {
                return new[] { force.Ni, force.Qyi, force.Qzi, force.Mxi, force.Myi, force.Mzi };
            }

            if (isEnd)
            {
                return new[] { force.Nj, force.Qyj, force.Qzj, force.Mxj, force.Myj, force.Mzj };
            }

            if (exact && length > 0.0)
            {
                var v = StbSectionForces.Evaluate(force, length, loadSegments, t);
                return new[] { v.N, v.Qy, v.Qz, v.Mx, v.My, v.Mz };
            }

            return new[]
            {
                Linear(force.Ni, force.Nj, t),
                Linear(force.Qyi, force.Qyj, t),
                Linear(force.Qzi, force.Qzj, t),
                Linear(force.Mxi, force.Mxj, t),
                Quadratic(force.Myi, force.Myc, force.Myj, t),
                Quadratic(force.Mzi, force.Mzc, force.Mzj, t),
            };
        }

        private static double Linear(double valueI, double valueJ, double t)
        {
            return valueI + (valueJ - valueI) * t;
        }

        private static double Quadratic(double valueI, double center, double valueJ, double t)
        {
            var l0 = 2.0 * (t - 0.5) * (t - 1.0);
            var lc = 4.0 * t * (1.0 - t);
            var l1 = 2.0 * t * (t - 0.5);
            return valueI * l0 + center * lc + valueJ * l1;
        }
    }
}
