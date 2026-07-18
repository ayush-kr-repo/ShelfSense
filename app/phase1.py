from pathlib import Path

from ultralytics import YOLO

from app.schemas import Warehouse, Shelf

WEIGHTS = Path("ml/weights/best.pt")
_model = None                      # loaded once, lazily (it's ~6MB + torch startup)


def get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO(str(WEIGHTS))
    return _model


def zone_class_for(occupancy: float) -> str:
    """Page 7 bands: <0.20 empty · 0.20-0.50 low · 0.50-0.80 medium · >0.80 high."""
    if occupancy < 0.20:
        return "empty"
    if occupancy < 0.50:
        return "low"
    if occupancy < 0.80:
        return "medium"
    return "high"


def run_phase1(warehouse_id: str, image_path: str) -> Warehouse:
    """Phase 1, for real: image -> YOLO detections -> Warehouse JSON."""
    results = get_model()(image_path)
    r = results[0]
    img_h, img_w = r.orig_shape

    # split detections by class name
    shelves_px, boxes_px = [], []
    for b in r.boxes:
        name = r.names[int(b.cls)]
        xyxy = [float(v) for v in b.xyxy[0]]          # [x1, y1, x2, y2] pixels
        if name == "shelf":
            shelves_px.append((xyxy, float(b.conf)))
        elif name == "box":
            boxes_px.append(xyxy)

    shelves = []
    for i, (s, conf) in enumerate(shelves_px):
        sx1, sy1, sx2, sy2 = s
        s_area = max((sx2 - sx1) * (sy2 - sy1), 1.0)

        # boxes whose CENTER falls inside this shelf = "on" it
        inside = [b for b in boxes_px
                  if sx1 <= (b[0] + b[2]) / 2 <= sx2
                  and sy1 <= (b[1] + b[3]) / 2 <= sy2]
        covered = sum((b[2] - b[0]) * (b[3] - b[1]) for b in inside)
        occupancy = min(covered / s_area, 1.0)

        shelves.append(Shelf(
            id=f"S-{i}",
            pixel_position={"x": int(sx1), "y": int(sy1)},
            # relative mode: no metres exist — px/100 keeps numbers readable
            position={"x": sx1 / 100, "y": 0.0, "z": sy1 / 100},
            estimated_dims={"w": (sx2 - sx1) / 100,
                            "h": (sy2 - sy1) / 100, "d": 0.6},
            occupancy_pct=round(occupancy, 2),
            box_count=len(inside),
            capacity_estimate=max(len(inside), 1),
            zone_class=zone_class_for(occupancy),
            confidence=round(conf, 2),
        ))

    return Warehouse(
        warehouse_id=warehouse_id,
        image_count=1,
        scale={"mode": "relative", "confidence": 0.3},   # honest: no metres yet
        dimensions=None,                                  # page 7 rule: relative -> null
        shelves=shelves,
        floor_plan={"total_area": float(img_w * img_h), "used_area": 0.0},
        metadata={"model_versions": {"yolo": "v8n-shelfsense-v2"},
                  "confidence_summary": 0.5},
    )
