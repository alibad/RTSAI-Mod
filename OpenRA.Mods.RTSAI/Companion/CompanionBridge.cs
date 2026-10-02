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
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;
using RLProto = OpenRA.Mods.RTSAI.RL;

namespace OpenRA.Mods.RTSAI.Traits
{
	[Desc("Publishes read-only, fog-respecting local-player observations for OpenRA AI.")]
	[TraitLocation(SystemActors.World | SystemActors.EditorWorld)]
	public sealed class RTSAICompanionBridgeInfo : TraitInfo
	{
		[Desc("Number of game ticks between snapshots.")]
		public readonly int ObservationInterval = 10;

		public override object Create(ActorInitializer init) { return new RTSAICompanionBridge(this, init); }
	}

	/// <summary>
	/// Captures observations on the game thread, then serves immutable clones
	/// through the existing gRPC host. Separately confirmed actions are validated
	/// on the game thread and queued without pausing play.
	/// </summary>
	public sealed class RTSAICompanionBridge : ITick, INotifyCreated, INotifyActorDisposing
	{
		static readonly object CurrentLock = new();
		static readonly HashSet<RLProto.ActionType> AllowedActions =
		[
			RLProto.ActionType.Move,
			RLProto.ActionType.AttackMove,
			RLProto.ActionType.Attack,
			RLProto.ActionType.Stop,
			RLProto.ActionType.Harvest,
			RLProto.ActionType.Build,
			RLProto.ActionType.Train,
			RLProto.ActionType.Deploy,
			RLProto.ActionType.Sell,
			RLProto.ActionType.Repair,
			RLProto.ActionType.PlaceBuilding,
			RLProto.ActionType.CancelProduction,
			RLProto.ActionType.SetRallyPoint,
			RLProto.ActionType.Guard,
			RLProto.ActionType.SetStance,
			RLProto.ActionType.EnterTransport,
			RLProto.ActionType.Disguise,
			RLProto.ActionType.Infiltrate,
			RLProto.ActionType.Demolish,
			RLProto.ActionType.Capture,
			RLProto.ActionType.Unload,
			RLProto.ActionType.PowerDown,
			RLProto.ActionType.SetPrimary,
			RLProto.ActionType.UseSupportPower
		];
		const int MaxCommandsPerRequest = 12;
		const int MaxPendingRequests = 8;
		const int MaxRememberedRequests = 128;
		const int MaxSnapshotAgeTicks = 125;
		const long SpokenStatusTimeoutMilliseconds = 12000;
		const long ErrorStatusTimeoutMilliseconds = 4000;
		static RTSAICompanionBridge current;
		static RLProto.CompanionStatus companionStatus = ReadyStatus();
		static RLProto.CompanionThreat companionThreat = CalmThreat();
		static long companionStatusUpdatedAt = Environment.TickCount64;

		readonly RTSAICompanionBridgeInfo info;
		readonly World world;
		readonly string episodeId = Guid.NewGuid().ToString("N")[..12];
		readonly object observationLock = new();
		readonly object actionLock = new();
		readonly ConcurrentQueue<PendingActionRequest> pendingActions = new();
		readonly Dictionary<string, Task<RLProto.CompanionActionReceipt>> actionRequests = [];
		readonly Queue<string> completedActionRequests = [];

		ObservationSerializer serializer;
		ActionHandler actionHandler;
		ModularBot assistantBot;
		Actor assistantPlayerActor;
		int assistantConditionToken = Actor.InvalidConditionToken;
		string activeAssistantStrategy = "";
		bool assistantAutoRequested;
		bool companionStatusAcknowledged;
		string assistantStrategyRequested = "normal";
		RLProto.GameObservation latestObservation;
		RLProto.GameState latestState;
		bool enabled;

		sealed class PendingActionRequest
		{
			public readonly RLProto.CompanionActionRequest Request;
			public readonly TaskCompletionSource<RLProto.CompanionActionReceipt> Completion =
				new(TaskCreationOptions.RunContinuationsAsynchronously);

			public PendingActionRequest(RLProto.CompanionActionRequest request)
			{
				Request = request;
			}
		}

		public RTSAICompanionBridge(RTSAICompanionBridgeInfo info, ActorInitializer init)
		{
			this.info = info;
			world = init.World;
		}

