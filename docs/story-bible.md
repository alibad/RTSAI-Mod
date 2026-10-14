# Lines of Hope: story bible

Draft 2, 14 October 2026. The playable text comes from `resources/campaign-story.json`; this bible decides what chapters, briefing films, radio calls and debriefs may say. When the two disagree, update the JSON to match the bible (`RTSAI-WebGame/tools/build-campaign-story.py --text-only`), never the other way round.

Draft 2 replaces draft 1's anthology with an alternate-history sequel to the original Red Alert (1996), at the owner's request ("invent a story as creative or even more creative … feel free to use the Red Alert 1 classic stories").

## In one breath

In 1953, at the end of the Red Alert war, Einstein goes to switch off the Chronosphere for good. Arkady Orlov gets there first. He was Stalin's quiet adviser, the man missing from every photograph of the court. He steps through the machine, and the Allied commando Tanya, with a fist in his coat, is pulled through with him. The Chronosphere falls silent, but its echo travels forward seventy-three years and leaks into every radar and radio on a crisis coast in 2026. Pictures loop and clocks read 1953; sweeps move before anything flies. Six commanders on different shores keep their roads, sea lanes and signals open while a civilian coordinator called Lantern follows the echo to its source. That source is Orlov. He now runs the Obsidian Directorate, a sensor broker that sells every army its picture of the world and edits that picture when it pays. He means to edit the whole region into a war.

## The idea underneath

- **Red Alert began when one man was removed from history.** Einstein believed he could fix the century by erasing a single person, and it made everything worse. Orlov's whole craft is erasing people: from photographs in 1953, from radar pictures in 2026. The heroes never win by erasing anyone. They win by keeping lines open so that people get home.
- **Lines of Hope means three kinds of line:** the lifelines (roads, ports, sea lanes), the signal lines (radar, radio, networks) and the timelines. Each act opens a different one.
- **A destroyed base is never the measure of success.** Victory is counted in convoys that arrive, ferries that cross and survivors at the clinic.

## Rules

1. **Red Alert 1 classic material may be used** (owner decision, 14 October 2026): Einstein, the Chronosphere, the Iron Curtain, Tanya and the Allied–Soviet war of the late 1940s and early 1950s. Write every line new: no original dialogue, catchphrases, briefing text or cinematics. Nothing from Red Alert 2 or Yuri's Revenge (RA2 is not freeware); the villain is our own. The EA notice appears wherever this material appears, and no Command & Conquer music is used.
2. **Real modern nations are never the villain of new content.** New chapters pit one playable force against the Obsidian Directorate or Orion Group, in fictional places.
3. **Two real modern nations never share a battlefield in new content,** as allies or as enemies. Tanya, a 1953 Allied soldier with no nation in 2026, may fight beside any commander. When several commanders serve one operation, each holds a separate front and they meet only on the radio.
4. **The three source-dated chapters stay as built** (Jizan, Hodeidah, Bab al-Mandab): same objectives, same factual-cutoff note. The story adds no blame and no new facts about the real crisis. The echo and the Directorate exploit the crisis; they did not cause it.
5. **History stays in 1953.** Historical figures appear only in the 1953 layer. Stalin is never shown speaking; he is a portrait on a wall and an empty chair. The man Einstein removed in the original story is never named or shown. No real living leader appears anywhere.
6. **Civilians are protected, never targeted and never spectacle.** No civilian casualties on screen.
7. **Relay Under Siege stays a labelled fictional training exercise.** Its commander has no name, rank badge or organisation insignia, and it leads to no new operations.
8. **Generated art carries no flags, insignia, logos or lettering** (the shot-list style string enforces this). Einstein is painted in an archival style and is never photoreal. Orlov's face is never shown: he is always cut out, in shadow or reflected in black glass.

## Shape

| Part | Line | Chapters | State (14 Oct) |
| --- | --- | --- | --- |
| Prologue · 1953 | Timeline | A film, not a mission | Film commissioned tonight |
| Act I · The Lifeline | Roads and sea lanes | Jizan Corridor, Hodeidah Lifeline, Bab al-Mandab Passage | Playable; briefing films finishing tonight |
| Act II · Broken Signals | Signals | Straits Shield, Haitan Network, Relay Under Siege | Playable; briefing films finishing tonight |
| Act III · The Missing Man | People | Lights in the Water, Hold the Ferry Line, Glass Island, Black Platform, Every Light On | All five playable: the last three on the Phase 2 mission features (14 Oct) |
| Epilogue | Timeline | A film after the finale | Later |

## Backstory: the 1953 layer

