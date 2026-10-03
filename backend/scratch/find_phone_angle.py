import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import cv2
from backend.app.services.yolo_engine import yolo_engine

cap = cv2.VideoCapture(0)
print("Scanning for 'cell phone' (class 67). Try showing back of phone or side...")
t_end = time.time() + 15
found = False

while time.time() < t_end:
    ret, frame = cap.read()
    if not ret: break
    objs = yolo_engine.detect_objects(frame, conf_threshold=0.15)
    for o in objs:
        if o.class_id == 67 or "phone" in o.label.lower():
            print(f"*** DETECTED: {o.label} ({o.confidence:.2f}) at box {o.raw_box} ***")
            found = True
    time.sleep(0.2)

cap.release()
print("Found cell phone:", found)
