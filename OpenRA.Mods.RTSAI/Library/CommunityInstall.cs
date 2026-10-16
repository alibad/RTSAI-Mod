using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace OpenRA.Mods.RTSAI.Library
{
	public sealed record CommunityRelease(string Id, string Name, string Version, string Description,
		string Url, long Bytes, string Sha256, string Executable, string Art, string Source);
	public sealed record CommunityReceipt(string Id, string Version, string Sha256, string Executable, DateTime InstalledUtc);
	public sealed record DownloadState(string Id, string Status, double Progress, bool Busy, int Process, DateTime UpdatedUtc);

	public sealed class CommunityInstall
	{
		public static readonly CommunityRelease[] Releases =
		[
			new("combined-arms", "Combined Arms", "1.09", "A separate combined-arms RTS with its own factions, campaigns and settings.",
				"https://github.com/Inq8/CAmod/releases/download/1.09/CombinedArms-1.09-x64-winportable.zip",
				233902710, "229ebb20e1dbb518ab9d2085ee4e09f5bbd44c5e7fb9688fd9feecb50b1110c2", "CombinedArms.exe", "classic", "https://github.com/Inq8/CAmod/releases/tag/1.09"),
			new("openhv", "OpenHV", "20250725", "An original pixel-art science-fiction RTS. Includes its own engine and game content.",
				"https://github.com/OpenHV/OpenHV/releases/download/20250725/OpenHV-20250725-x64-winportable.zip",
				151927007, "857275bb6343213a4638735920cba9b9b2fe708f756bc0667f07d6fc598259f1", "OpenHV.exe", "rts", "https://github.com/OpenHV/OpenHV/releases/tag/20250725")
		];
		public string Status { get; private set; } = "Choose a community game.";
		public double Progress { get; private set; }
		public bool Busy { get; private set; }
		public string ActiveId { get; private set; }
		CancellationTokenSource cancellation;
		DateTime published;
		static string JobFile => Path.Combine(NativeGameLibrary.Root, "Downloads", "community-job.json");
		static string CancelFile => Path.Combine(NativeGameLibrary.Root, "Downloads", "cancel-community-job");
		public void RequestInstall(CommunityRelease release, string archive = null)
		{
			Poll();
			if (Busy) return;
			Directory.CreateDirectory(Path.GetDirectoryName(JobFile));
			if (File.Exists(CancelFile)) File.Delete(CancelFile);
			var start = new ProcessStartInfo(Path.Combine(Platform.EngineDir, "bin", "OpenRA.Utility.exe"))
			{
				UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = Platform.EngineDir
			};
			start.ArgumentList.Add(NativeGameLibrary.Hub); start.ArgumentList.Add("--community-install"); start.ArgumentList.Add(release.Id);
			if (archive != null) start.ArgumentList.Add(Path.GetFullPath(archive));
			start.Environment["ENGINE_DIR"] = Platform.EngineDir;
			start.Environment["MOD_SEARCH_PATHS"] = Path.Combine(Platform.EngineDir, "mods");
			start.Environment["RTSAI_LIBRARY_SUPPORT"] = NativeGameLibrary.Root;
			Process.Start(start);
			Busy = true; ActiveId = release.Id; Status = "Starting download…"; Progress = 0;
		}
		public void Poll()
		{
			try
			{
				if (!File.Exists(JobFile)) return;
				var job = JsonSerializer.Deserialize<DownloadState>(File.ReadAllText(JobFile));
				if (job == null) return;
				ActiveId = job.Id; Status = job.Status; Progress = job.Progress; Busy = job.Busy;
				if (Busy && (DateTime.UtcNow - job.UpdatedUtc).TotalSeconds > 30)
				{
					try { if (Process.GetProcessById(job.Process).HasExited) Busy = false; }
					catch (ArgumentException) { Busy = false; }
					if (!Busy) Status = "Download interrupted. Resume from Community.";
				}
			}
			catch (IOException) { }
			catch (JsonException) { }
		}
		void Publish(bool force = false)
		{
			if (!force && (DateTime.UtcNow - published).TotalMilliseconds < 250) return;
			published = DateTime.UtcNow;
			var temporary = JobFile + ".tmp";
			File.WriteAllText(temporary, JsonSerializer.Serialize(new DownloadState(ActiveId, Status, Progress, Busy, Environment.ProcessId, published)));
			File.Move(temporary, JobFile, true);
			if (File.Exists(CancelFile)) cancellation?.Cancel();
		}
		static string DirectoryFor(CommunityRelease release) => Path.Combine(NativeGameLibrary.Root, "CommunityGames", release.Id, release.Version);
		static string ReceiptFor(CommunityRelease release) => Path.Combine(DirectoryFor(release), "rtsai-install.json");
		public static string InstalledExecutable(CommunityRelease release)
		{
			try
			{
				if (!File.Exists(ReceiptFor(release))) return null;
				var receipt = JsonSerializer.Deserialize<CommunityReceipt>(File.ReadAllText(ReceiptFor(release)));
				if (receipt?.Sha256 != release.Sha256 || receipt.Version != release.Version) return null;
				var executable = SafeEntryPath(DirectoryFor(release), receipt.Executable);
				return File.Exists(executable) ? executable : null;
			}
			catch (Exception) { return null; }
		}
		public static string SafeEntryPath(string root, string entry)
		{
			if (string.IsNullOrWhiteSpace(entry) || Path.IsPathRooted(entry) || entry.Contains(':'))
				throw new InvalidDataException("The archive contains an invalid file path.");
			var canonicalRoot = Path.GetFullPath(root) + Path.DirectorySeparatorChar;
			var target = Path.GetFullPath(Path.Combine(root, entry.Replace('/', Path.DirectorySeparatorChar).Replace('\\', Path.DirectorySeparatorChar)));
			if (!target.StartsWith(canonicalRoot, StringComparison.OrdinalIgnoreCase))
				throw new InvalidDataException("The archive contains a file outside its installation folder.");
			return target;
		}
		public void Cancel()
		{
			cancellation?.Cancel();
			Directory.CreateDirectory(Path.GetDirectoryName(CancelFile));
			File.WriteAllText(CancelFile, "pause");
		}
		public async Task InstallAsync(CommunityRelease release, string importedArchive = null)
		{
			if (Busy) return;
			Busy = true; ActiveId = release.Id; Progress = 0;
			cancellation = new CancellationTokenSource();
			var token = cancellation.Token;
			var cache = Path.Combine(NativeGameLibrary.Root, "Downloads");
			Directory.CreateDirectory(cache);
			using var installLock = new FileStream(Path.Combine(cache, "community-install.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
			if (File.Exists(CancelFile)) File.Delete(CancelFile);
			var archive = importedArchive ?? Path.Combine(cache, release.Id + "-" + release.Version + ".zip");
			var staging = DirectoryFor(release) + ".staging-" + Guid.NewGuid().ToString("N");
			try
			{
				Status = "Checking local installation requirements…"; Publish(true);
				if (!Environment.Is64BitOperatingSystem)
					throw new InvalidOperationException("This package requires 64-bit Windows.");
				if (new DriveInfo(Path.GetPathRoot(NativeGameLibrary.Root)).AvailableFreeSpace < release.Bytes * 4)
					throw new IOException("Not enough free storage. Free at least " + release.Bytes * 4 / 1048576 + " MB and retry.");
				if (importedArchive == null && !File.Exists(archive))
					await Download(release, archive, token);
				Status = "Verifying the official download…";
				await using (var stream = File.OpenRead(archive))
				{
					if (stream.Length != release.Bytes || Convert.ToHexString(await SHA256.HashDataAsync(stream, token)).ToLowerInvariant() != release.Sha256)
						throw new InvalidDataException("The download does not match the official release. Import a fresh official archive to retry.");
				}
				Status = "Installing the game and its compatible engine…";
				Publish(true);
				Directory.CreateDirectory(staging);
				await Task.Run(() =>
				{
					using var zip = ZipFile.OpenRead(archive);
					if (zip.Entries.Count > 100000 || zip.Entries.Sum(e => e.Length) > 8L * 1024 * 1024 * 1024)
						throw new InvalidDataException("This archive exceeds the supported installation size.");
					var completed = 0;
					foreach (var entry in zip.Entries)
					{
						token.ThrowIfCancellationRequested();
						var destination = SafeEntryPath(staging, entry.FullName);
						if (string.IsNullOrEmpty(entry.Name)) Directory.CreateDirectory(destination);
						else
						{
							Directory.CreateDirectory(Path.GetDirectoryName(destination));
							entry.ExtractToFile(destination, false);
						}
						Progress = ++completed / (double)zip.Entries.Count;
						Publish();
					}
				}, token);
				var executable = Directory.EnumerateFiles(staging, release.Executable, SearchOption.AllDirectories).SingleOrDefault()
					?? throw new InvalidDataException("The official game executable is missing.");
				var relative = Path.GetRelativePath(staging, executable);
				File.WriteAllText(Path.Combine(staging, "rtsai-install.json"), JsonSerializer.Serialize(new CommunityReceipt(
					release.Id, release.Version, release.Sha256, relative, DateTime.UtcNow), new JsonSerializerOptions { WriteIndented = true }));
				if (Directory.Exists(DirectoryFor(release)))
					Directory.Move(DirectoryFor(release), DirectoryFor(release) + ".previous-" + DateTime.UtcNow.ToString("yyyyMMddHHmmss"));
				Directory.Move(staging, DirectoryFor(release));
				Progress = 1; Status = release.Name + " is ready. Open it from your Library.";
			}
			catch (OperationCanceledException) { Status = "Download paused. Resume when you’re ready."; }
			catch (Exception e) { Status = e.Message; }
			finally { Busy = false; Publish(true); cancellation.Dispose(); cancellation = null; }
		}
		async Task Download(CommunityRelease release, string archive, CancellationToken token)
		{
			var partial = archive + ".part";
			var offset = File.Exists(partial) ? new FileInfo(partial).Length : 0;
			using var client = new HttpClient { Timeout = TimeSpan.FromMinutes(30) };
			client.DefaultRequestHeaders.UserAgent.ParseAdd("RTSAI-Native-Library/1.0");
			using var request = new HttpRequestMessage(HttpMethod.Get, release.Url);
			if (offset > 0) request.Headers.Range = new System.Net.Http.Headers.RangeHeaderValue(offset, null);
			using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, token);
			response.EnsureSuccessStatusCode();
			if (response.StatusCode != HttpStatusCode.PartialContent) offset = 0;
			else if (response.Content.Headers.ContentRange?.From != offset)
				throw new IOException("The server returned an invalid download range. Retry the download.");
			await using var input = await response.Content.ReadAsStreamAsync(token);
			await using (var output = new FileStream(partial, offset == 0 ? FileMode.Create : FileMode.Append, FileAccess.Write))
			{
				var buffer = new byte[128 * 1024];
				int read;
				while ((read = await input.ReadAsync(buffer, token)) != 0)
				{
					await output.WriteAsync(buffer.AsMemory(0, read), token);
					offset += read; Progress = Math.Min(1, offset / (double)release.Bytes);
					Status = $"Downloading {release.Name} · {offset / 1048576d:0.0} / {release.Bytes / 1048576d:0.0} MB";
					Publish();
				}
			}
			File.Move(partial, archive, true);
		}
		public static void Launch(CommunityRelease release)
		{
			var executable = InstalledExecutable(release) ?? throw new IOException("Install this game first.");
			var info = new ProcessStartInfo(executable) { UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = Path.GetDirectoryName(executable) };
			info.ArgumentList.Add("Engine.SupportDir=" + Path.Combine(NativeGameLibrary.Root, "CommunitySupport", release.Id));
			info.ArgumentList.Add("Game.FetchNews=false");
			Process.Start(info);
		}
	}
}
