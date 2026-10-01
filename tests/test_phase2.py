from app.phase2 import (aisle_adequacy, compute_sur, compute_health_score,
                        evaluate_health, generate_recommendations)
from tests.fixtures import (make_warehouse, make_empty_warehouse,
                            make_uniform_warehouse)


def test_sur_matches_hand_computed():
    # (0.70*2.64 + 0.15*2.64) / 5.28 * 100 = 42.5
    assert compute_sur(make_warehouse()) == 42.5


def test_sur_empty_warehouse_is_zero_not_crash():
    assert compute_sur(make_empty_warehouse()) == 0.0


def test_health_score_matches_page9_example():
    example = {"storage_efficiency": 72, "accessibility": 60,
               "safety_compliance": 55, "space_balance": 68,
               "unused_space_index": 40, "expansion_readiness": 80}
    result = compute_health_score(example)
    assert result["score"] == 62.8
    assert result["band"] == "Fair"


def test_stub_warehouse_full_evaluation():
    # hand-computed from the two fixture bays (0.70 and 0.15 full):
    #   storage_efficiency  = SUR                              = 42.5
    #   space_balance       = 1 - pstdev/mean = 1 - 0.275/0.425 = 35.3
    #   unused_space_index  = mean(min(occ/0.80, 1))           = 53.1
    #   expansion_readiness = (240 - 150) / 240                = 37.5
    #   accessibility, safety_compliance = None -> 0.40 of weight redistributed
    #   (12.75 + 5.295 + 5.31 + 1.875) / 0.60 = 42.05 -> 42.1
    result = evaluate_health(make_warehouse())
    assert result["score"] == 42.1
    assert result["band"] == "Poor"
    assert result["unavailable"] == ["accessibility", "safety_compliance"]


def test_unmeasurable_subscore_is_excluded_not_faked():
    """safety_compliance returns None, so it must not appear in the breakdown
    and its weight must be redistributed - not filled with a constant."""
    result = evaluate_health(make_warehouse())
    assert "safety_compliance" not in result["subscores"]
    assert "safety_compliance" in result["unavailable"]


def test_all_subscores_present_behaves_as_a_plain_weighted_sum():
    """With nothing missing, renormalising divides by 1.0 and changes nothing."""
    example = {"storage_efficiency": 72, "accessibility": 60,
               "safety_compliance": 55, "space_balance": 68,
               "unused_space_index": 40, "expansion_readiness": 80}
    assert compute_health_score(example)["score"] == 62.8


def test_adding_stock_never_lowers_the_health_score():
    """The bug this catches: an empty warehouse scored 51.0 and a 10%-full one
    scored 49.0, because expansion_readiness was 100 at zero boxes and 0 at
    one. Filling a warehouse must never make it look worse."""
    scores = [evaluate_health(make_uniform_warehouse(f))["score"]
              for f in (0.0, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)]
    assert scores == sorted(scores), scores


def test_space_balance_uses_the_whole_distribution():
    """The old max-min version was decided by two bays. Widening the spread of
    every bay must lower the score smoothly."""
    balances = [evaluate_health(make_uniform_warehouse(0.5, spread=s))
                ["subscores"]["space_balance"] for s in (0.0, 0.1, 0.2, 0.3)]
    assert balances == sorted(balances, reverse=True)
    assert balances[0] == 100.0
    assert len(set(balances)) == len(balances)          # genuinely varies


def test_space_balance_ignores_one_outlier_among_many():
    """One empty bay in 20 must not pin the score near zero."""
    wh = make_uniform_warehouse(0.7, n=20)
    wh.shelves[0].occupancy_pct = 0.0
    assert evaluate_health(wh)["subscores"]["space_balance"] > 50.0


def test_unused_space_index_has_no_cliff_at_fifty_percent():
    """zone_class bucketing made 0.49 -> 0.51 jump the sub-score 0 -> 100."""
    below = evaluate_health(make_uniform_warehouse(0.49))["subscores"]["unused_space_index"]
    above = evaluate_health(make_uniform_warehouse(0.51))["subscores"]["unused_space_index"]
    assert abs(above - below) < 5.0


def test_expansion_readiness_tracks_free_floor_not_box_count():
    """It used to be 1 - box_count/capacity, and phase 1 set capacity == box
    count, so it was structurally ~0 for any warehouse holding stock."""
    roomy = evaluate_health(make_uniform_warehouse(0.5, used_area=20.0))
    packed = evaluate_health(make_uniform_warehouse(0.5, used_area=200.0))
    assert roomy["subscores"]["expansion_readiness"] > \
           packed["subscores"]["expansion_readiness"]


def test_accessibility_is_reported_unavailable():
    """One front-on photo cannot tell 'adjacent bays in one rack' (correct)
    from 'two racks with no aisle' (a fault), so it is not scored."""
    result = evaluate_health(make_warehouse())
    assert "accessibility" not in result["subscores"]
    assert result["unavailable"] == ["accessibility", "safety_compliance"]


def test_aisle_adequacy_tracks_bay_spacing():
    """The helper itself works, ready for a data source that can tell bays
    apart from rack runs. Bays 2.0m wide at 3.0m spacing leave a 1.0m aisle
    (clears the 0.9m minimum); at 2.2m spacing they leave 0.2m."""
    roomy = make_uniform_warehouse(0.5, spacing_m=3.0).shelves
    tight = make_uniform_warehouse(0.5, spacing_m=2.2).shelves
    assert aisle_adequacy(roomy) == 100.0
    assert aisle_adequacy(tight) < 50.0


def test_recommendations_fire_correctly():
    recs = generate_recommendations(make_warehouse())
    assert len(recs) == 1                 # only large-empty-region fires
    assert recs[0]["impact"] == "High"    # (low-fill rule needs TWO shelves <25%)


def test_recommendations_empty_warehouse_no_crash():
    recs = generate_recommendations(make_empty_warehouse())
    assert isinstance(recs, list)         # must not crash on zero shelves
