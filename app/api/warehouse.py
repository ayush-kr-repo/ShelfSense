from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TaskRecord, UserRecord
from app.auth import get_current_user
from app.schemas import Warehouse, Analytics
from app.phase1 import run_phase1
from app.phase2 import run_phase2
from app.models import WarehouseRecord
from app.heatmap import generate_heatmap
from app.schemas import WarehouseUpdate

import re
from pathlib import Path
from fastapi import UploadFile, File, Form
from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_BYTES = 8 * 1024 * 1024

router = APIRouter(prefix="/api/v1", tags=["warehouse"])

DEMO_IMAGE = "ml/test_warehouse.jpg" 

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

HEATMAP_DIR = Path("static/heatmaps")
HEATMAP_DIR.mkdir(parents=True, exist_ok=True)

def safe_id(warehouse_id: str) -> str:
    """Reject anything that could escape the uploads folder (path traversal)."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", warehouse_id):
        raise HTTPException(status_code=400, detail="Invalid warehouse_id")
    return warehouse_id


def normalise_to_jpeg(path: Path) -> None:
    """Rewrite an uploaded file as a real JPEG, whatever it arrived as.

    The browser's content-type is not a guarantee. An AVIF or HEIC photo - what
    a modern phone or a right-click-save produces - arrives as image/* and gets
    saved under a .jpg name, but OpenCV (which YOLO decodes with) cannot read
    it and returns no results at all. Pillow reads far more formats, so the
    file is decoded once here and written back as something the model can
    actually open. Raises 400 if it isn't a readable image.
    """
    try:
        with Image.open(path) as im:
            im.load()
            rgb = im.convert("RGB")
        rgb.save(path, "JPEG", quality=90)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=400,
                            detail="Could not read that image file") from exc


def uploaded_image(warehouse_id: str) -> Path | None:
    """This warehouse's own photo, or None if it has never had one."""
    path = UPLOAD_DIR / f"{safe_id(warehouse_id)}.jpg"
    return path if path.exists() else None


def analysis_image(warehouse_id: str) -> tuple[str, bool]:
    """The image to analyse, and whether it is the stand-in demo photo.

    Falling back to the demo keeps a fresh account from looking broken, but the
    caller MUST pass the flag on to the response. Without it the user sees a
    health score, SUR and recommendations computed from a photograph of someone
    else's warehouse, labelled as their own.
    """
    own = uploaded_image(warehouse_id)
    return (str(own), False) if own else (DEMO_IMAGE, True)


@router.get("/warehouse/{warehouse_id}", response_model=Warehouse)
def get_warehouse(warehouse_id: str,
                  px_per_m: float | None = None,
                  db: Session = Depends(get_db),
                  user: UserRecord = Depends(get_current_user)):
    record = owned_warehouse(warehouse_id, db, user)
    image_path, _ = analysis_image(warehouse_id)
    return run_phase1(warehouse_id, image_path, px_per_m, record.dimensions)

@router.get("/analytics/{warehouse_id}", response_model=Analytics)
def get_analytics(warehouse_id: str,
                  px_per_m: float | None = None,
                  db: Session = Depends(get_db),
                  user: UserRecord = Depends(get_current_user)):
    record = owned_warehouse(warehouse_id, db, user)
    dims = record.dimensions
    image_path, is_demo = analysis_image(warehouse_id)
    wh = run_phase1(warehouse_id, image_path, px_per_m, dims)
    analytics = run_phase2(wh)

    out = HEATMAP_DIR / f"{safe_id(warehouse_id)}.png"
    # overlay the image that was ACTUALLY analysed, so the picture and the
    # numbers always describe the same thing
    generate_heatmap(wh, str(out), image_path)
    analytics.heatmap_ref = f"/static/heatmaps/{warehouse_id}.png"      # served by static mount
    analytics.is_demo = is_demo
    if not is_demo:
        analytics.image_ref = f"/uploads/{warehouse_id}.jpg"
    analytics.shelf_count = len(wh.shelves)
    analytics.floor_dims = wh.dimensions

    return analytics

@router.post("/analyze")
def analyze(warehouse_id: str = "wh_demo",
            db: Session = Depends(get_db),
            user: UserRecord = Depends(get_current_user)):
    record = owned_warehouse(warehouse_id, db, user)
    task = TaskRecord(warehouse_id=warehouse_id, type="analyze", status="running")
    db.add(task); db.commit(); db.refresh(task)
    try:
        wh = run_phase1(warehouse_id, analysis_image(warehouse_id)[0], None, record.dimensions)
        run_phase2(wh)
        task.status, task.progress = "done", 100
    except Exception as e:
        task.status, task.error = "failed", str(e)
    db.commit()
    return {"task_id": task.id, "status": task.status}


@router.get("/task/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(TaskRecord, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task.id, "status": task.status,
            "progress": task.progress, "error": task.error}

@router.post("/warehouse/{warehouse_id}/upload")
def upload_image(warehouse_id: str,
                 file: UploadFile = File(...),
                 length_m: float | None = Form(None),
                 width_m: float | None = Form(None),
                 height_m: float | None = Form(None),
                 db: Session = Depends(get_db),
                 user: UserRecord = Depends(get_current_user)):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    dest = UPLOAD_DIR / f"{safe_id(warehouse_id)}.jpg"
    size = 0
    try:
        with open(dest, "wb") as out:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Image too large (max 8 MB)")
                out.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise

    normalise_to_jpeg(dest)      # .jpg must actually BE a jpeg

    dims = None
    if length_m and width_m:
        dims = {"length": length_m, "width": width_m, "height":height_m or 4.0}

    record = db.get(WarehouseRecord, warehouse_id)
    if record is None:
        record = WarehouseRecord(id=warehouse_id, owner_id=user.id,
                                 name = warehouse_id, image_path=str(dest), dimensions=dims)
        db.add(record)
    else:
        record.image_path = str(dest)
    db.commit()
    return {"warehouse_id": warehouse_id, "saved": file.filename, "dimensions": dims}

@router.get("/warehouses")
def list_warehouses(db: Session = Depends(get_db),
                    user: UserRecord = Depends(get_current_user)):
    rows = (db.query(WarehouseRecord)
              .filter(WarehouseRecord.owner_id == user.id)      # ← USER SCOPING
              .order_by(WarehouseRecord.created_at.desc())
              .all())
    return [{"id": r.id, "name": r.name,
             "image_path": r.image_path,
             "created_at": r.created_at} for r in rows]

def owned_warehouse(warehouse_id: str, db: Session, user: UserRecord) -> WarehouseRecord:
    """Fetch a warehouse only if it exists AND belongs to this user."""
    record = db.get(WarehouseRecord, warehouse_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    if record.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your warehouse")
    return record


@router.patch("/warehouse/{warehouse_id}/meta")
def update_warehouse(warehouse_id: str, body: WarehouseUpdate,
                     db: Session = Depends(get_db),
                     user: UserRecord = Depends(get_current_user)):
    record = owned_warehouse(warehouse_id, db, user)
    if body.name is not None:
        record.name = body.name
    if body.length_m and body.width_m:
        record.dimensions = {"length": body.length_m, "width": body.width_m,
                             "height": body.height_m or 4.0}
    if body.occupancy_pct is not None:
        record.manual_occupancy = body.occupancy_pct

    db.commit()
    return {"id": record.id, "name": record.name,
        "dimensions": record.dimensions,
        "manual_occupancy": record.manual_occupancy}


@router.delete("/warehouse/{warehouse_id}")
def delete_warehouse(warehouse_id: str,
                     db: Session = Depends(get_db),
                     user: UserRecord = Depends(get_current_user)):
    record = owned_warehouse(warehouse_id, db, user)
    (UPLOAD_DIR / f"{safe_id(warehouse_id)}.jpg").unlink(missing_ok=True)
    (HEATMAP_DIR / f"{safe_id(warehouse_id)}.png").unlink(missing_ok=True)
    db.delete(record); db.commit()
    return {"deleted": warehouse_id}
