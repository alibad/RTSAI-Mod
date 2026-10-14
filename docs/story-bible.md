# Lines of Hope: story bible

Draft 2, 14 October 2026; Act IV, the epilogue and the Part II hook added the same night. The playable text comes from `resources/campaign-story.json`; this bible decides what chapters, briefing films, radio calls and debriefs may say. When the two disagree, update the JSON to match the bible (`RTSAI-WebGame/tools/build-campaign-story.py --text-only`), never the other way round.

Draft 2 replaces draft 1's anthology with an alternate-history sequel to the original Red Alert (1996), at the owner's request ("invent a story as creative or even more creative … feel free to use the Red Alert 1 classic stories").

## In one breath

In 1953, at the end of the Red Alert war, Einstein goes to switch off the Chronosphere for good. Arkady Orlov gets there first. He was Stalin's quiet adviser, the man missing from every photograph of the court. He steps through the machine, and the Allied commando Tanya, with a fist in his coat, is pulled through with him. The Chronosphere falls silent, but its echo travels forward seventy-three years and leaks into every radar and radio on a crisis coast in 2026. Pictures loop and clocks read 1953; sweeps move before anything flies. Six commanders on different shores keep their roads, sea lanes and signals open while a civilian coordinator called Lantern follows the echo to its source. That source is Orlov. He now runs the Obsidian Directorate, a sensor broker that sells every army its picture of the world and edits that picture when it pays. He means to edit the whole region into a war.

## The idea underneath

- **Red Alert began when one man was removed from history.** Einstein believed he could fix the century by erasing a single person, and it made everything worse. Orlov's whole craft is erasing people: from photographs in 1953, from radar pictures in 2026. The heroes never win by erasing anyone. They win by keeping lines open so that people get home.
- **Lines of Hope means three kinds of line:** the lifelines (roads, ports, sea lanes), the signal lines (radar, radio, networks) and the timelines. Each act opens a different one. Act IV comes back to the first two after the third has closed (water on one coast, the picture on another), and the epilogue opens the timeline again.
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
| Act IV · Aftershocks | Lifelines and signals, once more | Sweet Water (Iran), Ghosts on the Glass (Israel) | Both playable (14 Oct, branch `campaign/act4`); portraits and films to make |
| Epilogue · 1946 | Timeline | A film after Act IV | Shot list written (`tools/briefings/epilogue.json`); film to make |
| Part II · The Retoucher | Timeline | The sequel, teased | A locked "Coming" card after the epilogue |

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
| Colonel Arash Tavakoli (Iran) | An army engineer who has laid water lines across three deserts; he counts every truck twice and never raises his voice | IV-1 | Fifties, close-cropped greying beard, sand-coloured field uniform with rolled sleeves, a dusty scarf, reading glasses in his breast pocket, beside a water tanker on a salt flat at dusk |
| Lieutenant Colonel Maya Ronen (Israel) | Keeps a harbour city's air and sea picture; trusts nothing she has not seen twice, and says so | IV-2 | Forties, dark hair in a low knot, olive field uniform, headset around her neck, binoculars on a strap, a harbour command room at night lit by green screens |
| **Lantern**, Dr. Amina Farah | Civilian deconfliction coordinator from the far shore of the strait; a physicist by training. She shares traffic pictures so aid and shipping can move, notices that every side's blind spots match, and follows the echo to 1953. The story's conscience. | Every act, on the radio; the epilogue | Forties, plain shirt and cardigan, glasses pushed up, small operations room lit by one amber desk lamp |
| **Tanya** | Allied commando from 1953, displaced to 2026. Fearless, dry and fast; rarely surprised by danger, but often surprised by the future ("They fight wars from a screen now?"). The only person alive who knows Orlov's face. After the finale she works from Lantern's desk. | Prologue, III-1 to III-5; IV on the radio | Late twenties, dark hair tied back, 1950s commando fatigues and webbing, rolled sleeves, pistol holster, sea-soaked when found |
| **Albert Einstein** | The scientist who started it, trying to end it; speaks from his 1953 film reel | Prologue, III-3, III-5; the 1946 photograph in the epilogue | Elderly physicist with white hair and moustache, in painted archival style, lit by Chronosphere blue |
| **Arkady Orlov**, the Broker | See the antagonist | Prologue, voice from III-2, IV on the radio; the background of the 1946 photograph in the epilogue | Never shown: a figure cut out of a photograph, a silhouette, a reflection, a face lost in shadow |

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

