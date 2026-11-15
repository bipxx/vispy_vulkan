# Historical Evidence & Prior-Packet Causal Reuse Dispositions

Date: 2026-11-15 (Wave 2 Slice `W2-1`, run `gap-forensics-reuse-959`).

## 1. TOOL-03 (B17) — Historical Compiler-Cache Receipt Disposition

- **Inventory**: `build/opengl-removal-execution-root-1/compiler-retention67-candidate-files.json` (`100a056d7dcf9759be913692088c6ec6c23342b86ef5c44104cdc56a420e0a87`)
- **Verified entries**: `12134 / 12134` retained byte-for-byte (`2,138` `.obj`, `9,996` `.tlog`, `2825459986` logical bytes across `31` `native-pass24..57-sdk` roots; `0` missing, `0` mismatched).
- **Missing B17 receipt**: `compiler-retirement69-result.json` (`apply-compiler-retirement69.ps1`) is `missing-historical-unpromoted` with `0` reclaimed bytes claimed.
- **Integrity**: `hygiene70-integrity.json` (`24b5e45bf74091087385ede7c8c62c69d6a7500b31f7f44c2ebdf1c53d21719a`) and `tools/build_hygiene.py` (`0a4f8cbc161afa39dfaf25e840bb0c788fda4f709b84f7440bd52102f847fa84`) unchanged; `verify-hygiene70.py` not executed; `0` overlaps with `legacy-project-cleanup-945`.
- **JSON**: [tool03-historical-receipt-disposition-v1.json](../compat/api-acceptance/tool03-historical-receipt-disposition-v1.json)

## 2. BUG-02 (B12) — Historical PyQt5 OLE Hang vs Startup Stall

- **Disposition**: `separate-historical-unreproduced-preserved`.
- **Classification**: `BUG-02` records the historical intermittent Qt5 OLE `RegisterDragDrop` / `RoGetAgileReference` / ALPC RPC hang (including concurrent `repro5` QWidget stall), distinct from the proved/fixed Windows observer INT3 resolver-ownership race (`windows-resolver-race3/controls.json`) and separate in profile from `BUG-01` (`B22`, default thread-pool worker-factory handle loss, D33 watcher-only).
- **Current candidate**: Does not block `tk-state-resource-16`; original evidence refs preserved in `docs/threedee-startup-diagnosis.md`, `docs/opengl-removal-status.md`, and `docs/superpowers/plans/2026-10-28-consolidated-plan.md`.
- **JSON**: [bug02-ole-hang-disposition-v1.json](../compat/api-acceptance/bug02-ole-hang-disposition-v1.json)

## 3. PERF-04 (B14) — Historical 16 Review-Finding Regressions & Cold-Build Claims

- **Disposition**: All 16 historical review-finding regressions from `2026-10-09-vispy-vulkan-completion-plan.md` are reconciled against current test/lifecycle/shader/state suites and are not active unaddressed runtime regressions.
- **Wheel-reuse workflow**: Current CI (`qualification-ci.json`) runs in 1 GiB wheel-reuse mode over unchanged 133 C++ inputs (`93241ed251ce3d75d9c346ea7abcf02c51cc7c4ac0450921e5e4489cd078e4af`) and reused `_dawn` binaries (`057d13e6...` / `fcf0c5a8...`); cold-build/peak-memory benchmarking remains unselected.
- **JSON**: [perf04-cold-build-reconciliation-v1.json](../compat/api-acceptance/perf04-cold-build-reconciliation-v1.json)

## 4. TOOL-01 — Metal Reuse Audit Check

