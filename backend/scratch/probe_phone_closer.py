import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import cv2
from backend.app.services.yolo_engine import yolo_engine

cap = cv2.VideoCapture(0)
print("--- PROBING PHONE CLOSER (20-30cm, PORTRAIT) FOR 10 SECONDS ---")
t_end = time.time() + 10

while time.time() < t_end:
    ret, frame = cap.read()
    if not ret: break
    objs = yolo_engine.detect_objects(frame, conf_threshold=0.25)
    phone = [o for o in objs if o.class_id == 67 or o.label == "cell phone" or o.detection_type == "MOBILE_PHONE"]
    rem = t_end - time.time()
    if phone:
        p = phone[0]
        print(f"[{rem:4.1f}s] *** MOBILE_PHONE DETECTED! Conf={p.confidence:.2f}, Size={p.raw_box[2]}x{p.raw_box[3]} ***")
    else:
        labels = [f"{o.label}:{o.confidence:.2f}" for o in objs if o.class_id != 0]
        print(f"[{rem:4.1f}s] Non-person: {labels or 'none'}")
    time.sleep(0.3)

cap.release()
print("Complete.")
