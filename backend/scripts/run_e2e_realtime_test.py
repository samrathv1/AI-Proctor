"""
AI-Proctor End-to-End Real-Time Camera -> AI -> ESP32 Integration Test Runner.
Executes the controlled scenario:
1. Live Camera captures frames.
2. Candidate face recognized via YuNet + SFace + Exam Biometric Cache.
3. Tracking ID maintained.
4. Mobile phone detected via YOLOv8n and spatially correlated to candidate desk area.
5. Observable event MOBILE_PHONE_DETECTED generated.
6. Temporal analysis tracks continuous duration without frame duplication.
7. Suspicion scoring engine fuses signals.
8. If alert threshold reached -> Alert created in Supabase & dispatched to IoT beacon.
9. ESP32-HALL304-01 receives command, actuates LED-1 (GPIO 27) & Buzzer (GPIO 15) for safe duration.
10. ESP32 sends ACK, backend records acknowledgement.
"""

import sys
import os
import time
import json
import base64
import requests
import cv2
import numpy as np

import functools
print = functools.partial(print, flush=True)

BACKEND_URL = "http://127.0.0.1:8000"
API_KEY = "dev-proctor-secret-key"
DEVICE_ID = "ESP32-HALL304-01"
EXAM_ID = "exam-01"
EXAM_SESSION_ID = "ses-exam-01"
CAMERA_ID = "webcam-01"

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def check_backend_and_device():
    print("\n--- [PRE-FLIGHT] Checking Backend & ESP32 Hardware Status ---")
    try:
        r_health = requests.get(f"{BACKEND_URL}/health", timeout=3)
        assert r_health.status_code == 200, f"Backend health returned {r_health.status_code}"
        print(f"Backend Health: OK (HTTP {r_health.status_code})")
    except Exception as e:
        print(f"ERROR: Backend unavailable at {BACKEND_URL}: {e}")
        return False

    try:
        r_dev = requests.get(f"{BACKEND_URL}/api/v1/iot/devices", headers=HEADERS, timeout=3)
        assert r_dev.status_code == 200
        devices = r_dev.json()
        target = next((d for d in devices if d.get("device_uid") == DEVICE_ID), None)
        assert target is not None, f"Device {DEVICE_ID} not registered in backend"
        print(f"ESP32 Device:   {target['device_uid']} (Status: {target['status']}, IP: {target.get('ip_address')})")
        print(f"Actuator State: LED={target.get('led_status')}, Buzzer={target.get('buzzer_status')}")
    except Exception as e:
        print(f"ERROR: ESP32 device check failed: {e}")
        return False

    return True

