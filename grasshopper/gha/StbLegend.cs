using System;
using System.Drawing;
using System.Globalization;
using Grasshopper.Kernel;
using Rhino.Geometry;

namespace StbGrasshopper
{
    /// <summary>
    /// Shared contour palette and viewport legend for the result preview components,
    /// so model colors and legend bands always match across components.
    /// </summary>
    internal static class StbLegend
    {
        public const int Bands = 7;

        private static readonly Color[] Palette =
        {
            Color.FromArgb(35, 70, 180),
            Color.FromArgb(35, 120, 220),
            Color.FromArgb(0, 190, 220),
            Color.FromArgb(35, 170, 90),
            Color.FromArgb(245, 220, 40),
            Color.FromArgb(245, 145, 25),
            Color.FromArgb(215, 35, 35),
        };

        private static readonly Color TextColor = Color.FromArgb(55, 60, 65);
        private const int Width = 210;
        private const int Margin = 18;
        private const int TitleHeight = 38;
        private const int BarOffset = 14;
        private const int BarWidth = 24;
        private const int BarHeight = 252;
        private const int TickLength = 5;
        private const int TextSize = 14;

        public static Color ColorFor(double normalized)
        {
            if (double.IsNaN(normalized) || double.IsInfinity(normalized))
            {
                return Palette[0];
            }

            var t = Math.Max(0.0, Math.Min(1.0, normalized));
            return Palette[Math.Min(Bands - 1, (int)Math.Floor(t * Bands))];
        }

        /// <summary>Draws a 0..maximum legend at the right edge, vertically centered.</summary>
        public static void Draw(IGH_PreviewArgs args, string title, double maximum)
        {
            var display = args.Display;
            var viewport = args.Viewport.Bounds;
            var left = Math.Max(viewport.Left + 8, viewport.Right - Width - Margin);
            var top = Math.Max(viewport.Top + 8, viewport.Top + (viewport.Height - TitleHeight - BarHeight) / 2);
            var barLeft = left + BarOffset;
            var barTop = top + TitleHeight;

            display.Draw2dText(title, TextColor, new Point2d(left + 10, top + 11), false, TextSize);

            for (var i = 0; i < Bands; i++)
            {
                var y0 = barTop + i * BarHeight / Bands;
                var y1 = barTop + (i + 1) * BarHeight / Bands;
                var color = Palette[Bands - 1 - i];
                display.Draw2dRectangle(new Rectangle(barLeft, y0, BarWidth, y1 - y0), color, 0, color);
            }

            display.Draw2dRectangle(new Rectangle(barLeft, barTop, BarWidth, BarHeight), TextColor, 1, Color.Transparent);

            var decimals = Decimals(maximum);
            var tickLeft = barLeft + BarWidth;
            for (var i = 0; i <= Bands; i++)
            {
                var y = barTop + i * BarHeight / Bands;
                var value = maximum * (Bands - i) / Bands;
                display.Draw2dLine(
                    new System.Drawing.Point(tickLeft, y),
                    new System.Drawing.Point(tickLeft + TickLength, y),
                    TextColor,
                    1f);
                display.Draw2dText(
                    value.ToString("F" + decimals, CultureInfo.InvariantCulture),
                    TextColor,
                    new Point2d(tickLeft + TickLength + 5, y - 5),
                    false,
                    TextSize);
            }
        }

        private static int Decimals(double maximum)
        {
            if (!(maximum > 0.0) || double.IsInfinity(maximum))
            {
                return 1;
            }

            var magnitude = (int)Math.Floor(Math.Log10(maximum));
            return Math.Max(0, Math.Min(6, 2 - magnitude));
        }
    }
}
