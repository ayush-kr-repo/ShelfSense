from schemas import Warehouse

def run_phase1(warehouse_id: str) -> Warehouse:
    """Phase 1 : photos -> Warehouse
    
    Eventually runs YOLO + SAM + scale on real images. For now it returns
    a hand-built valid Warehouse so the rest of the system can run.
    """
    return Warehouse(
        warehouse_id=warehouse_id,
        image_count=1,
        scale={"mode": "reference", "px_per_m": 240.0,"confidence": 0.9},
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