def run_integration_stream(max_duration_seconds=30):
    print("\n================================================================================")
    print("  AI-PROCTOR: LIVE CAMERA -> AI PIPELINE -> ESP32 REAL-TIME INTEGRATION TEST  ")
    print("================================================================================")
    print(f"Exam: {EXAM_ID} | Session: {EXAM_SESSION_ID} | Camera: {CAMERA_ID}")
    print(f"Target ESP32 Beacon: {DEVICE_ID}")
    print("--------------------------------------------------------------------------------")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Failed to open webcam at index 0.")
        return {"error": "WEBCAM_OPEN_FAILED"}

    # Results tracker
    results = {
        "camera_ok": False,
        "face_ok": False,
        "tracking_ok": False,
        "phone_ok": False,
        "spatial_ok": False,
        "behaviour_ok": False,
        "temporal_ok": False,
        "suspicion_ok": False,
        "alert_dispatched": False,
        "esp32_received": False,
        "esp32_ack": False,
        "candidate_info": None,
        "tracking_id": None,
        "phone_bbox": None,
        "max_score": 0,
        "max_severity": "LOW",
        "command_id": None,
        "ack_status": None,
        "timeline": []
    }

    start_time = time.time()
    frame_idx = 0
    phone_seen_frames = 0
    alert_triggered_at = None

    print("\n[STREAM START] Ingesting live webcam frames at ~4 FPS...")
    print("INSTRUCTIONS: Ensure candidate face is visible. Then introduce a mobile phone into desk view.\n")

    try:
        while time.time() - start_time < max_duration_seconds:
            loop_start = time.perf_counter()
            ret, frame = cap.read()
            if not ret or frame is None:
                print("Warning: empty frame read")
                time.sleep(0.1)
                continue

            frame_idx += 1
            results["camera_ok"] = True

            # Encode frame to JPEG Base64
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            b64_frame = base64.b64encode(buf).decode("utf-8")

            # Send to Unified Live Surveillance Frame Analysis Endpoint
            payload = {
                "camera_id": CAMERA_ID,
                "exam_id": EXAM_ID,
                "exam_session_id": EXAM_SESSION_ID,
                "frame_base64": b64_frame,
                "timestamp": None
            }

            try:
                t0_req = time.perf_counter()
                r = requests.post(f"{BACKEND_URL}/api/v1/monitoring/frame", json=payload, headers=HEADERS, timeout=5)
                req_ms = (time.perf_counter() - t0_req) * 1000
            except Exception as e:
                print(f"Frame {frame_idx}: API request error: {e}")
                time.sleep(0.2)
                continue

            if r.status_code != 200:
                print(f"Frame {frame_idx}: HTTP {r.status_code} - {r.text}")
                time.sleep(0.2)
                continue

            data = r.json()
            faces = data.get("recognized_faces", [])
            objects = data.get("detected_objects", [])
            events = data.get("observable_events", [])
            suspicion = data.get("suspicion_index", {})
            score = suspicion.get("score", 0)
            severity = suspicion.get("severity", "LOW")
            factors = suspicion.get("contributing_factors", [])

            if score > results["max_score"]:
                results["max_score"] = score
                results["max_severity"] = severity

            # Check Face Recognition
            for f in faces:
                if f.get("identity_status") == "IDENTIFIED":
                    results["face_ok"] = True
                    results["candidate_info"] = f"{f.get('student_name')} ({f.get('student_id')}, {f.get('similarity')*100:.1f}%)"
                    results["tracking_id"] = f.get("tracking_id")
                    results["tracking_ok"] = True

            # Check Mobile Phone Detection & Spatial Correlation
            phone_det = next((o for o in objects if o.get("detection_type") == "MOBILE_PHONE"), None)
            if phone_det:
                phone_seen_frames += 1
                results["phone_ok"] = True
                results["phone_bbox"] = phone_det.get("bounding_box")
                meta = phone_det.get("metadata", {})
                relation = meta.get("spatial_relation")
                if relation in ["WITHIN_DESK_AREA", "IN_PROXIMITY"]:
                    results["spatial_ok"] = True
                if not os.path.exists("backend/scratch/live_phone_detected_evidence.jpg"):
                    try:
                        vis = frame.copy()
                        h_f, w_f = vis.shape[:2]
                        bb = phone_det.get("bounding_box", {})
                        bx, by, bw, bh = int(bb["x"]*w_f), int(bb["y"]*h_f), int(bb["width"]*w_f), int(bb["height"]*h_f)
                        cv2.rectangle(vis, (bx, by), (bx+bw, by+bh), (0, 0, 255), 2)
                        cv2.putText(vis, f"MOBILE_PHONE {phone_det.get('confidence'):.2f}", (bx, max(20, by-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        cv2.imwrite("backend/scratch/live_phone_detected_evidence.jpg", vis)
                    except Exception:
                        pass


            # Check Behaviour Event
            phone_ev = next((e for e in events if e.get("behaviour_type") == "MOBILE_PHONE_DETECTED"), None)
            if phone_ev:
                results["behaviour_ok"] = True
                dur = phone_ev.get("duration_seconds", 0.0)
                if dur > 0.0 or phone_seen_frames >= 2:
                    results["temporal_ok"] = True

            # Check Suspicion Engine
            if len(factors) > 0:
                results["suspicion_ok"] = True

            # Print frame summary line
            face_str = results["candidate_info"] or "NO_FACE"
            obj_summary = ", ".join([f"{o.get('detection_type')}:{o.get('confidence'):.2f}" for o in objects if o.get('detection_type') != 'PERSON']) or "none"
            events_summary = ", ".join([e.get("behaviour_type") for e in events]) or "none"
            
            elapsed = time.time() - start_time
            print(f"[{elapsed:4.1f}s | F{frame_idx:03d}] Face: {face_str} | Objs: [{obj_summary}] | Events: [{events_summary}] | Score: {score}/100 ({severity}) [{req_ms:.0f}ms]")

            # Check if IoT Command Dispatched via device state (do NOT consume pending queue)
            if not results["alert_dispatched"]:
                try:
                    r_dev = requests.get(f"{BACKEND_URL}/api/v1/iot/devices", headers=HEADERS, timeout=2)
                    devs = r_dev.json() if r_dev.status_code == 200 else []
                    target = next((d for d in devs if d.get("device_uid") == DEVICE_ID), None)
                    if target and target.get("last_command_id"):
                        results["alert_dispatched"] = True
                        results["command_id"] = target.get("last_command_id")
                        alert_triggered_at = time.time()
                        print(f"\n>>> [ALERT DISPATCHED] Command {results['command_id']} dispatched for {DEVICE_ID} (Status: {target.get('last_command_status')}) <<<\n")
                except Exception as e:
                    pass

            # If alert was dispatched, check for ESP32 execution and ACK
            if results["alert_dispatched"] and not results["esp32_ack"]:
                try:
                    r_dev = requests.get(f"{BACKEND_URL}/api/v1/iot/devices", headers=HEADERS, timeout=2)
                    devs = r_dev.json() if r_dev.status_code == 200 else []
                    target = next((d for d in devs if d.get("device_uid") == DEVICE_ID), None)
                    if target:
                        last_cmd_id = target.get("last_command_id")
                        last_cmd_status = target.get("last_command_status")
                        if last_cmd_id == results["command_id"]:
                            results["esp32_received"] = True
                            if last_cmd_status == "ACKNOWLEDGED":
                                results["esp32_ack"] = True
                                results["ack_status"] = last_cmd_status
                                print(f"\n>>> [ESP32 ACK RECEIVED] Command {last_cmd_id} execution ACKNOWLEDGED by ESP32 hardware! <<<\n")
                                # Wait 2 seconds for safe duration completion
                                time.sleep(2.0)
                                break
                except Exception as e:
                    pass

            # Rate limit to ~4 FPS (250 ms period)
            loop_elapsed = time.perf_counter() - loop_start
            sleep_needed = max(0.01, 0.25 - loop_elapsed)
            time.sleep(sleep_needed)

    finally:
        cap.release()

    # Final check on IoT command status if command was dispatched but ack not caught in loop
    if results["alert_dispatched"] and not results["esp32_ack"]:
        print("\nWaiting up to 3 seconds for trailing ESP32 ACK...")
        for _ in range(6):
            time.sleep(0.5)
            try:
                r_dev = requests.get(f"{BACKEND_URL}/api/v1/iot/devices", headers=HEADERS, timeout=2)
                devs = r_dev.json() if r_dev.status_code == 200 else []
                target = next((d for d in devs if d.get("device_uid") == DEVICE_ID), None)
                if target and target.get("last_command_id") == results["command_id"] and target.get("last_command_status") == "ACKNOWLEDGED":
                    results["esp32_received"] = True
                    results["esp32_ack"] = True
                    results["ack_status"] = "ACKNOWLEDGED"
                    print(f">>> [ESP32 ACK RECEIVED] Confirmed trailing ACK for {results['command_id']}! <<<")
                    break
            except Exception:
                pass

    return results

if __name__ == "__main__":
    if not check_backend_and_device():
        sys.exit(1)
    results = run_integration_stream(max_duration_seconds=35)
    print("\n--- EXECUTION SUMMARY ---")
    print(json.dumps(results, indent=2))
