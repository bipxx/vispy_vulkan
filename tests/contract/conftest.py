# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic review-gate controls independent of the project's review phase."""
from copy import deepcopy
from pathlib import Path

import pytest


@pytest.fixture
def without_current_reviews(monkeypatch):
    """Remove reviews only from an in-memory candidate; retain the real verifier."""
    from tools.compatibility_candidate import seal, scope_digest
    candidate_path = Path(__file__).resolve().parents[2] / 'compat/candidates/tk-state-resource-1/candidate.json'

    def isolate(module):
        original = module.read_json

        def read(path):
            value = original(path)
            if Path(path).resolve() == candidate_path:
                before = scope_digest(value)
                value = deepcopy(value)
                value['reviews'] = {'source': None, 'scope': None}
                seal(value)
                assert scope_digest(value) == before
            return value

        monkeypatch.setattr(module, 'read_json', read)

    return isolate
