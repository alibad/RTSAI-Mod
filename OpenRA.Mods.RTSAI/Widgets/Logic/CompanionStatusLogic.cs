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
using System.Diagnostics;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using OpenRA.Graphics;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.Common.Widgets.Logic;
using OpenRA.Mods.RTSAI.Companion;
using OpenRA.Mods.RTSAI.Traits;
using CompanionBridge = OpenRA.Mods.RTSAI.Traits.CompanionBridge;
using OpenRA.Primitives;
using OpenRA.Support;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	public sealed class CompanionStatusLogic : ChromeLogic
	{
		const int VoiceButtonWidth = 94;
		const int FeedbackButtonWidth = 70;
		const int ActionConfirmButtonWidth = 76;
		const int ActionCancelButtonWidth = 58;
		const int AutoButtonWidth = 72;
		const int FeedPanelHeight = 356;
		const int MaxFeedEntries = 80;
		const int ButtonTextPadding = 6;
		sealed class FeedEntry
		{
			public readonly Widget Widget;
			public readonly LabelWidget MessageLabel;
			public readonly string Message;
			public readonly string Meta;
			public readonly Color Color;
			public readonly bool IsPlayer;

			public FeedEntry(Widget widget, LabelWidget messageLabel, string message, string meta, Color color, bool isPlayer)
			{
				Widget = widget;
				MessageLabel = messageLabel;
				Message = message;
				Meta = meta;
				Color = color;
				IsPlayer = isPlayer;
			}
		}

		[FluentReference]
		const string VoiceOn = "button-ai-companion-voice-on";

		[FluentReference]
		const string VoiceOff = "button-ai-companion-voice-off";

		[FluentReference]
		const string VoicePending = "button-ai-companion-voice-pending";

		readonly List<FeedEntry> feedEntries = [];
		readonly BackgroundWidget feedPanel;
		readonly ScrollPanelWidget historyPanel;
		readonly ContainerWidget historyTemplate;
		readonly LabelWidget latestMetaLabel;
		readonly LabelWidget latestMessageLabel;
		readonly LabelWidget feedCountLabel;
		readonly LabelWidget feedEmptyLabel;
		readonly ColorBlockWidget feedAccent;
		readonly SpriteFont latestFont;
		readonly ModData modData;
		readonly World world;
		bool feedExpanded;
		bool showOnlyPlayer;
		bool postGameDebriefScheduled;
		string lastCapturedSignature = "";
		string latestMeta = "LINK READY // AWAITING FIRST SIGNAL";
		string latestMessage = "Your latest AI advice, alerts, voice transcript, and confirmed orders will remain here.";
		Color latestColor = Color.LightGreen;
		int laidOutFeedWidth;

		[ObjectCreator.UseCtor]
		public CompanionStatusLogic(Widget widget, ModData modData, World world)
		{
			this.modData = modData;
			this.world = world;
			var statusButton = widget.Get<ButtonWidget>("STATUS");
			var feedToggleButton = widget.Get<ButtonWidget>("FEED_TOGGLE");
			var actionConfirmButton = widget.Get<ButtonWidget>("ACTION_CONFIRM");
			var actionCancelButton = widget.Get<ButtonWidget>("ACTION_CANCEL");
			var autoButton = widget.Get<ButtonWidget>("AUTO_TOGGLE");
			var threatLabel = widget.Get<LabelWidget>("THREAT_LABEL");
			var threatTrack = widget.Get<ColorBlockWidget>("THREAT_TRACK");
			var threatFill = widget.Get<ColorBlockWidget>("THREAT_FILL");
			var voiceButton = widget.Get<ButtonWidget>("VOICE_TOGGLE");
			var feedbackButton = widget.Get<ButtonWidget>("FEEDBACK");
			var askShortcut = widget.GetOrNull<LabelWidget>("ASK_SHORTCUT");
			if (askShortcut != null)
				askShortcut.GetText = () => $"Hold {Binding("AIAsk")} to ask AI";
			feedPanel = widget.Get<BackgroundWidget>("FEED_PANEL");
			historyPanel = feedPanel.Get<ScrollPanelWidget>("FEED_HISTORY");
			historyTemplate = historyPanel.Get<ContainerWidget>("FEED_ITEM_TEMPLATE");
			latestMetaLabel = feedPanel.Get<LabelWidget>("LATEST_META");
			latestMessageLabel = feedPanel.Get<LabelWidget>("LATEST_MESSAGE");
			feedCountLabel = feedPanel.Get<LabelWidget>("FEED_COUNT");
			feedEmptyLabel = feedPanel.Get<LabelWidget>("FEED_EMPTY");
			feedAccent = feedPanel.Get<ColorBlockWidget>("FEED_ACCENT");
			latestFont = Game.Renderer.Fonts[latestMessageLabel.Font];
			statusButton.Font = "Regular";
			statusButton.Align = TextAlign.Left;
			var font = Game.Renderer.Fonts[statusButton.Font];
			var displayMessage = "";
			var requestPending = false;
			var actionRequestPending = false;
			var autoRequestPending = false;
			var feedbackRequestPending = false;

			feedPanel.Get<LabelWidget>("FEED_TITLE").GetText = () => "ACTIVITY";
			feedPanel.Get<LabelWidget>("LATEST_KICKER").GetText = () =>
				showOnlyPlayer ? "YOUR REQUESTS" : "LATEST UPDATE";
			feedPanel.Get<LabelWidget>("FEED_FOOTER").GetText = () =>
				"Automatic orders and spoken replies are optional.";
			feedEmptyLabel.GetText = () => showOnlyPlayer
				? "Your requests will appear here."
				: "Advice and confirmed orders will appear here.";
			feedPanel.Get<ButtonWidget>("FEED_CLOSE").GetText = () => "X";
			feedPanel.Get<ButtonWidget>("FEED_CLOSE").OnClick = () => feedExpanded = false;
			feedPanel.Get<ColorBlockWidget>("FEED_HEADER_RULE").GetColor = () => Color.FromArgb(130, latestColor);
			feedPanel.Get<ColorBlockWidget>("FEED_HISTORY_RULE").GetColor = () => Color.FromArgb(80, latestColor);
			feedPanel.Get<LabelWidget>("FEED_TITLE").GetColor = () => Color.LightGreen;
			feedPanel.Get<LabelWidget>("LATEST_KICKER").GetColor = () => Color.Gray;
			feedPanel.Get<LabelWidget>("FEED_FOOTER").GetColor = () => Color.Gray;
			feedPanel.IsVisible = () => feedExpanded;
			feedEmptyLabel.IsVisible = () => showOnlyPlayer ? PlayerEntryCount() == 0 : feedEntries.Count == 0;
			feedCountLabel.GetText = () => $"{feedEntries.Count} updates";
			feedCountLabel.GetColor = () => feedEntries.Count == 0 ? Color.Gray : latestColor;
			latestMetaLabel.GetText = () => latestMeta;
			latestMetaLabel.GetColor = () => latestColor;
			latestMessageLabel.GetText = () => FitToLines(latestMessage, latestMessageLabel.Bounds.Width, latestFont, 3);
			latestMessageLabel.GetColor = () => Color.White;
			feedAccent.GetColor = () => CompanionBridge.TryGetThreat(out _, out var level, out _)
				? ThreatColor(level)
				: Color.LightGreen;

			var filterAllButton = feedPanel.Get<ButtonWidget>("FILTER_ALL");
			var filterYouButton = feedPanel.Get<ButtonWidget>("FILTER_YOU");
			filterAllButton.GetText = () => "ALL";
			filterYouButton.GetText = () => "YOU";
			filterAllButton.IsHighlighted = () => !showOnlyPlayer;
			filterYouButton.IsHighlighted = () => showOnlyPlayer;
			filterAllButton.OnClick = () => SetPlayerFilter(false);
			filterYouButton.OnClick = () => SetPlayerFilter(true);

			void ToggleFeed()
			{
				feedExpanded = !feedExpanded;
				if (feedExpanded)
					historyPanel.ScrollToBottom();
			}

			statusButton.OnClick = () => OpenWarRoom("live");
			feedToggleButton.OnClick = ToggleFeed;
			feedToggleButton.GetText = () => feedExpanded ? "CLOSE" : "DETAILS";
			feedToggleButton.IsHighlighted = () => feedExpanded;
			feedbackButton.GetText = () => feedbackRequestPending ? "WAIT" : "REPORT";
			feedbackButton.IsHighlighted = () => feedbackRequestPending;
			feedbackButton.IsDisabled = () => feedbackRequestPending ||
				!CompanionBridge.TryGetStatus(out _, out _, out _, out _);
			feedbackButton.OnClick = () => _ = CaptureFeedbackAsync();

			async Task CaptureFeedbackAsync()
			{
				if (feedbackRequestPending)
					return;

				feedbackRequestPending = true;
				try
				{
					var uri = OpenRAAILocalClient.GetBaseUri("OPENRA_AI_CONSOLE_URL", "http://127.0.0.1:8787/");
					using var result = await OpenRAAILocalClient.PostAsync(uri, "v1/feedback/capture", new { }, 12);
					var feedbackPath = result.RootElement.GetProperty("feedback_url").GetString();
					if (!Uri.TryCreate(uri, feedbackPath, out var feedbackUri) || !feedbackUri.IsLoopback)
						throw new InvalidOperationException("The feedback URL must be local.");

					Game.RunAfterTick(() =>
					{
						CompanionBridge.UpdateLocalStatus("feedback", "FEEDBACK DRAFT SAVED  •  ADD YOUR NOTE IN BROWSER");
						try
						{
							Process.Start(new ProcessStartInfo
							{
								FileName = feedbackUri.AbsoluteUri,
								UseShellExecute = true,
							});
						}
						catch (Exception error)
						{
							Log.Write("debug", $"Feedback draft saved but could not open the browser: {error}");
						}
					});
				}
				catch (Exception e)
				{
					Log.Write("debug", $"Failed to capture OpenRA AI feedback: {e}");
					Game.RunAfterTick(() => CompanionBridge.UpdateLocalControlError(
						"FEEDBACK CAPTURE UNAVAILABLE  •  GAMEPLAY UNAFFECTED"));
				}
				finally
				{
					Game.RunAfterTick(() => feedbackRequestPending = false);
				}
			}

			bool HasPendingAction()
			{
				return CompanionBridge.TryGetStatus(out var state, out _) && state == "action-pending";
			}

			actionConfirmButton.GetText = () => actionRequestPending ? "WAIT" : "ACCEPT";
			actionCancelButton.GetText = () => "CANCEL";
			actionConfirmButton.IsVisible = HasPendingAction;
			actionCancelButton.IsVisible = HasPendingAction;
			actionConfirmButton.IsDisabled = () => actionRequestPending;
			actionCancelButton.IsDisabled = () => actionRequestPending;
			actionConfirmButton.IsHighlighted = HasPendingAction;
			actionConfirmButton.OnClick = () => _ = SubmitActionAsync("confirm");
			actionCancelButton.OnClick = () => _ = SubmitActionAsync("cancel");

			async Task SubmitActionAsync(string operation)
			{
				if (actionRequestPending || !HasPendingAction())
					return;

				actionRequestPending = true;
				try
				{
					var configuredUrl = Environment.GetEnvironmentVariable("OPENRA_AI_CONSOLE_URL");
					var baseUrl = string.IsNullOrWhiteSpace(configuredUrl) ? "http://127.0.0.1:8787/" : configuredUrl;
					if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var uri) || !uri.IsLoopback)
						throw new InvalidOperationException("The companion control URL must be local.");

					using var state = await OpenRAAILocalClient.GetAsync(uri, "v1/state");
					if (!state.RootElement.TryGetProperty("pending_action", out var pending)
						|| pending.ValueKind != JsonValueKind.Object)
						return;
					var proposalId = pending.GetProperty("proposal_id").GetString();
					var summary = pending.GetProperty("summary").GetString();
					if (operation == "confirm")
					{
						var review = new TaskCompletionSource<bool>();
						Game.RunAfterTick(() => ConfirmationDialogs.ButtonPrompt(modData,
							title: "dialog-ai-proposal-title", text: "dialog-ai-proposal-review",
							textArguments: ["summary", summary], onConfirm: () => review.TrySetResult(true),
							confirmText: "dialog-ai-proposal-confirm", onCancel: () => review.TrySetResult(false), cancelText: "button-back"));
						if (!await review.Task)
							return;
					}
					await OpenRAAIProposalClient.ApplyAsync(uri, proposalId, operation);
				}
				catch (Exception e)
				{
					Log.Write("debug", $"Failed to {operation} OpenRA AI action: {e}");
					Game.RunAfterTick(() => CompanionBridge.UpdateLocalControlError(
						"AI ACTION CONTROL UNAVAILABLE  •  NOTHING WAS SENT"));
				}
				finally
				{
					Game.RunAfterTick(() => actionRequestPending = false);
				}
			}

			bool AutoActEnabled()
			{
				return CompanionBridge.TryGetAutoAct(out var enabled) && enabled;
			}

			autoButton.GetText = () =>
			{
				var available = CompanionBridge.TryGetAutoAct(out var enabled);
				return AIControlDisplay.AutoButtonText(autoRequestPending, available, enabled);
			};
			autoButton.IsHighlighted = () => CompanionBridge.TryGetAutoAct(out var enabled) && enabled;
			autoButton.IsDisabled = () => autoRequestPending ||
				!CompanionBridge.TryGetAutoAct(out _) ||
				!CompanionBridge.TryGetStatus(out _, out _, out var enabled, out _) || !enabled;
			autoButton.OnClick = () => _ = SetAutoActAsync(!AutoActEnabled());

			async Task SetAutoActAsync(bool enabled)
			{
				if (autoRequestPending)
					return;

				autoRequestPending = true;
				try
				{
					var configuredUrl = Environment.GetEnvironmentVariable("OPENRA_AI_CONSOLE_URL");
					var baseUrl = string.IsNullOrWhiteSpace(configuredUrl) ? "http://127.0.0.1:8787/" : configuredUrl;
					if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var uri) || !uri.IsLoopback)
						throw new InvalidOperationException("The companion control URL must be local.");

					using var client = HttpClientFactory.Create();
					client.Timeout = TimeSpan.FromSeconds(6);
					using var content = new StringContent(
						JsonSerializer.Serialize(new { auto_act = enabled }), Encoding.UTF8, "application/json");
					using var response = await client.PostAsync(new Uri(uri, "v1/control"), content);
					response.EnsureSuccessStatusCode();
					using var result = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
					_ = result.RootElement.GetProperty("auto_act").GetBoolean();
				}
				catch (Exception e)
				{
					Log.Write("debug", $"Failed to update OpenRA AI auto mode: {e}");
					Game.RunAfterTick(() => CompanionBridge.UpdateLocalControlError(
						"AI AUTO CONTROL UNAVAILABLE  •  MANUAL PLAY UNAFFECTED"));
				}
				finally
				{
					Game.RunAfterTick(() => autoRequestPending = false);
				}
			}

			voiceButton.GetText = () => requestPending
				? FluentProvider.GetMessage(VoicePending)
				: CompanionBridge.TryGetStatus(out _, out _, out var enabled, out var muted) && enabled && !muted
					? FluentProvider.GetMessage(VoiceOn)
					: FluentProvider.GetMessage(VoiceOff);
			voiceButton.IsHighlighted = () =>
				CompanionBridge.TryGetStatus(out _, out _, out var enabled, out var muted) && enabled && !muted;
			voiceButton.IsDisabled = () => requestPending ||
				!CompanionBridge.TryGetStatus(out _, out _, out var enabled, out _) || !enabled;
			voiceButton.OnClick = () =>
			{
				if (!CompanionBridge.TryGetStatus(out _, out _, out var enabled, out var muted) || !enabled)
					return;

				_ = SetVoiceMutedAsync(!muted);
			};

			async Task SetVoiceMutedAsync(bool muted)
			{
				requestPending = true;
				try
				{
					var configuredUrl = Environment.GetEnvironmentVariable("OPENRA_AI_CONSOLE_URL");
					var baseUrl = string.IsNullOrWhiteSpace(configuredUrl) ? "http://127.0.0.1:8787/" : configuredUrl;
					if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var uri) || !uri.IsLoopback)
						throw new InvalidOperationException("The companion control URL must be local.");

					using var client = HttpClientFactory.Create();
					client.Timeout = TimeSpan.FromSeconds(4);
					using var content = new StringContent(JsonSerializer.Serialize(new { muted }), Encoding.UTF8, "application/json");
					using var response = await client.PostAsync(new Uri(uri, "v1/control"), content);
					response.EnsureSuccessStatusCode();
					using var result = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
					var appliedMuted = result.RootElement.GetProperty("muted").GetBoolean();
					Game.RunAfterTick(() => CompanionBridge.UpdateLocalVoiceState(appliedMuted));
				}
				catch (Exception e)
				{
					Log.Write("debug", $"Failed to update OpenRA AI voice state: {e}");
					Game.RunAfterTick(() => CompanionBridge.UpdateLocalControlError(
						"AI VOICE CONTROL UNAVAILABLE  •  GAMEPLAY UNAFFECTED"));
				}
				finally
				{
					Game.RunAfterTick(() => requestPending = false);
				}
			}

			// Keep secondary controls in the optional activity panel, not across the battlefield.
			foreach (var control in new Widget[] { feedbackButton, autoButton, voiceButton, askShortcut })
			{
				if (control == null)
					continue;
				widget.Children.Remove(control);
				feedPanel.AddChild(control);
			}

			widget.IsVisible = () =>
			{
				if (!CompanionBridge.HudAvailable || !CompanionBridge.TryGetStatus(out var state, out var message))
					return false;

				var (x, width, height) = CompanionHudDisplay.Layout(Game.Renderer.Resolution.Width, HasPendingAction());
				var voiceWidth = voiceButton.Bounds.Width = FitButton(voiceButton, VoiceButtonWidth);
				var autoWidth = autoButton.Bounds.Width = FitButton(autoButton, AutoButtonWidth);
				var feedWidthButton = feedToggleButton.Bounds.Width = FitButton(feedToggleButton, 78);
				var feedbackWidth = feedbackButton.Bounds.Width = FitButton(feedbackButton, FeedbackButtonWidth);
				var confirmWidth = actionConfirmButton.Bounds.Width = FitButton(actionConfirmButton, ActionConfirmButtonWidth);
				var cancelWidth = actionCancelButton.Bounds.Width = FitButton(actionCancelButton, ActionCancelButtonWidth);
				widget.Bounds.X = x;
				widget.Bounds.Width = width;
				widget.Bounds.Height = height;
				statusButton.Bounds.X = 12;
				statusButton.Bounds.Y = 27;
				statusButton.Bounds.Width = width - 24;
				statusButton.Bounds.Height = 32;
				displayMessage = FitToTwoLines(CompanionHudDisplay.Message(state, LocalizeShortcutMessage(message)), statusButton.Bounds.Width, font);
				feedToggleButton.Bounds.X = width - feedWidthButton - 8;
				feedToggleButton.Bounds.Y = 5;
				feedToggleButton.Bounds.Height = 24;
				actionConfirmButton.Bounds.X = width - confirmWidth - cancelWidth - 20;
				actionCancelButton.Bounds.X = width - cancelWidth - 12;
				actionConfirmButton.Bounds.Y = actionCancelButton.Bounds.Y = 70;
				actionConfirmButton.Bounds.Height = actionCancelButton.Bounds.Height = 26;
				threatLabel.Bounds.X = 12;
				threatLabel.Bounds.Y = 4;
				threatLabel.Bounds.Width = width - feedWidthButton - 36;
				threatLabel.Bounds.Height = 20;
				threatLabel.Align = TextAlign.Left;
				// A numerical threat meter suggests precision we cannot promise before an observation.
				threatTrack.IsVisible = () => false;
				threatFill.IsVisible = () => false;

				feedPanel.Bounds.X = 0;
				feedPanel.Bounds.Y = height + 6;
				feedPanel.Bounds.Width = width;
				feedPanel.Bounds.Height = FeedPanelHeight;
				LayoutFeed(width);
				feedPanel.Get<LabelWidget>("FEED_TITLE").Bounds.Width = Math.Max(70, width - 280);
				feedbackButton.Bounds.X = 12;
				autoButton.Bounds.X = feedbackWidth + 20;
				voiceButton.Bounds.X = feedbackWidth + autoWidth + 28;
				feedbackButton.Bounds.Y = autoButton.Bounds.Y = voiceButton.Bounds.Y = 300;
				feedbackButton.Bounds.Height = autoButton.Bounds.Height = voiceButton.Bounds.Height = 26;
				if (askShortcut != null)
				{
					askShortcut.Bounds.Y = 332;
					askShortcut.Bounds.Width = width - 16;
				}
				return true;
			};

			statusButton.GetText = () => displayMessage;
			statusButton.IsHighlighted = () => feedExpanded;
			threatLabel.GetText = () => CompanionBridge.TryGetThreat(out _, out var level, out var reason) && !string.IsNullOrWhiteSpace(reason)
				? $"ADVISER / {level.ToUpperInvariant()}" : "ADVISER";
			threatTrack.GetColor = () => Color.FromArgb(62, 66, 72);
			threatFill.GetColor = () => CompanionBridge.TryGetThreat(out _, out var level, out _)
				? ThreatColor(level)
				: Color.LightGreen;
			threatLabel.GetColor = () => CompanionBridge.TryGetThreat(out _, out var level, out _)
				? ThreatColor(level)
				: Color.LightGreen;
			statusButton.GetColor = () => Color.White;
		}

		public override void Tick()
		{
			if (!CompanionBridge.HudAvailable)
			{
				feedExpanded = false;
				return;
			}
			if (!postGameDebriefScheduled && !world.IsReplay && world.IsGameOver && world.LocalPlayer != null)
			{
				postGameDebriefScheduled = true;
				Game.RunAfterDelay(120, () =>
				{
					if (Game.IsCurrentWorld(world))
						OpenWarRoom("debrief");
				});
			}

			if (!CompanionBridge.TryGetStatus(out var state, out var message) || string.IsNullOrWhiteSpace(message))
				return;

			var signature = $"{state}\n{message}";
			if (signature == lastCapturedSignature)
				return;

			lastCapturedSignature = signature;
			if (!ShouldArchive(state, message))
				return;

			CompanionBridge.TryGetThreat(out var threatScore, out _, out _);
			AppendFeedEntry(state, CleanMessage(LocalizeShortcutMessage(message)), threatScore);
		}

		static void OpenWarRoom(string initialTab)
		{
			if (Ui.CurrentWindow()?.Id == "AI_WAR_ROOM_PANEL")
				return;

			try
			{
				Game.OpenWindow("AI_WAR_ROOM_PANEL", new WidgetArgs
				{
					{ "initialTab", initialTab },
					{ "onExit", () => { } },
				});
			}
			catch (System.IO.InvalidDataException)
			{
				// The War Room panel has not been ported to the mod yet (MIGRATION.md). Opening it used to
				// throw at every game over once the HUD was visible; the feed (LOG) stays available.
			}
		}

		void AppendFeedEntry(string state, string message, int threatScore)
		{
			var category = FeedCategory(state, message, threatScore);
			var color = FeedColor(state, message, threatScore);
			var meta = $"{DateTime.Now:HH:mm:ss} // {category} // THREAT {threatScore}";
			var isPlayer = state == "transcript";
			if (!showOnlyPlayer || isPlayer)
			{
				latestMeta = meta;
				latestMessage = message;
				latestColor = color;
			}

			var item = historyTemplate.Clone();
			item.IsVisible = () => !showOnlyPlayer || isPlayer;
			var cardBackground = item.Get<ColorBlockWidget>("CARD_BG");
			var cardAccent = item.Get<ColorBlockWidget>("CARD_ACCENT");
			var metaLabel = item.Get<LabelWidget>("CARD_META");
			var messageLabel = item.Get<LabelWidget>("CARD_MESSAGE");
			cardBackground.GetColor = () => Color.FromArgb(205, 10, 14, 18);
			cardAccent.GetColor = () => color;
			metaLabel.GetText = () => meta;
			metaLabel.GetColor = () => color;
			messageLabel.GetText = () => message;
			messageLabel.GetColor = () => Color.White;

			var entry = new FeedEntry(item, messageLabel, message, meta, color, isPlayer);
			LayoutFeedEntry(entry);
			historyPanel.AddChild(item);
			feedEntries.Add(entry);
			if (feedEntries.Count > MaxFeedEntries)
			{
				historyPanel.RemoveChild(feedEntries[0].Widget);
				feedEntries.RemoveAt(0);
			}

			historyPanel.ScrollToBottom();
		}

		int PlayerEntryCount()
		{
			var count = 0;
			foreach (var entry in feedEntries)
				if (entry.IsPlayer)
					count++;
			return count;
		}

		void SetPlayerFilter(bool playerOnly)
		{
			showOnlyPlayer = playerOnly;
			var found = false;
			for (var i = feedEntries.Count - 1; i >= 0; i--)
			{
				var entry = feedEntries[i];
				if (showOnlyPlayer && !entry.IsPlayer)
					continue;
				latestMeta = entry.Meta;
				latestMessage = entry.Message;
				latestColor = entry.Color;
				found = true;
				break;
			}
			if (!found && showOnlyPlayer)
			{
				latestMeta = "VOICE CHANNEL READY // NO TRANSMISSIONS";
				latestMessage = $"Hold {Binding("AIAsk")} and speak; every recognized transmission will be stored in this view.";
				latestColor = Color.Cyan;
			}
			historyPanel.Layout.AdjustChildren();
			historyPanel.ScrollToBottom();
		}

		void LayoutFeed(int feedWidth)
		{
			if (feedWidth == laidOutFeedWidth)
				return;

			laidOutFeedWidth = feedWidth;
			feedAccent.Bounds.Width = feedWidth;
			feedPanel.Get<LabelWidget>("FEED_TITLE").Bounds.Width = feedWidth - 260;
			feedPanel.Get<ButtonWidget>("FILTER_ALL").Bounds.X = feedWidth - 244;
			feedPanel.Get<ButtonWidget>("FILTER_YOU").Bounds.X = feedWidth - 206;
			feedPanel.Get<LabelWidget>("FEED_COUNT").Bounds.X = feedWidth - 162;
			feedPanel.Get<ButtonWidget>("FEED_CLOSE").Bounds.X = feedWidth - 32;
			feedPanel.Get<ColorBlockWidget>("FEED_HEADER_RULE").Bounds.Width = feedWidth - 20;
			feedPanel.Get<LabelWidget>("LATEST_KICKER").Bounds.Width = feedWidth - 24;
			latestMetaLabel.Bounds.Width = feedWidth - 24;
			latestMessageLabel.Bounds.Width = feedWidth - 24;
			feedPanel.Get<ColorBlockWidget>("FEED_HISTORY_RULE").Bounds.Width = feedWidth - 20;
			historyPanel.Bounds.Width = feedWidth - 16;
			historyTemplate.Bounds.Width = historyPanel.Bounds.Width - 35;
			feedEmptyLabel.Bounds.Width = feedWidth - 48;
			feedPanel.Get<LabelWidget>("FEED_FOOTER").Bounds.Width = feedWidth - 24;

			foreach (var entry in feedEntries)
				LayoutFeedEntry(entry);
			historyPanel.Layout.AdjustChildren();
			if (feedExpanded)
				historyPanel.ScrollToBottom();
		}

		void LayoutFeedEntry(FeedEntry entry)
		{
			entry.Widget.Bounds.Width = Math.Max(120, historyPanel.Bounds.Width - 35);
			var cardBackground = entry.Widget.Get<ColorBlockWidget>("CARD_BG");
			var cardAccent = entry.Widget.Get<ColorBlockWidget>("CARD_ACCENT");
			var metaLabel = entry.Widget.Get<LabelWidget>("CARD_META");
			entry.MessageLabel.Bounds.Width = entry.Widget.Bounds.Width - 16;
			metaLabel.Bounds.Width = entry.Widget.Bounds.Width - 16;
			var messageFont = Game.Renderer.Fonts[entry.MessageLabel.Font];
			var wrapped = WidgetUtils.WrapText(entry.Message, entry.MessageLabel.Bounds.Width, messageFont);
			entry.MessageLabel.Bounds.Height = Math.Max(22, messageFont.Measure(wrapped).Y);
			entry.Widget.Bounds.Height = entry.MessageLabel.Bounds.Y + entry.MessageLabel.Bounds.Height + 7;
			cardBackground.Bounds.Width = entry.Widget.Bounds.Width;
			cardBackground.Bounds.Height = entry.Widget.Bounds.Height;
			cardAccent.Bounds.Height = entry.Widget.Bounds.Height;
		}

		string Binding(string name)
		{
			var key = modData.Hotkeys[name].GetValue();
			return key.IsValid() ? key.DisplayString() : "Unbound";
		}

		string LocalizeShortcutMessage(string message)
		{
			return message
				.Replace("CTRL+SPACE", Binding("AIAsk").ToUpperInvariant(), StringComparison.OrdinalIgnoreCase)
				.Replace("CTRL+SHIFT+A", Binding("AIToggleAuto").ToUpperInvariant(), StringComparison.OrdinalIgnoreCase)
				.Replace("CTRL+SHIFT+M", Binding("AIToggleVoice").ToUpperInvariant(), StringComparison.OrdinalIgnoreCase)
				.Replace("ASK KEY", Binding("AIAsk").ToUpperInvariant(), StringComparison.OrdinalIgnoreCase);
		}

		static bool ShouldArchive(string state, string message)
		{
			if (state == "ready")
				return message.Contains("INTERRUPTED", StringComparison.OrdinalIgnoreCase);

			return state is not ("listening" or "transcribing" or "thinking" or "muted" or "disabled");
		}

		static string CleanMessage(string message)
		{
			if (message.StartsWith("AI", StringComparison.Ordinal) || message.StartsWith("YOU", StringComparison.Ordinal))
			{
				var firstSeparator = message.IndexOf("  ", StringComparison.Ordinal);
				var secondSeparator = firstSeparator < 0
					? -1
					: message.IndexOf("  ", firstSeparator + 2, StringComparison.Ordinal);
				if (secondSeparator >= 0 && secondSeparator + 2 < message.Length)
					return message[(secondSeparator + 2)..].Trim();
			}

			return message.Trim();
		}

		static string FeedCategory(string state, string message, int threatScore)
		{
			if (state == "transcript")
				return "YOU // VOICE";
			if (state == "capabilities")
				return "SYSTEM // MCP ONLINE";
			if (state.StartsWith("auto-active", StringComparison.Ordinal))
				return "SYSTEM // NATIVE AI ASSISTANT";
			if (state == "action-pending")
				return "ORDER // AWAITING CONFIRM";
			if (state == "action-executed")
				return "ORDER // EXECUTED";
			if (state is "action-rejected" or "action-cancelled")
				return "ORDER // NOT EXECUTED";
			if (state == "error")
				return "SYSTEM // DEGRADED";
			if (message.Contains("harvester", StringComparison.OrdinalIgnoreCase))
				return "ECONOMY // ATTENTION";
			if (message.Contains("power", StringComparison.OrdinalIgnoreCase))
				return "BASE // POWER";
			if (message.Contains("damage", StringComparison.OrdinalIgnoreCase))
				return "ASSET // DAMAGE";
			if (threatScore >= 70)
				return "ALERT // CRITICAL";
			if (threatScore >= 45)
				return "ALERT // HIGH";
			if (state.Contains("important", StringComparison.Ordinal))
				return "TACTICAL // PRIORITY";
			return "AI // ADVISORY";
		}

		static Color FeedColor(string state, string message, int threatScore)
		{
			if (state is "listening" or "transcript")
				return Color.Cyan;
			if (state is "transcribing" or "thinking" or "action-pending")
				return Color.Gold;
			if (state is "speaking" or "insight" or "routine" or "action-executed" ||
				state.StartsWith("auto-active", StringComparison.Ordinal))
				return Color.LightGreen;
			if (state is "error" or "action-rejected" ||
				message.Contains("critically damaged", StringComparison.OrdinalIgnoreCase))
				return Color.OrangeRed;
			if (state is "muted" or "disabled" or "action-cancelled")
				return Color.Gray;
			if (message.Contains("harvester", StringComparison.OrdinalIgnoreCase) ||
				message.Contains("power", StringComparison.OrdinalIgnoreCase))
				return Color.Gold;
			if (threatScore >= 70)
				return Color.OrangeRed;
			if (threatScore >= 45)
				return Color.FromArgb(244, 134, 67);
			if (state.Contains("important", StringComparison.Ordinal) ||
				state.Contains("critical", StringComparison.Ordinal))
				return Color.Gold;
			return Color.White;
		}

		static Color ThreatColor(string level)
		{
			return level switch
			{
				"critical" => Color.OrangeRed,
				"high" => Color.FromArgb(244, 134, 67),
				"guarded" => Color.Gold,
				_ => Color.LightGreen
			};
		}

		static int FitButton(ButtonWidget button, int minimumWidth)
		{
			var text = button.GetText();
			if (string.IsNullOrEmpty(text))
				return minimumWidth;

			return Math.Max(minimumWidth, Game.Renderer.Fonts[button.Font].Measure(text).X + 2 * ButtonTextPadding);
		}

		static string FitToTwoLines(string message, int width, SpriteFont font)
		{
			var wrapped = WidgetUtils.WrapText(message, width, font);
			var firstBreak = wrapped.IndexOf('\n');
			if (firstBreak < 0)
				return WidgetUtils.TruncateText(wrapped, width, font);

			var firstLine = WidgetUtils.TruncateText(wrapped[..firstBreak], width, font);
			var remaining = wrapped[(firstBreak + 1)..];
			var secondBreak = remaining.IndexOf('\n');
			if (secondBreak < 0)
				return $"{firstLine}\n{WidgetUtils.TruncateText(remaining, width, font)}";

			remaining = remaining.Replace('\n', ' ');
			return $"{firstLine}\n{WidgetUtils.TruncateText(remaining, width, font)}";
		}

		static string FitToLines(string message, int width, SpriteFont font, int maximumLines)
		{
			var wrapped = WidgetUtils.WrapText(message, width, font);
			var lines = wrapped.Split('\n');
			if (lines.Length <= maximumLines)
				return wrapped;

			var result = new StringBuilder();
			for (var i = 0; i < maximumLines; i++)
			{
				if (i > 0)
					result.Append('\n');

				var line = i == maximumLines - 1
					? string.Join(" ", lines, i, lines.Length - i)
					: lines[i];
				result.Append(WidgetUtils.TruncateText(line, width, font));
			}

			return result.ToString();
		}
	}
}
