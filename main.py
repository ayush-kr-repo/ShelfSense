from fastapi import FastAPI
from phase2 import run_phase2
from schemas import Warehouse, Analytics
from phase1 import run_phase1
from phase3 import run_phase3
from schemas import Warehouse, Analytics, Layout, OptimizeRequst
from fastapi.staticfiles import StaticFiles
from database import Base, engine, SessionLocal
from  models import LayoutRecord
from fastapi import Depends
from sqlalchemy.orm import Session

app = FastAPI(title="ShelfSense API")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/v1/analytics/{warehouse_id}", response_model=Analytics)
def get_analytics(warehouse_id: str):
    """Run Phase 1 + Phase 2 for a warehouse and return the evaluation."""
    wh = run_phase1(warehouse_id)     
    return run_phase2(wh)

@app.get("/api/v1/warehouse/{warehouse_id}", response_model=Warehouse)
def get_warehouse(warehouse_id: str):
    return run_phase1(warehouse_id)

app.mount("/static", StaticFiles(directory="static"), name="static")

Base.metadata.create_all(bind=engine)       # create any missing tables

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
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Layout not found")
    data = dict(record.optimized_layout)
    data["layout_id"] = record.id
    return data
