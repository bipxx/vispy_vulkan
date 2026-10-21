"""Separate scalar-serialization variant; scene and criteria remain immutable."""
from pathlib import Path
import json
import numpy as np
import oracle_marker_extensions_corrected_capture as capture

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "tests/reference/marker-extensions-opengl/serialized-attempt-3"


def scalar_json(value):
    """Preserve NumPy scalar values as native JSON numbers, including uintc IDs."""
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Unsupported capture JSON value: {type(value).__name__}")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, default=scalar_json) + "\n", encoding="utf-8")


capture.REFERENCE = REFERENCE
capture.SOURCES += ("tools/oracle_marker_extensions_serialized_capture.py",
                    "tests/parity/test_marker_extensions_serialized_parity.py")
capture.write_json = write_json
# The parent's subprocess command must enter this exact wrapper in every child.
capture.__file__ = str(Path(__file__).resolve())

if __name__ == "__main__":
    raise SystemExit(capture.main())
