# Working in RTSAI-Mod

Several sessions change RTS AI at the same time. Work that lives only on a branch, or on a checkout that is behind,
gets lost or shipped half-done. On 14 October 2026 a browser runtime built from a stale worktree went live without a
fix that was already on main.

## Branches: commit on main, always from the latest main

- `main` is the only long-lived branch and `origin/main` is the truth. Commit on main.
- Before you start, before every commit, and before any build you test or ship, run `git fetch` and bring your
  checkout up to the latest `origin/main`: `git pull --ff-only`, or `git pull --rebase` if you have local commits. Never
  build or test on a checkout that is behind main.
- If another session already uses the main checkout, work in a worktree started from the latest main
  (`git worktree add -b <topic> <dir> origin/main`). Keep rebasing it onto `origin/main` and land it on main
  (`git push origin HEAD:main`) as soon as it works, the same day. Don't stack branches on branches.
- Finished work must not sit on a branch or as unpushed commits on a local main, because other sessions can't see it.
- Commit before you build inputs. `RTSAI-WebGame/tools/prepare-inputs.py` snapshots this checkout's current source,
  including uncommitted files, so commit first to keep builds reproducible.
- Never force-push, hard-reset or rebase commits that are already on `origin/main` or that belong to another session.

## The engine

- The engine is `alibad/OpenRA` branch `rtsai/engine`; for the engine, that branch is main. Keep engine changes
  minimal, and make them on the latest `rtsai/engine`.
- Push `rtsai/engine` first. Then repin `ENGINE_VERSION` in `mod.config` with a commit on main here, so the pin always
  resolves.
- The browser release (`RTSAI-WebGame/tools/release-play.mjs`) builds new runtimes with exactly this pin, and only
  once it is pushed.

## The browser game

rtsai.net/play is released only with `node tools/release-play.mjs` in RTSAI-WebGame, and only with the owner's
approval. See that repository's AGENTS.md.
