import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import cv2
from backend.app.services.yolo_engine import yolo_engine

cap = cv2.VideoCapture(0)
print("--- BOX SIZES & LABELS (10 SECONDS) ---")
t_end = time.time() + 10

while time.time() < t_end:
    ret, frame = cap.read()
    if not ret: break
    objs = yolo_engine.detect_objects(frame, conf_threshold=0.25)
    for o in objs:
        if o.class_id != 0:
            print(f"[{time.time()-t_end+10:4.1f}s] {o.label:12s} conf={o.confidence:.2f}, box=({o.raw_box[0]},{o.raw_box[1]},{o.raw_box[2]},{o.raw_box[3]})", flush=True)
    time.sleep(0.4)

cap.release()
print("Done.", flush=True)
