#!/usr/bin/env python3
"""Inventory custom resources and preserve unique legacy bytes locally, never in a release.

Legacy additions/edits are preservation candidates, not automatic licence clearance.
No source files are removed or modified. Run --check to verify the snapshot archive.
"""
import argparse, collections, hashlib, json, subprocess, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
DEST = ROOT / 'resources'
MANIFEST = DEST / 'resource-transition.json'
ARCHIVE = DEST / 'preserved' / 'legacy-custom-resources-20261009.zip'

def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def verify():
    document = json.loads(MANIFEST.read_text(encoding='utf-8'))
    count = 0
    with zipfile.ZipFile(ROOT / document['archive']) as archive:
        for entry in document['preserved']:
            if digest(archive.read(entry['archiveMember'])) != entry['sha256']:
                raise RuntimeError('Archive hash mismatch: ' + entry['source'])
            count += 1
    for entry in document['installed']:
        path = ROOT / entry['path']
        if not path.is_file() or digest(path.read_bytes()) != entry['sha256']:
            raise RuntimeError('Installed resource changed since inventory: ' + entry['path'])
    print(f"Verified {count} preserved source entries and {len(document['installed'])} installed resources")

def capture():
    if ARCHIVE.exists():
        raise RuntimeError('Snapshot exists; use --check. Preserve earlier snapshots before creating a new one.')
    classic = WORKSPACE / 'OpenRA'
    baseline = git(classic, 'merge-base', 'main', 'bleed')
    sources = []
    # Keep custom additions and edits, including art-audit branches and their uncommitted sprite variants.
    for name in ['OpenRA', 'OpenRA-wt-art-audit', 'OpenRA-wt-art-audit-baseline', 'OpenRA-wt-in-game-catalog', 'OpenRA-wt-integrator', 'OpenRA-wt-usa-concept']:
        repo = WORKSPACE / name
        if not repo.exists():
            continue
        paths = set(git(repo, 'diff', '--name-only', '--diff-filter=AM', baseline, 'HEAD', '--', 'mods/ra').splitlines())
        paths.update(git(repo, 'diff', '--name-only', '--diff-filter=AM', 'HEAD', '--', 'mods/ra').splitlines())
        paths.update(git(repo, 'ls-files', '--others', '--exclude-standard', '--', 'mods/ra').splitlines())
        for rel in sorted(paths):
            file = repo / rel
            if file.is_file():
                sources.append((name + '/' + rel, file, 'legacy-classic; provenance/port review required'))
    # Retain the authored faction source assets, voice provenance, scripts and old mission sources.
    for name in ['OpenRA-AI', 'OpenRA-AI-wt-art-audit', 'OpenRA-AI-wt-ra2-red-sea', 'OpenRA-AI-wt-usa-concept', 'OpenRA-AI-wt-integrator']:
        repo = WORKSPACE / name
        if not repo.exists():
            continue
        for folder in ['assets', 'missions', 'scripts', 'docs/upstream-reuse']:
            paths = set(git(repo, 'ls-files', '--', folder).splitlines())
            paths.update(git(repo, 'ls-files', '--others', '--exclude-standard', '--', folder).splitlines())
            for rel in sorted(paths):
                file = repo / rel
                if file.is_file() and '__pycache__' not in file.parts:
                    sources.append((name + '/' + rel, file, 'source resource; provenance/port review required'))
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    preserved, seen = [], set()
    with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for source, path, status in sources:
            data = path.read_bytes()
            sha = digest(data)
            member = 'objects/' + sha
            if sha not in seen:
                archive.writestr(member, data)
                seen.add(sha)
            preserved.append(dict(source=source, bytes=len(data), sha256=sha, archiveMember=member, status=status))
    installed = []
    for folder in ['mods/rtsai/modern-factions', 'mods/rtsai/standalone', 'mods/rtsai/uibits', 'tools/terrain']:
        for file in sorted((ROOT / folder).rglob('*')):
            if file.is_file() and '__pycache__' not in file.parts:
                installed.append(dict(path=file.relative_to(ROOT).as_posix(), bytes=file.stat().st_size, sha256=digest(file.read_bytes())))
    art = WORKSPACE / 'RTSAI-Art'
    art_files = git(art, 'ls-files', '--', 'units', 'models', 'bible', 'history', 'animations', 'tools').splitlines()
    art_loose = git(art, 'ls-files', '--others', '--exclude-standard', '--', 'units', 'models', 'bible', 'history', 'animations', 'tools').splitlines()
    retained = []
    for rel in sorted(set(art_files + art_loose)):
        file = art / rel
        if file.is_file():
            retained.append(dict(source='RTSAI-Art/' + rel, sha256=digest(file.read_bytes()), bytes=file.stat().st_size, status='retained editable source library; do not remove'))
    document = dict(schemaVersion=1, captured='2026-10-09', archive=ARCHIVE.relative_to(ROOT).as_posix(), archiveSha256=digest(ARCHIVE.read_bytes()),
                    policy='Local preservation only. Legacy entries are not licensed or runtime-integrated by this inventory; never mount/archive them in release packages.',
                    classicBaseline=baseline, preserved=preserved, installed=installed, retainedArtSources=retained,
                    counts=dict(preservedEntries=len(preserved), uniquePreservedObjects=len(seen), installedResources=len(installed), retainedArtSources=len(retained), archiveBytes=ARCHIVE.stat().st_size))
    MANIFEST.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(document['counts']))
    verify()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    verify() if args.check else capture()
