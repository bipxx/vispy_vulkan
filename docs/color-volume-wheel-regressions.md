# Installed color-volume regression plan

The original scientific release requirements include legal RGB and RGBA volumes.
This packet adds24 public VolumeVisual cases: both color forms for all seven
exposed scalar rendering methods; opaque and low-alpha RGBA MIP controls; RGB and
RGBA plane depiction, linear sampling, public color updates, and transitions in
both directions between three and four channels.32-cubed asymmetric ellipsoids
carry independent red/green/blue values. A grays colormap makes unintended
luminance mapping visible. The RGBA iso threshold is fixed at.25, between the
analytic background and positive opaque-color luminance times alpha.

Author inputs, CPU controls, source freeze and read-only review precede either
renderer. Capture all24 originals in fresh installed official VisPy0.17.0/PyQt6
workers before any candidate, using the hash-locked NumPy2.4.6 runtime. Persist
full RGBA arrays, GLIR, expanded shaders, parameters and every before-frame.
Require independent RGB-plane face landmarks, nonblank distinct color channels,
visible public update changes, implicit RGB alpha equal to explicit opaque RGBA,
and a visible low-alpha difference. An original failure blocks every candidate;
retain its failure and do not weaken the criterion after observing pixels.

Then run the same24 cases in separate fresh workers installed from the archived
Native58 wheel. Every final RGBA byte, before-frame and parameter must match the
admitted original exactly, with no alignment, excluded pixel or color fit. All
cases remain required on failure. Verify all installed wheel members, actual
native module origins, positive draw/pipeline/queue work, the Vulkan hardware
identity, actual worker termination and all eight zero shutdown counters. New
external environments/cache are removed only after workers are terminal.

This is a finite Windows CPython3.12.8/NVIDIA color-volume packet. It does not
qualify other drivers, bindings/platforms, arbitrary color volumes, full volume
semantics, performance or release completion. The original scalar/categorical
fixtures, thresholds, reference files and smooth-line failures stay unchanged.
AGPL and original BSD notices remain attached. No native source/binary changes,
protected/heldout access or retry of refused cleanup is part of this packet.


Source review corrections before any graphics
---------------------------------------------

Review1 asked that RGB semantics be verified in the actual frozen wheel rather
than recalled from older VisPy versions. Official wheel c4862155... contains
vispy/visuals/volume.py SHA256
923a9ee775bc83825321317c098bee63716d6cb5aa96cfab2e1a8fe5ba83d240.
Its set_data sets u_rgb_mode=1 for3/4channels. colorToVal explicitly uses
RGB dot(.2126,.7152,.0722) times alpha in that mode. applyColormap returns the
per-channel clim/gamma-adjusted color directly, bypassing cmap. Thus color
landmarks and luminance*alpha threshold checks are intentional upstream semantics.
MIP/MinIP choose sample locations by that scalar and then recover their actual
sample color; attenuated MIP scales the selected color; translucent/additive
integrate colors; average averages colors; iso shades a threshold-crossing color.
Each path ends in direct color or applyColormap, which preserves RGB mode.
No fixture criterion changes follow this source check. Both RGB and RGBA iso
crossings are now CPU-checked against the actual shader quantity.

Official TurntableCamera says zero elevation/azimuth points along+y. The frozen
PerspectiveCamera (dd43cc06fd520ba535bb50cf5d3d84bbffe4d96c5cac6adc68665e65507ee54b)
_get_dim_vectors returns up+z, forward+y, right=cross(forward,up)=+x. Orthographic
scale_factor40 and square96 viewport give world_x=15.5+(pixel_x+.5-48)*40/96,
world_z=15.5-(pixel_y+.5-48)*40/96. The full3x3 patches at x32/64,y48 map into
the red/green ellipsoid interiors, respectively. Plane position components are
all15.5 and normal(0,1,0), invariant under xyz/zyx reversal. A CPU control derives
these neighborhoods directly. The four exact frozen upstream sources are retained
under the private prep upstream-source tree for review; original notices remain.

Source2 checks every installed archive payload, including dist-info metadata,
wheel tags and licenses. The sole exclusion is dist-info/RECORD, rewritten by
the installer to add its generated files; installed version is also checked.
The native-origin inventory uses the package payload subset. Both graphics
paths require the RTX4090 identity. The original GL path also requires
driver610.88; the candidate checks backend/vendor/device and records its driver.
Cache cleanup failures are recorded before the outer result is written. Cases
lacking verified worker results are explicitly listed; none becomes a skip.


The first Source2 upstream attempt completed all24 workers and failed every3D
texture setup because the minimal closure omitted PyOpenGL. All worker origins
and termination checks pass, environment/cache are removed, and no candidate
runs. Saved failure build/color-volume-wheel-prep-root-1/saved-failure1.json
preserves this dependency failure. Source3 adds only PyOpenGL3.1.10 from the
same existing hash-locked closure and records its installed version. The runtime
now has nine distributions. Inputs, thresholds, landmarks, public APIs and all
pixel/parameter/before-frame criteria retain their exact Source2 bytes. A new
reviewed source and new output root are required before the corrected pair.


Verified result
---------------

All24 fresh originals and all24 installed Native58 candidate cases pass on the
observed Windows CPython3.12.8 / NumPy2.4.6 / RTX4090 cell. Independent saved
inspection recomputes exact equality for221184 final pixels and36864 before-frame
pixels, all four channels. It checks process joins for48 actual case
workers plus two actual parent suites, installed payloads, native origins,
positive native work and eight shutdown zeros. Both environments and the owned
cache are removed. Full saved result: build/color-volume-wheel-run-root-2/result.json,
SHA256e2941b9d7e9f896b6e8600a3d082f9ff111b348924c50410fd036098b8bdd346.

The portable tests/reference/color-volume-opengl packet contains149 unchanged
original files, manifestc8af8d76e1ecdaac1e21303a47ba75a7cce83cb269085a230e89cf0f127c4337.
The source fixture/runner and the original runtime closure are repository files;
no runtime build/ dependency is required. The24 mandatory tests are in
tests/contract/test_color_volume_wheel_parity.py. Set VISPY_TEST_WHEEL to the
candidate artifact and optionally VISPY_COLOR_VOLUME_EVIDENCE to a fresh output
path, then run that file with pytest. Missing artifacts, unqualified hardware,
missing results or any color mismatch fail rather than skip. This packet remains
specific to its admitted cell; extending all ABI/binding/platform rows remains
part of the original release scope. CPU CI adds its51 controls to the existing
166 in every unchanged20-row CPU matrix. The GPU packet is an explicit entry
point; it is not newly claimed as all-platform hardware CI coverage.


The pytest entry point also requires Windows CPython3.12.8 and enforces the
parent suite return code, complete-pass status, opacity control and absence of
missing results or parent errors. Six CPU controls ensure passing worker rows
cannot hide a parent cleanup/seal/control failure. The saved GPU evidence is
from the actual48-worker driver; the pytest entry point is collected and its
parent gate is CPU-tested, not separately replayed on GPU after publication edits.
Use a byte-exact checkout (core.autocrlf=false); Git must preserve all pinned
source and reference bytes. The CI checkout already enforces this policy.
