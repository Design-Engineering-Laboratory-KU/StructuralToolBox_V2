using System;
using System.Collections.Generic;
using System.Linq;
using Rhino.Geometry;

namespace StbGrasshopper
{
    internal sealed class StbMeshAreaExpansion
    {
        public List<StbLoadModel> Loads { get; } = new List<StbLoadModel>();
        public List<string> Warnings { get; } = new List<string>();
        public List<string> Remarks { get; } = new List<string>();
    }

    /// <summary>
    /// Turns area loads from a mesh into ordinary area loads: the model elements
    /// lying on the mesh divide it into panels, and each panel bounded by 3 or 4
    /// elements becomes one area load (ALOD).
    /// </summary>
    internal static class StbMeshAreaLoads
    {
        /// <summary>Returns the loads with every mesh area load replaced by its panel loads.</summary>
        public static StbMeshAreaExpansion Expand(
            IReadOnlyList<StbElementModel> elements,
            IEnumerable<StbLoadModel> loads,
            double documentTolerance)
        {
            var result = new StbMeshAreaExpansion();
            foreach (var load in loads)
            {
                if (load?.Kind == StbLoadKind.MeshArea)
                {
                    result.Loads.AddRange(Panels(elements, load, documentTolerance, result));
                }
                else
                {
                    result.Loads.Add(load);
                }
            }

            return result;
        }

        private static List<StbLoadModel> Panels(
            IReadOnlyList<StbElementModel> elements,
            StbLoadModel load,
            double documentTolerance,
            StbMeshAreaExpansion result)
        {
            var label = "Area load from mesh LC" + load.LoadCase;
            var loads = new List<StbLoadModel>();
            var meshes = load.Meshes
                .Where(m => m != null && m.IsValid && m.Faces.Count > 0)
                .Select(PrepareMesh)
                .ToList();
            if (meshes.Count == 0)
            {
                result.Warnings.Add(label + " has no valid mesh.");
                return loads;
            }

            var tolerance = load.MeshTolerance > 0.0 ? load.MeshTolerance : documentTolerance;
            var wanted = new HashSet<string>(
                load.ElementNames.Where(n => !string.IsNullOrWhiteSpace(n)).Select(n => n.Trim()),
                StringComparer.Ordinal);
            var found = new HashSet<string>(StringComparer.Ordinal);
            var lines = new List<Line>();
            foreach (var element in elements ?? Array.Empty<StbElementModel>())
            {
                if (element == null || !element.Line.IsValid)
                {
                    continue;
                }

                var name = element.Name?.Trim() ?? string.Empty;
                if (wanted.Count == 0 || wanted.Contains(name))
                {
                    lines.Add(element.Line);
                    found.Add(name);
                }
            }

            var missing = wanted.Where(n => !found.Contains(n)).ToList();
            if (missing.Count > 0)
            {
                result.Warnings.Add(label + ": no element named " + string.Join(", ", missing) + ".");
            }

            var panels = new List<StbPanel>();
            var skipped = new List<StbPanel>();
            StbPanelFinder.Find(lines, p => NormalOnMeshes(meshes, p, tolerance), tolerance, panels, skipped);

            foreach (var panel in panels)
            {
                var panelLoad = new StbLoadModel
                {
                    Kind = StbLoadKind.Area,
                    LoadCase = load.LoadCase,
                    Pressure = load.Pressure,
                };
                foreach (var index in panel.LineIndices)
                {
                    panelLoad.BoundaryLines.Add(lines[index]);
                }

                loads.Add(panelLoad);
            }

            if (panels.Count == 0)
            {
                result.Warnings.Add(
                    label + ": no panel found. Check that the elements lie on the mesh (Tolerance) and form closed loops.");
            }
            else
            {
                result.Remarks.Add(label + ": " + panels.Count + " panel(s) loaded.");
            }

            if (skipped.Count > 0)
            {
                result.Warnings.Add(
                    label + ": " + skipped.Count + " panel(s) have more than 4 boundary elements and get no load. "
                    + "Split them with an extra element, or load them with STb Line Load.");
            }

            return loads;
        }

        private static Mesh PrepareMesh(Mesh source)
        {
            var mesh = source.DuplicateMesh();
            mesh.FaceNormals.ComputeFaceNormals();
            return mesh;
        }

        private static Vector3d NormalOnMeshes(List<Mesh> meshes, Point3d point, double tolerance)
        {
            foreach (var mesh in meshes)
            {
                var hit = mesh.ClosestMeshPoint(point, tolerance);
                if (hit != null && hit.FaceIndex >= 0)
                {
                    return new Vector3d(mesh.FaceNormals[hit.FaceIndex]);
                }
            }

            return Vector3d.Unset;
        }
    }
}
