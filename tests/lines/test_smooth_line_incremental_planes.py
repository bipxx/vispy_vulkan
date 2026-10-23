"""A single-pixel block is exactly the parent global plane evaluation."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import Probe
from smooth_line_ordered_planes import HYPOTHESES as PATHS,predict_ordered_planes
from smooth_line_incremental_planes import predict_incremental_planes
sys.path.pop(0)


@pytest.mark.parametrize('path',PATHS)
def test_single_pixel_block_is_identical_to_the_global_parent(path):
    p=Probe('control',(5376,12543),(3072,3327),832)
    np.testing.assert_array_equal(predict_incremental_planes(p,(1,path)),predict_ordered_planes(p,path))


def test_boolean_block_is_not_an_integer_geometry_choice():
    with pytest.raises(ValueError,match='declared incremental'):
        predict_incremental_planes(Probe('control',(3072,3072),(12288,9984),256),(True,PATHS[0]))
