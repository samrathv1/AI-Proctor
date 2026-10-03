import base64
import os
import time
import cv2
import numpy as np
import pytest

from backend.app.services.yolo_engine import yolo_engine, DetectedObject
from backend.app.services.detection_service import detection_service
from backend.app.services.behaviour_service import behaviour_service
from backend.app.services.suspicion_service import suspicion_service
from backend.app.services.tracking_service import Tracklet
from backend.app.models.responses import BoundingBox, DetectionItem
from backend.app.core.config import settings


def encode_image_base64(img_bgr: np.ndarray) -> str:
    """Helper to convert BGR image to base64 JPEG string."""
    _, buffer = cv2.imencode(".jpg", img_bgr)
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")


# ==============================================================================
# REAL YOLO OBJECT DETECTION TESTS
# ==============================================================================

def test_yolo_engine_initialization():
    """TEST 1: Verifies YOLOv8 ONNX session is properly initialized and configured."""
    assert yolo_engine.session is not None
    assert os.path.exists(yolo_engine.model_path)
    assert yolo_engine.input_name == "images"
    assert yolo_engine.output_name == "output0"
    assert yolo_engine.input_size == 640


def test_yolo_real_mobile_phone_detection():
    """TEST 2: Real camera-grade image of a phone on an exam desk is accurately detected."""
    img_path = "backend/models/test_exam_phone.jpg"
    assert os.path.exists(img_path), f"Test image {img_path} must exist"

    img = cv2.imread(img_path)
    assert img is not None

    detections = yolo_engine.detect_objects(img, conf_threshold=0.35)
    assert len(detections) > 0

    # Locate mobile phone detection
    phone_dets = [d for d in detections if d.detection_type == "MOBILE_PHONE"]
    assert len(phone_dets) >= 1, "YOLO must detect the mobile phone on the examination desk"

    phone = phone_dets[0]
    assert phone.confidence >= 0.80, f"Phone confidence should be high (observed {phone.confidence})"
    assert phone.label == "cell phone"
    assert phone.bbox.width > 0.05 and phone.bbox.height > 0.05


def test_yolo_real_laptop_detection():
    """TEST 3: Real examination desk with an unauthorized laptop is accurately detected."""
    img_path = "backend/models/test_exam_laptop.jpg"
    assert os.path.exists(img_path), f"Test image {img_path} must exist"

    img = cv2.imread(img_path)
    assert img is not None

    detections = yolo_engine.detect_objects(img, conf_threshold=0.35)
    assert len(detections) > 0

    laptop_dets = [d for d in detections if d.detection_type == "LAPTOP"]
    assert len(laptop_dets) >= 1, "YOLO must detect the laptop on the examination desk"
    assert laptop_dets[0].confidence >= 0.85


def test_yolo_clean_frame_no_unauthorized_objects():
    """TEST 4: Clean/blank surveillance frame returns 0 object detections."""
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = yolo_engine.detect_objects(blank, conf_threshold=0.35)
    assert len(detections) == 0


def test_track_correlation_phone_with_student():
    """TEST 5: Correlates a detected mobile phone to the nearest student desk tracklet."""
    # Active student tracklet at desk (normalized coordinates)
    student_track = Tracklet(
        tracking_id="trk-cam-01-001",
        camera_id="cam-01",
        box=(300, 100, 200, 300),  # pixel box in a 640x480 frame
        initial_status="IDENTIFIED"
    )
    student_track.student_id = "s-01"
    student_track.student_name = "Dev Sharma"

    # Phone detection lying directly on the desk in front of the student
    phone_item = DetectionItem(
        detection_type="MOBILE_PHONE",
        confidence=0.91,
        bounding_box=BoundingBox(x=0.55, y=0.35, width=0.10, height=0.18),
        tracking_reference="obj-raw-01",
        metadata={"label": "cell phone"}
    )

    correlated = detection_service.correlate_objects_with_tracks(
        detections=[phone_item],
        active_tracks=[student_track],
        camera_id="cam-01"
    )

    assert len(correlated) == 1
    res = correlated[0]
    assert res.metadata.get("correlated_tracking_id") == "trk-cam-01-001"
    assert res.metadata.get("correlated_student_id") == "s-01"
    assert res.metadata.get("correlated_student_name") == "Dev Sharma"
    assert res.metadata.get("spatial_relation") in ["WITHIN_DESK_AREA", "IN_PROXIMITY"]


def test_unattended_phone_detection():
    """TEST 6: A phone detected far from any student is classified as UNATTENDED."""
    # Student on far left
    student_track = Tracklet(
        tracking_id="trk-cam-01-002",
        camera_id="cam-01",
        box=(50, 50, 100, 150),
        initial_status="IDENTIFIED"
    )
    student_track.student_id = "s-02"

    # Phone on far right desk
    phone_item = DetectionItem(
        detection_type="MOBILE_PHONE",
        confidence=0.88,
        bounding_box=BoundingBox(x=0.85, y=0.80, width=0.10, height=0.15),
        tracking_reference="obj-raw-02",
        metadata={"label": "cell phone"}
    )

    correlated = detection_service.correlate_objects_with_tracks(
        detections=[phone_item],
        active_tracks=[student_track],
        camera_id="cam-01",
        proximity_threshold=0.25
    )

    assert len(correlated) == 1
    res = correlated[0]
    assert res.metadata.get("spatial_relation") == "UNATTENDED"
    assert res.metadata.get("correlated_student_id") is None


