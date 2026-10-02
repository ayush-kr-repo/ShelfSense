"""Occupancy ground-truth evaluation.

Phase 1 estimates how full each rack bay is. Until now nothing checked that
estimate against reality, which is why the project's metrics table carries
"occupancy mean absolute error - not measured".

Labels are stored against a bay's bounding box, not its index, and matched to
detections by overlap at scoring time. That matters for two reasons:

  * labels survive a model change - S-3 in v3 is not S-3 in v4, but the bay in
    the top-left corner is still the same bay
  * detection error and occupancy error stay separate. MAE is computed over
    matched bays only, and the match rate is reported alongside it, so a drop
    in detection recall can't masquerade as an occupancy regression.
"""

from statistics import mean

Box = tuple[float, float, float, float]      # x1, y1, x2, y2 in pixels


def iou(a: Box, b: Box) -> float:
    """Intersection over union of two axis-aligned boxes."""
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = max(a[2] - a[0], 0) * max(a[3] - a[1], 0)
    area_b = max(b[2] - b[0], 0) * max(b[3] - b[1], 0)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def match_bays(labelled: list[dict], detected: list[dict],
               min_iou: float = 0.5) -> tuple[list[tuple[dict, dict]], list[dict]]:
    """Greedily pair each labelled bay with the detection it overlaps most.

    Each detection is used at most once. Returns (pairs, unmatched_labels).
    A label with no detection above min_iou is a detection miss, not an
    occupancy error, and is excluded from MAE.
    """
    pairs, unmatched, taken = [], [], set()
    for label in labelled:
        best, best_iou = None, min_iou
        for i, det in enumerate(detected):
            if i in taken:
                continue
            score = iou(tuple(label["box"]), tuple(det["box"]))
            if score >= best_iou:
                best, best_iou = i, score
        if best is None:
            unmatched.append(label)
        else:
            taken.add(best)
            pairs.append((label, detected[best]))
    return pairs, unmatched


def summarise(pairs: list[tuple[dict, dict]], n_labelled: int,
              target_mae_pp: float = 10.0) -> dict:
    """Error statistics over matched bays, in occupancy PERCENTAGE POINTS.

    bias is the signed mean: positive means the estimate reads fuller than the
    bay really is. That direction matters more than its size - a planner that
    overstates how full a warehouse is will refuse stock it could have taken.
    """
    if not pairs:
        return {"n_labelled": n_labelled, "n_matched": 0, "match_rate": 0.0,
                "mae_pp": None, "bias_pp": None, "max_err_pp": None,
                "within_target": False, "target_mae_pp": target_mae_pp}

    errors = [(d["occupancy"] - l["true_occupancy"]) * 100 for l, d in pairs]
    mae = mean(abs(e) for e in errors)
    return {
        "n_labelled": n_labelled,
        "n_matched": len(pairs),
        "match_rate": round(len(pairs) / n_labelled, 3) if n_labelled else 0.0,
        "mae_pp": round(mae, 2),
        "bias_pp": round(mean(errors), 2),
        "max_err_pp": round(max(abs(e) for e in errors), 2),
        "within_target": mae <= target_mae_pp,
        "target_mae_pp": target_mae_pp,
    }


def validate_labels(entries: list[dict]) -> list[str]:
    """Problems with hand-entered ground truth, as human-readable strings.

    true_occupancy is a FRACTION. Typing 20 for "20%" is the easy slip, and it
    is silent: the arithmetic still runs and reports a 1952 pp error, which
    reads as a catastrophic model failure rather than a typo. Catch it here.
    """
    problems = []
    for e in entries:
        value = e.get("true_occupancy")
        if value is None:
            continue
        where = f"{e['image']} bay {e['bay']}"
        if not isinstance(value, (int, float)):
            problems.append(f"{where}: true_occupancy must be a number, got {value!r}")
        elif not 0.0 <= value <= 1.0:
            hint = f" (did you mean {value / 100:.2f}?)" if 1 < value <= 100 else ""
            problems.append(f"{where}: true_occupancy must be 0.0-1.0, got {value}{hint}")
    return problems
