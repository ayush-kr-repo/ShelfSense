# ShelfSense AI 📦

> An AI warehouse digital twin: photograph your warehouse, get health analytics, a mathematically optimized shelf layout, and an interactive 3D view — before moving a single real shelf.

ShelfSense transforms warehouse photos into a structured digital model (Phase 1), evaluates warehouse efficiency and provides actionable recommendations (Phase 2), optimizes the warehouse layout using mathematical constraint solving (Phase 3), and finally renders the optimized warehouse as an interactive browser-based 3D digital twin.

**Status:** The complete pipeline runs end-to-end on real uploaded warehouse images. A fine-tuned YOLOv8 object detector (trained on a custom warehouse dataset) powers perception, while analytics, optimization, asynchronous processing, database persistence, JWT authentication, and the 3D visualization complete the workflow. Detection currently performs best on pallets, with shelf and box accuracy improving as additional training data is collected. The system can be upgraded simply by replacing the YOLO model weights.

---

## ShelfSense Pipeline

```mermaid
flowchart LR
    A[Warehouse Photos]
    -->|"Phase 1 • Fine-Tuned YOLOv8"|
    B[Warehouse JSON Contract]

    B -->|"Phase 2 • Analytics"|
    C[Health Score + Recommendations]

    B -->|"Phase 3 • OR-Tools CP-SAT"|
    D[Optimized Warehouse Layout]

    D --> E[Three.js Interactive 3D Digital Twin]
```

Everything in ShelfSense revolves around a single validated JSON contract (built using Pydantic).

- Phase 1 generates the contract.
- Phase 2 consumes it for analytics.
- Phase 3 extends it with optimized shelf placements.
- The Three.js viewer renders the final warehouse directly from this JSON.

---

# Phase 1 — Warehouse Perception

A fine-tuned **YOLOv8** model detects:

- Shelves
- Boxes
- Pallets

from a single warehouse photograph.

The detected objects are converted into structured warehouse metadata including:

- Shelf positions
- Bounding boxes
- Occupancy estimation
- Warehouse dimensions
- Object relationships

Occupancy percentages are computed geometrically.

When one real-world reference measurement is provided (for example, a known shelf width), ShelfSense converts all pixel measurements into real-world metres.

---

# Phase 2 — Warehouse Analytics

The generated warehouse model is analyzed to determine warehouse health.

Analytics include:

- Storage Utilization Rate (SUR)
- Six-dimensional weighted Health Score (0–100)
- Health category (Poor, Fair, Good, Excellent)
- Rule-based warehouse recommendations

Example recommendations include:

- Consolidate underutilized shelves
- Reclaim large unused floor areas
- Improve storage distribution
- Increase warehouse efficiency

---

# Phase 3 — Layout Optimization

Warehouse optimization is performed using **Google OR-Tools CP-SAT**.

The optimizer enforces real warehouse constraints including:

- No shelf overlaps
- Minimum aisle clearance
- Exit keep-out zones
- Optional 90° shelf rotation

Optimization objective:

> Maximize the number of shelves that can be placed while satisfying every constraint.

The resulting optimized layout is exported back into the common JSON contract.

---

# Interactive 3D Digital Twin

The optimized warehouse layout is rendered using **Three.js**.

Features include:

- Orbit camera
- Zoom
- Pan
- Clickable shelves
- Accurate layout visualization
- Browser-based rendering

No desktop software is required.

---

# Asynchronous Processing Pipeline

Long-running operations execute asynchronously using:

- Celery
- Redis

Workflow:

1. Client uploads warehouse image.
2. API immediately returns a `task_id`.
3. Celery performs detection, analytics, and optimization.
4. Client polls task status until completion.

Task states include:

- Queued
- Running
- Completed
- Failed

---

# Technology Stack

