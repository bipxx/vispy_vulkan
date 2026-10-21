# SPDX-License-Identifier: AGPL-3.0-only
"""All five corrected Glue workflows, with fresh original and candidate wheels."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from tools import glue_wheel_suite as suite

pytestmark = [pytest.mark.gpu, pytest.mark.wheel]


@pytest.fixture(scope='module')
def qualified_suite():
    original = os.environ.get('VISPY_GLUE_UPSTREAM_WHEEL')
    candidate = os.environ.get('VISPY_TEST_WHEEL')
    assert original and candidate, 'Both original upstream and candidate wheel artifacts are required'
    output = Path(os.environ.get('VISPY_GLUE_WHEEL_EVIDENCE', suite.ROOT / 'build/evidence/glue-wheel-suite')).resolve()
    assert not output.exists(), 'Preserve all prior Glue attempts'
    output.mkdir(parents=True)
    repository = Path(os.environ.get('VISPY_GLUE_REPOSITORY', suite.ROOT)).resolve()
    upstream = SimpleNamespace(kind='upstream', wheel=Path(original).resolve(), output=output / 'upstream',
        repository=repository, reference=None, reference_sha256=None)
    assert suite.run(upstream) == 0, 'Fresh upstream failure blocks candidate qualification'
    reference_digest = suite.sha(upstream.output / 'manifest.json')
    verified = suite.verify_saved(upstream.output, reference_digest, upstream.wheel, 'upstream')
    suite.write(output / 'upstream-verification.json', verified)
    run = SimpleNamespace(kind='candidate', wheel=Path(candidate).resolve(), output=output / 'candidate',
        repository=repository, reference=upstream.output, reference_sha256=reference_digest)
    code = suite.run(run)
    verified = suite.verify_saved(run.output, suite.sha(run.output / 'manifest.json'), run.wheel, 'candidate',
        reference=upstream.output, reference_sha256=reference_digest)
    assert code == (1 if verified['failed'] else 0)
    suite.write(output / 'candidate-verification.json', verified)
    return json.loads((run.output / 'manifest.json').read_bytes())


@pytest.mark.parametrize('name', suite.CASES)
def test_corrected_glue_workflow_matches_fresh_original_exactly(name, qualified_suite):
    row = qualified_suite['workers'][name]
    assert row['process_exit'] == row['worker']['process_exit'] == 0, row['worker'].get('error', row['worker']['status'])
    assert row['worker']['status'] == 'PASS_CANDIDATE_GLUE_CASE'
    assert row['worker']['compared_pixels'] == 128 * 128 and row['worker']['excluded_pixels'] == 0
