# Coverage gap review — 2026-11-08

Primary-agent review of source, the canonical inventory, method catalog,
acceptance packets, original JUnit results and current qualification subjects.
No new functional tests ran. This review supplies findings and priorities;
independent source/scope approval remains pending.

**Follow-up, 2026-11-08:** finding 2's three exact-wheel refresh needs are now
closed by `current-scope-windows-434` / `current-scope-wsl-435`: all 126 cases
pass on each current wheel, with original node IDs/source pins, matching
installed origins and zero renderer shutdown gauges. Both targets are cleaned.
[Fresh acceptance packet](../compat/api-acceptance/current-event-input-depth-v1.json).
Other findings retain their stated scope and priority.

## Findings

### 1. High: current successor release profiles are still unproved

Both current revision-3 qualification subjects have `qualification_head=null`,
no producer/selected attempt, and empty attempts. The 128 selected criteria
remain unproved at qualification level. The eight qualified mandatory matrix
rows retain published-v1 artifact identities. Local current-wheel functional
passes and renewed records are useful prerequisites; current installed strict
observer/control/profile, CI and promotion evidence is still required.

Evidence: [state subject](../compat/candidates/tk-state-resource-3/qualification-subject.json),
[capture subject](../compat/candidates/tk-capture-3/qualification-subject.json),
[matrix](../compat/no-opengl-matrix.json),
[current review packet](../compat/candidates/tk-v2-current/review-packet.json).

**Action:** complete real independent source/scope review and the selected
same-artifact qualification attempts before claiming the successor release is
qualified. Keep the 128 criterion count separate from API or test-case coverage.

### 2. Resolved at finite scope: three older-wheel suites refreshed on current artifacts

These accepted packets bind Windows `5cb463cd…` / Linux `b4c72484…`, while the
current wheels are `ba8a54c5…` / `4bc3cd77…`. The following refresh actions from
the initial review have now passed on both current wheels:

| Scope | Cases per platform | Current source pins | Completed refresh |
| --- | ---: | --- | --- |
| Event payload/dispatch/value semantics | 57 | All seven pinned files unchanged | Passed, preserving CPU-only scope. |
| Tk input/camera delivery | 39 | All nine pinned files unchanged | Passed recorded toolkit-generated cases and recovery. |
| Reversed depth | 30 | Pinned test file unchanged | Passed analytic pixels/depth and loss cases. |

Evidence: [event packet](../compat/api-acceptance/event-values-v1.json),
[input packet](../compat/api-acceptance/tk-input-v1.json),
[depth packet](../compat/api-acceptance/reversed-depth-v1.json).

The earlier passes remain valid at their original identities. The identified
current-artifact verification gap is now closed for these subsets, with no
observed product failure.
Whether each scope blocks release depends on the selected claims; this review
does not turn optional breadth into mandatory scope.

**Completed action:** reused one bounded offline installation per platform to
rerun the existing **126 cases per platform**, verified package/loaded origins
and relevant shutdown gauges, retained results and cleaned both targets.
No native rebuild or new dependency environment was needed. The new packet
adds successor observations without changing old result identities.

The 32 older literal-sampler cases are already present in passing current
Windows 75-case / WSL 195-case shader JUnit results, with no missing node IDs.
Their rerun is already recorded in the
[dynamic sampler packet](../compat/api-acceptance/dynamic-explicit-samplers-wip.json).
Do not repeat them merely because their original standalone packet is older.

### 3. Medium: API breadth has discovery accounting but incomplete acceptance mapping

The canonical ledger remains `reviewed=false`. Its 142 seed parents comprise
25 app, 19 gloo, 22 scene and 76 visual entries. The retained discovery catalog
has 984 operation groups, all with `acceptance=unreviewed`, and 265 aliases.
The finite event overlay separately maps 38 groups/62 aliases. Source parent
reviews and reflection results do not establish all values, combinations,
inherited methods, events or render routes.

