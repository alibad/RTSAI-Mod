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
	/// A chrome image scaled to cover the widget's bounds (aspect kept, overflow cropped): the main menu's full-window
	/// backdrop at any window size. When the window is narrower than the image, the horizontal crop keeps the image
	/// columns SafeLeft..SafeRight (image pixels) centred in the part of the widget that InsetLeft pixels of other
	/// widgets do not cover; without a safe range, FocusX places the crop (0 = keep the left edge, 1 = the right edge).
	/// </summary>
	public class CoverImageWidget : ImageWidget
	{
		public readonly float FocusX = 0.5f;
		public readonly int SafeLeft = -1;
		public readonly int SafeRight = -1;
		public readonly int InsetLeft = 0;

		public CoverImageWidget() { }

		protected CoverImageWidget(CoverImageWidget other)
			: base(other)
		{
			FocusX = other.FocusX;
			SafeLeft = other.SafeLeft;
			SafeRight = other.SafeRight;
			InsetLeft = other.InsetLeft;
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
			var x = rb.X + (rb.Width - size.X) * FocusX;
			if (SafeRight > SafeLeft && SafeLeft >= 0)
			{
				var target = rb.X + InsetLeft + (rb.Width - InsetLeft) / 2f;
				// keep the image covering the widget (no Math.Clamp: rounding can leave min a hair above max)
				x = Math.Max(Math.Min(target - (SafeLeft + SafeRight) / 2f * scale, rb.X), rb.Right - size.X);
			}

			var origin = new Vector2(x, rb.Y + (rb.Height - size.Y) / 2);

			Game.Renderer.EnableScissor(rb);
			WidgetUtils.DrawSprite(sprite, origin, size);
			Game.Renderer.DisableScissor();
		}
	}
}