		void INotifyCreated.Created(Actor self)
		{
			enabled = world.Type == WorldType.Regular
				&& Environment.GetEnvironmentVariable("OPENRA_AI_COMPANION") == "1"
				&& !world.IsReplay;
			if (!enabled)
				return;

			var startup = StartupState(Environment.GetEnvironmentVariable);

			lock (CurrentLock)
			{
				current = this;
				companionStatusAcknowledged = startup.Ready;
				assistantAutoRequested = startup.Ready && startup.Enabled && startup.AutoAct;
				assistantStrategyRequested = NormalizeAssistantStrategy(startup.Strategy);
				companionStatus = startup.Ready
					? StartupStatus(startup.Enabled, startup.Muted, assistantAutoRequested, assistantStrategyRequested)
					: ReadyStatus();
				companionThreat = CalmThreat();
				companionStatusUpdatedAt = Environment.TickCount64;
			}

			var port = 9998;
			var envPort = Environment.GetEnvironmentVariable("OPENRA_AI_GRPC_PORT");
			if (!string.IsNullOrEmpty(envPort) && int.TryParse(envPort, out var configuredPort))
				port = configuredPort;

			var thread = new Thread(() => RTSAIExternalBotBridge.StartGrpcServer(port))
			{
				IsBackground = true,
				Name = "OpenRA-AI-Companion-gRPC"
			};
			thread.Start();
			Log.Write("rl-bridge", $"OpenRA AI companion enabled on port {port} (trait {GetType().FullName} from {GetType().Assembly.GetName().Name})");
		}

		void ITick.Tick(Actor self)
		{
			if (!enabled)
				return;

			SyncNativeAssistant();
			ProcessPendingActions();

			if (world.LocalPlayer == null || world.LocalPlayer.Spectating
				|| world.WorldTick % Math.Max(1, info.ObservationInterval) != 0)
				return;

			serializer ??= new ObservationSerializer(world, world.LocalPlayer, episodeId);
			var observation = serializer.Serialize(world.WorldTick);
			var state = BuildState();
			lock (observationLock)
			{
				latestObservation = observation;
				latestState = state;
			}
		}

		static string NormalizeAssistantStrategy(string value)
		{
			value = value?.Trim().ToLowerInvariant() ?? "";
			return value switch
			{
				"rush" => "rush",
				"turtle" => "turtle",
				"naval" => "naval",
				"medium" => "medium",
				// Adaptive starts from OpenRA's richest general-purpose profile.
				// The companion can move it to a specialist profile at a strategy event.
				"adaptive" => "normal",
				_ => "normal"
			};
		}

		public static (bool Ready, bool Enabled, bool Muted, bool AutoAct, string Strategy) StartupState(
			Func<string, string> readEnvironment)
		{
			static bool Flag(Func<string, string> read, string name, bool fallback)
			{
				var value = read(name);
				if (string.IsNullOrWhiteSpace(value))
					return fallback;

				return value.Trim().ToLowerInvariant() is "1" or "true" or "yes" or "on";
			}

			return (
				Flag(readEnvironment, "OPENRA_AI_COMPANION_READY", false),
				Flag(readEnvironment, "OPENRA_AI_STARTUP_ENABLED", true),
				Flag(readEnvironment, "OPENRA_AI_STARTUP_MUTED", false),
				Flag(readEnvironment, "OPENRA_AI_STARTUP_AUTO_ACT", false),
				readEnvironment("OPENRA_AI_STARTUP_STRATEGY") ?? "normal");
		}

		void UpdateAssistantRequest(string state)
		{
			if (string.IsNullOrWhiteSpace(state))
				return;

			var separator = state.IndexOf(':');
			var lifecycle = separator < 0 ? state : state[..separator];
			var requestedStrategy = separator < 0 ? "" : state[(separator + 1)..];
			if (lifecycle == "auto-active")
			{
				assistantAutoRequested = true;
				if (!string.IsNullOrWhiteSpace(requestedStrategy))
					assistantStrategyRequested = NormalizeAssistantStrategy(requestedStrategy);
			}
			else if (OpenRA.Mods.Common.Widgets.Logic.AIControlDisplay.IsExplicitManualModeState(state))
			{
				assistantAutoRequested = false;
				if (!string.IsNullOrWhiteSpace(requestedStrategy))
					assistantStrategyRequested = NormalizeAssistantStrategy(requestedStrategy);
			}
		}

