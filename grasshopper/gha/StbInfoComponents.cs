using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using Grasshopper.Kernel;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbInfoElementComponent : GH_Component
    {
        public StbInfoElementComponent()
            : base("Info Element", "Info Elem", "Read the properties of an STb element.", StbCategories.Tab, StbCategories.Info) { }

        public override Guid ComponentGuid => new Guid("3e0fa250-dcdb-471f-b903-7cc86c6879ed");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.InfoElement;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbElementParameter(), "STb Element", "Elem", "STB element to inspect.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddTextParameter("Name", "Name", "Element name.", GH_ParamAccess.item);
            pManager.AddLineParameter("Line", "L", "Element center line.", GH_ParamAccess.item);
            pManager.AddParameter(new StbSectionParameter(), "STb Section", "Sec", "Section of the element.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Beta", "Beta", "Section beta angle in degrees.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Ryi", "Ryi", "EJNT spring about local y at the i-end in kNm/rad. Empty = rigid.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Rzi", "Rzi", "EJNT spring about local z at the i-end in kNm/rad. Empty = rigid.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Ryj", "Ryj", "EJNT spring about local y at the j-end in kNm/rad. Empty = rigid.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Rzj", "Rzj", "EJNT spring about local z at the j-end in kNm/rad. Empty = rigid.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbElementGoo goo = null;
            if (!da.GetData(0, ref goo) || goo?.Value == null) return;

            var element = goo.Value;
            da.SetData(0, element.Name);
            da.SetData(1, element.Line);
            da.SetData(2, element.Section == null ? null : new StbSectionGoo(element.Section));
            da.SetData(3, element.Beta);
            StbInfoUtil.SetOptional(da, 4, element.JointRyi);
            StbInfoUtil.SetOptional(da, 5, element.JointRzi);
            StbInfoUtil.SetOptional(da, 6, element.JointRyj);
            StbInfoUtil.SetOptional(da, 7, element.JointRzj);
        }
    }

    public sealed class StbInfoMaterialComponent : GH_Component
    {
        public StbInfoMaterialComponent()
            : base("Info Material", "Info Mat", "Read the properties of an STb material.", StbCategories.Tab, StbCategories.Info) { }

        public override Guid ComponentGuid => new Guid("234d0eac-3a87-4e98-806c-866221cb3fde");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.InfoMaterial;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbMaterialParameter(), "STb Mat", "Mat", "STB material to inspect.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddTextParameter("Name", "Name", "Material name.", GH_ParamAccess.item);
            pManager.AddNumberParameter("E", "E", "Young's modulus in N/mm2.", GH_ParamAccess.item);
            pManager.AddNumberParameter("G", "G", "Shear modulus in N/mm2.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Gamma", "Gamma", "Unit weight in kN/m3.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Alpha", "Alpha", "Thermal expansion coefficient.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Fy", "Fy", "Yield stress in N/mm2.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbMaterialGoo goo = null;
            if (!da.GetData(0, ref goo) || goo?.Value == null) return;

            var material = goo.Value;
            da.SetData(0, material.Name);
            da.SetData(1, material.E);
            da.SetData(2, material.G);
            da.SetData(3, material.Gamma);
            da.SetData(4, material.Alpha);
            da.SetData(5, material.Fy);
        }
    }

    public sealed class StbInfoSectionComponent : GH_Component
    {
        // Every dimension name used by any section type. A section fills only the
        // outputs its type defines, so mixed section types stay aligned item by item.
        private static readonly string[] AllDimensionNames = { "B", "H", "D", "tw", "tf", "t" };
        private const int FirstDimensionOutput = 6;

        public StbInfoSectionComponent()
            : base(
                "Info Section",
                "Info Sec",
                "Read the properties of an STb section of any type. Dimension outputs that the section type does not use stay empty.",
                StbCategories.Tab,
                StbCategories.Info)
        {
        }

        public override Guid ComponentGuid => new Guid("ddd9bba3-e1f4-4ba5-ac72-5d54e6fc8803");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.InfoSection;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbSectionParameter(), "STb Section", "Sec", "STB section to inspect.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddTextParameter("Name", "Name", "Section name.", GH_ParamAccess.item);
            pManager.AddParameter(new StbMaterialParameter(), "STb Mat", "Mat", "Material of the section.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("Type", "Type", "Section type id (0 = Rectangle, 1 = Circle, 2 = I-section, 3 = CHS, 4 = RHS).", GH_ParamAccess.item);
            pManager.AddTextParameter("Type Name", "TName", "Section type name as shown in the STb Section drop-down.", GH_ParamAccess.item);
            pManager.AddTextParameter("Dimension Names", "DimN", "Dimension names of this section type, in input order.", GH_ParamAccess.list);
            pManager.AddNumberParameter("Dimensions", "Dims", "Dimensions in mm, in the order of Dimension Names.", GH_ParamAccess.list);
            foreach (var name in AllDimensionNames)
            {
                pManager.AddNumberParameter(name, name, name + " in mm. Empty when the section type has no " + name + ".", GH_ParamAccess.item);
            }
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbSectionGoo goo = null;
            if (!da.GetData(0, ref goo) || goo?.Value == null) return;

            var section = goo.Value;
            da.SetData(0, section.Name);
            da.SetData(1, section.Material == null ? null : new StbMaterialGoo(section.Material));
            da.SetData(2, section.Type);
            da.SetDataList(5, section.Dimensions);

            if (section.Type < 0 || section.Type >= StbSectionDimensions.TypeCount)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Unknown section type " + section.Type + ".");
                return;
            }

            var names = StbSectionDimensions.ParameterNames(section.Type);
            da.SetData(3, StbSectionDimensions.TypeName(section.Type));
            da.SetDataList(4, names);

            if (section.Dimensions.Count != names.Count)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    section.Name + " has " + section.Dimensions.Count + " dimension(s); "
                    + StbSectionDimensions.TypeName(section.Type) + " expects " + names.Count + ".");
            }

            for (var i = 0; i < AllDimensionNames.Length; i++)
            {
                var index = IndexOf(names, AllDimensionNames[i]);
                if (index >= 0 && index < section.Dimensions.Count)
                {
                    da.SetData(FirstDimensionOutput + i, section.Dimensions[index]);
                }
            }
        }

        private static int IndexOf(IReadOnlyList<string> names, string name)
        {
            for (var i = 0; i < names.Count; i++)
            {
                if (string.Equals(names[i], name, StringComparison.Ordinal)) return i;
            }

            return -1;
        }
    }

    public sealed class StbInfoLoadComponent : GH_Component
    {
        public StbInfoLoadComponent()
            : base(
                "Info Load",
                "Info Ld",
                "Read the properties of an STb load of any kind (point, line, area, gravity, combination). Outputs that do not apply to the load kind stay empty.",
                StbCategories.Tab,
                StbCategories.Info)
        {
        }

        public override Guid ComponentGuid => new Guid("b396726c-8b0a-49ae-accd-4c67afcab9db");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.InfoLoad;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbLoadParameter(), "STb Load", "Ld", "STB load to inspect.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddTextParameter("Kind", "Kind", "Point, Line, Area, Gravity, or Combination.", GH_ParamAccess.item);
            pManager.AddIntegerParameter("LC", "LC", "Load case id.", GH_ParamAccess.item);
            pManager.AddPointParameter("Point", "P", "Point load: loaded point in meters.", GH_ParamAccess.item);
            pManager.AddVectorParameter("F", "F", "Point load: force vector in kN.", GH_ParamAccess.item);
            pManager.AddVectorParameter("M", "M", "Point load: moment vector in kNm.", GH_ParamAccess.item);
            pManager.AddLineParameter("Element Line", "L", "Line load: center line of the loaded element.", GH_ParamAccess.item);
            pManager.AddBooleanParameter("Global", "G", "Line load: true for global, false for element local coordinates.", GH_ParamAccess.item);
            pManager.AddVectorParameter("Load i", "Wi", "Line load: distributed load at T0 in kN/m.", GH_ParamAccess.item);
            pManager.AddVectorParameter("Load j", "Wj", "Line load: distributed load at T1 in kN/m.", GH_ParamAccess.item);
            pManager.AddNumberParameter("T0", "T0", "Line load: start of the segment (0 = i-end, 1 = j-end).", GH_ParamAccess.item);
            pManager.AddNumberParameter("T1", "T1", "Line load: end of the segment (0 = i-end, 1 = j-end).", GH_ParamAccess.item);
            pManager.AddLineParameter("Boundary", "B", "Area load: boundary element lines.", GH_ParamAccess.list);
            pManager.AddVectorParameter("Pressure", "Pr", "Area load: pressure vector in kN/m2.", GH_ParamAccess.item);
            pManager.AddVectorParameter("Acceleration", "Acc", "Gravity load: acceleration vector in m/s2.", GH_ParamAccess.item);
            pManager.AddTextParameter("Name", "Name", "Combination: name.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Factors", "Fac", "Combination: factor for each combined load case.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Load Cases", "LCs", "Combination: combined load cases, in the order of Factors.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbLoadGoo goo = null;
            if (!da.GetData(0, ref goo) || goo?.Value == null) return;

            var load = goo.Value;
            da.SetData(0, load.Kind.ToString());
            da.SetData(1, load.LoadCase);

            switch (load.Kind)
            {
                case StbLoadKind.Point:
                    da.SetData(2, load.Point);
                    da.SetData(3, load.Force);
                    da.SetData(4, load.Moment);
                    break;
                case StbLoadKind.Line:
                    da.SetData(5, load.ElementLine);
                    da.SetData(6, load.IsGlobal);
                    da.SetData(7, load.LoadAtI);
                    da.SetData(8, load.LoadAtJ);
                    da.SetData(9, load.T0);
                    da.SetData(10, load.T1);
                    break;
                case StbLoadKind.Area:
                    da.SetDataList(11, load.BoundaryLines);
                    da.SetData(12, load.Pressure);
                    break;
                case StbLoadKind.Gravity:
                    da.SetData(13, load.Acceleration);
                    break;
                case StbLoadKind.Combination:
                    da.SetData(14, load.CombinationName);
                    da.SetDataList(15, load.CombinationFactors);
                    da.SetDataList(16, load.CombinationCases);
                    break;
            }
        }
    }

    public sealed class StbInfoSupportComponent : GH_Component
    {
        public StbInfoSupportComponent()
            : base("Info Support", "Info Sup", "Read the location and restraints of an STb support.", StbCategories.Tab, StbCategories.Info) { }

        public override Guid ComponentGuid => new Guid("f7594f87-734b-42ce-b3de-f0acf95bfaa9");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.InfoSupport;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbSupportParameter(), "STb Support", "Sup", "STB support to inspect.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddPointParameter("Point", "P", "Support location in meters.", GH_ParamAccess.item);
            pManager.AddTextParameter("Condition", "Cond", "Restraints as Tx,Ty,Tz,Rx,Ry,Rz (1 = fixed, 0 = free).", GH_ParamAccess.item);
            pManager.AddBooleanParameter("Tx", "Tx", "True when translation along X is fixed.", GH_ParamAccess.item);
            pManager.AddBooleanParameter("Ty", "Ty", "True when translation along Y is fixed.", GH_ParamAccess.item);
            pManager.AddBooleanParameter("Tz", "Tz", "True when translation along Z is fixed.", GH_ParamAccess.item);
            pManager.AddBooleanParameter("Rx", "Rx", "True when rotation about X is fixed.", GH_ParamAccess.item);
            pManager.AddBooleanParameter("Ry", "Ry", "True when rotation about Y is fixed.", GH_ParamAccess.item);
            pManager.AddBooleanParameter("Rz", "Rz", "True when rotation about Z is fixed.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbSupportGoo goo = null;
            if (!da.GetData(0, ref goo) || goo?.Value == null) return;

            var support = goo.Value;
            var restraints = new[] { support.Tx, support.Ty, support.Tz, support.Rx, support.Ry, support.Rz };
            var bits = new string[restraints.Length];
            for (var i = 0; i < restraints.Length; i++)
            {
                bits[i] = restraints[i] ? "1" : "0";
                da.SetData(2 + i, restraints[i]);
            }

            da.SetData(0, support.Point);
            da.SetData(1, string.Join(",", bits));
        }
    }

    public sealed class StbInfoModelComponent : GH_Component
    {
        public StbInfoModelComponent()
            : base("Info Model", "Info Model", "Read the elements, supports, loads, sections, and materials of an STb model.", StbCategories.Tab, StbCategories.Info) { }

        public override Guid ComponentGuid => new Guid("d12196c2-7481-4e77-8986-9b07dd09e32b");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.InfoModel;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "STb model to inspect.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbElementParameter(), "STb Element", "Elem", "Elements of the model.", GH_ParamAccess.list);
            pManager.AddParameter(new StbSupportParameter(), "STb Support", "Sup", "Supports of the model.", GH_ParamAccess.list);
            pManager.AddParameter(new StbLoadParameter(), "STb Load", "Ld", "Loads and load combinations of the model.", GH_ParamAccess.list);
            pManager.AddParameter(new StbSectionParameter(), "STb Section", "Sec", "Distinct sections used by the elements.", GH_ParamAccess.list);
            pManager.AddParameter(new StbMaterialParameter(), "STb Mat", "Mat", "Distinct materials used by the sections.", GH_ParamAccess.list);
            pManager.AddLineParameter("Lines", "L", "Element center lines.", GH_ParamAccess.list);
            pManager.AddTextParameter("DAT Text", "Text", "Assembled STB input text.", GH_ParamAccess.item);
            pManager.AddTextParameter("DAT Path", "DAT", "Path of the .dat file. Empty when it has not been written.", GH_ParamAccess.item);
            pManager.AddBooleanParameter("Analyzed", "Res", "True when the model carries analysis results.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            if (!StbModelGooUtil.TryGetModel(da, 0, out var model)) return;

            var elements = new List<StbElementGoo>();
            var lines = new List<Line>();
            var sections = new List<StbSectionModel>();
            var materials = new List<StbMaterialModel>();
            foreach (var element in model.Elements)
            {
                if (element == null) continue;
                elements.Add(new StbElementGoo(element));
                lines.Add(element.Line);
                var section = element.Section;
                if (section == null || sections.Exists(s => s.Matches(section, StbInfoUtil.PropertyTolerance))) continue;
                sections.Add(section);
                var material = section.Material;
                if (material != null && !materials.Exists(m => m.Matches(material, StbInfoUtil.PropertyTolerance)))
                {
                    materials.Add(material);
                }
            }

            var supports = new List<StbSupportGoo>();
            foreach (var support in model.Supports)
            {
                if (support != null) supports.Add(new StbSupportGoo(support));
            }

            var loads = new List<StbLoadGoo>();
            foreach (var load in model.Loads)
            {
                if (load != null) loads.Add(new StbLoadGoo(load));
            }

            da.SetDataList(0, elements);
            da.SetDataList(1, supports);
            da.SetDataList(2, loads);
            da.SetDataList(3, sections.ConvertAll(s => new StbSectionGoo(s)));
            da.SetDataList(4, materials.ConvertAll(m => new StbMaterialGoo(m)));
            da.SetDataList(5, lines);
            da.SetData(6, model.DatText);
            da.SetData(7, model.DatPath);
            da.SetData(8, model.Results != null);
        }
    }

    public sealed class StbInfoNodeComponent : GH_Component
    {
        public StbInfoNodeComponent()
            : base(
                "Info Node",
                "Info Node",
                "Read the nodes of an STb model with the ids used in its .dat text and analysis results (after duplicate nodes are merged).",
                StbCategories.Tab,
                StbCategories.Info)
        {
        }

        public override Guid ComponentGuid => new Guid("0a8fc9f1-66e4-4119-8998-b58ae5ab7394");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.InfoNode;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "STb model whose nodes are listed.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddIntegerParameter("Node IDs", "N", "Node ids, matching Displacements and Reactions.", GH_ParamAccess.list);
            pManager.AddPointParameter("Points", "P", "Node coordinates in meters.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            if (!StbModelGooUtil.TryGetModel(da, 0, out var model)) return;

            if (string.IsNullOrWhiteSpace(model.DatText))
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "The model has no .dat text; connect it from STB Assemble Model or STb Assembly from file.");
                return;
            }

            var ids = new List<int>();
            var points = new List<Point3d>();
            using (var reader = new StringReader(model.DatText))
            {
                string rawLine;
                while ((rawLine = reader.ReadLine()) != null)
                {
                    var parts = rawLine.Trim().Split(',');
                    if (parts.Length < 5 || !string.Equals(parts[0].Trim(), "NODE", StringComparison.OrdinalIgnoreCase)) continue;

                    if (int.TryParse(parts[1].Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var id)
                        && TryNumber(parts[2], out var x)
                        && TryNumber(parts[3], out var y)
                        && TryNumber(parts[4].Trim().TrimEnd('*'), out var z))
                    {
                        ids.Add(id);
                        points.Add(new Point3d(x, y, z));
                    }
                }
            }

            da.SetDataList(0, ids);
            da.SetDataList(1, points);
        }

        private static bool TryNumber(string text, out double value)
        {
            return double.TryParse(text.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out value);
        }
    }

    internal static class StbInfoUtil
    {
        public const double PropertyTolerance = 1e-6;

        public static void SetOptional(IGH_DataAccess da, int index, double? value)
        {
            if (value.HasValue)
            {
                da.SetData(index, value.Value);
            }
        }
    }
}
