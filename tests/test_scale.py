import pytest

from app.scale import reference_scale, px_to_m

def test_reference_scale():
    assert reference_scale(2.0, 480) == 240.0

def test_px_to_m():
    assert px_to_m(360, 240.0) == 1.5

def test_rejects_unncessary_lengths():
    with pytest.raises(ValueError):
        reference_scale(0, 480)
    with pytest.raises(ValueError):
        reference_scale(2.0, -1.0)