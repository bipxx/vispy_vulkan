# Volume scientific admissions

`tools/volume_scientific_admission.py` joins the actual 24 large-volume
benchmark workloads to the 17 independently captured scalar and categorical
controls. It reads saved raw artifacts without importing VisPy or a provider.
The qualified cell is Windows CPython 3.12.8, NumPy 2.4.6, PyQt6 and the
Native58 candidate on the RTX 4090 with driver 610.88. Other cells remain open.

The small controls were rerun unchanged in NumPy 2.4.6, rather than reusing the
earlier NumPy 2.5.3 run. All 17 match their pinned original OpenGL references
exactly across 156,672 RGBA pixels. They cover categorical background and label
IDs, clipping, mesh depth, and the existing MIP/iso numeric and plane controls.
The 24 full-size candidate captures retain the original whole-frame error
limit of 2, exact unchanged repeats and both visible-change checks. Each joins
the same complete 550-file installed candidate package fingerprint and wheel
digest. These bounded controls do not establish arbitrary scientific behavior.

Portable raw evidence is retained in
`tests/reference/volume-scientific-controls-numpy246` (manifest SHA256
`e9f2ef17e59a222372a4588dd5faa639f73beab0a8ad41e6713625864bbd406f`)
and `tests/reference/large-volume-native58` (manifest SHA256
`e3f285bcbf97d4a40cb75e031bda9c23abf5fc5d35cf2ad6047c0c8ada9cd576`).
The unchanged large originals remain in `tests/reference/large-volume-opengl`.
Every admission also lists the original small-control artifacts, their producer
sources, runtime profile and original BSD and AGPL notices directly.

The current records are in
`compat/scientific-admissions/volume-native58-cp312-numpy246-v5`.
`quality-plan.json` maps all 24 workload names to their admissions;
`qualification.json` binds their digests and explicitly disclaims performance
and full release qualification. Earlier local admission sets remain historical:
the first lacked direct original-small-control links, and the second omitted
their oracle producer files from its evidence closure. v3 preceded the review
hardening. v4 stopped before writing admissions at an incorrect equality between
the launcher and child PIDs; v5 checks their actual parent/child relationship.
Use a fresh output path for regeneration and preserve prior results:

```powershell
.venv/Scripts/python.exe -I -B tools/volume_scientific_admission.py --output <fresh-directory>
```

Optimized Python is refused because it disables assertions. Records are staged
in a sibling `.pending` directory and published by renaming only after all 24
cases and schema checks succeed. Failed pending directories remain for diagnosis;
consume only completed directories with `qualification.json`. Output must be on
the repository's filesystem volume, and portable copies must preserve the
relative layout of the records and every declared evidence file.

Small-control execution and the complete installed-file fingerprints are
attested by the pinned worker reports and audited capture sources. Their raw
GLIR draws and shaders are retained and checked, but the small runs did not
record independent native draw/queue-submit counter deltas. The exact launch
driver is retained as `driver.py` in the control bundle for inspection; its
historical build paths are not used by the saved verifier. The original wheel
archive itself is not part of this portable packet.

The existing benchmark admission schema and evidence hashes are checked with
input-identity records when producing these files. Those records are CPU schema
checks, not captured timing runs. `measurement_identity` additionally requires
an actual timing run's complete installed package fingerprint, wheel digest,
input digest and Python/NumPy cell. The old benchmark's seven Python source
hashes cannot satisfy this check. Its timing adapter has not yet been wired to
provide and enforce the stronger identity.

Before performance qualification, the original renderer's unchanged repeated
96-byte vertex and 56-byte index uploads need a narrowly attested measurement
allowance. Their actual work and time must remain in the baseline. The candidate
resident counters must stay zero. Full 100-warmup/1000-measured-frame, five-pair
timings, the 20% resident speedup target, p95 and update limits, presentation,
other platforms and the full release remain pending.

The implementation is AGPL-3.0-only. The original VisPy BSD license, copyright
and disclaimer remain unchanged and attached; see `LICENSING.md`.
