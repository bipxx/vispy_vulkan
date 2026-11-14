# Qt lifecycle preview

Published and delivery-verified, 2026-11-14:
[prerelease](https://github.com/bipxx/vispy_vulkan/releases/tag/qt-lifecycle-55fd4e8).
CI, exact final review, guarded admission and protected integration have passed.
[Public delivery evidence](../compat/api-acceptance/preview-public-delivery-v1.json)
verifies actual wheel/index bytes and joins Windows Vulkan-clear and WSL ABI-only
channel smokes by exact hashes. Original selected GPU qualification stays separate.

The GitHub prerelease tag `qt-lifecycle-55fd4e8` targets exactly
`55fd4e82e1a1d7bcb9d3c93a5e66c1bc825b09a1`. The wheels contain runtime source
`2b8bccd0ac886f771c3e37255a3d5559c254b3cd`. The tag must not target a PR test
merge or a later documentation/test commit.

These exact CPython3.12x86_64 wheels still report version `0.17.0+vulkan.2`.
They contain different bytes from the earlier stable Vulkan.2 release. This
preview is not a stable upgrade or Vulkan.3, and an existing installation will
not automatically select these bytes merely because its version matches.

The separate [preview package index](https://bipxx.github.io/vispy_vulkan/previews/qt-lifecycle-55fd4e8/simple/)
is public and its bytes verified. Do not
combine that index with the stable index through `--extra-index-url` or a shared
package search configuration: both contain identical wheel filenames/version
strings with different hashes. Use the direct hash-pinned URLs below instead.
The stable release assets and four-link stable index remain unchanged.

## Exact installation

Use an existing matching dependency profile. These commands install only VisPy;
they do not install the filtered Qt closures or the pinned WSL software driver.
`--no-index` prevents package-index selection; `--force-reinstall` is necessary
because the package version has not changed. The preview assets are public and
their delivery checks pass at the exact scope linked above.

Windows CPython3.12x86_64:

```sh
python -m pip install --no-index --no-deps --force-reinstall "https://github.com/bipxx/vispy_vulkan/releases/download/qt-lifecycle-55fd4e8/vispy-0.17.0%2Bvulkan.2-cp312-cp312-win_amd64.whl#sha256=9e4e30cc50d49a759ea42cd7915cc2544a42d2af869d505e3ef5290d47617286"
```

Linux CPython3.12x86_64, glibc2.39or newer, in the selected WSL profile:

```sh
python -m pip install --no-index --no-deps --force-reinstall "https://github.com/bipxx/vispy_vulkan/releases/download/qt-lifecycle-55fd4e8/vispy-0.17.0%2Bvulkan.2-cp312-cp312-manylinux_2_39_x86_64.whl#sha256=a2715d2659f0caf8c01d430c34ba1dc2d5f9b520b6c36ce85a0c75328556fe56"
```

## Identify the installed implementation

`pip show vispy` and `vispy.__version__` cannot distinguish this preview from
the earlier stable Vulkan.2 bytes. The following check reads two changed
installed source members and distinguishes the preview implementation. It is
a small identity check, not full537-member installed qualification.

```python
import hashlib
from pathlib import Path
import vispy

root = Path(vispy.__file__).resolve().parent
expected = {
    "app/backends/_qt.py": "16fec18d9346aeb03a560c7e5e3569eead864e60b362a682709749413dab8997",
    "app/canvas.py": "dd1173d41033a2715f6b5546428089d59737343edf8b374b507bbf1c9db8a929",
}
for name, digest in expected.items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    assert actual == digest, (name, actual)
print("Qt lifecycle preview members match:", root)
```

For a downloaded wheel, compare its full SHA256 with the hash in its direct URL.
The publication checks separately verify all installed runtime members and the
actual delivered wheel bytes.

## Scope

Selected Windows Vulkan and WSL software Vulkan headless/plain-QWidget profiles
cover PyQt5/PyQt6/PySide6, lifecycle/ownership and the finite recorded workflows.
Additional camera and color/alpha composition tests are local installed
observations; they are not retroactively part of the frozen-head CI or strict
admission criteria. Metal remains experimental build/import scope. Physical
Linux GPUs, optional applications, full API/raster parity and lab display
scanout measurements are outside this preview's claims.

The implementation is AGPL-3.0-only. The original VisPy BSD license and retained
dependency licenses/notices remain attached to each wheel. The existing stable
release and its historical qualification records keep their own byte identities.
