"""Hand-written warehouses with known, hand-computed properties."""

from app.schemas import Warehouse, zone_class_for

def make_warehouse() -> Warehouse:
    """Mirror of the Phase-1 stub: 2 shelves, SUR=42.5, health=47.0/Poor."""
    return Warehouse(
        warehouse_id="wh_test",
        image_count=1,
        scale={"mode": "reference", "px_per_m": 240.0, "confidence": 0.9},
        dimensions={"length": 20, "width": 12, "height": 4},
        shelves=[
            {
                "id": "S-A1",
                "pixel_position": {"x": 120, "y": 340},
                "position": {"x": 1.2, "y": 0.0, "z": 3.4},
                "estimated_dims": {"w": 2.0, "h": 2.2, "d": 0.6},
                "occupancy_pct": 0.70, "box_count": 84, "capacity_estimate": 120,
                "zone_class": "medium", "confidence": 0.91,
            },
            {
                "id": "S-A2",
                "pixel_position": {"x": 320, "y": 340},
                "position": {"x": 4.0, "y": 0.0, "z": 3.4},
                "estimated_dims": {"w": 2.0, "h": 2.2, "d": 0.6},
                "occupancy_pct": 0.15, "box_count": 12, "capacity_estimate": 120,
                "zone_class": "empty", "confidence": 0.88,
            },
        ],
        floor_plan={"total_area": 240, "used_area": 150},
        metadata={"confidence_summary": 0.88},
    )

def make_empty_warehouse() -> Warehouse:
    """Zero shelves — the divide-by-zero ambush."""
    return Warehouse(
        warehouse_id="wh_empty",
        image_count=1,
        scale={"mode": "relative", "confidence": 0.5},
        shelves=[],
        floor_plan={"total_area": 240, "used_area": 0},
        metadata={"confidence_summary": 0.5},
    )

def valid_shelf_dict() -> dict:
    """A known-good shelf; tests break ONE field at a time."""
    return {
        "id": "S-OK",
        "pixel_position": {"x": 1, "y": 1},
        "position": {"x": 0, "y": 0, "z": 0},
        "estimated_dims": {"w": 1, "h": 1, "d": 1},
        "occupancy_pct": 0.5, "box_count": 1, "capacity_estimate": 10,
        "zone_class": "medium", "confidence": 0.9,
    }


def make_uniform_warehouse(fill: float, n: int = 10, spacing_m: float = 3.0,
                           used_area: float | None = None,
                           spread: float = 0.0) -> Warehouse:
    """A tunable warehouse for property tests.

    fill      occupancy of every bay (0..1)
    spacing_m centre-to-centre gap between bays; bays are 2.0 m wide, so the
              clear aisle is spacing_m - 2.0
    spread    alternate bays sit at fill +/- spread, to exercise space_balance
    """
    occs = [min(1.0, max(0.0, fill + (spread if i % 2 else -spread)))
            for i in range(n)]
    return Warehouse(
        warehouse_id="wh_uniform",
        image_count=1,
        scale={"mode": "reference", "px_per_m": 100.0, "confidence": 0.9},
        dimensions={"length": 20, "width": 12, "height": 4},
        shelves=[{
            "id": f"S{i}",
            "pixel_position": {"x": 0, "y": 0},
            "position": {"x": i * spacing_m, "y": 0.0, "z": 0.0},
            "estimated_dims": {"w": 2.0, "h": 2.2, "d": 0.6},
            "occupancy_pct": occs[i],
            "box_count": int(occs[i] * 20),
            "capacity_estimate": 20,
            "zone_class": zone_class_for(occs[i]),
            "confidence": 0.9,
        } for i in range(n)],
        floor_plan={"total_area": 240.0,
                    "used_area": n * 1.2 if used_area is None else used_area,
                    "unshelved_boxes": 0},
        metadata={"confidence_summary": 0.9},
    )