The discovery catalog also records the three examples as `executed=false` at
its original discovery epoch, whereas later exact-wheel runs execute the
maintained examples. This shows why the immutable catalog needs an additive
acceptance map rather than being read as a live pass/fail dashboard.

Evidence: [inventory](../compat/vispy-compatibility.json),
[method reconciliation](api-method-reconciliation.md),
[event mapping](../compat/api-acceptance/event-values-v1.json),
[maintained examples](../examples).

**Action:** map selected shared implementations and their aliases to finite
value/profile acceptance packets, with explicit supported/refused/deferred
dispositions. Preserve the original catalog and required obligations. Neither
984 nor 142 is a denominator for an overall support percentage; unreviewed
operations are not automatically missing implementations.

### 4. Medium: successful refusal tests do not close supported shader breadth

The seven new generated-line cases prove their specific diagnostics and
same-canvas recovery. Storage writes, atomics, image stores, barriers and early
fragment tests remain refused on those paths. Direct geometry shaders are
explicitly refused at LINK. Dynamic explicit sampler lowering selects only
one-dimensional arrays and its listed operations; broader implicit derivatives,
helper forms, multidimensional runtime indexing and mip/filter combinations
remain bounded or unsettled.

Evidence: [seven-case packet](../compat/api-acceptance/line-side-effect-boundaries-v1.json),
[line-side-effect guards](../cpp/shader/line_consumer.cpp#L596),
[geometry refusal](../cpp/runtime.cpp#L7669),
[dynamic lowering](../cpp/shader/normalize.cpp#L722),
[sampler scope](dynamic-sampler-indexing.md).

**Action:** retain the green diagnostic/recovery subset and the open SHD-01–05
parents. For an actual required consumer, select a narrow supported expansion
or document its rewrite/refusal. Avoid broad compiler changes solely to make
the parent checkbox green.

### 5. Medium: scene/host lifecycle combinations remain a high-value test target

The source reviews explicitly leave rendered picking/clipping, nested widgets,
camera changes, reparenting, timer-driven cameras and shared lifetimes as finite
acceptance work. The three maintained Tk examples cover selected image, mesh
and volume behavior; they do not establish all Qt host/scientific combinations.
The scientific fixture history includes valuable older artifacts and should be
reconciled per selected workflow rather than replayed as current coverage.

Evidence: [scene review](scene-coverage-review.md),
[visual review](visual-coverage-review.md),
[scientific fixtures](superpowers/plans/scientific-fixture-coverage.md),
[lifecycle worklist](remaining-gaps-checklist.md#lifecycle-capture-input-and-known-issues).

**Action:** after refreshing existing suites, select one real Qt scene workflow
with independently expected output, data/transform mutation, input delivery,
resize/reparent, loss/close and resource retirement. Add a second 3D/camera
workflow only if its claim is needed. Reuse existing scene/backend mechanisms.

## Recommended order

1. **Complete:** refreshed the three older finite suites on current wheels:
   126 cases per platform, reusing existing artifacts and dependencies.
2. Complete current independent review, strict installed profile evidence and
   selected CI/promotion gates for the successor release.
3. Add a finite real Qt scene lifecycle workflow where required by product use.
4. Extend the additive method/value/alias acceptance map while selecting the
   next consumer-driven rendering subset.

Keep the rare Windows startup stall under its existing recurrence policy.
Keep Metal experimental, native Linux physical GPUs unqualified and other
deferred platforms outside the selected release scope. Full upstream parity
and lab-grade input-to-visible equality are not completion requirements.

## Audit retention

The source-only audit, source-pin checks, older/current sampler node comparison,
matrix artifact tally and empty-attempt checks are retained in
`D:/vispy-vulkan-managed/build/runs/coverage-gap-review-433/` as `audit.py`,
`review.json` and `verification.json`. No scratch, build, installation or
functional test execution was created for this review.
