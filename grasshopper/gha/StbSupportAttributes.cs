using System;
using System.Drawing;
using Grasshopper.GUI;
using Grasshopper.GUI.Canvas;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Attributes;

namespace StbGrasshopper
{
    /// <summary>
    /// Adds six independent restraint toggles to the Support component body.
    /// Blue means restrained; grey means free.
    /// </summary>
    internal sealed class StbSupportAttributes : GH_ComponentAttributes
    {
        // Each label is drawn as a letter followed by a lowered, smaller subscript.
        private static readonly string[] Letters = { "T", "T", "T", "R", "R", "R" };
        private static readonly string[] Subscripts = { "x", "y", "z", "x", "y", "z" };
        private static readonly Color ActiveColor = Color.FromArgb(0, 174, 227);
        private static readonly Color InactiveColor = Color.FromArgb(110, 116, 122);

        private readonly StbSupportComponent _owner;
        private readonly RectangleF[] _buttons = new RectangleF[Letters.Length];

        public StbSupportAttributes(StbSupportComponent owner)
            : base(owner)
        {
            _owner = owner;
        }

        protected override void Layout()
        {
            base.Layout();

            const int columnCount = 3;
            const int rowCount = 2;
            const float margin = 4f;
            const float gap = 2f;

            // Size the buttons from the font so the subscript is never clipped,
            // whatever font size the OS or Grasshopper is configured with.
            var buttonHeight = Math.Max(17f, GH_FontServer.StandardAdjusted.Height + 4f);
            var stripHeight = 3f + rowCount * buttonHeight + (rowCount - 1) * gap + 4f;

            var original = Bounds;
            Bounds = new RectangleF(
                original.X,
                original.Y,
                original.Width,
                original.Height + stripHeight);

            var inputOffset = Bounds.Left - original.Left;
            foreach (var input in _owner.Params.Input)
            {
                if (input.Attributes == null)
                {
                    continue;
                }

                var parameterBounds = input.Attributes.Bounds;
                parameterBounds.Offset(inputOffset, 0f);
                input.Attributes.Bounds = parameterBounds;

                var pivot = input.Attributes.Pivot;
                input.Attributes.Pivot = new PointF(pivot.X + inputOffset, pivot.Y);
            }

            var outputOffset = Bounds.Right - original.Right;
            foreach (var output in _owner.Params.Output)
            {
                if (output.Attributes == null)
                {
                    continue;
                }

                var parameterBounds = output.Attributes.Bounds;
                parameterBounds.Offset(outputOffset, 0f);
                output.Attributes.Bounds = parameterBounds;

                var pivot = output.Attributes.Pivot;
                output.Attributes.Pivot = new PointF(pivot.X + outputOffset, pivot.Y);
            }

            var availableWidth = Bounds.Width - margin * 2f - gap * (columnCount - 1);
            var buttonWidth = availableWidth / columnCount;

            for (var i = 0; i < _buttons.Length; i++)
            {
                var row = i / columnCount;
                var column = i % columnCount;
                _buttons[i] = new RectangleF(
                    Bounds.Left + margin + column * (buttonWidth + gap),
                    original.Bottom + 3f + row * (buttonHeight + gap),
                    buttonWidth,
                    buttonHeight);
            }
        }

        protected override void Render(
            GH_Canvas canvas,
            Graphics graphics,
            GH_CanvasChannel channel)
        {
            base.Render(canvas, graphics, channel);

            if (channel != GH_CanvasChannel.Objects)
            {
                return;
            }

            using (var border = new Pen(Color.FromArgb(75, 80, 85), 1f))
            using (var textBrush = new SolidBrush(Color.White))
            {
                for (var i = 0; i < _buttons.Length; i++)
                {
                    using (var fill = new SolidBrush(
                        _owner.IsRestrained(i) ? ActiveColor : InactiveColor))
                    {
                        graphics.FillRectangle(fill, _buttons[i]);
                    }

                    graphics.DrawRectangle(
                        border,
                        _buttons[i].X,
                        _buttons[i].Y,
                        _buttons[i].Width,
                        _buttons[i].Height);
                    DrawSubscriptLabel(graphics, Letters[i], Subscripts[i], textBrush, _buttons[i]);
                }
            }
        }

        private static void DrawSubscriptLabel(
            Graphics graphics,
            string letter,
            string subscript,
            Brush brush,
            RectangleF bounds)
        {
            var letterFont = GH_FontServer.StandardAdjusted;
            var subscriptFont = GH_FontServer.Small;
            var fit = FitScale(graphics, letter, subscript, letterFont, subscriptFont, bounds);
            if (fit >= 1f)
            {
                DrawSubscriptLabel(graphics, letter, subscript, letterFont, subscriptFont, brush, bounds);
                return;
            }

            // Shrink both glyphs when a narrow button cannot hold them.
            using (var smallLetter = GH_FontServer.NewFont(letterFont, letterFont.Size * fit))
            using (var smallSubscript = GH_FontServer.NewFont(subscriptFont, subscriptFont.Size * fit))
            {
                DrawSubscriptLabel(graphics, letter, subscript, smallLetter, smallSubscript, brush, bounds);
            }
        }

        private static float FitScale(
            Graphics graphics,
            string letter,
            string subscript,
            Font letterFont,
            Font subscriptFont,
            RectangleF bounds)
        {
            var size = MeasureLabel(graphics, letter, subscript, letterFont, subscriptFont, out _, out _);
            return Math.Min(1f, Math.Min((bounds.Width - 2f) / size.Width, (bounds.Height - 2f) / size.Height));
        }

        private static void DrawSubscriptLabel(
            Graphics graphics,
            string letter,
            string subscript,
            Font letterFont,
            Font subscriptFont,
            Brush brush,
            RectangleF bounds)
        {
            var size = MeasureLabel(graphics, letter, subscript, letterFont, subscriptFont, out var letterWidth, out var drop);
            var left = bounds.Left + (bounds.Width - size.Width) * 0.5f;
            var top = bounds.Top + (bounds.Height - size.Height) * 0.5f;
            var format = StringFormat.GenericTypographic;
            graphics.DrawString(letter, letterFont, brush, left, top, format);
            graphics.DrawString(subscript, subscriptFont, brush, left + letterWidth, top + drop, format);
        }

        private static SizeF MeasureLabel(
            Graphics graphics,
            string letter,
            string subscript,
            Font letterFont,
            Font subscriptFont,
            out float letterWidth,
            out float drop)
        {
            var format = StringFormat.GenericTypographic;
            var letterSize = graphics.MeasureString(letter, letterFont, PointF.Empty, format);
            var subscriptSize = graphics.MeasureString(subscript, subscriptFont, PointF.Empty, format);
            letterWidth = letterSize.Width;
            drop = letterSize.Height * 0.3f;
            return new SizeF(
                letterSize.Width + subscriptSize.Width,
                Math.Max(letterSize.Height, drop + subscriptSize.Height));
        }

        public override GH_ObjectResponse RespondToMouseDown(
            GH_Canvas sender,
            GH_CanvasMouseEvent e)
        {
            for (var i = 0; i < _buttons.Length; i++)
            {
                if (_buttons[i].Contains(e.CanvasLocation))
                {
                    _owner.ToggleRestraint(i);
                    return GH_ObjectResponse.Handled;
                }
            }

            return base.RespondToMouseDown(sender, e);
        }
    }
}