		void SyncNativeAssistant()
		{
			bool requested;
			string strategy;
			lock (CurrentLock)
			{
				requested = assistantAutoRequested;
				strategy = assistantStrategyRequested;
			}

			var player = world.LocalPlayer;
			var scriptedMission = world.WorldActor.Info.TraitInfoOrDefault<MissionDataInfo>() != null;
			var canDelegate = requested && !scriptedMission && Game.IsHost && world.Type == WorldType.Regular
				&& !world.IsReplay && !world.IsGameOver && player != null && !player.Spectating && !player.IsBot;
			if (!canDelegate)
			{
				StopNativeAssistant();
				return;
			}

			strategy = NormalizeAssistantStrategy(strategy);
			if (assistantBot != null && activeAssistantStrategy == strategy && assistantBot.IsEnabled)
				return;

			StopNativeAssistant();
			var bot = player.PlayerActor.TraitsImplementing<ModularBot>()
				.FirstOrDefault(candidate => ((IBot)candidate).Info.Type == strategy);
			if (bot == null)
			{
				Log.Write("rl-bridge", $"Native assistant strategy '{strategy}' is unavailable.");
				return;
			}

			assistantPlayerActor = player.PlayerActor;
			assistantConditionToken = assistantPlayerActor.GrantCondition($"enable-{strategy}-ai");
			assistantBot = bot;
			activeAssistantStrategy = strategy;
			assistantBot.Activate(player);
			Log.Write("rl-bridge", $"Native assistant delegated the local player to OpenRA {strategy} AI.");
		}

		void StopNativeAssistant()
		{
			if (assistantBot != null)
				assistantBot.Deactivate();

			if (assistantPlayerActor != null && assistantConditionToken != Actor.InvalidConditionToken)
				assistantConditionToken = assistantPlayerActor.RevokeCondition(assistantConditionToken);

			if (!string.IsNullOrEmpty(activeAssistantStrategy))
				Log.Write("rl-bridge", $"Native assistant released OpenRA {activeAssistantStrategy} AI control.");

			assistantBot = null;
			assistantPlayerActor = null;
			assistantConditionToken = Actor.InvalidConditionToken;
			activeAssistantStrategy = "";
		}

		RLProto.GameState BuildState()
		{
			var winner = world.IsGameOver
				? world.Players.FirstOrDefault(player => player.WinState == WinState.Won)?.InternalName ?? ""
				: "";
			var enemyFaction = world.Players
				.FirstOrDefault(player => player != world.LocalPlayer && !player.NonCombatant && player.Playable)
				?.Faction?.InternalName ?? "";

			return new RLProto.GameState
			{
				EpisodeId = episodeId,
				Tick = world.WorldTick,
				Phase = world.IsGameOver ? "game_over" : "playing",
				Winner = winner,
				PlayerCount = world.Players.Length,
				PlayerFaction = world.LocalPlayer?.Faction?.InternalName ?? "",
				EnemyFaction = enemyFaction,
			};
		}

		void INotifyActorDisposing.Disposing(Actor self)
		{
			StopNativeAssistant();
			lock (CurrentLock)
			{
				if (current == this)
					current = null;
			}

			while (pendingActions.TryDequeue(out var pending))
				pending.Completion.TrySetResult(RejectedReceipt(
					pending.Request, "The match ended before the confirmed action could be queued."));
		}

		internal static Task<RLProto.CompanionActionReceipt> ExecuteActions(
			RLProto.CompanionActionRequest request)
		{
			RTSAICompanionBridge bridge;
			lock (CurrentLock)
				bridge = current;

			return bridge == null
				? Task.FromResult(RejectedReceipt(request, "No active local companion match is available."))
				: bridge.QueueActions(request);
		}

		Task<RLProto.CompanionActionReceipt> QueueActions(RLProto.CompanionActionRequest request)
		{
			var requestId = request.RequestId?.Trim() ?? "";
			if (requestId.Length < 8 || requestId.Length > 80 || requestId != request.RequestId)
				return Task.FromResult(RejectedReceipt(request, "The action request id is invalid.", world.WorldTick));

			lock (actionLock)
			{
				if (actionRequests.TryGetValue(requestId, out var existing))
					return existing;

				if (pendingActions.Count >= MaxPendingRequests)
					return Task.FromResult(RejectedReceipt(request, "The companion action queue is full.", world.WorldTick));

				var pending = new PendingActionRequest(request.Clone());
				actionRequests.Add(requestId, pending.Completion.Task);
				pendingActions.Enqueue(pending);
				return pending.Completion.Task;
			}
		}

