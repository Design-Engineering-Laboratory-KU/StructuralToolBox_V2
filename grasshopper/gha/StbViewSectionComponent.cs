using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Linq;
using Grasshopper.Kernel;
using Rhino.Display;
using Rhino.Geometry;

namespace StbGrasshopper
{
    public sealed class StbViewSectionComponent : GH_Component
    {
        private const double Zero = 1e-9;
        private const int DefaultSegments = 12;
        private const int MinSegments = 6;
        private const int MaxSegments = 64;

        private static readonly Color[] Palette =
        {
            Color.FromArgb(120, 160, 200),
            Color.FromArgb(214, 150, 90),
            Color.FromArgb(130, 180, 120),
            Color.FromArgb(200, 120, 130),
            Color.FromArgb(160, 140, 200),
            Color.FromArgb(210, 190, 100),
            Color.FromArgb(110, 175, 180),
            Color.FromArgb(180, 150, 120),
            Color.FromArgb(150, 160, 170),
            Color.FromArgb(220, 160, 180),
        };

        private static readonly Color EdgeColor = Color.FromArgb(45, 50, 55);

        // Section name -> member meshes, in order of first appearance; one combined
        // preview mesh per section keeps the viewport to a few draw calls.
        private readonly Dictionary<string, List<Mesh>> _pending = new Dictionary<string, List<Mesh>>();
        private readonly List<string> _sectionOrder = new List<string>();
        private readonly List<(Mesh Mesh, DisplayMaterial Material)> _previews = new List<(Mesh Mesh, DisplayMaterial Material)>();
        private readonly List<Line> _edges = new List<Line>();
        private BoundingBox _clippingBox = BoundingBox.Empty;
        private bool _showEdges = true;

        public StbViewSectionComponent()
            : base(
                "View Section",
                "View Sec",
                "Display STB members with their section shape as closed meshes between the start and end nodes.",
                StbCategories.Tab,
                StbCategories.Info)
        {
        }

        public override Guid ComponentGuid => new Guid("88e9347f-aaf8-4752-b6d8-4252ce760941");
        protected override Bitmap Icon => StbIcons.ViewSection;
        public override BoundingBox ClippingBox => _clippingBox;

        protected override void RegisterInputParams(GH_InputParamManager pManager)
        {
            pManager.AddParameter(new StbModelParameter(), "STb Model", "STb Model", "STb Model whose members are displayed.", GH_ParamAccess.item);
            pManager.AddParameter(new StbElementParameter(), "Element", "Elem", "Additional STb Element objects, e.g. before assembling the model.", GH_ParamAccess.list);
            pManager.AddIntegerParameter(
                "Segments",
                "N",
                "Polygon segments for circular sections (" + MinSegments + "-" + MaxSegments + "). Fewer is faster.",
                GH_ParamAccess.item,
                DefaultSegments);
            pManager.AddBooleanParameter("Edges", "E", "Draw section outlines and member edges in the viewport.", GH_ParamAccess.item, true);
            pManager[0].Optional = true;
            pManager[1].Optional = true;
        }

        protected override void RegisterOutputParams(GH_OutputParamManager pManager)
        {
            pManager.AddMeshParameter("Meshes", "M", "One closed mesh per member, from its start node to its end node.", GH_ParamAccess.list);
            pManager.AddTextParameter("Sections", "S", "Section name of each mesh.", GH_ParamAccess.list);
        }

        protected override void BeforeSolveInstance()
        {
            _pending.Clear();
            _sectionOrder.Clear();
            _previews.Clear();
            _edges.Clear();
            _clippingBox = BoundingBox.Empty;
            base.BeforeSolveInstance();
        }

