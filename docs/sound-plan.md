# RTS AI sound plan: the seven modern factions

The owner asked (14 October 2026) whether the local models are good enough to make solid sounds for every new unit,
and for a well-thought plan for all sounds. This is that plan. The nine original countries are out of scope: they get
Westwood's original voices and sounds (branch `rtsai/original-voices` in RTSAI-WebGame, under EA's non-commercial
modding guidelines; never C&C music).

**The bar:** with your eyes closed you can tell what is on screen and whose it is. Every unit sounds like itself,
every faction sounds like a place, and nothing ships until the owner (and, for speech, a native speaker) has listened.

## 1. Where we are

Measured on RTSAI-Mod `main` 7497bea with `tools/standalone-audit.py` and the provenance files
(`mods/rtsai/modern-factions/audio/PROVENANCE.json`, `mods/rtsai/standalone/audio/PROVENANCE.json`).

| | Today | What is wrong |
|---|---|---|
| Unit voices | 252 lines, 41 voice sets for 124 units. Chatterbox (ar, he, tr, zh), MOSS (fa), Kokoro (en) | Sets shared by up to 8 units; in four factions Move, Attack and Action play the same line; no Feedback lines; all deaths are the same 3 cries; 0 of 230 rows reviewed by a native speaker |
| Weapons | 129 weapon definitions; China, Iran and Türkiye have no sounds of their own | Procedural stand-ins under RA2 file names: `igiat1a-c` on 18 units (tank coax guns and heroes included), `vintatta` on 19, all 12 AA weapons share one sound; a demolition charge plays a tank cannon; boats "fire" an alarm; 6 weapons are silent |
| Impacts | 8 files for 124 units | `gexp14a` on 41 units |
| Deaths | 3 explosion files for every vehicle, ship and building | No size or material difference |
| Movement | Nothing for vehicles, ships or jets | Only two drones have a loop |
| Announcer | 7 × 111 Kokoro English lines, identical script, female voices | Says "Chronosphere ready" for the Strategic Uplink and "Iron Curtain ready" for the EW Array |
| Buildings, UI | Procedural, identical for every faction | |
| Ambience | None | |
| Music | 11 ACE-Step tracks, one global playlist | Owner found it repetitive (d974499); Yemen has no track |
| The dog | Numpy synthesis (a jittery vowel-shaped buzz) | It doesn't sound like a dog |

Nothing reachable in a skirmish is silent. The problem is that almost nothing has its own voice.

## 2. Are the local models good enough?

| Need | Local model | Verdict |
|---|---|---|
| Speech in Arabic, Hebrew, Turkish, Mandarin | Chatterbox Multilingual V2 (MIT, 0.5B, voice cloning, `exaggeration` for shouting) | **Good enough with direction.** Needs written personas, best-of-N takes, a radio chain and native review. No dialect control: Saudi and Yemeni lines come out Modern Standard Arabic. Hebrew needs vowel points (error rate 0.21 → 0.05). |
| Speech in Persian | MOSS-TTS-Nano + a Persian fine-tune (Apache-2.0) | **Not good enough.** Read-speech style, and Whisper often fails to recognise it as Persian. |
| Speech in English | Kokoro-82M (Apache-2.0) | Good for the announcer, flat for soldiers. Chatterbox English with cloning is better for units. |
| Sound effects | **None installed.** Everything is `standalone_dsp.py` synthesis | **No.** This is why the guns, explosions and the dog sound thin. |
| Music | ACE-Step 1.5 (MIT) | **Good enough.** The problem was structure and repetition, not the model. |
| Checking | Whisper large-v3, LAION CLAP | Good: Whisper checks speech against the script; CLAP can score sound candidates against their description. |

So: voices yes (except Persian), music yes, sound effects need a new source.

## 3. Where new sounds come from

Licence rule: every file must be redistributable inside the GPL-3.0 game and the public repos. Weights or libraries
under a non-commercial licence are out, as the project already decided for XTTS-v2 and the CC BY-NC Chatterbox-Persian
fine-tunes.

