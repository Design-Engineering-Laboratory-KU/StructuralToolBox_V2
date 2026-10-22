using System;
using System.Collections.Generic;
using System.Drawing;
using Grasshopper;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Data;
using Grasshopper.Kernel.Parameters;
using Grasshopper.Kernel.Types;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbGridFrameComponent : GH_Component
    {
        public StbGridFrameComponent()
            : base(
                "STb Grid Frame",
                "STb Grid",
                "Generate a rectangular multi-story frame: member lines, base supports, and floor / exterior wall panel boundaries for area loads.",
                StbCategories.Tab,
                StbCategories.Element)
        {
        }

        public override Guid ComponentGuid => new Guid("6f3d2b81-4c9e-4a57-b0e2-8d1c5a7f9e36");
        public override GH_Exposure Exposure => GH_Exposure.tertiary;

        protected override Bitmap Icon => StbIcons.GridFrame;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddNumberParameter("X Spans", "X", "Span lengths along X in meters. The list repeats when X Count is larger.", GH_ParamAccess.list, 5.5);
            pManager.AddIntegerParameter("X Count", "Nx", "Number of X spans. 0 uses the X Spans list as given.", GH_ParamAccess.item, 0);
            pManager.AddNumberParameter("Y Spans", "Y", "Span lengths along Y in meters. The list repeats when Y Count is larger.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Y Count", "Ny", "Number of Y spans. 0 uses the Y Spans list as given.", GH_ParamAccess.item, 0);
            pManager.AddNumberParameter("Story Heights", "H", "Story heights from the base in meters. The list repeats when Stories is larger.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Stories", "Nz", "Number of stories. 0 uses the Story Heights list as given.", GH_ParamAccess.item, 0);
            SetDefaults(pManager, 2, 9.0, 3.2);
            SetDefaults(pManager, 4, 3.8, 3.5);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddPointParameter("Nodes", "Pt", "All grid nodes.", GH_ParamAccess.list);
            pManager.AddLineParameter("Columns", "C", "Column lines.", GH_ParamAccess.list);
            pManager.AddLineParameter("X Beams", "Bx", "Beam lines along X on the upper floors.", GH_ParamAccess.list);
            pManager.AddLineParameter("Y Beams", "By", "Beam lines along Y on the upper floors.", GH_ParamAccess.list);
            pManager.AddLineParameter("X Foundation", "Fx", "Foundation beam lines along X at the base.", GH_ParamAccess.list);
            pManager.AddLineParameter("Y Foundation", "Fy", "Foundation beam lines along Y at the base.", GH_ParamAccess.list);
            pManager.AddPointParameter("Supports", "S", "Base nodes.", GH_ParamAccess.list);
            pManager.AddLineParameter("Floor Panels", "Pf", "One branch of four boundary lines per floor bay, base level included.", GH_ParamAccess.tree);
            pManager.AddLineParameter("Wall Panels", "Pw", "One branch of four boundary lines per bay on the exterior walls at Y = 0 and Y = max.", GH_ParamAccess.tree);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var xSpans = new List<double>();
            var ySpans = new List<double>();
            var heights = new List<double>();
            int xCount = 0, yCount = 0, stories = 0;
            da.GetDataList(0, xSpans);
            da.GetData(1, ref xCount);
            da.GetDataList(2, ySpans);
            da.GetData(3, ref yCount);
            da.GetDataList(4, heights);
            da.GetData(5, ref stories);

            if (!TryExpand("X Spans", xSpans, xCount, out var xs)
                || !TryExpand("Y Spans", ySpans, yCount, out var ys)
                || !TryExpand("Story Heights", heights, stories, out var zs))
            {
                return;
            }

            var x = Coordinates(xs);
            var y = Coordinates(ys);
            var z = Coordinates(zs);
            int nx = xs.Count, ny = ys.Count, nz = zs.Count;

            Point3d P(int i, int j, int k) => new Point3d(x[i], y[j], z[k]);

            // xLine[k, j, i]: level k, grid row j, bay i. yLine[k, i, j]: level k, grid column i, bay j.
            var xLine = new Line[nz + 1, ny + 1, nx];
            var yLine = new Line[nz + 1, nx + 1, ny];
            var column = new Line[nz, nx + 1, ny + 1];

            var nodes = new List<Point3d>();
            var supports = new List<Point3d>();
            var columns = new List<Line>();
            var xBeams = new List<Line>();
            var yBeams = new List<Line>();
            var xFoundation = new List<Line>();
            var yFoundation = new List<Line>();

            for (var k = 0; k <= nz; k++)
            {
                for (var j = 0; j <= ny; j++)
                {
                    for (var i = 0; i <= nx; i++)
                    {
                        nodes.Add(P(i, j, k));
                        if (k == 0)
                        {
                            supports.Add(P(i, j, k));
                        }
                    }
                }

                for (var j = 0; j <= ny; j++)
                {
                    for (var i = 0; i < nx; i++)
                    {
                        xLine[k, j, i] = new Line(P(i, j, k), P(i + 1, j, k));
                        (k == 0 ? xFoundation : xBeams).Add(xLine[k, j, i]);
                    }
                }

                for (var i = 0; i <= nx; i++)
                {
                    for (var j = 0; j < ny; j++)
                    {
                        yLine[k, i, j] = new Line(P(i, j, k), P(i, j + 1, k));
                        (k == 0 ? yFoundation : yBeams).Add(yLine[k, i, j]);
                    }
                }

                if (k == nz)
                {
                    continue;
                }

                for (var j = 0; j <= ny; j++)
                {
                    for (var i = 0; i <= nx; i++)
                    {
                        column[k, i, j] = new Line(P(i, j, k), P(i, j, k + 1));
                        columns.Add(column[k, i, j]);
                    }
                }
            }

            var floorPanels = new DataTree<Line>();
            var panel = 0;
            for (var k = 0; k <= nz; k++)
            {
                for (var j = 0; j < ny; j++)
                {
                    for (var i = 0; i < nx; i++)
                    {
                        floorPanels.AddRange(
                            new[] { xLine[k, j, i], yLine[k, i + 1, j], xLine[k, j + 1, i], yLine[k, i, j] },
                            new GH_Path(panel++));
                    }
                }
            }

            var wallPanels = new DataTree<Line>();
            panel = 0;
            foreach (var j in new[] { 0, ny })
            {
                for (var k = 0; k < nz; k++)
                {
                    for (var i = 0; i < nx; i++)
                    {
                        wallPanels.AddRange(
                            new[] { xLine[k, j, i], column[k, i + 1, j], xLine[k + 1, j, i], column[k, i, j] },
                            new GH_Path(panel++));
                    }
                }
            }

            Message = nx + " x " + ny + " spans, " + nz + (nz == 1 ? " story" : " stories");

            da.SetDataList(0, nodes);
            da.SetDataList(1, columns);
            da.SetDataList(2, xBeams);
            da.SetDataList(3, yBeams);
            da.SetDataList(4, xFoundation);
            da.SetDataList(5, yFoundation);
            da.SetDataList(6, supports);
            da.SetDataTree(7, floorPanels);
            da.SetDataTree(8, wallPanels);
        }

        private bool TryExpand(string name, List<double> values, int count, out List<double> result)
        {
            result = new List<double>();
            if (values.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, name + " is empty.");
                return false;
            }

            foreach (var value in values)
            {
                if (!(value > 0.0) || double.IsInfinity(value))
                {
                    AddRuntimeMessage(GH_RuntimeMessageLevel.Error, name + " must contain positive lengths.");
                    return false;
                }
            }

            var n = count > 0 ? count : values.Count;
            for (var i = 0; i < n; i++)
            {
                result.Add(values[i % values.Count]);
            }

            return true;
        }

        private static List<double> Coordinates(List<double> spans)
        {
            var coordinates = new List<double> { 0.0 };
            foreach (var span in spans)
            {
                coordinates.Add(coordinates[coordinates.Count - 1] + span);
            }

            return coordinates;
        }

        private static void SetDefaults(GH_InputParamManager pManager, int index, params double[] values)
        {
            var parameter = (Param_Number)pManager[index];
            parameter.PersistentData.ClearData();
            foreach (var value in values)
            {
                parameter.PersistentData.Append(new GH_Number(value));
            }
        }
    }
}
