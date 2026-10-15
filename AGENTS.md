# Working in RTSAI-Mod

Several sessions change RTS AI at the same time. Work that lives only on a branch, or on a checkout that is behind,
gets lost or shipped half-done. On 14 October 2026 a browser runtime built from a stale worktree went live without a
fix that was already on main.

## Branches: commit on main, always from the latest main

- `main` is the only long-lived branch and `origin/main` is the truth. Commit on main.
- Before you start, before every commit, and before any build you test or ship, run `git fetch` and bring your
  checkout up to the latest `origin/main`: `git pull --ff-only`, or `git pull --rebase` if you have local commits. Never
  build or test on a checkout that is behind main.
- If another session uses main, coordinate or wait. Worktrees require an explicit owner request; see the policy below.
- Finished work must not sit on a branch or as unpushed commits on a local main, because other sessions can't see it.
- Commit before you build inputs. `RTSAI-WebGame/tools/prepare-inputs.py` snapshots this checkout's current source,
  including uncommitted files, so commit first to keep builds reproducible.
- Never force-push, hard-reset or rebase commits that are already on `origin/main` or that belong to another session.

## The engine

- The engine is now canonical `../OpenRA` on `main` (owner fork remote `fork/main`). The former `rtsai/engine` and local engine feature work were consolidated there on 15 October 2026. Do not resume development in the old worktree or branch.
- Keep engine changes minimal. Published `ENGINE_VERSION` pins must continue to resolve; only update a public pin after an explicitly authorized engine push. A local consolidation does not authorize publishing.
- Local desktop builds use canonical OpenRA main and record its exact SHA. Browser releases remain subject to the existing release script and owner approval.

## The browser game

rtsai.net/play is released only with `node tools/release-play.mjs` in RTSAI-WebGame, and only with the owner's
approval. See that repository's AGENTS.md.

## Worktrees require an explicit owner request (15 October 2026)

- Use the existing canonical checkout. Do not create a Git worktree or a parallel clone unless the owner explicitly asks for it in the current task. This supersedes older instructions permitting worktrees for concurrency, isolation, convenience, or risk.
- Another session using the checkout is not permission to create a worktree. Coordinate non-overlapping changes, wait, or report the specific blocker; preserve all in-progress work.
- In the OpenRA/RTS AI repositories, work and commit on canonical `main`. Fetch the correct owner remote and safely incorporate its main before starting, committing, or validating a build. Never reset, force-push, or rewrite another session's commits.
- If the owner explicitly authorizes a worktree, keep it temporary, start from current main, and integrate validated work back into canonical main. Do not leave the only copy of finished work on a branch or worktree.
- Before retiring an existing branch or worktree, verify that its unique commits, uncommitted files, and user artifacts are preserved and integrated where appropriate. Never delete unique work to make a checkout look clean.
- Keep this policy change and local consolidation local. A request to consolidate on main does not by itself authorize a push, deployment, release, or deletion of branches/worktrees.
