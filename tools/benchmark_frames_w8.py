# SPDX-License-Identifier: AGPL-3.0-only
"""W8 successor of the pinned frame benchmark (tools/benchmark_frames.py): its setup and RGBA format fixed.

The volume scientific admissions pin the harness (runner_sha256), so it stays unchanged. This runs the harness's own
code with three single-line changes (CHANGES), so its line numbers, and those in tracebacks, still match the harness:
- setup: workers get VISPY_PYQT5_SHARE_CONTEXT=true, without which upstream VisPy's PyQt6 canvases fail, and
  VISPY_QT_PRESENTATION=native, the candidate presentation whose completions the harness measures (the Windows
  default, readback, reports none). W8's paced campaign (run w8-paced-benchmark-245) had to set both by hand.
- RGBA images: the harness passed texture_format="rgba8", but VisPy expands a format's "r" to the data's channels
  ("r8" becomes "rgba8"), so every RGBA workload failed on both sides with the invalid "rgbagba8". It passes "r8".
- evidence: the request also records the pinned harness's sha256 (runner_sha256 is this file's).
Usage: as tools/benchmark_frames.py, for example --list.
"""
import hashlib
from pathlib import Path

HARNESS = Path(__file__).with_name('benchmark_frames.py')
HARNESS_SHA256 = '55f76b5cf1bc95b23547b572af61e41a6bd524911fd44bc2305318002e60ab26'
CHANGES = (
    ('    env.update(QT_API="pyqt6", QT_SCALE_FACTOR="1")\n',
     '    env.update(QT_API="pyqt6", QT_SCALE_FACTOR="1", VISPY_PYQT5_SHARE_CONTEXT="true", '
     'VISPY_QT_PRESENTATION="native")\n'),
    ('texture_format="r32f" if channels == 1 else "rgba8")\n',
     'texture_format="r32f" if channels == 1 else "r8")\n'),
    ('"runner_sha256": sha256(__file__), "reference_python": ',
     '"runner_sha256": sha256(__file__), "harness_sha256": HARNESS_SHA256, "reference_python": '),
)


def derived_source():
    """The pinned harness's source with CHANGES applied; each must match exactly once."""
    data = HARNESS.read_bytes()
    if hashlib.sha256(data).hexdigest() != HARNESS_SHA256:
        raise RuntimeError('tools/benchmark_frames.py is not the pinned harness')
    text = data.decode('utf-8')
    for old, new in CHANGES:
        if text.count(old) != 1:
            raise RuntimeError('a change does not match exactly once: ' + old.strip())
        text = text.replace(old, new)
    return text


if __name__ == '__main__':
    # Run as this module, so the harness's workers start this file and dataclasses resolve through sys.modules.
    exec(compile(derived_source(), str(HARNESS), 'exec', dont_inherit=True), globals())
