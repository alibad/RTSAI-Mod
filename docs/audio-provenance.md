# Audio provenance

Status, 2026-10-06: everything below ships on `main`. It arrived with the promotion of the owner-approved art preview,
which also brought Israel's Hebrew and Hezbollah's Lebanese Arabic voices, announcers and call signs. `make.cmd test`
on `main` decodes every clip through `CheckFactionAudio`, with no warnings [ran]. Art has its own record:
[art-provenance.md](art-provenance.md).

Every voice line and announcer clip that the modern factions ship is made locally by an engine whose
code, weights and voice allow the generated audio to be redistributed in a GPL game, commercial use
included. Per-line records are in
[`mods/rtsai/modern-factions/audio/PROVENANCE.json`](../mods/rtsai/modern-factions/audio/PROVENANCE.json):
engine, model and pinned revision, license, speaker, language, text, seed, the speech-recognition
check and the generation date.

The earlier lines came from `edge-tts`, an unofficial client for Microsoft Edge's Read Aloud
service. Nothing grants redistribution of that output, so all of it has been replaced.

The standalone build replaces every Red Alert 2 sound it still needed (weapon and impact effects, UI
sounds, the shared units' voices and the music) with project-made audio. Those files and their
records are in [`mods/rtsai/standalone/audio/`](../mods/rtsai/standalone/audio/PROVENANCE.json); see
[Standalone build](#standalone-build-no-red-alert-2-audio). No EA audio is shipped.

## Engines

| Language | Engine (pinned revision) | License | Evidence |
|---|---|---|---|
| English (unit lines and announcers) | Kokoro-82M v1.0, `hexgrad/Kokoro-82M@f3ff357`, `kokoro` 0.9.4 | Apache-2.0 (code, weights and voicepacks) | [Model card](https://huggingface.co/hexgrad/Kokoro-82M): `license: apache-2.0`; trained on permissive or non-copyrighted audio (see open points) |
| Arabic (Modern Standard and Lebanese), Hebrew, Turkish, Mandarin | Chatterbox Multilingual V2, `ResembleAI/chatterbox@5bb1f6e` (`t3_mtl23ls_v2`), `chatterbox-tts` 0.1.7 | MIT | [Model card](https://huggingface.co/ResembleAI/chatterbox): `license: mit`; lists ar, he, tr, zh |
| Persian | MOSS-TTS-Nano with the Persian fine-tune `nimaaaAI/MOSS-TTS-Nano-Persian@dcfd7f2`, on `OpenMOSS-Team/MOSS-TTS-Nano@44502f8` and `MOSS-Audio-Tokenizer-Nano@6aa02b0` | Apache-2.0 | Fine-tune [LICENSE](https://huggingface.co/nimaaaAI/MOSS-TTS-Nano-Persian/blob/main/LICENSE) (Apache-2.0, trained only on Mozilla Common Voice Persian, CC0); base and codec cards `license: apache-2.0`; [GitHub](https://github.com/OpenMOSS/MOSS-TTS-Nano) LICENSE Apache-2.0 |

Chatterbox embeds Resemble's inaudible Perth watermark in its output. It is left in place.

## Voices

No real person's voice is cloned. Each speaker is a Kokoro voicepack, or the average of two:

- English lines are spoken by the voicepack directly.
- For the other languages, the voicepack first speaks a fixed English reference sentence. Each
  faction's crew therefore keeps one synthetic timbre in both of its languages.
- Arabic, Hebrew, Turkish and Mandarin are a two-step clone with Chatterbox:
  1. From the English clip at `cfg_weight` 0 (the model card's setting against carrying an accent
     across), it speaks the same sentence in the target language.
  2. Each line is cloned from that native clip at the default `cfg_weight` 0.5. Reference and
     target then share a language, as the model card recommends.
- Hezbollah's native clip is a Lebanese Arabic sentence (`NATIVE_REFERENCE_TEXT["ar-LB"]`), so its
  lines are cloned from Lebanese rather than Modern Standard Arabic speech.
- Hebrew is read with vowel points (niqqud), written by hand in `generate-levant-voices.py`.
  Chatterbox's Hebrew front end expects pointed text; it would add the points with the optional
  `dicta_onnx` diacritizer, which is not installed. The unpointed script is what the sheet shows and
  what speech recognition is checked against.
- Persian is cloned by MOSS-TTS-Nano directly from the English clip. That is how the Persian
  fine-tune is documented to be used.

| Faction | Infantry and heroes | Vehicle, air and naval crews | Announcer (EVA) |
|---|---|---|---|
| China | `am_puck` | `am_fenrir` + `am_puck` | `af_bella`, crisp networked command voice |
| Iran | `am_michael` | `am_michael` + `bm_george` | `af_sarah`, narrow-band command radio |
| Türkiye | `am_fenrir` | `bm_lewis` | `af_heart`, clean broadcast voice |
| Saudi Arabia | `bm_george` | `bm_fable` | `af_kore`, operations room with a short room tail |
| Yemen | `am_fenrir` + `bm_fable` | `bm_lewis` + `am_michael` | `af_aoede`, lo-fi field radio |
| Israel | `am_puck` + `bm_lewis` | `am_michael` + `am_adam` | `bf_emma` + `af_heart`, clipped digital command net |
| Hezbollah | `am_fenrir` + `am_michael` | `bm_george` + `am_puck` | `bf_isabella`, VHF field radio with a short slap |

Arabic is Modern Standard Arabic for Saudi Arabia and Yemen. Hezbollah's lines are written in
Lebanese Arabic (هلق، عم، شو، منتحرك) and cloned from a Lebanese reference; Chatterbox has no
dialect setting, so how Lebanese they sound is for the native reviewer. The Persian fine-tune was
trained on read speech, so the Persian lines are flatter than the others.

Israel and Hezbollah (since 5 October) have the same inventory as Iran: six voice sets of select,
move, attack and action lines, each in the faction's language and in English (24 + 24 lines), plus
their own announcer. `levant-voices.yaml` defines the sets (`R2Israel*Voice`, `R2Hezbollah*Voice`):
infantry, forward observer or field spotter, the recon specialist or scout, vehicles (also used by
their defenses, as before), aircraft or drone, and naval. `israel-audio.yaml` and
`hezbollah-audio.yaml` assign them to the units, and `eva-notifications.yaml` points both factions
at their announcer folders instead of the stock `ceva` and `csof`. Every line is a neutral unit
acknowledgement or report, like the other factions': no slogans, no religious or political phrases,
no real people or operations.

Hezbollah's FPV Team (Salvo and swarm, 7 October) adds a seventh set, `R2HezbollahfpvVoice`: four Lebanese Arabic
lines and their English counterparts (`hz-fpv-*`), same generator, speaker (`hezbollah-infantry`) and field-radio
chain. They were rendered on the CPU because the GPU was claimed by another session, so the Lebanese reference
was bootstrapped again (seed 5, CER 0.07); the machine review rows are in `docs/voice-review.csv` and the native
check is pending, like the other Lebanese lines. The FPV drones themselves are not voiced (not selectable).

### Engine check (5 October 2026)

Before the Hebrew and Lebanese lines were made, every licensed engine that might speak the language
read the faction's own 24 scripts, two seeds each, from the same synthetic speaker. Each raw take
was transcribed by Whisper large-v3 forced to the language, and language-identified automatically.
The columns are the mean character error rate of each line's best take, the lines with a clean take
(error rate 0.05 or less), and the mean probability Whisper gives the target language over all
takes.

| Language | Candidate | CER | Clean lines | Language ID | Result |
|---|---|---|---|---|---|
| Hebrew | Chatterbox, unpointed text | 0.21 | 4/24 | 0.51 | rejected |
| Hebrew | Chatterbox, pointed text | 0.05 | 18/24 | 0.69 | **used** |
| Hebrew | MOSS-TTS-Nano base (Hebrew is not one of its 20 languages) | 0.46 | 0/24 | 0.02 | rejected |
| Hebrew, Arabic | Kokoro-82M | — | — | — | no Hebrew or Arabic front end |
| Lebanese Arabic | Chatterbox, Lebanese reference | 0.03 | 18/24 | 0.90 | **used** |
| Lebanese Arabic | MOSS-TTS-Nano base | 0.19 | 4/24 | 0.46 | rejected |
| Persian | MOSS fine-tune from the English clip (shipped), seeds 1–2 / 3–4 | 0.09 / 0.17 | 12 / 7 | 0.65 / 0.57 | **kept** |
| Persian | MOSS fine-tune from a synthetic Persian clip | 0.13 | 9/24 | 0.54 | rejected |
| Persian | MOSS-TTS-Nano base | 0.19 | 4/24 | 0.05 | rejected |
| Persian | MOSS fine-tune, `bm_george` reference | 0.14 | 12/24 | 0.44 | rejected |
| Persian | MOSS fine-tune, `am_fenrir` reference, seeds 1–2 / 3–4 | 0.03 / 0.16 | 17 / 9 | 0.76 / 0.71 | not clearly better |
| Persian | MOSS fine-tune, `am_fenrir` blends (`+am_michael`, `+bm_lewis`), seeds 1–2 / 3–4 | 0.07 / 0.13 | 11 / 11 | 0.69 / 0.69 | not clearly better |

Persian was tested for the accent the first review found. A reference built on `am_fenrir` raised
Persian language ID by about 0.07–0.14 on both seed sets, but the transcripts were not consistently
better: its CER advantage on seeds 1–2 did not repeat on seeds 3–4, and over four seeds the blends'
mean take error was 0.16 against 0.18. So the Persian set was not switched. Chatterbox has no
Persian, and the other Persian engines are rejected on license grounds (see below). Seed 4 fails
for MOSS on most lines, so the seeds 3–4 rows have fewer takes. The probe script and its raw
results are not shipped; the outcomes are also recorded under `rejected` in `PROVENANCE.json`.

## Quality check

The cloned engines sample, so each line is generated with up to 6 seeds (8 for Persian), stopping
after two clean takes. Every take is transcribed with Whisper large-v3 (`faster-whisper` 1.2.1).
Audio more than 0.25 s past the last recognized word is cut, because the cloned engines sometimes
add a breath or babble there. The take with the lowest character error rate against the script is
kept, and the shortest one breaks a tie. Kokoro is deterministic and gets one take, which is checked
the same way. Each record stores the transcript and its error rate.

The original processing chains are reapplied unchanged after synthesis: each generator's band-pass,
compression and loudness filters, then its radio beep, noise floor and fades. The old edge-tts
speaking-rate offsets become tempo factors (for example −6% becomes 0.94).

### Results

| Set | Files | Engines | Exact transcript | Highest error rate |
|---|---|---|---|---|
| Unit voice lines, 2 October | 148 | 74 Kokoro, 50 Chatterbox, 24 MOSS | 139 | 0.15 |
| Unit voice lines, 6 October | 244 | 122 Kokoro, 98 Chatterbox, 24 MOSS | 231 | 0.14 |
| Announcer clips, 2 October | 555 (111 × 5) | Kokoro | 537 | 0.13 |
| Announcer clips, 6 October | 777 (111 × 7) | Kokoro | 743 | 0.20 |

The remaining mismatches are mostly recognizer homophones such as "ore miner" heard as "or minor",
or "route" as "root", and Whisper writing Lebanese contractions in their long form (عالشاشة as
على الشاشة). The real slips found by the review were regenerated (see
[Native-speaker review](#native-speaker-review)). The Israel announcer is `bf_emma` blended with
`af_heart`: `bf_emma` alone added a syllable to four clips ("Unit lost" heard as "Unit Laster"),
and the blend reads all 111 cleanly.

Compared with the edge-tts files:
- Same format: 44.1 kHz mono 16-bit PCM.
- Speech is 0.90× as long (median).
- Files are about half as long because edge-tts padded each line with about 1.1 s of silence.
- Loudness changed by −0.2 LUFS (median; 10th–90th percentile −2.1 to +1.5).
- The Persian lines rose from −24.2 to −18.7 LUFS. They had been about 4 dB quieter than the
  English lines of the same units.

## Native-speaker review

**Status: native-speaker sign-off has not happened. It is an owner gate before release.** What
exists is a machine-assisted first pass (5 October 2026, extended on 6 October to the new Hebrew and
Lebanese lines and the changed call signs), written up line by line in
[`voice-review.csv`](voice-review.csv) so a native speaker can confirm or correct each line quickly.

The sheet has one row per non-English line: the script, its English line, a literal meaning of the
script, a fresh Whisper transcript of the shipped file and its error rate, Whisper's language ID,
Whisper's own English translation (a hint only; it is often wrong on clips this short), the verdict,
the action and notes. The `native_speaker` column is empty, waiting for the reviewer.

How the first pass was done:
1. Every shipped non-English file was transcribed again with the pinned Whisper large-v3: forced to
   the line's language with the generator's settings, then with automatic language ID, then
   translated to English (`tools/voice-review.py transcribe`).
2. Each transcript was compared with the script and with the transcript taken at generation time.
   Spelling-only differences (for example ث/س or ع/ء in Persian, traditional Chinese characters) and
   exact homophones are not slips.
3. Each script was read against its English line for wrong words, unnatural phrasing, the wrong
   script or dialect, and a tone that fits a military RTS. The reviewer is not a native speaker of
   any of these languages, so wording points are suggestions for the native pass, not changes.
4. A line was regenerated when both transcriptions heard a different content word, and when a
   changed call sign was not heard as written.

| Language | Faction | Lines checked | Regenerated | Flagged for a native check | No issue found |
|---|---|---|---|---|---|
| Persian (fa-IR) | Iran | 24 | 4 | 7 (plus 2 of the regenerated) | 13 |
| Arabic (ar-SA, MSA) | Saudi Arabia | 14 | 2 (call sign) | 2 (plus 1) | 10 |
| Arabic (ar-YE, MSA) | Yemen | 14 | 0 | 4 | 10 |
| Turkish (tr-TR) | Türkiye | 12 | 0 | 1 | 11 |
| Mandarin (zh-CN) | China | 10 | 1 (call sign) | 0 (plus 1) | 9 |
| Hebrew (he-IL) | Israel | 24 (new) | 0 | 5 | 19 |
| Lebanese Arabic (ar-LB) | Hezbollah | 24 (new) | 2 | 4 (plus 1) | 18 |
| **Total** | | **122** | **9** | **23 (plus 5)** | **90** |

### Regenerated lines

| File | Script | Shipped take heard as | New take heard as (generation; shipped file) |
|---|---|---|---|
| `iran-naval-attack-fa.wav` | ردیابی تثبیت شد. | ردیابی تسبیح شد ("rosary") | تسبیت; تسکیت |
| `shadow-action-fa.wav` | نقطه ورود مشخص شد. | نقطه برود ("should go") | exact; exact |
| `iran-drone-select-fa.wav` | پیوند داده برقرار است. | پیاند (no v) | exact; exact |
| `iran-naval-select-fa.wav` | خدمه دریایی آماده است. | خدم ("servants") | exact; exact |
| `hz-veh-select-ar.wav` | الطاقم جاهز. | الطاقة مجاهز ("the energy") | exact; exact |
| `hz-spotter-move-ar.wav` | رايح عالتلة. | رايحة (feminine) | exact; رايحة |
| `rsa-falcon-build-ar.wav` | الصقر في الميدان. | السقر (no emphatic ص) | exact; exact |
| `rsa-falcon-select-ar.wav` | الصقر واحد جاهز. | السقر | exact; exact |

The Persian lines were regenerated on 5 October and the Arabic ones on 6 October. The text,
speaker, English reference clip, MOSS-TTS-Nano Persian fine-tune and Iran processing
chain are unchanged (`tools/voice-review.py regenerate`, with `RTSAI_MOSS_PYTHON` set to a
transformers 4.57 interpreter). The one change is the seed range: 1–24 instead of 1–8, because the
documented range had already produced the shipped take. MOSS sampling on the GPU is not
bit-reproducible between runs (`shadow-action-fa` passes at seed 1 now and did not on 2 October),
so a seed identifies a take only within its run. Each record in `PROVENANCE.json` has a `review`
entry with the replaced seed and transcript. تسبیت sounds the same as تثبیت, because ث and س are both
/s/ in Persian. The Iran chain normalizes peak, not loudness: three new takes are within 0.5 LU of
the old ones, and `iran-drone-select-fa` went from −20.4 to −17.2 LUFS, still inside the range of
the Persian set.

### For the native speaker, in order

1. **Persian accent.** Whisper's language ID often does not recognize the MOSS clips as Persian. Six
   clips of two or more words score below 0.5 for `fa` (for example `iran-inf-action-fa` scores
   en 0.65), while the Arabic, Turkish and Mandarin clips score 0.9–1.0. This may be an accent
   carried over from the English reference clip.
2. **`iran-naval-attack-fa`**: listen for "tasbit". The wording is a calque of "Track is steady";
   ردیابی پایدار است or هدف قفل شد may sound more natural.
3. **Heard differently by one of the two transcriptions:** `iran-drone-move-fa` (به‌روز),
   `rsa-inf-action-ar`, `rsa-veh-select-ar`, and the Yemeni Ghost lines `rye-ghost-action-ar`,
   `rye-ghost-build-ar` and `rye-ghost-select-ar` (is the ḥ of الشبح audible?).
4. **Wording suggestions:** `iran-drone-action-fa` (تصویر واضح است for "picture is clear"),
   `shadow-attack-fa` (جدا شد reads as "separated"), the Saudi call sign فالكون in
   `rsa-falcon-build-ar` and `rsa-falcon-select-ar` (the English "Falcon One", or الصقر),
   `rye-naval-select-ar`, and `tr-greywolf-attack-tr` ("İşaretimle" for "on my mark").
5. **Call signs (changed 6 October).** Saudi فالكون is now الصقر; in `rsa-falcon-select-ar`,
   الصقر واحد puts the article on a numbered call sign, and صقر واحد جاهز may sound more natural.
   China's 红矛 is now 赤矛, which avoids the slur homophone 红毛. Whisper still hears 赤毛 ("red hair
   or fur"), an exact homophone that is not a slur; confirm by ear. The English names stay
   "Falcon One" and "Red Spear"; no Fluent string contained the Arabic or Chinese call sign.
6. **Hebrew (new).** Language ID is weak on `il-observer-select-he`, `il-recon-move-he` and
   `il-inf-attack-he`. One transcription heard a different word in `il-inf-attack-he` (בוטחים),
   `il-recon-select-he` (הסייעה) and `il-veh-move-he` (נעין). The vowel points fed to the engine are
   in `generate-levant-voices.py`.
7. **Lebanese Arabic (new).** Does it sound Lebanese? Whisper wrote نحن for نحنا in
   `hz-inf-select-ar`. Listen to `hz-spotter-move-ar` (رايح or رايحة?) and `hz-scout-move-ar`; and
   `hz-naval-action-ar` may be heard as من غير ("without") rather than منغيّر.
8. **Dialect:** Yemen speaks Modern Standard Arabic, not Yemeni Arabic.

A wording change belongs in the OpenRA-AI generator scripts, which hold the scripts; regenerate the
line afterwards with the generator or `tools/voice-review.py regenerate`, then re-run
`tools/voice-review.py transcribe`, which refreshes the machine columns and keeps the human ones.

## Announcers

`mods/rtsai/modern-factions/eva-notifications.yaml` adds a Speech prefix for each modern faction,
so the engine plays `audio/eva/<faction>/<clip>.wav` for that faction's player. Every Speech clip in
`audio/notifications.yaml` has a line for all seven factions (Israel and Hezbollah since 5 October). The wording is original, not a
transcript of the Red Alert 2 announcer. Announcers are English so alerts stay clear for every
player. Files are IMA ADPCM WAV at 22.05 kHz mono, the format RA2's own announcer uses.

`voice-prefixes.yaml` maps the modern factions onto the stock engineer voice of their side. Without
it, a modern engineer looks up unprefixed file names that do not exist.

## Checks

- The `CheckFactionAudio` lint pass (`OpenRA.Mods.RTSAI/Lint`, run by `make test`) opens and fully
  decodes every sound the mod ships with an explicit `ra2|` path. That covers every voice clip and
  every announcer clip for every faction. It also fails when a faction-keyed voice or notification
  set has no entry for a playable faction.
- `generate-rtsai-mod-audio.py` refuses to run if the rules reference a shipped file that is neither
  a generated voice line nor a listed sound effect. It runs speech recognition on the 23 sound
  effects to confirm that none contains speech.
- `tools/naval-sfx.py` regenerates the four naval sounds in memory and exits non-zero if a shipped
  file differs by a single byte.
- `tools/standalone-audio.py check` fails if any audio file under `mods/` has no structured
  provenance record (an entry with a matching SHA-256 in the nearest `PROVENANCE.json` of the
  `{"files": ...}` form, as in `standalone/audio/` and `audio/sfx/`, or a `filename` record in
  `modern-factions/audio/PROVENANCE.json`), if a record's file is gone, or if the per-file tables at
  the end of this page are stale.
- `tools/standalone-sfx.py verify` rebuilds every procedural standalone sound in memory and fails if a
  shipped file differs; `tools/standalone-music.py check` checks each track's loop seam, loudness and
  record.

## Reproduce

From an OpenRA-AI checkout, with the Python environment described in `scripts/voice_engines.py`
and ffmpeg on `PATH`:

```
python scripts/generate-rtsai-mod-audio.py --mod ../RTSAI-Mod                        # everything
python scripts/generate-rtsai-mod-audio.py --mod ../RTSAI-Mod --only tr-air-select-tr.wav --skip-eva
python scripts/generate-rtsai-mod-audio.py --mod ../RTSAI-Mod --eva-only --eva-clips 048,062
```

Partial runs merge their records into `PROVENANCE.json`. Set `RTSAI_MOSS_PYTHON` to the Persian
worker's interpreter. The Israel and Hezbollah lines come from `scripts/generate-levant-voices.py`,
which the driver loads like the other faction generators; their announcers are in
`generate-faction-eva.py`. Hebrew needs no diacritizer: the points are in the script.

From this repository, in the same Python environment:

```
python tools/voice-review.py transcribe --openra-ai ../OpenRA-AI       # refresh docs/voice-review.csv
python tools/voice-review.py regenerate --openra-ai ../OpenRA-AI --mod <scratch copy> --seeds 24 shadow-action-fa.wav
python tools/naval-sfx.py                                               # check the naval sounds (stdlib only)
```

The 5 October review ran in a Python 3.12 environment with torch 2.11 (CUDA 12.8), `kokoro` 0.9.4,
`chatterbox-tts` 0.1.7, transformers 5.2.0 and `faster-whisper` 1.2.1. The Persian worker used
transformers 4.57.6.

## Rejected options

| Candidate | Reason |
|---|---|
| edge-tts | Unofficial client of a Microsoft service; no redistribution grant |
| Piper `fa_IR` amir, ganji, ganji_adabi, reza_ibrahim | Fine-tuned from the en_US lessac voice, whose [Blizzard 2013 license](https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html) is research-only |
| Piper `fa_IR` gyro | No dataset license stated |
| `Thomcles/Chatterbox-TTS-Persian-Farsi` | CC BY-NC 4.0 |
| `mazrba/Chatterbox-TTS-Persian-gguf` | Labelled MIT, but a quantization of the CC BY-NC model above |
| `Kamtera/persian-tts-*-vits` | Dataset has no stated license |
| `facebook/mms-tts-*` | CC BY-NC 4.0 |
| Coqui XTTS-v2 | Coqui Public Model License (non-commercial) |
| Kokoro Mandarin voicepacks | License-compatible, but graded D on the model card |
| Kokoro for Hebrew or Arabic | No Hebrew or Arabic front end |
| MOSS-TTS-Nano base for Hebrew, Lebanese Arabic or Persian | Worse in the [engine check](#engine-check-5-october-2026); no Hebrew |
| Chatterbox Hebrew without vowel points | CER 0.21 against 0.05 with points |

## Open points for the owner

- **Training data.** Each license above covers the weights and their output. The Kokoro model card
  says its data also includes synthetic audio from closed commercial TTS models. Chatterbox and the
  MOSS base model do not disclose their training data. None of this changes the grant to users of
  the weights, but it is the residual risk in this choice.
- **Persian fine-tune.** It is published by an individual (`nimaaaAI`), not by OpenMOSS. Its weights
  are loaded with `torch.load(weights_only=True)` and its code is not run; the model code comes from
  the pinned OpenMOSS revision.
- **Native-speaker sign-off.** Still open, and a release gate: a native speaker of Persian, Hebrew,
  Arabic (ideally Saudi, Yemeni and Lebanese), Turkish and Mandarin should fill the `native_speaker`
  column of [`voice-review.csv`](voice-review.csv). The first pass found likely accent problems in
  the Persian lines, and weaker Hebrew language ID on some lines, that only a listener can judge.
- **Hebrew vowel points** were written by hand for the TTS input only; a Hebrew reader should glance
  at them in `generate-levant-voices.py` (`POINTED`) if a line sounds wrong.
- **OpenRA-AI wording.** `generate-rtsai-mod-audio.py` in OpenRA-AI still describes the naval sounds
  by the fork path only. A full regeneration would overwrite the source text in `PROVENANCE.json`
  until its `SFX` entry is updated to name `generate_naval_assets.py`.

## Sound effects

The 23 weapon, naval and network sounds are procedural. None was regenerated, and speech recognition
finds no speech in any of them. Nineteen come from procedural generators in OpenRA-AI
(`generate-china-sfx.py`, `generate-red-sea-sfx.py`).

### Death explosions and the other sounds RA2 itself lacks (7 October 2026)

Four sound names in the rules are not in Red Alert 2's own files (they come from Yuri's Revenge or
are engine defaults), so those sounds never played: `expnew13.wav` and `expnew09.wav` (every
vehicle, ship, aircraft and building death: `UnitExplodeSmall`, `UnitExplode`, the R2FX deaths,
`Demolish`), `vapoar2b.wav` (one of three AA-missile reports) and `chrono2.aud` (the
`Chronoshiftable` default). Five original sounds replace them, referenced by explicit
`ra2|audio/sfx/` paths: `rtsai-explode-small.wav`, `rtsai-explode-medium.wav`,
`rtsai-explode-large.wav`, `rtsai-aa-launch.wav` and `rtsai-shift.wav`. They are procedural
(sines, seeded noise, filters and synthetic reverb; no recordings or samples), made by
`tools/standalone-sfx.py` on branch `rtsai/standalone-audio`, which rebuilds them byte for byte.
Per-file records (role, seed, licence, measured length and level, SHA-256) are in
[`mods/rtsai/audio/sfx/PROVENANCE.json`](../mods/rtsai/audio/sfx/PROVENANCE.json). Licence: the
project's own code (GPL-3.0); the output carries no third-party rights.

### Naval sounds

The four `naval-*` files are procedural too. Their generator had been overlooked: it was added in the
same fork commit as the files.

- **Origin.** The `alibad/OpenRA` commit `1d76c546f1` ("Add Saudi and Yemen naval systems",
  12 August 2026, Ali Badereddin) added `mods/ra/bits/naval/*.wav` together with the script that
  wrote them, `packaging/naval/generate_naval_assets.py`. The copy in the OpenRA-AI checkout is
  `engine/openra/packaging/naval/`.
- **How they are made.** Its `synth()` computes each sound from sine waves and white noise. The
  noise comes from Python's `random.Random`, seeded with the sound's name. Output is 22.05 kHz mono
  16-bit, peak-normalized to 0.70. No recording, sample library or EA/RA2 audio is involved.
- **License.** The code is the project's own, under the fork's GPL-3.0. Its output carries no
  third-party rights.
- **Proof.** Re-running that commit's script reproduces all four files byte for byte.
  `tools/naval-sfx.py` carries the four formulas and checks the shipped files from this repository
  (identical under Python 3.11 and 3.12).

The files, their names and their loudness are unchanged, so no rules changed.

| Shipped file | Fork name | Length | SHA-256 |
|---|---|---|---|
| `naval-ciws-burst.wav` | `ciws-burst` | 0.34 s | `a1765138adeb92ab05e45981309ace6675e8ecab244f2ccbcaf3c6444dcfccf2` |
| `naval-missile-launch.wav` | `missile-launch` | 0.72 s | `9d926359fc598027274bc99ebeeeb7d97f927e0c245379d318aa4f6e4e67936a` |
| `naval-naval-alarm.wav` | `naval-alarm` | 1.05 s | `4e93158c02fc87c9e99545e9028950f7f81cb165354e309109c1d235d27d9f68` |
| `naval-radar-sweep.wav` | `radar-sweep` | 0.82 s | `275b2381ce7ab5aadba5adf9476bd2f1eb0d2b95fd377009cc6043e9c9ab217b` |

## Standalone build (no Red Alert 2 audio)

Added 7 October 2026 on `rtsai/standalone-audio`. The file list is the standalone agent's
`docs/standalone-deliverables.json` ("audio"): the sounds the rules still name for what the seven
modern factions can reach, after the original factions, Chrono Commando and Yuri Prime left the
modern scope. Every file keeps the name the rules use; nothing in the rules changes.

| Category | Files | How it is made | Licence |
|---|---|---|---|
| Weapon, impact, explosion and superweapon effects | 81 (77, plus 4 names missing even in RA2: `chrono2.aud`, `expnew09.wav`, `expnew13.wav`, `vapoar2b.wav`) | procedural, `tools/standalone-sfx.py` | project code, GPL-3.0 |
| UI sounds | 14 | procedural, same tool | project code, GPL-3.0 |
| Dog (select, move, feedback, death) | 6 voices (its 2 attack sounds are among the effects) | procedural barks (jittery voiced source with period doubling, an opening-mouth formant sweep, chest resonance, a plosive onset), growls and whines | project code, GPL-3.0 |
| Shared-unit voices and death cries | 104 (85 spoken lines, 19 cries) | Kokoro-82M (lines) and Chatterbox (cries) through OpenRA-AI `voice_engines.py`, `tools/standalone-voices.py` | Apache-2.0 (Kokoro), MIT (Chatterbox) |
| Music | 12 looping tracks + `score` (victory/defeat) | ACE-Step 1.5, local, `tools/standalone-music.py` | MIT |

### How the effects are made

`tools/standalone_dsp.py` is a small numpy kit: sine and additive oscillators, seeded noise
(PCG64, seeded from `sha256('rtsai-standalone-sfx-1/<file>')`), state-variable filters,
envelopes, a soft clipper, a compressor, a look-ahead limiter and synthetic impulse-response
reverb. `tools/standalone-sfx.py` builds each file from a recipe. An explosion is a crack, a noise
blast with a falling cutoff and follow-up blasts, a pitch-dropping sub, a long rumble, crackle and
debris; a rifle shot is a crack, a band-passed blast, a low thump and a mechanical click, plus slap
echoes. No recording, sample library or EA audio is involved. `verify` rebuilds every file in
memory and compares it with the shipped bytes.

**Matching the expected role, length and loudness.** `tools/standalone-audio.py measure` runs
`tools/standalone-audio/MeasureAudio.cs`, an engine utility command, against the player's own RA2
content in a disposable sandbox (as `standalone-audit.py` does). It decodes each sound the rules
name in memory and prints coarse numbers only: length, sample rate, peak, RMS, the loudest 50 ms,
attack and decay times, zero-crossing rate and low/high energy shares. Those numbers are in
[`tools/standalone-audio/reference-metrics.json`](../tools/standalone-audio/reference-metrics.json);
no samples were written or kept. Each new file has the reference's length, and its loudest 50 ms
is brought to the reference's level under a -0.3 dBFS look-ahead limiter, so a new explosion sits
in the mix where the old one did. The four names missing even in RA2 got lengths and levels from
their siblings. The sounds are 22.05 kHz mono 16-bit WAV; `chrono2.aud` is a Westwood AUD (IMA
ADPCM), which the engine decodes with its own reader.

### Sounds the rules name that RA2 itself lacks (main and standalone)

Four names in the rules resolve in neither build, because Red Alert 2's own files do not contain
them (they are Yuri's Revenge or engine defaults): `expnew13.wav` (`UnitExplodeSmall`,
`BuildingExplode` and the small R2FX deaths), `expnew09.wav` (`UnitExplode`, the medium R2FX deaths,
`Kirov`/`Plane`/`ApocExplode`, `Demolish`), `vapoar2b.wav` (one of three AA-missile reports) and
`chrono2.aud` (the `Chronoshiftable` trait's default `ChronoshiftSound`). So every vehicle death was
silent. Five project sounds with their own names fill these roles in both builds, in
`mods/rtsai/audio/sfx/` with their own `PROVENANCE.json`, referenced by explicit path
(`ra2|audio/sfx/<file>`): `rtsai-explode-small.wav`, `rtsai-explode-medium.wav`,
`rtsai-explode-large.wav` (a fireball, a hull clang, debris and, for the larger two, ammunition
cooking off), `rtsai-shift.wav` and `rtsai-aa-launch.wav`. RTSAI-Mod main wires them since
5df5950 (which also fixes the `^InfantryDeath` `DisablePrefixes` indentation and drops the engineer
variants RA2 has only for the Allied prefix); make test passes with 0 warnings, the engine audit
with RA2 content finds 0 missing sounds for the modern factions, and in a scripted game 24
destroyed vehicles produced no missing-sound or decode error. The standalone set also ships the
four old names, so the standalone build resolves them until its rules are rewired the same way.

### Shared-unit voices

The engineer, spy, MCVs and ore trucks, the Soviet-side AA track and the two naval transports are
shared by several factions, so their lines are English, like the English half of the faction sets.
They are spoken by Kokoro-82M at the pinned revision with the faction sets' settings: the same
engine code (`voice_engines.Synthesizer.render`), Whisper large-v3 QA, a radio chain like the
faction chains (band-pass, compression, `loudnorm` to -18 LUFS, squelch tone, noise floor, fades)
and 44.1 kHz mono 16-bit output. The speakers are new blends of the voicepacks the factions already
use (for example `am_adam`+`am_puck` for the Allied-side engineer and `bm_george`+`am_michael` for
the Soviet-side one); no real person is imitated. The wording is original: short acknowledgements
in the faction sets' register, not RA2's lines. The 19 death cries use the faction sets' second
engine, Chatterbox (MIT), cloned from the speaker's Kokoro English reference at exaggeration 1.3
and cfg_weight 0.3 (Chatterbox's own tip for expressive speech), because Kokoro reads interjections
as words ("I egg", "oh yeah"). Of twelve seeds per cry, the take that Whisper hears as a bare
interjection and that is closest to the expected length is kept.
Melted, Zapped and PsyCrush add a procedural acid, electric or crush layer. Chatterbox output
carries Resemble's inaudible Perth watermark, as the faction sets' cloned lines do. Every line has a row in
[`voice-review.csv`](voice-review.csv) (file `standalone/voices/...`); `tools/voice-review.py
transcribe` keeps those rows.

### Music

ACE-Step 1.5 ran locally (BeTenshi music service: XL turbo DiT, 5Hz LM planner 1.7B, int8 weights
as served). Code and weights are MIT, and the model card says generated music can be used
commercially; it describes its training data as licensed, royalty-free or public-domain, and
synthetic music. Each track's request (caption, bpm, key, length, seed, instrumental) and the
service's reply are in its record. The captions name styles and instruments only (industrial,
electronic and rock, and per theatre erhu and guzheng, santur and tombak, baglama and zurna, oud,
darbuka, mizmar, qanun), never an artist, song or anthem.

Mastering (`tools/standalone-music.py master`): the take's composed ending is dropped and the body
is cut to a whole number of bars; the bars after the cut are crossfaded into the head (equal power),
so the file repeats without a seam. Of the 12 cuts whose onset envelopes match the head best, each
with a 2- and a 4-bar crossfade, the one whose wrap brings the smallest onset is kept (since
7 October; this moved the three tracks that sat near the check's limit, Yangtze Steel, Desert
Convoy and Plateau Engines, from the 98th-99th percentile to the 18th-78th).
Then one static gain to -14 LUFS integrated (EBU R128) and a stereo look-ahead limiter, run
circularly so the seam stays continuous; Ogg Vorbis q4, 44.1 kHz stereo, about 2.5 MB per track.
`check` ranks the spectral flux across the wrap against every frame of the track (the wrap must not
be a bigger onset than the music's own) and checks the sample step there. `music.yaml` lists the
tracks; `score` keeps its key because `MusicPlaylist` plays it on the victory and defeat screens,
and it is hidden from the playlist. The manifest's `SoundFormats` includes `Ogg`.

A generated track can still resemble existing music by chance; the records say the tracks are
AI-generated.

### Reproduce

```
python tools/standalone-audio.py measure --content ../OpenRA/Support/Content --names <list> --out <scratch>/ref.json
python tools/standalone-sfx.py build && python tools/standalone-sfx.py verify          # numpy only
<voice env python> tools/standalone-voices.py build --openra-ai ../OpenRA-AI --device cuda
python tools/standalone-music.py generate --cache <dir>     # music service on :8014; GPU claim/yield protocol
python tools/standalone-music.py master --cache <dir> && python tools/standalone-music.py check
python tools/standalone-audio.py doc && python tools/standalone-audio.py check
```

### Files

<!-- standalone-audio-files: generated by tools/standalone-audio.py doc; do not edit by hand -->

#### Music

Generator `tools/standalone-music.py`; ACE-Step 1.5, MIT. Request = caption below, instrumental, the bpm/key/length in the record, 8 turbo steps.

| File | Title | Seed | Prompt (caption) | Licence |
|---|---|---|---|---|
| `standalone/audio/music/rtsai-anatolian-armor.ogg` | Anatolian Armor | 7340 | energetic rock and electronic fusion instrumental, baglama saz riffs, davul and darbuka percussion, zurna reed lead, distorted guitars, powerful drums, heroic and driving | MIT (ACE-Step 1.5) |
| `standalone/audio/music/rtsai-black-ore.ogg` | Black Ore | 7390 | heavy industrial metal groove instrumental, down-tuned guitars, machine-like drums, anvil hits, grinding synths, menacing and powerful | MIT (ACE-Step 1.5) |
| `standalone/audio/music/rtsai-cedar-signal.ogg` | Cedar Signal | 7370 | dark electronic instrumental, oud and ney melody, darbuka groove, pulsing analog synth bass, radio static textures, tense and brooding, steady build | MIT (ACE-Step 1.5) |
| `standalone/audio/music/rtsai-coastline-watch.ogg` | Coastline Watch | 7380 | synthwave industrial instrumental, qanun arpeggios, driving electronic drums, gated synth pads, punchy bass, vigilant and determined | MIT (ACE-Step 1.5) |
| `standalone/audio/music/rtsai-desert-convoy.ogg` | Desert Convoy | 7350 | big beat electronic instrumental, oud riffs, darbuka and riq percussion, cinematic brass stabs, synth bass, marching energy, wide desert atmosphere | MIT (ACE-Step 1.5) |
| `standalone/audio/music/rtsai-final-push.ogg` | Final Push | 7410 | fast industrial techno instrumental, pounding four-on-the-floor kick, distorted acid bassline, metallic percussion, alarm-like synth leads, intense and triumphant | MIT (ACE-Step 1.5) |
| `standalone/audio/music/rtsai-grid-assault.ogg` | Grid Assault | 7310 | electronic industrial drum and bass instrumental, fast breakbeats, heavy reese bass, sharp synth stabs, glitchy arpeggios, tense and relentless, futuristic military | MIT (ACE-Step 1.5) |
| `standalone/audio/music/rtsai-iron-foundry.ogg` | Iron Foundry | 7300 | industrial rock instrumental, chugging distorted guitar riffs, pounding live drums, gritty synth bass, metallic percussion hits, driving and aggressive, real-time strategy battle music | MIT (ACE-Step 1.5) |
| `standalone/audio/music/rtsai-plateau-engines.ogg` | Plateau Engines | 7330 | dark electronic industrial instrumental, santur arpeggios, tombak and daf hand drums, kamancheh melody, deep pulsing bass, metallic hits, tense and driving | MIT (ACE-Step 1.5) |
| `standalone/audio/music/rtsai-pressure-front.ogg` | Pressure Front | 7400 | tense cinematic industrial electronic instrumental, ticking percussion, low drones, slowly building synth arpeggio, distant war drums, suspenseful | MIT (ACE-Step 1.5) |
| `standalone/audio/music/rtsai-yangtze-steel.ogg` | Yangtze Steel | 7320 | cinematic industrial electronic instrumental, erhu lead melody, guzheng ostinato, Chinese war drums, heavy synth bass, distorted guitar layer, epic and determined | MIT (ACE-Step 1.5) |
| `standalone/audio/music/score.ogg` | Debrief | 7420 | short cinematic electronic outro instrumental, steady military snare, warm synth pads, low brass, reflective and resolved | MIT (ACE-Step 1.5) |

#### Sound effects, UI sounds and the dog

Generator `tools/standalone-sfx.py` (procedural; no recordings or samples). Seed: the first 8 bytes of `sha256('rtsai-standalone-sfx-1/<file>')`. Licence: the project's own code (GPL-3.0); the output carries no third-party rights.

| File | Role | Seed | Licence |
|---|---|---|---|
| `audio/sfx/rtsai-aa-launch.wav` | anti-aircraft missile launch (third variant beside vapoat2a/vapoat2c) | sha256('rtsai-standalone-sfx-1/rtsai-aa-launch.wav') | GPL-3.0 code, no third-party rights |
| `audio/sfx/rtsai-explode-large.wav` | vehicle death, large: heavy vehicles, aircraft and demolition (R2FXDeathLarge, Kirov/Plane/Apoc, Demolish) | sha256('rtsai-standalone-sfx-1/rtsai-explode-large.wav') | GPL-3.0 code, no third-party rights |
| `audio/sfx/rtsai-explode-medium.wav` | vehicle death, medium (UnitExplode) | sha256('rtsai-standalone-sfx-1/rtsai-explode-medium.wav') | GPL-3.0 code, no third-party rights |
| `audio/sfx/rtsai-explode-small.wav` | vehicle death, small (UnitExplodeSmall and the R2FX small deaths) | sha256('rtsai-standalone-sfx-1/rtsai-explode-small.wav') | GPL-3.0 code, no third-party rights |
| `audio/sfx/rtsai-shift.wav` | unit returns from a space shift (Chronoshiftable ChronoshiftSound) | sha256('rtsai-standalone-sfx-1/rtsai-shift.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bflaatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bflaatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bflaattb.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bflaattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bflaattc.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bflaattc.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bflaattd.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bflaattd.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bgendiea.wav` | building destroyed: large explosion and collapse | sha256('rtsai-standalone-sfx-1/bgendiea.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bgendieb.wav` | building destroyed: large explosion and collapse | sha256('rtsai-standalone-sfx-1/bgendieb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bgendiec.wav` | building destroyed: large explosion and collapse | sha256('rtsai-standalone-sfx-1/bgendiec.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bgendied.wav` | building destroyed: large explosion and collapse | sha256('rtsai-standalone-sfx-1/bgendied.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bgendiee.wav` | building destroyed: large explosion and collapse | sha256('rtsai-standalone-sfx-1/bgendiee.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bgendief.wav` | building destroyed: large explosion and collapse | sha256('rtsai-standalone-sfx-1/bgendief.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bgraatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bgraatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bpatatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bpatatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bpilatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bpilatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bpilattb.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bpilattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bpilattc.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bpilattc.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bpilattd.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bpilattd.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bpowdiea.wav` | power plant destroyed: explosion, arcing and a dying transformer hum | sha256('rtsai-standalone-sfx-1/bpowdiea.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bpowdieb.wav` | power plant destroyed: explosion, arcing and a dying transformer hum | sha256('rtsai-standalone-sfx-1/bpowdieb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bpriat1a.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bpriat1a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bsenatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bsenatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bsenattb.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bsenattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bsenattc.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bsenattc.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/bsenattd.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/bsenattd.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/btesat1a.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/btesat1a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/btesat2a.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/btesat2a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/chrono2.aud` | shift device effect (Westwood AUD, the name the rules use) | sha256('rtsai-standalone-sfx-1/chrono2.aud') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/expnew09.wav` | large vehicle or missile explosion | sha256('rtsai-standalone-sfx-1/expnew09.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/expnew13.wav` | medium explosion with burning debris | sha256('rtsai-standalone-sfx-1/expnew13.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gdamag1a.wav` | building heavily damaged: smaller blast, metal stress and debris | sha256('rtsai-standalone-sfx-1/gdamag1a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gdamag1b.wav` | building heavily damaged: smaller blast, metal stress and debris | sha256('rtsai-standalone-sfx-1/gdamag1b.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gdamag1c.wav` | building heavily damaged: smaller blast, metal stress and debris | sha256('rtsai-standalone-sfx-1/gdamag1c.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gdamag1d.wav` | building heavily damaged: smaller blast, metal stress and debris | sha256('rtsai-standalone-sfx-1/gdamag1d.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gdamag1e.wav` | building heavily damaged: smaller blast, metal stress and debris | sha256('rtsai-standalone-sfx-1/gdamag1e.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gexp10a.wav` | air-defence hit: two quick airbursts high up | sha256('rtsai-standalone-sfx-1/gexp10a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gexp14a.wav` | general shell and rocket impact: medium explosion | sha256('rtsai-standalone-sfx-1/gexp14a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gexp15a.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/gexp15a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gexpapoa.wav` | heavy bomb impact: deep double blast | sha256('rtsai-standalone-sfx-1/gexpapoa.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gexpbara.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/gexpbara.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gexpbarb.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/gexpbarb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gexpbarc.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/gexpbarc.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gexpcraa.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/gexpcraa.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gexpifva.wav` | light bomb impact: deep medium explosion | sha256('rtsai-standalone-sfx-1/gexpifva.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gexpwala.wav` | large water impact: underwater blast and a tall splash | sha256('rtsai-standalone-sfx-1/gexpwala.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gexpwasa.wav` | small water impact: splash | sha256('rtsai-standalone-sfx-1/gexpwasa.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/gexpwasb.wav` | torpedo or depth hit: muffled thump and splash | sha256('rtsai-standalone-sfx-1/gexpwasb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/ichratta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/ichratta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/iconatta.wav` | rifle: three-round burst | sha256('rtsai-standalone-sfx-1/iconatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/iconattb.wav` | rifle: double tap | sha256('rtsai-standalone-sfx-1/iconattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/iconattc.wav` | rifle: five-round burst with echo | sha256('rtsai-standalone-sfx-1/iconattc.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/iconattd.wav` | rifle: single shot | sha256('rtsai-standalone-sfx-1/iconattd.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/iconatte.wav` | rifle: two quick shots | sha256('rtsai-standalone-sfx-1/iconatte.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/icraatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/icraatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/idesat1a.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/idesat1a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/idesat2a.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/idesat2a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/idogatca.wav` | dog attack: growl rising into a bark and a bite | sha256('rtsai-standalone-sfx-1/idogatca.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/idogatta.wav` | dog attack: two barks and a bite | sha256('rtsai-standalone-sfx-1/idogatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/igensqua.wav` | infantry run over: crunch and a wet squelch | sha256('rtsai-standalone-sfx-1/igensqua.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/igiat1a.wav` | machine gun: five-round burst | sha256('rtsai-standalone-sfx-1/igiat1a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/igiat1b.wav` | machine gun: six-round burst | sha256('rtsai-standalone-sfx-1/igiat1b.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/igiat1c.wav` | machine gun: three-round burst | sha256('rtsai-standalone-sfx-1/igiat1c.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/igiat2a.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/igiat2a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/igiat2b.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/igiat2b.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/igiat2c.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/igiat2c.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/igiat2d.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/igiat2d.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/irocatta.wav` | infantry-carrier cannon and launcher: heavy round with a short whoosh | sha256('rtsai-standalone-sfx-1/irocatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/iseaatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/iseaatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/iseaattb.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/iseaattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/isniatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/isniatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/itanatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/itanatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/itanattb.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/itanattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/itesat2a.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/itesat2a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/itesat2b.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/itesat2b.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/itesatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/itesatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/iteschaa.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/iteschaa.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/iyurat2a.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/iyurat2a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/schrmov.wav` | unit shifted through space: low whomp, chorus sweep and arrival pop | sha256('rtsai-standalone-sfx-1/schrmov.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/schropen.wav` | space-shift device powering up: deep hum swelling into a charged shimmer | sha256('rtsai-standalone-sfx-1/schropen.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/siroon.wav` | protective field switched on: electric surge and metallic shimmer | sha256('rtsai-standalone-sfx-1/siroon.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/siroread.wav` | protective field ready: low swelling drone | sha256('rtsai-standalone-sfx-1/siroread.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/snukexpl.wav` | strategic missile detonation: enormous blast and a long rolling roar | sha256('rtsai-standalone-sfx-1/snukexpl.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/snukintr.wav` | strategic missile incoming: rising roar and a falling shriek | sha256('rtsai-standalone-sfx-1/snukintr.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/snuklaun.wav` | strategic missile launch: ignition and a deep rocket roar | sha256('rtsai-standalone-sfx-1/snuklaun.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/snukread.wav` | missile silo ready: hydraulic doors and a two-tone warning | sha256('rtsai-standalone-sfx-1/snukread.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/sweaintr.wav` | storm brewing: rising wind and distant thunder | sha256('rtsai-standalone-sfx-1/sweaintr.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/sweastra.wav` | lightning strike: rolling thunder | sha256('rtsai-standalone-sfx-1/sweastra.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/sweastrb.wav` | lightning strike: sharp crack | sha256('rtsai-standalone-sfx-1/sweastrb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/sweastrc.wav` | lightning strike: crack and roll | sha256('rtsai-standalone-sfx-1/sweastrc.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/sweastrd.wav` | lightning strike: rolling thunder | sha256('rtsai-standalone-sfx-1/sweastrd.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/uplace.wav` | structure placed: heavy thud, metal ring and settling debris | sha256('rtsai-standalone-sfx-1/uplace.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/uselbuil.wav` | structure sold or packed up: servo whine, ratchet and a closing clank | sha256('rtsai-standalone-sfx-1/uselbuil.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vaegatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vaegatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vaegattb.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vaegattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vapoar2b.wav` | anti-aircraft missile launch (the second of three variants) | sha256('rtsai-standalone-sfx-1/vapoar2b.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vapoat1a.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vapoat1a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vapoat2a.wav` | anti-aircraft missile launch | sha256('rtsai-standalone-sfx-1/vapoat2a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vapoat2c.wav` | anti-aircraft missile launch | sha256('rtsai-standalone-sfx-1/vapoat2c.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vbleatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vbleatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vbleattb.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vbleattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vblhatta.wav` | helicopter rotary cannon: spin-up burst | sha256('rtsai-standalone-sfx-1/vblhatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vblhattb.wav` | helicopter rotary cannon: spin-up burst | sha256('rtsai-standalone-sfx-1/vblhattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vchrtele.wav` | ore carrier teleports home: short whomp and shimmer | sha256('rtsai-standalone-sfx-1/vchrtele.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vdemdiea.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vdemdiea.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vdesatta.wav` | heavy gun and howitzer: deep boom | sha256('rtsai-standalone-sfx-1/vdesatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vdesattb.wav` | heavy gun and howitzer: deep boom | sha256('rtsai-standalone-sfx-1/vdesattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vdolatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vdolatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vflaat1a.wav` | tracked autocannon: two heavy rounds | sha256('rtsai-standalone-sfx-1/vflaat1a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vflaat1b.wav` | tracked autocannon: two heavy rounds | sha256('rtsai-standalone-sfx-1/vflaat1b.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vflaat2a.wav` | twin anti-aircraft cannon: burst | sha256('rtsai-standalone-sfx-1/vflaat2a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vflaat2b.wav` | twin anti-aircraft cannon: burst | sha256('rtsai-standalone-sfx-1/vflaat2b.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vflaat2c.wav` | twin anti-aircraft cannon: burst | sha256('rtsai-standalone-sfx-1/vflaat2c.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vflaat2d.wav` | twin anti-aircraft cannon: burst | sha256('rtsai-standalone-sfx-1/vflaat2d.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vgramoa.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vgramoa.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vgramoc.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vgramoc.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vgriatta.wav` | main battle tank gun | sha256('rtsai-standalone-sfx-1/vgriatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vgriattb.wav` | main battle tank gun | sha256('rtsai-standalone-sfx-1/vgriattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vgriattc.wav` | main battle tank gun | sha256('rtsai-standalone-sfx-1/vgriattc.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vhorlana.wav` | drone landing | sha256('rtsai-standalone-sfx-1/vhorlana.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vhorlanb.wav` | drone landing | sha256('rtsai-standalone-sfx-1/vhorlanb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vhortaka.wav` | drone take-off | sha256('rtsai-standalone-sfx-1/vhortaka.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vhortakb.wav` | drone take-off | sha256('rtsai-standalone-sfx-1/vhortakb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vifvat2a.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vifvat2a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vifvat2b.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vifvat2b.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vifvat2c.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vifvat2c.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vifvatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vifvatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vifvrepa.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vifvrepa.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vintatta.wav` | missile launch: ignition and hiss | sha256('rtsai-standalone-sfx-1/vintatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vkiratta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vkiratta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vmiratta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vmiratta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vnavupa.wav` | submarine diving or surfacing: venting air, bubbles, hull groan | sha256('rtsai-standalone-sfx-1/vnavupa.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vospatta.wav` | bomb release: latch clunk and a low thud | sha256('rtsai-standalone-sfx-1/vospatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vpriatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vpriatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vrhiatta.wav` | light cannon: tight report | sha256('rtsai-standalone-sfx-1/vrhiatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vrhiattb.wav` | light cannon: tight report | sha256('rtsai-standalone-sfx-1/vrhiattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vrhiattc.wav` | light cannon: report with echo | sha256('rtsai-standalone-sfx-1/vrhiattc.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vrhiattd.wav` | light cannon: tight report | sha256('rtsai-standalone-sfx-1/vrhiattd.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vsquat1a.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vsquat1a.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vsubatta.wav` | torpedo launch: compressed-air thunk, bubbles and a fading motor | sha256('rtsai-standalone-sfx-1/vsubatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vtadatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vtadatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vtadattb.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vtadattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vtadattc.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vtadattc.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vteratta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vteratta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vtesatta.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vtesatta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vtesattb.wav` | restored-country weapon or impact | sha256('rtsai-standalone-sfx-1/vtesattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vwaratta.wav` | 20 mm cannon: burst | sha256('rtsai-standalone-sfx-1/vwaratta.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/sfx/vwarattb.wav` | 20 mm cannon: burst | sha256('rtsai-standalone-sfx-1/vwarattb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/gpowof.wav` | power lost: clunk and a generator winding down | sha256('rtsai-standalone-sfx-1/gpowof.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/gpowon.wav` | power restored: click, rising generator hum and electric buzz | sha256('rtsai-standalone-sfx-1/gpowon.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/gupgrad1.wav` | unit promoted: rising three-note chime | sha256('rtsai-standalone-sfx-1/gupgrad1.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/ubeacon.wav` | beacon placed: sonar-like ping with echoes | sha256('rtsai-standalone-sfx-1/ubeacon.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/ucreddn.wav` | credits counting down: tiny low tick | sha256('rtsai-standalone-sfx-1/ucreddn.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/ucredup.wav` | credits counting up: tiny bright tick | sha256('rtsai-standalone-sfx-1/ucredup.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/ugamclos.wav` | disabled click: dull knock | sha256('rtsai-standalone-sfx-1/ugamclos.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/umenucl1.wav` | menu click: crisp tick | sha256('rtsai-standalone-sfx-1/umenucl1.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/umessage.wav` | chat message: two-tone blip | sha256('rtsai-standalone-sfx-1/umessage.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/uradarof.wav` | radar offline: descending power-down and fading static | sha256('rtsai-standalone-sfx-1/uradarof.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/uradaron.wav` | radar online: power-up sweep, scanning tone and acknowledgement beeps | sha256('rtsai-standalone-sfx-1/uradaron.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/uslide1.wav` | build palette opens: mechanical slide and latch | sha256('rtsai-standalone-sfx-1/uslide1.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/uslide2.wav` | build palette closes: slide back and a thunk | sha256('rtsai-standalone-sfx-1/uslide2.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/ui/utab.wav` | tab click: bright tick | sha256('rtsai-standalone-sfx-1/utab.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/voices/idogdiea.wav` | dog dies: sharp yelp | sha256('rtsai-standalone-sfx-1/idogdiea.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/voices/idogfea.wav` | dog feedback: snarl and bark | sha256('rtsai-standalone-sfx-1/idogfea.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/voices/idogfeb.wav` | dog feedback: whimper then a sharp bark | sha256('rtsai-standalone-sfx-1/idogfeb.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/voices/idogfec.wav` | dog feedback: whine | sha256('rtsai-standalone-sfx-1/idogfec.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/voices/idogmova.wav` | dog moving: panting and a short bark | sha256('rtsai-standalone-sfx-1/idogmova.wav') | GPL-3.0 code, no third-party rights |
| `standalone/audio/voices/idogsela.wav` | dog selected: one alert bark | sha256('rtsai-standalone-sfx-1/idogsela.wav') | GPL-3.0 code, no third-party rights |

#### Shared-unit voices

Generator `tools/standalone-voices.py` with OpenRA-AI `scripts/voice_engines.py`. Spoken lines: Kokoro-82M `hexgrad/Kokoro-82M@f3ff357` (Apache-2.0), deterministic, so no seed. Death cries: Chatterbox `ResembleAI/chatterbox@5bb1f6e` (MIT), cloned from the speaker's Kokoro English reference, with the seed shown. The prompt is the text.

| File | Unit set | Speaker (voicepacks) | Text | Engine, seed | Licence |
|---|---|---|---|---|---|
| `standalone/audio/voices/ienaata.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | I'll take that building. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienaatb.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Going in. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienaatc.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Securing the site. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienadia.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Aaaargh! | Chatterbox, seed 7 | MIT |
| `standalone/audio/voices/ienadib.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Augh! | Chatterbox, seed 3 | MIT |
| `standalone/audio/voices/ienadic.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Nooo! | Chatterbox, seed 6 | MIT |
| `standalone/audio/voices/ienadid.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Ungh! | Chatterbox, seed 4 | MIT |
| `standalone/audio/voices/ienafea.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Taking fire! | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienafeb.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | I need cover! | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienafec.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Get me out of here! | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienamoa.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Moving. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienamob.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | On my way. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienamoc.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Heading there now. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienasea.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Engineer ready. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienaseb.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Tools ready. What's the job? | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienasec.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | What needs fixing? | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienased.wav` | engineer (EngineerVoice, iena) | shared-engineer-allied (am_adam+am_puck) | Engineer on the net. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/iensata.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Taking over the building. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/iensatb.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Wiring it up now. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/iensatc.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | I'm going inside. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/iensdia.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Arrgh! | Chatterbox, seed 11 | MIT |
| `standalone/audio/voices/iensdib.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Aaah! | Chatterbox, seed 10 | MIT |
| `standalone/audio/voices/iensdic.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Ohhh! | Chatterbox, seed 1 | MIT |
| `standalone/audio/voices/iensdid.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Ugh! | Chatterbox, seed 4 | MIT |
| `standalone/audio/voices/iensfea.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | They're shooting at me! | Kokoro | Apache-2.0 |
| `standalone/audio/voices/iensfeb.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Cover me! | Kokoro | Apache-2.0 |
| `standalone/audio/voices/iensfec.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | I need support! | Kokoro | Apache-2.0 |
| `standalone/audio/voices/iensmoa.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Moving out. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/iensmob.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Going. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/iensmoc.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Right away. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienssea.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Engineer standing by. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/iensseb.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Ready to work. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienssec.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Give me a job. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ienssed.wav` | engineer (EngineerVoice, iens) | shared-engineer-soviet (bm_george+am_michael) | Field engineer here. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/igenexpa.wav` | generic infantry deaths | shared-infantry (am_fenrir+am_puck) | Ugh! | Chatterbox, seed 11 | MIT |
| `standalone/audio/voices/igenmela.wav` | generic infantry deaths | shared-infantry (am_fenrir+am_puck) | Aaaaah! | Chatterbox, seed 5 | MIT |
| `standalone/audio/voices/igenmelb.wav` | generic infantry deaths | shared-infantry (am_fenrir+am_puck) | Arrgh! | Chatterbox, seed 11 | MIT |
| `standalone/audio/voices/igenmelc.wav` | generic infantry deaths | shared-infantry (am_fenrir+am_puck) | Aaah! | Chatterbox, seed 12 | MIT |
| `standalone/audio/voices/igenzapa.wav` | generic infantry deaths | shared-infantry (am_fenrir+am_puck) | Aaargh! | Chatterbox, seed 4 | MIT |
| `standalone/audio/voices/igidia.wav` | generic infantry deaths | shared-infantry (am_fenrir+am_puck) | Aaaargh! | Chatterbox, seed 12 | MIT |
| `standalone/audio/voices/igidib.wav` | generic infantry deaths | shared-infantry (am_fenrir+am_puck) | Augh! | Chatterbox, seed 8 | MIT |
| `standalone/audio/voices/igidic.wav` | generic infantry deaths | shared-infantry (am_fenrir+am_puck) | Ungh! | Chatterbox, seed 10 | MIT |
| `standalone/audio/voices/ispyata.wav` | spy (SpyVoice) | shared-spy (bm_fable) | On my way. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ispyatb.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Getting inside. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ispyatd.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Let's see what they know. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ispydia.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Aaargh! | Chatterbox, seed 3 | MIT |
| `standalone/audio/voices/ispydib.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Ungh! | Chatterbox, seed 3 | MIT |
| `standalone/audio/voices/ispydic.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Aaah! | Chatterbox, seed 11 | MIT |
| `standalone/audio/voices/ispyfea.wav` | spy (SpyVoice) | shared-spy (bm_fable) | My cover is blown! | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ispyfeb.wav` | spy (SpyVoice) | shared-spy (bm_fable) | They're onto me. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ispymob.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Blending in. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ispymoc.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Nobody will notice. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ispymod.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Moving discreetly. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ispymoe.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Consider it done. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ispysea.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Yes? | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ispyseb.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Listening. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ispysec.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Quietly now. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/ispysed.wav` | spy (SpyVoice) | shared-spy (bm_fable) | Agent ready. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgraata.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | Understood. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgraatb.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | Copy that. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgraatc.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | Will do. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgraatd.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | Acknowledged. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgraate.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | Right away. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgramob.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | Rolling. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgramod.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | Moving out. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgramoe.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | On the way. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgramof.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | On course. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrasea.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | Vehicle ready. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgraseb.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | Driver here. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrasec.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | Systems green. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrased.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | Awaiting orders. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrasee.wav` | MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice) | shared-crew-allied (am_michael+am_fenrir) | Standing by. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrsata.wav` | MCV, ore truck and AA track (SovietVehicleVoice) | shared-crew-soviet (bm_lewis+am_fenrir) | Engaging. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrsatb.wav` | MCV, ore truck and AA track (SovietVehicleVoice) | shared-crew-soviet (bm_lewis+am_fenrir) | Target acquired. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrsatc.wav` | MCV, ore truck and AA track (SovietVehicleVoice) | shared-crew-soviet (bm_lewis+am_fenrir) | Opening fire. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrsatd.wav` | MCV, ore truck and AA track (SovietVehicleVoice) | shared-crew-soviet (bm_lewis+am_fenrir) | Weapons free. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrsmoa.wav` | MCV, ore truck and AA track (SovietVehicleVoice) | shared-crew-soviet (bm_lewis+am_fenrir) | Moving. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrsmob.wav` | MCV, ore truck and AA track (SovietVehicleVoice) | shared-crew-soviet (bm_lewis+am_fenrir) | Heading out. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrsmoc.wav` | MCV, ore truck and AA track (SovietVehicleVoice) | shared-crew-soviet (bm_lewis+am_fenrir) | Rolling forward. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrssea.wav` | MCV, ore truck and AA track (SovietVehicleVoice) | shared-crew-soviet (bm_lewis+am_fenrir) | Crew here. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrsseb.wav` | MCV, ore truck and AA track (SovietVehicleVoice) | shared-crew-soviet (bm_lewis+am_fenrir) | Engine running. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vgrssec.wav` | MCV, ore truck and AA track (SovietVehicleVoice) | shared-crew-soviet (bm_lewis+am_fenrir) | Ready to move. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwaaata.wav` | landing craft (AlliedNavalVoice) | shared-naval-allied (am_puck+bm_fable) | Engaging. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwaaatb.wav` | landing craft (AlliedNavalVoice) | shared-naval-allied (am_puck+bm_fable) | Target in sight. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwaaatc.wav` | landing craft (AlliedNavalVoice) | shared-naval-allied (am_puck+bm_fable) | Firing. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwaamoa.wav` | landing craft (AlliedNavalVoice) | shared-naval-allied (am_puck+bm_fable) | Underway. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwaamob.wav` | landing craft (AlliedNavalVoice) | shared-naval-allied (am_puck+bm_fable) | Setting course. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwaamoc.wav` | landing craft (AlliedNavalVoice) | shared-naval-allied (am_puck+bm_fable) | Heading for the beach. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwaamod.wav` | landing craft (AlliedNavalVoice) | shared-naval-allied (am_puck+bm_fable) | Full ahead. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwaamoe.wav` | landing craft (AlliedNavalVoice) | shared-naval-allied (am_puck+bm_fable) | Course laid in. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwaasea.wav` | landing craft (AlliedNavalVoice) | shared-naval-allied (am_puck+bm_fable) | Boat ready. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwaaseb.wav` | landing craft (AlliedNavalVoice) | shared-naval-allied (am_puck+bm_fable) | Helm here. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwaasec.wav` | landing craft (AlliedNavalVoice) | shared-naval-allied (am_puck+bm_fable) | Ready to load. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwaased.wav` | landing craft (AlliedNavalVoice) | shared-naval-allied (am_puck+bm_fable) | Landing craft standing by. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwasata.wav` | amphibious transport (SovietNavalVoice) | shared-naval-soviet (am_michael+bm_lewis) | Engaging. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwasatb.wav` | amphibious transport (SovietNavalVoice) | shared-naval-soviet (am_michael+bm_lewis) | Target spotted. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwasatc.wav` | amphibious transport (SovietNavalVoice) | shared-naval-soviet (am_michael+bm_lewis) | Opening fire. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwasmoa.wav` | amphibious transport (SovietNavalVoice) | shared-naval-soviet (am_michael+bm_lewis) | Into the water. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwasmob.wav` | amphibious transport (SovietNavalVoice) | shared-naval-soviet (am_michael+bm_lewis) | Moving. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwasmoc.wav` | amphibious transport (SovietNavalVoice) | shared-naval-soviet (am_michael+bm_lewis) | Crossing now. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwasmod.wav` | amphibious transport (SovietNavalVoice) | shared-naval-soviet (am_michael+bm_lewis) | Heading to shore. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwassea.wav` | amphibious transport (SovietNavalVoice) | shared-naval-soviet (am_michael+bm_lewis) | Transport ready. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwasseb.wav` | amphibious transport (SovietNavalVoice) | shared-naval-soviet (am_michael+bm_lewis) | Hatch is open. | Kokoro | Apache-2.0 |
| `standalone/audio/voices/vwassec.wav` | amphibious transport (SovietNavalVoice) | shared-naval-soviet (am_michael+bm_lewis) | Amphibious crew here. | Kokoro | Apache-2.0 |

<!-- /standalone-audio-files -->
