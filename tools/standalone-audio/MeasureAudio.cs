#region Copyright & License Information
/*
 * Copyright (c) The RTS AI authors. GPL-3.0, like the rest of this mod.
 */
#endregion

// Reference measurement for the standalone audio set (tools/standalone-audio.py measure).
//
// An OpenRA utility command, compiled and run in the same disposable sandbox as tools/standalone-audit.py. For each
// sound name it asks the engine's file system for the file, decodes it with the mod's own sound loaders in memory and
// prints a handful of coarse numbers: length, sample rate, peak, RMS, attack and decay times, zero-crossing rate and
// the share of energy below 250 Hz and above 2.5 kHz. Nothing else leaves the process: no samples are written, so the
// replacement sounds can match the role, length and loudness of what the rules expect without copying any audio.
// The same command measures the project-made files (absolute paths), so both sides use one definition.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace OpenRA.Mods.RTSAIAudit
{
	public sealed class MeasureAudioCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--audio-measure";

		bool IUtilityCommand.ValidateArguments(string[] args) { return args.Length >= 3; }

		[Desc("NAMES.txt", "OUTPUT.json", "Coarse length/loudness/brightness numbers for each sound name (no samples written).")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			var modData = Game.ModData = utility.ModData;
			var fs = modData.ModFiles;
			var names = File.ReadAllLines(args[1]).Select(l => l.Trim()).Where(l => l.Length > 0).ToList();
			var result = new Dictionary<string, object>();
			foreach (var name in names)
			{
				try
				{
					Stream s;
					string by;
					if (Path.IsPathRooted(name))
					{
						s = File.OpenRead(name);
						by = "file";
					}
					else if (fs.TryOpen(name, out s))
						by = fs.TryGetPackageContaining(name, out var pkg, out _) ? Path.GetFileName(pkg.Name) : "?";
					else
					{
						result[name] = new Dictionary<string, object> { ["error"] = "missing" };
						continue;
					}

					using (s)
					{
						ISoundFormat fmt = null;
						foreach (var loader in modData.SoundLoaders)
						{
							s.Position = 0;
							if (loader.TryParseSound(s, out fmt))
								break;
						}

						if (fmt == null)
						{
							result[name] = new Dictionary<string, object> { ["error"] = "undecodable" };
							continue;
						}

						var m = Measure(fmt);
						m["package"] = by;
						result[name] = m;
						fmt.Dispose();
					}
				}
				catch (Exception e)
				{
					result[name] = new Dictionary<string, object> { ["error"] = e.GetType().Name + ": " + e.Message };
				}
			}

			File.WriteAllText(args[2], JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));
			Console.WriteLine($"measured {result.Count} sounds -> {args[2]}");
		}

		static Dictionary<string, object> Measure(ISoundFormat fmt)
		{
			var rate = fmt.SampleRate;
			var ch = fmt.Channels;
			var bits = fmt.SampleBits;
			var mono = new List<float>();
			using (var pcm = fmt.GetPCMInputStream())
			{
				var bytesPer = bits / 8;
				var frame = new byte[bytesPer * ch];
				while (true)
				{
					var n = pcm.Read(frame, 0, frame.Length);
					if (n < frame.Length)
						break;
					float sum = 0;
					for (var c = 0; c < ch; c++)
						sum += bytesPer == 2 ? BitConverter.ToInt16(frame, c * 2) / 32768f : (frame[c] - 128) / 128f;
					mono.Add(sum / ch);
				}
			}

			var len = mono.Count;
			var d = new Dictionary<string, object>
			{
				["rate"] = rate, ["channels"] = ch, ["bits"] = bits,
				["seconds"] = Math.Round(len / (double)rate, 3),
			};
			if (len == 0)
				return d;

			double peak = 0, sq = 0;
			var peakAt = 0;
			for (var i = 0; i < len; i++)
			{
				var a = Math.Abs(mono[i]);
				sq += mono[i] * mono[i];
				if (a > peak) { peak = a; peakAt = i; }
			}

			// 10 ms RMS envelope
			var win = Math.Max(1, rate / 100);
			var env = new List<double>();
			for (var i = 0; i < len; i += win)
			{
				double e = 0;
				var n = Math.Min(win, len - i);
				for (var j = 0; j < n; j++)
					e += mono[i + j] * mono[i + j];
				env.Add(Math.Sqrt(e / n));
			}

			var envMax = env.Max();

			// loudest 50 ms (five consecutive 10 ms windows): the short-term level that sets how punchy a sound is
			double max50 = 0;
			for (var i = 0; i < env.Count; i++)
			{
				double e = 0;
				var n = Math.Min(5, env.Count - i);
				for (var j = 0; j < n; j++)
					e += env[i + j] * env[i + j];
				max50 = Math.Max(max50, Math.Sqrt(e / 5));
			}

			var envPeak = env.IndexOf(envMax);
			var decayEnd = envPeak;
			for (var i = envPeak; i < env.Count; i++)
				if (env[i] >= envMax * 0.1)
					decayEnd = i;  // last window within -20 dB of the loudest window
			var start = env.FindIndex(e => e >= envMax * 0.1);

			// RMS over the windows within -40 dB of the loudest window (ignores leading/trailing silence)
			var active = env.Where(e => e >= envMax * 0.01).ToList();
			var activeRms = Math.Sqrt(active.Sum(e => e * e) / Math.Max(1, active.Count));

			// zero crossings and a crude 3-band split with one-pole filters
			var zc = 0;
			double lp = 0, hpPrev = 0, hpOut = 0, low = 0, high = 0;
			var aLow = Math.Exp(-2 * Math.PI * 250.0 / rate);
			var aHigh = Math.Exp(-2 * Math.PI * 2500.0 / rate);
			for (var i = 0; i < len; i++)
			{
				if (i > 0 && (mono[i] >= 0) != (mono[i - 1] >= 0))
					zc++;
				lp = (1 - aLow) * mono[i] + aLow * lp;
				low += lp * lp;
				hpOut = aHigh * (hpOut + mono[i] - hpPrev);
				hpPrev = mono[i];
				high += hpOut * hpOut;
			}

			double Db(double x) => x > 0 ? Math.Round(20 * Math.Log10(x), 1) : -120;
			d["peak_dbfs"] = Db(peak);
			d["rms_dbfs"] = Db(Math.Sqrt(sq / len));
			d["active_rms_dbfs"] = Db(activeRms);
			d["max50_rms_dbfs"] = Db(max50);
			d["onset_ms"] = Math.Max(0, start) * 10;
			d["attack_ms"] = Math.Max(0, envPeak - Math.Max(0, start)) * 10;
			d["decay20_ms"] = (decayEnd - envPeak) * 10;
			d["peak_at_ms"] = (int)(peakAt * 1000.0 / rate);
			d["zcr_hz"] = Math.Round(zc * rate / (2.0 * len));
			d["low_share"] = sq > 0 ? Math.Round(low / sq, 3) : 0;
			d["high_share"] = sq > 0 ? Math.Round(high / sq, 3) : 0;
			return d;
		}
	}
}
