from fastapi import FastAPI, Depends, HTTPException
from app.phase2 import run_phase2
from app.schemas import Warehouse, Analytics
from app.phase1 import run_phase1
from app.phase3 import run_phase3
from app.schemas import Warehouse, Analytics, Layout, OptimizeRequst
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine, SessionLocal
from app.models import LayoutRecord
from fastapi import Depends
from sqlalchemy.orm import Session
from app.worker import run_analysis
from app.models import TaskRecord

app = FastAPI(title="ShelfSense API")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/v1/analytics/{warehouse_id}", response_model=Analytics)
def get_analytics(warehouse_id: str):
    """Run app.phase 1 + app.phase 2 for a warehouse and return the evaluation."""
    wh = run_phase1(warehouse_id)     
    return run_phase2(wh)

@app.get("/api/v1/warehouse/{warehouse_id}", response_model=Warehouse)
def get_warehouse(warehouse_id: str):
    return run_phase1(warehouse_id)

app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()         # open the call
    try:
        yield db
    finally:
        db.close()
    
@app.post("/api/v1/optimize", response_model=Layout)
def optimize(req: OptimizeRequst, db: Session = Depends(get_db)):
    layout = run_phase3(req)

    record = LayoutRecord(
        warehouse_id="wh_demo",
        constraint_inputs=req.model_dump(),
        optimized_layout=layout.model_dump(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    layout.layout_id=record.id
    return layout

@app.get("/api/v1/layout/{layout_id}", response_model=Layout)
def get_layout(layout_id: int, db: Session = Depends(get_db)):
    record = db.get(LayoutRecord, layout_id)      # look up by primary key
    if record is None:
        raise HTTPException(status_code=404, detail="Layout not found")
    data = dict(record.optimized_layout)
    data["layout_id"] = record.id
    return data

@app.post("/api/v1/analyze")
def analyze(warehouse_id:str = "wh_demo", db:Session = Depends(get_db)):
    task = TaskRecord(warehouse_id=warehouse_id, type="analyze")
    db.add(task); db.commit(); db.refresh(task)
    run_analysis.delay(task.id, warehouse_id)
    return {"task_id": task.id}

@app.get("/api/v1/task/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(TaskRecord, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task.id, "status": task.status,
            "progress": task.progress, "error": task.error}
