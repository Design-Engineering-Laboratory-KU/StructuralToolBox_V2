using System;
using System.Collections.Generic;

namespace StbGrasshopper
{
    public sealed class StbAnalyzeResult
    {
        public bool Success { get; set; }
        public int ExitCode { get; set; }
        public string DatPath { get; set; } = string.Empty;
        public string OutPath { get; set; } = string.Empty;
        public string Stdout { get; set; } = string.Empty;
        public string Stderr { get; set; } = string.Empty;
        public string Summary { get; set; } = string.Empty;
        public StbParsedResults Results { get; set; } = new StbParsedResults();
    }

    public sealed class StbParsedResults
    {
        public string DatPath { get; set; } = string.Empty;
        public List<NodalDisplacement> Displacements { get; } = new List<NodalDisplacement>();
        public List<ReactionForce> Reactions { get; } = new List<ReactionForce>();
        public List<ElementForce> ElementForces { get; } = new List<ElementForce>();
        public List<ElementLoadSegment> ElementLoadSegments { get; } = new List<ElementLoadSegment>();
        public List<StbSectionProperties> Sections { get; } = new List<StbSectionProperties>();
        public List<StbNodeGeometry> Nodes { get; } = new List<StbNodeGeometry>();
        public List<StbElementGeometry> Elements { get; } = new List<StbElementGeometry>();

        private Dictionary<(int LoadCase, int ElementId), List<ElementLoadSegment>> _loadSegmentLookup;
        private int _loadSegmentLookupCount = -1;

        public IReadOnlyList<ElementLoadSegment> GetElementLoadSegments(int loadCase, int elementId)
        {
            if (_loadSegmentLookup == null || _loadSegmentLookupCount != ElementLoadSegments.Count)
            {
                _loadSegmentLookup = new Dictionary<(int LoadCase, int ElementId), List<ElementLoadSegment>>();
                foreach (var segment in ElementLoadSegments)
                {
                    var key = (segment.LoadCase, segment.ElementId);
                    if (!_loadSegmentLookup.TryGetValue(key, out var list))
                    {
                        list = new List<ElementLoadSegment>();
                        _loadSegmentLookup.Add(key, list);
                    }

                    list.Add(segment);
                }

                _loadSegmentLookupCount = ElementLoadSegments.Count;
            }

            return _loadSegmentLookup.TryGetValue((loadCase, elementId), out var segments)
                ? segments
                : Array.Empty<ElementLoadSegment>();
        }
    }

    public sealed class NodalDisplacement
    {
        public int LoadCase { get; set; }
        public int NodeId { get; set; }
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
        public double ThetaX { get; set; }
        public double ThetaY { get; set; }
        public double ThetaZ { get; set; }
    }

    public sealed class ReactionForce
    {
        public int LoadCase { get; set; }
        public int NodeId { get; set; }
        public double Tx { get; set; }
        public double Ty { get; set; }
        public double Tz { get; set; }
        public double Rx { get; set; }
        public double Ry { get; set; }
        public double Rz { get; set; }
    }

    public sealed class ElementForce
    {
        public int LoadCase { get; set; }
        public int ElementId { get; set; }
        public double Ni { get; set; }
        public double Qyi { get; set; }
        public double Qzi { get; set; }
        public double Mxi { get; set; }
        public double Myi { get; set; }
        public double Mzi { get; set; }
        public double Nj { get; set; }
        public double Qyj { get; set; }
        public double Qzj { get; set; }
        public double Mxj { get; set; }
        public double Myj { get; set; }
        public double Mzj { get; set; }
        public double Myc { get; set; }
        public double Mzc { get; set; }
    }

    public sealed class ElementLoadSegment
    {
        public int LoadCase { get; set; }
        public int ElementId { get; set; }
        public double T0 { get; set; }
        public double T1 { get; set; }
        public double WXi { get; set; }
        public double WYi { get; set; }
        public double WZi { get; set; }
        public double WXj { get; set; }
        public double WYj { get; set; }
        public double WZj { get; set; }
    }

    public sealed class StbSectionProperties
    {
        public int SectionId { get; set; }
        public double Area { get; set; }
        public double Wy { get; set; }
        public double Wz { get; set; }
    }
}
