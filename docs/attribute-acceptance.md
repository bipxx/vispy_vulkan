# Finite matrix and array attribute acceptance

The [acceptance packet](../compat/api-acceptance/attributes-v1.json) binds 285
passing cases per platform to Windows wheel `ba8a54c5` and WSL manylinux wheel
`4bc3cd77`. No native build or new environment was needed. Separate 282-case
and three-case boundary executions retain their exact source epochs. The two
original rendering function ASTs remain unchanged after adding boundary tests.
All 537 installed members and loaded origins match; ten shutdown gauges are
zero on every run. All scratch targets are removed and evidence rehashed.

The baseline includes 275 CPU cases: 87 matrix packing, 91 array packing and
97 composed-input cases. They distinguish column words, vertex counts, stride,
offsets, constants, buffer replacement/subupdates, endian/type/shape refusals,
divisor inheritance and unchanged values/cache identity after rejection.

Four rendered geometry cases use an independent pixel-center inverse of a
non-symmetric mat3x2 transform. Separate/interleaved records and divisors 1/2
place distinct instances; partial updates change one instance record; forced
device loss preserves the updated output. Exact whole-image masks avoid samples
on polygon edges. Three retained aggregate groups add 149 raw, three indexed
and 207 composed pixel observations per platform. These cover nine float matrix
shapes, selected nested vector/matrix/signed-integer arrays, triangle/point/line
routes, updates, rebuilds and uint16 indexed comparisons. Their center-byte
comparisons permit one unit of quantization; they are not whole-frame proofs.

The three boundary cases distinguish routes. Triangles and points reject one
extra location, then recover on the same canvas using every location of the
actual 30-location grant. Generated width-5 lines evaluate inputs in compute:
31 logical locations render successfully, then a 30-location shader renders.
Compute/storage grants govern that route. The first fixture incorrectly applied
the raster limit to wide lines; its failure, source and correction are retained.
Production code and verifiers were unchanged by that fixture correction.

The current native builds' artifact contract also checks exact matrix-column
and array location expansion, word offsets, binding views, physical reflection,
dead input compaction and atomic malformed/overflowing-shape refusal. The
called header and caller hashes match the Windows before/after source map and
Linux preferred source archive. Both linked native builds passed all 44 native
contracts. This compiler evidence supplements the distinct CPU/GPU observations.

SHD-03 remains open for additional combinations, compute/storage limits, MSAA,
other hardware/profiles and independent admission. Unsigned vector reflection
does not establish every unsigned value/output form. These finite observations
do not qualify a strict profile or constitute full attribute parity.