		void ProcessPendingActions()
		{
			while (pendingActions.TryDequeue(out var pending))
			{
				RLProto.CompanionActionReceipt receipt;
				try
				{
					receipt = ValidateAndIssue(pending.Request);
				}
				catch (Exception e)
				{
					Log.Write("rl-bridge", $"Confirmed companion action failed: {e}");
					receipt = RejectedReceipt(pending.Request, "The engine rejected the confirmed action.", world.WorldTick);
				}

				pending.Completion.TrySetResult(receipt);
				lock (actionLock)
				{
					completedActionRequests.Enqueue(pending.Request.RequestId);
					while (completedActionRequests.Count > MaxRememberedRequests)
						actionRequests.Remove(completedActionRequests.Dequeue());
				}
			}
		}

		RLProto.CompanionActionReceipt ValidateAndIssue(RLProto.CompanionActionRequest request)
		{
			if (!TryGetStatus(out _, out _, out var statusEnabled, out _) || !statusEnabled)
				return RejectedReceipt(request, "The companion action kill switch is disabled.", world.WorldTick);

			if (world.LocalPlayer == null || world.LocalPlayer.Spectating)
				return RejectedReceipt(request, "There is no controllable local player.", world.WorldTick);

			if (world.LobbyInfo.NonBotClients.Count() != 1)
				return RejectedReceipt(request, "Companion actions are currently limited to single-player matches.", world.WorldTick);

			if (request.Commands.Count == 0 || request.Commands.Count > MaxCommandsPerRequest)
				return RejectedReceipt(request, $"A request must contain 1 to {MaxCommandsPerRequest} commands.", world.WorldTick);

			if (request.ExpectedTick <= 0 || Math.Abs(world.WorldTick - request.ExpectedTick) > MaxSnapshotAgeTicks)
				return RejectedReceipt(request, "The battlefield snapshot is stale; ask again before confirming.", world.WorldTick);

			actionHandler ??= new ActionHandler(world, world.LocalPlayer);
			var orders = new List<(RLProto.Command Command, Order Order)>();
			for (var i = 0; i < request.Commands.Count; i++)
			{
				var command = request.Commands[i];
				if (!TryValidateCommand(command, out var detail))
					return RejectedReceipt(request, $"Command {i + 1} was rejected: {detail}", world.WorldTick);

				var order = actionHandler.ConvertCommand(command);
				if (order == null)
					return RejectedReceipt(request, $"Command {i + 1} is not currently available.", world.WorldTick);

				orders.Add((command, order));
			}

			var receipt = new RLProto.CompanionActionReceipt
			{
				RequestId = request.RequestId,
				Accepted = true,
				GameTick = world.WorldTick,
				Detail = $"Queued {orders.Count} confirmed player order{(orders.Count == 1 ? "" : "s")}."
			};

			for (var i = 0; i < orders.Count; i++)
			{
				world.IssueOrder(orders[i].Order);
				receipt.Results.Add(new RLProto.CompanionCommandResult
				{
					Index = i,
					Action = orders[i].Command.Action,
					Accepted = true,
					Detail = "Queued as a synchronized local-player order."
				});
			}

			Log.Write("rl-bridge", $"Queued confirmed companion action {request.RequestId} at tick {world.WorldTick}");
			return receipt;
		}

