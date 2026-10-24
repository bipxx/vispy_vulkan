# Build and experiment hygiene

Read [docs/build-hygiene.md](docs/build-hygiene.md) before native builds, package
installation, source snapshots, large experiments or installed-artifact checks.
The versioned limits are in `compat/build-hygiene.json`.

- Use one coordinator-selected storage root and budget across agents. Register a
  unique owner/run with `tools/build_hygiene.py preflight --register` before
  creating writable scratch. Keep scratch in `build/work/<run-id>`; do not start
  another unmanaged top-level build directory or temporary virtual environment.
- Reuse a matching qualified wheel, SDK, locked environment and immutable source
  archive. A documentation, test or report change alone is not a reason to
  rebuild a native wheel or clone its dependency/source history.
- Never recursively copy old `build/`, evidence directories, environments or
  provenance payloads into a new run. Reference retained inputs by hash. Keep
  preferred sources, patches and original licenses once per distinct input.
- After every terminal run, retain the source, evidence, licenses and necessary
  artifacts outside scratch. Failed/cancelled runs also need a reproducer.
  Record the actual exit and child wait. Generate a cleanup plan, apply it, and
  report its result before handing off or starting the next experiment.
- Preserve meaningful failures and current qualification evidence. Superseded
  successful experiments need small reports and reconstruction references, not
  another live copy of every dataset, compiler cache or SDK.
- Never move, replace or deduplicate identity-pinned dependency origins. A legacy
  cleanup needs a dependency audit and an exact plan; the managed tool does not
  adopt legacy directories. Do not weaken an existing verifier to make cleanup
  pass.
- Never retry automatic-review-rejected cleanup targets, including through a
  different shell, child path or parent directory. Load the local protected and
  blocked registry for every managed cleanup. Preserve the rejection record.
- Disk-budget failures stop new work. Large dependency builds need an explicit
  documented policy profile, not a force flag or silent limit increase. WSL
  builds must check the guest filesystem and the Windows backing volume.
- Use existing test environments and disable incidental bytecode/cache output
  for one-shot checks where practical. Small source-only tests need no native
  build lease, source clone or new virtual environment.

User instructions take precedence over these project defaults. Follow existing
ownership boundaries and preserve other agents' edits. Hygiene work does not
authorize unrelated deployment, messaging, cybersecurity work or release-scope
changes.
