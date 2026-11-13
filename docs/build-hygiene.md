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

Retained registry files are input identities. To add protections, create a
successor registry containing every predecessor protected/blocked entry and the
new pinned paths; preserve the predecessor bytes. Explicitly pass `--registry`
on all subsequent preflight, plan and apply commands. Do not silently fall back
to an older registry or overwrite a registry cited by retained qualification.
The current coordinator selection is recorded in
[mandatory review follow-up](../compat/api-acceptance/mandatory-review-followup-v1.json):
`D:/vispy-vulkan-managed/build/.hygiene/registry-mandatory-successor-535.json`.
Its 18 added legacy inputs remain at their original paths; they are protected
from cleanup, not adopted as scratch or relocated into the evidence store.

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

## Windows native leaf on secondary storage

The versioned
[`windows-native-secondary-v1` profile](../compat/build-profiles/windows-native-secondary-v1.json)
places an SDK-linked Windows leaf in the coordinator's registered D: workspace.
It keeps the existing 768 MiB additional allocation, shared 20 GiB scratch cap
and 10 GiB reserve. The source workspace, original SDK, prepared Python/compiler
and immutable dependency origins remain on C:. This permits no SDK rebuild,
environment installation, source-history clone or change to an identity-pinned
origin. Set TEMP/TMP before launching the producer; CMake, compiler, CTest and
retained output paths must all use the selected D: run/store.

The optional recipe `storage_profile` reference binds the exact profile bytes
into the recipe digest and its existing independent review edge. Legacy recipes
retain their original source-workspace scratch rule. A selected profile must
bind canonical, separate local-drive roots and the original SDK location;
source/cache/project/command joins, all required native tests and shipping
output checks remain mandatory. An admitted v1 profile is immutable; changed
policy needs a successor. Live guards tolerate only files disappearing during
sampling; other I/O errors stop the owned child. Terminal cleanup still uses
the unchanged strict snapshot and inherited protected/blocked registry.

This profile establishes storage placement for local native proof. Formal
candidate records still require their own admitted reference resolution and
review bindings. A passing native proof on D: does not establish cross-store
admission, current installed-wheel qualification, strict profile coverage or
release promotion. Retain the original native source archive and notices by
hash rather than copying its contents into another run.

Current Windows backend-only assembly and installed checks use the
[`windows-package-secondary-v1` profile](../compat/build-profiles/windows-package-secondary-v1.json):
one 512 MiB registered D: allocation under the same shared cap/reserve, the
existing packaging backend/dependencies, retained native outputs and one offline
no-deps copied target. A source or report update does not justify rebuilding the
native leaf. Supply the frozen source version explicitly to both
`source_distribution_licenses` and `audit_archive`; their v1 defaults preserve
historical callers. If a caller omits that argument, retain/clean the failure and
audit the same archive bytes with the correct source expectation before deciding
that another assembly is needed. Reuse existing preferred source/license
archives by hash; keep only distinct harness/profile sources and focused results.

## Retained evidence on secondary storage

[`secondary-v1`](../compat/evidence-stores/secondary-v1.json) explicitly describes
the existing Windows and WSL views of the source workspace and D: retained
store. `tools/retained_evidence.py` validates that hash-bound profile, separate
canonical roots and their actual host directories. It rejects managed-scratch
roots and root aliases. There is no ambient environment override, alternate-root
search, source copy or SDK/dependency relocation. The existing retained-file
hash, containment and scratch checks still run under the selected evidence root.
Omitting the selector preserves the original source-root behavior.

| Record | Source workspace retains authority for | Selected store supplies |
| --- | --- | --- |
| Windows native | Candidate/reviews/profile/runtime inputs, original source inputs, preparation, SDK record/consumer/manifest, tool origins | Recipe, original result/logs, before/after source maps, caches/projects/CTest and native outputs |
| Linux native | Candidate/reviews/profile/runtime inputs, schema and producer policy | Original capture descriptor and its retained original CI payloads |
| Wheel archive | Candidate/profile, source version, runtime package contract, pure sources and notices | Exact wheel and native output files |

