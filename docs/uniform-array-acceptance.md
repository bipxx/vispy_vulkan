# Finite multidimensional uniform-array acceptance

SHD-02 remains open for other storage/interface classes and broader profiles.
The [Windows packet](../compat/api-acceptance/uniform-arrays-windows-v1.json)
records 120 passing cases on actual successor wheel `ba8a54c5`, without skips:
35 public Program shape/upload cases, 37 Variable/composition cases and 48
rendered composed-array cases. No native compilation or new environment was
needed. All 537 installed members and 151 loaded module origins match; ten
shutdown gauges are zero. Scratch is removed and retained evidence rehashed.

The CPU cases check whole/subarray/leaf assignment, dimensions versus equal
element counts, invalid-value preservation, shader replacement, cached write
order, compiler naming and interface metadata. Those checks establish public
metadata/upload semantics, not GPU reflection for every interface class.

The rendered subset is float/int/bool/vec3/bvec3/mat2/mat2x3/mat4x2 over shapes
[3], [2][3] and [2][2][3], using triangles and generated lines. Shared-stage
composition, name collisions, dynamic indexing and updates are compared with
independently supplied scalar values and visible landmarks. This does not
generalize to every numeric type, nested structure, SSBO, vertex attribute,
varying, array shape or loss scenario.

Linux CI `42381467559` has completed successfully for native source `f7d21c31`.
The imported native/source/archive joins and all 44 native contracts pass.
Final manylinux wheel `4bc3cd77` then passes the same 120 uniform cases inside
a 195-case shader process, with no skips, exact installed origins and ten zero
shutdown gauges. Its eight numeric types, three shapes and triangle/line scope
match the Windows fixture hashes. The [cross-platform packet](../compat/api-acceptance/uniform-arrays-v1.json)
links the unchanged original Windows observation and the exact Linux node IDs.
Linux includes 150 loaded VisPy origins under the checked target; Windows has
151. Both scratch targets are removed and evidence rehashed. This closes that
finite uniform subset on Windows and WSL, while other storage/interface classes,
additional shapes/types, independent review and profile admission remain open.