- **1946.** Einstein's first jump removes one man from history. The world that follows is the Red Alert war. (Original Red Alert; we only refer to it.)
- **1953.** The war is over, and Einstein knows the Chronosphere must never run again. On the night he goes to shut it down, Arkady Orlov is already in the chamber. Orlov served at Stalin's side for twenty years and appears in no photograph: the court's retouchers took him out of every picture, on his own orders. Tanya has been hunting him since the war ended. She reaches him on the platform as the machine fires, and both vanish. Einstein shuts the Chronosphere down, but the jump leaves an echo in the signal itself. Before he dies, he puts what he understands on a film reel and hides it where the echo will one day surface.
- **1953 to 2026, for Orlov.** He arrives decades early, in the 1990s, and builds the Obsidian Directorate around the one thing the new century runs on: pictures. Radar maintenance, drone uplinks, "clean pictures" sold to anyone, often to both sides of one coast. Inside each uplink is a hand-wound coil copied from the Chronosphere: the Directorate's network is a Chronosphere antenna spread across a whole region. **For Tanya**, the jump lasts an instant. She surfaces off a reef in 2026, the night Act III begins.

## The antagonist

**Arkady Orlov, "the Broker".** He is calm, courteous and patient, and always opens with an offer: "You could have a clearer picture." He believes the world is run by whoever controls what it sees, and that a war seen on every screen is the most valuable picture of all. He never raises his voice and never appears. On radio he is a slightly processed voice; on screen he is a gap in a photograph, a silhouette, a reflection in black glass. Only Tanya knows his face.

**The Obsidian Directorate.** A stateless sensor broker. It blinds and spoofs the systems it maintains to create demand, and it serves every side at once. It is never a state, an ethnicity or a religion, and it has no flag.

**Orion Group.** The Directorate's contractor force: frigates, corvettes, uncrewed surface vessels and guard units with no national markings.

**What he wants.** He wants to run the rebuilt Chronosphere once through the whole regional network, edit the picture every army sees, and stage an attack that never happened. That would put a red alert on every screen at once.

**Visual signature.** Matte black glass masts, domes and housings, each with a single cold white strobe, set against the amber of the lifelines. Hand-wound copper coils glow inside 2026 hardware.

## Cast

The player commands as a different commander in each chapter. Portrait anchors repeat the original shot-list prompts so a face stays the same; later portraits are Qwen-Image edits of the first.

| Name | Who | Chapters | Portrait anchor |
| --- | --- | --- | --- |
| Colonel Badr Al-Shammari (Saudi Arabia) | Sees the radar go silent first, and closes the story | I-1, III-5 | Fifties, short grey beard, desert camouflage, radio headset, dim forward command post |
| Captain Nabil Haidar (Yemen) | Brings everyone home; finds Tanya | I-2, III-1 | Thirties, short black beard, olive field uniform, scarf, radio handset, beside a dusty pickup |
| Commander Turki Al-Zahrani (Saudi Arabia) | Passage Control; boards the platform | I-3, III-4 | Forties, neat black beard, navy uniform, headset, harbour control room |
| Colonel Kemal Aydın (Türkiye) | Takes the strait, then holds it | II-1, III-2 | Fifties, short grey hair and moustache, green camouflage, headset, coastal command post |
| Commander Lin Haoran (China) | Restores the island network; goes to Glass Island | II-2, III-3 | Forties, short black hair, blue digital camouflage, headset, ship deck at night |
| The signals chief | Exercise commander, unnamed by rule 7 | II-3 | Forties, short dark beard, plain olive fatigues without badges, bunker radio room |
| **Lantern**, Dr. Amina Farah | Civilian deconfliction coordinator from the far shore of the strait; a physicist by training. She shares traffic pictures so aid and shipping can move, notices that every side's blind spots match, and follows the echo to 1953. The story's conscience. | Every act, on the radio | Forties, plain shirt and cardigan, glasses pushed up, small operations room lit by one amber desk lamp |
| **Tanya** | Allied commando from 1953, displaced to 2026. Fearless, dry and fast; rarely surprised by danger, but often surprised by the future ("They fight wars from a screen now?"). The only person alive who knows Orlov's face. | Prologue, III-1 to III-5 | Late twenties, dark hair tied back, 1950s commando fatigues and webbing, rolled sleeves, pistol holster, sea-soaked when found |
| **Albert Einstein** | The scientist who started it, trying to end it; speaks from his 1953 film reel | Prologue, III-3, III-5 | Elderly physicist with white hair and moustache, in painted archival style, lit by Chronosphere blue |
| **Arkady Orlov**, the Broker | See the antagonist | Prologue, voice from III-2 | Never shown: a figure cut out of a photograph, a silhouette, a reflection |

## Prologue · 1953 (film)

Archival look: film grain, silver and tungsten light, Chronosphere blue arcs. Six shots:

1. The vast Chronosphere chamber under a mountain, 1953; Einstein alone at the control desk. "Nineteen fifty-three. The war is over, and Albert Einstein has one task left: switch off the machine that started it."
2. A formal 1950s photograph of a state room: officials in a row, one gap where a man was cut out. "In every photograph of Stalin's court, one place is empty. His name was Arkady Orlov."
3. A woman commando running through a concrete corridor lit by red alarm lamps, pistol drawn. "The Allies sent their best to bring him in."
4. The platform firing: a silhouette in a long coat in the white core, a woman leaping to grab him. "He reached the machine first. She reached him."
5. The empty chamber, the arcs dying, a radio needle still swinging. "The Chronosphere fell silent. Its echo did not."
6. 2026, dawn over a Red Sea coast: a radar dish on a hill stops turning. "Seventy-three years later, on a coast at dawn, a radar goes quiet." Title card: *Lines of Hope*.

## Act I · The Lifeline (built)

Three views of one coast in crisis, 2026. The echo surfaces in the picture.

| Chapter | Commander | Mission | What the player learns (debrief and radio) |
| --- | --- | --- | --- |
| 1 · A Road Through the Silence | Badr | Retake Radar Node Seven, destroy two launchers, bring the convoy to the port | The radar was never destroyed: it showed an empty sea, and its clock read 1953 |
| 2 · The Return Journey | Nabil | Deliver supplies inland, clear the surveillance zone, bring the evacuation convoy home | The sweep moved four minutes before anything flew: someone reads the picture before it happens |
| 3 · Four Ships at First Light | Turki | Radar network, three sectors, launchers, four ships through | Every blind spot traces to one contract, held by the Obsidian Directorate; its oldest file is a 1953 photograph with one man cut out |

## Act II · Broken Signals (built)

The Directorate's hardware, in fictional places.

| Chapter | Commander | Mission | What it adds |
| --- | --- | --- | --- |
| 1 · Across the Divide | Kemal | Destroy three uplinks, capture the harbour relay, sink the five-ship group | Orion Group answers to no country; inside every uplink is a hand-wound coil dated 1953 |
| 2 · Bring the Islands Online | Lin | Restore the network, run the water gate, destroy the control node | The traffic leads to one island no chart names, sending a time code seventy-three years old |
| 3 · Keep the Signal Alive | Signals chief | A training exercise: relay and workshop, survive, take the command post | Stays an exercise (rule 7) |

## Act III · The Missing Man (new)