		bool TryValidateCommand(RLProto.Command command, out string detail)
		{
			if (!AllowedActions.Contains(command.Action))
			{
				detail = $"{command.Action} is not in the safe action allowlist.";
				return false;
			}

			var requiresActor = command.Action is RLProto.ActionType.Move or RLProto.ActionType.AttackMove
				or RLProto.ActionType.Attack or RLProto.ActionType.Stop or RLProto.ActionType.Harvest
				or RLProto.ActionType.Deploy or RLProto.ActionType.Sell or RLProto.ActionType.Repair
				or RLProto.ActionType.SetRallyPoint or RLProto.ActionType.Guard or RLProto.ActionType.SetStance
				or RLProto.ActionType.EnterTransport or RLProto.ActionType.Disguise
				or RLProto.ActionType.Infiltrate or RLProto.ActionType.Demolish or RLProto.ActionType.Capture or RLProto.ActionType.Unload
				or RLProto.ActionType.PowerDown or RLProto.ActionType.SetPrimary;
			Actor subject = null;
			if (requiresActor)
			{
				subject = world.GetActorById(command.ActorId);
				if (subject == null || subject.IsDead || !subject.IsInWorld || subject.Owner != world.LocalPlayer)
				{
					detail = "the subject is not a live actor owned by the local player.";
					return false;
				}
			}

			if (command.Action is RLProto.ActionType.Move or RLProto.ActionType.AttackMove)
			{
				if (!subject.Info.HasTraitInfo<IMoveInfo>())
				{
					detail = "the subject cannot move.";
					return false;
				}
			}

			if (command.Action is RLProto.ActionType.Attack or RLProto.ActionType.AttackMove
				or RLProto.ActionType.Guard or RLProto.ActionType.SetStance)
			{
				if (!subject.Info.HasTraitInfo<AttackBaseInfo>())
				{
					detail = "the subject cannot attack.";
					return false;
				}
			}

			if (command.Action == RLProto.ActionType.Attack)
			{
				var target = world.GetActorById(command.TargetActorId);
				if (target == null || target.IsDead || !target.IsInWorld
					|| world.LocalPlayer.RelationshipWith(target.Owner) != PlayerRelationship.Enemy
					|| !world.LocalPlayer.Shroud.IsVisible(target.CenterPosition))
				{
					detail = "the attack target is not a live visible enemy.";
					return false;
				}
			}

			if (command.Action == RLProto.ActionType.Harvest && !subject.Info.HasTraitInfo<HarvesterInfo>())
			{
				detail = "the subject is not a harvester.";
				return false;
			}

			if (command.Action == RLProto.ActionType.Deploy
				&& !subject.TraitsImplementing<IIssueDeployOrder>()
					.Any(deploy => deploy.CanIssueDeployOrder(subject, command.Queued)))
			{
				detail = "the subject cannot deploy.";
				return false;
			}

			if (command.Action == RLProto.ActionType.Sell && !subject.Info.HasTraitInfo<SellableInfo>())
			{
				detail = "the subject cannot be sold.";
				return false;
			}

			if (command.Action == RLProto.ActionType.Repair)
			{
				var repairable = subject.TraitOrDefault<RepairableBuilding>();
				if (repairable == null || subject.GetDamageState() == DamageState.Undamaged)
				{
					detail = "the subject is not a damaged repairable building.";
					return false;
				}

				if (repairable.Repairers.Contains(world.LocalPlayer))
				{
					detail = "the subject is already being repaired by the local player.";
					return false;
				}
			}

			if (command.Action == RLProto.ActionType.SetRallyPoint && !subject.Info.HasTraitInfo<RallyPointInfo>())
			{
				detail = "the subject does not support rally points.";
				return false;
			}

			if (command.Action == RLProto.ActionType.Guard)
			{
				var target = world.GetActorById(command.TargetActorId);
				if (!subject.Info.HasTraitInfo<GuardInfo>() || target == null || target.IsDead || !target.IsInWorld
					|| world.LocalPlayer.RelationshipWith(target.Owner) != PlayerRelationship.Ally
					|| !target.Info.HasTraitInfo<GuardableInfo>())
				{
					detail = "the guard subject or allied target does not support guarding.";
					return false;
				}
			}

			if (command.Action == RLProto.ActionType.SetStance
				&& (!subject.Info.HasTraitInfo<AutoTargetInfo>() || command.TargetX < 0 || command.TargetX > 3))
			{
				detail = "the subject does not support the requested stance.";
				return false;
			}

			if (command.Action == RLProto.ActionType.EnterTransport)
			{
				var passenger = subject.TraitOrDefault<Passenger>();
				var target = world.GetActorById(command.TargetActorId);
				var cargo = target?.TraitOrDefault<Cargo>();
				if (passenger == null || target == null || target.IsDead || !target.IsInWorld
					|| world.LocalPlayer.RelationshipWith(target.Owner) != PlayerRelationship.Ally
					|| cargo == null || cargo.IsTraitDisabled
					|| !cargo.Info.Types.Contains(passenger.Info.CargoType) || !cargo.HasSpace(passenger.Info.Weight))
				{
					detail = "the passenger cannot enter that allied transport.";
					return false;
				}
			}

			if (command.Action is RLProto.ActionType.Disguise or RLProto.ActionType.Infiltrate
				or RLProto.ActionType.Demolish or RLProto.ActionType.Capture)
			{
				var target = world.GetActorById(command.TargetActorId);
				var orderId = command.Action switch
				{
					RLProto.ActionType.Disguise => "Disguise",
					RLProto.ActionType.Infiltrate => "Infiltrate",
					RLProto.ActionType.Demolish => "C4",
					_ => "CaptureActor"
				};
				if (target == null || target.IsDead || !target.IsInWorld
					|| (target.Owner != world.LocalPlayer && !world.LocalPlayer.Shroud.IsVisible(target.CenterPosition))
					|| !CanIssueTargetedOrder(subject, target, orderId))
				{
					detail = $"the subject cannot {orderId.ToLowerInvariant()} that currently visible target.";
					return false;
				}
			}

			if (command.Action == RLProto.ActionType.Unload)
			{
				var cargo = subject.TraitOrDefault<Cargo>();
				if (cargo == null || cargo.IsTraitDisabled || cargo.PassengerCount == 0)
				{
					detail = "the subject is not a loaded transport.";
					return false;
				}
			}

			if (command.Action == RLProto.ActionType.PowerDown
				&& !subject.Info.HasTraitInfo<ToggleConditionOnOrderInfo>())
			{
				detail = "the subject cannot be powered down.";
				return false;
			}

			if (command.Action == RLProto.ActionType.SetPrimary
				&& !subject.Info.HasTraitInfo<PrimaryBuildingInfo>())
			{
				detail = "the subject cannot be a primary producer.";
				return false;
			}

			if (command.Action is RLProto.ActionType.Move or RLProto.ActionType.AttackMove or RLProto.ActionType.SetRallyPoint
				|| (command.Action is RLProto.ActionType.Harvest or RLProto.ActionType.PlaceBuilding
					&& (command.TargetX != 0 || command.TargetY != 0)))
			{
				if (!world.Map.Contains(new MPos(command.TargetX, command.TargetY).ToCPos(world.Map)))
				{
					detail = "the target cell is outside the playable map.";
					return false;
				}
			}

			if (command.Action == RLProto.ActionType.UseSupportPower)
			{
				var cell = new MPos(command.TargetX, command.TargetY).ToCPos(world.Map);
				var manager = world.LocalPlayer.PlayerActor.TraitOrDefault<SupportPowerManager>();
				var power = manager?.Powers.FirstOrDefault(pair =>
					pair.Key.Equals(command.ItemType, StringComparison.OrdinalIgnoreCase));
				if (!world.Map.Contains(cell) || !world.LocalPlayer.Shroud.IsExplored(cell)
					|| power == null || string.IsNullOrEmpty(power.Value.Key) || !power.Value.Value.Ready)
				{
					detail = "the requested support power is not ready or its target cell is unexplored.";
					return false;
				}

				var descriptor = $"{power.Value.Key} {power.Value.Value.Name} {power.Value.Value.Description}";
				var destructive = descriptor.Contains("nuke", StringComparison.OrdinalIgnoreCase)
					|| descriptor.Contains("atomic", StringComparison.OrdinalIgnoreCase)
					|| descriptor.Contains("parabomb", StringComparison.OrdinalIgnoreCase);
				if (destructive)
				{
					var friendlyTooClose = world.Actors.Any(actor => actor.IsInWorld && !actor.IsDead && actor.Owner != null
						&& world.LocalPlayer.RelationshipWith(actor.Owner) == PlayerRelationship.Ally
						&& actor.Info.HasTraitInfo<ValuedInfo>()
						&& (actor.Location - cell).LengthSquared <= 15 * 15);
					var visibleEnemyCluster = world.Actors.Any(actor => actor.IsInWorld && !actor.IsDead && actor.Owner != null
						&& world.LocalPlayer.RelationshipWith(actor.Owner) == PlayerRelationship.Enemy
						&& world.LocalPlayer.Shroud.IsVisible(actor.CenterPosition)
						&& (actor.Location - cell).LengthSquared <= 6 * 6);
					if (friendlyTooClose || !visibleEnemyCluster)
					{
						detail = "destructive support powers require a visible enemy cluster and a 15-cell friendly-fire exclusion zone.";
						return false;
					}
				}
			}

			if (command.Action is RLProto.ActionType.Build or RLProto.ActionType.Train
				or RLProto.ActionType.PlaceBuilding or RLProto.ActionType.CancelProduction
				or RLProto.ActionType.UseSupportPower)
			{
				if (string.IsNullOrWhiteSpace(command.ItemType) || command.ItemType.Length > 64)
				{
					detail = "the production item is missing or invalid.";
					return false;
				}
			}

			detail = "validated";
			return true;
		}

