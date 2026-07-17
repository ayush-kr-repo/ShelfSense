from ultralytics import YOLO

model = YOLO("ml/weights/best.pt")

results = model("ml/test_warehouse.jpg")

for box in results[0].boxes:
    class_name = model.names[int(box.cls)]
    confidence = float(box.conf)
    print(f"{class_name}: {confidence:.2f}")

results[0].save("ml/test_result.jpg")
print("Saved annotated image in ml/test_result.jpg")