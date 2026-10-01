import statistics

from app.schemas import Warehouse, Shelf, Analytics


def shelf_volume(shelf: Shelf) -> float:
    """Volume a shelf could hold in cubic metres = w x h x d"""
    dims = shelf.estimated_dims
    return dims.w * dims.h * dims.d


def compute_sur(warehouse: Warehouse) -> float:
    """Storage Utilization Rate as a percentage"""
    usable_vol = sum(shelf_volume(s) for s in warehouse.shelves)
    occupied_vol = sum(s.occupancy_pct * shelf_volume(s) for s in warehouse.shelves)

    if usable_vol == 0:
        return 0.0

    return round(occupied_vol / usable_vol * 100, 1)


HEALTH_WEIGHTS = {
    "storage_efficiency": 0.30,
    "accessibility": 0.20,
    "safety_compliance": 0.20,
    "space_balance": 0.15,
    "unused_space_index": 0.10,
    "expansion_readiness": 0.05,
}


def health_band(score: float) -> str:
    """Map a 0-100 score to a label"""
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 55:
        return "Fair"
    return "Poor"


def compute_health_score(subscores: dict) -> dict:
    """Weighted mean of the 0-100 sub-scores that could actually be measured.

    A sub-score of None means "not measurable from this input". Its weight is
    redistributed over the rest instead of being filled with a constant, so the
    result always spans a real 0-100. The old version substituted a fixed 60.0
    for safety_compliance, which pinned 12 points into every score ever
    produced and made the true range 12-92.
    """
    available = {k: v for k, v in subscores.items() if v is not None}
    weight_sum = sum(HEALTH_WEIGHTS[k] for k in available)
    if weight_sum == 0:
        return {"score": 0.0, "band": health_band(0.0),
                "unavailable": sorted(subscores)}
    total = round(
        sum(available[k] * HEALTH_WEIGHTS[k] for k in available) / weight_sum, 1)
    return {"score": total, "band": health_band(total),
            "unavailable": sorted(k for k, v in subscores.items() if v is None)}


def score_storage_efficiency(wh: Warehouse) -> float:
    """How well volume is used -> just the SUR"""
    return min(compute_sur(wh), 100.0)


def score_space_balance(wh: Warehouse) -> float:
    """How evenly stock is spread across bays, over the WHOLE distribution.

    Uses the coefficient of variation (spread relative to the mean). The old
    version was max(occ) - min(occ), so with 100 bays a single empty one
    pinned the score near zero and the other 99 were ignored entirely.
    """
    occ = [s.occupancy_pct for s in wh.shelves]
    if not occ:
        return 0.0
    mean = sum(occ) / len(occ)
    if mean == 0:
        return 100.0                    # nothing stored anywhere is trivially even
    cv = statistics.pstdev(occ) / mean
    return round(max(0.0, 1 - cv) * 100, 1)


TARGET_FILL = 0.80              # a bay at or above this is fully productive


def score_unused_space_index(wh: Warehouse) -> float:
    """How close each bay is to a healthy fill level, averaged over all bays.

    Continuous: a bay at 40% contributes 50, not 0. The old version bucketed on
    zone_class, so 49% full counted as wasted and 51% as fully productive -- a
    17-point jump in the total health score from one box crossing a threshold.
    """
    if not wh.shelves:
        return 0.0
    productive = sum(min(s.occupancy_pct / TARGET_FILL, 1.0) for s in wh.shelves)
    return round(productive / len(wh.shelves) * 100, 1)


MIN_AISLE_M = 0.9               # a working aisle between two bays


def _gap_m(a: Shelf, b: Shelf) -> float:
    """Clear distance between two bays in the observed plane, in metres.

    Positions come from a single photo, so x runs across the image and z down
    it; a bay occupies [x, x+w] by [z, z+h]. Two rectangles overlapping on
    both axes have a gap of zero.
    """
    dx = max(a.position.x - (b.position.x + b.estimated_dims.w),
             b.position.x - (a.position.x + a.estimated_dims.w), 0.0)
    dz = max(a.position.z - (b.position.z + b.estimated_dims.h),
             b.position.z - (a.position.z + a.estimated_dims.h), 0.0)
    return max(dx, dz)