        protected override void SolveInstance(IGH_DataAccess da)
        {
            var elements = new List<StbElementModel>();
            StbModelGoo modelGoo = null;
            if (da.GetData(0, ref modelGoo) && modelGoo?.Value != null)
            {
                elements.AddRange(modelGoo.Value.Elements.Where(e => e != null));
            }

            var elementGoos = new List<StbElementGoo>();
            da.GetDataList(1, elementGoos);
            elements.AddRange(elementGoos.Where(g => g?.Value != null).Select(g => g.Value));
            if (elements.Count == 0)
            {
                AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Connect an STb Model or STb Element objects.");
                return;
            }

            var segments = DefaultSegments;
            var showEdges = true;
            da.GetData(2, ref segments);
            da.GetData(3, ref showEdges);
            segments = Math.Max(MinSegments, Math.Min(MaxSegments, segments));
            _showEdges = showEdges;

            var profiles = new Dictionary<string, StbSectionSolid>();
            var meshes = new List<Mesh>();
            var sectionNames = new List<string>();
            var skipped = new List<string>();
            var simplified = new SortedSet<string>(StringComparer.Ordinal);
            foreach (var element in elements)
            {
                var line = element.Line;
                var section = element.Section;
                if (!line.IsValid || line.Length <= Zero || section == null)
                {
                    skipped.Add(element.Name);
                    continue;
                }

                var key = ProfileKey(section, segments);
                if (!profiles.TryGetValue(key, out var profile))
                {
                    profile = StbSectionSolid.Create(section.Type, section.Dimensions, segments);
                    profiles[key] = profile;
                }

                if (profile == null)
                {
                    skipped.Add(element.Name);
                    continue;
                }

                if (profile.IsSimplified)
                {
                    simplified.Add(section.Name);
                }

                var mesh = profile.BuildMesh(line, element.Beta, showEdges ? _edges : null);
                meshes.Add(mesh);
                sectionNames.Add(section.Name);
                AddPreview(section.Name, mesh);
            }

            if (skipped.Count > 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Warning,
                    skipped.Count + " member(s) skipped: zero length, no section, or invalid section dimensions ("
                    + string.Join(", ", skipped.Distinct().Take(5)) + (skipped.Count > 5 ? ", ..." : string.Empty) + ").");
            }

            if (simplified.Count > 0)
            {
                AddRuntimeMessage(
                    GH_RuntimeMessageLevel.Remark,
                    "Walls too thick for a hole; drawn solid: " + string.Join(", ", simplified) + ".");
            }

            da.SetDataList(0, meshes);
            da.SetDataList(1, sectionNames);
        }

        protected override void AfterSolveInstance()
        {
            for (var i = 0; i < _sectionOrder.Count; i++)
            {
                var combined = new Mesh();
                combined.Append(_pending[_sectionOrder[i]]);
                _previews.Add((combined, new DisplayMaterial(Palette[i % Palette.Length])));
                _clippingBox.Union(combined.GetBoundingBox(false));
            }

            _pending.Clear();
            base.AfterSolveInstance();
        }

        public override void DrawViewportMeshes(IGH_PreviewArgs args)
        {
            foreach (var (mesh, material) in _previews)
            {
                args.Display.DrawMeshShaded(mesh, Attributes.Selected ? args.ShadeMaterial_Selected : material);
            }
        }

        public override void DrawViewportWires(IGH_PreviewArgs args)
        {
            if (_showEdges && _edges.Count > 0)
            {
                args.Display.DrawLines(_edges, Attributes.Selected ? args.WireColour_Selected : EdgeColor, 1);
            }
        }

        private void AddPreview(string sectionName, Mesh mesh)
        {
            var name = sectionName ?? string.Empty;
            if (!_pending.TryGetValue(name, out var list))
            {
                list = new List<Mesh>();
                _pending[name] = list;
                _sectionOrder.Add(name);
            }

            list.Add(mesh);
        }

        private static string ProfileKey(StbSectionModel section, int segments)
        {
            return section.Type.ToString(CultureInfo.InvariantCulture)
                + ":" + segments.ToString(CultureInfo.InvariantCulture)
                + ":" + string.Join(",", section.Dimensions.Select(d => d.ToString("R", CultureInfo.InvariantCulture)));
        }
    }
}
