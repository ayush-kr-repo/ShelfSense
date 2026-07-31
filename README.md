<div align="center">

# 📦 ShelfSense AI

### Warehouse Intelligence from a Single Photograph

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=20&duration=3500&pause=1000&color=38BDF8&center=true&vCenter=true&width=650&lines=Detect+shelves+with+computer+vision;Score+warehouse+health+in+six+dimensions;Optimize+layout+with+constraint+programming;Explore+the+result+in+an+interactive+3D+twin" alt="ShelfSense" />

<br/>

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Fine--Tuned-FF6F00?style=for-the-badge&logo=pytorch&logoColor=white)
![OR-Tools](https://img.shields.io/badge/OR--Tools-CP--SAT-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Three.js](https://img.shields.io/badge/Three.js-000000?style=for-the-badge&logo=three.js&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-v4-38BDF8?style=for-the-badge&logo=tailwindcss&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)

</div>

---

> **ShelfSense turns a warehouse photograph into a decision.** Computer vision reads the shelves, an analytics engine scores storage health, a constraint solver computes the mathematically optimal layout, and an interactive 3D twin lets you explore the result — before a single real shelf is moved.

![ShelfSense 3D digital twin](docs/twin.png)

---

## 💡 What Problem Does It Solve?

Warehouse space is expensive, and most storage decisions are made with a tape measure, a spreadsheet, and intuition. Managers rarely have a fast answer to the questions that matter most:

| Question | ShelfSense Answers With |
|---|---|
| 📊 **How full is my warehouse?** | Storage Utilization Rate computed from detected shelf occupancy |
| 🩺 **How healthy is my storage?** | A weighted 0–100 health score across six dimensions |
| 📐 **How many more shelves fit?** | A CP-SAT solver that packs your real floor under real constraints |
| 🎯 **What is the optimal layout?** | An optimized arrangement, rendered in interactive 3D |
| ⚠️ **What should I fix first?** | Ranked, rule-based recommendations with impact levels |

---

## ✨ Features

### 🗂️ Multi-Warehouse Management

Upload a photo with real floor dimensions to create a warehouse. Rename, resize, and delete from the dashboard. Every warehouse is scoped to its owner and protected by JWT authentication.

![Dashboard](docs/dashboard.png)

### 📊 Warehouse Health Analytics

A weighted health score built from six sub-scores — storage efficiency, accessibility, safety compliance, space balance, unused space index, and expansion readiness — visualized as a radar breakdown alongside actionable recommendations.

![Analytics](docs/Analytics.png)

### 🔥 Occupancy Heatmap

Every detected shelf bay is rendered and color-coded by how full it is, placed side by side with the source photograph so you can verify exactly what the model saw.

![Occupancy heatmap](docs/Heatmap.png)

### 📐 Capacity Planner & 3D Digital Twin

Enter your floor size, shelf footprint, and aisle width — the constraint solver packs the space and reports how many shelves fit, how much storage area that represents, and how much room remains to grow. Existing capacity renders green, growth potential renders amber, and the entire layout is explorable in 3D with orbit, pan, and zoom.

### 🏷️ Purpose-Built Training Dataset

No public dataset contained warehouse shelf bays, so one was built: ~1,700 images assembled from multiple sources, with shelf bays hand-annotated under a documented convention — one label per rack bay, upright to upright, floor to top.

![Dataset annotation](docs/annotated.png)

---

## 🏗️ Architecture

```mermaid
flowchart LR
    A[Warehouse Photo] -->|"Phase 1 · YOLOv8"| B[Warehouse JSON Contract]
    B -->|"Phase 2 · Analytics"| C[Health Score + Recommendations]
    B -->|"Phase 3 · CP-SAT"| D[Optimized Layout]
    D --> E[Interactive 3D Twin]
    C --> F[React Dashboard]
    E --> F
```

Every stage communicates through **one validated JSON contract** defined in Pydantic. Phase 1 produces it, Phase 2 consumes it, Phase 3 extends it, and the frontend renders it. That contract is why each layer can be replaced independently — upgrading the detection model is a one-line change.

---

## 🔬 How It Works

### Phase 1 — Perception

A fine-tuned **YOLOv8** detector locates shelves, boxes, and pallets in a single photograph. Detections are converted into structured metadata: shelf positions, per-bay occupancy computed geometrically from box coverage, zone classification, and floor-plan areas.

Pixel measurements become real-world metres either from entered floor dimensions or from a single reference measurement passed as `?px_per_m=`. When no scale is available, the system reports relative units and declares it, rather than inventing numbers.

### Phase 2 — Analytics

Storage Utilization Rate is computed volumetrically across all detected shelves. Six sub-scores are weighted into a single health score with a categorical band, and a rule engine produces recommendations from real square-metre analysis. When a required input is missing, the engine reports what it needs instead of guessing.

### Phase 3 — Optimization

**Google OR-Tools CP-SAT** solves the layout as a constraint satisfaction problem:

- **No-overlap** in 2D across all placed shelves
- **Aisle clearance** enforced through interval padding
- **Exit keep-out zones** via reified boolean disjunction
- **Optional 90° rotation** per shelf
- **Optional placement**, so an over-constrained floor degrades gracefully instead of becoming infeasible

The objective maximizes the number of shelves placed — which is precisely the number a planner needs to know.

---

## 📈 Model Performance

Trained on a custom dataset assembled from public sources plus hand-annotated rack imagery. Current per-class results on the held-out validation set:

| Class | mAP@50 | Notes |
|---|---|---|
| 🟢 **pallet** | **0.96** | Strong — approximately 3,000 training instances |
| 🟡 **shelf** | **0.41** | Limited by data volume; dataset expansion in progress |
| 🟡 **box** | **0.38** | Limited by annotation convention conflicts between merged sources |

**Documented experiments**

- **Model capacity is not the bottleneck.** Scaling from YOLOv8n to YOLOv8s (3.5× parameters) moved overall mAP by 0.02 — a controlled result establishing that the limit is training data, not architecture.
- **Label consistency dominates label volume.** A retrain with expanded annotations *reduced* box accuracy, because newly annotated images used a different granularity convention than the validation set. That result drove a dataset rebuild around a single documented standard.

**Known limitations**, stated deliberately:

- Occupancy is estimated from a single 2D viewpoint; stock depth behind the visible front row cannot be observed
- Shelf detection is reliable on straight-on rack imagery and degrades on oblique or low-light scenes
- Safety compliance returns a neutral placeholder pending aisle-width and load-weight inputs

Detection is upgradeable by replacing a single weights file — no application changes required.

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology |
|:---|:---|
| **API** | FastAPI · Pydantic · Uvicorn |
| **Computer Vision** | Ultralytics YOLOv8 (fine-tuned) · Roboflow |
| **Optimization** | Google OR-Tools CP-SAT |
| **Frontend** | React 19 · Vite · Tailwind v4 |
| **Visualization** | Three.js (react-three-fiber) · Recharts · Framer Motion · Matplotlib |
| **Persistence** | SQLite · SQLAlchemy · Alembic |
| **Async** | Celery · Redis |
| **Auth** | JWT (python-jose) · bcrypt |
| **Tooling** | uv · pytest · Docker |

</div>

---

## 🚀 Quickstart

**Prerequisites:** Python 3.13 · [uv](https://docs.astral.sh/uv/) · Node 20+ · Docker Desktop

```bash
git clone https://github.com/ayush-kr-repo/ShelfSense.git
cd ShelfSense
uv sync
```

**Start the backend**

```bash
docker run -d -p 6379:6379 --name shelfsense-redis redis
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

**Start the worker** — separate terminal, optional, for asynchronous analysis

```bash
uv run celery -A app.worker.celery_app worker --loglevel=info --pool=solo
```

**Start the dashboard** — separate terminal

```bash
cd frontend
npm install
npm run dev
```

| Service | URL |
|---|---|
| 🖥️ Dashboard | http://localhost:5173 |
| 📚 Interactive API docs | http://127.0.0.1:8000/docs |

**Run the tests**

```bash
uv run pytest
```

---

## 🔌 REST API

![API endpoints](docs/endpoints.png)

| Endpoint | Purpose |
|:---|:---|
| `POST /api/v1/auth/register` | Create an account |
| `POST /api/v1/auth/login` | Authenticate and receive a JWT |
| `GET /api/v1/warehouses` | List the authenticated user's warehouses |
| `POST /api/v1/warehouse/{id}/upload` | Upload a photo with optional floor dimensions |
| `GET /api/v1/warehouse/{id}` | Phase 1 detection output |
| `GET /api/v1/analytics/{id}` | Health analytics, heatmap, and capacity data |
| `PATCH /api/v1/warehouse/{id}/meta` | Update name or floor dimensions |
| `DELETE /api/v1/warehouse/{id}` | Delete a warehouse and its media |
| `POST /api/v1/optimize` | Run CP-SAT layout optimization |
| `GET /api/v1/layout/{id}` | Retrieve a stored optimized layout |
| `POST /api/v1/analyze` | Queue asynchronous analysis, returns a task id |
| `GET /api/v1/task/{id}` | Poll task status and progress |

All warehouse endpoints require JWT authentication and enforce per-user ownership.

---

## 📁 Project Structure

```text
app/
├── main.py              # FastAPI application assembly
├── api/                 # Route modules: warehouse · optimize · auth
├── schemas.py           # The shared JSON contract (Pydantic)
├── models.py            # SQLAlchemy ORM models
├── database.py          # Engine and session management
├── auth.py              # JWT issuance, verification, password hashing
├── scale.py             # Pixel-to-metre conversion
├── heatmap.py           # Occupancy heatmap rendering
├── worker.py            # Celery task definitions
└── phase1.py … phase3.py    # Perception · Analytics · Optimization

frontend/src/
├── api.js               # Fetch wrapper: base URL, JWT injection, 401 handling
├── Login.jsx            # Authentication
├── Dashboard.jsx        # Warehouse grid and management
├── Upload.jsx           # Multipart photo upload with dimensions
├── Analytics.jsx        # Health score, radar, recommendations, media
├── Optimize.jsx         # Capacity planner and solver interface
└── Twin.jsx             # react-three-fiber 3D digital twin

alembic/                 # Database migrations
ml/                      # Model weights and training notebook
tests/                   # Pytest suite
Dockerfile               # Container definition for deployment
```

---

## 🗺️ Roadmap

**Shipped**

- ✅ Contract-first JSON schema across all phases
- ✅ Fine-tuned YOLOv8 detector with a purpose-built dataset
- ✅ Analytics engine — SUR, six-dimension health score, recommendations
- ✅ CP-SAT optimizer with aisle, exit, and rotation constraints
- ✅ Interactive 3D digital twin
- ✅ React dashboard with capacity planning
- ✅ JWT authentication with per-user ownership enforcement
- ✅ SQLite persistence with Alembic migrations
- ✅ Asynchronous Celery pipeline
- ✅ Pixel-to-metre scaling

**In Progress**

- 🔄 Rebuilt training dataset under a single annotation standard
- 🔄 Cloud deployment — containerized and ready

**Planned**

- ⬜ Occupancy estimation v2, post-retrain
- ⬜ Data-driven safety compliance scoring
- ⬜ PostgreSQL migration and signed media URLs
- ⬜ PDF report export

---

<div align="center">

**MIT License** · Built by [Ayush Kumar](https://github.com/ayush-kr-repo)

⭐ If this project is useful to you, consider starring the repository.

</div>