- `compat/qualification-ci.json`: `ce789d69999363f097af2229f0eac301d056cabb971a5b26ba2fd0df4341dd41`
- `cpu-contract.yml`: `bab17b8057bfbcd254cd7781c12de411bd05bfb2805093881ddaa0f75f155027`
- `linux-vulkan.yml`: `84f8760e72dbcee78ade8a3750e8e239ab863f875d7b899ea5f5fadd9f9d01cd`
- `metal-wheel.yml`: `6c051d233db4752d8cda90545398f51d678e55e4737626fbce5a8a4f634b8a97`
- `orphan-release-metal-reuse-pin-v1.json`: `7263d329b20f63e6ca195b625a8e45df25c409340cb61d46965edfd570c0cd95`

## 5. API-06 — Causal Input-Hash Reuse Table (`9919a280` / `e600b29e`)

- **Candidate vs Prior Release (`4f537748` / `dfe1033f`)**: Exactly `1` of `537` runtime members changed (`vispy/gloo/dawn_parser.py`).
- **Candidate vs `ba8a54c5` / `4bc3cd77`**: `9` runtime members changed on Windows (`_dawn`, `VkLayer_vispy_submit.dll`, `_sdf_cpu`, `_dawn_tk.py`, `_qt.py`, `canvas.py`, `dawn_parser.py`, `glir.py`, `wrappers.py`) and `7` on Linux.

| Workstream | Prior Wheels | Disposition | Basis |
| --- | --- | --- | --- |
| `SHD-01` | `5cb463cd, b4c72484` | `requires-fresh-installed-execution` | Native _dawn module, dawn_parser.py, glir.py, and wrappers.py changed between 5cb463cd/b4c72484 and 9919a280/e600b29e (deferred to Slice W2-3). |
| `SHD-02` | `ba8a54c5, 4bc3cd77` | `requires-fresh-installed-execution` | Native _dawn module, dawn_parser.py, glir.py, and wrappers.py changed between ba8a54c5/4bc3cd77 and 9919a280/e600b29e (deferred to Slice W2-3). |
| `SHD-03` | `ba8a54c5, 4bc3cd77` | `requires-fresh-installed-execution` | Native _dawn module, dawn_parser.py, glir.py, and wrappers.py changed between ba8a54c5/4bc3cd77 and 9919a280/e600b29e (deferred to Slice W2-3). |
| `SHD-05` | `ba8a54c5, 4bc3cd77` | `requires-fresh-installed-execution` | Native _dawn module, dawn_parser.py, glir.py, and wrappers.py changed between ba8a54c5/4bc3cd77 and 9919a280/e600b29e (deferred to Slice W2-3). |
| `STA-02` | `5cb463cd, b4c72484, ba8a54c5, 4bc3cd77` | `requires-fresh-installed-execution` | Depth/viewport state execution routes through _dawn, dawn_parser.py, glir.py, and wrappers.py which changed since ba8a54c5/4bc3cd77 (deferred to Slice W2-2). |
| `API-05-EVENT-VALUES (pure CPU subset)` | `5cb463cd, b4c72484, ba8a54c5, 4bc3cd77` | `reusable-by-input-hash` | vispy/util/event.py, vispy/util/keys.py, and vispy/scene/events.py are byte-identical across 5cb463cd/b4c72484, ba8a54c5/4bc3cd77, 4f537748/dfe1033f, and 9919a280/e600b29e; canvas.py-dependent subset remains requires-fresh-installed-execution. |
| `LIF-06-TK` | `5cb463cd, b4c72484, ba8a54c5, 4bc3cd77` | `requires-fresh-installed-execution` | _dawn_tk.py, canvas.py, and _dawn changed between ba8a54c5/4bc3cd77 and 9919a280/e600b29e; tk-state-resource-16 subset already re-verified in 936/937/942/943/944/945. |
| `ORPHAN-RELEASE non-dawn_parser proofs` | `4f537748, dfe1033f` | `reusable-by-input-hash` | 536 of 537 runtime members are byte-identical between 4f537748/dfe1033f and 9919a280/e600b29e; only vispy/gloo/dawn_parser.py changed. |

- **JSON**: [api06-unchanged-proof-reuse-v1.json](../compat/api-acceptance/api06-unchanged-proof-reuse-v1.json)
