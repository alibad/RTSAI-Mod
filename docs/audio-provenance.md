# Audio provenance

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
| Arabic, Turkish, Mandarin | Chatterbox Multilingual V2, `ResembleAI/chatterbox@5bb1f6e` (`t3_mtl23ls_v2`), `chatterbox-tts` 0.1.7 | MIT | [Model card](https://huggingface.co/ResembleAI/chatterbox): `license: mit`; lists ar, tr, zh |
| Persian | MOSS-TTS-Nano with the Persian fine-tune `nimaaaAI/MOSS-TTS-Nano-Persian@dcfd7f2`, on `OpenMOSS-Team/MOSS-TTS-Nano@44502f8` and `MOSS-Audio-Tokenizer-Nano@6aa02b0` | Apache-2.0 | Fine-tune [LICENSE](https://huggingface.co/nimaaaAI/MOSS-TTS-Nano-Persian/blob/main/LICENSE) (Apache-2.0, trained only on Mozilla Common Voice Persian, CC0); base and codec cards `license: apache-2.0`; [GitHub](https://github.com/OpenMOSS/MOSS-TTS-Nano) LICENSE Apache-2.0 |

Chatterbox embeds Resemble's inaudible Perth watermark in its output. It is left in place.

## Voices

No real person's voice is cloned. Each speaker is a Kokoro voicepack, or the average of two:

- English lines are spoken by the voicepack directly.
- For the other languages, the voicepack first speaks a fixed English reference sentence. Each
  faction's crew therefore keeps one synthetic timbre in both of its languages.
- Arabic, Turkish and Mandarin are a two-step clone with Chatterbox:
  1. From the English clip at `cfg_weight` 0 (the model card's setting against carrying an accent
     across), it speaks the same sentence in the target language.
  2. Each line is cloned from that native clip at the default `cfg_weight` 0.5. Reference and
     target then share a language, as the model card recommends.
- Persian is cloned by MOSS-TTS-Nano directly from the English clip. That is how the Persian
  fine-tune is documented to be used.

| Faction | Infantry and heroes | Vehicle, air and naval crews | Announcer (EVA) |
|---|---|---|---|
| China | `am_puck` | `am_fenrir` + `am_puck` | `af_bella`, crisp networked command voice |
| Iran | `am_michael` | `am_michael` + `bm_george` | `af_sarah`, narrow-band command radio |
| Türkiye | `am_fenrir` | `bm_lewis` | `af_heart`, clean broadcast voice |
| Saudi Arabia | `bm_george` | `bm_fable` | `af_kore`, operations room with a short room tail |
| Yemen | `am_fenrir` + `bm_fable` | `bm_lewis` + `am_michael` | `af_aoede`, lo-fi field radio |

Arabic is Modern Standard Arabic for both Saudi Arabia and Yemen; Chatterbox has no regional
Arabic. The Persian fine-tune was trained on read speech, so the Persian lines are flatter than the
others.

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

### Results (2 October 2026)

| Set | Files | Engines | Exact transcript | Highest error rate |
|---|---|---|---|---|
| Unit voice lines | 148 | 74 Kokoro, 50 Chatterbox, 24 MOSS | 139 | 0.15 |
| Announcer clips | 555 (111 × 5) | Kokoro | 537 | 0.13 |

The remaining mismatches are recognizer homophones such as "ore miner" heard as "or minor", or
"route" as "root". One may be a real slip: `iran-naval-attack-fa.wav` was heard as تسبیح for
تثبیت. Native speakers should review all non-English lines before release.

Compared with the edge-tts files:
- Same format: 44.1 kHz mono 16-bit PCM.
- Speech is 0.90× as long (median).
- Files are about half as long because edge-tts padded each line with about 1.1 s of silence.
- Loudness changed by −0.2 LUFS (median; 10th–90th percentile −2.1 to +1.5).
- The Persian lines rose from −24.2 to −18.7 LUFS. They had been about 4 dB quieter than the
  English lines of the same units.

## Announcers

`mods/rtsai/modern-factions/eva-notifications.yaml` adds a Speech prefix for each modern faction,
so the engine plays `audio/eva/<faction>/<clip>.wav` for that faction's player. Every Speech clip in
`audio/notifications.yaml` has a line for all five factions. The wording is original, not a
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

## Reproduce

From an OpenRA-AI checkout, with the Python environment described in `scripts/voice_engines.py`
and ffmpeg on `PATH`:

```
python scripts/generate-rtsai-mod-audio.py --mod ../RTSAI-Mod                        # everything
python scripts/generate-rtsai-mod-audio.py --mod ../RTSAI-Mod --only tr-air-select-tr.wav --skip-eva
python scripts/generate-rtsai-mod-audio.py --mod ../RTSAI-Mod --eva-only --eva-clips 048,062
```

Partial runs merge their records into `PROVENANCE.json`. Set `RTSAI_MOSS_PYTHON` to the Persian
worker's interpreter.

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

## Open points for the owner

- **Training data.** Each license above covers the weights and their output. The Kokoro model card
  says its data also includes synthetic audio from closed commercial TTS models. Chatterbox and the
  MOSS base model do not disclose their training data. None of this changes the grant to users of
  the weights, but it is the residual risk in this choice.
- **Persian fine-tune.** It is published by an individual (`nimaaaAI`), not by OpenMOSS. Its weights
  are loaded with `torch.load(weights_only=True)` and its code is not run; the model code comes from
  the pinned OpenMOSS revision.

## Sound effects

The 23 weapon, naval and network sounds were not regenerated. Speech recognition finds no speech in
any of them. Nineteen come from procedural generators in OpenRA-AI (`generate-china-sfx.py`,
`generate-red-sea-sfx.py`). The four `naval-*` files came from the fork commit 1d76c546f1 with no
generator or provenance record. Their origin should be confirmed before release.
