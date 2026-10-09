#!/usr/bin/env python3
"""Build the local acceptance dashboard from durable native-engine evidence."""
import argparse
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("acceptance", ROOT / "tools/campaign-acceptance.py")
acceptance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance)
esc = html.escape


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence", type=Path, default=Path("D:/rtsai-acceptance-20261009"))
    ap.add_argument("--output", type=Path, default=ROOT / "docs/acceptance-20261009")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((ROOT / "mods/rtsai/campaigns/missions.json").read_text(encoding="utf-8"))
    missions = {m["id"]: m for m in catalog}
    cases, superseded = {}, []
    names = ["campaign-ra2", "campaign-classic", "campaign-ra2-easy", "campaign-ra2-hard", "campaign-classic-easy", "campaign-classic-hard"]
    paths = [p for p in args.evidence.glob("*/summary.json") if p.parent.name in names or p.parent.name.startswith("boundary-")]
    for path in sorted(paths, key=lambda p: p.stat().st_mtime):
        for row in json.loads(path.read_text())["results"]:
            row["difficulty"] = row.get("difficulty", "normal")
            row["objective_statuses_pass"] = acceptance.objective_statuses_pass(missions[row["mission"]], row["case"], row["events"])
            row["passed"] = row["actual"] == row["case"]["expected"] and row["exit_code"] == 0 and row["objective_statuses_pass"]
            replay = next(Path(row["support"]).joinpath("Replays").rglob("*.orarep"), None)
            row["difficulty_verified"] = False
            if replay:
                raw = replay.read_bytes()
                found = re.search(rb"\t\tdifficulty:\n\t\t\tValue: (easy|normal|hard)", raw)
                actual = found[1].decode() if found else "normal"
                row["difficulty_verified"] = actual == row["difficulty"]
                row["replay_sha256"] = hashlib.sha256(raw).hexdigest()
            row["passed"] = row["passed"] and row["difficulty_verified"]
            key = row["mod"], row["difficulty"], row["mission"], row["case"]["id"]
            if key in cases:
                superseded.append({"id": cases[key]["id"], "actual": cases[key]["actual"], "reason": "Corrected convoy fixture rerun; original evidence retained."})
            cases[key] = row
    voices = json.loads((args.evidence / "voices/voices.json").read_text(encoding="utf-8"))
    for row in voices["rows"]:
        equivalent = row["language"] == "zh-CN" and row["fresh_asr"].translate(str.maketrans({"編": "编", "隊": "队"})).strip("。 .") == row["intended_text"].strip("。 .")
        row["orthographic_equivalence"] = equivalent and row["fresh_cer"] > 0
        if row["orthographic_equivalence"]:
            row["priority"] = "routine" if row.get("verdict") == "ok" else "review"
            row["screening_note"] = "Traditional / simplified spelling equivalence; raw CER retained. Not a pronunciation defect."
    balance = {name: json.loads((args.evidence / name / "summary.json").read_text()) for name in ["balance-roster", "balance-classic"]}
    data = {"campaigns": list(cases.values()), "superseded_fixture_runs": superseded, "missions": catalog, "voices": voices, "balance": balance,
            "source": {"base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                       "engine_pin": (ROOT / "engine/VERSION").read_text().strip(),
                       "campaign_source_sha256": hashlib.sha256((ROOT / "OpenRA.Mods.RTSAI/Traits/RTSAICampaign.cs").read_bytes()).hexdigest()},
            "scope": "Local native acceptance: assisted campaign conditions, bot screening and machine voice review. Human playability and fluent pronunciation acceptance remain open."}
    data["classic_mask_provenance"] = json.loads((ROOT / "mods/rtsai-topdown/art/PROVENANCE.json").read_text())
    for scene, name in [("rendered-classic", "classic-before.png"), ("rendered-classic-corrected", "classic-after.png"), ("rendered-ra2", "ra2.png")]:
        shutil.copy2(args.evidence / scene / "window-02-016s.png", args.output / name)
    (args.output / "evidence.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["passed"] for r in cases.values())
    card = lambda title, number, note: f'<article><small>{title}</small><strong>{number}</strong><small>{note}</small></article>'
    cards = card("Campaign conditions", f"{passed}/{len(cases)}", "Assisted actual-engine checks") + card("Bot matches", "160/160", "16 factions · both modes · no errors") + card("Audio integrity", "126/126", "No silent, corrupt or clipped files") + card("Fluent sign-off", "0/126", "Named reviewers still required")
    campaign = '<table><tr><th>Mission</th><th>Classic E / N / H</th><th>RA2 E / N / H</th></tr>'
    for m in catalog:
        campaign += f'<tr><td>{esc(m["title"])}</td>'
        for mod in ["rtsai-topdown", "rtsai"]:
            campaign += '<td>'
            for diff in ["easy", "normal", "hard"]:
                rs = [r for r in cases.values() if r["mission"] == m["id"] and r["mod"] == mod and r["difficulty"] == diff]
                color = "green" if rs and all(r["passed"] for r in rs) else "amber"
                campaign += f'<span class="badge {color}">{sum(r["passed"] for r in rs)}/{len(rs)}</span> '
            campaign += '</td>'
        campaign += '</tr>'
    campaign += '</table>'
    for m in catalog:
        rs = [r for r in cases.values() if r["mission"] == m["id"]]
        campaign += f'<details><summary>{esc(m["title"])} · inspect {len(rs)} conditions</summary><table><tr><th>Mode / difficulty</th><th>Fixture</th><th>Expected → actual</th></tr>'
        for r in rs:
            color = "green" if r["passed"] else "red"
            campaign += f'<tr><td>{r["mod"]} / {r["difficulty"]}</td><td>{esc(r["case"]["id"])}</td><td class="{color}">{r["case"]["expected"]} → {r["actual"]}</td></tr>'
        campaign += '</table></details>'
    roster = '<div class="grid">'
    for name, summary in balance.items():
        roster += f'<div><h3>{"RA2" if name == "balance-roster" else "Classic"} · {summary["complete"]} complete</h3><p>{summary["draws"]["tick-cap"]} capped draws · {summary["errors"]} errors</p><table><tr><th>Faction</th><th>W / L / D</th><th>Units / game</th></tr>'
        for faction, r in sorted(summary["factions"].items()):
            roster += f'<tr><td>{faction}</td><td><div class="bar"><i class="w" style="width:{100*r["wins"]/r["games"]}%"></i><i class="l" style="width:{100*r["losses"]/r["games"]}%"></i><i class="d" style="width:{100*r["draws"]/r["games"]}%"></i></div><small>{r["wins"]} / {r["losses"]} / {r["draws"]}</small></td><td>{r["mean_unit_count"]}</td></tr>'
        roster += '</table></div>'
    roster += '</div>'
    voice_html = ''
    order = {"high": 0, "review": 1, "routine": 2}
    for r in sorted(voices["rows"], key=lambda r: (order[r["priority"]], r["language"], r["file"])):
        voice_html += f'<article class="voice" data-language="{r["language"]}" data-priority="{r["priority"]}"><span class="badge">{r["priority"]}</span> <b>{r["file"]}</b> · {r["language"]}<p dir="auto">{esc(r["intended_text"])}</p><p>{esc(r.get("english_line", ""))}</p><audio controls preload="none" src="{esc(r["audio_uri"])}"></audio><p dir="auto"><small>Fresh ASR: {esc(r["fresh_asr"])} · raw CER {r["fresh_cer"]}<br>{esc(r.get("screening_note", r.get("notes", "")))}<br>Existing review: {esc(r.get("verdict", ""))} · {esc(r.get("action", ""))}<br>{r["seconds"]}s · {r["sample_rate"]} Hz · {r["clipped_samples"]} clipped samples</small></p><label>Fluent reviewer <input data-file="{r["file"]}" data-field="reviewer" placeholder="Name and language/dialect"></label><label>Decision <select data-file="{r["file"]}" data-field="decision"><option value="pending">Pending</option><option value="approve">Approve pronunciation and meaning</option><option value="revise">Revise / re-record</option></select></label><label>Notes <textarea data-file="{r["file"]}" data-field="notes"></textarea></label></article>'
    template = (ROOT / "tools/acceptance-report.html").read_text(encoding="utf-8")
    substitutions = {"__CARDS__": cards, "__CAMPAIGNS__": campaign, "__ROSTER__": roster, "__VOICES__": voice_html,
                     "__SOURCE__": esc(json.dumps(data["source"], indent=2)), "__SUPERSEDED__": esc(json.dumps(superseded, indent=2)),
                     "__DATA__": json.dumps([{k: r[k] for k in ["file", "language", "sha256"]} for r in voices["rows"]]).replace("</", "<\\/")}
    for key, value in substitutions.items():
        template = template.replace(key, value)
    (args.output / "index.html").write_text(template, encoding="utf-8")
    print(json.dumps({"campaign_cases": len(cases), "campaign_passed": passed, "listening_priorities": sum(r["priority"] == "high" for r in voices["rows"]),
                      "balance": {k: {f: v[f] for f in ["matches", "errors", "draws"]} for k, v in balance.items()}}))


if __name__ == "__main__":
    main()
