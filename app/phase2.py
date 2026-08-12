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
    """Weighted sum of six 0-100 subscores -> final score + band"""
    total = sum(subscores[name] * weight for name, weight in HEALTH_WEIGHTS.items())
    total = round(total, 1)
    return {"score": total, "band": health_band(total)}


def score_storage_efficiency(wh: Warehouse) -> float:
    """How well volume is used -> just the SUR"""
    return min(compute_sur(wh), 100.0)


def score_space_balance(wh: Warehouse) -> float:
    occ = [s.occupancy_pct for s in wh.shelves]
    if not occ:
        return 0.0
    spread = max(occ) - min(occ)        # 0 = perfectly even, 1 = wildly uneven
    return round((1 - spread) * 100, 1)


def score_unused_space_index(wh: Warehouse) -> float:
    """Fraction of shelves that are actually being used (not empty/low)."""
    if not wh.shelves:
        return 0.0
    wasted = sum(1 for s in wh.shelves if s.zone_class in ("empty", "low"))
    filled_fraction = 1 - wasted / len(wh.shelves)
    return round(filled_fraction * 100, 1)


def score_accessibility(wh: Warehouse) -> float:
    """Proxy: free floor space = room to move around."""
    fp = wh.floor_plan
    if fp.total_area == 0:
        return 0.0
    free_ratio = (fp.total_area - fp.used_area) / fp.total_area
    return round(free_ratio * 100, 1)


def score_expansion_readiness(wh: Warehouse) -> float:
    """Spare CAPACITY across shelves = room to grow."""
    total_cap = sum(s.capacity_estimate for s in wh.shelves)
    total_boxes = sum(s.box_count for s in wh.shelves)
    if total_cap == 0:
        return 0.0
    free_capacity_ratio = 1 - total_boxes / total_cap
    return round(free_capacity_ratio * 100, 1)


def score_safety_compliance(wh: Warehouse) -> float:
    """Page 9 wants aisle-width (<80cm) and heavy-SKU-on-top checks.
    Phase 1 doesn't supply aisle widths or SKU weights yet, so we return a
    neutral placeholder rather than fake a precise number.
    TODO: compute for real once phase 1 supplies aisle + weight data.
    """
    return 60.0


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
    result["subscores"] = subscores     # keep the breakdown for the dashboard
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
