# SPDX-License-Identifier: AGPL-3.0-only
"""Release projection and independent-control semantics; no compiler or device."""
import copy
import io
import json
from pathlib import Path
import tarfile

import pytest
from tools import build_software_vulkan as driver


def source_tar(path, entries):
    with tarfile.open(path, 'w') as archive:
        for name, data, link in entries:
            member = tarfile.TarInfo(name)
            if link is not None:
                member.type = tarfile.SYMTYPE
                member.linkname = link
                archive.addfile(member)
            else:
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))


def test_release_aliases_are_regular_and_dangling_hook_is_recorded(tmp_path):
    archive = tmp_path / 'source.tar'
    source_tar(archive, [('mesa-n/include/value.h', b'original header', None),
                         ('mesa-n/include/alias.h', b'', 'value.h'),
                         ('mesa-n/bin/ci/pipeline_message.py', b'', '../../.marge/hooks/pipeline_message.py')])
    destination = tmp_path / 'source'
    projection = driver.project_source(archive, destination)
    assert (destination / 'include/alias.h').read_bytes() == b'original header'
    assert not (destination / 'include/alias.h').is_symlink()
    assert not (destination / 'bin/ci/pipeline_message.py').exists()
    assert len(projection) == 2


def test_other_missing_source_link_is_not_silently_omitted(tmp_path):
    archive = tmp_path / 'source.tar'
    source_tar(archive, [('mesa-n/include/value.h', b'', 'missing.h')])
    with pytest.raises(ValueError, match='unresolved release link'):
        driver.project_source(archive, tmp_path / 'source')


def controls(baseline):
    lines = []
    for clipped in (False, True):
        for linear in (False, True):
            lines.append('CASE ' + json.dumps(dict(clipped=clipped, noperspective=linear,
                covered=256 if clipped else 120, mismatches=40 if baseline and clipped and linear else 0)))
    return '\n'.join(lines) + '\nTERMINAL device_waited=true objects_destroyed=true\n'


def test_control_parser_preserves_expected_failure_and_terminal_cleanup():
    assert len(driver.control_cases(controls(True), True)) == 4
    assert len(driver.control_cases(controls(False), False)) == 4
    with pytest.raises(ValueError, match='baseline'):
        driver.control_cases(controls(False), True)
    with pytest.raises(ValueError, match='patched'):
        driver.control_cases(controls(True), False)
    with pytest.raises(ValueError, match='cleanup'):
        driver.control_cases(controls(False).replace('device_waited=true', 'device_waited=false'), False)
    with pytest.raises(ValueError, match='incomplete'):
        driver.control_cases(controls(False).replace('"clipped": false, "noperspective": true',
                                                     '"clipped": false, "noperspective": false'), False)


@pytest.mark.parametrize('change', ['opengl', 'fallback', 'duplicate', 'conflict'])
def test_recipe_cannot_change_the_observed_configuration(change):
    pin = json.loads(driver.PIN.read_bytes())
    driver.validate_recipe(pin)
    pin = copy.deepcopy(pin)
    if change in ('opengl', 'fallback'):
        original = '-Dopengl=false' if change == 'opengl' else '--wrap-mode=nofallback'
        pin['flags'].remove(original)
    elif change == 'duplicate':
        pin['flags'].append(pin['flags'][0])
    else:
        pin['flags'].append('-Dopengl=true')
    with pytest.raises(ValueError, match='configuration'):
        driver.validate_recipe(pin)


@pytest.mark.parametrize('awaited', [True, False])
def test_completed_producer_cleanup_keeps_evidence_and_refuses_unawaited_work(tmp_path, awaited):
    scratch = tmp_path / 'build/work/synthetic'
    scratch.mkdir(parents=True)
    (scratch / '.build-hygiene-owner.json').write_text(json.dumps(
        dict(schema=1, run_id='synthetic', owner='test')))
    payload = scratch / 'discard.tmp'
    payload.write_bytes(b'disposable')
    source = tmp_path / 'source.txt'
    source.write_bytes(b'synthetic source and license, not native proof')
    output = tmp_path / 'producer.json'
    output.write_text(json.dumps(dict(run_id='synthetic', owner='test',
        status='SOURCE_FUNCTIONAL_NOT_ADMITTED', commands=[dict(child_waited=awaited)],
        retained=[dict(path=str(source), sha256=driver.digest(source),
                       roles=['source','licenses','repro'])])))
    if not awaited:
        with pytest.raises(ValueError, match='unawaited'):
            driver.cleanup_record('synthetic','test',output,0,workspace=tmp_path)
        assert payload.exists()
    else:
        result = driver.cleanup_record('synthetic','test',output,0,workspace=tmp_path)
        assert result['status'] == 'PASS_APPLY'
        assert source.read_bytes() == b'synthetic source and license, not native proof'
        assert not scratch.exists() or not list(scratch.iterdir())