Five chapters on classic mission patterns, in fictional places. Tanya joins from chapter 1. Each chapter borrows the layout, pacing and objectives of a preserved original Red Alert mission (OpenRA's ports under `OpenRA/mods/ra/maps`, indexed in `resources/map-library.json`) and replaces everything else.

### III-1 · Lights in the Water (rescue)
- **Commander:** Nabil. **Setting:** a fictional reef coast and fishing town, at night. **Source missions:** Evacuation; Allies 01 "In the Thick of It".
- **Mission:** Spoofed navigation walked a fishing fleet onto the reef, and Orion patrols are searching the water for someone. With a small force and no base, find three stranded crews and bring every survivor to the clinic.
- **Beat:** the third crew has pulled a stranger out of the sea, a woman in a soaked 1950s uniform. "Took you long enough. Who's in charge here, and what year is it?" At the clinic she gives her name: Tanya.

### III-2 · Hold the Ferry Line (timed defence)
- **Commander:** Kemal, with Tanya. **Setting:** the strait port town on the shore taken in Straits Shield. **Source missions:** Exodus; Survival 01.
- **Mission:** Orion Group wants the strait back. Hold three approaches for twelve minutes while four ferries carry the town across.
- **Beat:** the Broker speaks for the first time, offering Kemal "a much clearer picture of the strait". Tanya knows the voice: Orlov. A prisoner's orders name Glass Island.

### III-3 · Glass Island (infiltration)
- **Commander:** Lin, with Tanya. **Setting:** the uncharted island from Haitan. **Source missions:** Infiltration; Allies 09a "Evacuate Kosygin".
- **Mission:** A three-unit team lands at night, stays out of the sensor masts' sight, copies the routing logs and leaves by boat. Sensor masts show their zones as rings; most sweep on a cycle, so the team crosses while a ring is dark. Every mast that sees the team, or goes dark, sends the garrison; the island tolerates one alarm on normal.
- **Beat:** beside the logs is a film reel in Einstein's hand. His 1953 message: the Chronosphere was never truly switched off; its echo can only be folded shut by running the machine once, the right way, and only from the place it is now anchored. That place is the Directorate's hub, hidden behind a jammer platform.

### III-4 · Black Platform (commando)
- **Commander:** Turki, with Tanya. **Setting:** a Directorate jamming platform in open sea. **Source mission:** Allies 13 "Focused Blast".
- **Mission:** The jammers run on an Iron Curtain prototype that makes the platform untouchable from outside. A boarding team with no reinforcements takes the curtain control room with an engineer (the curtain drops), places charges on every generator, then holds the room against the counterattack from the docks and the sea. Losing Tanya, the room, or both engineers before the capture fails the mission.
- **Beat:** every screen on the coast lights up at once. The hub is exposed, and the Broker makes his offer to everyone at the same moment. Nobody answers.

### III-5 · Every Light On (finale)
- **Commander:** Badr, closing the story that began with his silent radar. **Setting:** the Directorate hub on a fortified fictional island chain, with the rebuilt Chronosphere at its heart. **Source missions:** Soviet 13a "Capture the Chronosphere"; Intervention.
- **Mission:** Take the radar domes to sever the link, then capture the Chronosphere. Four fronts are heard only on the radio (rule 3):
  - Lin keeps the picture alive; if the relay falls, the fog returns.
  - Turki holds the platform, and the jamming stays off.
  - Kemal closes the northern lane, so naval waves stop at a set minute.
  - Nabil reports the mainland towns clear, and the final strike unlocks only then.
- **Ending:** as the machine falls, Orlov steps into it and is gone. Lantern runs Einstein's sequence once, the right way, and the echo folds shut; across the coast, convoys, ferries and ships light up one by one. The captured Chronosphere could send Tanya home to 1953. She stays: "He's out there somewhere in time. Somebody who knows his face should be waiting."

### Epilogue (film)
Lantern pins a print to her wall: the 1946 photograph of the Chronosphere's first test, Einstein beside the machine. In the background stands a man who was not in the picture yesterday. Fade to amber.

## Radio calls

Every mission has calls in `campaign-story.json` under `radio`: a speaker from the cast, one line, and a trigger (`start`, a game-time second, an objective index, `victory`, `defeat`). House style:
- one or two short sentences, spoken by the person who would say them;
- the commander gives orders, Lantern brings what the coordination desk sees, and Tanya speaks only from III-1;
- the Broker always makes an offer and never threatens;
- calls carry the clue thread (1953, the loop, the contract, the coil, the island) so a player who skips films still follows the story.

## Look and sound

- **Two worlds.** 1953 is archival: grain, silver, tungsten and Chronosphere blue. 2026 is painted key art: amber lifelines, red threats and the cold white of the Directorate. When the echo surfaces, a 1953 image bleeds into a 2026 screen.
- **Recurring images.** The holographic briefing table built from the mission's own map; the commander's portrait; the gap in the photograph; the copper coil inside black glass; the last shot of each film on the line that matters.
- **Voices.** One narrator for the films. From Act III, Lantern opens each briefing and the commanders give orders on the radio. The Broker's voice is calm and slightly processed, and Einstein's is an old recording.
- **Music.** The 1953 theme is a slow brass waltz under film crackle. Act I uses oud, frame drum and low strings; Act II synth pulses and taiko; Act III joins them under one amber brass theme, which the finale states in full. All scores are ACE-Step originals.

## What Act III needs from the game (Phase 2)

- Radio calls with portraits and captions (built 14 Oct; calls can also key off mission events).
- Timed events; event-gated objectives and reinforcements; map-wide reveal events (the "lights on" moments). Built 14 Oct (RTSAI-WebGame `Missions.cs`, desktop `RTSAICampaign.cs`).
- Fixed-squad starts with a squad-loss failure, and a Tanya hero unit. Built 14 Oct; Tanya is the `tany` actor drawn with the original commando art (america faction) until an original 1953 commando model is made.
- Detection zones: a unit seen by a sensor mast raises the alarm. Built 14 Oct.
- Lazy-loaded mission maps.

## Production

1. Shot lists live in `RTSAI-WebGame/tools/briefings/<id>.json`; stills come from `art.mjs` (Qwen-Image 2.1), clips from the forge commission, and the cut from Montage; `from-montage.mjs` publishes them. Cast portraits go to the CDN under `campaign/cast/<id>.webp`.
2. Returning faces: extend `art.mjs` with a portrait reference so a later portrait is an edit of the first.
3. For each new chapter: map, mission, a playtest of every success and failure path, radio calls, then the film.

## Open decisions

- Iran and Israel have no chapters. Either keep them skirmish-only, or give each a fictional-theatre chapter against the Directorate under rules 2 and 3.
- Voices for Lantern, Tanya, the Broker and Einstein's recording (local Chatterbox voices; never a clone of a real person's voice).
- Whether the six built films are later re-cut with the prologue's look and Lantern's opening line.
