# Optional Numba CPU runtime closure

Numba 0.68.0 ships an optional Windows TBB extension with a `tbb12.dll` import.
Its pinned source requires interface version 12060 or newer. The reviewed
TBB 2021.6.0 core exports all 21 symbols required by the actual Numba extension
and returns interface 12060. The ordinary vendor wheel also contains unused
HWLOC binding plugins with unavailable dependencies; those are not selected.

`compat/dependencies/windows-numba-tbb.json` freezes the original vendor wheel,
unchanged core DLL, required ABI symbols, source guard, and original notices.
The original runtime retains its **Intel Simplified Software License**. The
profile producer and small DLL-directory registration module are AGPL-3.0-only;
the profile does not relicense the original binary or assume an Apache license.

The selected wheel registers its own runtime directory with Python's documented
`os.add_dll_directory` API using a process-owned cookie. It changes no application
functions, provides no fake modules, and loads no graphics implementation.
Fresh consumer tests explicitly select `NUMBA_THREADING_LAYER=tbb`, execute a
real parallel JIT calculation, check the result, interface version and loaded
DLL path/hash. Functional host/native qualification follows in a fresh consumer;
frozen environments are not changed.

```text
PYTHONPATH=tools python -B -m no_opengl.tbb_profile --manifest compat/dependencies/windows-numba-tbb.json --source <pinned-original-wheel> --output <new-profile-directory>
uv pip install --python <fresh-consumer-python> --no-index --find-links <profile-directory> --require-hashes -r compat/dependencies/windows-numba-tbb-requirements.txt
```

This is an explicit derived dependency sub-lock. Existing Numba, NumPy and
llvmlite pins remain unchanged. It provides the CPU scheduler core, not optional
HWLOC topology/NUMA binding or alternate-allocator plugins. Linux uses separately
pinned standard `libgomp1`/`libtbb12` package closures; it does not use this wheel.
