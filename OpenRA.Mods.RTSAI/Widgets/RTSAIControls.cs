using System.Numerics;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Primitives;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets
{
	static class RTSAIControlSurface
	{
		public static void Draw(Rectangle rect, bool disabled, bool pressed, bool hover, bool accent)
		{
			var border = disabled ? Color.FromArgb(255, 41, 55, 64) : hover ? Color.FromArgb(255, 100, 209, 212) : Color.FromArgb(255, 61, 82, 94);
			var fill = accent && !disabled ? Color.FromArgb(255, 100, 209, 212) : pressed ? Color.FromArgb(255, 23, 49, 58) : hover ? Color.FromArgb(255, 35, 57, 68) : Color.FromArgb(255, 25, 40, 50);
			Game.Renderer.RgbaColorRenderer.FillRect(new Vector3(rect.Left, rect.Top, 0), new Vector3(rect.Right, rect.Bottom, 0), border);
			Game.Renderer.RgbaColorRenderer.FillRect(new Vector3(rect.Left + 1, rect.Top + 1, 0), new Vector3(rect.Right - 1, rect.Bottom - 1, 0), fill);
		}
	}

	public sealed class RTSAIButtonWidget : ButtonWidget
	{
		public bool Accent;
		[ObjectCreator.UseCtor]
		public RTSAIButtonWidget(ModData modData) : base(modData) { }
		RTSAIButtonWidget(RTSAIButtonWidget other) : base(other) { Accent = other.Accent; }
		public override ButtonWidget Clone() => new RTSAIButtonWidget(this);
		public override void DrawBackground(Rectangle rect, bool disabled, bool pressed, bool hover, bool highlighted) => RTSAIControlSurface.Draw(rect, disabled, pressed, hover, Accent || highlighted);
	}

	public sealed class RTSAIDropDownButtonWidget : DropDownButtonWidget
	{
		[ObjectCreator.UseCtor]
		public RTSAIDropDownButtonWidget(ModData modData) : base(modData) { }
		RTSAIDropDownButtonWidget(RTSAIDropDownButtonWidget other) : base(other) { }
		public override DropDownButtonWidget Clone() => new RTSAIDropDownButtonWidget(this);
		public override void DrawBackground(Rectangle rect, bool disabled, bool pressed, bool hover, bool highlighted) => RTSAIControlSurface.Draw(rect, disabled, pressed, hover, false);
	}

	public sealed class RTSAIPanelWidget : BackgroundWidget
	{
		public RTSAIPanelWidget() { }
		RTSAIPanelWidget(RTSAIPanelWidget other) : base(other) { }
		public override BackgroundWidget Clone() => new RTSAIPanelWidget(this);
		public override void Draw()
		{
			var r = RenderBounds;
			Game.Renderer.RgbaColorRenderer.FillRect(new Vector3(r.Left, r.Top, 0), new Vector3(r.Right, r.Bottom, 0), Color.FromArgb(255, 20, 31, 39));
		}
	}

	public sealed class RTSAIScrollItemWidget : ScrollItemWidget
	{
		[ObjectCreator.UseCtor]
		public RTSAIScrollItemWidget(ModData modData) : base(modData) { }
		RTSAIScrollItemWidget(RTSAIScrollItemWidget other) : base(other) { }
		public override ScrollItemWidget Clone() => new RTSAIScrollItemWidget(this);
		public override void Draw()
		{
			var selected = IsSelected() || IsHighlighted();
			RTSAIControlSurface.Draw(RenderBounds, IsDisabled(), Depressed, Ui.MouseOverWidget == this || selected, false);
			if (selected)
			{
				var r = RenderBounds;
				Game.Renderer.RgbaColorRenderer.FillRect(new Vector3(r.Left, r.Top, 0), new Vector3(r.Left + 3, r.Bottom, 0), Color.FromArgb(255, 100, 209, 212));
			}
		}
	}
}