@pytest.mark.asyncio
async def test_behaviour_event_strictly_objective_no_cheating_label():
    """TEST 7: Events record objective facts and NEVER state 'cheating'."""
    event = await behaviour_service.create_behaviour_event(
        exam_session_id="ses-01",
        camera_id="cam-01",
        behaviour_type="MOBILE_PHONE_DETECTED",
        confidence=0.92,
        student_id="s-01",
        tracking_id="trk-cam-01-001",
        metadata={"spatial_relation": "WITHIN_DESK_AREA"}
    )

    assert event.behaviour_type == "MOBILE_PHONE_DETECTED"
    assert "cheating" not in event.behaviour_type.lower()
    assert "cheater" not in str(event.metadata).lower()
    assert event.confidence == 0.92


def test_suspicion_engine_scoring_on_phone():
    """TEST 8: Suspicion engine computes advisory risk score without declaring guilt."""
    from backend.app.models.responses import BehaviourEvent
    from datetime import datetime, timezone

    phone_event = BehaviourEvent(
        event_id="beh-phone-01",
        exam_session_id="ses-01",
        camera_id="cam-01",
        student_id="s-01",
        behaviour_type="MOBILE_PHONE_DETECTED",
        confidence=0.95,
        timestamp=datetime.now(timezone.utc)
    )

    score_res = suspicion_service.calculate_suspicion([phone_event])
    # Weight of mobile phone is 45 -> 45 * 0.95 = 42
    assert score_res.score >= 40
    assert score_res.severity in ["MEDIUM", "HIGH"]
    assert score_res.recommended_action in ["MONITOR", "REVIEW_EVIDENCE"]

    # When multiple infractions occur (phone + unknown person):
    unknown_event = BehaviourEvent(
        event_id="beh-unk-01",
        exam_session_id="ses-01",
        camera_id="cam-01",
        behaviour_type="UNKNOWN_PERSON",
        confidence=0.90,
        timestamp=datetime.now(timezone.utc)
    )
    critical_res = suspicion_service.calculate_suspicion([phone_event, unknown_event])
    assert critical_res.score >= 85
    assert critical_res.severity == "CRITICAL"
    assert critical_res.recommended_action == "TRIGGER_IOT_ALARM"


def test_yolo_threshold_configuration():
    """TEST 9: Thresholds can be altered dynamically to control sensitivity."""
    img_path = "backend/models/test_exam_phone.jpg"
    img = cv2.imread(img_path)

    # Very high threshold rejects borderline detections
    strict_dets = yolo_engine.detect_objects(img, conf_threshold=0.98)
    len_strict = len(strict_dets)

    # Standard threshold retains detections
    normal_dets = yolo_engine.detect_objects(img, conf_threshold=0.35)
    len_normal = len(normal_dets)

    assert len_normal >= len_strict


def test_performance_benchmarks_yolo_onnx():
    """TEST 10: Benchmarks YOLOv8 ONNX inference latency on CPU."""
    img = cv2.imread("backend/models/test_exam_phone.jpg")
    assert img is not None

    # Warmup
    _ = yolo_engine.detect_objects(img, conf_threshold=0.35)

    # 1. Letterbox & Preprocess
    t0 = time.perf_counter()
    padded_img, ratio, (dw, dh) = yolo_engine.letterbox(img, (640, 640))
    blob = cv2.dnn.blobFromImage(padded_img, 1.0 / 255.0, (640, 640), swapRB=True)
    t_pre = (time.perf_counter() - t0) * 1000

    # 2. ONNX Forward Pass
    t0 = time.perf_counter()
    outputs = yolo_engine.session.run([yolo_engine.output_name], {yolo_engine.input_name: blob})
    t_infer = (time.perf_counter() - t0) * 1000

    # 3. Postprocess & NMS
    t0 = time.perf_counter()
    preds = np.transpose(outputs[0][0])
    boxes, confs, cids = [], [], []
    for row in preds:
        scores = row[4:]
        cid = int(np.argmax(scores))
        conf = float(scores[cid])
        if conf >= 0.35:
            boxes.append([int(row[0]), int(row[1]), int(row[2]), int(row[3])])
            confs.append(conf)
            cids.append(cid)
    _ = cv2.dnn.NMSBoxes(boxes, confs, 0.35, 0.45)
    t_post = (time.perf_counter() - t0) * 1000

    total_ms = t_pre + t_infer + t_post
    fps = 1000.0 / total_ms

    print(f"\n[YOLO ONNX BENCHMARK] Pre: {t_pre:.2f}ms | Inference: {t_infer:.2f}ms | Post/NMS: {t_post:.2f}ms")
    print(f"[YOLO FPS] Total: {total_ms:.2f}ms (~{fps:.1f} FPS on CPU)")

    assert total_ms < 150.0  # Runs under 150ms on CPU
    assert t_infer < 120.0   # ONNX inference under 120ms


def test_dual_pipeline_monitoring_frame_integration(client, auth_headers):
    """TEST 11: End-to-end integration of dual Face + YOLO pipeline via /api/v1/monitoring/frame."""
    img = cv2.imread("backend/models/test_exam_phone.jpg")
    b64 = encode_image_base64(img)

    payload = {
        "camera_id": "cam-01",
        "exam_session_id": "ses-01",
        "exam_id": "exam-01",
        "frame_base64": b64
    }

    resp = client.post("/api/v1/monitoring/frame", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "detected_objects" in data
    assert "recognized_faces" in data
    assert "observable_events" in data
    assert "suspicion_index" in data

    # Verify detected_objects contains MOBILE_PHONE
    detected_types = [obj["detection_type"] for obj in data["detected_objects"]]
    assert "MOBILE_PHONE" in detected_types, f"Expected MOBILE_PHONE in {detected_types}"

    # Verify observable_events contains MOBILE_PHONE_DETECTED
    event_types = [ev["behaviour_type"] for ev in data["observable_events"]]
    assert "MOBILE_PHONE_DETECTED" in event_types