| Layer | Technology |
|--------|------------|
| API | FastAPI |
| Validation | Pydantic |
| Computer Vision | Fine-Tuned Ultralytics YOLOv8 |
| Optimization | Google OR-Tools CP-SAT |
| Database | SQLite |
| ORM | SQLAlchemy |
| Database Migration | Alembic |
| Background Processing | Celery |
| Message Broker | Redis |
| Authentication | JWT (python-jose) |
| Password Hashing | bcrypt |
| 3D Visualization | Three.js |
| Package Manager | uv |
| Containerization | Docker Desktop |

---

# Quickstart

## Prerequisites

- Python 3.13
- uv
- Docker Desktop

Clone the repository:

```bash
git clone https://github.com/ayush-kr-repo/ShelfSense.git

cd ShelfSense

uv sync
```

Start Redis:

```bash
docker run -d \
-p 6379:6379 \
--name shelfsense-redis \
redis
```

Create the database:

```bash
uv run alembic upgrade head
```

Start the FastAPI server:

```bash
uv run uvicorn app.main:app --reload
```

Start the Celery worker:

```bash
uv run celery \
-A app.worker.celery_app \
worker \
--loglevel=info \
--pool=solo
```

---

# Open in Browser

Interactive API Documentation

```
http://127.0.0.1:8000/docs
```

3D Digital Twin

```
http://127.0.0.1:8000/static/twin.html
```

---

# REST API

| Endpoint | Description |
|-----------|-------------|
| **POST /api/v1/analyze** | Upload a warehouse image and start the complete pipeline. Returns a `task_id` immediately. |
| **GET /api/v1/task/{id}** | Check asynchronous task progress. |
| **GET /api/v1/warehouse/{id}** | Retrieve Phase 1 warehouse detection output. |
| **GET /api/v1/analytics/{id}** | Retrieve warehouse health analytics. |
| **POST /api/v1/optimize** | Optimize warehouse layout using CP-SAT. |
| **GET /api/v1/layout/{id}** | Retrieve a previously generated optimized layout. |
| **POST /api/v1/warehouse/{id}/upload** | Upload a warehouse image. |
| **GET /api/v1/warehouses** | List warehouses belonging to the authenticated user. |
| **POST /api/v1/auth/register** | Register a new account. |
| **POST /api/v1/auth/login** | Authenticate and receive a JWT token. |

All warehouse endpoints require JWT authentication.

To enable real-world metre measurements, append:

```
?px_per_m=<value>
```

to warehouse and analytics endpoints.

---

# Project Structure

```text
app/
├── main.py              # FastAPI application entry point
├── api/                 # REST API routes
│   ├── warehouse.py
│   ├── optimize.py
│   └── auth.py
├── schemas.py           # Shared JSON contract (Pydantic)
├── models.py            # SQLAlchemy models
├── database.py          # Database engine and sessions
├── auth.py              # JWT authentication
├── scale.py             # Pixel-to-metre conversion
├── worker.py            # Celery worker
└── phase1-3.py          # Perception, analytics, optimization

alembic/                 # Database migrations

ml/                      # Fine-tuned YOLO weights and training notebooks

static/                  # Three.js digital twin

tests/                   # Pytest suite
```

---

# Roadmap

- [x] Locked JSON contract using Pydantic
- [x] Warehouse analytics engine
- [x] Storage Utilization Rate (SUR)
- [x] Health Score generation
- [x] Rule-based warehouse recommendations
- [x] CP-SAT warehouse optimizer
- [x] Aisle clearance constraints
- [x] Exit keep-out zones
- [x] Shelf rotation support
- [x] Interactive Three.js digital twin
- [x] Asynchronous Celery pipeline
- [x] Redis task queue
- [x] SQLite persistence
- [x] Alembic migrations
- [x] Fine-tuned YOLOv8 warehouse detector
- [x]Comprehensive pytest test suite
- [x] JWT authentication
- [x] User-scoped warehouse management
- [x] Image upload support
- [x] Pixel-to-metre scaling (Tier 2)
- [] React analytics dashboard
- [] PostgreSQL migration
- [] Docker Compose deployment

---