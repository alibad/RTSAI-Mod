#!/usr/bin/env python3
"""Freeze exact local build inputs; no checkouts, worktrees, downloads or overwrite.

engine: export the mod.config pin from an existing read-only Git object database.
snapshot: copy tracked/current non-ignored source (including untracked additions).
verify: verify a manifest, rejecting missing, changed or unexpected source files.
Copies contain no .git; bin/obj are disposable only in per-session build copies.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SECRET_NAMES = {"user.config", ".env", "credentials.json", "token.json", "tokens.json"}
EXCLUDED_PARTS = {".git", ".github", ".disabled-workflows", "bin", "obj", "node_modules", ".cache", ".inputs", ".session-artifacts", "private", "preserved", "Support"}
PROPRIETARY = {".mix", ".bag", ".idx", ".vqa", ".bik"}

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], env={**os.environ, "GIT_NO_LAZY_FETCH": "1"})

def digest_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()

def identity(entries):
    return hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def manifest(root, metadata):
    entries = [{"path": p.relative_to(root).as_posix(), "size": p.stat().st_size, "sha256": digest_file(p),
                "executable": bool(p.stat().st_mode & 0o111)}
               for p in sorted(root.rglob("*")) if p.is_file() and p != root / "INPUTS.json"]
    value = {"schema": 1, **metadata, "sourceSha256": identity(entries), "files": entries}
    (root / "INPUTS.json").write_text(json.dumps(value, indent=2) + "\n")
    return value

def check(root):
    value = json.loads((root / "INPUTS.json").read_text())
    actual = [{"path": p.relative_to(root).as_posix(), "size": p.stat().st_size, "sha256": digest_file(p),
               "executable": bool(p.stat().st_mode & 0o111)}
              for p in sorted(root.rglob("*")) if p.is_file() and p != root / "INPUTS.json"]
    if actual != value["files"] or identity(actual) != value["sourceSha256"]:
        raise ValueError(f"Input changed: {root}; recreate a NEW snapshot rather than overwrite")
    if any(p.name == ".git" for p in root.rglob("*")): raise ValueError("Input contains Git metadata")
    return value

def new_destination(dest, source):
    dest = dest.absolute()
    if dest.exists() or dest.with_suffix(".tar").exists(): raise ValueError(f"Refusing to overwrite existing input/archive: {dest}")
    if source == dest or dest in source.parents: raise ValueError("Destination is a source ancestor")
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest

def export_engine(repo, dest):
    pin = re.search(r'^ENGINE_VERSION="([a-f0-9]{40})"', (ROOT / "mod.config").read_text(), re.M).group(1)
    commit = git(repo, "rev-parse", pin + "^{commit}").decode().strip()
    if commit != pin: raise ValueError("Engine pin resolution differs")
    with tempfile.TemporaryDirectory(dir=dest.parent) as work:
        work = Path(work)
        archive = work / "engine.tar"
        subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", "--output", str(archive), pin], check=True, env={**os.environ, "GIT_NO_LAZY_FETCH": "1"})
        with archive.open("rb") as stream:
            exported = subprocess.check_output(["git", "get-tar-commit-id"], stdin=stream).decode().strip()
        if exported != pin: raise ValueError("Archive commit verification failed")
        stage = work / "source"; stage.mkdir()
        with tarfile.open(archive) as tar:
            for member in tar:
                rel = Path(member.name)
                if rel.is_absolute() or ".." in rel.parts or ".git" in rel.parts or member.issym() or member.islnk():
                    raise ValueError(f"Unsafe archive member: {member.name}")
                if rel.parts[0] == ".github": continue
                tar.extract(member, stage, filter="data")
        value = manifest(stage, {"kind": "engine-archive", "commit": pin,
                          "tree": git(repo, "rev-parse", pin + "^{tree}").decode().strip(),
                          "archiveSha256": digest_file(archive), "archiveFormat": "git tar",
                          "transforms": ["omit .github"],
                          "source": str(repo), "localOnlyResourcesCopied": False})
        shutil.copy2(archive, dest.with_suffix(".tar"))
        shutil.move(str(stage), dest)
    return value

def snapshot(repo, dest, prefixes):
    branch = git(repo, "branch", "--show-current").decode().strip()
    if branch not in ("main", "master"): raise ValueError(f"Only primary main/master inputs permitted: {repo} is {branch}")
    paths = sorted(set(git(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0")) - {""})
    selected = []; omitted = []
    for name in paths:
        rel = Path(name)
        if prefixes and not any(name == prefix or name.startswith(prefix.rstrip("/") + "/") for prefix in prefixes): continue
        if EXCLUDED_PARTS.intersection(rel.parts) or rel.name in SECRET_NAMES or rel.name.startswith(".env.") or rel.suffix.lower() in PROPRIETARY or rel.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
            omitted.append(name); continue
        p = repo / rel
        if not p.exists(): continue  # current tracked deletions belong to the source identity
        if p.is_symlink(): raise ValueError(f"Source symlinks must be resolved explicitly, refusing {p}")
        if p.is_file(): selected.append(name)
    with tempfile.TemporaryDirectory(dir=dest.parent) as work:
        stage = Path(work) / "source"; stage.mkdir()
        for name in selected:
            to = stage / name; to.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(repo / name, to)
        diff = git(repo, "diff", "HEAD", "--binary")
        value = manifest(stage, {"kind": "working-tree-snapshot", "source": str(repo), "branch": branch,
                          "head": git(repo, "rev-parse", "HEAD").decode().strip(),
                          "diffSha256": hashlib.sha256(diff).hexdigest(),
                          "dirtyPaths": git(repo, "status", "--short").decode().splitlines(),
                          "prefixes": prefixes, "omitted": omitted})
        for entry in value["files"]:
            if digest_file(repo / entry["path"]) != entry["sha256"]: raise ValueError("Source changed during snapshot")
        shutil.move(str(stage), dest)
    return value

def build_copy(source, dest):
    if source in dest.parents: raise ValueError("Build copy must be outside frozen input")
    value = check(source)
    shutil.copytree(source, dest)
    transforms = []
    if value['kind'] == 'engine-archive':
        pin = value['commit']
        (dest/'VERSION').write_text(pin+'\n')
        for mod in (dest/'mods').glob('*/mod.yaml'):
            mod.write_text(re.sub(r'Version: .*', f'Version: {pin}', mod.read_text()))
        transforms = ['stamp private VERSION and engine mod versions']
    receipt = {'schema':1, 'kind':'private-build-copy', 'inputSourceSha256':value['sourceSha256'],
               'input':str(source), 'transforms':transforms}
    (dest/'BUILD-INPUTS.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    subs = ap.add_subparsers(dest="command", required=True)
    engine = subs.add_parser("engine"); engine.add_argument("--repo", type=Path, default=ROOT.parent / "OpenRA"); engine.add_argument("--out", type=Path, required=True)
    snap = subs.add_parser("snapshot"); snap.add_argument("--repo", type=Path, required=True); snap.add_argument("--out", type=Path, required=True); snap.add_argument("--include", action="append", default=[])
    cp = subs.add_parser("copy"); cp.add_argument("--input", type=Path, required=True); cp.add_argument("--out", type=Path, required=True)
    verify = subs.add_parser("verify"); verify.add_argument("path", type=Path)
    args = ap.parse_args()
    if args.command == "verify": value = check(args.path)
    elif args.command == "copy":
        source = args.input.resolve(); dest = new_destination(args.out, source); value = build_copy(source, dest)
    else:
        repo = args.repo.resolve(); dest = new_destination(args.out, repo)
        value = export_engine(repo, dest) if args.command == "engine" else snapshot(repo, dest, args.include)
        check(dest)
    print(json.dumps({k: v for k, v in value.items() if k != "files"}, indent=2))

if __name__ == "__main__": main()
