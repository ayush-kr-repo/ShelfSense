from app.schemas import Warehouse, Shelf
from app.schemas import Analytics

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
    
    return round(occupied_vol/usable_vol * 100, 1)

HEALTH_WEIGHTS = {
    "storage_efficiency" : 0.30,
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
    if score >=55:
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
    spread = max(occ) - min(occ)        # 0 = perfectly even, 1 = wildly even
    return round((1-spread) * 100,1)

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
    Our app.phase 1 stub doesn't provide aisle widths or SKU weights yet,
    so we return a neutral placeholder rather than fake a precise number.
    TODO: compute for real once app.phase 1 supplies aisle + weight data.
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

LOW_FILL_THRESHOLD = 0.25       # "<25% full"
LARGE_EMPTY_AREA_M2 = 50.0      # free floor beyond this = "large empty region"

def generate_recommendations(wh: Warehouse) -> list[dict]:
    """Scan the warehouse and return a list of actionable recommendations"""
    recs = []

    low_fill = [s for s in wh.shelves if s.occupancy_pct < LOW_FILL_THRESHOLD]
    if len(low_fill) >= 2:
        ids = ", ".join(s.id for s in low_fill)
        recs.append({
            "condition": f"{len(low_fill)} shelves under 25% full ({ids})",
            "recommendation": "Consolidate stock onto fewer shelves; repurpose the freed slots",
            "impact": "Medium",
        })

    free_area = wh.floor_plan.total_area - wh.floor_plan.used_area
    if free_area >= LARGE_EMPTY_AREA_M2:
        recs.append({
            "condition": f"Large empty floor region (~{free_area:.0f} m2 unused)",
            "recommendation": "Add vertical racks to convert floor space into storage capacity.",
            "impact": "High",
        })

    return recs

def run_phase2(wh: Warehouse) -> Analytics:
    """Full app.phase 2: Take a Warehouse, return its Analytics."""
    return Analytics(
        warehouse_id=wh.warehouse_id,
        sur=compute_sur(wh),
        health=evaluate_health(wh),
        recommendations=generate_recommendations(wh),
    )