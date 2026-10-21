"""Require the fixed DIVE pixels, exports and public state for an installed leaf."""

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("original_dive_comparison", ROOT / "tools/compare_dive_installed.py")
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)


def parameters_match(upstream, candidate):
    """Only the known native widget implementation differs from upstream."""
    left, right = dict(upstream), dict(candidate)
    left_mro, right_mro = left.pop("native_mro", None), right.pop("native_mro", None)
    return (isinstance(left_mro, list) and isinstance(right_mro, list)
            and "QOpenGLWidget" in left_mro and "QWidget" in right_mro
            and "QOpenGLWidget" not in right_mro and left == right)


def compare(reference, candidate):
    result = original.compare(reference, candidate)
    before = json.loads((reference / "manifest.json").read_text())
    after = json.loads((candidate / "manifest.json").read_text())
    for name, row in result["results"].items():
        row["public_parameters_exact"] = parameters_match(before["fixtures"][name]["parameters"],
                                                          after["fixtures"][name]["parameters"])
    result["fixed_public_parameters_qualified"] = all(row["public_parameters_exact"] for row in result["results"].values())
    result["qualified"] = result["scoped_pixel_parity_qualified"] and result["fixed_public_parameters_qualified"]
    result["allowed_parameter_difference"] = "native_mro: upstream QOpenGLWidget to candidate QWidget"
    result["original_comparison_tool_sha256"] = original.sha(ROOT / "tools/compare_dive_installed.py")
    result["comparison_tool_sha256"] = original.sha(Path(__file__))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Comparison evidence must be new")
    result = compare(args.reference.resolve(strict=True), args.candidate.resolve(strict=True))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"qualified": result["qualified"], "full_frame_exact": result["scoped_pixel_parity_qualified"],
                      "public_parameters_exact": result["fixed_public_parameters_qualified"]}))
    return int(not result["qualified"])


if __name__ == "__main__":
    raise SystemExit(main())
