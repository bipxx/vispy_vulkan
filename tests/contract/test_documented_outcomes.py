# SPDX-License-Identifier: AGPL-3.0-only
"""The documented-outcome index (tools/documented_outcomes.py) matches the rules that run and never changes a result."""
import importlib
from pathlib import Path
import re
from types import SimpleNamespace

import pytest

from tools import documented_outcomes as outcomes

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('decision', sorted(outcomes.DIFFERENCES))
def test_each_documented_difference_matches_the_modules_that_apply_it(decision):
    difference = outcomes.DIFFERENCES[decision]
    assert difference.rule and difference.modules
    for name in difference.modules:
        source = (ROOT / 'tools' / (name + '.py')).read_text(encoding='utf-8')
        assert re.search(r'\b%s\b' % decision, source), (name, decision)
    for name, attribute, expected in difference.bindings:
        actual = getattr(importlib.import_module('tools.' + name), attribute)
        if isinstance(expected, set):
            actual = set(actual)
        elif isinstance(expected, dict):
            actual = dict(actual)
        assert actual == expected, (decision, name, attribute)


def test_each_expected_failure_names_a_case_of_its_suite():
    assert len(outcomes.EXPECTED_FAILURES) == 41
    for nodeid, failure in outcomes.EXPECTED_FAILURES.items():
        assert failure.decision in ('D6', 'D8') and failure.reason, nodeid
        path, test = nodeid.split('::')
        function, case = re.fullmatch(r'(\w+)\[(\w+)\]', test).groups()
        source = (ROOT / path).read_text(encoding='utf-8')
        assert re.search(r'(?m)^def %s\(name[,)]' % function, source), nodeid
        fixture = re.search(r'(?m)^from tools\.(fixture_\w+) import (?:\([^)]*|[^\n(]*)\bCASES\b', source).group(1)
        assert case in importlib.import_module('tools.' + fixture).CASES, nodeid


def test_d8_covers_exactly_the_four_render_plane_scheduled_cases():
    d8 = sorted(nodeid for nodeid, failure in outcomes.EXPECTED_FAILURES.items() if failure.decision == 'D8')
    assert [nodeid.split('[')[1].rstrip(']') for nodeid in d8] == [
        'plane_clipped', 'plane_handles', 'plane_rotation', 'plane_translation']
    assert all(nodeid.startswith('tests/hosts/test_napari_render_plane_scheduled_parity.py::') for nodeid in d8)


def report(nodeid, when='call', outcome='failed'):
    return SimpleNamespace(nodeid=nodeid, when=when, outcome=outcome, failed=outcome == 'failed', sections=[],
                           user_properties=[])


def test_a_documented_failure_is_labelled_and_still_fails():
    nodeid = next(iter(outcomes.EXPECTED_FAILURES))
    item, failing = SimpleNamespace(nodeid=nodeid, user_properties=[]), report(nodeid)
    outcomes.label_report(item, failing)
    assert failing.outcome == 'failed' and failing.failed
    (title, text), = failing.sections
    assert 'documented' in title and text.startswith('D8: ')
    assert failing.user_properties == item.user_properties == [('documented_failure', text)]
    for unlabelled in (report(nodeid, outcome='passed'), report(nodeid, when='setup'), report('tests/x.py::test_y')):
        item = SimpleNamespace(nodeid=unlabelled.nodeid, user_properties=[])
        outcomes.label_report(item, unlabelled)
        assert not unlabelled.sections and not unlabelled.user_properties and not item.user_properties


class Reporter:
    def __init__(self, **stats):
        self.stats, self.lines = stats, []

    def section(self, title):
        self.lines.append('== ' + title)

    def write_line(self, line):
        self.lines.append(line)


def test_the_summary_counts_documented_and_other_failures_and_flags_listed_passes():
    documented, listed = list(outcomes.EXPECTED_FAILURES)[:2]
    reporter = Reporter(failed=[report(documented), report('tests/hosts/test_other.py::test_new')],
                        passed=[report(listed, outcome='passed')])
    config = SimpleNamespace()
    outcomes.summarize(reporter, config)
    assert reporter.lines[1:] == [documented + '  [D8]', listed + '  [D8] passed; update the index',
                                  '1 failed as documented, 1 failed without a documented reason, 1 listed but passed']
    outcomes.summarize(reporter, config)  # the second conftest's call adds nothing
    assert len(reporter.lines) == 4
    quiet = Reporter(failed=[report('tests/hosts/test_other.py::test_new')])
    outcomes.summarize(quiet, SimpleNamespace())
    assert quiet.lines == []


@pytest.mark.parametrize('directory', ('hosts', 'parity'))
def test_the_conftests_only_label_reports(directory):
    source = (ROOT / 'tests' / directory / 'conftest.py').read_text(encoding='utf-8')
    assert 'documented_outcomes.label_report(item, report)' in source
    assert 'documented_outcomes.summarize(terminalreporter, config)' in source
    for forbidden in ('xfail', 'skip', 'outcome =', '.outcome', 'longrepr'):
        assert forbidden not in source, forbidden


__all__ = [name for name in dir() if name.startswith('test_')]
