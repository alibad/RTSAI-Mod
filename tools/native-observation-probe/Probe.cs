using System;
using System.Linq;
using System.Text.Json;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.RTSAI.Traits
{
	[TraitLocation(SystemActors.World)]
	public sealed class NativeObservationProbeInfo : TraitInfo
	{
		public readonly bool DisableBasePower = false;
		public override object Create(ActorInitializer init) => new NativeObservationProbe(this);
	}

	public sealed class NativeObservationProbe : ITick
	{
		readonly NativeObservationProbeInfo info;
		bool complete;
		public NativeObservationProbe(NativeObservationProbeInfo info) { this.info = info; }
		static void Require(bool value, string message)
		{
			if (!value) throw new InvalidOperationException(message);
		}
		void ITick.Tick(Actor self)
		{
			var world = self.World;
			if (complete || world.WorldTick < 20) return;
			complete = true;
			var player = world.Players.Single(p => p.InternalName == "Saudi Arabia");
			var refinery = world.Actors.First(a => a.Owner == player && a.Info.Name == "garefn");
			var power = refinery.TraitsImplementing<Power>().ToArray();
			Require(power.Length == 2, "Actual refinery must have base and purifier Power traits");
			var hospital = world.CreateActor(true, "cahosp", new TypeDictionary
			{
				new OwnerInit(player), new LocationInit(new CPos(40, 20)), new FactionInit(player.Faction.InternalName)
			});
			Require(!hospital.TraitsImplementing<Power>().Any(), "Hospital must exercise no-Power semantics");
			var serializer = new ObservationSerializer(world, player, "native-observation-probe");
			var beforeHash = world.SyncHash();
			var baseline = serializer.Serialize(world.WorldTick);
			Require(beforeHash == world.SyncHash(), "Observation changed synchronized world state");
			var building = baseline.Buildings.Single(b => b.ActorId == refinery.ActorID);
			Require(building.PowerAmount == (info.DisableBasePower ? 0 : -50), "Baseline includes disabled power or loses enabled base");
			Require(building.IsPowered == !info.DisableBasePower, "All-disabled power status incorrect");
			var noPower = baseline.Buildings.Single(b => b.ActorId == hospital.ActorID);
			Require(noPower.PowerAmount == 0 && noPower.IsPowered, "No-Power building status incorrect");
			var token = refinery.GrantCondition("purified");
			var purified = serializer.Serialize(world.WorldTick).Buildings.Single(b => b.ActorId == refinery.ActorID);
			Require(purified.PowerAmount == (info.DisableBasePower ? -50 : -100) && purified.IsPowered,
				"Enabled purifier must aggregate with enabled base only");
			refinery.RevokeCondition(token);
			Require(serializer.Serialize(world.WorldTick).Buildings.Single(b => b.ActorId == refinery.ActorID).PowerAmount == building.PowerAmount,
				"Revoked condition retained stale power");
			var settings = Game.Settings.GetOrCreate<RTSAISettings>(null);
			var previous = settings.VoiceLanguage;
			var voiceHash = world.SyncHash();
			var voices = world.Actors.SelectMany(a => a.TraitsImplementing<IVoiced>().Select(v => (Actor: a, Voice: v))).ToArray();
			Require(voices.Length > 0, "World must contain actual voiced actors");
			foreach (var preference in new[] { "faction", "en", "invalid" })
			{
				settings.VoiceLanguage = preference;
				foreach (var item in voices)
				{
					item.Voice.HasVoice(item.Actor, "Select");
					item.Voice.PlayVoice(item.Actor, "Select", item.Actor.Owner.Faction.InternalName);
				}
				Require(world.SyncHash() == voiceHash, "Voice presentation preference changed world hash");
			}
			settings.VoiceLanguage = previous;
			Console.WriteLine("NATIVE_OBSERVATION_PROBE|" + JsonSerializer.Serialize(new
			{
				passed = true, profile = Game.ModData.Manifest.Id, tick = world.WorldTick,
				disableBasePower = info.DisableBasePower, actualPowerTraits = power.Length,
				baselinePower = building.PowerAmount, purifiedPower = purified.PowerAmount,
				noPowerIsPowered = noPower.IsPowered, observationHashUnchanged = true,
				voiceHashUnchanged = true, voiceActors = voices.Length, providerCalls = 0
			}));
			Game.Exit();
		}
	}
}
