# Installing the Tk CPython 3.12 wheelhouse

This is the recipe for the `tk-cp312-1` distribution under preparation. It uses
the exact wheels in the [qualified Tk baseline](qualified-tk-baseline.md), with
the [distribution descriptor](../compat/distributions/tk-cp312-1/distribution.json)
and platform-specific hash-locked requirements. It is separate from the older
Qt bundle. Public download availability and the archive checksum must be
supplied with the assembled artifact before it is advertised for download.

## Supply the external runtime first

Use 64-bit CPython with `venv`, `pip` and working `tkinter`. The tested Windows
profile is CPython 3.12.8/Tk 8.6 with an RTX 4090 Vulkan driver; the tested Linux
profile is CPython 3.12.13/Tk 9.0.3 on WSL Ubuntu 24.04/X11 with the retained
Mesa 26.1.8 software Vulkan build. The wheelhouse contains neither interpreter,
Tcl/Tk, Vulkan loader/driver, X11 nor OS packages. Provision them before going
offline. A generic system driver or Tk installation is a different environment
and does not inherit those qualification receipts.

The Linux wheel uses the `cp312-linux_x86_64` tag, not a portable manylinux ABI
promise. Its NumPy dependency also requires glibc 2.27 or newer. Use the declared
Ubuntu profile when reconstructing the retained claim. Native Linux GPU and
Metal graphics qualification remain separate.

## Verify and install

Compare the archive SHA-256 with the separately supplied checksum before
extraction. After extraction, `ASSETS.json` records the size and SHA-256 of every
payload file. Verify those entries and retain `distribution.json`; wheel names
alone do not establish identity. Use a fresh environment and one platform's
requirements. Do not install Qt extras into this Tk-only profile.

From the extracted wheelhouse directory, Windows PowerShell:

```powershell
& C:\path\to\python312\python.exe -m venv C:\path\to\vispy-tk
& C:\path\to\vispy-tk\Scripts\python.exe -m pip install --no-index --only-binary :all: --require-hashes --find-links shared/wheels --find-links windows/wheels -r windows-requirements.txt
& C:\path\to\vispy-tk\Scripts\python.exe -c "import tkinter, vispy; from vispy import app; print(vispy.__version__, tkinter.TkVersion); print(app.Application('tkinter').backend_name)"
```

Linux/WSL shell:

```sh
/path/to/python3.12 -m venv /path/to/vispy-tk
/path/to/vispy-tk/bin/python -m pip install --no-index --only-binary :all: --require-hashes --find-links shared/wheels --find-links linux/wheels -r linux-requirements.txt
/path/to/vispy-tk/bin/python -c "import tkinter, vispy; from vispy import app; print(vispy.__version__, tkinter.TkVersion); print(app.Application('tkinter').backend_name)"
```

Check the chosen interpreter's actual version before creating the environment.
The import command checks package/backend selection; it is not a rendered-frame,
resource-lifetime or absence qualification. Real Tk windows require a working
display. Missing Vulkan support must be resolved as a runtime prerequisite,
without substituting an OpenGL backend and retaining the original claim.

## Source, licenses and evidence

The wheels retain their AGPL-3.0-only implementation license, the original VisPy
BSD license and third-party notices. Keep the wheels intact: notices are included
under both `vispy/_licenses/` and the distribution's `licenses/` metadata.
Dependency wheels retain their original licenses. `distribution.json` identifies
the complete implementation source commit and the dependency source archives
with their locked hashes; it does not relicense those dependencies.

The historical 120-criterion baseline and separate eight-criterion capture
admission apply to their exact original profiles. Extracting or installing the
wheelhouse is not a new combined admission. Full installed-member, functional,
observer/control, shutdown and promotion evidence is required before claiming
another environment qualified. See the [baseline](qualified-tk-baseline.md)
for the evidence entry points, presentation limits and source-only camera work.
