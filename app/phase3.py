from ortools.sat.python import cp_model
from app.schemas import OptimizeRequst, Layout

def solve_layout(floor_w_m, floor_d_m, shelves, cell_m=0.5,
                 aisle_m=0.9, exit_zone=None, time_limit_s=10):
    """Place shelves on the floor: no overlaps, aisle gaps, exit kept
    clear, optional 90-degree rotation. Maximizes number placed.

    shelves:   [{"id": "S0", "w": 2.0, "d": 0.6}, ...]
    exit_zone: (x0, z0, x1, z1) rectangle in metres to keep clear, or None.
    Returns (status_name, layout) where layout lists the placed shelves.
    """
    m = cp_model.CpModel()
    W = int(round(floor_w_m / cell_m))          # floor width in cells
    D = int(round(floor_d_m / cell_m))          # floor depth in cells
    pad = int(round(aisle_m / cell_m))          # aisle gap in cells

    placed, xs, zs, ews, eds, rots, x_ivs, z_ivs = [], [], [], [], [], [], [], []

    for s in shelves:
        sw = int(round(s["w"] / cell_m))        # shelf size in cells
        sd = int(round(s["d"] / cell_m))

        present = m.NewBoolVar(f"p_{s['id']}")  # v3: is it placed at all?
        rot = m.NewBoolVar(f"r_{s['id']}")      # v2: rotated 90 degrees?

        # v2: effective dims follow the rotation choice
        ew = m.NewIntVar(0, max(sw, sd), f"ew_{s['id']}")
        ed = m.NewIntVar(0, max(sw, sd), f"ed_{s['id']}")
        m.Add(ew == sw).OnlyEnforceIf(rot.Not())
        m.Add(ed == sd).OnlyEnforceIf(rot.Not())
        m.Add(ew == sd).OnlyEnforceIf(rot)
        m.Add(ed == sw).OnlyEnforceIf(rot)

        x = m.NewIntVar(0, W, f"x_{s['id']}")
        z = m.NewIntVar(0, D, f"z_{s['id']}")
        m.Add(x + ew <= W).OnlyEnforceIf(present)   # v1: stay in bounds
        m.Add(z + ed <= D).OnlyEnforceIf(present)

        # v3: aisle-padded, optional rectangles feed the no-overlap rule
        x_end = m.NewIntVar(0, W + pad, f"xe_{s['id']}")
        z_end = m.NewIntVar(0, D + pad, f"ze_{s['id']}")
        x_iv = m.NewOptionalIntervalVar(x, ew + pad, x_end,
                                        present, f"xiv_{s['id']}")
        z_iv = m.NewOptionalIntervalVar(z, ed + pad, z_end,
                                        present, f"ziv_{s['id']}")

        if exit_zone:                                # v4: dodge the exit
            ex0, ez0, ex1, ez1 = [int(round(v / cell_m)) for v in exit_zone]
            L = m.NewBoolVar(f"L_{s['id']}")
            R = m.NewBoolVar(f"R_{s['id']}")
            B = m.NewBoolVar(f"B_{s['id']}")
            A = m.NewBoolVar(f"A_{s['id']}")
            m.Add(x + ew <= ex0).OnlyEnforceIf(L)
            m.Add(x >= ex1).OnlyEnforceIf(R)
            m.Add(z + ed <= ez0).OnlyEnforceIf(B)
            m.Add(z >= ez1).OnlyEnforceIf(A)
            m.AddBoolOr([L, R, B, A]).OnlyEnforceIf(present)

        placed.append(present); xs.append(x); zs.append(z)
        ews.append(ew); eds.append(ed); rots.append(rot)
        x_ivs.append(x_iv); z_ivs.append(z_iv)

    m.AddNoOverlap2D(x_ivs, z_ivs)              # v1: THE rule
    m.Maximize(sum(placed))                     # v3: fit as many as possible

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s   # v4: budget
    status = solver.Solve(m)

    layout = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for i, s in enumerate(shelves):
            if not solver.Value(placed[i]):
                continue                        # skipped shelf: not in layout
            layout.append({
                "id": s["id"],
                "x": solver.Value(xs[i]) * cell_m,
                "z": solver.Value(zs[i]) * cell_m,
                "w": solver.Value(ews[i]) * cell_m,   # as-placed dims
                "d": solver.Value(eds[i]) * cell_m,
                "rotated": bool(solver.Value(rots[i])),
            })
    return solver.StatusName(status), layout

def run_phase3(req: OptimizeRequst) -> Layout:
    status, layout = solve_layout(
        floor_w_m=req.floor_w_m,
        floor_d_m=req.floor_d_m,
        shelves=[s.model_dump() for s in req.shelves],   # ShelfSpec -> dict
        cell_m=req.cell_m,
        aisle_m=req.aisle_m,
        exit_zone=tuple(req.exit_zone) if req.exit_zone else None,
        time_limit_s=req.time_limit_s,
    )
    return Layout(
        status=status,
        placed_count=len(layout),
        total_requested=len(req.shelves),
        shelves=layout,        # dicts -> PlacedShelf, validated by Pydantic
    )