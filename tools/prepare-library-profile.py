"""Prepare the same per-mode support directory used by the native Library; never overwrite player files."""
import argparse
import json
from pathlib import Path
import shutil

def prepare(root, mode):
    if mode not in ('rtsai-classic-core', 'rtsai-ra2'):
        raise ValueError('Choose Classic or RA2')
    target = root / 'Games' / mode
    target.mkdir(parents=True, exist_ok=True)
    def missing(source, destination):
        if source.is_symlink(): raise ValueError(f'Linked player data must be reviewed before migration: {source}')
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            for child in source.iterdir(): missing(child, destination / child.name)
        elif source.is_file() and not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    marker = target / 'migration.json'
    if not marker.exists():
        missing(root / 'settings.yaml', target / 'settings.yaml')
        for kind in ['Saves', 'Replays', 'maps', 'ExperiencePacks', 'CapabilityPacks']:
            missing(root / kind / mode, target / kind / mode)
        if mode == 'rtsai-classic-core': missing(root / 'maps/ra', target / 'maps/ra')
        marker.write_text(json.dumps({'source': str(root), 'game': mode, 'originalPreserved': True}) + '\n')
    if mode == 'rtsai-classic-core' and not (target / 'Content').exists():
        missing(root / 'Content', target / 'Content')
    return target

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--mode', required=True)
    args = p.parse_args()
    print(json.dumps({'support': str(prepare(args.root.resolve(), args.mode))}))
