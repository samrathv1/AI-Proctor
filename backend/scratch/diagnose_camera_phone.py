import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import cv2
from backend.app.services.yolo_engine import yolo_engine

cap = cv2.VideoCapture(0)
print("Scanning camera for 10 seconds. Please hold your mobile phone visible towards the camera...")
t_end = time.time() + 10

while time.time() < t_end:
    ret, frame = cap.read()
    if not ret: break
    objs = yolo_engine.detect_objects(frame, conf_threshold=0.25)
    non_person = [o for o in objs if o.detection_type != "PERSON"]
    if non_person:
        for o in non_person:
            print(f"  [{time.time()-t_end+10:.1f}s] label='{o.label}' (class {o.class_id}), type='{o.detection_type}', conf={o.confidence:.2f}, box={o.raw_box}")
    time.sleep(0.3)

cap.release()
print("Scan complete.")
