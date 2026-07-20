from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LayoutRecord, UserRecord
from app.auth import get_current_user
from app.schemas import Layout, OptimizeRequest
from app.phase3 import run_phase3

router = APIRouter(prefix="/api/v1", tags=["optimize"])

@router.post("/optimize", response_model=Layout)
def optimize(req: OptimizeRequest, db: Session = Depends(get_db)):
    layout = run_phase3(req)
    record = LayoutRecord(
        warehouse_id="wh_demo",
        constraint_inputs=req.model_dump(),
        optimized_layout=layout.model_dump(),
    )
    db.add(record); db.commit(); db.refresh(record)
    layout.layout_id = record.id
    return layout


@router.get("/layout/{layout_id}", response_model=Layout)
def get_layout(layout_id: int, db: Session = Depends(get_db)):
    record = db.get(LayoutRecord, layout_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Layout not found")
    data = dict(record.optimized_layout)
    data["layout_id"] = record.id
    return data
