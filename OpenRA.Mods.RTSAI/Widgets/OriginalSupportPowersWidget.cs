using System;
using System.Collections.Generic;
using System.Reflection;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.RTSAI.Rendering;
using OpenRA.Primitives;

namespace OpenRA.Mods.RTSAI.Widgets
{
	// Keep the engine's input, charge, targeting and tooltip behavior. Only the
	// prepared sprite/palette pair changes for original-country players.
	public sealed class OriginalSupportPowersWidget : SupportPowersWidget
	{
		static readonly FieldInfo Icons = typeof(SupportPowersWidget).GetField("icons", BindingFlags.Instance | BindingFlags.NonPublic);
		readonly WorldRenderer renderer;
		readonly FactionSupportPowerIconsInfo mapping;
		readonly bool original;
		Dictionary<Rectangle, SupportPowerIcon> lastIcons;

		public static void CheckCompatibility()
		{
			if (Icons == null || Icons.FieldType != typeof(Dictionary<Rectangle, SupportPowerIcon>))
				throw new InvalidOperationException("Native support-power icon adapter needs review for this engine version.");
		}

		[ObjectCreator.UseCtor]
		public OriginalSupportPowersWidget(ModData modData, World world, WorldRenderer worldRenderer)
			: base(modData, world, worldRenderer)
		{
			renderer = worldRenderer;
			mapping = world.LocalPlayer.PlayerActor.Info.TraitInfoOrDefault<FactionSupportPowerIconsInfo>();
			original = mapping != null && mapping.Factions.Contains(world.LocalPlayer.Faction.InternalName);
			CheckCompatibility();
			if (Environment.GetEnvironmentVariable("RTSAI_ORIGINAL_ART_VERIFY") == "1")
				Console.WriteLine($"RTSAI_ORIGINAL_POWER_UI|{world.LocalPlayer.Faction.InternalName}|mapping={mapping != null}|original={original}");
		}

		public override void Draw()
		{
			if (original)
			{
				var icons = (Dictionary<Rectangle, SupportPowerIcon>)Icons.GetValue(this);
				if (!ReferenceEquals(icons, lastIcons))
				{
					lastIcons = icons;
					foreach (var prepared in icons.Values)
					{
						var power = prepared.Power.Info;
						if (power.IconImage != mapping.SourceImage || !renderer.World.Map.Sequences.HasSequence(mapping.Image, power.Icon))
							continue;
						var animation = new Animation(renderer.World, mapping.Image);
						animation.Play(power.Icon);
						prepared.Sprite = animation.Image;
						prepared.Palette = renderer.Palette(mapping.Palette);
						if (Environment.GetEnvironmentVariable("RTSAI_ORIGINAL_ART_VERIFY") == "1")
							Console.WriteLine($"RTSAI_ORIGINAL_POWER_ICON|{mapping.Image}|{power.Icon}|{mapping.Palette}");
					}
				}
			}
			base.Draw();
		}
	}
}
