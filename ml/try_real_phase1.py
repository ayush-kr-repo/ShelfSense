from app.phase1 import run_phase1

wh = run_phase1("wh_real_test", "ml/test_warehouse.jpg")
print(wh.model_dump_json(indent=2))
