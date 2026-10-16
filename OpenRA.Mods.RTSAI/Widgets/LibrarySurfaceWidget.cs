using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Primitives;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets
{
	// A native, resolution-independent surface. Every interactive target remains an
	// OpenRA widget; illustrations contain no baked controls or text.
	public sealed class LibrarySurfaceWidget : ContainerWidget
	{
		public static readonly Color Ink = Color.FromArgb(12, 16, 18);
		public static readonly Color Cream = Color.FromArgb(239, 231, 209);
		public static readonly Color Muted = Color.FromArgb(177, 181, 179);
		public static readonly Color Amber = Color.FromArgb(237, 173, 62);
		public static readonly Color LineColor = Color.FromArgb(70, 79, 79);
		public Action RenderContent = () => { };
		public Action OnTick = () => { };
		public Action<int> OnScroll = _ => { };
		public Action OnBack = () => { };
		public bool Quiet;
		public float Scale { get; private set; } = 1;
		public Vector2 Origin { get; private set; }
		readonly Dictionary<Widget, Rectangle> layout = new();
		int focusIndex = -1;
		static readonly int[] Sizes = { 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 40, 48, 56, 64, 72, 80, 96 };

		public void Place(Widget widget, int x, int y, int width, int height)
		{
			layout[widget] = new Rectangle(x, y, width, height);
			AddChild(widget);
			Layout();
		}
		public void Clear()
		{
			RemoveChildren(); layout.Clear(); focusIndex = -1;
		}
		void Layout()
		{
			var size = Game.Renderer.Resolution;
			Bounds = new WidgetBounds(0, 0, size.Width, size.Height);
			Scale = Math.Min(size.Width / 1920f, size.Height / 1080f);
			Origin = new Vector2((size.Width - 1920 * Scale) / 2, (size.Height - 1080 * Scale) / 2);
			foreach (var pair in layout)
			{
				var r = pair.Value;
				pair.Key.Bounds = new WidgetBounds((int)(Origin.X + r.X * Scale), (int)(Origin.Y + r.Y * Scale),
					(int)(r.Width * Scale), (int)(r.Height * Scale));
			}
		}
		public override void Tick() { Layout(); OnTick(); base.Tick(); }
		public override void Draw()
		{
			Layout();
			Image("frontline", "backdrop", 0, 0, 1920, 1080);
			Rect(0, 0, 1920, 1080, Color.FromArgb(Quiet ? 232 : 130, 8, 12, 14));
			RenderContent();
		}
		public Vector2 Point(float x, float y) => Origin + new Vector2(x, y) * Scale;
		public SpriteFont FontFor(int size, bool display = false) => Game.Renderer.Fonts[(display ? "FrontlinePlay" : "FrontlineMenu") + Sizes.MinBy(s => Math.Abs(s - size * Scale))];
		public void Text(float x, float y, string text, int size = 24, Color? color = null, int width = 0, bool display = false)
		{
			var font = FontFor(size, display);
			if (width > 0) text = WidgetUtils.WrapText(text ?? "", (int)(width * Scale), font);
			font.DrawText(text ?? "", Point(x, y), color ?? Cream);
		}
		public void Rect(float x, float y, float width, float height, Color color)
		{
			var a = Point(x, y); var b = Point(x + width, y + height);
			Game.Renderer.RgbaColorRenderer.FillRect(new Vector3(a.X, a.Y, 0), new Vector3(b.X, b.Y, 0), color);
		}
		public void Rule(float x, float y, float width, Color? color = null) => Rect(x, y, width, 1.5f, color ?? LineColor);
		public void Frame(float x, float y, float width, float height, Color color)
		{
			Rect(x, y, width, 2, color); Rect(x, y + height - 2, width, 2, color);
			Rect(x, y, 2, height, color); Rect(x + width - 2, y, 2, height, color);
		}
		public void Image(string collection, string name, float x, float y, float width, float height)
		{
			Game.Renderer.EnableAntialiasingFilter();
			WidgetUtils.DrawSprite(ChromeProvider.GetImage(collection, name), Point(x, y), new Vector2(width, height) * Scale);
			Game.Renderer.DisableAntialiasingFilter();
		}
		public LibraryActionWidget Button(ModData mod, string id, string text, int x, int y, int width, int height, Action action, bool primary = false)
		{
			var button = new LibraryActionWidget(mod) { Id = id, Surface = this, Primary = primary, GetText = () => text, OnClick = action };
			Place(button, x, y, width, height);
			return button;
		}
		public override bool HandleMouseInput(MouseInput mi)
		{
			if (mi.Event == MouseInputEvent.Scroll) OnScroll(mi.Delta.Y > 0 ? -1 : 1);
			return true;
		}
		public override bool HandleKeyPress(KeyInput e)
		{
			if (e.Event != KeyInputEvent.Down) return false;
			if (e.Key == Keycode.ESCAPE) { OnBack(); return true; }
			var buttons = Children.OfType<LibraryActionWidget>().Where(b => b.IsVisible() && !b.IsDisabled()).ToArray();
			if (e.Key == Keycode.TAB && buttons.Length > 0)
			{
				focusIndex = (focusIndex + (e.Modifiers.HasModifier(Modifiers.Shift) ? buttons.Length - 1 : 1)) % buttons.Length;
				foreach (var b in buttons) b.KeyboardFocused = false;
				buttons[focusIndex].KeyboardFocused = true;
				return true;
			}
			if ((e.Key == Keycode.RETURN || e.Key == Keycode.SPACE) && focusIndex >= 0 && focusIndex < buttons.Length)
			{
				buttons[focusIndex].OnClick(); return true;
			}
			if (e.Key == Keycode.PAGEDOWN || e.Key == Keycode.DOWN) { OnScroll(1); return true; }
			if (e.Key == Keycode.PAGEUP || e.Key == Keycode.UP) { OnScroll(-1); return true; }
			return false;
		}
	}

	public sealed class LibraryActionWidget : ButtonWidget
	{
		public LibrarySurfaceWidget Surface;
		public bool Primary, Flat, KeyboardFocused, Invisible;
		public int TextSize = 26;
		public LibraryActionWidget(ModData modData) : base(modData) { }
		public override void Draw()
		{
			if (Invisible) return;
			var r = RenderBounds;
			var hover = Ui.MouseOverWidget == this || KeyboardFocused;
			var selected = IsHighlighted();
			var disabled = IsDisabled();
			var color = Primary ? LibrarySurfaceWidget.Cream : Color.FromArgb(228, 15, 21, 24);
			if (!Flat || hover || selected)
			{
				Game.Renderer.RgbaColorRenderer.FillRect(new Vector3(r.Left, r.Top, 0), new Vector3(r.Right, r.Bottom, 0), color);
				var border = hover || selected ? LibrarySurfaceWidget.Amber : LibrarySurfaceWidget.LineColor;
				Game.Renderer.RgbaColorRenderer.DrawRect(new Vector3(r.Left, r.Top, 0), new Vector3(r.Right, r.Bottom, 0), 1, border);
			}
			var font = Surface.FontFor(TextSize);
			var text = GetText();
			var size = font.Measure(text);
			font.DrawText(text, new Vector2(r.Left + (r.Width - size.X) / 2f, r.Top + (r.Height - size.Y) / 2f),
				disabled ? LibrarySurfaceWidget.Muted : Primary ? LibrarySurfaceWidget.Ink : hover || selected ? LibrarySurfaceWidget.Amber : LibrarySurfaceWidget.Cream);
		}
	}
}
