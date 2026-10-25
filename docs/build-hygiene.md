# Build storage and retention

Use a bounded run lifecycle: register, execute, retain, clean. Retaining every
experiment is not required for reproducibility. The current implementation's
qualification and licensing requirements still apply; cleanup does not promote
an unqualified artifact or remove a failed result from the capability matrix.

## Storage layout

Select one storage workspace for cooperating agents. Source worktrees may be
separate, but agents share its budget, dependency cache and artifact store.

| Path | Purpose and retention |
| --- | --- |
| `build/work/<run-id>/` | One owner's writable scratch; remove after the child exits and retained outputs are verified. |
| `build/runs/<run-id>/` | Command, actual exit/wait, source/artifact hashes, focused results, cleanup plan and receipt. Keep these small. |
| `build/artifacts/<sha256>/` | One copy of each retained wheel, source archive, patch set or other deliverable. Other runs reference it. |
| `build/cache/` | Shared immutable dependency sources, one SDK per source/toolchain/configuration, and one environment per lock/profile. |
| `build/.hygiene/` | Local explicit protected/blocked paths, admitted legacy roots, capacity roots and retention index. |

Do not place Git repositories, directory aliases or hardlinked writable files
inside managed scratch. Build from an existing worktree or shared source cache.
Immutable inputs stay outside scratch. If a native producer creates output
symlinks, use its documented clean target after collecting outputs; the generic
cleanup tool refuses aliases rather than following them. Resolve such a refusal
with an audited producer-specific cleanup, not a force option.

Do not recursively snapshot previous build/evidence directories or whole
installed environments. Prefer a source commit plus its retained preferred
source archive and any dirty patch, pinned toolchain/dependency inputs, a command
and focused results. Existing frozen protocols that require materialized inputs
must reuse their exact admitted origins. Register the smallest necessary legacy
keep set and its reason instead of retaining every historical working tree.

## Budget and ownership

The default policy permits **20 GiB of managed scratch in aggregate** and keeps
**10 GiB free** after the declared additional peak allocation. All agents use the
same coordinator-selected workspace; three agents do not get three independent
budgets. A larger Qt/toolchain build needs an explicitly named, versioned policy
profile with its expected peak, owner and terminal cleanup. There is no force
override. A refused preflight means clean eligible old work or revise a genuinely
necessary declared build profile before launching the command.

Preflight is a capacity check, not a continuous process monitor. Long-running
build drivers must retain their periodic disk guards and stop only their owned
processes when the reserve is threatened. For WSL builds, include the Windows
backing volume (normally `/mnt/c`) in the guest registry's `capacity_roots` as
well as checking the guest workspace; free space in a virtual ext4 volume alone
does not prove backing-disk capacity. Do not change filesystem, driver or system
settings as a substitute for cleanup.

An exclusive `.build-hygiene-owner.json` marker binds each run ID to one owner.
The tool does not adopt an existing unregistered directory. In the local
registry, `legacy_roots` enumerates the existing top-level build entries and
admitted persistent stores. When this list is present, new unregistered
top-level entries cause refusal. This is an inventory, not permission to delete
those legacy entries. `protected_roots` and `blocked_roots` are explicit paths;
both a protected descendant and a protected ancestor prevent overlapping cleanup.
If `--registry` is omitted, an existing `build/.hygiene/registry.json` in the
selected workspace loads automatically. Do not replace it with an empty ledger
to bypass an earlier refusal. A separate WSL workspace needs its own native-path
registry and backing-volume entry; the coordinator also accounts for combined
Windows/guest allocations rather than treating their budgets as independent.

## Required lifecycle

1. Reuse an existing artifact when native inputs and configuration match. Before
   allocating new scratch, run preflight with the expected **additional** peak
   bytes, unique run ID and owner. Use `--register` only when starting that run.
2. Write only disposable outputs in its reported `build/work/<run-id>` path.
   Share immutable dependencies outside scratch. Keep command/source/lock
   identity and the actual process result in `build/runs/<run-id>`.
3. Wait for the build/test child and its owned work to finish. Copy necessary
   outputs into stable, hash-addressed storage before declaring them inputs to
   later qualification. A permanent receipt must not depend on disposable
   scratch unless an existing identity-pinned protocol explicitly requires it.
4. Write a terminal retention manifest outside **all** of `build/work`. It must identify the
   matching owner, awaited exit and retained files with SHA-256 hashes and
   `source`, `evidence`, `licenses` roles. Failed/cancelled runs also require a
   `repro` role: retain the minimal reproducer, command, relevant failure log and
   exact source inputs. One file can satisfy multiple roles.
5. Generate a plan, inspect its bounded target, retained hashes and protected
   path checks, then apply it. Application revalidates the manifest, policy,
   registry and exact scratch snapshot before deleting ordinary files and empty
   directories. A changed file, live child, alias or retained-data mismatch
   causes refusal. Record the result, reclaimed bytes and any refusal before
   the next experiment or handoff.

Owner-supplied exit/wait metadata must describe the actual process; it is not a
process-tree attestation supplied by this tool. The optional `child_pid` check
requires that PID to be dead. Concurrent writers are unsupported: late changes
can stop cleanup after some validated files have already been removed. Preserve
the actual deletion count and inspect the remaining state; never report a
partial cleanup as complete.
Retained files and plans must also stay outside all managed scratch, including
other owners' runs. A sibling run is not durable artifact or evidence storage.

