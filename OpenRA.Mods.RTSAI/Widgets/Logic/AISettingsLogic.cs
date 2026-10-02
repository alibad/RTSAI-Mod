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
using System.Text.Json;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.Common.Widgets.Logic;
using OpenRA.Mods.RTSAI.Traits;
using OpenRA.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	public static class AISettingsDisplay
	{
		public static string DownloadButton(long bytes) => $"INSTALL {bytes / 1_000_000_000d:0.0} GB PACK";

		public static string AskShortcut(string binding)
		{
			return $"HOLD {binding.ToUpperInvariant()} TO TALK";
		}

		public static string DiagnosticFailure(bool localSelected, bool localReady)
		{
			return localSelected && !localReady
				? "Local AI is not installed yet. Open Models and select Install Local AI."
				: "The selected AI service is unavailable. Check Models, then retry the diagnostic.";
		}
	}

	public class AISettingsLogic : ChromeLogic
	{
		const string DefaultAILayerUrl = "http://127.0.0.1:4000";

		static readonly Dictionary<string, string> SelectionLabels = new()
		{
			{ "auto", "Automatic — recommended" },
			{ "lightweight", "Lightweight — protect game performance" },
			{ "recommended", "Balanced — includes map images" },
			{ "manual", "Manual — advanced settings" }
		};

		static readonly Dictionary<string, string> PaceLabels = new()
		{
			{ "calm", "Calm" },
			{ "balanced", "Balanced" },
			{ "frequent", "Frequent" }
		};

		static readonly Dictionary<string, string> VoicePriorityLabels = new()
		{
			{ "critical", "Critical only" },
			{ "important", "Important + critical" },
			{ "off", "Never for updates" }
		};

		static readonly Dictionary<string, string> StrategyLabels = new()
		{
			{ "adaptive", "Adaptive - assistant chooses" },
			{ "normal", "Balanced - Normal native AI" },
			{ "rush", "Aggressive - Rush native AI" },
			{ "turtle", "Fortified - Turtle native AI" },
			{ "naval", "Naval control - Naval native AI" },
			{ "medium", "Measured - Medium native AI" }
		};

		static readonly Dictionary<string, string> DefaultProviderLabels = new()
		{
			{ "openai", "OpenAI" },
			{ "anthropic", "Anthropic / Claude" },
			{ "gemini", "Google / Gemini" },
			{ "local", "On-device AI" },
			{ "custom", "Custom endpoint" }
		};

		static readonly Dictionary<string, string> DefaultVoiceLabels = new()
		{
			{ "alloy", "Alloy" },
			{ "echo", "Echo" },
			{ "fable", "Fable" },
			{ "onyx", "Onyx" },
			{ "nova", "Nova" },
			{ "shimmer", "Shimmer" }
		};

		sealed class ModelOption
		{
			public string Id { get; init; }
			public string Label { get; init; }
			public string Provider { get; init; }
			public string Mode { get; init; }
		}

		readonly Dictionary<string, string> providerLabels = new(DefaultProviderLabels);
		readonly Dictionary<string, string> voiceLabels = new(DefaultVoiceLabels);
		readonly List<ModelOption> models =
		[
			new() { Id = "gpt-5.5", Label = "GPT-5.5", Provider = "openai", Mode = "chat" },
			new() { Id = "claude-opus", Label = "Claude Opus", Provider = "anthropic", Mode = "chat" },
			new() { Id = "claude-sonnet", Label = "Claude Sonnet", Provider = "anthropic", Mode = "chat" },
			new() { Id = "claude-haiku", Label = "Claude Haiku", Provider = "anthropic", Mode = "chat" },
			new() { Id = "gemini-pro", Label = "Gemini Pro", Provider = "gemini", Mode = "chat" },
			new() { Id = "gemini-flash", Label = "Gemini Flash", Provider = "gemini", Mode = "chat" },
			new() { Id = "local-coder", Label = "On-device assistant", Provider = "local", Mode = "chat" },
			new() { Id = "openai-transcribe", Label = "OpenAI Transcription", Provider = "openai", Mode = "audio_transcription" },
			new() { Id = "local-whisper", Label = "Local Whisper", Provider = "local", Mode = "audio_transcription" },
			new() { Id = "openai-tts", Label = "OpenAI Voice", Provider = "openai", Mode = "audio_speech" },
			new() { Id = "local-kokoro", Label = "Local Voice", Provider = "local", Mode = "audio_speech" }
		];

		bool companionEnabled = true;
		bool advancedModels;
		string modelSelection = "auto";
		string selectionSummary = "Automatic selects a tested profile for this computer and reserves resources for the game.";
		string selectedModelDetail = "";
		string readinessSummary = "Assistant, voice input, and spoken replies: checking…";
		long downloadBytes = 1821003048;
		bool voiceEnabled = true;
		bool busy;
		bool localInstallBusy;
		bool catalogueAvailable;
		bool localSetupSupported;
		bool localSetupInstalled;
		string localSetupState = "not_installed";
		string localSetupDetail = "Checking Local AI Pack…";
		int localSetupProgress;
		string provider = "local";
		string pace = "calm";
		string voicePriority = "critical";
		string nativeStrategy = "adaptive";
		string textModel = "local-coder";
		string visionModel = "local-coder";
		string transcribeModel = "local-whisper";
		string speechModel = "local-kokoro";
		string speechVoice = "alloy";
		string selectedTab = "assistant";
		string aiLayerUrl = DefaultAILayerUrl;
		string status = "Connecting to the AI layer...";
		string costTotal = "Session estimate: waiting for usage";
		string costBreakdown = "Text --  |  Speech --  |  Transcription --";
		string costAssumptions = "Estimates appear after the companion reports its active routes.";

		ScrollPanelWidget scrollPanel;
		TextFieldWidget customEndpoint;
		TextFieldWidget customTextModel;
		TextFieldWidget customVisionModel;
		LabelWidget statusLabel;
		LabelWidget providerStatusLabel;
		LabelWidget costAssumptionsLabel;
		LabelWidget localSetupStatusLabel;
		readonly ModData modData;

		[ObjectCreator.UseCtor]
		public AISettingsLogic(ModData modData, SettingsLogic settingsLogic, string panelID, string label)
		{
			this.modData = modData;
			settingsLogic.RegisterSettingsPanel(panelID, label, InitPanel, ResetPanel);
		}

		Func<bool> InitPanel(Widget panel)
		{
			scrollPanel = panel.Get<ScrollPanelWidget>("SETTINGS_SCROLLPANEL");
			BindTab(panel.Get<ButtonWidget>("ASSISTANT_TAB"), "assistant");
			BindTab(panel.Get<ButtonWidget>("VOICE_TAB"), "voice");
			BindTab(panel.Get<ButtonWidget>("MODELS_TAB"), "models");
			BindTab(panel.Get<ButtonWidget>("USAGE_TAB"), "usage");

			foreach (var id in new[]
			{
				"COMPANION_SECTION_HEADER", "COMPANION_ENABLED_ROW", "COMPANION_PACE_ROW",
				"STRATEGY_BRAIN_ROW", "SHORTCUTS_HINT_ROW"
			})
				panel.Get(id).IsVisible = () => selectedTab == "assistant";
			foreach (var id in new[] { "VOICE_SECTION_HEADER", "VOICE_SHORTCUT_ROW", "VOICE_ENABLED_ROW", "VOICE_PRIORITY_ROW", "VOICE_ROUTES_ROW" })
				panel.Get(id).IsVisible = () => selectedTab == "voice";
			foreach (var id in new[] { "MODEL_SECTION_HEADER", "LOCAL_SETUP_ROW", "MODEL_PICKER_ROW" })
				panel.Get(id).IsVisible = () => selectedTab == "models";
			panel.Get("LOCAL_SETUP_ROW").IsVisible = () => selectedTab == "models" && provider == "local";
			panel.Get("AUTO_PROFILE_ROW").IsVisible = () => selectedTab == "models" && provider == "local";
			panel.Get("MODEL_READINESS_ROW").IsVisible = () => selectedTab is "models" or "voice";
			panel.Get("ADVANCED_MODELS_ROW").IsVisible = () => selectedTab == "models";
			panel.Get("MODEL_PICKER_ROW").IsVisible = () => selectedTab == "models" && advancedModels;
			BindDropdown(panel.Get<DropDownButtonWidget>("MODEL_SELECTION"), () => SelectionLabels,
				() => modelSelection, value =>
				{
					modelSelection = value;
					SetStatus("Select Apply Now, then relaunch to use the new profile. The current download/profile is unchanged.");
				});
			panel.Get<LabelWidget>("MODEL_SELECTION_SUMMARY").GetText = () => selectionSummary + (advancedModels ? $"\n{selectedModelDetail}" : "");
			panel.Get<LabelWidget>("MODEL_READINESS").GetText = () => readinessSummary;
			var advanced = panel.Get<ButtonWidget>("ADVANCED_MODELS");
			advanced.GetText = () => advancedModels ? "HIDE ADVANCED MODEL SETTINGS" : "ADVANCED: MODELS AND PROVIDERS";
			advanced.OnClick = () =>
			{
				advancedModels = !advancedModels;
				SettingsUtils.AdjustSettingsScrollPanelLayout(scrollPanel);
			};
			panel.Get("LM_STUDIO_ROW").IsVisible = () => selectedTab == "models" && advancedModels;
			var discover = panel.Get<ButtonWidget>("DISCOVER_LM_STUDIO");
			discover.GetText = () => "DETECT LOCAL LM STUDIO";
			discover.IsDisabled = () => busy;
			discover.OnClick = () => _ = DiscoverLMStudioAsync();
			foreach (var id in new[] { "COST_SECTION_HEADER", "COST_ROW" })
				panel.Get(id).IsVisible = () => selectedTab == "usage";

			var enabled = panel.Get<CheckboxWidget>("AI_ENABLED");
			enabled.IsChecked = () => companionEnabled;
			enabled.OnClick = () => companionEnabled = !companionEnabled;
			var voice = panel.Get<CheckboxWidget>("VOICE_ENABLED");
			voice.IsChecked = () => voiceEnabled;
			voice.OnClick = () => voiceEnabled = !voiceEnabled;

			BindDropdown(panel.Get<DropDownButtonWidget>("PACE"), () => PaceLabels, () => pace, value => pace = value);
			BindDropdown(panel.Get<DropDownButtonWidget>("VOICE_PRIORITY"), () => VoicePriorityLabels,
				() => voicePriority, value => voicePriority = value);
			BindDropdown(panel.Get<DropDownButtonWidget>("STRATEGY_BRAIN"), () => StrategyLabels,
				() => nativeStrategy, value => nativeStrategy = value);

			BindDropdown(panel.Get<DropDownButtonWidget>("PROVIDER"), () => providerLabels, () => provider, SelectProvider);
			BindDropdown(panel.Get<DropDownButtonWidget>("TEXT_MODEL"),
				() => ModelLabels("chat", provider, textModel), () => textModel, value => textModel = value);
			BindDropdown(panel.Get<DropDownButtonWidget>("VISION_MODEL"),
				() => ModelLabels("chat", provider, visionModel), () => visionModel, value => visionModel = value);
			BindDropdown(panel.Get<DropDownButtonWidget>("TRANSCRIBE_MODEL"),
				() => ModelLabels("audio_transcription", null, transcribeModel), () => transcribeModel, value => transcribeModel = value);
			BindDropdown(panel.Get<DropDownButtonWidget>("SPEECH_MODEL"),
				() => ModelLabels("audio_speech", null, speechModel), () => speechModel, value => speechModel = value);
			BindDropdown(panel.Get<DropDownButtonWidget>("SPEECH_VOICE"), () => voiceLabels,
				() => speechVoice, value => speechVoice = value);
			panel.Get("TEXT_MODEL_CONTAINER").IsVisible = () => selectedTab == "models" && advancedModels && provider != "custom";
			panel.Get("VISION_PICKER_ROW").IsVisible = () => selectedTab == "models" && advancedModels && provider != "custom";
			panel.Get("VOICE_ROUTES_ROW").IsVisible = () => selectedTab == "voice" && (advancedModels || provider != "local");

			customEndpoint = panel.Get<TextFieldWidget>("CUSTOM_ENDPOINT");
			customTextModel = panel.Get<TextFieldWidget>("CUSTOM_TEXT_MODEL");
			customVisionModel = panel.Get<TextFieldWidget>("CUSTOM_VISION_MODEL");
			panel.Get("CUSTOM_ENDPOINT_ROW").IsVisible = () => selectedTab == "models" && advancedModels && provider == "custom";
			panel.Get("CUSTOM_MODELS_ROW").IsVisible = () => selectedTab == "models" && advancedModels && provider == "custom";
			panel.Get<LabelWidget>("ASK_SHORTCUT").GetText = () => AISettingsDisplay.AskShortcut(Binding("AIAsk"));
			panel.Get<LabelWidget>("ASK_SHORTCUT_HINT").GetText = () =>
				"Release to send. Remap under Settings > Hotkeys > AI Assistant.";
			panel.Get<LabelWidget>("SHORTCUTS_HINT").GetText = () =>
				$"Ask: {Binding("AIAsk")}  |  AUTO: {Binding("AIToggleAuto")}  |  Voice: {Binding("AIToggleVoice")}  |  Remap under Hotkeys > AI Assistant.";
			localSetupStatusLabel = panel.Get<LabelWidget>("LOCAL_SETUP_STATUS");
			localSetupStatusLabel.GetText = LocalSetupStatus;
			var installLocal = panel.Get<ButtonWidget>("INSTALL_LOCAL_AI");
			installLocal.GetText = LocalSetupButtonText;
			installLocal.IsDisabled = () => busy || localInstallBusy || !localSetupSupported || localSetupState == "running";
			installLocal.OnClick = () => _ = InstallLocalAIAsync();

			providerStatusLabel = panel.Get<LabelWidget>("PROVIDER_STATUS");
			providerStatusLabel.GetText = ProviderStatus;
			statusLabel = panel.Get<LabelWidget>("STATUS");
			statusLabel.GetText = () => status;
			panel.Get<LabelWidget>("COST_TOTAL").GetText = () => costTotal;
			panel.Get<LabelWidget>("COST_BREAKDOWN").GetText = () => costBreakdown;
			costAssumptionsLabel = panel.Get<LabelWidget>("COST_ASSUMPTIONS");
			costAssumptionsLabel.GetText = () => costAssumptions;

			var apply = panel.Get<ButtonWidget>("APPLY");
			apply.IsDisabled = () => busy;
			apply.OnClick = () => _ = ApplyAsync();
			var test = panel.Get<ButtonWidget>("TEST");
			test.IsDisabled = () => busy || (provider == "local" && localSetupState != "running");
			test.OnClick = () => _ = TestAsync();
			var refresh = panel.Get<ButtonWidget>("REFRESH_USAGE");
			refresh.IsDisabled = () => busy;
			refresh.OnClick = () => _ = LoadAsync();
			SettingsUtils.AdjustSettingsScrollPanelLayout(scrollPanel);
			_ = LoadAsync();
			return () =>
			{
				YieldTextFocus();
				return false;
			};
		}

		Action ResetPanel(Widget panel)
		{
			return () =>
			{
				companionEnabled = true;
				voiceEnabled = true;
				selectedTab = "assistant";
				provider = "local";
				pace = "calm";
				voicePriority = "critical";
				nativeStrategy = "adaptive";
				modelSelection = "auto";
				advancedModels = false;
				textModel = "local-coder";
				visionModel = "local-coder";
				transcribeModel = "local-whisper";
				speechModel = "local-kokoro";
				speechVoice = "alloy";
				aiLayerUrl = DefaultAILayerUrl;
				customEndpoint.Text = DefaultAILayerUrl;
				customTextModel.Text = "model-name";
				customVisionModel.Text = "model-name";
				SettingsUtils.AdjustSettingsScrollPanelLayout(scrollPanel);
				_ = ApplyAsync();
			};
		}

		void BindTab(ButtonWidget button, string tab)
		{
			button.IsHighlighted = () => selectedTab == tab;
			button.OnClick = () =>
			{
				selectedTab = tab;
				SettingsUtils.AdjustSettingsScrollPanelLayout(scrollPanel);
				scrollPanel.ScrollToTop();
			};
		}

		void BindDropdown(DropDownButtonWidget dropdown, Func<Dictionary<string, string>> getOptions,
			Func<string> getValue, Action<string> setValue)
		{
			dropdown.GetText = () =>
			{
				var options = getOptions();
				return options.TryGetValue(getValue(), out var value) ? value : getValue();
			};
			dropdown.OnMouseDown = _ =>
			{
				var options = getOptions();
				ScrollItemWidget SetupItem(string key, ScrollItemWidget template)
				{
					var item = ScrollItemWidget.Setup(template, () => getValue() == key, () => setValue(key));
					item.Get<LabelWidget>("LABEL").GetText = () => options[key];
					return item;
				}

				dropdown.ShowDropDown("LABEL_DROPDOWN_TEMPLATE", 300, options.Keys, SetupItem);
			};
		}

		Dictionary<string, string> ModelLabels(string mode, string modelProvider, string current)
		{
			var options = models
				.Where(model => model.Mode == mode && (modelProvider == null || model.Provider == modelProvider))
				.ToDictionary(model => model.Id, model => model.Label);
			if (!string.IsNullOrEmpty(current) && !options.ContainsKey(current))
				options[current] = current;
			return options;
		}

		void SelectProvider(string value)
		{
			if (provider == value)
				return;
			provider = value;
			if (provider == "custom")
			{
				customEndpoint.Text = string.IsNullOrWhiteSpace(customEndpoint.Text) ? DefaultAILayerUrl : customEndpoint.Text;
				customTextModel.Text = textModel;
				customVisionModel.Text = visionModel;
			}
			else
			{
				var compatible = models.Where(model => model.Mode == "chat" && model.Provider == provider).ToList();
				if (compatible.Count > 0)
				{
					textModel = compatible[0].Id;
					visionModel = compatible[0].Id;
				}
			}

			SettingsUtils.AdjustSettingsScrollPanelLayout(scrollPanel);
		}

		string ProviderStatus()
		{
			string message;
			if (provider == "custom")
				message = "Custom OpenAI-compatible endpoint. You control the URL and model IDs.";
			else if (provider == "local")
				message = localSetupState == "running"
					? "Local models are installed and ready. Voice and answers stay on this computer."
					: localSetupDetail;
			else
				message = "Credentials and routing are managed by the AI layer. No endpoint URL is needed.";
			if (!catalogueAvailable && provider != "local")
				message = "The selected AI service is offline. Configure a reachable endpoint before testing.";
			return WidgetUtils.TruncateText(message, providerStatusLabel.Bounds.Width,
				Game.Renderer.Fonts[providerStatusLabel.Font]);
		}

		async System.Threading.Tasks.Task LoadAsync()
		{
			SetBusy("Reading AI settings...");
			try
			{
				var baseUri = OpenRAAILocalClient.GetBaseUri("OPENRA_AI_CONSOLE_URL", "http://127.0.0.1:8787/");
				using var stateDocument = await OpenRAAILocalClient.GetAsync(baseUri, "v1/state");
				var state = stateDocument.RootElement.Clone();
				JsonElement catalogue = default;
				var hasCatalogue = false;
				try
				{
					using var catalogueDocument = await OpenRAAILocalClient.GetAsync(baseUri, "v1/catalog");
					catalogue = catalogueDocument.RootElement.Clone();
					hasCatalogue = true;
				}
				catch { }
				Game.RunAfterTick(() =>
				{
					if (hasCatalogue)
						ApplyCatalogue(catalogue);
					ApplyState(state, localSetupState == "running"
						? "AI and voice models are ready."
						: "Companion ready. Open Models to finish Local AI setup.");
				});
			}
			catch (Exception e)
			{
				Game.RunAfterTick(() => SetIdle($"AI layer unavailable: {e.Message}"));
			}
		}

		async System.Threading.Tasks.Task ApplyAsync()
		{
			YieldTextFocus();
			SetBusy("Saving AI settings...");
			try
			{
				var baseUri = OpenRAAILocalClient.GetBaseUri("OPENRA_AI_CONSOLE_URL", "http://127.0.0.1:8787/");
				using var document = await OpenRAAILocalClient.PostAsync(baseUri, "v1/state", BuildPayload());
				var snapshot = document.RootElement.Clone();
				Game.RunAfterTick(() => ApplyState(snapshot, "Settings saved. Local AI profile changes take effect next launch."));
			}
			catch (Exception e)
			{
				Game.RunAfterTick(() => SetIdle($"Could not save AI settings: {e.Message}"));
			}
		}

		async System.Threading.Tasks.Task DiscoverLMStudioAsync()
		{
			SetBusy("Checking your local LM Studio server…");
			try
			{
				var baseUri = OpenRAAILocalClient.GetBaseUri("OPENRA_AI_CONSOLE_URL", "http://127.0.0.1:8787/");
				using var document = await OpenRAAILocalClient.GetAsync(baseUri, "v1/lm-studio");
				var root = document.RootElement.Clone();
				Game.RunAfterTick(() =>
				{
					if (!root.TryGetProperty("suggested", out var model) || model.ValueKind == JsonValueKind.Null)
					{
						SetIdle("No tool-capable LM Studio model fits the game memory budget. Your current AI is unchanged.");
						return;
					}
					provider = "custom";
					modelSelection = "manual";
					customEndpoint.Text = root.GetProperty("endpoint").GetString();
					customTextModel.Text = model.GetProperty("id").GetString();
					customVisionModel.Text = model.GetProperty("supports_vision").GetBoolean() ? customTextModel.Text : "local-no-vision";
					SettingsUtils.AdjustSettingsScrollPanelLayout(scrollPanel);
					SetIdle($"Detected {model.GetProperty("label").GetString()}. Select Apply Now to use it; this does not download models.");
				});
			}
			catch (Exception)
			{
				Game.RunAfterTick(() => SetIdle("Start LM Studio's local server on port 1234, then retry. Token-protected discovery is not supported yet."));
			}
		}

		async System.Threading.Tasks.Task TestAsync()
		{
			SetBusy("Testing the selected model and voice...");
			try
			{
				var baseUri = OpenRAAILocalClient.GetBaseUri("OPENRA_AI_CONSOLE_URL", "http://127.0.0.1:8787/");
				using var savedState = await OpenRAAILocalClient.PostAsync(baseUri, "v1/state", BuildPayload());
				using var document = await OpenRAAILocalClient.PostAsync(baseUri, "v1/test/full", new { }, 45);
				var root = document.RootElement;
				var latency = root.GetProperty("text").GetProperty("latency_ms").GetInt32();
				var speechPlayed = root.GetProperty("ok").GetBoolean();
				Game.RunAfterTick(() =>
				{
					SetIdle(speechPlayed
						? $"Diagnostic passed. The model replied in {latency} ms and voice played locally."
						: $"The model passed in {latency} ms. Enable AI voice to include speech in this test.");
					_ = RefreshUsageAsync();
				});
			}
			catch (Exception)
			{
				Game.RunAfterTick(() => SetIdle(AISettingsDisplay.DiagnosticFailure(
					provider == "local", localSetupState == "running")));
			}
		}

		async System.Threading.Tasks.Task InstallLocalAIAsync()
		{
			localInstallBusy = true;
			SetStatus("Starting the verified Local AI Pack download…");
			try
			{
				var baseUri = OpenRAAILocalClient.GetBaseUri("OPENRA_AI_CONSOLE_URL", "http://127.0.0.1:8787/");
				var route = localSetupState == "error" ? "v1/local-ai/retry" : "v1/local-ai/install";
				using (var response = await OpenRAAILocalClient.PostAsync(baseUri, route, new { }))
				{
					var initial = response.RootElement.Clone();
					Game.RunAfterTick(() => ApplyLocalSetup(initial));
				}

				for (var attempt = 0; attempt < 3600; attempt++)
				{
					await System.Threading.Tasks.Task.Delay(1000);
					using var response = await OpenRAAILocalClient.GetAsync(baseUri, "v1/local-ai");
					var snapshot = response.RootElement.Clone();
					var state = snapshot.GetProperty("state").GetString() ?? "error";
					Game.RunAfterTick(() => ApplyLocalSetup(snapshot));
					if (state is not ("installing" or "starting" or "ready"))
					{
						if (state == "running")
							_ = LoadAsync();
						break;
					}
				}
			}
			catch (Exception)
			{
				Game.RunAfterTick(() =>
				{
					localSetupState = "error";
					localSetupDetail = "Local AI setup could not continue. Select Retry to resume safely.";
					SetStatus(localSetupDetail);
				});
			}
			finally
			{
				Game.RunAfterTick(() => localInstallBusy = false);
			}
		}

		Dictionary<string, object> BuildPayload()
		{
			var custom = provider == "custom";
			return new Dictionary<string, object>
			{
				{ "companion_enabled", companionEnabled },
				{ "voice_enabled", voiceEnabled },
				{ "notification_pace", pace },
				{ "voice_priority", voicePriority },
				{ "native_strategy", nativeStrategy },
				{ "model_provider", provider },
				{ "model_selection", modelSelection },
				{ "router_url", custom ? customEndpoint.Text.Trim() : aiLayerUrl },
				{ "text_model", custom ? customTextModel.Text.Trim() : textModel },
				{ "vision_model", custom ? customVisionModel.Text.Trim() : visionModel },
				{ "transcribe_model", transcribeModel },
				{ "speech_model", speechModel },
				{ "speech_voice", speechVoice }
			};
		}

		async System.Threading.Tasks.Task RefreshUsageAsync()
		{
			try
			{
				var baseUri = OpenRAAILocalClient.GetBaseUri("OPENRA_AI_CONSOLE_URL", "http://127.0.0.1:8787/");
				using var document = await OpenRAAILocalClient.GetAsync(baseUri, "v1/usage");
				var usage = document.RootElement.Clone();
				Game.RunAfterTick(() => ApplyUsage(usage));
			}
			catch { }
		}

		void ApplyCatalogue(JsonElement root)
		{
			catalogueAvailable = root.TryGetProperty("router_available", out var available) && available.GetBoolean();
			if (root.TryGetProperty("local_setup", out var localSetup))
				ApplyLocalSetup(localSetup);
			providerLabels.Clear();
			foreach (var value in root.GetProperty("providers").EnumerateArray())
				providerLabels[value.GetProperty("id").GetString()] = value.GetProperty("label").GetString();

			models.Clear();
			foreach (var value in root.GetProperty("models").EnumerateArray())
			{
				models.Add(new ModelOption
				{
					Id = value.GetProperty("id").GetString(),
					Label = value.GetProperty("label").GetString(),
					Provider = value.GetProperty("provider").GetString(),
					Mode = value.GetProperty("mode").GetString()
				});
			}

			voiceLabels.Clear();
			foreach (var value in root.GetProperty("voices").EnumerateArray())
				voiceLabels[value.GetProperty("id").GetString()] = value.GetProperty("label").GetString();
			SettingsUtils.AdjustSettingsScrollPanelLayout(scrollPanel);
		}

		void ApplyLocalSetup(JsonElement root)
		{
			localSetupSupported = root.TryGetProperty("supported", out var supported) && supported.GetBoolean();
			localSetupInstalled = root.TryGetProperty("installed", out var installed) && installed.GetBoolean();
			localSetupState = root.TryGetProperty("state", out var state)
				? state.GetString() ?? "not_installed"
				: "not_installed";
			localSetupDetail = root.TryGetProperty("detail", out var detail)
				? detail.GetString() ?? "Local AI setup status unavailable."
				: "Local AI setup status unavailable.";
			localSetupProgress = root.TryGetProperty("progress_percent", out var progress) ? progress.GetInt32() : 0;
			if (root.TryGetProperty("total_bytes", out var bytes))
				downloadBytes = bytes.GetInt64();
			if (root.TryGetProperty("selection", out var selection))
			{
				var label = selection.GetProperty("label").GetString();
				var model = selection.GetProperty("model").GetString();
				var images = selection.GetProperty("vision").GetBoolean() ? "Map images enabled." : "Uses game state; map images disabled.";
				selectionSummary = $"{label}\n{images}";
				selectedModelDetail = $"Model: {model}";
			}
			var modelState = localSetupState switch
			{
				"running" => "Model ready",
				"not_installed" => "Install required",
				"installing" => "Downloading",
				"starting" => "Loading",
				"error" => "Retry required",
				_ => "Unavailable"
			};
			var assistantState = provider == "local" ? modelState : "External provider";
			var voiceState = localSetupState == "running" ? "Whisper installed" : modelState;
			var speechState = localSetupState == "running" ? "Loads on demand" : modelState;
			readinessSummary = $"Assistant: {assistantState}  |  Voice input: {voiceState}  |  Spoken replies: {speechState}\n" +
				"Whisper Base English (~147 MB) is installed with the Local AI Pack. " +
				"Microphone signal is checked when you speak.";
			if (localSetupState is "installing" or "starting")
				SetStatus(LocalSetupStatus());
			SettingsUtils.AdjustSettingsScrollPanelLayout(scrollPanel);
		}

		string LocalSetupStatus()
		{
			var message = localSetupState == "installing"
				? $"Downloading and verifying Local AI Pack… {localSetupProgress}%"
				: localSetupDetail;
			return WidgetUtils.WrapText(message, localSetupStatusLabel.Bounds.Width,
				Game.Renderer.Fonts[localSetupStatusLabel.Font]);
		}

		string LocalSetupButtonText()
		{
			return localSetupState switch
			{
				"installing" => $"INSTALLING… {localSetupProgress}%",
				"starting" => "LOADING MODELS…",
				"running" => "LOCAL AI READY",
				"error" => "RETRY LOCAL AI",
				_ when localSetupInstalled => "START LOCAL AI",
				_ => AISettingsDisplay.DownloadButton(downloadBytes)
			};
		}

		string Binding(string name)
		{
			var key = modData.Hotkeys[name].GetValue();
			return key.IsValid() ? key.DisplayString() : "Unbound";
		}

		void ApplyState(JsonElement root, string message)
		{
			var config = root.GetProperty("config");
			companionEnabled = config.GetProperty("companion_enabled").GetBoolean();
			voiceEnabled = config.GetProperty("voice_enabled").GetBoolean();
			pace = config.GetProperty("notification_pace").GetString() ?? "calm";
			voicePriority = config.GetProperty("voice_priority").GetString() ?? "critical";
			nativeStrategy = config.TryGetProperty("native_strategy", out var configuredStrategy)
				? configuredStrategy.GetString() ?? "adaptive"
				: "adaptive";
			modelSelection = config.TryGetProperty("model_selection", out var configuredSelection)
				? configuredSelection.GetString() ?? "auto" : "auto";
			textModel = config.GetProperty("text_model").GetString() ?? "local-coder";
			visionModel = config.GetProperty("vision_model").GetString() ?? textModel;
			transcribeModel = config.GetProperty("transcribe_model").GetString() ?? "openai-transcribe";
			speechModel = config.GetProperty("speech_model").GetString() ?? "openai-tts";
			speechVoice = config.GetProperty("speech_voice").GetString() ?? "alloy";
			provider = config.TryGetProperty("model_provider", out var configuredProvider)
				? configuredProvider.GetString() ?? InferProvider(textModel)
				: InferProvider(textModel);
			var configuredUrl = config.GetProperty("router_url").GetString() ?? DefaultAILayerUrl;
			if (provider == "custom")
				customEndpoint.Text = configuredUrl;
			else
				aiLayerUrl = configuredUrl;
			customTextModel.Text = textModel;
			customVisionModel.Text = visionModel;
			ApplyUsage(root.GetProperty("usage"));
			if (root.TryGetProperty("local_ai", out var setup))
				ApplyLocalSetup(setup);
			SettingsUtils.AdjustSettingsScrollPanelLayout(scrollPanel);
			SetIdle(message);
		}

		string InferProvider(string model)
		{
			return models.FirstOrDefault(option => option.Id == model)?.Provider ?? "custom";
		}

		void ApplyUsage(JsonElement usage)
		{
			var total = usage.GetProperty("session_cost_usd").GetDouble();
			var hourly = usage.GetProperty("hourly_cost_usd").GetDouble();
			costTotal = $"Session estimate: ${total:0.000000}  |  Current pace: ${hourly:0.0000}/hour";
			costBreakdown = $"Text ${usage.GetProperty("text_cost_usd").GetDouble():0.000000}  |  " +
				$"Speech ${usage.GetProperty("speech_cost_usd").GetDouble():0.000000}  |  " +
				$"Transcription ${usage.GetProperty("transcription_cost_usd").GetDouble():0.000000}";
			var assumptions = string.Join("  |  ", usage.GetProperty("assumptions").EnumerateArray().Select(value => value.GetString()));
			costAssumptions = WidgetUtils.WrapText(assumptions, costAssumptionsLabel.Bounds.Width,
				Game.Renderer.Fonts[costAssumptionsLabel.Font]);
		}

		void SetBusy(string message)
		{
			busy = true;
			SetStatus(message);
		}

		void SetIdle(string message)
		{
			busy = false;
			SetStatus(message);
		}

		void SetStatus(string message)
		{
			status = statusLabel == null ? message : WidgetUtils.TruncateText(message, statusLabel.Bounds.Width,
				Game.Renderer.Fonts[statusLabel.Font]);
		}

		void YieldTextFocus()
		{
			customEndpoint?.YieldKeyboardFocus();
			customTextModel?.YieldKeyboardFocus();
			customVisionModel?.YieldKeyboardFocus();
		}
	}
}
