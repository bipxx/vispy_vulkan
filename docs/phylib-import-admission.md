# phylib Linux import-only admission

phylib 2.7.1 has an admitted Linux x86_64 / CPython 3.12.8 CPU import cell. This
is the electrophysiology library, separate from the phy GUI. It does not import
VisPy or Qt and has no rendering workload. The `linux-x11` directory name follows
the existing host-matrix naming; this import-only cell requires no X11 display.

The existing source commit and source/package hashes in `compat/hosts.lock.toml`
remain unchanged. `phylib.linux_environment` adds a Linux binary-wheel dependency
lock and a recorded import inventory alongside the retained Windows inventory.
The lock constrains dependency versions to the existing Windows pins and retains
the same 2026-10-09 cutoff. Every dependency is installed with required hashes.

`tools/phylib_import_cell.py` verifies the complete original source and package
trees, copies the unchanged package into a fresh dependency environment, and runs
all twelve original import probes. It verifies package version and byte identity,
isolated module origins, zero import errors and no loaded VisPy/Qt modules. The
source copy creates no distribution metadata; CI verifies the actual source and
imports instead of requesting metadata that was never installed.

The completed WSL Linux run passed all twelve probes. Independent saved
inspection joined every imported module hash to the original source. All three
actual child processes were waited on, and the newly owned environment was
removed. This proves CPU imports only. Vulkan, Metal, GUI behavior, scientific
rendering and release qualification remain separate requirements.

The formal cell is at
`compat/qualifications/phylib/linux-x11/3.12.8/none/admission.json`. The admission
gate requires the hash-verified completed inventory and validates its exact probe
list, source/package identity and import-only flags. The reusable
`.github/workflows/phylib-import.yml` repeats installation and probes on its
Ubuntu runner when its inputs change, and the manual host matrix calls the same
job. This CPU workflow runs independently of the hardware renderer matrix.
Missing dependencies
or failed imports fail the job. No GPU admission is granted to phylib.

To repeat in a fresh Linux CPython 3.12.8 virtual environment, install
`compat/host-environments/phylib-linux-cpython312-cpu.txt` with `uv pip install
--require-hashes --only-binary :all:`, fetch the original source with
`tools/host_inventory.py fetch --host phylib --directory <fresh-source>`, then run:

```sh
<venv>/bin/python -I -B tools/phylib_import_cell.py \
  --source <verified-extracted-source> --output <new-import-inventory.json>
```

New implementation code is AGPL-3.0-only. The original VisPy BSD license and
third-party notices remain attached and unchanged; upstream host source retains
its own original license and notices.
