"""Walk the unlabelled bays and record occupancy ground truth.

    uv run python ml/eval/label.py

For each bay it prints the path to that bay's crop in ml/eval/crops/. Open the
image, judge it, type a number. Saves after every answer, so you can stop with
`q` and pick up where you left off.

What to judge: the fraction of the OUTLINED RECTANGLE's visible face that is
covered by stock. Not volume - depth is invisible in a photograph, and that
limitation belongs in the error analysis, not in the labels.

  - include empty shelf levels; the outline runs floor to top of rack
  - two full levels out of four is about 0.5
  - judge the region as drawn, even where outlines overlap
  - round to the nearest 0.05; precision past that is invented

Accepts 0-1 (0.85) or 0-100 (85). Enter alone re-shows the bay,
`s` skips it, `b` goes back one, `q` saves and quits.
"""

import json
import sys
from pathlib import Path

LABELS = Path("ml/eval/labels.json")
CROPS = Path("ml/eval/crops")


def parse(raw: str) -> float | None:
    """Accept a fraction or a percentage; reject anything out of range."""
    try:
        value = float(raw)
    except ValueError:
        return None
    if value > 1.0:                 # typed 85 meaning 85%
        value /= 100.0
    if not 0.0 <= value <= 1.0:
        return None
    return round(value * 20) / 20   # snap to the nearest 0.05


def main() -> None:
    if not LABELS.exists():
        sys.exit("No labels.json. Run: uv run python ml/eval/make_labels.py")

    doc = json.loads(LABELS.read_text())
    bays = doc["bays"]

    def save() -> None:
        LABELS.write_text(json.dumps(doc, indent=2))

    todo = [i for i, b in enumerate(bays) if b["true_occupancy"] is None]
    if not todo:
        print("All bays already labelled. Run: uv run python ml/eval/score.py")
        return

    print(__doc__.split("Accepts")[0].strip())
    print(f"\n{len(todo)} bays to label ({len(bays) - len(todo)} already done).")
    print("Enter a number, or: s skip | b back | q save and quit\n")

    pos = 0
    while pos < len(todo):
        idx = todo[pos]
        entry = bays[idx]
        stem = Path(entry["image"]).stem
        crop = CROPS / f"{stem}_bay{entry['bay']}.png"
        x1, y1, x2, y2 = entry["box"]

        print(f"[{pos + 1}/{len(todo)}]  {stem}  bay {entry['bay']}"
              f"   ({int(x2 - x1)} x {int(y2 - y1)} px)")
        print(f"   {crop}")

        raw = input("   occupancy > ").strip().lower()

        if raw == "q":
            save()
            done = sum(1 for b in bays if b["true_occupancy"] is not None)
            print(f"\nSaved. {done}/{len(bays)} labelled.")
            return
        if raw == "b":
            pos = max(0, pos - 1)
            continue
        if raw == "s":
            pos += 1
            continue
        if raw == "":
            continue                # re-show this bay

        value = parse(raw)
        if value is None:
            print("   ! enter 0-1 (0.85) or 0-100 (85)")
            continue

        entry["true_occupancy"] = value
        save()
        print(f"   -> {value}")
        pos += 1

    save()
    done = sum(1 for b in bays if b["true_occupancy"] is not None)
    print(f"\nDone. {done}/{len(bays)} labelled.")
    print("Now run:  uv run python ml/eval/score.py")


if __name__ == "__main__":
    main()
