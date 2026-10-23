"""Training-only descriptors and necessary coverage diagnostics; no renderer model."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import numpy as np

PIXEL_UNITS = 256
SIZE = (64, 64)
SAMPLE_COUNTS = (4, 8, 16, 32, 64)
FUTURE_HOLDOUT_ROLES = tuple('new-holdout-role-' + str(index) for index in range(8))


@dataclass(frozen=True)
class Probe:
    identity: str
    start_units: tuple[int, int]
    end_units: tuple[int, int]
    width_units: int

    def clip_positions(self):
        positions = np.array([self.start_units, self.end_units], dtype=np.float32)
        positions[:, 0] = positions[:, 0] / (PIXEL_UNITS * SIZE[0] / 2) - 1
        positions[:, 1] = 1 - positions[:, 1] / (PIXEL_UNITS * SIZE[1] / 2)
        return positions


def training_probes():
    probes = []
    for orientation in ('horizontal', 'vertical'):
        for reverse in (False, True):
            for width in (256, 384, 832):
                for phase in range(256):
                    if orientation == 'horizontal':
                        start, end = (12 * 256 + 32, 20 * 256 + phase), (52 * 256 + 32, 20 * 256 + phase)
                    else:
                        start, end = (20 * 256 + phase, 12 * 256 + 32), (20 * 256 + phase, 52 * 256 + 32)
                    if reverse:
                        start, end = end, start
                    probes.append(Probe(f'axial-{orientation}-r{int(reverse)}-w{width}-p{phase:03}', start, end, width))
    phases = sorted({pair for phase in range(0, 256, 16)
                     for pair in ((phase, 0), (0, phase), (phase, phase), (phase, 255 - phase))})
    vectors = ((36, 9), (36, 18), (36, 27), (27, 36), (18, 36), (9, 36), (36, 36), (36, -18))
    for index, (dx, dy) in enumerate(vectors):
        for reverse in (False, True):
            for width in (256, 384, 832, 1920):
                for px, py in phases:
                    origin = (12, 48 if dy < 0 else 12)
                    start = (origin[0] * 256 + px, origin[1] * 256 + py)
                    end = ((origin[0] + dx) * 256 + px, (origin[1] + dy) * 256 + py)
                    if reverse:
                        start, end = end, start
                    probes.append(Probe(f'oblique-{index}-r{int(reverse)}-w{width}-p{px:03}-{py:03}', start, end, width))
    return tuple(probes)


def training_contract(target_format='rgba8'):
    if target_format not in ('rgba8', 'rgba16', 'rgba32f'):
        raise ValueError('Only the declared RGBA8/RGBA16/RGBA32F observation formats are allowed')
    probes = training_probes()
    records = [asdict(probe) for probe in probes]
    payload = json.dumps(records, sort_keys=True, separators=(',', ':')).encode()
    return dict(schema=1, scope='Training mechanism observations only; no selected model', size=list(SIZE),
                pixel_units=PIXEL_UNITS, probe_count=len(probes), probes_sha256=hashlib.sha256(payload).hexdigest(),
                color=[1, 1, 1, 1], clear=[0, 0, 0, 0], blending=False, line_smooth=True,
                depth_test=False, stencil_test=False, sample_count=1,
                format={'rgba8': 'linear RGBA8', 'rgba16': 'linear RGBA16', 'rgba32f': 'linear RGBA32F'}[target_format],
                line_smooth_hint='GL_DONT_CARE', dither=False, framebuffer_srgb=False,
                comparison='full RGBA exact; generated mask is independent of quantized alpha',
                finite_sample_counts=list(SAMPLE_COUNTS), future_holdout_roles=list(FUTURE_HOLDOUT_ROLES),
                future_model_family=dict(
                    grids='all ordered power-of-two factor pairs of N; centered cell samples',
                    rotations=['identity', 'q16.16-45deg-coefficient46341'],
                    endpoint_snap=['floor-1/256', 'nearest-1/256'],
                    endpoint_extent=['butt', 'half-width'], alpha_conversion=['floor', 'nearest'],
                    generated_mask=['nonzero-sample-count', 'positive-rectangle-pixel-intersection'],
                    fixed_hypotheses=800, exact_training_match_required=True,
                    selection_tie_break='lowest canonical hypothesis ID; sealed before holdout inputs'),
                model_selected=False, renderer_qualified=False)


def training_artifact_name(identity):
    # Decide the scientific role before constructing/opening any artifact path.
    allowed = {probe.identity for probe in training_probes()}
    if type(identity) is not str or identity not in allowed:
        raise ValueError('Descriptor is not in the frozen training selection')
    return 'training/' + identity + '.rgba.npy'


def read_training_artifact(root, identity):
    name = training_artifact_name(identity)
    return (Path(root) / name).read_bytes()


@lru_cache(maxsize=1)
def _training_row_indices():
    return MappingProxyType({probe.identity: index for index, probe in enumerate(training_probes())})


def read_training_row(root, identity):
    # The produced bulk array contains training rows only. Admit the exact
    # scientific identity/index before even opening its header or mapping it.
    if type(identity) is not str or identity not in _training_row_indices():
        raise ValueError('Descriptor is not in the frozen training selection')
    index = _training_row_indices()[identity]
    data = np.load(Path(root) / 'training.rgba.npy', mmap_mode='r', allow_pickle=False)
    if data.dtype != np.uint8 or data.shape != (7040, SIZE[1], SIZE[0], 4):
        raise ValueError('Complete frozen training array required')
    return np.array(data[index], copy=True)


def quantized_levels(sample_count, rounding):
    if sample_count not in SAMPLE_COUNTS or rounding not in ('floor', 'nearest'):
        raise ValueError('Unselected finite-sample diagnostic')
    counts = np.arange(sample_count + 1, dtype=np.int64)
    return ((counts * 255 + (sample_count // 2 if rounding == 'nearest' else 0)) // sample_count).astype(np.uint8)


def coverage_diagnostics(frames):
    frames = np.asarray(frames)
    if frames.dtype != np.uint8 or frames.ndim != 4 or frames.shape[1:] != (SIZE[1], SIZE[0], 4) or not len(frames):
        raise ValueError('Expected nonempty training RGBA8 frames')
    rgb = frames[..., :3]
    if not np.all((rgb == 0) | (rgb == 255)) or not np.all(rgb == rgb[..., :1]):
        raise ValueError('Constant white, blend-off coverage observation required')
    generated = rgb[..., 0] == 255
    alpha = frames[..., 3]
    if np.any(alpha[~generated] != 0):
        raise ValueError('Unwritten pixels must retain transparent clear')
    histogram = np.bincount(alpha[generated], minlength=256)
    observed = np.flatnonzero(histogram)
    compatible = []
    for count in SAMPLE_COUNTS:
        for rounding in ('floor', 'nearest'):
            if np.isin(observed, quantized_levels(count, rounding)).all():
                compatible.append(dict(sample_count=count, rounding=rounding))
    return dict(frame_count=len(frames), generated_fragments=int(generated.sum()),
                zero_alpha_generated_fragments=int(np.count_nonzero(generated & (alpha == 0))),
                alpha_histogram=histogram.tolist(), observed_alpha_levels=observed.tolist(),
                necessary_lattice_compatibility=compatible, mechanism_identified=False,
                coverage_model_selected=False, full_frame_parity_proven=False)