def aisle_adequacy(shelves: list[Shelf]) -> float:
    """Mean nearest-neighbour gap between bays, scored against MIN_AISLE_M.

    Ready for use once a data source can tell bays apart from rack runs --
    fiducial-derived poses or multi-view capture. Not wired into the health
    score yet; see score_accessibility for why.
    """
    if len(shelves) < 2:
        return 100.0                    # nothing to obstruct anything
    scores = []
    for i, a in enumerate(shelves):
        nearest = min(_gap_m(a, b) for j, b in enumerate(shelves) if j != i)
        scores.append(min(nearest / MIN_AISLE_M, 1.0))
    return round(sum(scores) / len(scores) * 100, 1)


def score_accessibility(wh: Warehouse) -> float | None:
    """Not measurable from a single photograph.

    The old version returned free floor area, which is a linear function of
    shelf count: it never varied with layout, and an empty warehouse scored
    100 for "accessibility". That metric was real but misnamed, and now lives
    correctly named as expansion_readiness.

    Measuring it properly means asking whether bays are far enough apart to
    work between -- which aisle_adequacy() computes. But one front-on photo
    cannot separate "adjacent bays within one rack run", where touching is
    correct, from "two rack runs with no aisle", where it is a fault. Scoring
    the gap anyway rates normal racking as inaccessible. Rather than trade a
    meaningless number for a misleading one, this returns None and its weight
    is redistributed.
    TODO: wire up aisle_adequacy() once bays carry a rack id (fiducial poses).
    """
    return None


def score_expansion_readiness(wh: Warehouse) -> float:
    """Room to GROW: how much floor is still unracked and could take shelving.

    The old version was 1 - box_count / capacity_estimate, and phase 1 defined
    capacity_estimate AS the box count -- so this was structurally ~0 for every
    warehouse holding any stock, and 100 for an empty one. That discontinuity
    is why adding the first box to an empty warehouse LOWERED its health score.
    """
    fp = wh.floor_plan
    if fp.total_area <= 0:
        return 0.0
    free_ratio = max(0.0, (fp.total_area - fp.used_area) / fp.total_area)
    return round(free_ratio * 100, 1)


def score_safety_compliance(wh: Warehouse) -> float | None:
    """Aisle-width and heavy-SKU-on-top checks need data phase 1 can't supply.

    Returns None = "not measurable", so compute_health_score redistributes this
    weight over the sub-scores that ARE measurable. It used to return a fixed
    60.0, which at weight 0.20 baked 12 points into every score and capped the
    real range at 12-92 while the UI claimed 0-100.
    TODO: compute for real once phase 1 supplies aisle + weight data.
    """
    return None


def evaluate_health(wh: Warehouse) -> dict:
    """Compute all six sub-scores, then the weighted Health Score."""
    subscores = {
        "storage_efficiency": score_storage_efficiency(wh),
        "accessibility": score_accessibility(wh),
        "safety_compliance": score_safety_compliance(wh),
        "space_balance": score_space_balance(wh),
        "unused_space_index": score_unused_space_index(wh),
        "expansion_readiness": score_expansion_readiness(wh),
    }
    result = compute_health_score(subscores)
    # report only what was measured; `unavailable` names the rest
    result["subscores"] = {k: v for k, v in subscores.items() if v is not None}
    return result


# ---------------------------------------------------------------
# Recommendation rules
# Each rule takes a Warehouse and returns a dict or None.
# "points" is the estimated health-score gain — used only for ranking.
# ---------------------------------------------------------------