		static bool CanIssueTargetedOrder(Actor subject, Actor target, string orderId)
		{
			foreach (var targeter in subject.TraitsImplementing<IIssueOrder>()
				.SelectMany(issuer => issuer.Orders)
				.Where(targeter => targeter.OrderID == orderId))
			{
				var modifiers = TargetModifiers.None;
				var cursor = "";
				if (targeter.CanTarget(subject, Target.FromActor(target), ref modifiers, ref cursor))
					return true;
			}

			return false;
		}

		static RLProto.CompanionActionReceipt RejectedReceipt(
			RLProto.CompanionActionRequest request, string detail, int tick = 0)
		{
			var receipt = new RLProto.CompanionActionReceipt
			{
				RequestId = request?.RequestId ?? "",
				Accepted = false,
				GameTick = tick,
				Detail = detail
			};

			if (request != null)
			{
				for (var i = 0; i < request.Commands.Count; i++)
					receipt.Results.Add(new RLProto.CompanionCommandResult
					{
						Index = i,
						Action = request.Commands[i].Action,
						Accepted = false,
						Detail = detail
					});
			}

			return receipt;
		}

		internal static bool TryGetObservation(out RLProto.GameObservation observation)
		{
			RTSAICompanionBridge bridge;
			lock (CurrentLock)
				bridge = current;

			if (bridge == null)
			{
				observation = null;
				return false;
			}

			lock (bridge.observationLock)
			{
				if (bridge.latestObservation == null)
				{
					observation = null;
					return false;
				}

				observation = bridge.latestObservation.Clone();
				return true;
			}
		}

