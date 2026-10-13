# Lines of Hope: story bible

Draft 1, 14 October 2026. The playable text still comes from `resources/campaign-story.json`; this bible decides what new chapters, briefing films, radio lines and debriefs may say. When the two disagree, update the JSON to match the bible (`RTSAI-WebGame/tools/build-campaign-story.py --text-only`), never the other way round.

## In one breath

Someone is switching off the region's eyes and ears. Radar goes quiet, pictures loop, navigation lies, and every side buys a "clearer picture" from the same broker. Six commanders who never share a battlefield learn the same lesson from different shores: the only thing worth defending is the line that gets people home, whether that line is a road, a sea lane or a signal.

## What the campaign is about

- **A lifeline matters because of who is at the end of it.** Victory is counted in convoys that arrive, ferries that cross and people who come home, not in bases destroyed. Jizan already says it: "A destroyed enemy base is not the measure of success."
- **A network turns isolated forces into a team.** This is the lesson of Broken Signals, and the enemy is the one who sells the network and cuts it.
- **Three kinds of line, three acts:** roads and sea lanes (Act I), signals (Act II), people (Act III).

## Rules

1. **Real nations are never the villain of new content.** New chapters pit one playable nation against the fictional Obsidian Directorate or its contractor arm, Orion Group, in fictional places.
2. **The three source-dated chapters stay as built** (Jizan, Hodeidah, Bab al-Mandab): same objectives, same factual-cutoff note. The story adds no blame and no new facts about the real crisis. The Directorate exploits the crisis; it did not cause it.
3. **No real leaders, operations, attacks or force dispositions.** Generated art carries no flags, insignia, logos or lettering (the shot-list style string enforces this).
4. **Civilians are protected, never targeted, never spectacle.** No civilian casualties on screen; civilians appear as the people the player gets home.
5. **Two real nations never share a battlefield in new content,** as allies or as enemies. When several commanders contribute to one operation, each holds a separate front and they meet only on the radio.
6. **Relay Under Siege stays a labelled fictional training exercise.** Its commander has no name, rank badge or organisation insignia, and the exercise does not lead into new operations.
7. **EA conditions hold:** no Command & Conquer music; every score is an original ACE-Step piece, and the EA notice stays where the release requires it.

## Shape: three acts, eleven chapters

| Act | Line | Chapters | State |
| --- | --- | --- | --- |
| I · The Lifeline | Roads and sea lanes | Jizan Corridor, Hodeidah Lifeline, Bab al-Mandab Passage | Playable; films: Jizan done, rest rendering 14 Oct |
| II · Broken Signals | Signals | Straits Shield, Haitan Network, Relay Under Siege | Playable; films rendering 14 Oct |
| III · Lines of Hope | People | Lights in the Water, Hold the Ferry Line, Glass Island, Black Platform, Every Light On | Not built; needs the Phase 2 mission engine |

The acts run in order, but every chapter stays playable on its own, as today.

## The antagonist

**Obsidian Directorate.** A stateless sensor broker. It sells radar maintenance, drone uplinks and "clean pictures" to anyone who pays, often to both sides of the same coast, and it creates demand by blinding and spoofing the very systems it maintains. It wins whenever nobody can see clearly. It is never a state, an ethnicity or a religion, and it has no flag.

**Orion Group.** The Directorate's contractor fleet and security force: frigates, corvettes, uncrewed surface vessels and guard units without national markings. It is the force the player fights in Straits Shield.

**The Broker.** The Directorate's only voice. Calm, polite and commercial, it always opens with an offer ("You could have a clearer picture"). It is never shown; its image is a matte black glass surface reflecting screen light. It first speaks in Act III.

**Visual signature.** Matte black glass masts, domes and housings with a single cold white strobe, against the amber of the lifelines.

## Cast

The player commands as a different commander in each chapter. Act III brings five of them back. Portrait anchors repeat the original shot-list prompts so a face stays the same; later portraits should be Qwen-Image edits of the first one (see Production).

