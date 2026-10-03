import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import cv2
from backend.app.services.yolo_engine import yolo_engine

cap = cv2.VideoCapture(0)
print("=== CAMERA MONITORING: PLEASE RAISE PHONE TO CHEST/CHIN HEIGHT ===")
t_end = time.time() + 15

while time.time() < t_end:
    ret, frame = cap.read()
    if not ret: break
    objs = yolo_engine.detect_objects(frame, conf_threshold=0.20)
    for o in objs:
        if o.class_id == 67 or o.detection_type == "MOBILE_PHONE":
            print(f"[{time.time()-t_end+15:.1f}s] >>> PHONE DETECTED! Conf={o.confidence:.2f}, Box={o.raw_box} <<<", flush=True)
        elif o.class_id != 0:
            print(f"[{time.time()-t_end+15:.1f}s] {o.label}:{o.confidence:.2f} at {o.raw_box}", flush=True)
    time.sleep(0.3)

cap.release()
print("Finished.", flush=True)
