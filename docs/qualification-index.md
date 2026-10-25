# Integrated qualification index

The read-only entry point is `tools/qualification_index.py`. The closed formats
are in `compat/qualification-index.schema.json`. The real draft subject is
`compat/candidates/tk-state-resource-1/qualification-subject.json`; it retains
both profiles, all 120 selected criteria and the original incomplete inventory.
It contains no invented wheel, producer, CI or review proof. Its qualification
implementation head is null until the real source freeze. Null proof is reported
per criterion; strict admission cannot pass without the detached envelope.

```powershell
python -B tools/qualification_index.py
python -B tools/qualification_index.py --require-admitted
python -B tools/qualification_index.py --envelope path/to/promotion-envelope.json --require-admitted
```

The first is structural checking of a potentially incomplete subject. The second
currently rejects the absent promotion envelope/current-head CI. The third checks
the subject plus detached promotion basis, original required CI bundle, impact
approval and independent final review. A successful scoped result never marks
candidate-wide, original-inventory or release completion true.

## What is joined

The immutable subject pins full candidate/selection/execution-map/execution-ledger
bytes. Existing validators check their frozen scope, original parents and same-
profile whole-row dependencies. Each selected profile names the exact archive,
native producer, original attempt history, selected latest attempt and retention
proof. Archive membership/native hashes must match the producer's four shipping
outputs. Qualified row identities must match that wheel. The existing inventory
validator revalidates functional pytest, installed distribution and all three
normalized original absence/control/shutdown gates. The index additionally binds
the gate runtime report to the selected terminal attempt.

A closed original attempt-history record retains every declared attempt with its
ID/order/outcome/report. Omission or substitution relative to that record rejects.
The latest selected attempt must pass; every attempt needs actual process exit/
wait and terminal retention. Failed or cancelled attempts need a bound independent
resolution, identifying the attempt, profile and wheel. Full external discovery
and review of the history remain necessary; the validator cannot discover a run
never exported by its producer.

Retention checking consumes the original terminal manifest, exact cleanup plan,
applied command/result and frozen policy/registry references. It verifies hashes,
owner/run, original workspace paths, exact scratch scope/absence, full deletion
count, retained role/hash coverage and actual exit/wait. Artifact/native inputs
and original installed reports/tests/gates must remain in the retained set.
It never invokes cleanup, requires obsolete scratch to stay live, or treats a
currently reused PID as evidence of a historical process lifetime.

The promotion basis pins subject, repository/head, required CI policy/bundle and
independent change-impact decision. The detached final review names the basis
digest. Neither object contains its future approval hash. An envelope cannot
replace its subject, use another head's CI or transplant an old final review.
Changing source/tools/scope/proof changes affected identities and review needs.

## Native production and reuse

`tools/qualification_native.py` separates stable production identity from its
original test recipe and candidate-specific reuse link. Actual native/build/lock
inputs, toolchain/ABI/SDK/build preparation and output hashes identify production;
harness and CTest requirements remain in their original recipe/proof. Unrelated
CPython preparation helpers and candidate/spec/observer fields are not production
inputs. A historical harness is checked from retained bytes rather than compared
with today's mutable tests. Current candidate source/scope approvals must bind
the exact reuse link; a stable binary does not transfer approval to a changed
observer or requested scope.

`tools/qualification_epoch.py` adapts the original native_epoch command protocol,
including its actual MSBuild argument and original CTest list. It checks original
ownership/freeze/status, retained sources/harness/projects/cache, locked build
preparation/SDK, command logs, actual terminal receipt and all four output hashes.
It supports only the known hash-matching guard protocol; other producer versions
need an explicit reviewed adapter. Original commands are not rewritten into the
new recipe. Missing old proof remains missing and may necessitate one managed
build. No original leaf is actually admitted by this source packet.

## Validation scope and remaining work

Synthetic outer-index tests deliberately stub already separately tested validators
to exercise reference, attempt, retention and promotion orchestration in memory.
They are not original installed reports or actual approvals. Native/archive/SDK/
CI validators have their own semantic control suites; existing compatibility
inventory tests exercise their original report gates. These tests never establish
that a real wheel passed the complete protocol. The real subject remains missing
all required proof.

Next requirements are actual cumulative source/fixture and semantic scope review,
producer-admissibility/blocker decisions, exact installed candidate evidence with
original controls, full retained attempt history, current-head CI and independent
promotion review. The [Linux scissor investigation](msaa-scissor-isolation.md)
now has a tested compatible driver and an offline preparation command; adopting
that exact configuration still requires renewed profile/installed evidence.
The [Windows threedee packet](threedee-startup-diagnosis.md) now passes the old
exact installed host workflow and all three absence gates, but did not establish
the historical stall's cause; causal/final-artifact obligations remain open.
Full API breadth and distinct Linux GPU/Metal hardware obligations remain required. Source controls cannot close them. Source, test results and meaningful failures are retained locally
under `build/runs/integrated-h4-38/`; actual managed scratch, if used by fixture
checks, requires its own applied cleanup receipt before handoff.
