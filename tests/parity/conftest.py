# SPDX-License-Identifier: AGPL-3.0-only
"""Label the expected failures listed in tools/documented_outcomes.py in pytest's report; no outcome changes."""
import pytest

from tools import documented_outcomes


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    documented_outcomes.label_report(item, report)
    return report


def pytest_terminal_summary(terminalreporter, config):
    documented_outcomes.summarize(terminalreporter, config)
