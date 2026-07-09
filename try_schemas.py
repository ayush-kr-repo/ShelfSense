from schemas import Warehouse

wh = Warehouse(
    warehouse_id="wh_8a3f",
    image_count=3,
    scale={"mode": "reference", "px_per_m": 240.0, "confidence": 0.9},
    dimensions={"length": 20, "width": 12, "height": 4},
    shelves=[{
        "id": "S-A1",
        "pixel_position": {"x": 120, "y": 340},
        "position": {"x": 1.2, "y": 0.0, "z": 3.4},
        "estimated_dims": {"w": 2.0, "h": 2.2, "d": 0.6},
        "occupancy_pct": 0.70, "box_count": 84, "capacity_estimate": 120,
        "zone_class": "medium", "confidence": 0.91,
    }],
    floor_plan={"total_area": 240, "used_area": 150},
    metadata={"confidence_summary": 0.88},
)

# Pydantic can print the whole thing back as clean JSON:
print(wh.model_dump_json(indent=2))

