"""Occupancy heatmap: each detected bay tinted by how full it is.

Drawn as an OVERLAY on the uploaded photo, at each bay's true detected
rectangle. The previous version drew every bay as a fixed 140x180 box on a
blank background, which lost three things at once:

  * true size - real bays here are 100-274 px wide by ~700 tall, so every one
    was drawn 3-8x too small and at the wrong aspect ratio
  * separation - bays 105 px apart drawn 140 wide overlapped each other, and
    which one was hidden came down to draw order
  * context - five rectangles on a dark background, with no way to tell which
    rectangle was which rack

Colour is a sequential ramp (viridis), not red-yellow-green. A traffic light
reads as a verdict - green good, red bad - which contradicts the health score,
where storage_efficiency (the largest weight) rewards exactly the fullness that
red would condemn. Occupancy is a magnitude, not a judgement.
"""

from pathlib import Path

import matplotlib
from matplotlib import cm
from PIL import Image, ImageDraw, ImageFont

FALLBACK_PX_PER_M = 100.0        # phase 1's own fallback when scale is relative
LOW_CONFIDENCE = 0.50            # below this, the bay is drawn as provisional
# NOTE: Shelf.confidence is YOLO's score for the SHELF detection - how sure it
# is that this rectangle is a rack bay. It is NOT a confidence in the occupancy
# figure; nothing produces one of those yet. The two correlate (a bay the model
# barely sees is also one it finds no boxes in) but they are different claims,
# so the legend says "detection confidence" rather than just "confidence".
FILL_ALPHA = 95                  # 0-255; the photo must stay readable underneath

INK = (248, 250, 252)
PANEL = (15, 23, 42)
DIM = (148, 163, 184)
_FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(str(_FONT_DIR / name), size)
    except OSError:
        return ImageFont.load_default()


def occupancy_color(value: float) -> tuple[int, int, int]:
    """Sequential ramp: low occupancy dark, high occupancy bright."""
    r, g, b, _ = cm.viridis(max(0.0, min(1.0, value)))
    return int(r * 255), int(g * 255), int(b * 255)


def _dashed_rect(draw: ImageDraw.ImageDraw, box, color, width: int, dash: int = 14):
    """A dashed outline - PIL has no native one. Marks a low-confidence bay."""
    x1, y1, x2, y2 = box
    for x in range(int(x1), int(x2), dash * 2):
        draw.line([x, y1, min(x + dash, x2), y1], fill=color, width=width)
        draw.line([x, y2, min(x + dash, x2), y2], fill=color, width=width)
    for y in range(int(y1), int(y2), dash * 2):
        draw.line([x1, y, x1, min(y + dash, y2)], fill=color, width=width)
        draw.line([x2, y, x2, min(y + dash, y2)], fill=color, width=width)


def _bay_rect(shelf, px_per_m: float) -> tuple[float, float, float, float]:
    """The bay's rectangle back in pixel space.

    Phase 1 stores the top-left in pixels and the size in metres, so the size
    is converted back with the same scale factor phase 1 divided by.
    """
    x, y = shelf.pixel_position.x, shelf.pixel_position.y
    return (x, y,
            x + shelf.estimated_dims.w * px_per_m,
            y + shelf.estimated_dims.h * px_per_m)


def _legend(img: Image.Image, draw: ImageDraw.ImageDraw) -> None:
    """Colour ramp plus the meaning of a dashed outline.

    Sits on its own opaque panel - the ramp lands on whatever bay happens to
    be in the corner, and pale text over a bright bay is unreadable.
    """
    w, h = img.size
    bar_w, bar_h = min(240, w // 4), 14
    pad = 10
    panel_w, panel_h = bar_w + pad * 2, bar_h + 54
    px, py = w - panel_w - 16, h - panel_h - 16
    draw.rectangle([px, py, px + panel_w, py + panel_h], fill=PANEL)

    small = _font(13)
    x0, y0 = px + pad, py + pad + 16
    draw.text((x0, py + pad), "empty", font=small, fill=INK)
    fw = draw.textbbox((0, 0), "full", font=small)[2]
    draw.text((x0 + bar_w - fw, py + pad), "full", font=small, fill=INK)
    for i in range(bar_w):
        draw.line([x0 + i, y0, x0 + i, y0 + bar_h],
                  fill=occupancy_color(i / max(bar_w - 1, 1)))
    draw.rectangle([x0, y0, x0 + bar_w, y0 + bar_h], outline=INK, width=1)
    draw.text((x0, y0 + bar_h + 6), "dashed = low detection confidence",
              font=small, fill=DIM)


def generate_heatmap(wh, out_path: str, image_path: str | None = None) -> None:
    """Draw each bay on the photo, tinted by occupancy and tagged with confidence."""
    if image_path and Path(image_path).exists():
        base = Image.open(image_path).convert("RGB")
    else:
        # no photo available: fall back to a blank canvas at the detections' extent
        span = max((_bay_rect(s, FALLBACK_PX_PER_M)[2] for s in wh.shelves), default=900)
        tall = max((_bay_rect(s, FALLBACK_PX_PER_M)[3] for s in wh.shelves), default=600)
        base = Image.new("RGB", (int(span) + 60, int(tall) + 60), PANEL)

    draw = ImageDraw.Draw(base)

    if not wh.shelves:
        msg = "No shelving detected in this photo"
        f = _font(22, bold=True)
        tw = draw.textbbox((0, 0), msg, font=f)[2]
        draw.rectangle([0, 0, base.width, 52], fill=PANEL)
        draw.text(((base.width - tw) / 2, 14), msg, font=f, fill=INK)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        base.save(out_path)
        return

    px_per_m = wh.scale.px_per_m or FALLBACK_PX_PER_M
    stroke = max(2, base.width // 350)
    label_font = _font(max(15, base.width // 60), bold=True)
    sub_font = _font(max(12, base.width // 80))

    # tint pass on its own layer, so overlapping bays blend instead of hiding
    tint = Image.new("RGBA", base.size, (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tint)
    for s in wh.shelves:
        tdraw.rectangle(_bay_rect(s, px_per_m),
                        fill=occupancy_color(s.occupancy_pct) + (FILL_ALPHA,))
    base = Image.alpha_composite(base.convert("RGBA"), tint).convert("RGB")
    draw = ImageDraw.Draw(base)

    for s in wh.shelves:
        rect = _bay_rect(s, px_per_m)
        low = s.confidence < LOW_CONFIDENCE
        if low:
            _dashed_rect(draw, rect, INK, stroke)
        else:
            draw.rectangle(rect, outline=INK, width=stroke)

        pct = f"{int(round(s.occupancy_pct * 100))}%"
        meta = f"{s.id} · det {s.confidence:.2f}"
        pw, ph = draw.textbbox((0, 0), pct, font=label_font)[2:]
        mw, mh = draw.textbbox((0, 0), meta, font=sub_font)[2:]

        bw, bh = max(pw, mw) + 14, ph + mh + 14
        bx, by = rect[0] + 4, rect[1] + 4
        bx = min(bx, base.width - bw - 2)            # keep the tag on-canvas
        by = min(by, base.height - bh - 2)
        draw.rectangle([bx, by, bx + bw, by + bh], fill=PANEL)
        draw.text((bx + 7, by + 4), pct, font=label_font, fill=INK)
        draw.text((bx + 7, by + ph + 7), meta, font=sub_font, fill=DIM)

    _legend(base, draw)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path)
