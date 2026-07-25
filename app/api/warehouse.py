from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TaskRecord, UserRecord
from app.auth import get_current_user
from app.schemas import Warehouse, Analytics
from app.phase1 import run_phase1
from app.phase2 import run_phase2
from app.worker import run_analysis
from app.models import WarehouseRecord
from app.heatmap import generate_heatmap
from app.schemas import WarehouseUpdate

import re
import shutil
from pathlib import Path
from fastapi import UploadFile, File, Form

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


def image_for(warehouse_id: str) -> str:
    """Use this warehouse's uploaded photo if it exists, else the demo image."""
    path = UPLOAD_DIR / f"{safe_id(warehouse_id)}.jpg"
    return str(path) if path.exists() else DEMO_IMAGE


@router.get("/warehouse/{warehouse_id}", response_model=Warehouse)
def get_warehouse(warehouse_id: str,
                  px_per_m: float | None = None,
                  user: UserRecord = Depends(get_current_user)):
    return run_phase1(warehouse_id, image_for(warehouse_id), px_per_m)


@router.get("/analytics/{warehouse_id}", response_model=Analytics)
def get_analytics(warehouse_id: str,
                  px_per_m: float | None = None,
                  db: Session = Depends(get_db),
                  user: UserRecord = Depends(get_current_user)):
    record = db.get(WarehouseRecord, warehouse_id)
    dims = record.dimensions if record else None
    wh = run_phase1(warehouse_id, image_for(warehouse_id), px_per_m, dims)
    analytics = run_phase2(wh)

    out = HEATMAP_DIR / f"{safe_id(warehouse_id)}.png"
    generate_heatmap(wh, str(out))      # Draw + save PNG
    analytics.heatmap_ref = f"/static/heatmaps/{warehouse_id}.png"      # served by static mount
    if (UPLOAD_DIR / f"{warehouse_id}.jpg").exists():
        analytics.image_ref = f"/uploads/{warehouse_id}.jpg"

    return analytics

@router.post("/analyze")
def analyze(warehouse_id: str = "wh_demo", db: Session = Depends(get_db)):
    task = TaskRecord(warehouse_id=warehouse_id, type="analyze")
    db.add(task); db.commit(); db.refresh(task)
    run_analysis.delay(task.id, warehouse_id)
    return {"task_id": task.id}


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
    with open(dest, "wb") as out:
        shutil.copyfileobj(file.file, out)      # stream bytes → disk

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
    db.commit()
    return {"id": record.id, "name": record.name, "dimensions": record.dimensions}


@router.delete("/warehouse/{warehouse_id}")
def delete_warehouse(warehouse_id: str,
                     db: Session = Depends(get_db),
                     user: UserRecord = Depends(get_current_user)):
    record = owned_warehouse(warehouse_id, db, user)
    (UPLOAD_DIR / f"{safe_id(warehouse_id)}.jpg").unlink(missing_ok=True)
    (HEATMAP_DIR / f"{safe_id(warehouse_id)}.png").unlink(missing_ok=True)
    db.delete(record); db.commit()
    return {"deleted": warehouse_id}
