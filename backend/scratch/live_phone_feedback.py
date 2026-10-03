import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import cv2
from backend.app.services.yolo_engine import yolo_engine

cap = cv2.VideoCapture(0)
print("--- REAL-TIME PHONE DETECTION ASSISTANT (20 SECONDS) ---")
print("TIPS FOR YOLOV8n COCO RECOGNITION:")
print("1. Turn ON the phone screen (display home screen or a white/bright screen).")
print("2. Hold the phone by its edges so fingers don't cover the screen/bezel.")
print("3. Hold it upright in front of your chest ~25-35 cm from camera.")
print("----------------------------------------------------------------------")

t_end = time.time() + 20
detected_count = 0

while time.time() < t_end:
    ret, frame = cap.read()
    if not ret: break
    objs = yolo_engine.detect_objects(frame, conf_threshold=0.20)
    phones = [o for o in objs if o.class_id == 67 or o.label == "cell phone" or o.detection_type == "MOBILE_PHONE"]
    rem = t_end - time.time()
    if phones:
        detected_count += 1
        p = phones[0]
        print(f"[{rem:4.1f}s] >>> SUCCESS! PHONE DETECTED! Conf={p.confidence*100:.1f}%, Box=({p.raw_box[0]},{p.raw_box[1]},{p.raw_box[2]},{p.raw_box[3]}) <<<")
    else:
        # show top 3 non-person detections
        other = [f"{o.label}:{o.confidence*100:.0f}%" for o in objs if o.class_id != 0][:3]
        print(f"[{rem:4.1f}s] Searching... Visible objects: {other or 'none'}")
    time.sleep(0.3)

cap.release()
print(f"Test ended. Total phone frames detected: {detected_count}")
