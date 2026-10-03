from pathlib import Path

import torch
from ultralytics import YOLO

# One thread: free-tier hosts give a fraction of a core, and torch's
# default thread pool only adds contention and RSS there.
torch.set_num_threads(1)

from app.schemas import Warehouse, Shelf, zone_class_for

WEIGHTS = Path("ml/weights/best_clean.pt")
_model = None                      # loaded once, lazily (it's ~6MB + torch startup)

STANDARD_SHELF_FOOTPRINT_M2 = 1.2   # a typical shelf footprint (2.0 × 0.6 m)
TYPICAL_BOX_VOLUME_M3 = 0.036       # a 0.4 × 0.3 × 0.3 m carton

def get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO(str(WEIGHTS))
    return _model

def coverage_ratio(shelf_xyxy, boxes):
    """Fraction of the shelf rectangle covered by at least one box.

    Exact: the union area is computed by coordinate compression, so
    overlapping boxes are never double-counted and there is no
    sampling error.
    """
    sx1, sy1, sx2, sy2 = shelf_xyxy
    area = (sx2 - sx1) * (sy2 - sy1)
    if area <= 0:                                   # degenerate detection
        return 0.0

    # clip every box to the shelf; drop the ones that miss it entirely
    clipped = []
    for b in boxes:
        x1, y1 = max(b[0], sx1), max(b[1], sy1)
        x2, y2 = min(b[2], sx2), min(b[3], sy2)
        if x2 > x1 and y2 > y1:
            clipped.append((x1, y1, x2, y2))

    if not clipped:
        return 0.0

    # cut lines: coverage can only change at a box edge
    xs = sorted({v for r in clipped for v in (r[0], r[2])})
    ys = sorted({v for r in clipped for v in (r[1], r[3])})
    xi = {v: i for i, v in enumerate(xs)}
    yi = {v: i for i, v in enumerate(ys)}

    # every cell of this irregular grid is wholly covered or wholly empty
    covered = [[False] * (len(ys) - 1) for _ in range(len(xs) - 1)]
    for x1, y1, x2, y2 in clipped:
        for a in range(xi[x1], xi[x2]):
            row = covered[a]
            for b in range(yi[y1], yi[y2]):
                row[b] = True

    total = 0.0
    for a in range(len(xs) - 1):
        width = xs[a + 1] - xs[a]
        for b in range(len(ys) - 1):
            if covered[a][b]:
                total += width * (ys[b + 1] - ys[b])

    return total / area

def run_phase1(warehouse_id: str, image_path: str,
               px_per_m: float | None = None,
               dimensions: dict | None = None) -> Warehouse:
    """Phase 1, for real: image -> YOLO detections -> Warehouse JSON."""
    results = get_model()(image_path, conf=0.15)
    if not results:
        # OpenCV returns nothing for a format it can't decode - an AVIF or HEIC
        # file saved with a .jpg name, or a truncated upload. Without this the
        # failure surfaced as "IndexError: list index out of range".
        raise ValueError(f"Could not read image: {image_path}")
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

    # boxes whose centre isn't inside any detected bay = stock sitting on the floor
    def _on_a_shelf(b):
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        return any(s[0] <= cx <= s[2] and s[1] <= cy <= s[3] for s, _ in shelves_px)

    unshelved = sum(1 for b in boxes_px if not _on_a_shelf(b))

    f = px_per_m if px_per_m else 100.0
    shelves = []
    for i, (s, conf) in enumerate(shelves_px):
        sx1, sy1, sx2, sy2 = s

        # boxes whose CENTER falls inside this shelf = "on" it
        inside = [b for b in boxes_px
                  if sx1 <= (b[0] + b[2]) / 2 <= sx2
                  and sy1 <= (b[1] + b[3]) / 2 <= sy2]
        occupancy = coverage_ratio(s, boxes_px)

        shelves.append(Shelf(
            id=f"S-{i}",
            pixel_position={"x": int(sx1), "y": int(sy1)},
            position={"x": sx1 / f, "y": 0.0, "z": sy1 / f},
            estimated_dims={"w": (sx2 - sx1) / f,
                            "h": (sy2 - sy1) / f, "d": 0.6},
            occupancy_pct=round(occupancy, 2),
            box_count=len(inside),
            # capacity comes from GEOMETRY, not from what we happened to detect.
            # It used to be max(len(inside), 1), i.e. capacity == box_count, which
            # made phase 2's expansion_readiness score structurally always ~0.
            capacity_estimate=max(
                1, round((sx2 - sx1) / f * (sy2 - sy1) / f * 0.6 / TYPICAL_BOX_VOLUME_M3)
            ),
            zone_class=zone_class_for(occupancy),
            confidence=round(conf, 2),
        ))

    if dimensions:
        total_area = dimensions["length"] * dimensions["width"]
        used_area = round(len(shelves) * STANDARD_SHELF_FOOTPRINT_M2, 1)
        dims_obj = {"length": dimensions["length"], "width": dimensions["width"],
                    "height": dimensions.get("height", 4.0)}

    else:
        total_area = float(img_w * img_h)     # old pixel-area fallback
        used_area = 0.0
        dims_obj = None

    return Warehouse(
        warehouse_id=warehouse_id,
        image_count=1,
        scale=(
            {"mode": "reference", "px_per_m": px_per_m, "confidence": 0.7}
            if px_per_m else
            {"mode": "relative", "confidence": 0.3}
        ),
        dimensions=dims_obj,                                  
        shelves=shelves,
        floor_plan={"total_area": total_area, "used_area": used_area,
                    "unshelved_boxes": unshelved},
        metadata={"model_versions": {"yolo": "v8n-shelfsense-v2"},
                  "confidence_summary": 0.5},
    )
