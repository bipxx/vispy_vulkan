# Required CI evidence joins

`tools/qualification_ci.py` validates `compat/qualification-ci.json` against the
current workflow bytes, collector and finite matrices: 20 CPU jobs, Linux
software Vulkan and two Metal wheel builds. Its closed formats are in
`compat/qualification-ci.schema.json`. CI success provides no artifact or
hardware admission. Metal build/CPU checks do not qualify Metal graphics.

Default validation is read-only:

```powershell
python -B tools/qualification_ci.py
python -B tools/qualification_ci.py --bundle path/to/ci-bundle.json
```

The first checks policy only. A bundle references complete original GitHub API
run history for one qualification head, every attempt's run/jobs exports and
per-job checkout reports, each by retained path and SHA-256. `total_count` must
match the complete exported arrays: an uncombined paginated first page fails.
Every required visible run and each attempt through its latest attempt must be
included. The policy selects the greatest run ID and latest attempt for each
workflow, requires its entire successful matrix and forbids cross-attempt mixing.
A newer failed/pending run cannot be omitted in favor of an older green run.
Original failed/cancelled attempts remain in the bundle, including early failures
with no checkout report or jobs. Such missing reports cannot satisfy the selected
successful matrix. Every retained attempt must be terminal. Full artifact promotion
also needs their reviewed dispositions; this CI join does not resolve product
failures merely because a later CI run passes.

Each original checkout report binds repository, run/attempt, job key and exact
matrix name, event, source head, tested commit, raw commit parents, workflow file
and collector hashes. A PR merge checkout must contain the source head as a
parent; direct source checkouts are allowed. Other events must test the source
commit itself. Reading raw commit headers preserves parents even in shallow
checkouts. All three workflows capture `ci-identity.json` with their existing
Python environments and retain it through existing evidence uploads.

The validator checks hash-bound original exports, not status-name summaries.
It does not query GitHub itself: complete export/discovery and the final review
of that external evidence remain necessary. Synthetic unit exports are not real
CI receipts. No real passing bundle or independent approval is supplied by this
packet. A changed policy, workflow, collector or qualification head requires
updated source/scope review and current-head CI; old green runs cannot transfer.

Verification: 48 Windows source checks (16.01 seconds), 43 WSL source checks
(1.79 seconds), and actionlint over all three changed workflows pass. Tests cover
required-job policy reduction, complete synthetic joins, wrong repository/head/
workflow/checkout/collector, pagination, missing or duplicated jobs, mixed and
omitted attempts, skipped/cancelled/pending/failed results, and original shallow
merge-parent capture. Five Windows checks additionally validate current real
candidate/coverage/execution/selection and unchanged original scope. The Windows
and WSL CI controls create no scratch/output files; the capture test intercepts
only its output stream. No wheel/SDK, environment, install or source snapshot is
created. Small source/result/license references are retained locally under
`build/runs/required-ci-35/`; no managed cleanup deletion is applicable.

Remaining H4 work includes the exact artifact/producer and original installed
gates, full product-attempt/disposition index, terminal retention join and the
immutable promotion basis/envelope. H2 independent source/scope review, installed
qualification, final current-head CI/review and all broad parity requirements
remain open. Product source remains `6345ceef42df1a64a7401a83c2d1a30384903cd1`.
