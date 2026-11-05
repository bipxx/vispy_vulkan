# SPDX-License-Identifier: AGPL-3.0-only
"""PEP 503 index pages for released wheels: exact links, hashes and Python requirement."""
import hashlib
import io
import zipfile
from html.parser import HTMLParser

import pytest

from tools.wheel_index import build_index

BASE = 'https://github.com/bipxx/vispy_vulkan/releases/download/v0.17.0-vulkan.2/'


def wheel(tmp_path, name, requires_python='>=3.10'):
    path = tmp_path / name
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        dist = name.split('-')[0] + '-' + name.split('-')[1] + '.dist-info'
        archive.writestr(dist + '/METADATA', 'Metadata-Version: 2.4\nName: vispy\nVersion: '
                         + name.split('-')[1] + '\nRequires-Python: ' + requires_python + '\n')
    path.write_bytes(buffer.getvalue())
    return path


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs))


def links(page):
    parser = Links()
    parser.feed(page)
    return parser.links


def test_project_page_links_every_wheel_with_hash_and_python_requirement(tmp_path):
    first = wheel(tmp_path, 'vispy-0.17.0+vulkan.2-cp312-cp312-win_amd64.whl')
    second = wheel(tmp_path, 'vispy-0.17.0+vulkan.2-cp313-cp313-win_amd64.whl', '>=3.11')
    pages = build_index([second, first], BASE)
    assert set(pages) == {'index.html', 'vispy/index.html'}
    assert [a['href'] for a in links(pages['index.html'])] == ['vispy/']
    project = links(pages['vispy/index.html'])
    assert [a['href'] for a in project] == [
        BASE + 'vispy-0.17.0%2Bvulkan.2-cp312-cp312-win_amd64.whl#sha256=' + hashlib.sha256(first.read_bytes()).hexdigest(),
        BASE + 'vispy-0.17.0%2Bvulkan.2-cp313-cp313-win_amd64.whl#sha256=' + hashlib.sha256(second.read_bytes()).hexdigest(),
    ]
    assert [a['data-requires-python'] for a in project] == ['>=3.10', '>=3.11']


def test_requires_python_is_html_escaped(tmp_path):
    page = build_index([wheel(tmp_path, 'vispy-0.17.0+vulkan.2-cp312-cp312-win_amd64.whl', '>=3.10,<4')], BASE)['vispy/index.html']
    assert 'data-requires-python="&gt;=3.10,&lt;4"' in page


def test_only_vispy_wheels_with_a_vulkan_local_version_are_indexed(tmp_path):
    with pytest.raises(ValueError, match='vulkan local version'):
        build_index([wheel(tmp_path, 'vispy-0.17.0-cp312-cp312-win_amd64.whl')], BASE)
    with pytest.raises(ValueError, match='not a vispy wheel'):
        build_index([wheel(tmp_path, 'napari-0.9.2-py3-none-any.whl')], BASE)


def test_base_url_must_be_an_https_release_directory(tmp_path):
    with pytest.raises(ValueError, match='https'):
        build_index([wheel(tmp_path, 'vispy-0.17.0+vulkan.2-cp312-cp312-win_amd64.whl')], 'http://example.com/')


__all__ = [name for name in dir() if name.startswith('test_')]
