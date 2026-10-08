# Custom resource transition

`resource-transition.json` records the exact SHA-256 and source/destination for installed standalone resources, retained RTSAI-Art source models/candidates, and preserved legacy Classic resources.

`preserved/legacy-custom-resources-20261009.zip` is a **local, ignored preservation archive**. Its objects are deduplicated by hash; the manifest maps each source path and variant back to the exact bytes. It includes legacy custom edits and authored asset/tool/mission sources. A legacy addition is not proof of a redistribution licence: those entries remain outside the runtime mounts and packages until reviewed and ported.

All original repositories, worktrees, models, loose files and build artifacts remain in place. No resources are deleted by this transition. RTSAI-Art remains the editable art source library. The preserved archive and that library must be retained when cleaning up folders; the tracked manifest alone is not a backup.

Run `python tools/preserve-custom-resources.py --check` to verify all preserved objects and installed resources against this snapshot. Capture a new snapshot after intentional resource changes; never overwrite the only archived version.
