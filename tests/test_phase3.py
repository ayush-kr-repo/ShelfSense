from app.phase3 import solve_layout
import pytest

def overlaps(a, b):
    """Two rectangles overlap only if they intersect on BOTH axes."""
    return (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and
            a["z"] < b["z"] + b["d"] and b["z"] < a["z"] + a["d"])


def test_figure5_layout_is_valid():
    shelves = [{"id": f"S{i}", "w": 2.0, "d": 0.6} for i in range(12)]
    status, layout = solve_layout(10.0, 8.0, shelves,
                                  exit_zone=(0, 0, 1.5, 1.5))
    assert status in ("OPTIMAL", "FEASIBLE")
    assert len(layout) == 12

    exit_rect = {"x": 0, "z": 0, "w": 1.5, "d": 1.5}
    for s in layout:
        assert 0 <= s["x"] and s["x"] + s["w"] <= 10.0     # in bounds (x)
        assert 0 <= s["z"] and s["z"] + s["d"] <= 8.0      # in bounds (z)
        assert not overlaps(s, exit_rect)                  # exit kept clear

    for i, a in enumerate(layout):
        for b in layout[i + 1:]:
            assert not overlaps(a, b)                      # no two overlap


def test_overfull_floor_places_fewer_gracefully():
    """Too many shelves for the floor -> solver places what fits, skips the rest"""
    shelves = [{"id": f"S{i}", "w": 2.0, "d": 0.6} for i in range(3)]
    status, layout = solve_layout(2.0, 1.0, shelves)
    assert status in ("OPTIMAL", "FEASIBLE")
    assert len(layout) < 3                      
    for s in layout:                            
        assert 0 <= s["x"] and s["x"] + s["w"] <= 2.0
        assert 0 <= s["z"] and s["z"] + s["d"] <= 1.0

def test_shelves_never_shrink_below_requested_size():
    """A 0.6m deep shelf must not be modelled as 0.5m. Rounding is
    conservative: shelves and aisles up, floor down."""
    shelves = [{"id": "S0", "w": 2.0, "d": 0.6}]
    status, layout = solve_layout(10.0, 8.0, shelves, cell_m=0.5)
    assert len(layout) == 1
    assert layout[0]["w"] >= 2.0
    assert layout[0]["d"] >= 0.6


def test_floor_is_not_rounded_up():
    """A 10.3m floor must not be treated as 10.5m."""
    shelves = [{"id": f"S{i}", "w": 2.0, "d": 0.6} for i in range(8)]
    status, layout = solve_layout(10.3, 8.0, shelves, cell_m=0.5)
    for s in layout:
        assert s["x"] + s["w"] <= 10.3
        assert s["z"] + s["d"] <= 8.0

@pytest.mark.parametrize("n, w, d, floor_w, floor_d, expected", [
    (6,  2.0, 0.6, 5.0, 3.0, 4),
    (10, 2.0, 0.6, 6.0, 4.0, 5),
    (14, 2.4, 0.8, 8.0, 5.0, 7),
    (20, 2.0, 0.6, 8.0, 6.0, 10),
])
def test_symmetry_breaking_does_not_lose_the_optimum(n, w, d, floor_w, floor_d, expected):
    """These counts were proved OPTIMAL without symmetry breaking. Adding it
    must never place fewer - that would mean the ordering excluded a real layout."""
    shelves = [{"id": f"S{i}", "w": w, "d": d} for i in range(n)]
    status, layout = solve_layout(floor_w, floor_d, shelves, time_limit_s=60)
    assert status == "OPTIMAL"
    assert len(layout) == expected
