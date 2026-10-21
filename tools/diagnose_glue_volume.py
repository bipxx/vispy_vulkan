"""Capture native exceptions suppressed by the unchanged Glue volume visual."""

import argparse
from pathlib import Path
import traceback

import numpy as np

from fixture_glue import render
from oracle_capture import provenance, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    import vispy
    from vispy import _dawn
    vispy.use(app='pyqt6')
    record = {'scope': 'Diagnostic wrapper rethrows original native errors; unchanged volume fixture',
              'provenance': provenance('candidate'), 'native_origin': _dawn.__file__,
              'native_sha256': sha256(_dawn.__file__), 'errors': [], 'status': 'diagnostic'}
    original = _dawn.execute

    def observe(canvas_id, packed, arrays):
        try:
            return original(canvas_id, packed, arrays)
        except Exception as error:
            record['errors'].append({'canvas_id': canvas_id, 'error_type': type(error).__name__,
                                     'error': str(error), 'packed_bytes': len(packed),
                                     'array_count': len(arrays), 'traceback': traceback.format_exc()})
            raise

    _dawn.execute = observe
    try:
        record['counters_before'] = dict(_dawn.probe())
        image, commands, shaders, parameters = render('volume')
        np.save(args.output / 'volume.npy', image, allow_pickle=False)
        write_json(args.output / 'volume.glir.json', commands)
        write_json(args.output / 'volume.shaders.json', shaders)
        record['parameters'] = parameters
        record['image_sha256'] = sha256(args.output / 'volume.npy')
    finally:
        _dawn.execute = original
        record['counters_after'] = dict(_dawn.probe())
        record['native_trace'] = _dawn.debug_trace()
        write_json(args.output / 'diagnostic.json', record)
    for error in record['errors']:
        print(error['error'], flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