Native records put `evidence_store: {path, sha256}` inside their existing `reuse`
object. Both independent `native_reuse_links` bind the digest of that complete
object, including the store selection. The Windows recipe's existing scratch
policy is a separate input; retention placement does not rewrite where a producer
originally ran. Linux capture validation reads the schema at the source root and
the original bytes at the evidence root, preserving original remote paths and
checking imported scratch absence under both local roots. Archive records carry
an optional top-level `evidence_store` reference and continue to report missing
producer/installed gates rather than artifact admission.

The imported helper is a required candidate preparation-tool identity. Missing
or changed helper bytes therefore invalidate a new candidate before origin or
review checks. Existing v1 candidates/approvals are not rewritten to fit these
new identities. Keep an admitted v1 store profile immutable; a successor profile
needs explicit schema support and new bindings. No positive synthetic record,
raw archive check or historical proof replay supplies an actual approval.

## Local R2 Linux native profile

Local R2 Linux integration uses the explicit
[`linux-r2-native` profile](../compat/build-profiles/linux-r2-native.json).
Its 6 GiB allocation matches fresh Linux CI and leaves the shared 20 GiB cap
and 10 GiB reserve unchanged. The retained full Linux run used about 3.12 GB;
its source was about 400 MB. Use the existing guest workspace and inherited
registry, keep Windows managed scratch empty, and check both filesystems.
Reuse locked tools, dependency sources, licenses and the selected software
Vulkan driver. A missing prerequisite stops the run. No system installation or
automatic download fallback is authorized by this profile. It covers local
development integration; it does not admit an artifact or qualify native GPUs.

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


For isolated installed-wheel checks, retain/load the produced driver outside the
source and publication checkouts. Linux CI selects an owned workspace under
`RUNNER_TEMP`, registers its `build/work/<run>` and passes `--library-store`
pointing to that workspace's `build/artifacts`. The builder accepts only its
source or selected workspace artifact store, never scratch or an arbitrary
origin. Source archives remain shared immutable inputs; both necessary driver
libraries and their original notices are retained/uploaded with the evidence.
The ordinary installed native-module inventory still rejects every repository
native image. Do not exempt the driver or weaken that verifier to accommodate a
repository-local ICD. Default local library retention is unchanged.

The Linux wheel workflow now uses `tools/linux_ci_lifecycle.py` to register one
external native lease before installing its build tools. Its environment,
consumer, temporary files and native build share that lease; Mesa uses another
registered run in the same workspace and budget. The per-run uv artifact cache
lives in the selected workspace and is cleared with uv's own clean command.
`UV_LINK_MODE=copy` and copied interpreters avoid hardlinked scratch. Audited uv
interpreter aliases are materialized without changing their original targets;
only its redundant `lib64` alias is removed. Unknown aliases still reject.

Each phase retains its real argv, PID, exit, wait, log and selected input
environment. Native commands run directly through the recorder; shell setup
scripts retain their original bytes. Source inputs/licenses, before/after source
maps, generated build configuration, observed toolchain hashes and shipping
outputs survive outside scratch. Every successful or failed terminal run uses
the existing registry-aware cleanup planner and verifier. A still-active or
unawaited child prevents cleanup. Source changes are retained as a delta and
remain failures even after scratch is cleaned. These are development/CI
receipts, not producer or installed-artifact admission.


Experimental Metal CI uses the same registered external POSIX lifecycle. Its
default is exact original build-only reuse with fresh installed CPU controls;
`compat/build-profiles/metal-ci-native.json` documents the explicit 6 GiB fresh
mode. Reuse reserves 1 GiB, and both modes preserve the shared 20 GiB scratch and
10 GiB reserve limits. A PR path filter sees cumulative changes, so it does not
replace an input comparison inside the job. Metadata-only changes must not
silently trigger a native rebuild. Metal graphics qualification remains open.

The [dynamic Windows package profile](../compat/build-profiles/windows-dynamic-package-secondary-v1.json)
is a distinct local successor for the dynamic sampler source. It reuses the
verified outputs of `dynamic-sampler-native-402`, the original prepared backend
and the same 512 MiB/20 GiB/10 GiB budgets. It does not rewrite the older profile
or permit a new native build, SDK or environment. Record the exact assembled
wheel and source/native joins, verify a normal offline target, then retain and
clean it. Its functional observations confer no independent/profile admission.
