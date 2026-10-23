"""An unproved debugger exception policy cannot be enabled by a run flag."""
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows native debugger baseline contract')
@pytest.mark.parametrize('value,reason', [({'schema': 1, 'status': 'FAIL'}, 'passing native'),
                                        ({'schema': 1, 'status': 'PASS_HANDLE_FIDELITY_CONTROLS', 'checks': {'asserted': True}, 'os_files': {}}, 'both actual OS')])
def test_invalid_fidelity_baseline_is_rejected_before_child_launch(tmp_path, value, reason):
    from no_opengl.windows import trace
    path = tmp_path / 'invalid.json'
    path.write_text(json.dumps(value))
    marker = tmp_path / 'child-started'
    with pytest.raises(ValueError, match=reason):
        trace([sys.executable, '-c', f'from pathlib import Path;Path({str(marker)!r}).touch()'],
              environment=os.environ.copy(), cwd=tmp_path, log=tmp_path / 'child.log', handle_baseline=path)
    assert not marker.exists()
