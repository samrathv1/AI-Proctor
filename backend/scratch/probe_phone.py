import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import cv2
from backend.app.services.yolo_engine import yolo_engine

cap = cv2.VideoCapture(0)
print("--- REAL-TIME PHONE DETECTION PROBE (15 SECONDS) ---")
print("Hold the phone upright with screen or back facing camera at ~30-50cm distance.")
t_end = time.time() + 15

while time.time() < t_end:
    ret, frame = cap.read()
    if not ret: break
    objs = yolo_engine.detect_objects(frame, conf_threshold=0.20)
    phone = [o for o in objs if o.class_id == 67 or o.label == "cell phone"]
    all_non_person = [f"{o.label}:{o.confidence:.2f}" for o in objs if o.class_id != 0]
    rem_time = t_end - time.time()
    if phone:
        print(f"[{rem_time:4.1f}s LEFT] >>> CELL PHONE DETECTED! Conf={phone[0].confidence:.2f}, Box={phone[0].raw_box} <<<")
    else:
        print(f"[{rem_time:4.1f}s LEFT] Objects: {all_non_person or 'none'}")
    time.sleep(0.3)

cap.release()
print("Probe complete.")
