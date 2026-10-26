# Exact archive and vendor SDK prerequisites

`tools/qualification_artifact.py` provides read-only H4 prerequisites, with closed
formats in `compat/qualification-artifact.schema.json` and the versioned policy
in `compat/qualification-producers.json`. No result from this tool admits a native
leaf, artifact, installed environment or hardware profile.

```powershell
python -B tools/qualification_artifact.py
python -B tools/qualification_artifact.py --archive path/to/archive-record.json
python -B tools/qualification_artifact.py --sdk path/to/sdk-reuse-record.json
```

Default policy checking keeps Windows vendor SDK reuse separate from native leaf
admission. Only the existing pinned Windows SDK manifest and compiler digest are
allowed. Linux's experimental producer stays blocked; Metal stays experimental.
`--sdk` delegates to the existing full `cmake/native_sdk.py` verifier, including
its complete SDK inventory, source lock, consumer settings and actual compiler
checks, then checks policy-verifier identity. It returns vendor-reuse-only with
native-leaf/artifact admission false. Unit tests mock that delegation explicitly;
this source packet performs no actual SDK qualification or build.

An archive record binds candidate scope, one selected profile, the exact wheel
and retained native output files. Candidate validation pins source/build/lock/
license inputs; profile ABI/architecture chooses the wheel filename, extension
suffix and WHEEL tag. Wheel/native and SDK proof references cannot use disposable
`build/work` storage. The audit reuses the runtime-package checker for complete
package membership and compares every shipped source, notice and native output
hash. It also checks the complete distribution inventory, original package and
dist-info license copies, unique Name/Version/AGPL metadata and the exact ABI tag.
Every RECORD row must name exactly one archived file with its actual SHA-256 and
size; RECORD itself has empty hash/size. An updated RECORD cannot hide changed
source/native/license bytes. The existing PE/ELF parser checks 64-bit x86-64
architecture without loading a library. Correctly rehashing an ARM native origin
cannot make it match the selected x86-64 profile.

Original notice inputs come from the shipping manifest; dist-info license inputs
come from the frozen project's explicit license-file patterns. The original BSD,
AGPL and explanatory licensing documents must remain byte-identical in both
copies. Source expectations are derived from retained project inputs, not from
an embedded wheel manifest alone. No archive is extracted, installed or executed.

`PASS_EXACT_ARCHIVE_PREREQUISITE` means byte/archive consistency only. It reports
producer admission, artifact admission and installed origin false. Hash equality
to a supplied native output does not establish how that output was compiled.
The complete native leaf build/compiler/configuration/source provenance and its
admission remain pending, as do original installed functional/absence/control/
shutdown proof, immutable subject/attempt/disposition and retention joins, CI/
promotion-basis review and H2 independent implementation/scope approval. No new
wheel or real producer-admission record is fabricated while those are missing.

CPU tests use tiny in-memory synthetic Windows/Linux wheels, including synthetic
native headers, explicit SDK delegation, and real original notice sources. They
reject altered source/native/license bytes after RECORD regeneration, incomplete
source/native/notice inputs, wrong architecture/ABI, duplicate metadata, wrong
AGPL metadata, extra members, malformed/missing/duplicate/incorrect RECORD rows,
experimental producer relabelling, unapproved SDKs and scratch-origin references.
These tests create no files, environments, installs, source snapshots or native
artifacts. Small terminal source/result/license references are retained locally
in `build/runs/archive-prerequisites-36/`; no managed scratch cleanup is needed.

Verification: 84 Windows CPU checks pass in 14.92 seconds; 79 WSL CPU checks
pass in 3.34 seconds. Both actual children exited zero and were waited. The
existing actionlint binary accepts all three workflows. These counts cover the
36 new artifact/SDK controls and 43 existing CI controls, plus five Windows
current-declaration checks. No native producer or installed gate was run.