| Source | Use it for | Licence | Status |
|---|---|---|---|
| **CC0 recordings**: the Free Firearm Sound Library (OpenGameArt), Freesound CC0 only, BigSoundBank | Real gunshots, mechanisms, engines, tracks, impacts, debris, boots | CC0 | Download to `D:\rtsai-sound\sources`, hash every file |
| **Stable Audio 3.0 Small SFX** (459M, May 2026, trained on licensed data) | Layers that can't be recorded: drone buzz, EW and laser textures, rocket roars, explosion tails, ambience beds | Stability AI Community License: outputs are ours; free below $1M yearly revenue; Gemma terms ride along with its text encoder | Not installed; ~2 GB on D: |
| Stable Audio Open 1.0 (trained on CC0, CC-BY and Sampling+ audio) | Second opinion in the bake-off | Stability AI Community License | Not installed |
| Chatterbox Multilingual | All unit speech except Persian; death cries (`exaggeration`) | MIT | Running service `voice` :8004 |
| Persian: a Chatterbox fine-tune on Common Voice Persian (CC0), or native volunteer recordings | Iran's voices | MIT / CC0 / volunteer release | To build or recruit |
| Kokoro | Announcers | Apache-2.0 | Running service `tts` :8002 |
| ACE-Step 1.5 | Music and stingers | MIT | Service `music` :8014 |
| `standalone_dsp.py` | UI ticks, beeps, simple tones only | Project code | Kept for UI |

**Rejected:** Sony Woosh, TangoFlux, MMAudio, OmniVoice and AudioGen (weights CC BY-NC or research-only); XTTS-v2
(CPML); the Sonniss GDC bundles (no AI use, no redistribution as files; a public repo of game files is too close);
any EA audio in the modern factions (their identity is their own).

**Why both recordings and generation:** generated audio is good at textures, tails and things that don't exist; it is
weak at the tight, punchy transient that makes a gunshot or a cannon feel real. Real CC0 recordings give the transient
and body, and generated layers give the character.

## 4. Each faction's sound

Each faction gets a material palette and a voice direction, so its sounds share a family resemblance. Voices stay
professional radio chatter: no slogans, no slurs, no religious phrases, the same dignity for every side (the narrative
guardrails in `docs/story-bible.md` apply).

| Faction | Palette | Signature sounds | Voices |
|---|---|---|---|
| China | Clean, electric, precise: capacitor whine, rail cracks, servo motors | Networked weapons ticking in sync; the Qilin's turbine; carrier drone launches | Mandarin, crisp and disciplined; English callsigns |
| Iran | Missiles and drones: solid-fuel roars, the two-stroke moped buzz of a one-way drone, heavy diesel | Salvo launches that ripple; drone swarms you hear before you see | Persian, steady and formal |
| Türkiye | Drones and modern armour: propeller drones, rotary cannons, a modern tank turbine | The Grey Wolf hero's own kit | Turkish, confident |
| Saudi Arabia | Expensive Western kit: jet turbines, interceptor launches, smooth hydraulics | Patriot-style interceptor boost; the strike jet's flyby | Gulf Arabic |
| Yemen | Improvised and rugged: diesel technicals, rattling metal, older rifles, boat outboards | Skiff motors; launch rails that clank | Yemeni Arabic |
| Israel | Precision and defence: interceptor bursts, a heavy tank's engine, quiet electronics | Interceptor "pop and chase"; the anti-missile burst | Hebrew, terse |
| Hezbollah | Cheap missiles, elite soldiers, micro-drones: launch tubes, FPV quad whine, close-quarters gunfire | FPV swarm whine; the elite soldiers' suppressed weapons | Levantine Arabic, low and calm |

## 5. What every unit gets

| Slot | Content | Variants |
|---|---|---|
| Select | 3 lines | Unique per hero and elite unit; shared per class inside a faction otherwise (no set covers more than 3 units) |
| Move, Attack | 3 lines each, all different | |
| Feedback (under fire, panic) | 2 lines | New: the engine has the slot, we never filled it |
| Death | Infantry: 3 cries per faction and language; vehicles and ships: by size and material | |
| Weapon report | Its own sound per weapon family | 3, picked at random by the engine |
| Projectile | Missile and rocket whoosh, shell whistle for artillery | 2 |
| Impact | By warhead: bullet on armour, bullet on flesh/ground, HE small/medium/large, AP, frag, incendiary, EMP | 3 |
| Movement | Engine loop while moving (`AmbientSound` gated by `GrantConditionOnMovement`, already in the engine): tracked, wheeled, hover, jet, prop drone, quad drone, rotor, fast boat, diesel ship, submarine | 1 loop + start |
| Deploy and special | Deploy/fold, mode switch, cloak, ability use | 1–2 |

Faction level: an announcer with its own script and correct wording (Strategic Uplink, EW Array), in a voice that
fits the faction (accented English, or the native language with subtitles); building place, power down, sell and
destroyed by size; the superweapon cycle (charging, ready, launch, impact); 2–3 music tracks each plus menu, score and
victory/defeat stingers; map ambience per biome (wind, birds, surf, distant city).

