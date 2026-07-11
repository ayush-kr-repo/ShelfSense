from app.phase3 import solve_layout

shelves = [{"id": f"S{i}", "w": 2.0, "d": 0.6} for i in range(12)]

status, layout = solve_layout(
    floor_w_m = 10.0, floor_d_m = 8.0, shelves = shelves,
    aisle_m = 0.9, exit_zone=(0, 0, 1.5, 1.5), time_limit_s = 10,
)

print("Status:", status, "| placed:", len(layout), "of", len(shelves))
for s in layout:
    print(f"  {s['id']}: x={s['x']:4.1f}  z={s['z']:4.1f}  "
          f"{s['w']}x{s['d']}  rotated={s['rotated']}")

