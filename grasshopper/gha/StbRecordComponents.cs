using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using GH_IO.Serialization;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using Rhino;
using Rhino.Geometry;

namespace StbGrasshopper
{
    internal static class StbRecord
    {
        public static string Number(double value)
        {
            return value.ToString("0.##########", CultureInfo.InvariantCulture);
        }
    }

    public sealed class StbDatNodesComponent : GH_Component
    {
        public StbDatNodesComponent() : base("STB DAT Nodes", "STB DAT Nodes", "Read NODE records from an existing STB .dat file.", StbCategories.Tab, StbCategories.Assemble) { }
        public override Guid ComponentGuid => new Guid("279ef031-21dd-4fda-b262-baa1e473a66f");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.DatNodes;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("DAT Path", "DAT", "Path to the STB .dat file.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddIntegerParameter("Node IDs", "N", "Node ids read from NODE records.", GH_ParamAccess.list);
            pManager.AddPointParameter("Points", "P", "Original node coordinates in meters.", GH_ParamAccess.list);
            pManager.AddTextParameter("Records", "Rec", "NODE records read from the file.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string datPath = null;
            if (!da.GetData(0, ref datPath)) return;

            if (string.IsNullOrWhiteSpace(datPath) || !File.Exists(datPath))
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "DAT file not found: " + datPath);
                return;
            }

            StbDatParser.ReadGeometry(datPath, out var parsedNodes, out _);

            var nodeIds = new List<int>();
            var points = new List<Point3d>();
            var records = new List<string>();

            foreach (var node in parsedNodes)
            {
                nodeIds.Add(node.NodeId);
                points.Add(node.Point);
                records.Add(
                    "NODE,"
                    + node.NodeId
                    + ","
                    + StbRecord.Number(node.Point.X)
                    + ","
                    + StbRecord.Number(node.Point.Y)
                    + ","
                    + StbRecord.Number(node.Point.Z));
            }

