from app.phase1 import run_phase1

print("=== Tier 1 (no ruler) ===")
wh = run_phase1("wh_real_test", "ml/test_warehouse.jpg")
print(wh.scale.model_dump(), "| shelf0 w:", wh.shelves[0].estimated_dims.w)

print("=== Tier 2 (ruler: 240 px/m) ===")
wh = run_phase1("wh.ref", "ml/test_warehouse.jpg", px_per_m=240.0)
print(wh.scale.model_dump(), "| shelf0 w:", wh.shelves[0].estimated_dims.w)
