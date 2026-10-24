# SPDX-License-Identifier: AGPL-3.0-only
"""Prepare pinned Glue Qt source for the Dawn QWidget host profile."""

import argparse
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    'prepare_napari_no_opengl', ROOT / 'tools/prepare_napari_no_opengl.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(_module.prepare(args.archive, args.output,
          ROOT / 'compat/host-patches/glue-qt-0.4.2-provenance.json'))


if __name__ == '__main__':
    main()
