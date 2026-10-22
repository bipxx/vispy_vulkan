"""Ready-token mentions cannot override a failing scientific verdict."""
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_review_gate import require_ready_review
sys.path.pop(0)

READY='READY_FOR_SCOPED_WINDOW_OBSERVATION'


def test_exact_final_verdict_admits():
    require_ready_review(dict(is_error=False,result='Findings closed.\n'+READY+'\n'),READY)


@pytest.mark.parametrize('response',(
    dict(is_error=False,result=READY+' mentioned conditionally\nFIX_BEFORE_CAPTURE'),
    dict(is_error=False,result='FIX_BEFORE_CAPTURE\n'+READY),
    dict(is_error=False,result='**'+READY+'**'),
    dict(is_error=False,result=READY+' extra'),
    dict(is_error=False,result='READY_FOR_OTHER_SCOPE'),
    dict(is_error=True,result=READY),dict(is_error=False,result=''),{}))
def test_non_ready_review_refuses(response):
    with pytest.raises(ValueError):require_ready_review(response,READY)
