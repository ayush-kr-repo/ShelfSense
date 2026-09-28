import math
from dataclasses import dataclass

from ortools.sat.python import cp_model

from app.schemas import OptimizeRequest, Layout


@dataclass
class _ShelfVars:
    """Every decision variable for one shelf, kept together.

    Replaces eight parallel lists held in sync by hand - appending to seven
    of them and forgetting the eighth silently shifted every later index.
    """
    spec: dict                      # the caller's {"id", "w", "d"}
    present: cp_model.IntVar        # placed at all?
    rot: cp_model.IntVar            # turned 90 degrees?
    x: cp_model.IntVar              # position, in cells
    z: cp_model.IntVar
    ew: cp_model.IntVar             # as-placed dims, in cells
    ed: cp_model.IntVar
    x_iv: cp_model.IntervalVar      # aisle-padded, optional
    z_iv: cp_model.IntervalVar


def solve_layout(floor_w_m, floor_d_m, shelves, cell_m=0.5,
                 aisle_m=0.9, exit_zone=None, time_limit_s=10):
    """Place shelves on the floor: no overlaps, aisle gaps, exit kept
    clear, optional 90-degree rotation. Maximizes number placed.

    shelves:   [{"id": "S0", "w": 2.0, "d": 0.6}, ...]
    exit_zone: (x0, z0, x1, z1) rectangle in metres to keep clear, or None.
    Returns (status_name, layout) where layout lists the placed shelves.

    Rounding is deliberately conservative in every direction: the floor
    rounds down, shelves and aisles round up, and the keep-clear zone
    grows. The planner may understate capacity; it must never overstate it.
    """
    m = cp_model.CpModel()
    W = int(floor_w_m / cell_m)          # floor width in cells, rounded DOWN
    D = int(floor_d_m / cell_m)          # don't invent floor space we don't have
    pad = math.ceil(aisle_m / cell_m)    # aisle gap in cells, rounded UP - never narrower

    if W < 1 or D < 1:
        raise ValueError(f"floor is smaller than one {cell_m}m cell")

    # hoisted out of the loop; near edges round down, far edges up, so the
    # forbidden rectangle is never smaller than the caller asked for
    if exit_zone:
        ex0 = int(exit_zone[0] / cell_m)
        ez0 = int(exit_zone[1] / cell_m)
        ex1 = math.ceil(exit_zone[2] / cell_m)
        ez1 = math.ceil(exit_zone[3] / cell_m)

    sv: list[_ShelfVars] = []

    for s in shelves:
        sid = s["id"]
        sw = math.ceil(s["w"] / cell_m)        # shelf size in cells, rounded UP
        sd = math.ceil(s["d"] / cell_m)        # a 0.6m shelf must never model as 0.5m

        present = m.NewBoolVar(f"p_{sid}")
        rot = m.NewBoolVar(f"r_{sid}")

        # effective dims follow the rotation choice. All four branches are
        # required - drop the rot ones and the solver picks ew=ed=0.
        ew = m.NewIntVar(0, max(sw, sd), f"ew_{sid}")
        ed = m.NewIntVar(0, max(sw, sd), f"ed_{sid}")
        m.Add(ew == sw).OnlyEnforceIf(rot.Not())
        m.Add(ed == sd).OnlyEnforceIf(rot.Not())
        m.Add(ew == sd).OnlyEnforceIf(rot)
        m.Add(ed == sw).OnlyEnforceIf(rot)

        x = m.NewIntVar(0, W, f"x_{sid}")
        z = m.NewIntVar(0, D, f"z_{sid}")
        m.Add(x + ew <= W).OnlyEnforceIf(present)   # stay in bounds
        m.Add(z + ed <= D).OnlyEnforceIf(present)

        # interval SIZE is ew+pad: each shelf claims its footprint plus an
        # aisle, so non-overlap of the padded boxes leaves a real gap.
        x_end = m.NewIntVar(0, W + pad, f"xe_{sid}")
        z_end = m.NewIntVar(0, D + pad, f"ze_{sid}")
        x_iv = m.NewOptionalIntervalVar(x, ew + pad, x_end, present, f"xiv_{sid}")
        z_iv = m.NewOptionalIntervalVar(z, ed + pad, z_end, present, f"ziv_{sid}")

        if exit_zone:                       # sit entirely on ONE side of it
            L = m.NewBoolVar(f"L_{sid}")
            R = m.NewBoolVar(f"R_{sid}")
            B = m.NewBoolVar(f"B_{sid}")
            A = m.NewBoolVar(f"A_{sid}")
            m.Add(x + ew <= ex0).OnlyEnforceIf(L)
            m.Add(x >= ex1).OnlyEnforceIf(R)
            m.Add(z + ed <= ez0).OnlyEnforceIf(B)
            m.Add(z >= ez1).OnlyEnforceIf(A)
            m.AddBoolOr([L, R, B, A]).OnlyEnforceIf(present)

        sv.append(_ShelfVars(s, present, rot, x, z, ew, ed, x_iv, z_iv))

    # Symmetry breaking: identical shelves are interchangeable, so every layout
    # has k! relabelled twins that score the same. Force a canonical order over
    # duplicates - this removes only duplicates, never a genuinely new layout.
    # (D+1) because z spans 0..D inclusive; a smaller multiplier collides.
    seen = {}
    for v in sv:
        key = (v.spec["w"], v.spec["d"])
        if key in seen:
            p = seen[key]                                   # previous of this size
            m.Add(p.x * (D + 1) + p.z <= v.x * (D + 1) + v.z)
            m.Add(p.present >= v.present)                   # fill duplicates in order
        seen[key] = v

    m.AddNoOverlap2D([v.x_iv for v in sv], [v.z_iv for v in sv])
    m.Maximize(sum(v.present for v in sv))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    status = solver.Solve(m)

    layout = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for v in sv:
            if not solver.Value(v.present):
                continue                    # skipped shelf: not in the layout
            layout.append({
                "id": v.spec["id"],
                "x": solver.Value(v.x) * cell_m,
                "z": solver.Value(v.z) * cell_m,
                "w": solver.Value(v.ew) * cell_m,   # as-placed dims
                "d": solver.Value(v.ed) * cell_m,
                "rotated": bool(solver.Value(v.rot)),
            })
    return solver.StatusName(status), layout


def run_phase3(req: OptimizeRequest) -> Layout:
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
