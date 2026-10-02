"""Build (or refresh) the occupancy ground-truth template.

    uv run python ml/eval/make_labels.py

Runs phase 1 over the evaluation images, writes one entry per detected bay to
ml/eval/labels.json with `true_occupancy: null`, and renders an annotated copy
of each image to ml/eval/annotated/ with every bay outlined and numbered.

Then you fill in `true_occupancy` by eye, bay by bay, as a fraction 0.0-1.0.

The annotated images deliberately show ONLY the bay outlines, never the model's
box detections or its occupancy estimate. Seeing the prediction before judging
the truth is how a ground-truth set quietly becomes a copy of the model.

Re-running is safe: any `true_occupancy` you have already entered is carried
over by matching bounding boxes, so refreshing after a model change keeps your
work. Bays that can no longer be matched are reported, not silently dropped.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PIL import Image, ImageDraw          # noqa: E402  (after sys.path fix)

from app.evaluation import iou            # noqa: E402
from app.phase1 import run_phase1         # noqa: E402

# The frozen evaluation set. These live under ml/ rather than uploads/ because
# uploads/ is gitignored - a benchmark nobody else can reproduce is not a
# benchmark. Add images here deliberately; don't point this at a live folder.
IMAGES = sorted(p.as_posix() for p in Path("ml/eval/images").glob("*.jpg"))

OUT = Path("ml/eval/labels.json")
ANNOTATED = Path("ml/eval/annotated")

OUTLINE = (56, 189, 248)      # sky-400
TEXT_BG = (15, 23, 42)        # slate-900


def detect_bays(image_path: str) -> list[dict]:
    """Phase 1's bays for one image, as plain dicts keyed by pixel box."""
    wh = run_phase1("eval", image_path)
    bays = []
    for s in wh.shelves:
        x1, y1 = s.pixel_position.x, s.pixel_position.y
        # estimated_dims are metres at the phase-1 fallback scale of 100 px/m
        bays.append({
            "box": [float(x1), float(y1),
                    float(x1 + s.estimated_dims.w * 100),
                    float(y1 + s.estimated_dims.h * 100)],
            "occupancy": s.occupancy_pct,
        })
    return bays


def annotate(image_path: str, bays: list[dict], out_path: Path) -> None:
    """Outline and number each bay so a human can judge it by eye."""
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    width = max(2, img.width // 400)
    for i, bay in enumerate(bays):
        x1, y1, x2, y2 = bay["box"]
        draw.rectangle([x1, y1, x2, y2], outline=OUTLINE, width=width)
        tag = str(i)
        tw, th = draw.textbbox((0, 0), tag)[2:]
        draw.rectangle([x1, y1, x1 + tw + 10, y1 + th + 8], fill=TEXT_BG)
        draw.text((x1 + 5, y1 + 4), tag, fill=OUTLINE)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def carry_over(old: list[dict], new: list[dict]) -> int:
    """Copy already-entered truths onto refreshed detections, matched by box."""
    kept = 0
    for entry in new:
        for prev in old:
            if (prev.get("true_occupancy") is not None
                    and prev["image"] == entry["image"]
                    and iou(tuple(prev["box"]), tuple(entry["box"])) >= 0.5):
                entry["true_occupancy"] = prev["true_occupancy"]
                kept += 1
                break
    return kept


def main() -> None:
    previous = []
    if OUT.exists():
        previous = json.loads(OUT.read_text())["bays"]

    entries = []
    for image_path in IMAGES:
        if not Path(image_path).exists():
            print(f"  skipping {image_path} (not found)")
            continue
        bays = detect_bays(image_path)
        name = Path(image_path).stem
        annotate(image_path, bays, ANNOTATED / f"{name}.png")
        for i, bay in enumerate(bays):
            entries.append({
                "image": image_path,
                "bay": i,
                "box": [round(v, 1) for v in bay["box"]],
                "true_occupancy": None,          # <-- you fill this in
            })
        print(f"  {image_path:26} {len(bays):2} bays -> annotated/{name}.png")

    kept = carry_over(previous, entries)
    lost = sum(1 for p in previous if p.get("true_occupancy") is not None) - kept

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "_readme": ("Fill in true_occupancy for each bay as a fraction 0.0-1.0, "
                    "judging from ml/eval/annotated/. Leave null to skip a bay."),
        "bays": entries,
    }, indent=2))

    todo = sum(1 for e in entries if e["true_occupancy"] is None)
    print(f"\n  {len(entries)} bays total, {kept} truths carried over, {todo} to label")
    if lost > 0:
        print(f"  WARNING: {lost} previously-labelled bays no longer match a detection")
    print(f"  -> edit {OUT}, then: uv run python ml/eval/score.py")


if __name__ == "__main__":
    main()