            da.SetDataList(0, nodeIds);
            da.SetDataList(1, points);
            da.SetDataList(2, records);
        }
    }

    public sealed class StbDatBeamsComponent : GH_Component
    {
        public StbDatBeamsComponent() : base("STB DAT Beams", "STB DAT Beams", "Read ELEM records from an existing STB .dat file.", StbCategories.Tab, StbCategories.Assemble) { }
        public override Guid ComponentGuid => new Guid("8b2f4a19-6c3d-4f0a-9f1e-2d8b7a4c1e03");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.DatBeams;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("DAT Path", "DAT", "Path to the STB .dat file.", GH_ParamAccess.item);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddIntegerParameter("Element IDs", "E", "Element ids read from ELEM records.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Node I", "I", "Start node ids.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Node J", "J", "End node ids.", GH_ParamAccess.list);
            pManager.AddTextParameter("Records", "Rec", "ELEM records read from the file.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string datPath = null;
            if (!da.GetData(0, ref datPath)) return;

            if (string.IsNullOrWhiteSpace(datPath) || !File.Exists(datPath))
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "DAT file not found: " + datPath);
                return;
            }

            StbDatParser.ReadGeometry(datPath, out _, out var parsedElements);

            var elementIds = new List<int>();
            var nodeI = new List<int>();
            var nodeJ = new List<int>();
            var records = new List<string>();

            foreach (var element in parsedElements)
            {
                elementIds.Add(element.ElementId);
                nodeI.Add(element.NodeI);
                nodeJ.Add(element.NodeJ);
                records.Add("ELEM," + element.ElementId + "," + element.NodeI + "," + element.NodeJ + ",0,0");
            }

            da.SetDataList(0, elementIds);
            da.SetDataList(1, nodeI);
            da.SetDataList(2, nodeJ);
            da.SetDataList(3, records);
        }
    }

    public sealed class StbElementComponent : GH_Component
    {
        public StbElementComponent() : base("STb Element", "STb Elem", "Create an STb element from a line and section.", StbCategories.Tab, StbCategories.Element) { }
        public override Guid ComponentGuid => new Guid("e9ac94fe-4ee4-4d15-b16b-7881e3b1f622");

        protected override Bitmap Icon => StbIcons.Element;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("Name", "Name", "Element name.", GH_ParamAccess.item, "ELEM");
            pManager.AddLineParameter("Line", "L", "Element center line.", GH_ParamAccess.item);
            pManager.AddParameter(new StbSectionParameter(), "STb Section", "Sec", "Section definition.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Beta", "Beta", "Section beta angle in degrees.", GH_ParamAccess.item, 0.0);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbElementParameter(), "STb Element", "Elem", "STB element object.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string name = "ELEM";
            var line = Line.Unset;
            double beta = 0.0;
            da.GetData(0, ref name);
            if (!da.GetData(1, ref line)) return;
            if (!StbModelGooUtil.TryGetSection(da, 2, out var section)) return;
            da.GetData(3, ref beta);

            if (!line.IsValid)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Invalid line.");
                return;
            }

            var element = new StbElementModel
            {
                Name = name,
                Line = line,
                Section = section,
                Beta = beta,
            };

            da.SetData(0, new StbElementGoo(element));
        }
    }

    public sealed class StbMaterialComponent : GH_Component
    {
        public StbMaterialComponent() : base("STb Mat", "STb Mat", "Create an STb material object.", StbCategories.Tab, StbCategories.Material) { }
        public override Guid ComponentGuid => new Guid("2c6d678d-92f9-4ee5-a171-e95d64b1411b");

        protected override Bitmap Icon => StbIcons.Material;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("Name", "Name", "Material name.", GH_ParamAccess.item, "MAT");
            pManager.AddNumberParameter("E", "E", "Young's modulus in N/mm2.", GH_ParamAccess.item, 205000.0);
            pManager.AddNumberParameter("G", "G", "Shear modulus in N/mm2.", GH_ParamAccess.item, 79000.0);
            pManager.AddNumberParameter("Gamma", "Gamma", "Unit weight in kN/m3.", GH_ParamAccess.item, 78.5);
            pManager.AddNumberParameter("Alpha", "Alpha", "Thermal expansion coefficient.", GH_ParamAccess.item, 0.0);
            pManager.AddNumberParameter("Fy", "Fy", "Yield stress in N/mm2.", GH_ParamAccess.item, 235.0);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbMaterialParameter(), "STb Mat", "Mat", "STB material object.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string name = "MAT";
            double e = 205000.0, g = 79000.0, gamma = 78.5, alpha = 0.0, fy = 235.0;
            da.GetData(0, ref name);
            da.GetData(1, ref e);
            da.GetData(2, ref g);
            da.GetData(3, ref gamma);
            da.GetData(4, ref alpha);
            da.GetData(5, ref fy);

            da.SetData(0, new StbMaterialGoo(new StbMaterialModel
            {
                Name = name,
                E = e,
                G = g,
                Gamma = gamma,
                Alpha = alpha,
                Fy = fy,
            }));
        }
    }

    public sealed class StbSectionComponent : GH_Component, IStbDropDownOwner
    {
        private const string SectionTypeKey = "SectionType";
        private int _sectionType;

        public StbSectionComponent() : base("STb Section", "STb Sec", "Create an STb section object.", StbCategories.Tab, StbCategories.Section) { }
        public override Guid ComponentGuid => new Guid("fd94f3c4-1574-45dc-bd80-6635f18517dd");

        protected override Bitmap Icon => StbIcons.Section;

        internal int SectionType => _sectionType;

        internal string SectionTypeName => StbSectionDimensions.TypeName(_sectionType);

        int IStbDropDownOwner.DropDownCount => StbSectionDimensions.TypeCount;
        int IStbDropDownOwner.DropDownSelection => _sectionType;
        string IStbDropDownOwner.DropDownName(int index) => StbSectionDimensions.TypeName(index);
        void IStbDropDownOwner.SetDropDownSelection(int index) => SetSectionType(index);

        public override void CreateAttributes()
        {
            m_attributes = new StbDropDownAttributes(this, this);
        }

        protected override void AppendAdditionalComponentMenuItems(System.Windows.Forms.ToolStripDropDown menu)
        {
            Menu_AppendSeparator(menu);
            StbDropDownAttributes.AppendChoices(menu, this);
        }

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddTextParameter("Name", "Name", "Section name.", GH_ParamAccess.item, "SEC");
            pManager.AddParameter(new StbMaterialParameter(), "STb Mat", "Mat", "Material definition.", GH_ParamAccess.item);
            AddDimensionParameters(pManager, _sectionType);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbSectionParameter(), "STb Section", "Sec", "STB section object.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            string name = "SEC";
            var dims = new List<double>();
            da.GetData(0, ref name);
            if (!StbModelGooUtil.TryGetMaterial(da, 1, out var material)) return;

            for (var i = 2; i < Params.Input.Count; i++)
            {
                double value = 0.0;
                if (!da.GetData(i, ref value))
                {
                    return;
                }

                dims.Add(value);
            }

            List<double> resolvedDims;
            try
            {
                resolvedDims = StbSectionDimensions.Resolve(_sectionType, dims, useDefaultsWhenEmpty: false);
            }
            catch (InvalidOperationException ex)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ex.Message);
                return;
            }

            var section = new StbSectionModel
            {
                Name = name,
                Material = material,
                Type = _sectionType,
            };
            section.Dimensions.AddRange(resolvedDims);

            da.SetData(0, new StbSectionGoo(section));
        }

        internal void SetSectionType(int type)
        {
            if (type == _sectionType || type < 0 || type >= StbSectionDimensions.TypeCount)
            {
                return;
            }

            RecordUndoEvent("Change section type");
            _sectionType = type;
            RebuildDimensionInputs();
        }

        public override bool Write(GH_IWriter writer)
        {
            writer.SetInt32(SectionTypeKey, _sectionType);
            return base.Write(writer);
        }

        public override bool Read(GH_IReader reader)
        {
            if (reader.ItemExists(SectionTypeKey))
            {
                var type = reader.GetInt32(SectionTypeKey);
                if (type >= 0 && type < StbSectionDimensions.TypeCount)
                {
                    _sectionType = type;
                    RebuildDimensionInputs(expireSolution: false);
                }
            }

            return base.Read(reader);
        }

        private static void AddDimensionParameters(GH_InputParamManager pManager, int type)
        {
            var names = StbSectionDimensions.ParameterNames(type);
            var defaults = StbSectionDimensions.Defaults(type);
            for (var i = 0; i < names.Count; i++)
            {
                var name = names[i];
                pManager.AddNumberParameter(
                    name,
                    name,
                    name + " for " + StbSectionDimensions.TypeName(type) + " in mm.",
                    GH_ParamAccess.item,
                    defaults[i]);
            }
        }

        private void RebuildDimensionInputs(bool expireSolution = true)
        {
            for (var i = Params.Input.Count - 1; i >= 2; i--)
            {
                Params.UnregisterInputParameter(Params.Input[i], true);
            }

            var names = StbSectionDimensions.ParameterNames(_sectionType);
            var defaults = StbSectionDimensions.Defaults(_sectionType);
            for (var i = 0; i < names.Count; i++)
            {
                var name = names[i];
                var parameter = new Param_Number
                {
                    Name = name,
                    NickName = name,
                    Description = name + " for " + SectionTypeName + " in mm.",
                    Access = GH_ParamAccess.item,
                };
                parameter.SetPersistentData(defaults[i]);
                Params.RegisterInputParam(parameter);
            }

            Params.OnParametersChanged();
            Attributes?.ExpireLayout();
            if (expireSolution)
            {
                ExpireSolution(true);
            }
        }
    }

    public sealed class StbSupportComponent : GH_Component
    {
        private readonly bool[] _restraints = { true, true, true, true, true, true };

        public StbSupportComponent() : base("STb Support", "STb Sup", "Create STb support objects from points.", StbCategories.Tab, StbCategories.Support) { }
        public override Guid ComponentGuid => new Guid("54816191-f022-43a1-b094-9bb5cf4bc371");

        protected override Bitmap Icon => StbIcons.Support;

        internal bool IsRestrained(int index) => _restraints[index];

        internal void ToggleRestraint(int index)
        {
            _restraints[index] = !_restraints[index];
            ExpireSolution(true);
        }

        public override void CreateAttributes()
        {
            m_attributes = new StbSupportAttributes(this);
        }

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddPointParameter("Point", "P", "Support location in meters.", GH_ParamAccess.list);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbSupportParameter(), "STb Support", "Sup", "STB support objects.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var points = new List<Point3d>();
            if (!da.GetDataList(0, points)) return;

            var supports = new List<StbSupportGoo>();
            foreach (var point in points)
            {
                supports.Add(new StbSupportGoo(new StbSupportModel
                {
                    Point = point,
                    Tx = _restraints[0],
                    Ty = _restraints[1],
                    Tz = _restraints[2],
                    Rx = _restraints[3],
                    Ry = _restraints[4],
                    Rz = _restraints[5],
                }));
            }

            da.SetDataList(0, supports);
        }

        public override bool Write(GH_IWriter writer)
        {
            for (var i = 0; i < _restraints.Length; i++)
            {
                writer.SetBoolean("Restraint" + i, _restraints[i]);
            }

            return base.Write(writer);
        }

        public override bool Read(GH_IReader reader)
        {
            for (var i = 0; i < _restraints.Length; i++)
            {
                var key = "Restraint" + i;
                if (reader.ItemExists(key))
                {
                    _restraints[i] = reader.GetBoolean(key);
                }
            }

            return base.Read(reader);
        }
    }

    public sealed class StbLoadComponent : GH_Component
    {
        public StbLoadComponent() : base("STb Load", "STb Load", "Create STb point load objects from points.", StbCategories.Tab, StbCategories.Load) { }
        public override Guid ComponentGuid => new Guid("fcf0fb0e-33d0-4926-a09f-1f1bbffcfbc1");

        protected override Bitmap Icon => StbIcons.PointLoad;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddPointParameter("Point", "P", "Loaded point in meters.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("LC", "LC", "Load case id.", GH_ParamAccess.item, 0);
            pManager.AddVectorParameter("F", "F", "Force vector in kN.", GH_ParamAccess.item, Vector3d.Zero);
            pManager.AddVectorParameter("M", "M", "Moment vector in kNm.", GH_ParamAccess.item, Vector3d.Zero);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbLoadParameter(), "STb Load", "Ld", "STB load objects.", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var points = new List<Point3d>();
            int loadCase = 0;
            var force = Vector3d.Zero;
            var moment = Vector3d.Zero;
            if (!da.GetDataList(0, points)) return;
            da.GetData(1, ref loadCase);
            da.GetData(2, ref force);
            da.GetData(3, ref moment);

            var loads = new List<StbLoadGoo>();
            foreach (var point in points)
            {
                loads.Add(new StbLoadGoo(new StbLoadModel
                {
                    Kind = StbLoadKind.Point,
                    Point = point,
                    LoadCase = loadCase,
                    Force = force,
                    Moment = moment,
                }));
            }

            da.SetDataList(0, loads);
        }
    }

    public sealed class StbLineLoadComponent : GH_Component
    {
        public StbLineLoadComponent()
            : base(
                "STb Load",
                "STb LLoad",
                "Create an STb distributed load on a frame element.",
                StbCategories.Tab,
                StbCategories.Load)
        {
        }

        public override Guid ComponentGuid => new Guid("164ce563-ef3c-43f3-887a-e5839829f06a");

        protected override Bitmap Icon => StbIcons.LineLoad;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(
                new StbElementParameter(),
                "STb Element",
                "Elem",
                "Loaded STB element.",
                GH_ParamAccess.item);
            pManager.AddIntegerParameter("LC", "LC", "Load case id.", GH_ParamAccess.item, 0);
            pManager.AddBooleanParameter(
                "Global",
                "G",
                "True: load vectors use global coordinates. False: element local coordinates.",
                GH_ParamAccess.item,
                true);
            pManager.AddVectorParameter(
                "Load i",
                "Wi",
                "Distributed load at the element i-end in kN/m.",
                GH_ParamAccess.item,
                Vector3d.Zero);
            pManager.AddVectorParameter(
                "Load j",
                "Wj",
                "Distributed load at the element j-end in kN/m.",
                GH_ParamAccess.item,
                Vector3d.Zero);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(
                new StbLoadParameter(),
                "STb Load",
                "Ld",
                "STB line load object.",
                GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbElementGoo elementGoo = null;
            int loadCase = 0;
            bool isGlobal = true;
            var loadAtI = Vector3d.Zero;
            var loadAtJ = Vector3d.Zero;

            if (!da.GetData(0, ref elementGoo) || elementGoo?.Value == null)
            {
                return;
            }

            da.GetData(1, ref loadCase);
            da.GetData(2, ref isGlobal);
            da.GetData(3, ref loadAtI);
            da.GetData(4, ref loadAtJ);

            var axis = elementGoo.Value.Line.Direction;
            if (axis.Unitize())
            {
                var axialAtI = isGlobal
                    ? Vector3d.Multiply(loadAtI, axis)
                    : loadAtI.X;
                var axialAtJ = isGlobal
                    ? Vector3d.Multiply(loadAtJ, axis)
                    : loadAtJ.X;
                if (Math.Abs(axialAtI) > 1e-9 || Math.Abs(axialAtJ) > 1e-9)
                {
                    AddRuntimeMessage(
                        GH_RuntimeMessageLevel.Warning,
                        "The STB solver currently ignores the member-axis component of ELOD.");
                }
            }

            da.SetData(0, new StbLoadGoo(new StbLoadModel
            {
                Kind = StbLoadKind.Line,
                ElementLine = elementGoo.Value.Line,
                LoadCase = loadCase,
                IsGlobal = isGlobal,
                LoadAtI = loadAtI,
                LoadAtJ = loadAtJ,
            }));
        }
    }

    public sealed class StbAreaLoadComponent : GH_Component
    {
        public StbAreaLoadComponent()
            : base(
                "STb Load",
                "STb ALoad",
                "Create an STb area load bounded by three or four frame elements.",
                StbCategories.Tab,
                StbCategories.Load)
        {
        }

        public override Guid ComponentGuid => new Guid("79badf8b-9c6c-47d7-bef5-ab1f729b89fb");

        protected override Bitmap Icon => StbIcons.AreaLoad;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(
                new StbElementParameter(),
                "STb Boundary Elements",
                "Elem",
                "Three or four STB elements forming one closed panel boundary.",
                GH_ParamAccess.list);
            pManager.AddIntegerParameter("LC", "LC", "Load case id.", GH_ParamAccess.item, 0);
            pManager.AddVectorParameter(
                "Pressure",
                "P",
                "Area-load vector in global coordinates in kN/m2.",
                GH_ParamAccess.item,
                Vector3d.Zero);
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(
                new StbLoadParameter(),
                "STb Load",
                "Ld",
                "STB area load object.",
                GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var elements = StbModelGooUtil.GetElements(da, 0);
            int loadCase = 0;
            var pressure = Vector3d.Zero;

            if (elements.Count < 3 || elements.Count > 4)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Error,
                    "Area load requires exactly 3 or 4 boundary elements.");
                return;
            }

            da.GetData(1, ref loadCase);
            da.GetData(2, ref pressure);

            var load = new StbLoadModel
            {
                Kind = StbLoadKind.Area,
                LoadCase = loadCase,
                Pressure = pressure,
            };
            foreach (var element in elements)
            {
                if (!element.Line.IsValid)
                {
                    AddRuntimeMessage(
                        GH_RuntimeMessageLevel.Error,
                        "Area-load boundary contains an invalid element line.");
                    return;
                }

                load.BoundaryLines.Add(element.Line);
            }

            da.SetData(0, new StbLoadGoo(load));
        }
    }

    public sealed class StbGravityLoadComponent : GH_Component
    {
        public StbGravityLoadComponent()
            : base(
                "STb Gravity Load",
                "STb GLoad",
                "Create an STb gravity (self-weight) load. Each member is loaded by its mass (section area x material Gamma) times the acceleration.",
                StbCategories.Tab,
                StbCategories.Load)
        {
        }

        public override Guid ComponentGuid => new Guid("3c6f0a52-7d1e-4b8a-9f35-2e8d41c7b906");

        protected override Bitmap Icon => StbIcons.GravityLoad;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddIntegerParameter("LC", "LC", "Load case id.", GH_ParamAccess.item, 0);
            pManager.AddVectorParameter(
                "Acceleration",
                "G",
                "Acceleration vector in global coordinates in m/s2. (0, 0, -9.80665) gives self weight.",
                GH_ParamAccess.item,
                new Vector3d(0.0, 0.0, -9.80665));
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbLoadParameter(), "STb Load", "Ld", "STB gravity load object.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            int loadCase = 0;
            var acceleration = new Vector3d(0.0, 0.0, -9.80665);
            da.GetData(0, ref loadCase);
            da.GetData(1, ref acceleration);

            if (acceleration.IsZero)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Acceleration is zero; the gravity load has no effect.");
            }

            da.SetData(0, new StbLoadGoo(new StbLoadModel
            {
                Kind = StbLoadKind.Gravity,
                LoadCase = loadCase,
                Acceleration = acceleration,
            }));
        }
    }

    public sealed class StbJointComponent : GH_Component
    {
        public StbJointComponent()
            : base(
                "STb Joint",
                "STb Joint",
                "Set member-end rotational springs (EJNT) on an STb element. Leave an input empty for a rigid end; 0 makes a pin.",
                StbCategories.Tab,
                StbCategories.Element)
        {
        }

        public override Guid ComponentGuid => new Guid("8e1b5d47-2a9c-4f63-b0d8-6c3e7a91f254");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.Joint;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbElementParameter(), "STb Element", "Elem", "Element to modify.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Ryi", "Ryi", "Spring about local y at the i-end in kNm/rad. Empty = rigid, 0 = pin.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Rzi", "Rzi", "Spring about local z at the i-end in kNm/rad. Empty = rigid, 0 = pin.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Ryj", "Ryj", "Spring about local y at the j-end in kNm/rad. Empty = rigid, 0 = pin.", GH_ParamAccess.item);
            pManager.AddNumberParameter("Rzj", "Rzj", "Spring about local z at the j-end in kNm/rad. Empty = rigid, 0 = pin.", GH_ParamAccess.item);
            for (var i = 1; i <= 4; i++)
            {
                pManager[i].Optional = true;
            }
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbElementParameter(), "STb Element", "Elem", "Element with EJNT springs.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            StbElementGoo elementGoo = null;
            if (!da.GetData(0, ref elementGoo) || elementGoo?.Value == null)
            {
                return;
            }

            var element = elementGoo.Value.Duplicate();
            var values = new double?[4];
            for (var i = 0; i < 4; i++)
            {
                double value = 0.0;
                if (!da.GetData(i + 1, ref value))
                {
                    continue;
                }

                if (value < 0.0 || double.IsNaN(value) || double.IsInfinity(value))
                {
                    AddRuntimeMessage(GH_RuntimeMessageLevel.Error, Params.Input[i + 1].Name + " must be zero or positive.");
                    return;
                }

                values[i] = value;
            }

            element.JointRyi = values[0];
            element.JointRzi = values[1];
            element.JointRyj = values[2];
            element.JointRzj = values[3];
            if (!element.HasJoint)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Remark, "All inputs are empty; the element stays rigid.");
            }

            da.SetData(0, new StbElementGoo(element));
        }
    }

    public sealed class StbLoadCombinationComponent : GH_Component
    {
        public StbLoadCombinationComponent()
            : base(
                "STb Load Combination",
                "STb LCMB",
                "Create an STb load combination (LCMB): LC = sum of factor x load case.",
                StbCategories.Tab,
                StbCategories.Load)
        {
        }

        public override Guid ComponentGuid => new Guid("5d2a9e80-4c7b-4f16-8a3d-91b6e0c5f723");
        public override GH_Exposure Exposure => GH_Exposure.secondary;

        protected override Bitmap Icon => StbIcons.LoadCombination;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddIntegerParameter("LC", "LC", "Combination load case id. Must differ from load cases that have loads.", GH_ParamAccess.item, 2);
            pManager.AddTextParameter("Name", "Name", "Combination name.", GH_ParamAccess.item, string.Empty);
            pManager.AddNumberParameter("Factors", "F", "Factor for each combined load case.", GH_ParamAccess.list);
            pManager.AddIntegerParameter("Load Cases", "LCs", "Load cases to combine, in the same order as Factors.", GH_ParamAccess.list);
            pManager[1].Optional = true;
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddParameter(new StbLoadParameter(), "STb Load", "Ld", "STB load combination object. Connect to STB Assemble Model Ld.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            int loadCase = 2;
            string name = string.Empty;
            var factors = new List<double>();
            var cases = new List<int>();
            da.GetData(0, ref loadCase);
            da.GetData(1, ref name);
            if (!da.GetDataList(2, factors) || !da.GetDataList(3, cases))
            {
                return;
            }

            if (factors.Count != cases.Count)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Factors and Load Cases must have the same length.");
                return;
            }

            if (cases.Contains(loadCase))
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "A combination cannot include its own load case LC" + loadCase + ".");
                return;
            }

            var load = new StbLoadModel
            {
                Kind = StbLoadKind.Combination,
                LoadCase = loadCase,
                CombinationName = name ?? string.Empty,
            };
            load.CombinationFactors.AddRange(factors);
            load.CombinationCases.AddRange(cases);
            da.SetData(0, new StbLoadGoo(load));
        }
    }

    public sealed class StbAssembleModelComponent : GH_Component
    {
        public StbAssembleModelComponent() : base("STB Assemble Model", "STb Model", "Assemble typed STB model objects into a .dat text file.", StbCategories.Tab, StbCategories.Assemble) { }
        public override Guid ComponentGuid => new Guid("ce8a157a-b1b7-4d92-918f-e6ce2294af1c");

        protected override Bitmap Icon => StbIcons.Assemble;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbElementParameter(), "STb Element", "Elem", "STB elements.", GH_ParamAccess.list);
            pManager.AddParameter(new StbLoadParameter(), "STb Load", "Ld", "STB loads.", GH_ParamAccess.list);
            pManager.AddParameter(new StbSupportParameter(), "STb Support", "Sup", "STB supports.", GH_ParamAccess.list);
            pManager.AddTextParameter("DAT", "DAT", "Output .dat path. Empty uses the temp folder.", GH_ParamAccess.item, string.Empty);
            pManager.AddBooleanParameter("Write", "Write", "Write the .dat file.", GH_ParamAccess.item, false);
            pManager.AddGenericParameter("Results", "R", "Optional parsed results to store in STb Model.", GH_ParamAccess.item);
            Params.Input[1].Optional = true;
            Params.Input[2].Optional = true;
            Params.Input[3].Optional = true;
            Params.Input[5].Optional = true;
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddTextParameter("Text", "Text", "Assembled STB input text.", GH_ParamAccess.item);
            pManager.AddTextParameter("DAT", "DAT", "Resolved .dat path. Populated when Write is true.", GH_ParamAccess.item);
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "Typed model and optional results for STB components.", GH_ParamAccess.item);
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var elements = StbModelGooUtil.GetElements(da, 0);
            var loads = StbModelGooUtil.GetLoads(da, 1);
            var supports = StbModelGooUtil.GetSupports(da, 2);
            string datPath = string.Empty;
            bool write = false;
            StbParsedResults results = null;
            da.GetData(3, ref datPath);
            da.GetData(4, ref write);
            StbModelGooUtil.TryGetResults(da, 5, out results);

            if (elements.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "At least one element is required.");
                return;
            }

            var tolerance = RhinoDoc.ActiveDoc?.ModelAbsoluteTolerance ?? 0.001;

            StbAssembleResult assembleResult;
            try
            {
                assembleResult = StbModelAssembler.Assemble(elements, loads, supports, tolerance);
            }
            catch (InvalidOperationException ex)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Error, ex.Message);
                return;
            }

            if (assembleResult.MergedNodeCount > 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Remark,
                    "Merged "
                    + assembleResult.MergedNodeCount
                    + " duplicate node(s) at tolerance "
                    + StbRecord.Number(tolerance)
                    + ".");
            }

            var writtenPath = string.Empty;
            if (write)
            {
                try
                {
                    writtenPath = StbPathUtil.WriteTextFile(datPath, assembleResult.Text);
                }
                catch (Exception ex)
                {
                    AddRuntimeMessage(GH_RuntimeMessageLevel.Error, "Failed to write .dat file: " + ex.Message);
                    return;
                }
            }
            else
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Remark,
                    "Write is false. Set Write to true before connecting DAT to STB Analyze.");
            }

            da.SetData(0, assembleResult.Text);
            da.SetData(1, writtenPath);
            var model = new StbModelModel();
            model.Elements.AddRange(elements);
            model.Supports.AddRange(supports);
            model.Loads.AddRange(loads);
            model.Results = results;
            model.DatText = assembleResult.Text;
            model.DatPath = writtenPath;
            da.SetData(2, new StbModelGoo(model));
        }
    }
}
