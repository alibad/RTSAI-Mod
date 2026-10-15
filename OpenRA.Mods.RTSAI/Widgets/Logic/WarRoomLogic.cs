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
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.RTSAI.Traits;
using CompanionBridge = OpenRA.Mods.RTSAI.Traits.CompanionBridge;
using OpenRA.Primitives;
using OpenRA.Support;
using OpenRA.Widgets;
using OpenRA.Mods.Common.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	/// <summary>
	/// Native consumer surface for the local OpenRA AI companion. The browser console
	/// remains useful for development, but players use this panel inside the game.
	/// </summary>
	public sealed class WarRoomLogic : ChromeLogic
	{
		const long LiveRefreshMilliseconds = 5000;
		static readonly string[] StrategyOrder = ["adaptive", "normal", "rush", "turtle", "naval", "medium"];

		sealed class ViewModel
		{
			public bool Connected;
			public bool AutoAct;
			public bool Voice;
			public bool PendingAction;
			public int Threat;
			public string ThreatLevel = "CALM";
			public string Connection = "CONNECTING TO LOCAL AI";
			public string LiveSummary = "Waiting for the local companion.";
			public string LiveMap = "NO ACTIVE MATCH";
			public string LiveEconomy = "No economy snapshot yet.";
			public string LiveMilitary = "No military snapshot yet.";
			public string LiveDecision = "No strategic decision has been recorded.";
			public string LiveAction = "No bounded action is pending.";
			public string LiveVerification = "Waiting for a verified game-state receipt.";
			public string DebriefResult = "NO COMPLETED MATCH";
			public string DebriefSummary = "Complete a match to create an after-action review.";
			public string DebriefMetrics = "No performance metrics yet.";
			public string DebriefStrengths = "No verified strengths yet.";
			public string DebriefImprovements = "No corrective lessons yet.";
			public string DebriefTimeline = "No decision timeline yet.";
			public string LearningSummary = "No evaluation history yet.";
			public string LearningDifficulty = "No difficulty ladder data yet.";
			public string LearningLessons = "No lessons have been recorded.";
			public string LearningAttempts = "No attempts have been recorded.";
			public string LearningPolicy = "ACTIVE POLICY: BASELINE";
			public string BrainOwner = "PLAYER";
			public string BrainStrategy = "No native strategy is active.";
			public string BrainDecision = "No fast decision is queued.";
			public string BrainGoals = "No goals are active.";
			public string BrainLeases = "No command leases or receipts are active.";
			public string Model = "unknown";
			public string Router = "Local AI route unavailable";
			public string Strategy = "adaptive";
		}

		readonly Dictionary<string, Widget> panels = [];
		readonly Dictionary<string, ButtonWidget> tabs = [];
		readonly Action onExit;
		readonly ColorBlockWidget threatFill;
		readonly ColorBlockWidget threatTrack;
		readonly ButtonWidget refreshButton;
		readonly ButtonWidget acceptButton;
		readonly ButtonWidget rejectButton;
		readonly ButtonWidget autoButton;
		readonly ButtonWidget voiceButton;
		readonly ButtonWidget strategyButton;
		ViewModel model = new();
		string activeTab;
		bool requestPending;
		long nextRefreshAt;

		[ObjectCreator.UseCtor]
		public WarRoomLogic(Widget widget, Action onExit, string initialTab = "live")
		{
			this.onExit = onExit;
			activeTab = NormalizeTab(initialTab);

			panels.Add("live", widget.Get("LIVE_PANEL"));
			panels.Add("debrief", widget.Get("DEBRIEF_PANEL"));
			panels.Add("learning", widget.Get("LEARNING_PANEL"));
			panels.Add("brain", widget.Get("BRAIN_PANEL"));
			panels.Add("settings", widget.Get("SETTINGS_PANEL"));

			tabs.Add("live", widget.Get<ButtonWidget>("LIVE_TAB"));
			tabs.Add("debrief", widget.Get<ButtonWidget>("DEBRIEF_TAB"));
			tabs.Add("learning", widget.Get<ButtonWidget>("LEARNING_TAB"));
			tabs.Add("brain", widget.Get<ButtonWidget>("BRAIN_TAB"));
			tabs.Add("settings", widget.Get<ButtonWidget>("SETTINGS_TAB"));
			foreach (var pair in tabs)
			{
				var tab = pair.Key;
				pair.Value.OnClick = () => SetTab(tab);
				pair.Value.IsHighlighted = () => activeTab == tab;
			}

			widget.Get<ColorBlockWidget>("TOP_ACCENT").GetColor = ThreatColor;
			widget.Get<LabelWidget>("CONNECTION").GetText = () => model.Connection;
			widget.Get<LabelWidget>("CONNECTION").GetColor = () => model.Connected ? Color.LightGreen : Color.OrangeRed;
			widget.Get<LabelWidget>("THREAT_VALUE").GetText = () => $"{model.Threat} / {model.ThreatLevel}";
			widget.Get<LabelWidget>("THREAT_VALUE").GetColor = ThreatColor;
			threatTrack = widget.Get<ColorBlockWidget>("THREAT_TRACK");
			threatTrack.GetColor = () => Color.FromArgb(255, 44, 50, 48);
			threatFill = widget.Get<ColorBlockWidget>("THREAT_FILL");
			threatFill.GetColor = ThreatColor;

			Bind(widget, "LIVE_SUMMARY", CurrentAssistantSummary);
			Bind(widget, "LIVE_MAP", () => model.LiveMap);
			Bind(widget, "LIVE_ECONOMY", () => model.LiveEconomy);
			Bind(widget, "LIVE_MILITARY", () => model.LiveMilitary);
			Bind(widget, "LIVE_DECISION", () => model.LiveDecision);
			Bind(widget, "LIVE_ACTION", () => model.LiveAction);
			Bind(widget, "LIVE_VERIFICATION", () => model.LiveVerification);

			Bind(widget, "DEBRIEF_RESULT", () => model.DebriefResult);
			Bind(widget, "DEBRIEF_SUMMARY", () => model.DebriefSummary);
			Bind(widget, "DEBRIEF_METRICS", () => model.DebriefMetrics);
			Bind(widget, "DEBRIEF_STRENGTHS", () => model.DebriefStrengths);
			Bind(widget, "DEBRIEF_IMPROVEMENTS", () => model.DebriefImprovements);
			Bind(widget, "DEBRIEF_TIMELINE", () => model.DebriefTimeline);

			Bind(widget, "LEARNING_SUMMARY", () => model.LearningSummary);
			Bind(widget, "LEARNING_DIFFICULTY", () => model.LearningDifficulty);
			Bind(widget, "LEARNING_LESSONS", () => model.LearningLessons);
			Bind(widget, "LEARNING_ATTEMPTS", () => model.LearningAttempts);
			Bind(widget, "LEARNING_POLICY", () => model.LearningPolicy);

			Bind(widget, "BRAIN_OWNER", () => model.BrainOwner);
			Bind(widget, "BRAIN_STRATEGY", () => model.BrainStrategy);
			Bind(widget, "BRAIN_DECISION", () => model.BrainDecision);
			Bind(widget, "BRAIN_GOALS", () => model.BrainGoals);
			Bind(widget, "BRAIN_LEASES", () => model.BrainLeases);

			Bind(widget, "SETTINGS_MODEL", () => $"COMPANION MODEL\n{model.Model}");
			Bind(widget, "SETTINGS_ROUTER", () => $"LOCAL AI ROUTE\n{model.Router}");
			Bind(widget, "SETTINGS_PRIVACY", () =>
				"Battle data, screenshots, transcripts, and learning history stay on this machine unless the selected model route requires network access.");

			refreshButton = widget.Get<ButtonWidget>("REFRESH_BUTTON");
			refreshButton.GetText = () => requestPending ? "SYNC..." : "SYNC";
			refreshButton.IsDisabled = () => requestPending;
			refreshButton.OnClick = () => _ = RefreshAsync();

			acceptButton = widget.Get<ButtonWidget>("ACCEPT_BUTTON");
			rejectButton = widget.Get<ButtonWidget>("REJECT_BUTTON");
			acceptButton.IsVisible = () => model.PendingAction;
			rejectButton.IsVisible = () => model.PendingAction;
			acceptButton.IsDisabled = () => requestPending;
			rejectButton.IsDisabled = () => requestPending;
			acceptButton.OnClick = () => _ = PostControlAsync("v1/actions/confirm", "{}", "Action accepted.");
			rejectButton.OnClick = () => _ = PostControlAsync("v1/actions/cancel", "{}", "Action rejected.");

			autoButton = widget.Get<ButtonWidget>("AUTO_BUTTON");
			voiceButton = widget.Get<ButtonWidget>("VOICE_BUTTON");
			strategyButton = widget.Get<ButtonWidget>("STRATEGY_BUTTON");
			autoButton.GetText = () => AIControlDisplay.AutoButtonText(requestPending, model.Connected, model.AutoAct);
			voiceButton.GetText = () => requestPending ? "VOICE: ..." : model.Voice ? "VOICE: ON" : "VOICE: OFF";
			strategyButton.GetText = () => $"STRATEGY: {model.Strategy.ToUpperInvariant()}";
			autoButton.IsHighlighted = () => model.AutoAct;
			voiceButton.IsHighlighted = () => model.Voice;
			autoButton.IsDisabled = () => requestPending || !model.Connected;
			voiceButton.IsDisabled = () => requestPending || !model.Connected;
			strategyButton.IsDisabled = () => requestPending || !model.Connected;
			autoButton.OnClick = () => _ = PostControlAsync("v1/control",
				JsonSerializer.Serialize(new { auto_act = !model.AutoAct }), "Auto-assistant mode updated.");
			voiceButton.OnClick = () => _ = PostControlAsync("v1/control",
				JsonSerializer.Serialize(new { muted = model.Voice }), "Voice mode updated.");
			strategyButton.OnClick = () =>
			{
				var index = Array.IndexOf(StrategyOrder, model.Strategy);
				var next = StrategyOrder[(index + 1 + StrategyOrder.Length) % StrategyOrder.Length];
				_ = PostControlAsync("v1/config", JsonSerializer.Serialize(new { native_strategy = next }),
					$"Strategy changed to {next}.");
			};

			widget.Get<ButtonWidget>("CLOSE_BUTTON").OnClick = Close;
			SetTab(activeTab);
			_ = RefreshAsync();
		}

		public override void Tick()
		{
			threatFill.Bounds.Width = threatTrack.Bounds.Width * Math.Clamp(model.Threat, 0, 100) / 100;
			if (!requestPending && Environment.TickCount64 >= nextRefreshAt)
				_ = RefreshAsync();
		}

		void Close()
		{
			Ui.CloseWindow();
			onExit();
		}

		void SetTab(string tab)
		{
			activeTab = NormalizeTab(tab);
			foreach (var pair in panels)
				pair.Value.IsVisible = () => activeTab == pair.Key;
		}

		async Task RefreshAsync()
		{
			if (requestPending)
				return;

			requestPending = true;
			nextRefreshAt = Environment.TickCount64 + LiveRefreshMilliseconds;
			try
			{
				using var client = LocalClient();
				using var response = await client.GetAsync("v1/war-room");
				response.EnsureSuccessStatusCode();
				using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
				var updated = BuildModel(document.RootElement);
				Game.RunAfterTick(() => model = updated);
			}
			catch (Exception e)
			{
				Log.Write("debug", $"Failed to refresh OpenRA AI War Room: {e}");
				Game.RunAfterTick(() =>
				{
					model.Connected = false;
					model.Connection = "LOCAL AI LINK UNAVAILABLE";
					model.LiveSummary = "The game remains playable. Start OpenRA from the packaged launcher to restore the AI companion.";
				});
			}
			finally
			{
				Game.RunAfterTick(() => requestPending = false);
			}
		}

		async Task PostControlAsync(string path, string payload, string success)
		{
			if (requestPending)
				return;

			requestPending = true;
			try
			{
				using var client = LocalClient();
				using var content = new StringContent(payload, Encoding.UTF8, "application/json");
				using var response = await client.PostAsync(path, content);
				response.EnsureSuccessStatusCode();
				Game.RunAfterTick(() => model.LiveVerification = success);
			}
			catch (Exception e)
			{
				Log.Write("debug", $"Failed to update OpenRA AI from the War Room: {e}");
				Game.RunAfterTick(() => model.LiveVerification = "Control request failed. No unsafe action was sent.");
			}
			finally
			{
				Game.RunAfterTick(() =>
				{
					requestPending = false;
					_ = RefreshAsync();
				});
			}
		}

		static HttpClient LocalClient()
		{
			var configuredUrl = Environment.GetEnvironmentVariable("OPENRA_AI_CONSOLE_URL");
			var baseUrl = string.IsNullOrWhiteSpace(configuredUrl) ? "http://127.0.0.1:8787/" : configuredUrl;
			if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var uri) || !uri.IsLoopback)
				throw new InvalidOperationException("The companion control URL must be local.");

			var client = HttpClientFactory.Create();
			client.BaseAddress = uri;
			client.Timeout = TimeSpan.FromSeconds(5);
			return client;
		}

		string CurrentAssistantSummary()
		{
			if (CompanionBridge.TryGetStatus(out _, out var message) && !string.IsNullOrWhiteSpace(message))
				return message.Replace("AI  •  ", "", StringComparison.OrdinalIgnoreCase);

			return model.LiveSummary;
		}

		Color ThreatColor()
		{
			if (model.Threat >= 80)
				return Color.Red;
			if (model.Threat >= 55)
				return Color.OrangeRed;
			if (model.Threat >= 30)
				return Color.Orange;
			return Color.LightGreen;
		}

		static void Bind(Widget widget, string id, Func<string> value)
		{
			var label = widget.Get<LabelWidget>(id);
			label.GetText = value;
		}

		static string NormalizeTab(string tab)
		{
			tab = tab?.Trim().ToLowerInvariant();
			return tab is "live" or "debrief" or "learning" or "brain" or "settings" ? tab : "live";
		}

		static ViewModel BuildModel(JsonElement root)
		{
			var result = new ViewModel();
			var live = Property(root, "live");
			var threat = Property(live, "threat");
			var snapshot = Property(live, "snapshot");
			var brain = Property(live, "brain");
			var strategy = Property(live, "strategy");
			var router = Property(live, "router");
			var settings = Property(root, "settings");

			// Reaching this method means that the local companion control plane replied.
			// The model router is a separate dependency and may be offline without
			// preventing local controls, history, or debriefs from working.
			result.Connected = true;
			result.Connection = "LOCAL COMPANION ONLINE";
			result.AutoAct = Boolean(live, "auto_act_enabled");
			result.Voice = Boolean(live, "voice_enabled");
			result.PendingAction = Property(live, "pending_action").ValueKind == JsonValueKind.Object;
			result.Threat = Integer(threat, "score");
			result.ThreatLevel = Text(threat, "level", "calm").ToUpperInvariant();
			result.LiveSummary = Text(threat, "reason", "No immediate visible threat.");
			result.Strategy = Text(settings, "native_strategy", Text(strategy, "profile", "adaptive"));
			result.Model = Text(settings, "text_model", "unknown");
			result.Router = Boolean(router, "reachable")
				? $"ONLINE / {Text(router, "url", "local")}" : $"OFFLINE / {Text(router, "url", "local")}";

			if (snapshot.ValueKind == JsonValueKind.Object)
			{
				var economy = Property(snapshot, "economy");
				var military = Property(snapshot, "military");
				result.LiveMap = $"{Text(snapshot, "map", "Unknown battlefield").ToUpperInvariant()}  /  TICK {Integer(snapshot, "tick"):N0}";
				result.LiveEconomy = $"CASH {Integer(economy, "cash"):N0}  /  ORE {Integer(economy, "ore"):N0}\n" +
					$"HARVESTERS {Integer(economy, "harvesters")}  /  STORAGE {Number(economy, "storage_percent"):0.#}%  /  POWER {Integer(economy, "power_balance"):+#;-#;0}";
				result.LiveMilitary = $"ARMY VALUE {Integer(military, "army_value"):N0}  /  ASSETS {Integer(military, "assets_value"):N0}\n" +
					$"KILLS {Integer(military, "units_killed")}  /  LOSSES {Integer(military, "units_lost")}  /  VISIBLE ENEMIES {ArrayCount(snapshot, "visible_enemies")}";
			}

			result.BrainOwner = Text(brain, "owner", "player").ToUpperInvariant();
			var controller = Property(brain, "controller");
			var program = Property(controller, "strategy_program");
			var fastDecision = Property(controller, "next_fast_decision");
			result.BrainStrategy = $"{Text(program, "profile", Text(strategy, "active_native_profile", result.Strategy)).ToUpperInvariant()}\n" +
				Text(program, "intent", Text(strategy, "intent", "No native strategy program is active."));
			result.BrainDecision = $"{Text(fastDecision, "key", "none").ToUpperInvariant()}\n" +
				Text(fastDecision, "summary", "No urgent bounded action is queued.");
			var goals = Property(brain, "goals");
			result.BrainGoals = GoalLines(Property(goals, "active"), "No goals are active.");
			var leases = Property(brain, "leases");
			result.BrainLeases = GoalLines(leases, "No command leases are active.");
			var updates = Property(brain, "latest_goal_updates");
			if (result.BrainLeases.StartsWith("No command", StringComparison.Ordinal) && updates.ValueKind == JsonValueKind.Array)
				result.BrainLeases = GoalLines(updates, result.BrainLeases);
			result.LiveDecision = Text(fastDecision, "summary", Text(program, "intent", result.LiveDecision));
			var pending = Property(live, "pending_action");
			result.LiveAction = result.PendingAction
				? Text(pending, "summary", Text(pending, "instruction", "A bounded action is waiting for approval."))
				: result.AutoAct ? "Native execution is active; bounded actions are verified from later snapshots." : result.LiveAction;
			if (updates.ValueKind == JsonValueKind.Array && updates.GetArrayLength() > 0)
			{
				var latestUpdate = updates.EnumerateArray().Last();
				result.LiveVerification = $"{Text(latestUpdate, "status", "updated").ToUpperInvariant()}: " +
					Text(latestUpdate, "summary", Text(latestUpdate, "instruction", "Goal receipt updated."));
			}

			BuildDebrief(result, Property(root, "debrief"));
			BuildLearning(result, Property(root, "learning"));
			return result;
		}

		static void BuildDebrief(ViewModel result, JsonElement match)
		{
			if (match.ValueKind != JsonValueKind.Object || string.IsNullOrEmpty(Text(match, "attempt_id")))
				return;

			var won = Boolean(match, "won");
			var resources = Property(match, "resources");
			var military = Property(resources, "final_military");
			var economy = Property(resources, "final_economy");
			result.DebriefResult = won ? "VERIFIED WIN" : Text(match, "result", "incomplete").ToUpperInvariant();
			result.DebriefSummary = $"{Text(match, "map", "Unknown map")}  /  {Text(match, "opponent", "unknown").ToUpperInvariant()}  /  " +
				$"TICK {Integer(match, "tick"):N0}  /  {Integer(match, "rounds"):N0} DECISION ROUNDS";
			result.DebriefMetrics = $"COMBAT VALUE RATIO {Number(resources, "combat_value_ratio"):0.00}\n" +
				$"KILLS {Integer(military, "units_killed")}  /  LOSSES {Integer(military, "units_lost")}  /  ENEMY STRUCTURES {Integer(military, "buildings_killed")}\n" +
				$"PEAK HARVESTERS {Integer(resources, "peak_harvesters")}  /  FINAL ORE {Integer(economy, "ore"):N0}  /  POWER {Integer(economy, "power_balance"):+#;-#;0}";
			var assessment = Property(match, "assessment");
			result.DebriefStrengths = Lines(Property(assessment, "strengths"), "No verified strengths yet.", 5);
			result.DebriefImprovements = Lines(Property(assessment, "improvements"), "No corrective lessons yet.", 5);
			result.DebriefTimeline = TimelineLines(Property(match, "timeline"));
		}

		static void BuildLearning(ViewModel result, JsonElement learning)
		{
			if (learning.ValueKind != JsonValueKind.Object)
				return;

			var attempts = Integer(learning, "attempts");
			var wins = Integer(learning, "wins");
			result.LearningSummary = $"{attempts:N0} RECORDED ATTEMPTS  /  {wins:N0} VERIFIED WINS  /  {Number(learning, "win_rate"):0.#}% WIN RATE";
			var difficulty = Property(learning, "by_difficulty");
			if (difficulty.ValueKind == JsonValueKind.Object)
				result.LearningDifficulty = difficulty.EnumerateObject().Select(pair =>
					$"{pair.Name.ToUpperInvariant()}: {Integer(pair.Value, "wins")} / {Integer(pair.Value, "attempts")} WINS ({Number(pair.Value, "win_rate"):0.#}%)")
					.JoinWith("\n");

			var lessons = Property(learning, "latest_lessons");
			var strengths = Lines(Property(lessons, "strengths"), "", 3);
			var improvements = Lines(Property(lessons, "improvements"), "", 3);
			result.LearningLessons = $"KEEP\n{strengths}\n\nCHANGE NEXT\n{improvements}".Trim();
			result.LearningAttempts = AttemptLines(Property(learning, "recent_attempts"));
			result.LearningPolicy = $"ACTIVE POLICY: {Text(Property(learning, "policies"), "active_policy", "baseline").ToUpperInvariant()}";
		}

		static string GoalLines(JsonElement values, string fallback)
		{
			if (values.ValueKind != JsonValueKind.Array || values.GetArrayLength() == 0)
				return fallback;

			return values.EnumerateArray().Take(6).Select(value =>
				$"- {Text(value, "summary", Text(value, "instruction", Text(value, "owner", "Goal")))} " +
				$"[{Text(value, "status", Text(value, "scope", "active")).ToUpperInvariant()}]").JoinWith("\n");
		}

		static string Lines(JsonElement values, string fallback, int limit)
		{
			if (values.ValueKind != JsonValueKind.Array || values.GetArrayLength() == 0)
				return fallback;

			return values.EnumerateArray().Take(limit).Select(value => $"- {value.GetString()}").JoinWith("\n");
		}

		static string TimelineLines(JsonElement values)
		{
			if (values.ValueKind != JsonValueKind.Array || values.GetArrayLength() == 0)
				return "No decision timeline yet.";

			return values.EnumerateArray().Reverse().Take(7).Select(value =>
			{
				var type = Text(value, "type", "event").ToUpperInvariant();
				var detail = Text(value, "decision", Text(value, "event", ""));
				if (string.IsNullOrEmpty(detail) && Property(value, "orders").ValueKind == JsonValueKind.Array)
					detail = $"{ArrayCount(value, "orders")} bounded order(s) issued";
				return $"T+{Integer(value, "tick"):N0}  {type}  {detail}";
			}).JoinWith("\n");
		}

		static string AttemptLines(JsonElement values)
		{
			if (values.ValueKind != JsonValueKind.Array || values.GetArrayLength() == 0)
				return "No attempts have been recorded.";

			return values.EnumerateArray().Take(8).Select(value =>
				$"{(Boolean(value, "won") ? "WIN " : "----")}  {Text(value, "map", "unknown")}  /  " +
				$"{Text(value, "opponent", "unknown").ToUpperInvariant()}  /  T+{Integer(value, "tick"):N0}").JoinWith("\n");
		}

		static JsonElement Property(JsonElement value, string name)
		{
			return value.ValueKind == JsonValueKind.Object && value.TryGetProperty(name, out var property)
				? property : default;
		}

		static string Text(JsonElement value, string name, string fallback = "")
		{
			var property = Property(value, name);
			return property.ValueKind == JsonValueKind.String ? property.GetString() ?? fallback : fallback;
		}

		static bool Boolean(JsonElement value, string name)
		{
			var property = Property(value, name);
			return property.ValueKind == JsonValueKind.True ||
				(property.ValueKind == JsonValueKind.String &&
					bool.TryParse(property.GetString(), out var parsed) && parsed);
		}

		static int Integer(JsonElement value, string name)
		{
			var property = Property(value, name);
			return property.ValueKind == JsonValueKind.Number && property.TryGetInt32(out var parsed) ? parsed : 0;
		}

		static double Number(JsonElement value, string name)
		{
			var property = Property(value, name);
			return property.ValueKind == JsonValueKind.Number && property.TryGetDouble(out var parsed) ? parsed : 0;
		}

		static int ArrayCount(JsonElement value, string name)
		{
			var property = Property(value, name);
			return property.ValueKind == JsonValueKind.Array ? property.GetArrayLength() : 0;
		}
	}
}
