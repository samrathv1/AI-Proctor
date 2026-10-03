import sys
import os
sys.path.insert(0, os.path.abspath("."))
import cv2
from backend.app.services.yolo_engine import yolo_engine

cap = cv2.VideoCapture(0)
for _ in range(5):
    ret, frame = cap.read()
cap.release()

if ret and frame is not None:
    objs = yolo_engine.detect_objects(frame, conf_threshold=0.30)
    print(f"Total objects: {len(objs)}")
    for o in objs:
        print(f"Detected: class_id={o.class_id}, label='{o.label}', detection_type='{o.detection_type}', conf={o.confidence:.3f}")
