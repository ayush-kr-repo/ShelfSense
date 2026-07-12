from app.phase2 import (compute_sur, compute_health_score, evaluate_health,
                        generate_recommendations)
from tests.fixtures import make_warehouse, make_empty_warehouse


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
    result = evaluate_health(make_warehouse())
    assert result["score"] == 47.0
    assert result["band"] == "Poor"


def test_recommendations_fire_correctly():
    recs = generate_recommendations(make_warehouse())
    assert len(recs) == 1                 # only large-empty-region fires
    assert recs[0]["impact"] == "High"    # (low-fill rule needs TWO shelves <25%)


def test_recommendations_empty_warehouse_no_crash():
    recs = generate_recommendations(make_empty_warehouse())
    assert isinstance(recs, list)         # must not crash on zero shelves