**Volume.** About 70 voice sets × 13 lines ≈ 900 lines (plus English variants where a faction mixes languages); about
45 weapon families × 3 = 135; impacts 15 × 3 = 45; deaths ≈ 60 (42 cries + by-size explosions); movement ≈ 25
loops; deploy and special ≈ 25; 7 announcers × ~120 = 840 lines; buildings and UI ≈ 50; ambience ≈ 10; music ≈ 20
tracks. Roughly 2,100 files.

## 6. The pipeline

All new tools live in `tools/sound/` and run on D: (C: is full).

1. **Spec**: `audio/sound-spec.yaml`, one entry per slot: what it is ("Qilin 125 mm main gun, heavy, metallic
   ring"), the faction palette, sources, recipe, loudness class, status. Generated from the rules so no slot is
   forgotten, then written by hand.
2. **Sources**: CC0 files and generated takes kept outside git under `D:\rtsai-sound\sources`, each with its hash,
   licence and origin URL or prompt and seed.
3. **Build**: a deterministic recipe per sound (layers, pitch, envelope, EQ, convolution reverb with a CC0 outdoor
   impulse response, limiter), using pedalboard and numpy. Rebuilding gives the same bytes, like `standalone-sfx.py`.
4. **Measure**: loudness per class (voices about −16 LUFS, weapons and explosions peak −1 dBTP, UI −20 LUFS, music
   −14 LUFS integrated as now), duration, clipping, CLAP score against the description, Whisper for speech.
5. **Listen**: a sound board page (the Faction viewer's sound panel for finished units; a review page with A/B against
   the current sound and the RA2 reference for candidates) with approve/reject per sound. Approvals are recorded in
   `docs/voice-review.csv` and the provenance files. Speech also gets a native speaker per language.
6. **Ship**: into the mod, the browser game's audio pack, the desktop release and the website's published clips;
   provenance in `PROVENANCE.json` for every file.

## 7. Phases

| Phase | What | Size | Owner time |
|---|---|---|---|
| 0. Bake-off | 10 test sounds (rifle, tank cannon, missile launch, explosion, impact, jet flyby, tank engine loop, quad drone, EW zap, building collapse), each from CC0 layering, Stable Audio 3.0 Small SFX, Stable Audio Open and today's synthesis, next to the RA2 original; 6 shouted voice lines per language with Chatterbox; 3 Persian options | ~60 candidates | 20 minutes of listening, then pick the pipeline |
| 1. Weapons, impacts, deaths | The biggest change you can hear | ~250 files | 2 listening sessions |
| 2. Movement and presence | Engine loops, flybys, wakes, start-ups | ~50 | 1 |
| 3. Voices | Personas and scripts per unit, generation, native review; Persian route decided in phase 0 | ~900 lines | 1 per faction + native reviewers |
| 4. Announcers | Faction scripts with the right wording, new voices | ~840 lines | 1 |
| 5. Buildings, superweapons, UI, ambience | | ~80 | 1 |
| 6. Music | 2–3 tracks per faction with real structure, stingers | ~20 tracks | 1 per faction |

Each phase ships on its own: spec, generate, measure, owner listens, release to the browser game and the desktop
build, then the website clips.

## 8. Risks

- **Licence of Stable Audio**: the Community License caps revenue at $1M a year and can change; outputs stay ours.
  CC0 recordings carry no such risk, so weapons lean on them.
- **Arabic dialects**: Chatterbox has no dialect control. Mitigation: dialect-specific wording and native review; a
  native volunteer recording a reference voice per faction.
- **Persian**: the weakest language today; decided in phase 0 (fine-tune vs. volunteers).
- **Sensitivity**: real-world factions. Lines are reviewed for tone, and a native speaker checks that nothing reads as
  a slogan.
- **GPU sharing**: generation runs only outside the Video Forge's claim windows (`AI\logs\gpu-claim.txt`, yield via
  `gpu-yield.txt`), and services stop when a batch ends.
- **Mix consistency**: thousands of files from mixed sources can sound like a collage. The loudness classes, shared
  reverb and the faction palettes are there to prevent that.

## 9. Decisions for the owner

1. Add Stable Audio 3.0 Small SFX (and Stable Audio Open for the bake-off) under the Stability AI Community License.
2. Use CC0 recording libraries as the base for weapons and engines.
3. Persian (and ideally every language): recruit native volunteers for reference voices and review, or AI only?
4. Announcers: accented English, the native language with subtitles, or both?
5. Start phase 0.
