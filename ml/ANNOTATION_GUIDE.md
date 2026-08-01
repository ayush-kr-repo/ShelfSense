# ShelfSense Annotation Guide

The single standard for labeling ShelfSense training data. **Consistency matters more than
volume** — this project has measured that directly: a retrain with more annotations but mixed
conventions *reduced* box accuracy from 0.34 to 0.10, while an 85-image consistently-labeled
dataset matched a 1,706-image mixed one on the target class.

If a judgment call isn't covered here, add it here before you make it twice.

---

## Classes

| Class | What it is | What it is NOT |
|---|---|---|
| `shelf` | One **rack bay** — the storage slot bounded by two uprights | Not a horizontal beam. Not a whole rack run. Not a column of boxes. |
| `box` | One **contiguous stack or unit load** of cartons | Not each carton within a shrink-wrapped pallet load. |
| `pallet` | One wooden/plastic **pallet base** | Not the goods sitting on it. |

---

## `shelf` — rack bays

**Rule:** one label per bay, **upright to upright** horizontally, **floor to top of rack**
vertically.

- ✅ Follow the **metal structure**, not the cardboard sitting in it
- ✅ Adjacent bays share an upright — boxes should touch, not overlap
- ✅ A bay counts even if partly empty; a bay is a *slot*, not its contents
- ❌ Never label a horizontal beam or plank
- ❌ Never let one label span two bays
- ⏭️ **Skip** any bay less than ~⅓ visible, or dissolving into background blur

**Judgment call — perspective runs:** in a receding aisle, label bays while they remain clearly
resolvable. Once they become slivers, stop. Don't label what you can't see the edges of.

---

## `box` — cartons and unit loads

**Rule:** one label per **contiguous unit**. Interpretation depends on how goods are packed:

| Scene | One label = |
|---|---|
| Shrink-wrapped pallet load | The whole wrapped load |
| Loose cartons stacked freely | Each individually visible carton |
| Dense uniform stack, no separation visible | The contiguous stack |

- ✅ Label the **visible extent only** — never guess what's hidden behind an upright
- ❌ **Never let a label cross a shelf beam.** Goods on tier 1 and tier 2 are separate units.
- ❌ Don't include pallet wood or beam metal inside a box label — hug the cardboard

---

## `pallet` — always label them

Every visible pallet base gets a label, in **every** image. An unlabeled pallet is not neutral —
it teaches the model that pallets are background, which erodes the class.

Same visibility rule: label the visible portion, skip what's under ⅓ visible.

---

## Image selection

Curation is part of annotation. An image you skip costs nothing; an image you half-label costs
quality.

**Prefer:**
- Straight-on rack shots, 1–3 bays filling the frame
- Varied rack types (pallet racking, light shelving, different heights)
- Varied lighting — bright, dim, backlit
- Real photographs

**Avoid:**
- Long perspective runs with 50+ objects receding into mush
- Heavily watermarked stock imagery (watermark texture becomes training noise)
- AI-generated / rendered scenes (clean studio lighting ≠ real warehouse conditions)
- Floor-stack-only scenes — all box, no shelf, worsens class imbalance

**The 3-minute test:** if you cannot label every visible object cleanly in about three minutes,
discard the image and pick a better one.

---

## Completeness

**Every visible object of every class gets a label.** There is no "I didn't get to that part."
In training data, an unlabeled object is an explicit negative example — it actively teaches the
model that the thing is background.

Half-labeled images are worse than excluded images.

---

## Auto-labeling ("Find Objects with AI")

Use it as an assist, never an oracle:

1. Keep the confidence threshold **high**, not near zero
2. Accept only suggestions that already match these conventions
3. Delete everything else and draw the misses by hand

Segmentation tools latch onto visually distinct surfaces — bright beam edges, individual
cartons — which is orthogonal to the bay concept. **Shelves must be drawn by hand.**

---

## Targets

| Class | Current | Target |
|---|---|---|
| shelf | ~240 | 500–1,000 |
| box | ~4,400 | sufficient |
| pallet | ~950 | 1,500+ |

Class imbalance is inherent — one bay holds twenty boxes. What matters is the **absolute count
of the rare class**, not the ratio.

**Validation split:** ensure at least ~30 shelf instances land in `valid`. Below that, the
reported mAP is statistically meaningless and small changes are indistinguishable from noise.

---

## Before every training run

1. Print `data.yaml` — confirm `nc: 3` and `names: ['box', 'pallet', 'shelf']`
2. Count label class ids — confirm all three ids appear in both `train` and `valid`
3. Confirm the training cell points at the **current** dataset path, not a stale variable

All three of these have silently corrupted a run on this project at least once.