| Name | Role | Faction | Chapters | Portrait anchor |
| --- | --- | --- | --- | --- |
| Colonel Badr Al-Shammari | Army colonel who first sees the radar go silent | Saudi Arabia | I-1, III-5 | Fifties, short grey beard, desert camouflage, radio headset, dim forward command post |
| Captain Nabil Haidar | Army captain on the relief corridor | Yemen | I-2, III-1 | Thirties, short black beard, olive field uniform, scarf, radio handset, beside a dusty pickup |
| Commander Turki Al-Zahrani | Naval commander at Passage Control | Saudi Arabia | I-3, III-4 | Forties, neat black beard, navy uniform, headset, harbour control room with radar screens |
| Colonel Kemal Aydın | Army colonel at the strait crossing | Türkiye | II-1, III-2 | Fifties, short grey hair and moustache, green camouflage, headset, coastal command post |
| Commander Lin Haoran | Marine commander of the island network | China | II-2, III-3 | Forties, short black hair, blue digital camouflage, headset, ship deck at night |
| The signals chief | Exercise commander, unnamed by rule 6 | Hezbollah | II-3 | Forties, short dark beard, plain olive fatigues without badges, bunker radio room |
| Dr. Amina Farah, call sign **Lantern** | Civilian deconfliction coordinator from the far shore of the strait; shares traffic pictures so aid and shipping can move | none | Clues from I-3; opens every Act III briefing | Forties, plain shirt and cardigan, glasses pushed up, small operations room lit by one amber desk lamp |
| The Broker | Voice of the Obsidian Directorate | Obsidian Directorate | III-2 to III-5 | Never shown |

Lantern is the thread through all three acts. She works with everyone and belongs to no one, which is exactly why she notices that every side's blind spots match.

## Act I · The Lifeline (built)

Three views of one coast in crisis. The gameplay and the real-world framing stay as built (rule 2). The story adds only what the player notices.

| Chapter | Commander | What happens | What the player notices |
| --- | --- | --- | --- |
| 1 · A Road Through the Silence | Badr | Retake Radar Node Seven, destroy two launchers, bring the relief convoy to the port | The radar was never destroyed: for six hours it showed an empty, looping sea |
| 2 · The Return Journey | Nabil | Deliver supplies inland, clear the surveillance zone before the sweep, bring the evacuation convoy home | The sweep moved before anything was airborne, as if someone was reading the same picture first |
| 3 · Four Ships at First Light | Turki | Build the radar network, survey three sectors, remove the launchers, see four merchant ships through | Lantern reports that every gap in the coastal picture matches one maintenance contract, held by the Obsidian Directorate |

## Act II · Broken Signals (built)

The Directorate's own hardware, in fictional places.

| Chapter | Commander | What happens | What it adds |
| --- | --- | --- | --- |
| 1 · Across the Divide | Kemal | Build all branches, destroy three drone uplinks, capture the harbour relay, sink the five-ship group | First fight against Orion Group; the uplinks carry no flag, only Directorate serials |
| 2 · Bring the Islands Online | Lin | Restore the command network, run the water gate, destroy the control node | The restored links show the region's traffic routed to one island no chart names |
| 3 · Keep the Signal Alive | Signals chief | A training exercise: build a relay and workshop, survive four minutes, destroy the opposing post | Stays an exercise (rule 6); its theme, keeping your own signal alive when it is cut, sets up Act III |

## Act III · Lines of Hope (new)

Five chapters built on classic mission patterns, all in fictional places, each against the Directorate or Orion Group. Objective kinds in **bold** already exist in the browser host (`capture`, `destroy`, `escort`, `protect`, `build`, `reach`, `scout`, `survive`, `disperse`, `shipping`); the rest are Phase 2 features.

