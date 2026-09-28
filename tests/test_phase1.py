"""coverage_ratio: fraction of a shelf rectangle covered by at least one box.

Every expected value here is hand-computed on a 10 x 10 shelf, so the maths can be checked on paper without running anything
"""

from app.phase1 import coverage_ratio

SHELF = (0.0, 0.0, 10.0, 10.0)      # Area = 100

def test_no_boxes_is_zero():
    assert coverage_ratio(SHELF, []) == 0.0

def test_box_entirely_outside_is_zero():
    assert coverage_ratio(SHELF, [(20, 20,30,30)]) == 0.0

def test_single_box_covering_everything():
    assert coverage_ratio(SHELF, [(0, 0, 10, 10)]) == 1.0

def test_left_half():
    # 5 x 10 = 50 of 100
    assert coverage_ratio(SHELF, [(0, 0, 5, 10)]) == 0.5

def test_bottom_left_quarter():
    # 5x5 = 25 of 100
    assert coverage_ratio(SHELF, [(0, 0, 5, 5)]) == 0.25


def test_two_disjoint_quarters_add_up():
    # 25 + 25 = 50 of 100
    assert coverage_ratio(SHELF, [(0, 0, 5, 5), (5, 5, 10, 10)]) == 0.5


def test_overlapping_boxes_are_not_double_counted():
    # 0-6 and 4-10 overlap on 4-6. Union spans the full width -> 1.0, not 1.2.
    assert coverage_ratio(SHELF, [(0, 0, 6, 10), (4, 0, 10, 10)]) == 1.0


def test_box_hanging_over_the_edge_is_clipped():
    # box is 15x15 but only its 5x5 corner is on the shelf
    assert coverage_ratio(SHELF, [(5, 5, 20, 20)]) == 0.25


def test_non_grid_aligned_box_is_exact():
    # 3.3 x 10 = 33 of 100. The 40x40 sampling grid answers 0.325 --
    # this is the accuracy bug the exact implementation fixes.
    assert coverage_ratio(SHELF, [(0, 0, 3.3, 10)]) == 0.33


