"""Tests for the occupancy evaluation harness.

These check the HARNESS, not the model. Whether MAE is good is a measurement
to report, not an assertion to make - but the arithmetic producing it has to
be right, or the number is worse than having none.
"""

from app.evaluation import iou, match_bays, summarise, validate_labels


# --------------------------------------------------------------- iou

def test_identical_boxes_have_iou_one():
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0


def test_disjoint_boxes_have_iou_zero():
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


def test_touching_boxes_have_iou_zero():
    # share an edge, no area in common
    assert iou((0, 0, 10, 10), (10, 0, 20, 10)) == 0.0


def test_half_overlap_iou_is_one_third():
    # intersection 50, union 100 + 100 - 50 = 150
    assert iou((0, 0, 10, 10), (5, 0, 15, 10)) == 50 / 150


def test_nested_box_iou_is_area_ratio():
    # inner 25 inside outer 100 -> union is the outer box
    assert iou((0, 0, 10, 10), (0, 0, 5, 5)) == 0.25


# --------------------------------------------------------------- matching

def _label(box, true_occ):
    return {"box": box, "true_occupancy": true_occ}


def _det(box, occ):
    return {"box": box, "occupancy": occ}


def test_each_detection_is_used_at_most_once():
    """Two labels, one detection: the better overlap wins, the other is a miss."""
    labels = [_label((0, 0, 10, 10), 0.5), _label((1, 1, 11, 11), 0.5)]
    dets = [_det((0, 0, 10, 10), 0.5)]
    pairs, unmatched = match_bays(labels, dets)
    assert len(pairs) == 1
    assert len(unmatched) == 1


def test_label_with_no_overlapping_detection_is_unmatched():
    pairs, unmatched = match_bays([_label((0, 0, 10, 10), 0.5)],
                                  [_det((50, 50, 60, 60), 0.5)])
    assert pairs == []
    assert len(unmatched) == 1


def test_weak_overlap_below_threshold_is_not_a_match():
    # iou = 50/150 = 0.33, under the 0.5 default
    pairs, unmatched = match_bays([_label((0, 0, 10, 10), 0.5)],
                                  [_det((5, 0, 15, 10), 0.5)])
    assert pairs == []
    assert len(unmatched) == 1


def test_shifted_but_overlapping_boxes_still_match():
    """Labels must survive a model that nudges its boxes slightly."""
    pairs, unmatched = match_bays([_label((0, 0, 10, 10), 0.5)],
                                  [_det((1, 1, 11, 11), 0.5)])
    assert len(pairs) == 1
    assert unmatched == []


# --------------------------------------------------------------- summarise

def test_perfect_predictions_give_zero_error():
    pairs = [(_label((0, 0, 1, 1), 0.5), _det((0, 0, 1, 1), 0.5))]
    s = summarise(pairs, n_labelled=1)
    assert s["mae_pp"] == 0.0
    assert s["bias_pp"] == 0.0
    assert s["within_target"] is True


def test_mae_is_in_percentage_points_not_fractions():
    """0.70 predicted vs 0.60 true is 10 percentage points, not 0.1."""
    pairs = [(_label((0, 0, 1, 1), 0.60), _det((0, 0, 1, 1), 0.70))]
    assert summarise(pairs, n_labelled=1)["mae_pp"] == 10.0


def test_bias_is_signed_but_mae_is_not():
    """One bay reads 20pp full, another 20pp empty: MAE 20, bias 0."""
    pairs = [(_label((0, 0, 1, 1), 0.50), _det((0, 0, 1, 1), 0.70)),
             (_label((2, 2, 3, 3), 0.50), _det((2, 2, 3, 3), 0.30))]
    s = summarise(pairs, n_labelled=2)
    assert s["mae_pp"] == 20.0
    assert s["bias_pp"] == 0.0


def test_positive_bias_means_reading_fuller_than_reality():
    pairs = [(_label((0, 0, 1, 1), 0.40), _det((0, 0, 1, 1), 0.60))]
    assert summarise(pairs, n_labelled=1)["bias_pp"] == 20.0


def test_unmatched_bays_lower_match_rate_not_mae():
    """A detection miss must not be laundered into an occupancy error."""
    pairs = [(_label((0, 0, 1, 1), 0.50), _det((0, 0, 1, 1), 0.50))]
    s = summarise(pairs, n_labelled=4)       # 3 labelled bays went undetected
    assert s["mae_pp"] == 0.0                # perfect on what was found
    assert s["match_rate"] == 0.25           # but only a quarter was found


def test_no_matches_reports_none_not_zero():
    """Zero MAE would read as perfect. Nothing was measured, so say so."""
    s = summarise([], n_labelled=5)
    assert s["mae_pp"] is None
    assert s["within_target"] is False


def test_target_boundary_is_inclusive():
    pairs = [(_label((0, 0, 1, 1), 0.50), _det((0, 0, 1, 1), 0.60))]
    assert summarise(pairs, n_labelled=1, target_mae_pp=10.0)["within_target"] is True
    assert summarise(pairs, n_labelled=1, target_mae_pp=9.0)["within_target"] is False


# --------------------------------------------------------------- label validation

def _entry(value):
    return {"image": "ml/eval/images/x.jpg", "bay": 1, "true_occupancy": value}


def test_valid_fractions_produce_no_problems():
    assert validate_labels([_entry(0.0), _entry(0.45), _entry(1.0)]) == []


def test_unlabelled_bays_are_not_problems():
    assert validate_labels([_entry(None)]) == []


def test_percentage_typed_as_whole_number_is_caught():
    """Typing 20 for "20%" is silent otherwise: the arithmetic runs and reports
    a 1952 pp error, which reads as model failure rather than a typo."""
    problems = validate_labels([_entry(20)])
    assert len(problems) == 1
    assert "0.20" in problems[0]          # suggests the correction


def test_negative_occupancy_is_caught():
    assert len(validate_labels([_entry(-0.1)])) == 1


def test_non_numeric_occupancy_is_caught():
    assert len(validate_labels([_entry("half")])) == 1


def test_every_bad_entry_is_reported_not_just_the_first():
    assert len(validate_labels([_entry(20), _entry(0.5), _entry(-1)])) == 2
