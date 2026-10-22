# SPDX-License-Identifier: AGPL-3.0-only
"""Admission-set CLI forwarding and metadata override lifetime; no renderer."""
import pytest
from tools import volume_benchmark_adapter3 as adapter

def test_admission_argument_is_forwarded_without_being_consumed(monkeypatch):
    observed=[]
    monkeypatch.setattr(adapter.observer_free,'main',lambda argv:observed.append(argv) or 17)
    selected='a'*64
    remaining=['--worker','candidate','--admission','controls/case.json','--output','evidence']
    before=(adapter.base.load_admission,adapter.observer_free.sources)
    assert adapter.main(['--admission-set-sha256',selected,*remaining])==17
    assert observed==[remaining]
    assert (adapter.base.load_admission,adapter.observer_free.sources)==before

def test_metadata_overrides_restore_on_worker_error(monkeypatch):
    before=(adapter.base.load_admission,adapter.observer_free.sources)
    def fail(argv):raise RuntimeError('actual worker failure')
    monkeypatch.setattr(adapter.observer_free,'main',fail)
    with pytest.raises(RuntimeError,match='actual worker failure'):
        adapter.main(['--admission-set-sha256','a'*64,'--admission','case.json'])
    assert (adapter.base.load_admission,adapter.observer_free.sources)==before

@pytest.mark.parametrize('digest',['','A'*64,'0'*63,'not-a-digest'])
def test_invalid_manifest_digest_fails_before_opening_evidence(digest):
    with pytest.raises(ValueError,match='lowercase qualification SHA256'):
        adapter.load_admission('nonexistent/case.json','volume-256-1024-mip-full',digest)
