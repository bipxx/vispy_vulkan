"""Compare a scoped installed DIVE capture with its immutable upstream oracle."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(base, artifact):
    path = base / artifact["file"]
    if sha(path) != artifact["sha256"]:
        raise ValueError(f"Capture artifact checksum mismatch: {path}")
    return path


def compare(reference, candidate):
    expected = json.loads((reference / "manifest.json").read_text())
    actual = json.loads((candidate / "manifest.json").read_text())
    assert expected["comparison"] == actual["comparison"]
    assert expected["scope"] == actual["scope"]
    assert expected["style_runner_sha256"] == actual["style_runner_sha256"]
    assert expected["cleanup_runner_sha256"] == actual["cleanup_runner_sha256"]
    assert set(expected["fixtures"]) == set(actual["fixtures"]) == {"image", "image_edit"}
    assert not actual["errors"]
    results = {}
    for name, record in actual["fixtures"].items():
        original = expected["fixtures"][name]
        assert original["process"]["exit_code"] == record["process"]["exit_code"] == 0
        for base, item in ((reference, original), (candidate, record)):
            for stream in ("stdout", "stderr"):
                checked(base, item["process"][stream])
            for key in ("capture", "cleanup", "style_restoration"):
                checked(base, item[key])
            for artifact in item["artifacts"].values():
                checked(base, artifact)
        frames = {}
        for key in ("rgba", "before"):
            if key not in original["artifacts"]:
                continue
            left = np.load(checked(reference, original["artifacts"][key]), allow_pickle=False)
            right = np.load(checked(candidate, record["artifacts"][key]), allow_pickle=False)
            assert left.shape == right.shape and left.dtype == right.dtype == np.uint8
            difference = np.abs(left.astype(np.int16) - right.astype(np.int16))
            differing = np.any(difference, axis=2)
            frames[key] = {"shape": list(left.shape), "exact": bool(np.array_equal(left, right)),
                           "file_bytes_exact": checked(reference, original["artifacts"][key]).read_bytes() == checked(candidate, record["artifacts"][key]).read_bytes(),
                           "pixels_differing": int(differing.sum()), "max_abs": int(difference.max()),
                           "channel_max_abs": difference.max(axis=(0, 1)).tolist()}
        png = {key: checked(reference, original["artifacts"][key]).read_bytes() == checked(candidate, record["artifacts"][key]).read_bytes()
               for key in ("png", "before_png") if key in original["artifacts"]}
        parameter_differences = {key: {"upstream": original["parameters"].get(key), "candidate": record["parameters"].get(key)}
                                 for key in original["parameters"].keys() | record["parameters"].keys()
                                 if original["parameters"].get(key) != record["parameters"].get(key)}
        results[name] = {"process_exit_code": 0, "frames": frames, "png_bytes_exact": png,
                         "parameter_differences": parameter_differences,
                         "full_frame_exact": all(item["exact"] and item["file_bytes_exact"] for item in frames.values()) and all(png.values())}
    return {"qualification": "scoped_dive_installed_full_frame_comparison", "scope": actual["scope"],
            "reference": str(reference), "reference_manifest_sha256": sha(reference / "manifest.json"),
            "candidate": str(candidate), "candidate_manifest_sha256": sha(candidate / "manifest.json"),
            "results": results, "legacy_init_render_and_clean_exit_verified": True,
            "scoped_pixel_parity_qualified": all(item["full_frame_exact"] for item in results.values()),
            "ordinary_host_teardown_qualified": False, "scatter_qualified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Comparison evidence must be new")
    result = compare(args.reference.resolve(strict=True), args.candidate.resolve(strict=True))
    result["comparison_tool_sha256"] = sha(Path(__file__))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"legacy_init_render_clean_exit": "passed", "full_frame_exact": result["scoped_pixel_parity_qualified"],
                      "fixtures": {key: value["frames"] for key, value in result["results"].items()}}))
    return 0 if result["scoped_pixel_parity_qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