		internal static bool TryGetState(out RLProto.GameState state)
		{
			RTSAICompanionBridge bridge;
			lock (CurrentLock)
				bridge = current;

			if (bridge == null)
			{
				state = null;
				return false;
			}

			lock (bridge.observationLock)
			{
				if (bridge.latestState == null)
				{
					state = null;
					return false;
				}

				state = bridge.latestState.Clone();
				return true;
			}
		}

		static RLProto.CompanionStatus ReadyStatus()
		{
			return IdleStatus(true, false);
		}

		static RLProto.CompanionStatus StartupStatus(bool enabled, bool muted, bool autoAct, string strategy)
		{
			if (!enabled || !autoAct)
				return IdleStatus(enabled, muted);

			return new RLProto.CompanionStatus
			{
				State = $"auto-active:{strategy}",
				Message = $"AUTO ASSISTANT ON  •  {strategy.ToUpperInvariant()} NATIVE BRAIN",
				Enabled = true,
				Muted = muted
			};
		}

		static RLProto.CompanionThreat CalmThreat()
		{
			return new RLProto.CompanionThreat
			{
				Score = 0,
				Level = "calm",
				Reason = "No immediate visible threat"
			};
		}

		static RLProto.CompanionStatus IdleStatus(bool enabled, bool muted)
		{
			return new RLProto.CompanionStatus
			{
				State = !enabled ? "disabled" : muted ? "muted" : "ready",
				Message = !enabled ? "AI OFF  •  ENABLE THE COMPANION IN SETTINGS" : muted
					? "AI VOICE OFF  •  TEXT INSIGHTS STAY ON"
					: "AI READY  •  HOLD ASK KEY TO SPEAK",
				Enabled = enabled,
				Muted = muted
			};
		}

		internal static bool UpdateStatus(RLProto.CompanionStatus status)
		{
			lock (CurrentLock)
			{
				if (current == null || !current.enabled)
					return false;

				companionStatus = status.Clone();
				companionStatusUpdatedAt = Environment.TickCount64;
				current.companionStatusAcknowledged = true;
				current.UpdateAssistantRequest(status.State);
				return true;
			}
		}

		internal static bool UpdateThreat(RLProto.CompanionThreat threat)
		{
			lock (CurrentLock)
			{
				if (current == null || !current.enabled)
					return false;

				companionThreat = threat.Clone();
				companionThreat.Score = Math.Clamp(companionThreat.Score, 0, 100);
				return true;
			}
		}

