# Exact plugin test inputs

These small third-party artifacts make the installed-wheel plugin test independent
of a developer's build directories. `manifest.json` binds every artifact to the
exact bytes used in the completed frozen Windows observation. The runner still
creates fresh environments and captures all original frames before candidates.

The genuine napari-threedee 0.0.29 wheel retains its original embedded license,
also attached here as `napari-threedee-LICENSE.txt`. The asciitree 0.3.3 wheel was
built from the attached, hash-locked upstream source. Its package and license
files are byte-identical to that source. Its original license is embedded in the
wheel and attached as `asciitree-LICENSE.txt`.

`asciitree-build.json` and `asciitree-build-source.txt` retain the original build
record and script as evidence. Historical paths in those records describe the
completed build; the runtime does not open them. The build uses the attached
source hash, locked setuptools/wheel profile and fixed source-date epoch.

Upstream licenses remain unchanged. The implementation's AGPL license does not
replace them. These inputs grant no renderer, host-cell or release qualification.
