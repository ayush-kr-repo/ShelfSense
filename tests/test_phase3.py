from app.phase3 import solve_layout


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

