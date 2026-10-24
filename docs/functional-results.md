# Functional results from the observed child

Script scenarios can export `VISPY_FUNCTIONAL_RESULT` as a nonempty JSON object.
The isolated probe captures it from the namespace returned by `runpy.run_path`.
It never parses stdout or accepts a separate functional-result file. The Tk
composite workflow requires the export; an early `SystemExit(0)` cannot supply a
returned namespace and fails that requirement. Other legacy scenarios remain
usable without an export and acquire no new functional-coverage claim.

The version 1 worker envelope has exactly these fields:

| Field | Required meaning |
| --- | --- |
| `schema` | Integer `1`. |
| `producer_pid` | The capturing worker's actual PID, equal to the worker report PID. |
| `workflow` | The exact observed ID, scenario, script hash, literal arguments, binding and features. |
| `source_mode` | Boolean matching the worker. Source results cannot back installed behavior. |
| `payload` | A detached JSON snapshot of the returned export. Non-JSON values, non-string keys and nonfinite numbers fail. |
| `payload_sha256` | SHA-256 of canonical sorted compact JSON for that snapshot. |

The controller records `functional_result_sha256` for the complete envelope.
Its existing `worker_report_sha256` still binds the complete original worker
report. The normalizer checks both edges for discovery and replay, matching PID,
workflow, mode, child exit/wait, artifact/environment and all original gates.
The snapshot helper and functional decoder are part of the frozen collector
source identity. A good payload cannot hide a later wheel/member or cleanup
failure; the actual failed worker/process verdict remains binding.

## Closed Tk payload contract

`tools/no_opengl/functional.py` enforces schema `1`, contract
`tk-state-resource-1`, closed fields at every nested record and these exact branch
sets. Unknown, missing or duplicate records fail even when metadata hashes are
recomputed.

| Branch ID | Required result |
| --- | --- |
| `ordinary.state` | Exactly one raw and wrapper ordinary submission record, actual before/after counters, no implicit wait/present and independently expected green/blue readback. |
| `resource.upload-recovery` | Actual upload injection and original callback traceback, stopped Timer, scoped counters equal their baseline, clean host teardown and explicit shared-resource/device recovery. A scoped baseline may contain unrelated existing allocations; final native shutdown is a separate zero-gauge requirement. |
| `progress.poll`, `progress.draw` | Both callback orders, one injected failure and one delivery, original traceback, stopped polling, explicit recovery, blue survivor output and no cleanup error. |
| `submission.gloo.immediate`, `submission.gloo.delayed`, `submission.raw.immediate`, `submission.raw.delayed` | All route/delay tuples: single configured slot, held ticket, contextual capacity error, retained queued work, unchanged submit/wait/present counters through rejection/early progress, observed retirement before retry, exactly one retry submission, no residual queued draws, exact green readback while Tk stays blue, preserved host and restored prior slots. |

Actual colors, counts, configured/saved/restored slots and the retirement
snapshot are recorded by the scenario. Full-frame assertions and existing
watchdogs remain intact. The decoder requires JSON integer counters/colors
rather than accepting booleans that compare equal to integers. A successful
scenario export exists only after its assertions and independent cleanup finish.

## Criterion and scope joins

The existing execution map now supports the closed `functional_result` field
on each mapping: `schema`, `contract`, and unique `branch_ids`. This is an
additive optional field in its v1 schema for other workflows; every known Tk
mapping requires the exact finite assignment semantically. Raw/wrapper flush
failure/recovery criteria bind their own immediate/delayed routes. Ordinary
state and resource/Timer criteria bind their corresponding result branches.
Both progress orders remain required by the whole composite contract.

The same existing scope approval binds `execution_map_sha256`, including these
assignments. `validate_for_criterion` consumes that reviewed mapping and the
bound worker result. The execution validator rejects substituting another
branch that happens to exist in the same report. Selecting one criterion cannot
filter a failed required branch out of its complete composite workflow.

The criterion decoder does not admit a row. Consumers first validate the reviewed
execution declaration and normalize its original complete raw-report bundle.
A matching PID or a non-source flag alone is not an installed-origin/member audit.

This adds a functional join to the existing report chain; it creates no fourth
absence gate, standalone auditor or new approval type. Installed member/origin,
dependency, startup/transient-load, execution/API, native controls, original
shutdown, required head CI and final promotion review remain mandatory.

## Source verification boundary

CPU controls exercise actual isolated probes and the controller, malformed or
missing exports, forged stdout fragments, different-child/workflow/source-mode
substitutions, duplicate/unexecuted branches, altered counts/colors, missing
retry/recovery and post-scenario failure. Synthetic fixtures and approvals are
explicitly unit data, never graphics or installed evidence.

Real Windows and WSL source runs reuse the existing native leaves. A hash-pinned
source-only wrapper supplies that leaf to the actual isolated probe and exports
the real composite result. Its source flag, wrapper hash and literal arguments
remain in the report; those identities cannot stand for the installed candidate
script. Source wrapper shutdown is checked separately and does not claim the
probe's installed-native cleanup ownership. The retained commands, raw results,
profiles, original attempts and terminal cleanup are in
`build/runs/worker-results-33/`.

Current declarations remain unreviewed and unqualified. The exact-artifact index
and actual installed qualification are still pending. No earlier source receipt
is converted into an installed result by this transport.
