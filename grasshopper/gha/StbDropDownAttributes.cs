using System;
using System.Drawing;
using System.Windows.Forms;
using Grasshopper.GUI;
using Grasshopper.GUI.Canvas;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Attributes;

namespace StbGrasshopper
{
    /// <summary>A component that exposes one choice through a body drop-down.</summary>
    internal interface IStbDropDownOwner
    {
        int DropDownCount { get; }
        int DropDownSelection { get; }
        string DropDownName(int index);
        void SetDropDownSelection(int index);
    }

    /// <summary>
    /// Adds a drop-down strip below the component body.
    /// </summary>
    internal sealed class StbDropDownAttributes : GH_ComponentAttributes
    {
        private static readonly Color DropDownColor = Color.FromArgb(70, 76, 82);
        private readonly GH_Component _component;
        private readonly IStbDropDownOwner _owner;
        private RectangleF _dropDownBounds;

        public StbDropDownAttributes(GH_Component component, IStbDropDownOwner owner)
            : base(component)
        {
            _component = component;
            _owner = owner;
        }

        protected override void Layout()
        {
            base.Layout();

            const float stripHeight = 25f;
            const float margin = 4f;
            const float dropDownPadding = 34f;

            var original = Bounds;
            var longestName = 0;
            for (var index = 0; index < _owner.DropDownCount; index++)
            {
                longestName = Math.Max(
                    longestName,
                    GH_FontServer.StringWidth(_owner.DropDownName(index), GH_FontServer.Standard));
            }

            // base.Layout() has already sized the component for the current
            // input/output labels. Only enlarge it when the drop-down needs
            // more room.
            var dropDownWidth = longestName + dropDownPadding;
            var width = Math.Max(original.Width, dropDownWidth + margin * 2f);
            var left = original.X - (width - original.Width) * 0.5f;
            Bounds = new RectangleF(left, original.Y, width, original.Height + stripHeight);

            // Keep Grasshopper's standard label-to-socket spacing. Move each
            // complete parameter attribute to the new edge instead of asking
            // the layout helpers to expand the label regions outwards.
            var inputOffset = Bounds.Left - original.Left;
            foreach (var input in _component.Params.Input)
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
            foreach (var output in _component.Params.Output)
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

            _dropDownBounds = new RectangleF(
                Bounds.Left + margin,
                original.Bottom + 3f,
                Bounds.Width - margin * 2f,
                18f);
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

            using (var fill = new SolidBrush(DropDownColor))
            using (var border = new Pen(Color.FromArgb(45, 50, 55), 1f))
            using (var textBrush = new SolidBrush(Color.White))
            using (var format = new StringFormat
            {
                Alignment = StringAlignment.Near,
                LineAlignment = StringAlignment.Center,
            })
            {
                graphics.FillRectangle(fill, _dropDownBounds);
                graphics.DrawRectangle(
                    border,
                    _dropDownBounds.X,
                    _dropDownBounds.Y,
                    _dropDownBounds.Width,
                    _dropDownBounds.Height);

                var textBounds = _dropDownBounds;
                textBounds.X += 6f;
                textBounds.Width -= 22f;
                graphics.DrawString(
                    _owner.DropDownName(_owner.DropDownSelection),
                    SystemFonts.MessageBoxFont,
                    textBrush,
                    textBounds,
                    format);

                var arrowX = _dropDownBounds.Right - 12f;
                var arrowY = _dropDownBounds.Top + _dropDownBounds.Height * 0.5f;
                graphics.FillPolygon(
                    textBrush,
                    new[]
                    {
                        new PointF(arrowX - 4f, arrowY - 2f),
                        new PointF(arrowX + 4f, arrowY - 2f),
                        new PointF(arrowX, arrowY + 3f),
                    });
            }
        }

        public override GH_ObjectResponse RespondToMouseDown(
            GH_Canvas sender,
            GH_CanvasMouseEvent e)
        {
            if (e.Button != MouseButtons.Left || !_dropDownBounds.Contains(e.CanvasLocation))
            {
                return base.RespondToMouseDown(sender, e);
            }

            var menu = new ContextMenuStrip();
            AppendChoices(menu, _owner);
            menu.Show(sender, e.ControlLocation);
            return GH_ObjectResponse.Handled;
        }

        /// <summary>
        /// Adds one checked item per choice. Shared by the body drop-down and the
        /// component's right-click menu, so a choice can still be made where the
        /// drop-down cannot be opened.
        /// </summary>
        internal static void AppendChoices(ToolStrip menu, IStbDropDownOwner owner)
        {
            for (var index = 0; index < owner.DropDownCount; index++)
            {
                var selected = index;
                // Per-item Click handlers, as Grasshopper's own menus use: the
                // Windows Forms layer of Rhino for Mac does not raise
                // ToolStrip.ItemClicked.
                GH_DocumentObject.Menu_AppendItem(
                    menu,
                    owner.DropDownName(index),
                    (_, __) => RunWhenIdle(() => owner.SetDropDownSelection(selected)),
                    true,
                    index == owner.DropDownSelection);
            }
        }

        /// <summary>
        /// Runs the action once Rhino is idle, i.e. after the menu has closed.
        /// Rebuilding component parameters while the menu is still dispatching
        /// its click can be ignored on some Rhino 8 builds, and Control.BeginInvoke
        /// is not dependable on Rhino for Mac.
        /// </summary>
        private static void RunWhenIdle(Action action)
        {
            EventHandler handler = null;
            handler = (_, __) =>
            {
                Rhino.RhinoApp.Idle -= handler;
                action();
            };
            Rhino.RhinoApp.Idle += handler;
        }
    }
}
