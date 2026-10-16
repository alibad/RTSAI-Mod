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
using System.IO;
using System.IO.Compression;
using System.Linq;
using OpenRA.Widgets;
using OpenRA.Mods.Common.Widgets;

namespace OpenRA.Mods.RTSAI.Widgets.Logic
{
	/// <summary>Browses folders and ZIP archives without exposing a raw path-entry prompt.</summary>
	public sealed class RTSAIPackageBrowserLogic : ChromeLogic
	{
		sealed record BrowserEntry(string Path, string Name, bool IsDirectory, bool IsPack, string Detail);

		static string lastDirectory;

		readonly Action<string> onSelected;
		readonly Action onCancel;
		readonly ScrollPanelWidget sourceList;
		readonly ScrollItemWidget sourceTemplate;
		readonly LabelWidget currentLocation;
		readonly LabelWidget selection;
		readonly LabelWidget status;
		readonly ButtonWidget upButton;
		readonly ButtonWidget openButton;
		readonly ButtonWidget installButton;

		string currentDirectory;
		BrowserEntry selectedEntry;
		bool showingComputer;
		bool currentDirectoryIsPack;

		[ObjectCreator.UseCtor]
		public RTSAIPackageBrowserLogic(Widget widget, string initialDirectory, Action<string> onSelected, Action onCancel)
		{
			this.onSelected = onSelected;
			this.onCancel = onCancel;
			sourceList = widget.Get<ScrollPanelWidget>("PACK_SOURCES");
			sourceTemplate = sourceList.Get<ScrollItemWidget>("PACK_SOURCE_TEMPLATE");
			currentLocation = widget.Get<LabelWidget>("CURRENT_LOCATION");
			selection = widget.Get<LabelWidget>("SELECTION");
			status = widget.Get<LabelWidget>("STATUS");
			upButton = widget.Get<ButtonWidget>("UP_BUTTON");
			openButton = widget.Get<ButtonWidget>("OPEN_BUTTON");
			installButton = widget.Get<ButtonWidget>("INSTALL_BUTTON");

			var downloads = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
			var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
			var documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
			SetupLocationButton(widget, "DOWNLOADS_BUTTON", downloads);
			SetupLocationButton(widget, "DESKTOP_BUTTON", desktop);
			SetupLocationButton(widget, "DOCUMENTS_BUTTON", documents);
			widget.Get<ButtonWidget>("COMPUTER_BUTTON").OnClick = ShowComputer;

			upButton.OnClick = GoUp;
			widget.Get<ButtonWidget>("REFRESH_BUTTON").OnClick = PopulateSources;
			openButton.OnClick = OpenSelectedDirectory;
			installButton.OnClick = InstallSelectedPack;
			widget.Get<ButtonWidget>("CANCEL_BUTTON").OnClick = Cancel;

			var start = FirstExistingDirectory(initialDirectory, lastDirectory, downloads, documents, desktop,
				Environment.GetFolderPath(Environment.SpecialFolder.UserProfile));
			if (start == null)
				ShowComputer();
			else
				ShowDirectory(start);

			if (Environment.GetEnvironmentVariable("OPENRA_AI_CAPTURE_CAPABILITY_BROWSER") == "1")
				Game.RunAfterDelay(750, Game.TakeScreenshot);
		}

		void SetupLocationButton(Widget widget, string id, string path)
		{
			var button = widget.Get<ButtonWidget>(id);
			button.IsDisabled = () => string.IsNullOrWhiteSpace(path) || !Directory.Exists(path);
			button.OnClick = () => ShowDirectory(path);
		}

		void ShowDirectory(string path)
		{
			try
			{
				path = Path.GetFullPath(path);
				if (!Directory.Exists(path))
					return;

				currentDirectory = path;
				lastDirectory = path;
				showingComputer = false;
				selectedEntry = null;
				PopulateSources();
			}
			catch (Exception e)
			{
				status.GetText = () => $"Could not open this location: {e.Message}";
			}
		}

		void ShowComputer()
		{
			showingComputer = true;
			currentDirectory = null;
			selectedEntry = null;
			PopulateSources();
		}

		void PopulateSources()
		{
			sourceList.RemoveChildren();
			currentDirectoryIsPack = !showingComputer && IsPackFolder(currentDirectory);
			BrowserEntry[] entries;
			string readError = null;
			try
			{
				entries = (showingComputer ? DriveEntries() : DirectoryEntries(currentDirectory)).ToArray();
			}
			catch (Exception e)
			{
				entries = [];
				readError = $"Could not read this location: {e.Message}";
			}

			foreach (var entry in entries)
			{
				var item = ScrollItemWidget.Setup(sourceTemplate,
					() => selectedEntry == entry,
					() => SelectEntry(entry),
					() => OpenEntry(entry));
				item.Get<LabelWidget>("NAME").GetText = () => entry.Name;
				item.Get<LabelWidget>("TYPE").GetText = () => entry.Detail;
				sourceList.AddChild(item);
			}

			currentLocation.GetText = () => showingComputer ? "This PC" : currentDirectory;
			RefreshActions();
			if (readError != null)
				status.GetText = () => readError;
		}

