"""Tests for the occupancy heatmap render.

The render itself is visual and not worth asserting pixel-by-pixel, but the
geometry underneath it is exactly the thing that broke before: the old version
drew every bay as a fixed 140x180 box, so bays 3-8x larger than that were
silently misrepresented and overlapping ones hid each other.
"""

from pathlib import Path

from app.heatmap import FALLBACK_PX_PER_M, _bay_rect, generate_heatmap, occupancy_color
from app.schemas import Warehouse
from tests.fixtures import make_warehouse, make_empty_warehouse


# --------------------------------------------------------------- geometry

class _Dims:
    def __init__(self, w, h):
        self.w, self.h = w, h


class _Pos:
    def __init__(self, x, y):
        self.x, self.y = x, y


class _Shelf:
    def __init__(self, x, y, w_m, h_m):
        self.pixel_position = _Pos(x, y)
        self.estimated_dims = _Dims(w_m, h_m)


def test_bay_rect_reconstructs_the_detected_pixel_box():
    """Phase 1 stores the corner in pixels and the size in metres; the render
    has to undo that with the same scale factor, or every bay is drawn wrong."""
    shelf = _Shelf(x=100, y=50, w_m=2.0, h_m=3.0)
    assert _bay_rect(shelf, 100.0) == (100, 50, 300.0, 350.0)


def test_bay_rect_respects_a_different_scale():
    shelf = _Shelf(x=0, y=0, w_m=2.0, h_m=3.0)
    assert _bay_rect(shelf, 250.0) == (0, 0, 500.0, 750.0)


def test_bays_of_different_sizes_render_at_different_sizes():
    """The regression that motivated the rewrite: a fixed draw size made a
    100px-wide bay and a 274px-wide bay look identical."""
    narrow = _bay_rect(_Shelf(0, 0, 1.0, 7.0), FALLBACK_PX_PER_M)
    wide = _bay_rect(_Shelf(0, 0, 2.7, 7.0), FALLBACK_PX_PER_M)
    assert (wide[2] - wide[0]) > (narrow[2] - narrow[0]) * 2


# --------------------------------------------------------------- colour

def test_empty_and_full_are_different_colours():
    assert occupancy_color(0.0) != occupancy_color(1.0)


def test_colour_is_deterministic():
    assert occupancy_color(0.42) == occupancy_color(0.42)


def test_colour_clamps_out_of_range_input():
    assert occupancy_color(-1.0) == occupancy_color(0.0)
    assert occupancy_color(2.0) == occupancy_color(1.0)


def test_scale_is_sequential_not_a_traffic_light():
    """Red-yellow-green reads as a verdict - green good, red bad - which
    contradicts storage_efficiency, where fullness is what's rewarded.
    A sequential ramp must brighten monotonically instead."""
    brightness = [sum(occupancy_color(v)) for v in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert brightness == sorted(brightness)


# --------------------------------------------------------------- rendering

def test_renders_without_a_photo(tmp_path: Path):
    """image_path is optional - falls back to a blank canvas rather than
    raising, so analytics still returns if the upload is missing."""
    out = tmp_path / "hm.png"
    generate_heatmap(make_warehouse(), str(out))
    assert out.exists() and out.stat().st_size > 0


def test_renders_a_warehouse_with_no_shelves(tmp_path: Path):
    """Zero detections must produce a readable image, not a crash."""
    out = tmp_path / "empty.png"
    generate_heatmap(make_empty_warehouse(), str(out))
    assert out.exists() and out.stat().st_size > 0


def test_creates_missing_output_directories(tmp_path: Path):
    out = tmp_path / "nested" / "dir" / "hm.png"
    generate_heatmap(make_warehouse(), str(out))
    assert out.exists()


def test_missing_photo_path_falls_back_instead_of_raising(tmp_path: Path):
    out = tmp_path / "hm.png"
    generate_heatmap(make_warehouse(), str(out), "does/not/exist.jpg")
    assert out.exists()
