import time

from celery import Celery

from app.database import SessionLocal
from app.models import TaskRecord
from app.phase1 import run_phase1
from app.phase2 import run_phase2

# The Celery app : named, and pointed to Redis
celery_app = Celery("shelfsense", broker="redis://localhost:6379/0")

@celery_app.task
def run_analysis(task_id:int, warehouse_id:str):
    """The full P1->P2 pipeline, as a background job with progress."""
    db = SessionLocal()                      # workers open their OWN session
    task = db.get(TaskRecord, task_id)
    try:
        task.status = "running"; task.progress = 10; db.commit()

        wh = run_app.phase1(warehouse_id)        # someday: real YOLO/SAM, minutes
        time.sleep(2)                        # simulate slow CV so you can WATCH progress
        task.progress = 60; db.commit()

        analytics = run_app.phase2(wh)           # noqa: F841  (stored properly later)
        time.sleep(1)
        task.progress = 90; db.commit()

        task.status = "done"; task.progress = 100; db.commit()
    except Exception as e:
        task.status = "failed"; task.error = str(e); db.commit()
    finally:
        db.close()