### III-1 · Lights in the Water (rescue)
- **Commander:** Nabil. **Setting:** a fictional reef coast and fishing town, night into dawn.
- **Premise:** Spoofed navigation signals have walked a fishing fleet and a relief boat onto a reef line. With a small mobile force and no base, find the three stranded groups before the tide turns and bring them to the town clinic.
- **Objectives:** **scout**/**reach** each group, **escort** survivors to the clinic, **protect** the clinic, all under a tide timer (Phase 2).
- **Plot beat:** a survivor's chart plotter recorded the false signal. It came from offshore, from a platform no chart lists.
- **Title line:** "Bring them in."

### III-2 · Hold the Ferry Line (timed defence)
- **Commander:** Kemal. **Setting:** a fictional strait port town on the shore taken in Straits Shield.
- **Premise:** Orion Group wants the strait back. A town has to cross on evacuation ferries before the counterattack arrives in force. Hold three approaches while the ferries load and sail.
- **Objectives:** **survive** twelve minutes, **protect** the piers, at least four ferries across (**shipping**).
- **Plot beat:** a captured contractor carries a Directorate tasking order with a platform call sign. The Broker speaks for the first time, on an intercepted channel, offering Kemal "a clearer picture of the strait".
- **Title line:** "Twelve minutes. Every ferry."

### III-3 · Glass Island (infiltration and extraction)
- **Commander:** Lin. **Setting:** the uncharted island found in Haitan Network.
- **Premise:** A three-unit team (network specialist, engineer, scout drone) lands at night, stays out of the sensor masts' cones, copies the routing logs at the core node and leaves by boat.
- **Objectives:** **reach** the node unseen (detection zones and alarm waves, Phase 2), **capture** the node, **reach** the extraction point.
- **Plot beat:** the logs give Lantern the whole map: the Directorate's hub, and the offshore jammer platform that hides it.
- **Title line:** "Seen by no one."

### III-4 · Black Platform (commando)
- **Commander:** Turki. **Setting:** a Directorate jamming platform in open sea.
- **Premise:** While the platform jams, no one can see the hub. A boarding team with no reinforcements disables four jammer arrays, then holds the control room until the picture comes back.
- **Objectives:** **destroy** four arrays, **capture** the control room, **survive** three minutes; a fixed squad with no base, and losing it fails the chapter (Phase 2).
- **Plot beat:** every screen on the coast lights up at once. The hub is exposed, and the Broker makes his offer to everyone at the same time. Nobody answers.
- **Title line:** "Lights on."

### III-5 · Every Light On (finale)
- **Commander:** Badr, closing the story that began with his silent radar. **Setting:** the Directorate hub, a fortified fictional archipelago.
- **Premise:** Build, push across three islands and destroy the hub core. Four other commanders hold their own fronts and are heard only on the radio (rule 5):
  - Lin keeps the picture alive; if the relay node falls, the fog returns.
  - Turki holds the platform, and the jamming stays off.
  - Kemal's ships close the northern lane, so enemy naval waves stop at a set minute.
  - Nabil reports the mainland towns clear. The final strike unlocks only then.
- **Objectives:** **build**, **protect** the relay node, **destroy** the hub core; radio events gate the final objective (Phase 2).
- **Ending:** one line from each commander, then Lantern: "Every light on." The last image is a night map of the coast as the lights of convoys, ferries and ships reconnect.

## Look and sound

- **Colour language.** Amber and gold for lifelines and people (convoy routes, Lantern's lamp, the title cards); red for immediate threats; cold white strobes on matte black glass for the Directorate.
- **Recurring images.** The holographic briefing table built from the mission's own map; the commander's portrait; Directorate masts; a final shot of the line that matters (port, road, open sea, ferry, lights).
- **Voices.** The six built films keep their single narrator. From Act III, Lantern opens each briefing, the commander gives the orders, and both reach the mission itself as radio calls with portraits (Phase 2). The Broker's voice is calm and slightly processed.
- **Music.** Act I: oud, frame drum and low strings. Act II: synth pulses and taiko. Act III joins both under one amber brass theme, the Lines of Hope theme, which the finale states in full.

## Continuity patches for the built chapters

These are text only. They plant the clues in the existing debriefs; tonight's films stay as they are. Apply them to the `victory` text in `resources/campaign-story.json` once the bible is approved.

| Chapter | Add to the victory text |
| --- | --- |
| Jizan Corridor | "One thing does not fit. Radar Node Seven was never destroyed. For six hours it showed an empty, looping sea." |
| Hodeidah Lifeline | "The sweep moved before anything was airborne. Someone was reading the same picture as everyone else, and reading it first." |
| Bab al-Mandab Passage | "Lantern's report is short: every gap in the coastal picture matches one maintenance contract. The contractor calls itself the Obsidian Directorate." |
| Straits Shield | "The uplinks carried no flag, only a serial prefix the harbour relay knew: OD." |
| Haitan Network | "The restored links show where the region's traffic was going: to one island no chart names." |
| Relay Under Siege | No change (rule 6). |

## What Act III needs from the game (Phase 2)

- Timed events, and scripted radio calls with a portrait and captions.
- No-base starts with a fixed squad and a "squad lost" failure.
- Detection zones: a unit seen by a sensor mast raises an alarm and triggers waves.
- Event-gated objectives and reinforcements, plus map-wide reveal events (the "lights on" moments).
- Lazy-loaded mission maps, so the campaign screen never holds more than the chapter being played.

## Production

1. Approve this bible, then apply the continuity patches.
2. Build the Phase 2 mission features in the browser host and the desktop mod together.
3. For each Act III chapter: map, mission JSON, a playtest of every success and failure path, then the film. The film pipeline is unchanged: shot list in `RTSAI-WebGame/tools/briefings/`, stills with `art.mjs`, clips through the forge commission, cut in Montage, published with `from-montage.mjs`.
4. Returning commanders: extend `art.mjs` with a portrait reference (today it supports only `"reference": "map"`) so a later portrait is an edit of the first and the face stays the same.
5. A short epilogue film after III-5: the five returning commanders and Lantern over the reconnected night map.

## Open decisions

- **Iran and Israel have no chapters.** Either keep them skirmish-only, or give each one fictional-theatre chapter against the Directorate under rules 1 and 5.
- **Lantern's voice:** pick one of the local Chatterbox voices.
- **Re-cutting the built films:** whether the six Act I and II films later get Lantern's opening line, or stay with the single narrator.