		static IEnumerable<BrowserEntry> DriveEntries()
		{
			foreach (var drive in DriveInfo.GetDrives().Where(drive => drive.IsReady).OrderBy(drive => drive.Name))
			{
				var name = string.IsNullOrWhiteSpace(drive.VolumeLabel) ? drive.Name : $"{drive.Name}  {drive.VolumeLabel}";
				yield return new BrowserEntry(drive.RootDirectory.FullName, name, true, false, "DRIVE");
			}
		}

		static IEnumerable<BrowserEntry> DirectoryEntries(string directory)
		{
			var folders = Directory.GetDirectories(directory)
				.OrderBy(Path.GetFileName, StringComparer.OrdinalIgnoreCase)
				.Select(path =>
				{
					var isPack = IsPackFolder(path);
					return new BrowserEntry(path, Path.GetFileName(path), true, isPack, isPack ? "PACK FOLDER" : "FOLDER");
				});
			var archives = Directory.GetFiles(directory, "*.zip")
				.OrderBy(Path.GetFileName, StringComparer.OrdinalIgnoreCase)
				.Select(path =>
				{
					var isPack = IsPackArchive(path);
					return new BrowserEntry(path, Path.GetFileName(path), false, isPack,
						isPack ? $"ZIP PACK  |  {FormatBytes(new FileInfo(path).Length)}" : "ZIP (NO PACK MANIFEST)");
				});
			return folders.Concat(archives);
		}

		void SelectEntry(BrowserEntry entry)
		{
			selectedEntry = entry;
			RefreshActions();
		}

		void OpenEntry(BrowserEntry entry)
		{
			if (entry.IsDirectory)
				ShowDirectory(entry.Path);
			else
			{
				SelectEntry(entry);
				if (entry.IsPack)
					InstallSelectedPack();
			}
		}

		void OpenSelectedDirectory()
		{
			if (selectedEntry?.IsDirectory == true)
				ShowDirectory(selectedEntry.Path);
		}

		void GoUp()
		{
			if (showingComputer)
				return;

			var parent = Directory.GetParent(currentDirectory);
			if (parent == null)
				ShowComputer();
			else
				ShowDirectory(parent.FullName);
		}

		void RefreshActions()
		{
			upButton.IsDisabled = () => showingComputer;
			openButton.IsDisabled = () => selectedEntry?.IsDirectory != true;
			var installSource = InstallSource();
			installButton.IsDisabled = () => installSource == null;

			if (selectedEntry != null)
				selection.GetText = () => selectedEntry.Name;
			else if (currentDirectoryIsPack)
				selection.GetText = () => Path.GetFileName(currentDirectory);
			else
				selection.GetText = () => "No pack selected";

			if (selectedEntry?.IsPack == true)
				status.GetText = () => "Ready to check this package. The target game and package compatibility are validated before installation.";
			else if (selectedEntry is { IsDirectory: false })
				status.GetText = () => "This ZIP does not contain a capability-pack manifest.";
			else if (selectedEntry?.IsDirectory == true)
				status.GetText = () => selectedEntry.IsPack ? "Pack folder found. Install it or open it to inspect its files." :
					"Open this folder to continue browsing.";
			else if (currentDirectoryIsPack)
				status.GetText = () => "This folder is a capability pack and is ready to install.";
			else
				status.GetText = () => "Choose a downloaded portable game ZIP, or a compatible add-on ZIP or folder.";
		}

		string InstallSource()
		{
			if (selectedEntry?.IsPack == true)
				return selectedEntry.Path;
			return currentDirectoryIsPack ? currentDirectory : null;
		}

		void InstallSelectedPack()
		{
			var source = InstallSource();
			if (source == null)
				return;

			Ui.CloseWindow();
			onSelected(source);
		}

		void Cancel()
		{
			Ui.CloseWindow();
			onCancel?.Invoke();
		}

		static bool IsPackFolder(string path)
		{
			return !string.IsNullOrWhiteSpace(path) && File.Exists(Path.Combine(path, "pack.yaml"));
		}

		static bool IsPackArchive(string path) => Path.GetExtension(path).Equals(".zip", StringComparison.OrdinalIgnoreCase);

		static string FirstExistingDirectory(params string[] paths)
		{
			return paths.FirstOrDefault(path => !string.IsNullOrWhiteSpace(path) && Directory.Exists(path));
		}

		static string FormatBytes(long bytes)
		{
			if (bytes >= 1024 * 1024)
				return $"{bytes / (1024d * 1024d):0.0} MB";
			if (bytes >= 1024)
				return $"{bytes / 1024d:0.0} KB";
			return $"{bytes} B";
		}
	}
}
