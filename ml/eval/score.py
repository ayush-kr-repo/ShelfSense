"""Score phase 1's occupancy estimates against the hand labels.

    uv run python ml/eval/score.py

Reads ml/eval/labels.json, re-runs phase 1 on each image, matches labelled
bays to detections by bounding-box overlap, and reports mean absolute error in
occupancy percentage points - the project's "occupancy MAE" metric.

Predictions are recomputed here rather than read from the label file, so the
number always reflects the current code.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.evaluation import match_bays, summarise      # noqa: E402
from make_labels import detect_bays                   # noqa: E402

LABELS = Path("ml/eval/labels.json")
TARGET_MAE_PP = 10.0


def main() -> None:
    if not LABELS.exists():
        sys.exit("No labels yet. Run: uv run python ml/eval/make_labels.py")

    entries = json.loads(LABELS.read_text())["bays"]
    labelled = [e for e in entries if e.get("true_occupancy") is not None]
    if not labelled:
        sys.exit(f"No bays labelled yet. Fill in true_occupancy in {LABELS}.")

    by_image: dict[str, list[dict]] = {}
    for e in labelled:
        by_image.setdefault(e["image"], []).append(e)

    all_pairs, all_unmatched = [], []
    print(f"{'image':26} {'bay':>4} {'true':>6} {'pred':>6} {'err pp':>7}")
    print("-" * 54)

    for image_path, labels in sorted(by_image.items()):
        detected = detect_bays(image_path)
        pairs, unmatched = match_bays(labels, detected)
        all_pairs += pairs
        all_unmatched += unmatched
        for label, det in pairs:
            err = (det["occupancy"] - label["true_occupancy"]) * 100
            flag = "  <-- off" if abs(err) > TARGET_MAE_PP else ""
            print(f"{image_path:26} {label['bay']:>4} "
                  f"{label['true_occupancy']:6.2f} {det['occupancy']:6.2f} "
                  f"{err:+7.1f}{flag}")
        for label in unmatched:
            print(f"{image_path:26} {label['bay']:>4} "
                  f"{label['true_occupancy']:6.2f} {'--':>6} {'no det':>7}")

    s = summarise(all_pairs, n_labelled=len(labelled), target_mae_pp=TARGET_MAE_PP)
    print("-" * 54)
    print(f"  labelled bays      {s['n_labelled']}")
    print(f"  matched to a bay   {s['n_matched']}  (match rate {s['match_rate']:.0%})")
    if s["mae_pp"] is None:
        print("  MAE                not measurable - nothing matched")
        return
    print(f"  MAE                {s['mae_pp']:.2f} pp   (target <= {TARGET_MAE_PP:.0f})")
    print(f"  bias               {s['bias_pp']:+.2f} pp   "
          f"({'reads FULLER than reality' if s['bias_pp'] > 0 else 'reads emptier than reality'})")
    print(f"  worst bay          {s['max_err_pp']:.2f} pp")
    print(f"  within target      {'YES' if s['within_target'] else 'NO'}")

    if all_unmatched:
        print(f"\n  {len(all_unmatched)} labelled bays were not detected at all - "
              f"that is a DETECTION gap, not an occupancy error, and is excluded "
              f"from MAE above.")


if __name__ == "__main__":
    main()
