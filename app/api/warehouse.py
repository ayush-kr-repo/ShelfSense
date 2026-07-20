from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TaskRecord, UserRecord
from app.auth import get_current_user
from app.schemas import Warehouse, Analytics
from app.phase1 import run_phase1
from app.phase2 import run_phase2
from app.worker import run_analysis

router = APIRouter(prefix="/api/v1", tags=["warehouse"])

DEMO_IMAGE = "ml/test_warehouse.jpg"   # TODO: replace with real per-warehouse uploads


@router.get("/warehouse/{warehouse_id}", response_model=Warehouse)
def get_warehouse(warehouse_id: str,
                  px_per_m: float | None = None,
                  user: UserRecord = Depends(get_current_user)):
    return run_phase1(warehouse_id, DEMO_IMAGE, px_per_m)


@router.get("/analytics/{warehouse_id}", response_model=Analytics)
def get_analytics(warehouse_id: str,
                  px_per_m: float | None = None,
                  user: UserRecord = Depends(get_current_user)):
    wh = run_phase1(warehouse_id, DEMO_IMAGE, px_per_m)
    return run_phase2(wh)


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
