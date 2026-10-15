using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Primitives;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets
{
	// Authored against the selected 1672 x 941 composition. Reflow from the original
	// coordinates, rather than repeatedly scaling rounded bounds after a resize.
	public sealed class FrontlineCanvasWidget : ContainerWidget
	{
		readonly Dictionary<Widget, WidgetBounds> designBounds = new();
		int2 previousSize;

		public override void Tick()
		{
			var size = new int2(Game.Renderer.Resolution.Width, Game.Renderer.Resolution.Height);
			if (size == previousSize)
				return;

			previousSize = size;
			Bounds = new WidgetBounds(0, 0, size.X, size.Y);
			var scale = Math.Min(size.X / 1672f, size.Y / 941f);
			var x = (size.X - 1672 * scale) / 2;
			var y = (size.Y - 941 * scale) / 2;
			foreach (var child in Children)
			{
				if (!designBounds.TryGetValue(child, out var bounds))
					designBounds.Add(child, bounds = child.Bounds);
				child.Bounds = new WidgetBounds((int)Math.Round(x + bounds.X * scale),
					(int)Math.Round(y + bounds.Y * scale), (int)Math.Round(bounds.Width * scale),
					(int)Math.Round(bounds.Height * scale));
				if (child is FrontlineButtonWidget button)
					button.LayoutScale = scale;
			}
		}
	}

	public sealed class FrontlineImageWidget : ImageWidget
	{
		public override void Draw()
		{
			Game.Renderer.EnableAntialiasingFilter();
			WidgetUtils.DrawSprite(GetSprite(), RenderOrigin.ToVector2(), RenderBounds.Size);
			Game.Renderer.DisableAntialiasingFilter();
		}
	}

	// These remain ordinary OpenRA buttons: real hit targets, hotkeys, sound and
	// disabled states. Only their rendering differs from the in-game controls.
	public sealed class FrontlineButtonWidget : ButtonWidget
	{
		public readonly bool Primary;
		public readonly bool Mode;
		public readonly bool Compact;
		public readonly int DesignFontSize = 28;
		public float LayoutScale = 1;
		static readonly int[] FontSizes = { 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 40, 48, 56, 64, 72, 80, 96 };

		[ObjectCreator.UseCtor]
		public FrontlineButtonWidget(ModData modData) : base(modData) { }

		FrontlineButtonWidget(FrontlineButtonWidget other) : base(other)
		{
			Primary = other.Primary;
			Mode = other.Mode;
			Compact = other.Compact;
			DesignFontSize = other.DesignFontSize;
			LayoutScale = other.LayoutScale;
		}

		public override ButtonWidget Clone() => new FrontlineButtonWidget(this);

		public override void Draw()
		{
			var r = RenderBounds;
			var hover = Ui.MouseOverWidget == this;
			var disabled = IsDisabled();
			var selected = IsHighlighted();
			var fontSize = FontSizes.MinBy(s => Math.Abs(s - DesignFontSize * LayoutScale));
			var font = Game.Renderer.Fonts[(Primary ? "FrontlinePlay" : "FrontlineMenu") + fontSize];
			var text = GetText();
			var tracking = (Primary ? 5 : Compact ? 1 : 2) * LayoutScale;
			var color = disabled ? Color.FromArgb(100, 100, 95) : Primary ? Color.FromArgb(12, 15, 15)
				: hover ? Color.FromArgb(255, 191, 83) : selected ? Color.FromArgb(255, 245, 224) : Color.FromArgb(195, 192, 181);

			if (Primary)
			{
				var sprite = OpenRA.Graphics.ChromeProvider.GetImage("frontline-assets", "play");
				Game.Renderer.EnableAntialiasingFilter();
				WidgetUtils.DrawSprite(sprite, new Vector2(r.Left, r.Top + (Depressed ? 2 : 0)), r.Size);
				Game.Renderer.DisableAntialiasingFilter();
				var arrow = OpenRA.Graphics.ChromeProvider.GetImage("frontline-icons", "chevron");
				WidgetUtils.DrawSprite(arrow, new Vector2(r.Right - 65 * LayoutScale, r.Top + 30 * LayoutScale),
					new Vector2(19, 31) * LayoutScale);
				if (hover)
					Game.Renderer.RgbaColorRenderer.FillRect(new Vector3(r.Left + 12 * LayoutScale, r.Bottom - 5 * LayoutScale, 0),
						new Vector3(r.Right - 12 * LayoutScale, r.Bottom - 2 * LayoutScale, 0), Color.FromArgb(242, 168, 46));
			}

			var width = text.Sum(c => font.Measure(c.ToString()).X) + Math.Max(0, text.Length - 1) * tracking;
			var pos = new Vector2(Mode ? r.Left + (r.Width - width) / 2 : r.Left + (Primary ? 36 : 0) * LayoutScale,
				r.Top + (r.Height - font.Measure(text).Y - font.TopOffset) / 2 + (Depressed ? 2 : 0));
			foreach (var c in text)
			{
				font.DrawText(c.ToString(), pos, color);
				pos.X += font.Measure(c.ToString()).X + tracking;
			}

			if (Mode && (selected || hover))
			{
				var lineHeight = Math.Max(2, (int)(3 * LayoutScale));
				Game.Renderer.RgbaColorRenderer.FillRect(new Vector3(r.Left + 8 * LayoutScale, r.Bottom - lineHeight, 0),
					new Vector3(r.Right - 8 * LayoutScale, r.Bottom, 0), selected ? Color.FromArgb(242, 168, 46) : Color.FromArgb(161, 123, 73));
			}
			else if (hover && !Primary)
				Game.Renderer.RgbaColorRenderer.FillRect(new Vector3(r.Left - 13 * LayoutScale, r.Top + r.Height / 3f, 0),
					new Vector3(r.Left - 10 * LayoutScale, r.Top + 2 * r.Height / 3f, 0), Color.FromArgb(242, 168, 46));
		}
	}
}
