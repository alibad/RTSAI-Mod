# Main-only source inputs

`tools/build-inputs.py` exports the engine revision already pinned in `mod.config`
from local OpenRA Git objects. It never checks out a ref, downloads content or
replaces an existing directory. `INPUTS.json` records the archive checksum, Git
commit/tree, all extracted file hashes. Engine VERSION/mod stamps are made only in the
private build copy and must be recorded in its build receipt.
The engine copy has no `.git` and excludes hosted workflows. Proprietary content,
credentials and ignored resources are never pulled from the engine checkout.

```sh
python3 tools/build-inputs.py engine --repo ../OpenRA --out ../.session-artifacts/S02/inputs/engine
python3 tools/build-inputs.py snapshot --repo . --out ../.session-artifacts/S02/inputs/mod
python3 tools/build-inputs.py verify ../.session-artifacts/S02/inputs/mod
```

Snapshots capture tracked current files and non-ignored untracked additions,
including deletions and source diffs. Default omissions include secrets, local
configuration, caches/build outputs, private/preserved content and MIX/BAG/video
archives. `--include` selects specific folders for small mission/art snapshots.
Every file identity includes path, size, SHA-256 and executable status. A new
snapshot must use a new destination. Keep `INPUTS.json` immutable with the source.

Before a build, verify inputs, then copy engine and mod snapshots to the session's
private build directory. Build only those copies: engine MSBuild projects write
`bin/obj` by design. Never build against another session's live source or frozen
input. A writable disposable copy is a dependency/build directory, never a Git
checkout or worktree. Preserve the original manifests beside build receipts;
verification after compilation fails intentionally because build outputs changed.
For native mod projects use `-p:EngineRootPath=/absolute/session/build/engine`.
The default remains `../engine`. Local resource prerequisites not captured by
snapshots (GeoIP, models, toolchains) must be explicitly declared and hashed in
release receipts; missing dependencies must not be replaced by owned-game data.

Use the verified copy command to prepare a disposable native engine dependency:

```sh
python3 tools/build-inputs.py copy --input /session/inputs/engine --out /session/native/engine
```

Only this private copy receives SDK VERSION/mod-version stamps, with an explicit
BUILD-INPUTS.json transform receipt linking its original source identity.
`fetch-local-engine.sh` freezes source in ignored .inputs/, verifies an existing
immutable input if present, then creates a **new** native build dependency. It
refuses existing build destinations rather than deleting them. VERSION prevents
the legacy SDK fetch-engine.sh from mistaking a raw archive for a missing pin.
The immutable input remains unchanged; native make/publish must use the copy.

For macOS ARM builds, pass `-p:TargetPlatform=osx-arm64`. Grpc.Tools 2.69.0 ships
an x64 macOS compiler: hosts without Rosetta must set `PROTOBUF_PROTOC` and
`GRPC_PROTOC_PLUGIN` to installed native executables. Record their versions and
hashes in the session receipt. Build the engine's OpenRA.Utility project in the
private engine copy before running `tools/standalone-audit.py`; the audit now uses
symlinks on macOS and propagates failures from `--utility --check-yaml`.
