"""Future holdout separation without opening any held-out input."""
from dataclasses import replace
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import Probe
from smooth_line_training_exclusion import geometry_digest,require_unseen_geometry,training_exclusion
sys.path.pop(0)

PROBE=Probe('training', (3072,3072), (12288,9984), 832)


def test_identity_and_endpoint_reversal_cannot_evade_geometry_exclusion():
    excluded=training_exclusion([PROBE])
    assert len(excluded)==1
    for probe in (PROBE,replace(PROBE,identity='future'),
                  replace(PROBE,identity='future',start_units=PROBE.end_units,end_units=PROBE.start_units)):
        with pytest.raises(ValueError,match='duplicates training'):
            require_unseen_geometry(probe,excluded)


def test_integer_geometry_and_width_are_both_part_of_the_key():
    excluded=training_exclusion([PROBE])
    for probe in (replace(PROBE,width_units=833),replace(PROBE,start_units=(3073,3072))):
        assert geometry_digest(probe)!=geometry_digest(PROBE)
        require_unseen_geometry(probe,excluded)


def test_degenerate_and_outside_viewport_holdouts_remain_representable():
    for probe in (Probe('future',(-256,0),(-256,0),256),Probe('future',(-256,0),(17000,17000),256)):
        require_unseen_geometry(probe,training_exclusion([PROBE]))


@pytest.mark.parametrize('probe',(replace(PROBE,width_units=True),replace(PROBE,width_units=0),
    replace(PROBE,start_units=(1.0,2)),replace(PROBE,end_units=(True,2))))
def test_inexact_geometry_refuses(probe):
    with pytest.raises(ValueError):
        geometry_digest(probe)
