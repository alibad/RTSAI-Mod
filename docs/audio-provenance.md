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
