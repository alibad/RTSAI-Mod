#region Copyright & License Information
/*
 * Copyright (c) The OpenRA Developers and Contributors
 * This file is part of OpenRA, which is free software. It is made
 * available to you under the terms of the GNU General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version. For more
 * information, see COPYING.
 */
#endregion

using System;
using System.Numerics;
using OpenRA.Mods.Common.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets
{
	/// <summary>
	/// A chrome image scaled to cover the widget's bounds (aspect kept, centred, overflow cropped): the main menu's
	/// full-window backdrop at any window size. FocusX moves the crop window horizontally (0 = keep the left edge,
	/// 1 = keep the right edge).
	/// </summary>
	public class CoverImageWidget : ImageWidget
	{
		public readonly float FocusX = 0.5f;

		public CoverImageWidget() { }

		protected CoverImageWidget(CoverImageWidget other)
			: base(other)
		{
			FocusX = other.FocusX;
		}

		public override CoverImageWidget Clone() { return new CoverImageWidget(this); }

		public override void Draw()
		{
			var sprite = GetSprite();
			if (sprite == null || sprite.Size.X <= 0 || sprite.Size.Y <= 0)
				return;

			var rb = RenderBounds;
			var scale = Math.Max(rb.Width / sprite.Size.X, rb.Height / sprite.Size.Y);
			var size = new Vector2(sprite.Size.X * scale, sprite.Size.Y * scale);
			var origin = new Vector2(rb.X + (rb.Width - size.X) * FocusX, rb.Y + (rb.Height - size.Y) / 2);

			Game.Renderer.EnableScissor(rb);
			WidgetUtils.DrawSprite(sprite, origin, size);
			Game.Renderer.DisableScissor();
		}
	}
}
