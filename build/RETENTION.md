# Local build retention

Follow ../AGENTS.md, ../docs/build-hygiene.md and the versioned limits in
../compat/build-hygiene.json. New scratch belongs in registered build/work runs;
retain terminal evidence outside scratch and apply a verified cleanup plan.

Keep current Windows/Linux artifacts, original licenses, qualification/failure
records and exact source/SDK origins. The current Windows SDK verifier pins
line-helper-dependency-work-1/o1 and
line-helper-sdk10-execution-work-5/relocated-sdk-1 by physical identity.
The older native-sdk/windows-x64-release-3 also supplies current verifier inputs.
Do not move, replace or deduplicate these origins.

Superseded successful histories no longer retain every original payload path.
legacy-retirement68-result.json records removal of 74,755 duplicate files and
14,509 empty directories, with an estimated 6.75 GiB reclaimed file allocation.
The exact legacy-retirement68-plan.json maps retired paths to retained identical
content; restore explicitly before deliberately replaying an affected old run.
Small historical reports, meaningful failures and original licenses remain.
hygiene70-integrity.json verifies all 3,970 retained hashes, 69 unique current
matrix references and nine final assets after retirement. These receipts live in
opengl-removal-execution-root-1. Older physical-space64-audit.json is a baseline,
not a current post-retirement total. Do not sum logical sizes of hardlinked files.

compiler-retention67 candidates remain present; no terminal receipt exists for
the uncertain compiler69 invocation. Do not count savings or repeat it blindly.
Previously automatic-review-rejected targets remain blocked, including child
paths and parent worktrees. build/.hygiene/registry.json carries the current
protected/blocked sets; preserve the original rejection records. Never edit
shared immutable payloads in place: use an independent copy for a new experiment.

Run `legacy-project-cleanup-945` (`D:/vispy-vulkan-managed/build/runs/legacy-project-cleanup-945/`):
plan `cleanup-plan.json` (`8cc281b505ec32b9cba85bed03d505cb0b8aca6856fbdde36a82d147192b4e2e`),
receipt `result.json` (`5d9b772d7121b538854dafdd6eebc8a894291312f55503c373bdf5bebc0a0fd9`), and
post-cleanup verification `verification.json` (`f9de0fc380e41d39e6af889dc91ce626aced2922cf7661637919e918ae81f045`)
record the removal of 9,655 unreferenced build/cache clutter files (9.1424 GiB logical,
7.9153 GiB physical; 7.94 GiB reclaimed on `C:\`) and 4,984 empty directories with 0 overlaps
against all protected/blocked registries, `compiler-retention67`, `legacy-retirement68`,
and current matrix/bundle/run references.