## Act IV · Aftershocks (new)

Days after every light came back on. The echo is folded shut, but Orlov stepped into the captured Chronosphere and is gone, and the Directorate's last cells are racing for the coil caches the hub's manifest lists: crates of hand-wound Chronosphere coils from 1953, any one of which could open the echo again. Two operations, on separate coasts and separate days, against two separate cells. They never meet (rule 3): Lantern's desk, where Tanya now works beside her, connects them only on the radio. Each chapter borrows a preserved original Red Alert mission's pattern, as Act III does, and replaces everything else. Neither needs anything new from the game: they run on Act III's mission features (sensors, events, conditions, deadlines) and their own map rules.

| Chapter | Commander | Mission | What the player learns (debrief and radio) |
| --- | --- | --- | --- |
| 1 · Sweet Water | Arash | Clear the salt road, bring the water trucks in, retake the plant, take the coil cache whole | The cache under the plant is a crate of coils dated 1953, wound like the one Kemal found; its manifest lists one more cache, on another coast |
| 2 · Ghosts on the Glass | Maya | Verify every contact before anything fires, destroy the relays that paint the phantoms, hold the harbour | The last relay holds the last cache on the manifest. Every cache is accounted for; Orlov is not |

### IV-1 · Sweet Water (convoy and recapture)
- **Commander:** Colonel Arash Tavakoli (Iran). **Setting:** a fictional salt-desert trade road and a port town on a fictional coast (the terrain of Jizan Corridor, repainted with a salt flat, the road, a coast and a dock). **Source missions:** Allies 02 "Five to One" (a road blocked in several places, cleared before the convoy is due) and Soviet 07 "Core of the Matter" (retake a plant that someone else has seized).
- **Mission:** a cell has seized the town's desalination and power plant, where a coil cache is hidden, and cut the water. From a road camp with a small column: destroy the guns of three roadblocks on the salt road before the army water trucks are due (10:00 on normal), bring at least two of the three trucks to the town cistern, capture the plant's pumps and its power station with engineers (the power station feeds the cell's tesla coils: take it and they go dark), then, once the vault's lock is cut, capture the coil cache with an engineer while the cell's recovery parties land at the dock. Raiders from the northern hills strike the road camp until the plant is retaken. Nothing on the plant can be destroyed: the town needs it, and the coils hold a charge.
- **Beat:** the Broker offers to turn the taps back on himself, for the plant's basement. In the vault, Tanya finds the crate: coils dated 1953, wound by hand like the one Kemal's engineers pulled from an uplink (II-1). Lantern reads the manifest: one more cache, on another coast.
- **Civilians:** the town's people are never on screen and never in the line of fire; the trucks are army water tankers.

### IV-2 · Ghosts on the Glass (verification)
- **Commander:** Lieutenant Colonel Maya Ronen (Israel). **Setting:** a fictional harbour city on a fictional bay; the cell's relay towers stand on the cape across it (the frame of the Bab al-Mandab map, repainted as a bay with a land bridge at its head). **Source missions:** Soviet 03 "Covert Cleanup" (find the one real threat hidden among people) and Negotiations (a town full of civilians, where nothing may fire carelessly).
- **Mission:** the city's picture shows nine contacts closing on the harbour. Six are phantoms the cell paints from its relays, to provoke a strike on nothing and sell the picture of a city that fired first. Every contact is a ring on the map: a unit of the player's coming within it verifies it, and a phantom then fades (its ring turns pale) while a real contact's ring turns red. Destroying a phantom before it is verified (a strike on nothing) fails the mission; a phantom takes a tenth of the damage while unverified, so a unit that opens fire on one can still be called off. Forward observers go first, and approaching units go on Return fire. Then the column takes the road round the head of the bay, destroys the three relay towers before first light (16:00 on normal; every phantom vanishes when they fall), and the harbour holds for three minutes against the strike group the lie was covering. The families wait in three public shelters; losing one fails the mission. Bonus: verify all nine contacts.
- **Beat:** Lantern on the first phantom: "Nothing there. Empty water." The Broker offers to say which contacts are real, for the city's first shot. The last relay holds the last coil cache on the manifest. Tanya: every cache is accounted for, so why can she still feel him in the room?
- **Civilians:** the families are never targeted: the shelters belong to a side nobody fires on, and Orion's landings go for the harbour command. Two phantoms are painted beside shelters, which is why striking an unverified contact is the one thing the city must never do.

## Epilogue · 1946 (film)

After Act IV, like the prologue before Act I: one film, no mission. The 2026 room is painted key art in Lantern's amber. The photograph is the story's only image of 1946 and belongs to the archival layer with the 1953 material (rule 5): Einstein is in it only as the prologue paints him, never photoreal, and the man in its background keeps his face in shadow (rule 8). The man Einstein removed is not in it. The shot list is `RTSAI-WebGame/tools/briefings/epilogue.json`. Six shots:

1. Lantern's small operations room at night, the crisis over: quiet screens, one amber desk lamp, a cork wall of pinned prints, maps and red string, a cold mug of tea. "When every light was back on, Lantern went back to her wall."
2. Her hands pin an old black-and-white print to the cork: a huge machine of brass rings in a laboratory hall, an elderly white-haired scientist beside it. "One print was missing from it: the first test of the Chronosphere, nineteen forty-six."
3. The print itself, filling the frame: the hall, the machine, the scientist at the control desk, technicians in a row. "She knew every face in it. She had counted them a hundred times."
4. A magnifying loupe over the print: far behind the machine, a tall man in a long dark coat, his face lost in shadow, one gloved hand on a brass rail. "Tonight there is one more. A man who was not in the picture yesterday."
5. Lantern at her desk, frozen, the print in her hand, the screens' glow behind her. "For seventy-three years he was missing from every photograph."
6. The old radio on her desk, its needle swinging again by itself; the pinned print out of focus behind it; a pale blue flicker like an old film frame. "Tonight he is in the first one." Title card: *Lines of Hope · Part II · The Retoucher*.

The last line is the hook: Orlov, who spent his life cutting himself out of pictures, has put himself into the one that made the century.

## Part II · The Retoucher (sequel hook)

**Premise.** Orlov spent his life taking himself out of pictures; now he is putting himself back in. The coil caches were never his way home: they were the map of every place the echo touched, and he has followed it back to the first jump, the 1946 test that made the Red Alert century. If he can stand in that photograph, he can stand at the switch, and whoever stands at the switch decides which world the next seventy years become. On the coasts of 2026 his last loyalists fight with a weapon nobody has faced, a battlefield that edits itself behind them: a bridge that was never built, a port that moves, a radar that remembers a different morning. Lantern can read the echo, Tanya knows his face, and the commanders who kept the lines open must hold one line more: the timeline itself.

**Rules that hold.** The man Einstein removed in 1946 is never named or shown, in Part II as in Part I (rule 5); the first test is seen only as the archival photograph and its echo. Orlov's face is never shown (rule 8). Real modern nations are never the villain, and two never share a battlefield (rules 2 and 3): the edited battlefields are the Directorate's weapon, not any nation's.

**On the campaign screen.** The story data's `sequel` entry: a locked "Coming" card after the epilogue, with its title and this premise's first sentence.

## Radio calls

Every mission has calls in `campaign-story.json` under `radio`: a speaker from the cast, one line, and a trigger (`start`, a game-time second, an objective index, `victory`, `defeat`). House style:
- one or two short sentences, spoken by the person who would say them;
- the commander gives orders, Lantern brings what the coordination desk sees, and Tanya speaks only from III-1 (in Act IV, from Lantern's desk);
- the Broker always makes an offer and never threatens;
- calls carry the clue thread (1953, the loop, the contract, the coil, the island; in Act IV the caches and their manifest) so a player who skips films still follows the story.

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

- Iran and Israel each have one fictional-theatre chapter against the Directorate (Act IV, under rules 2 and 3): decided 14 October. Their commanders' portraits (`cast/arash.webp`, `cast/maya.webp`), their radio voices and the two chapter films are still to make.
- Voices for Lantern, Tanya, the Broker and Einstein's recording (local Chatterbox voices; never a clone of a real person's voice).
- Part II: whether *The Retoucher* is a second campaign on the same screen or its own; what the edited battlefields need from the game (terrain and actors that change mid-match).
- Whether the six built films are later re-cut with the prologue's look and Lantern's opening line.