LOW_FILL_THRESHOLD = 0.25          # a bay under this counts as nearly empty
LARGE_EMPTY_AREA_M2 = 50.0         # free floor beyond this is worth racking
EFFECTIVE_AREA_PER_SHELF_M2 = 2.4  # 1.2 m² footprint plus an aisle allowance
FLOOR_STACK_THRESHOLD = 3          # fewer floor boxes than this isn't worth flagging


def _impact_label(points: float) -> str:
    if points >= 10:
        return "High"
    if points >= 4:
        return "Medium"
    return "Low"


def rule_no_detections(wh: Warehouse):
    if wh.shelves:
        return None
    return {
        "condition": "No shelving was detected in this photo",
        "recommendation": ("Upload a straight-on photo with the rack uprights visible. "
                           "Detection is unreliable at steep angles or in low light."),
        "points": 15.0,
    }


def rule_floor_stacking(wh: Warehouse):
    count = wh.floor_plan.unshelved_boxes
    if count < FLOOR_STACK_THRESHOLD:
        return None
    emptiest = min(wh.shelves, key=lambda s: s.occupancy_pct, default=None)
    if emptiest is not None and emptiest.occupancy_pct < 0.6:
        where = (f" {emptiest.id} is only {emptiest.occupancy_pct:.0%} full "
                 f"and could take them.")
    else:
        where = " Existing racking is near capacity, so this likely needs more shelving."
    return {
        "condition": f"{count} boxes are stacked on the floor rather than on racking",
        "recommendation": ("Floor-stacked stock blocks aisles, is slower to pick, and "
                           "is a safety risk." + where),
        "points": min(6.0 + 0.5 * count, 14.0),
    }


def rule_underused_bays(wh: Warehouse):
    low = [s for s in wh.shelves if s.occupancy_pct < LOW_FILL_THRESHOLD]
    if len(low) < 2:
        return None
    detail = ", ".join(f"{s.id} at {s.occupancy_pct:.0%}" for s in low)
    freed = len(low) - 1
    return {
        "condition": f"{len(low)} bays are under 25% full — {detail}",
        "recommendation": (f"Consolidate this stock onto one bay. That frees {freed} "
                           f"bay{'s' if freed != 1 else ''} for incoming inventory "
                           f"without adding any racking."),
        "points": 3.0 + 2.5 * len(low),
    }


def rule_free_floor(wh: Warehouse):
    if wh.dimensions is None:
        return None
    free_area = wh.floor_plan.total_area - wh.floor_plan.used_area
    if free_area < LARGE_EMPTY_AREA_M2:
        return None
    extra = int(free_area / EFFECTIVE_AREA_PER_SHELF_M2)
    return {
        "condition": f"About {free_area:.0f} m² of floor is unracked",
        "recommendation": (f"That space fits roughly {extra} more shelves including aisles. "
                           f"Use the Capacity Planner below to see the layout."),
        "points": 12.0,
    }


def rule_missing_dimensions(wh: Warehouse):
    if wh.dimensions is not None:
        return None
    return {
        "condition": "Floor dimensions have not been set",
        "recommendation": ("Add this warehouse's floor size from its dashboard card "
                           "to unlock space and capacity analysis."),
        "points": 1.0,
    }


RULES = [
    rule_no_detections,
    rule_floor_stacking,
    rule_underused_bays,
    rule_free_floor,
    rule_missing_dimensions,
]


def generate_recommendations(wh: Warehouse) -> list[dict]:
    """Run every rule, keep the ones that fired, rank by estimated impact."""
    fired = [result for rule in RULES if (result := rule(wh)) is not None]
    fired.sort(key=lambda r: r["points"], reverse=True)
    return [{"condition": r["condition"],
             "recommendation": r["recommendation"],
             "impact": _impact_label(r["points"])}
            for r in fired]


def run_phase2(wh: Warehouse) -> Analytics:
    """Full phase 2: take a Warehouse, return its Analytics."""
    return Analytics(
        warehouse_id=wh.warehouse_id,
        sur=compute_sur(wh),
        health=evaluate_health(wh),
        recommendations=generate_recommendations(wh),
    )
