# Qualified Tk compatibility baseline

The current practical baseline uses VisPy's public Python interfaces with Vulkan
rendering and Tk raster presentation. Some VisPy compatibility is required:
claimed workflows preserve familiar calls, data, events and observable behavior.
Intentional differences and improvements must be documented and tested. Full
upstream API, backend and pixel parity are not release requirements.

## Verified milestones

| Milestone | Published source | Evidence boundary |
| --- | --- | --- |
| State/resource baseline and readback validation | [PR #15](https://github.com/bipxx/vispy_vulkan/pull/15), merged as `c80de037a44377d7e617f57c17d32edbe78e7df1` | Fifteen finite features, 120 selected criteria across the two profiles, installed-artifact admission, independent review and 23 required CI jobs. |
| Cropped byte/float capture | [PR #17](https://github.com/bipxx/vispy_vulkan/pull/17), merged as `48df4b47b5ab5d4428e1207d0597363257d03f7a` | A separate eight-criterion installed admission on the same wheels, with independent review and 23 required CI jobs. |
| Separate-face stencil operations | [PR #16](https://github.com/bipxx/vispy_vulkan/pull/16) | Finite source regression evidence; no new installed stencil admission. |

The first milestone covers manual application pumping, basic canvases, current
and shared contexts, injected device-loss recovery, one-shot timers, submission,
selected raster state, readback and shared Program/Texture/VertexBuffer lifetime.
See the [feature table and differences](practical-compatibility-release.md) and
[capture contract](cropped-capture-compatibility.md) for the actual limits.
The two admissions retain their own source and evidence identities; they are
not one combined current 128-criterion admission.

The companion both-face stencil, PanZoom drag/resize/cancellation, cursor-anchored
wheel zoom and orthographic Turntable yaw tests are published in
[PR #18](https://github.com/bipxx/vispy_vulkan/pull/18), merged as
`a8378722dec6651760fb0e205f66e47421f371bf` with the exact tested source tree
and all eleven required source-merge checks passed. They are finite source
tests, not installed camera qualification or whole-image parity.

## Exact admitted wheels and profiles

| Profile | Wheel | SHA-256 |
| --- | --- | --- |
| Windows x86-64, CPython 3.12.8, Tk 8.6, NVIDIA RTX 4090 Vulkan | `vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl` | `444402459f79465fb1cb42b0dea55fb7e66ce73c22df9e96017f437786ce0d56` |
| WSL Ubuntu x86-64, CPython 3.12.13, Tk 9.0.3, Mesa 26.1.8 software Vulkan | `vispy-0.17.0+vulkan.1-cp312-cp312-linux_x86_64.whl` | `bd89a9944c71fb3b40260a3197c8f436e7a29021e485ff5f4a561fed907f844a` |

These are exact tested environments, not a claim about every CPython 3.12,
Tk, GPU or distribution combination. WSL software results do not qualify native
Linux GPU hardware. Metal graphics remain experimental.

Tk displays RGB through a CPU-memory copy into a PhotoImage. This mode does not
promise Vulkan window presentation, vsync or transparent window composition.
RGBA capture is separate. Device-loss recovery uses explicit injection and
recreation; camera source tests use generated events and manual pumping rather
than physical-device or mixed-monitor DPI qualification.

## Obtaining and reproducing the baseline

The retained wheels are local qualification artifacts under
`build/artifacts/<sha256>/<wheel-name>`. Build outputs and raw local evidence
are excluded from the source repository. This page does not announce public
downloads of these wheels or a complete offline Tk installation bundle.
The older [Qt bundle guide](offline-install-cp312.md) identifies different
artifacts and cannot supply these Tk profile qualifications.

For source development, follow the [build instructions](../cmake/README.md)
and [build storage policy](build-hygiene.md). A fresh build or ordinary package
installation does not inherit the retained installed qualification. Repeating
it requires the exact profile, member/license checks, functional/recovery tests,
observation controls, resource shutdown and reviewed admission evidence.

Maintainers can reconstruct the existing claims from
`build/runs/readback-promotion-129/milestone-handoff.md` and
`build/runs/capture-admission-151/milestone-handoff.md`. These are local evidence
entry points, not files supplied by a normal source checkout. The admitted
source heads are respectively `98694c6b7c9ed9befbfaf73e2f377d1516fca4c0`
and `27242b51f76eae5d96cc7163ee1af105f46f22ba`; each merge preserves its tested
complete Git tree.

Both wheels retain AGPL-3.0-only implementation licensing, the unchanged
original VisPy BSD license and original third-party notices. See
[licensing details](../LICENSING.md).

## Remaining delivery work

The [Tk distribution descriptor](../compat/distributions/tk-cp312-1/distribution.json)
and [installation recipe](install-tk-cp312.md) now identify the retained wheels,
exact dependencies and external runtime prerequisites. The descriptor remains
`PREPARED_NOT_DISTRIBUTED`. Its separate [archive record](../compat/distributions/tk-cp312-1/wheelhouse.json)
now identifies a 50,224,956-byte wheelhouse with two byte-identical assemblies,
verified payload hashes and six-package offline dependency plans per platform.
That record is `ASSEMBLED_NOT_PUBLISHED`; no public download is announced.
These assembly checks do not rerun installation or rendering qualification.
Preserve source and license references
without copying SDKs, environments or old evidence trees. Validate any assembled
bundle under the build storage policy. Public asset availability is a separate
deliverable from the completed rendering milestones.

Further API, shader, scene, host and backend coverage remains tracked in the
[active plan](superpowers/plans/2026-10-24-vispy-compatibility-gaps.md).
Unsupported breadth is visible backlog, not an assertion of full parity or a
reason to repeat already qualified native builds.
