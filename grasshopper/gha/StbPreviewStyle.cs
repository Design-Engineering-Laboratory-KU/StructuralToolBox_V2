using System;
using System.Drawing;
using Grasshopper.Kernel;
using Rhino.Display;
using Rhino.Geometry;

namespace StbGrasshopper
{
    /// <summary>
    /// Shared viewport text and arrow-head sizing for the preview components.
    /// Sizes are given at 96 DPI and scaled up on high-resolution displays.
    /// </summary>
    internal static class StbPreviewStyle
    {
        public const int DefaultTextSize = 14;
        public const double DefaultArrowSize = 1.0;

        private const double ArrowHeadPixels = 12.0;

        public const string TextSizeDescription = "Height of the value labels in screen pixels (at 100% display scaling).";
        public const string ArrowSizeDescription = "Arrow head size factor. 1 = default, 2 = twice as large.";

        public static int ReadTextSize(IGH_DataAccess da, int index, GH_Component owner)
        {
            var size = DefaultTextSize;
            da.GetData(index, ref size);
            if (size <= 0)
            {
                owner.AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Text Size must be positive; using " + DefaultTextSize + ".");
                return DefaultTextSize;
            }

            return size;
        }

        public static double ReadArrowSize(IGH_DataAccess da, int index, GH_Component owner)
        {
            var size = DefaultArrowSize;
            da.GetData(index, ref size);
            if (!(size > 0.0))
            {
                owner.AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "Arrow Size must be positive; using 1.");
                return DefaultArrowSize;
            }

            return size;
        }

        public static void DrawText(DisplayPipeline display, string text, Color color, Point3d point, int textSize)
        {
            var height = (int)Math.Round(textSize * DpiScale(display));
            display.Draw2dText(text, color, point, true, Math.Max(1, height));
        }

        public static void DrawArrow(DisplayPipeline display, Line line, Color color, double arrowSize)
        {
            display.DrawArrow(line, color, ArrowHeadPixels * arrowSize * DpiScale(display), 0.0);
        }

        /// <summary>
        /// Double-headed moment arrow; <paramref name="headSize"/> is in model units.
        /// </summary>
        public static void DrawMomentArrow(DisplayPipeline display, Line line, Color color, double headSize, double arrowSize)
        {
            var direction = line.Direction;
            direction.Unitize();
            var size = headSize * arrowSize;
            display.DrawLine(line, color, 2);
            display.DrawArrowHead(line.To, direction, color, 0.0, size);
            display.DrawArrowHead(line.To - direction * size * 0.6, direction, color, 0.0, size);
        }

        private static double DpiScale(DisplayPipeline display)
        {
            var scale = display.DpiScale;
            return scale > 0.0 ? scale : 1.0;
        }
    }
}
