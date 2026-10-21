"""Fixed scientific parity rules; optional raw candidate/difference artifacts."""

import json
from pathlib import Path

import numpy as np

from .fixture_gloo import FIXTURES, assert_expected_regions, comparison_masks

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "tests/reference/opengl"


def assert_reference(name, image, *, evidence=None):
    manifest = json.loads((REFERENCE / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["fixtures"][name]
    reference = np.load(REFERENCE / record["rgba"]["file"], allow_pickle=False)
    assert image.shape == reference.shape, (image.shape, reference.shape)
    assert image.dtype == reference.dtype == np.uint8
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    if evidence is not None:
        directory = Path(evidence)
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / f"{name}.candidate.npy", image, allow_pickle=False)
        np.save(directory / f"{name}.difference.npy", difference, allow_pickle=False)
    interior, edge = comparison_masks(name, image.shape)
    if FIXTURES[name].exact:
        assert np.array_equal(image, reference), (name, "exact categorical/landmark mismatch", int(difference.max()))
    else:
        assert not interior.any() or difference[interior].max() <= 2, (name, int(difference[interior].max()))
        differing = np.any(difference != 0, axis=2)
        assert np.count_nonzero(differing & edge) <= np.count_nonzero(edge) * .001, (
            name, "fixed edge-band mismatch", int(np.count_nonzero(differing & edge)))
    assert_expected_regions(name, image)