		internal static Task<RLProto.CompanionFrame> CaptureFrame(CancellationToken cancellationToken)
		{
			RTSAICompanionBridge bridge;
			lock (CurrentLock)
			{
				bridge = current;
				if (bridge == null || !bridge.enabled)
					throw new InvalidOperationException("No active local companion match is available.");
			}

			var completion = new TaskCompletionSource<RLProto.CompanionFrame>(
				TaskCreationOptions.RunContinuationsAsynchronously);
			var registration = cancellationToken.Register(() => completion.TrySetCanceled(cancellationToken));
			_ = completion.Task.ContinueWith(_ => registration.Dispose(), TaskScheduler.Default);
			Game.RunAfterTick(() =>
			{
				if (completion.Task.IsCompleted)
					return;

				try
				{
					var png = Game.Renderer.CaptureScreenshot(out var width, out var height);
					completion.TrySetResult(new RLProto.CompanionFrame
					{
						Tick = bridge.world.WorldTick,
						Png = Google.Protobuf.ByteString.CopyFrom(png),
						Width = width,
						Height = height,
						Scope = "rendered-player-viewport-fog-respecting"
					});
				}
				catch (Exception e)
				{
					completion.TrySetException(e);
				}
			});
			return completion.Task;
		}

		internal static bool UpdateLocalVoiceState(bool muted)
		{
			lock (CurrentLock)
			{
				if (current == null || !current.enabled)
					return false;

				companionStatus = IdleStatus(companionStatus.Enabled, muted);
				companionStatusUpdatedAt = Environment.TickCount64;
				return true;
			}
		}

		internal static bool UpdateLocalControlError(string message)
		{
			lock (CurrentLock)
			{
				if (current == null || !current.enabled)
					return false;

				companionStatus.State = "error";
				companionStatus.Message = message;
				companionStatusUpdatedAt = Environment.TickCount64;
				return true;
			}
		}

		internal static bool UpdateLocalStatus(string state, string message)
		{
			if (string.IsNullOrWhiteSpace(state) || string.IsNullOrWhiteSpace(message))
				return false;

			lock (CurrentLock)
			{
				if (current == null || !current.enabled)
					return false;

				companionStatus.State = state;
				companionStatus.Message = message;
				companionStatusUpdatedAt = Environment.TickCount64;
				return true;
			}
		}

		internal static bool TryGetStatus(out string state, out string message)
		{
			return TryGetStatus(out state, out message, out _, out _);
		}

		internal static bool TryGetAutoAct(out bool autoActEnabled)
		{
			lock (CurrentLock)
			{
				if (current == null || !current.enabled || !current.companionStatusAcknowledged)
				{
					autoActEnabled = false;
					return false;
				}

				autoActEnabled = current.assistantAutoRequested;
				return true;
			}
		}

		internal static bool TryGetThreat(out int score, out string level, out string reason)
		{
			lock (CurrentLock)
			{
				if (current == null || !current.enabled)
				{
					score = 0;
					level = "calm";
					reason = "";
					return false;
				}

				score = companionThreat.Score;
				level = companionThreat.Level;
				reason = companionThreat.Reason;
				return true;
			}
		}

		internal static bool TryGetStatus(out string state, out string message, out bool statusEnabled, out bool muted)
		{
			lock (CurrentLock)
			{
				if (current == null || !current.enabled)
				{
					state = null;
					message = null;
					statusEnabled = false;
					muted = false;
					return false;
				}

				// Insights describe a moment in time. Never leave one pinned
				// after the companion or audio process has moved on.
				if ((companionStatus.State == "speaking" || companionStatus.State == "insight" ||
					companionStatus.State == "routine" || companionStatus.State == "important" ||
					companionStatus.State == "critical" || companionStatus.State == "speaking-important" ||
					companionStatus.State == "speaking-critical")
					&& Environment.TickCount64 - companionStatusUpdatedAt >= SpokenStatusTimeoutMilliseconds)
				{
					companionStatus = IdleStatus(companionStatus.Enabled, companionStatus.Muted);
					companionStatusUpdatedAt = Environment.TickCount64;
				}
				else if (companionStatus.State == "error"
					&& Environment.TickCount64 - companionStatusUpdatedAt >= ErrorStatusTimeoutMilliseconds)
				{
					companionStatus = IdleStatus(companionStatus.Enabled, companionStatus.Muted);
					companionStatusUpdatedAt = Environment.TickCount64;
				}

				state = companionStatus.State;
				message = companionStatus.Message;
				statusEnabled = companionStatus.Enabled;
				muted = companionStatus.Muted;
				return true;
			}
		}
	}
}