The CLI is audit-only by default. Global options precede its subcommand:

```text
python -B tools/build_hygiene.py --workspace <storage-root> --registry <registry.json> audit
python -B tools/build_hygiene.py --workspace <storage-root> --registry <registry.json> preflight --run-id <id> --owner <owner> --expected-peak-bytes <bytes> --register
python -B tools/build_hygiene.py --workspace <storage-root> --registry <registry.json> plan --manifest <terminal.json> --output <cleanup-plan.json>
python -B tools/build_hygiene.py --workspace <storage-root> --registry <registry.json> apply --plan <cleanup-plan.json>
```

For example, a failed run's manifest can retain one source archive containing
the licenses and one failure/reproducer record:

```json
{
  "schema": 1,
  "run_id": "example-1",
  "owner": "packaging",
  "state": "failed",
  "process_exit": 1,
  "child_waited": true,
  "scratch_root": "build/work/example-1",
  "retained": [
    {"path": "build/artifacts/<source-sha>/source.tar.gz", "sha256": "<64 hex digits>", "roles": ["source", "licenses"]},
    {"path": "build/runs/example-1/failure.json", "sha256": "<64 hex digits>", "roles": ["evidence", "repro"]}
  ]
}
```

## Keep and retire

Keep the current Windows/Linux artifacts, their capability matrix and evidence,
one previous known-good artifact per relevant configuration with its original
scope, required preferred sources/patches/toolchain references, and all original
licenses. Keep an unresolved failure's minimal reproducer and necessary failing
artifact. A fixed failure can retain its before/after evidence without preserving
every compiler cache, expanded source copy or environment used to investigate it.

After validating reconstruction or a retained byte-identical copy, retire
superseded successful-run datasets, copied sealed packets, transport archives,
expanded staging, intermediate objects and unused environments. Retain a small
retirement index linking old paths to retained content and hashes. Do not break
actual current build prerequisites merely because their names look old. A
historical report mentioning a path, by itself, is not a reason to keep that
entire working directory indefinitely.

For legacy cleanup, audit the actual current verifier read set, artifact and
qualification references, source/licensing requirements, meaningful failures,
and previous rejection ledger first. Produce an exact action list and recovery
map. Preserve source-origin physical identities where existing verifiers require
them; do not weaken a verifier or retarget its inputs. Never retry an
automatic-review-rejected target, including via a different shell, child path,
or parent directory. Report the stated refusal reason and retain that record.

Measure both logical size and unique compressed file data, with hardlinks counted
once. Branch references and shared environments can look large in naive totals
while offering almost no reclaimable disk space. Do not create another large
backup of already-retained data merely to report cleanup.

## Mesa clipping-repair diagnostic profile

The versioned [mesa-lvp-repair profile](../compat/build-profiles/mesa-lvp-repair.json)
permits one bounded baseline/patch comparison using the retained Mesa release
archive and existing LLVM 18/GCC/Python. Its additional peak is 6 GiB; the shared
20 GiB scratch cap and 10 GiB free reserve are unchanged. It permits no system
package installation or automatic source/dependency fallback.

For this packet the coordinator selects `/home/heq/vispy-vulkan-managed` as the
single scratch workspace, avoiding repeated compiler reads across the Windows
mount. Windows managed scratch must be empty. The guest registry inherits all
current protected/blocked paths and protects existing dependency origins; both
guest and Windows backing capacity are checked. Periodic guards account for both
managed roots against the one aggregate budget. Stable inputs/artifacts/evidence
remain in the existing Windows store, referenced by hash rather than cloned.

The headless configuration isolates the arithmetic defect. It does not establish
complete window-system or hardware support. Retain original/patched necessary
libraries, sources, patch and notices, actual exits/waits and failing controls;
then plan/apply guest cleanup and rehash the retained files. No unpatched input,
system driver, SDK, existing environment or pinned origin is modified.


## Maintained Mesa source-build profile

`compat/software-vulkan-build.json` carries the same bounded headless repair
recipe for `tools/build_software_vulkan.py`: 6 GiB additional peak, four jobs,
30-second capacity guards and no automatic dependency fallback. Register a run
with the selected workspace before invoking it. A guest workspace must retain
its inherited protected/blocked registry and Windows backing-volume capacity
entry; the other coordinator scratch root must remain empty. The builder checks
read-only filesystems as well as free capacity throughout command execution.

The builder verifies the exact release and patch, records the original failing
control, applies the patch and requires all four independent Vulkan controls to
pass. `--fetch` permits only the pinned Mesa source archive if absent; compilers,
LLVM and Python build tools must already be supplied by the existing environment
or an explicitly retained projection. It creates no environment and installs no
system packages. The ephemeral Linux CI setup supplies its declared packages
and hashed Python tools before calling this same builder.

Retain the resulting source-input archive, original release, both necessary
libraries, full original notices, commands and actual exit. Only after waiting
for that invocation, invoke `--cleanup-exit <actual-exit>` with the same run,
owner, output and workspace. Cleanup validates retained identities and generates
and applies an exact managed plan. A failing or interrupted build remains a
failure with its reproducer; source controls do not establish producer admission,
installed artifact qualification or native Linux hardware support.
