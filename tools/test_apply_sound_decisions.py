#!/usr/bin/env python3
"""Tests for tools/apply-sound-decisions.py on a fixture mod (needs ffmpeg). Usage: python tools/test_apply_sound_decisions.py"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import math
import shutil
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

spec = importlib.util.spec_from_file_location("apply_sound_decisions", Path(__file__).with_name("apply-sound-decisions.py"))
asd = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = asd  # dataclasses resolve annotations through sys.modules
spec.loader.exec_module(asd)

MODERN = asd.MODERN


def tone(path: Path, seconds=0.6, freq=440.0, rate=22050, amp=0.3, channels=1):
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = b"".join(struct.pack("<" + "h" * channels, *([int(amp * 32767 * math.sin(2 * math.pi * freq * i / rate))] * channels)) for i in range(int(seconds * rate)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)
    return path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(root: Path) -> dict:
    """A tiny mod: two modern tanks sharing a coax gun, an original GI sharing a rifle with a modern rifleman, a death
    effect with two layered warheads, an aircraft whose husk explodes, voice sets, a notification table and the
    seven announcer folders. Plus a bake-off with one RA2 reference and a CC0 source."""
    mod = root / "mod" / "mods" / "rtsai"
    put = lambda rel, text: (mod / rel).parent.mkdir(parents=True, exist_ok=True) or (mod / rel).write_text(text, encoding="utf-8", newline="\n")
    put("mod.yaml", "Rules:\n\tra2|rules/defaults.yaml\n\tra2|modern-factions/china.yaml\n\nWeapons:\n\tra2|weapons/explosions.yaml\n\tra2|modern-factions/china-weapons.yaml\n\n"
        "Voices:\n\tra2|audio/voices.yaml\n\tra2|modern-factions/china-voices.yaml\n\nNotifications:\n\tra2|audio/notifications.yaml\n")
    put("rules/defaults.yaml", "^Vehicle:\n\tHealth:\n\t\tHP: 300\n\tFireWarheadsOnDeath:\n\t\tWeapon: UnitExplode\n\nE1:\n\tArmament:\n\t\tWeapon: M60\n\tVoiced:\n\t\tVoiceSet: GiVoice\n\n"
        "^Plane:\n\tHealth:\n\t\tHP: 100\n\nPLANEHUSK:\n\tFallsToEarth:\n\t\tExplosion: PlaneExplode\n")
    put("modern-factions/china.yaml", "r2tank:\n\tInherits: ^Vehicle\n\tArmament@gun:\n\t\tWeapon: TankGun\n\tArmament@coax:\n\t\tWeapon: Coax\n\tVoiced:\n\t\tVoiceSet: TankVoice\n"
        "\tGrantConditionOnDeploy:\n\t\tDeploySounds: ra2|modern-factions/audio/deploy.wav\n\n"
        "r2tank2:\n\tInherits: ^Vehicle\n\tArmament@coax:\n\t\tWeapon: Coax\n\tFireWarheadsOnDeath:\n\t\tWeapon: FXDeathLarge\n\n"
        "r2rifle:\n\tArmament:\n\t\tWeapon: M60\n\tVoiced:\n\t\tVoiceSet: RifleVoice\n\tDeathSounds:\n\n"
        "r2jet:\n\tInherits: ^Plane\n\tSpawnActorOnDeath:\n\t\tActor: r2jethusk\n\nr2jethusk:\n\tFallsToEarth:\n\t\tExplosion: PlaneExplode\n")
    put("weapons/explosions.yaml", "UnitExplode:\n\tWarhead@1Dam: SpreadDamage\n\t\tDamage: 50\n\tWarhead@2Eff: CreateEffect\n\t\tImpactSounds: ra2|audio/sfx/boom.wav\n"
        "\tWarhead@3Water: CreateEffect\n\t\tImpactSounds: ssplash.wav\n\t\tValidTargets: Water\n\n"
        "FXDeathLarge:\n\tInherits: UnitExplode\n\tWarhead@4Eff: CreateEffect\n\t\tImpactSounds: ra2|audio/sfx/boom.wav\n\t\tDelay: 5\n\n"
        "PlaneExplode:\n\tWarhead@1Eff: CreateEffect\n\t\tImpactSounds: gexp14a.wav\n\nM60:\n\tReloadDelay: 20\n\tReport: igiat1a.wav, igiat1b.wav\n\tWarhead@1Dam: SpreadDamage\n\t\tDamage: 15\n")
    put("modern-factions/china-weapons.yaml", "TankGun:\n\tReport: vgriatta.wav\n\tWarhead@1Dam: SpreadDamage\n\t\tDamage: 90\n\t\tImpactSounds: gexp14a.wav\n\n"
        "Coax:\n\tReloadDelay: 30\n\tReport: igiat1a.wav, igiat1b.wav, igiat1c.wav\n\tWarhead@1Dam: SpreadDamage\n\t\tDamage: 12\n")
    put("audio/voices.yaml", "^Deaths:\n\tVoices:\n\t\tDie: igidia, igidib\n\nGiVoice:\n\tInherits: ^Deaths\n\tDefaultVariant: .wav\n\tVoices:\n\t\tSelect: igisea\n")
    put("modern-factions/china-voices.yaml", "TankVoice:\n\tDefaultVariant: .wav\n\tVoices:\n\t\tSelect: ra2|modern-factions/audio/tank-select\n\n"
        "RifleVoice:\n\tInherits: ^Deaths\n\tDefaultVariant: .wav\n\tVoices:\n\t\tSelect: ra2|modern-factions/audio/rifle-select\n")
    put("audio/notifications.yaml", "Speech:\n\tDefaultVariant: .wav\n\tNotifications:\n\t\tNuclearMissileLaunched: 002\n\t\tNuclearMissileReady: 002\n\t\tAtomBombReady: 003\n")
    audio = mod / "modern-factions" / "audio"
    for f in MODERN:
        for clip in ("002", "003", "009"):
            tone(audio / "eva" / f / f"{clip}.wav", 0.8, 300)
    tone(audio / "tank-select.wav", 0.9, 220)
    tone(audio / "rifle-select.wav", 0.9, 240)
    tone(audio / "deploy.wav", 0.3, 800)
    prov = {"schema": "rtsai-audio-provenance/1", "updated": "2026-10-01",
            "voice_lines": [{"filename": "tank-select.wav", "text": "Tank ready.", "language": "en-US", "engine": "Kokoro-82M", "license": "Apache-2.0", "role": "crew"},
                            {"filename": "rifle-select.wav", "text": "Rifle ready.", "language": "en-US", "engine": "Kokoro-82M", "license": "Apache-2.0"}],
            "announcers": [{"filename": f"eva/{f}/{c}.wav", "faction": f, "clip": c, "text": t, "engine": "Kokoro-82M", "license": "Apache-2.0"}
                           for f in MODERN for c, t in (("002", "Nuclear missile launched."), ("003", "Nuclear missile ready."), ("009", "Chronosphere ready."))],
            "sound_effects": [{"filename": "deploy.wav", "source": "procedural"}]}
    (audio / "PROVENANCE.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
    (root / "mod" / "docs").mkdir(parents=True)
    (root / "mod" / "docs" / "audio-provenance.md").write_text("# Audio provenance\n", encoding="utf-8")
    bake = root / "bakeoff"
    ref = tone(bake / "sfx" / "rifle_burst" / "ra2-igiat1a.wav", 0.5, 900)
    rifle = tone(bake / "sfx" / "rifle_burst" / "cc0-layered.wav", 0.7, 1200, rate=48000, channels=2, amp=0.6)
    boom = tone(bake / "sfx" / "large_explosion" / "cc0-layered.wav", 2.5, 60, rate=48000, amp=0.8)
    (bake / "manifest.json").write_text(json.dumps({"candidates": [{"id": "A.rifle_burst.ra2-igiat1a", "source": "ra2-reference", "reference": True, "files": {"wav_master": "sfx/rifle_burst/ra2-igiat1a.wav"}}]}), encoding="utf-8")
    art = root / "art"
    take = tone(art / "sounds" / "china" / "eva_china_009" / "t1" / "clip.wav", 1.2, 330)
    (take.parent / "meta.json").write_text(json.dumps({"engine": "Kokoro-82M v1.0", "engine_id": "kokoro", "license": "Apache-2.0", "text": "Strategic uplink ready.", "language": "en-US", "voice": {"speaker": "china-eva"}, "slot": "eva:china:009"}), encoding="utf-8")
    cc0 = lambda p, title: {"source": "bakeoff", "id": f"bakeoff:{title}", "title": title, "path": str(p), "sha256": sha(p), "licence": "CC0 1.0"}
    entry = lambda chosen, kind="fire": {"label": "x", "faction": "china", "actor": None, "kind": kind, "current": [], "chosen": chosen, "rejected": [], "at": "2026-10-14T00:00:00Z", "notes": [], "log": []}
    slots = {
        "fire:r2tank:Coax": entry(cc0(rifle, "rifle")),
        "fire:r2tank2:Coax": entry(cc0(rifle, "rifle")),            # every Coax user agrees: overridden in place
        "fire:r2rifle:M60": entry(cc0(rifle, "rifle")),             # M60 is also the original GI's: a variant
        "impact:r2tank:TankGun": entry(cc0(boom, "boom"), "impact"),
        "death:r2tank2": entry({**cc0(boom, "boom"), "trim": {"start": 0.0, "end": 1.0}}, "death"),
        "death:r2jet": entry(cc0(boom, "boom"), "death"),
        "trait:r2tank:GrantConditionOnDeploy:DeploySounds": entry(cc0(rifle, "rifle"), "deploy"),
        "clip:mods/rtsai/modern-factions/audio/tank-select.wav": entry({**cc0(rifle, "rifle"), "text": "Armor up."}, "voice"),
        "clip:igidia.wav": entry(cc0(boom, "boom"), "voice"),
        "eva:china:009": entry({"source": "regen", "id": "regen:sounds/china/eva_china_009/t1/clip.wav", "title": "Strategic uplink ready.", "path": "sounds/china/eva_china_009/t1/clip.wav", "sha256": sha(take), "licence": "Apache-2.0", "text": "Strategic uplink ready."}, "announcer"),
        "notify:NuclearMissileReady": entry({"source": "eva-clip", "id": "eva-clip:003", "title": "003", "path": "003", "sha256": None, "licence": "Apache-2.0"}, "notify"),
        "fire:r2tank:TankGun": entry({**cc0(ref, "ref"), "licence": "CC0 1.0"}),   # bytes of an RA2 reference
        "impact:r2tank:Coax": entry({**cc0(rifle, "rifle"), "licence": "EA (Command & Conquer: Red Alert 2). LISTENING REFERENCE ONLY"}, "impact"),
        "death:r2tank": entry({**cc0(boom, "boom"), "sha256": "0" * 64}, "death"),   # changed since it was chosen
        "fire:r2tank:Nope": entry("current"),
    }
    decisions = art / "sound-review.json"
    decisions.write_text(json.dumps({"version": 1, "slots": slots, "deathSizes": {}}, indent=1), encoding="utf-8")
    return {"mod": root / "mod", "decisions": decisions, "bake": bake, "art": art}


def run(args: list[str]) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = asd.main(args)
    return code, out.getvalue()


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is required")
class ApplySoundDecisions(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sound-desk-test-"))
        self.f = fixture(self.tmp)
        self.args = ["--decisions", str(self.f["decisions"]), "--mod", str(self.f["mod"]), "--bakeoff", str(self.f["bake"])]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dry_run_prints_the_plan_and_writes_nothing(self):
        before = {p: p.read_bytes() for p in self.f["mod"].rglob("*") if p.is_file()}
        code, out = run(self.args + ["--dry-run"])
        self.assertEqual(code, 1, "refused slots make the run fail")
        after = {p: p.read_bytes() for p in self.f["mod"].rglob("*") if p.is_file()}
        self.assertEqual(before, after, "a dry run writes nothing")
        self.assertIn("11 slots to apply, 3 refused", out)
        self.assertIn("REFUSED fire:r2tank:TankGun: the bytes of an RA2 listening reference", out)
        self.assertIn("REFUSED impact:r2tank:Coax: licence not redistributable", out)
        self.assertIn("REFUSED death:r2tank: cc0-layered.wav changed since it was chosen", out)
        self.assertIn("+Coax:\n+\tReport: ra2|modern-factions/audio/sd/fire-coax-", out, "every Coax user agrees: in place")
        self.assertRegex(out, r"\+M60__sd_[0-9a-f]{6}:\n\+\tInherits: M60\n\+\tReport: ra2\|modern-factions/audio/sd/fire-m60-", "the GI shares M60: a variant")
        self.assertRegex(out, r"\+r2rifle:\n\+\tArmament:\n\+\t\tWeapon: M60__sd_", "the rifleman points at it")
        self.assertRegex(out, r"\+FXDeathLarge__sd_[0-9a-f]{6}:\n\+\tInherits: FXDeathLarge\n\+\tWarhead@2Eff: CreateEffect\n\+\t\tImpactSounds: ra2\|modern-factions/audio/sd/death-r2tank2-[0-9a-f]+\.wav\n\+\tWarhead@4Eff: CreateEffect\n\+\t\t-ImpactSounds:",
                         "one sound per death: the layered warhead goes quiet, the water splash is untouched")
        self.assertRegex(out, r"\+r2jethusk:\n\+\tFallsToEarth:\n\+\t\tExplosion: PlaneExplode__sd_", "an aircraft's husk explodes with the new sound")
        self.assertIn("+\tGrantConditionOnDeploy:\n+\t\tDeploySounds: ra2|modern-factions/audio/sd/", out)
        self.assertRegex(out, r"\+RifleVoice:\n\+\tVoices:\n\+\t\tDie: ra2\|modern-factions/audio/sd/clip-igidia-[0-9a-f]+, igidib", "a stand-in death cry is replaced in the modern set only")
        self.assertNotIn("+GiVoice", out, "the original GI keeps its voice")
        self.assertIn("-\t\tNuclearMissileReady: 002\n+\t\tNuclearMissileReady: 003", out)
        self.assertIn("REPLACE modern-factions/audio/eva/china/009.wav", out)
        self.assertIn("verbatim (already mastered by the faction chain)", out)
        self.assertIn("REPLACE modern-factions/audio/tank-select.wav", out)
        self.assertIn("Balance check: every armament and death weapon resolves identically apart from its sounds.", out)

    def test_apply_writes_sounds_rules_and_provenance_then_cleans_up(self):
        code, out = run(self.args + ["--skip-checks"])
        self.assertEqual(code, 1, out)  # the three refused slots
        mod = self.f["mod"] / "mods" / "rtsai"
        audio = mod / "modern-factions" / "audio"
        sd = sorted(p.name for p in (audio / "sd").glob("*.wav"))
        self.assertTrue(any(n.startswith("fire-coax-") for n in sd) and any(n.startswith("death-r2tank2-") for n in sd), sd)
        with wave.open(str(audio / "sd" / next(n for n in sd if n.startswith("fire-coax-")))) as w:
            self.assertEqual((w.getnchannels(), w.getframerate()), (1, 44100), "mono 44.1 kHz")
        manifest = (mod / "mod.yaml").read_text(encoding="utf-8")
        self.assertIn("\tra2|modern-factions/china.yaml\n\tra2|modern-factions/sound-desk-rules.yaml\n\nWeapons:", manifest)
        self.assertIn("ra2|modern-factions/sound-desk-voices.yaml", manifest)
        prov = json.loads((audio / "PROVENANCE.json").read_text(encoding="utf-8"))
        effects = {r["filename"]: r for r in prov["sound_effects"]}
        coax = next(r for k, r in effects.items() if k.startswith("sd/fire-coax-"))
        self.assertEqual(coax["license"], "CC0 1.0")
        self.assertEqual(coax["sound_desk"]["slots"], ["fire:r2tank2:Coax", "fire:r2tank:Coax"])
        self.assertEqual(coax["sha256"], sha(audio / coax["filename"]))
        eva = next(r for r in prov["announcers"] if r["filename"] == "eva/china/009.wav")
        self.assertEqual((eva["text"], eva["replaces"]["text"]), ("Strategic uplink ready.", "Chronosphere ready."))
        self.assertEqual(sha(audio / "eva" / "china" / "009.wav"), sha(self.f["art"] / "sounds/china/eva_china_009/t1/clip.wav"), "the take is copied as mastered")
        line = next(r for r in prov["voice_lines"] if r["filename"] == "tank-select.wav")
        self.assertEqual((line["text"], line["role"]), ("Armor up.", "crew"))
        death = next(r for k, r in effects.items() if k.startswith("sd/death-r2tank2-"))
        self.assertEqual(death["sound_desk"]["trim"], {"start": 0.0, "end": 1.0})
        self.assertIn("NuclearMissileReady: 003", (mod / "audio" / "notifications.yaml").read_text(encoding="utf-8"))
        self.assertIn("<!-- sound-desk:", (self.f["mod"] / "docs" / "audio-provenance.md").read_text(encoding="utf-8"))
        # Every decision taken back: the desk's files go, the in-place replacements stay (they are the mod now).
        self.f["decisions"].write_text(json.dumps({"version": 1, "slots": {}, "deathSizes": {}}), encoding="utf-8")
        code, out = run(self.args + ["--skip-checks"])
        self.assertEqual(code, 0, out)
        self.assertEqual(list((audio / "sd").glob("*.wav")), [])
        self.assertFalse((mod / "modern-factions" / "sound-desk-weapons.yaml").exists())
        self.assertNotIn("sound-desk", (mod / "mod.yaml").read_text(encoding="utf-8"))
        self.assertFalse(any(r["filename"].startswith("sd/") for r in json.loads((audio / "PROVENANCE.json").read_text(encoding="utf-8"))["sound_effects"]))

    def test_balance_check_catches_anything_but_sounds(self):
        before = asd.Mod(self.f["mod"])
        sneaky = before.read("modern-factions/china-weapons.yaml").replace("Damage: 12", "Damage: 99").replace("igiat1c.wav", "x.wav")
        after = asd.Mod(self.f["mod"], overlay={"modern-factions/china-weapons.yaml": sneaky})
        problems = asd.balance_check(before, after)
        self.assertTrue(any("Coax" in p for p in problems), problems)
        only_sound = before.read("modern-factions/china-weapons.yaml").replace("igiat1c.wav", "x.wav")
        self.assertEqual(asd.balance_check(before, asd.Mod(self.f["mod"], overlay={"modern-factions/china-weapons.yaml": only_sound})), [])

    def test_licences(self):
        v = asd.licence_verdict
        self.assertEqual([v("CC0 1.0"), v("MIT"), v("Apache-2.0 (Kokoro-82M)"), v("GPL-3.0 (project code)")], ["ok"] * 4)
        self.assertEqual([v("Stability AI Community License"), v("openai output: ...")], ["conditional"] * 2)
        self.assertEqual([v("EA (Command & Conquer: Red Alert 2)"), v("CC BY-NC 4.0"), v(""), v("CC0", reference=True), v("MIT base model + CC0 data (pilot checkpoint, not for shipping)")], ["refused"] * 5)

    def test_refuses_to_write_on_main(self):
        repo = self.f["mod"]
        import subprocess
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
        code, out = run(self.args)
        self.assertEqual(code, 2)
        self.assertIn("Refusing to write on main", out)


if __name__ == "__main__":
    unittest.main()
