# SPDX-License-Identifier: AGPL-3.0-only
"""Build a PEP 503 simple index for released vispy Vulkan wheels.

The index serves only the ``vispy`` project and links each wheel to its release
asset with a ``#sha256=`` fragment and ``data-requires-python``. Users combine it
with PyPI, pinning the exact local version so no upstream vispy release can win:

    pip install napari "vispy==0.17.0+vulkan.N" --extra-index-url <index>/simple/
"""
import argparse
import hashlib
import html
from email.parser import Parser
from pathlib import Path
from urllib.parse import quote
import zipfile


def _metadata(path):
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n.endswith('.dist-info/METADATA') and n.count('/') == 1]
        if len(names) != 1:
            raise ValueError('wheel must contain exactly one METADATA: ' + path.name)
        return Parser().parsestr(archive.read(names[0]).decode('utf-8'))


def build_index(wheels, base_url):
    """Return {relative page path: html} for ``wheels`` hosted under ``base_url``."""
    if not base_url.startswith('https://') or not base_url.endswith('/'):
        raise ValueError('base_url must be an https release directory ending in /')
    rows = []
    for path in sorted((Path(p) for p in wheels), key=lambda p: p.name):
        metadata = _metadata(path)
        if metadata['Name'].lower() != 'vispy' or not path.name.startswith('vispy-'):
            raise ValueError('not a vispy wheel: ' + path.name)
        if '+vulkan.' not in metadata['Version']:
            raise ValueError('wheel lacks a vulkan local version: ' + path.name)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        href = html.escape(base_url + quote(path.name) + '#sha256=' + digest)
        requires = html.escape(metadata['Requires-Python'] or '')
        rows.append(f'    <a href="{href}" data-requires-python="{requires}">{html.escape(path.name)}</a><br>')
    page = '<!DOCTYPE html>\n<html>\n  <body>\n{}\n  </body>\n</html>\n'
    return {'index.html': page.format('    <a href="vispy/">vispy</a><br>'),
            'vispy/index.html': page.format('\n'.join(rows))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('wheels', nargs='+', type=Path)
    args = parser.parse_args(argv)
    for name, text in build_index(args.wheels, args.base_url).items():
        target = args.output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
