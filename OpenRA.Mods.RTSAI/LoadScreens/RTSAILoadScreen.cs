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
using System.Linq;
using System.Numerics;
using OpenRA.FileSystem;
using OpenRA.Graphics;
using OpenRA.Mods.Common.LoadScreens;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.RTSAI.Companion;
using OpenRA.Primitives;

namespace OpenRA.Mods.RTSAI.LoadScreens
{
	/// <summary>
	/// The upstream logo-and-stripe load screen (LogoStripeLoadScreen is sealed, so its drawing is
	/// repeated here), plus the AI companion lifecycle: the sidecar starts when the mod starts and
	/// stops when the mod is disposed on exit. Below the stripe it shows one faction tip at a time, generated from the
	/// shared faction catalog (tools/faction-loading-tips.py writes modern-factions/loading-tips.ftl).
	/// </summary>
	public sealed class RTSAILoadScreen : SheetLoadScreen
	{
		[FluentReference]
		const string Loading = "loadscreen-loading";

		[FluentReference]
		const string FactionTips = "loadscreen-faction-tips";

		// Long enough to read a tip; a tip changes only on long loads.
		const int TipMilliseconds = 7000;

		Rectangle stripeRect;
		Vector2 logoPos;
		Sprite stripe, logo;

		Sheet lastSheet;
		int lastDensity;
		Size lastResolution;

		string[] messages = [];
		string[] tips = [];
		int firstTip;
		long tipsShownSince;

		public override void Init(Manifest manifest, IReadOnlyFileSystem fileSystem)
		{
			base.Init(manifest, fileSystem);

			messages = FluentProvider.GetMessage(Loading).Split(',').Select(x => x.Trim()).ToArray();
			if (FluentProvider.TryGetMessage(FactionTips, out var factionTips))
				tips = factionTips.Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

			firstTip = tips.Length > 0 ? Game.CosmeticRandom.Next(tips.Length) : 0;
			tipsShownSince = Game.RunTime;
		}

		public override void StartGame(Arguments args)
		{
			// Before the first world: the companion bridge reads the ports chosen here.
			CompanionHost.Initialize(Game.ModData);
			base.StartGame(args);
		}

		public override void DisplayInner(Renderer r, Sheet s, int density)
		{
			if (s != lastSheet || density != lastDensity)
			{
				lastSheet = s;
				lastDensity = density;
				logo = CreateSprite(s, density, new Rectangle(0, 0, 256, 256));
				stripe = CreateSprite(s, density, new Rectangle(258, 0, 253, 256));
			}

			if (r.Resolution != lastResolution)
			{
				lastResolution = r.Resolution;
				stripeRect = new Rectangle(0, lastResolution.Height / 2 - 128, lastResolution.Width, 256);
				logoPos = new Vector2(lastResolution.Width / 2 - 128, lastResolution.Height / 2 - 128);
			}

			if (stripe != null)
				WidgetUtils.FillRectWithSprite(stripeRect, stripe);

			if (logo != null)
				r.RgbaSpriteRenderer.DrawSprite(logo, logoPos.AsVector3());

			if (r.Fonts != null && messages.Length > 0)
			{
				var text = messages.Random(Game.CosmeticRandom);
				var textSize = r.Fonts["Bold"].Measure(text);
				r.Fonts["Bold"].DrawText(text, new Vector2(r.Resolution.Width - textSize.X - 20, r.Resolution.Height - textSize.Y - 20), Color.White);
			}

			if (r.Fonts != null && tips.Length > 0)
			{
				var font = r.Fonts["Bold"];
				var tip = tips[(firstTip + (int)((Game.RunTime - tipsShownSince) / TipMilliseconds)) % tips.Length];
				var y = stripeRect.Bottom + 24;
				foreach (var line in WidgetUtils.WrapText(tip, Math.Max(lastResolution.Width - 80, 200), font).Split('\n'))
				{
					var lineSize = font.Measure(line);
					font.DrawText(line, new Vector2((lastResolution.Width - lineSize.X) / 2, y), Color.White);
					y += lineSize.Y + 4;
				}
			}
		}

		protected override void Dispose(bool disposing)
		{
			if (disposing)
				CompanionHost.Shutdown();

			base.Dispose(disposing);
		}
	}
}
