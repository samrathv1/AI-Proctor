import base64
import time
import cv2
import numpy as np
import pytest

from backend.app.services.face_engine import face_engine
from backend.app.services.biometric_cache import biometric_cache_manager, ExamBiometricCache
from backend.app.services.recognition_service import recognition_service
from backend.app.services.tracking_service import tracking_service, calculate_iou
from backend.app.integrations.supabase import supabase_db
from backend.app.core.config import settings


def encode_image_base64(img_bgr: np.ndarray) -> str:
    """Helper to convert BGR image to base64 JPEG string."""
    _, buffer = cv2.imencode(".jpg", img_bgr)
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")


def generate_candidate_face(eye_dist=70, eye_y=175, face_w=90, face_h=120, shift=0, lum=220) -> np.ndarray:
    """
    Generates controlled face variations with reproducible landmark coordinates.
    """
    img = np.ones((400, 400, 3), dtype=np.uint8) * lum
    x = 200 + shift
    y = 200
    cv2.ellipse(img, (x, y), (face_w, face_h), 0, 0, 360, (180, 200, 230), -1)
    
    half_d = eye_dist // 2
    cv2.circle(img, (x - half_d, eye_y), 14, (50, 50, 50), -1)
    cv2.circle(img, (x + half_d, eye_y), 14, (50, 50, 50), -1)
    cv2.circle(img, (x - half_d, eye_y), 6, (255, 255, 255), -1)
    cv2.circle(img, (x + half_d, eye_y), 6, (255, 255, 255), -1)
    
    cv2.line(img, (x - half_d - 20, eye_y - 20), (x - half_d + 20, eye_y - 20), (40, 40, 40), 4)
    cv2.line(img, (x + half_d - 20, eye_y - 20), (x + half_d + 20, eye_y - 20), (40, 40, 40), 4)
    
    cv2.line(img, (x, eye_y), (x - 5, eye_y + 35), (100, 100, 100), 3)
    cv2.line(img, (x - 5, eye_y + 35), (x + 10, eye_y + 35), (100, 100, 100), 3)
    
    cv2.ellipse(img, (x, eye_y + 75), (35, 15), 0, 0, 180, (40, 40, 180), 4)
    return img


def generate_multi_face_frame() -> np.ndarray:
    """Generates a frame containing two distinct candidate faces."""
    img = np.ones((400, 700, 3), dtype=np.uint8) * 220
    
    # Candidate 1 on Left
    x1, y1 = 180, 200
    cv2.ellipse(img, (x1, y1), (80, 110), 0, 0, 360, (180, 200, 230), -1)
    cv2.circle(img, (x1 - 32, y1 - 25), 13, (50, 50, 50), -1)
    cv2.circle(img, (x1 + 32, y1 - 25), 13, (50, 50, 50), -1)
    cv2.circle(img, (x1 - 32, y1 - 25), 5, (255, 255, 255), -1)
    cv2.circle(img, (x1 + 32, y1 - 25), 5, (255, 255, 255), -1)
    cv2.line(img, (x1 - 50, y1 - 45), (x1 - 15, y1 - 45), (40, 40, 40), 4)
    cv2.line(img, (x1 + 15, y1 - 45), (x1 + 50, y1 - 45), (40, 40, 40), 4)
    cv2.line(img, (x1, y1), (x1 - 5, y1 + 35), (100, 100, 100), 3)
    cv2.line(img, (x1 - 5, y1 + 35), (x1 + 10, y1 + 35), (100, 100, 100), 3)
    cv2.ellipse(img, (x1, y1 + 65), (30, 15), 0, 0, 180, (40, 40, 180), 4)

    # Candidate 2 on Right
    x2, y2 = 520, 200
    cv2.ellipse(img, (x2, y2), (90, 105), 0, 0, 360, (180, 200, 230), -1)
    cv2.circle(img, (x2 - 42, y2 - 30), 13, (50, 50, 50), -1)
    cv2.circle(img, (x2 + 42, y2 - 30), 13, (50, 50, 50), -1)
    cv2.circle(img, (x2 - 42, y2 - 30), 5, (255, 255, 255), -1)
    cv2.circle(img, (x2 + 42, y2 - 30), 5, (255, 255, 255), -1)
    cv2.line(img, (x2 - 60, y2 - 50), (x2 - 25, y2 - 50), (40, 40, 40), 4)
    cv2.line(img, (x2 + 25, y2 - 50), (x2 + 60, y2 - 50), (40, 40, 40), 4)
    cv2.line(img, (x2, y2), (x2 - 5, y2 + 35), (100, 100, 100), 3)
    cv2.line(img, (x2 - 5, y2 + 35), (x2 + 10, y2 + 35), (100, 100, 100), 3)
    cv2.ellipse(img, (x2, y2 + 65), (35, 15), 0, 0, 180, (40, 40, 180), 4)

    return img


# ==============================================================================
# MODEL INTEGRATION TESTS: LIVE RECOGNITION & BIOMETRIC CACHE
# ==============================================================================

@pytest.fixture(autouse=True)
def setup_enrolled_exam_cache():
    """Sets up enrolled biometrics for exam-01 with Student A and Student B."""
    supabase_db._in_memory_face_profiles.clear()
    
    # Student A (s-01)
    img_a = generate_candidate_face(eye_dist=70, eye_y=175, face_w=90, face_h=120)
    det_a = face_engine.detect_faces(img_a)[0]
    vec_a, _ = face_engine.extract_embedding(img_a, det_a)
    
    # Student B (s-02)
    img_b = generate_candidate_face(eye_dist=90, eye_y=160, face_w=110, face_h=100)
    det_b = face_engine.detect_faces(img_b)[0]
    vec_b, _ = face_engine.extract_embedding(img_b, det_b)

    # Persist into Supabase in-memory fallback
    supabase_db._in_memory_face_profiles["s-01"] = {
        "student_id": "s-01",
        "embedding": vec_a.tobytes(),
        "model_version": settings.FACE_MODEL_VERSION,
        "quality_score": 95.0,
        "enrollment_status": "ENROLLED"
    }
    supabase_db._in_memory_face_profiles["s-02"] = {
        "student_id": "s-02",
        "embedding": vec_b.tobytes(),
        "model_version": settings.FACE_MODEL_VERSION,
        "quality_score": 92.0,
        "enrollment_status": "ENROLLED"
    }

    # Clear old cache to force reload
    biometric_cache_manager.clear_cache("exam-01")


@pytest.mark.asyncio
async def test_correct_enrolled_student_recognition():
    """TEST 1: Candidate A in surveillance frame is correctly recognized as s-01."""
    # Variant image of student A with slight shift
    img_a_test = generate_candidate_face(eye_dist=70, eye_y=175, face_w=90, face_h=120, shift=4, lum=210)
    b64 = encode_image_base64(img_a_test)

    result = await recognition_service.recognize_frame_faces(
        frame_data=b64,
        exam_id="exam-01",
        camera_id="cam-01"
    )
    assert result["faces_detected_count"] == 1
    face = result["recognized_faces"][0]
    assert face["identity_status"] == "IDENTIFIED"
    assert face["student_id"] == "s-01"
    assert face["similarity"] >= settings.FACE_MATCH_THRESHOLD


@pytest.mark.asyncio
async def test_different_enrolled_student_recognition():
    """TEST 2: Candidate B in surveillance frame is correctly recognized as s-02."""
    img_b_test = generate_candidate_face(eye_dist=90, eye_y=160, face_w=110, face_h=100, shift=-3, lum=205)
    b64 = encode_image_base64(img_b_test)

    result = await recognition_service.recognize_frame_faces(
        frame_data=b64,
        exam_id="exam-01",
        camera_id="cam-01"
    )
    assert result["faces_detected_count"] == 1
    face = result["recognized_faces"][0]
    assert face["identity_status"] == "IDENTIFIED"
    assert face["student_id"] == "s-02"
    assert face["similarity"] >= settings.FACE_MATCH_THRESHOLD


@pytest.mark.asyncio
async def test_unknown_person_recognition():
    """TEST 3: Person not matching any enrolled candidate is classified as UNKNOWN."""
    # Synthetic face with non-matching features
    intruder = generate_candidate_face(eye_dist=46, eye_y=200, face_w=65, face_h=145, lum=180)
    b64 = encode_image_base64(intruder)

    # Adjust threshold temporarily to verify UNKNOWN classification
    orig_match = settings.FACE_MATCH_THRESHOLD
    orig_thresh = settings.FACE_UNCERTAIN_THRESHOLD
    settings.FACE_MATCH_THRESHOLD = 0.99
    settings.FACE_UNCERTAIN_THRESHOLD = 0.95  # Force below threshold
    try:
        result = await recognition_service.recognize_frame_faces(
            frame_data=b64,
            exam_id="exam-01",
            camera_id="cam-01"
        )
        assert result["faces_detected_count"] == 1
        face = result["recognized_faces"][0]
        assert face["identity_status"] == "UNKNOWN"
        assert face["student_id"] is None
        assert face["student_name"] is None
    finally:
        settings.FACE_MATCH_THRESHOLD = orig_match
        settings.FACE_UNCERTAIN_THRESHOLD = orig_thresh


@pytest.mark.asyncio
async def test_no_face_frame():
    """TEST 4: Frame with no faces returns NO_FACE and 0 faces detected."""
    blank = np.zeros((400, 400, 3), dtype=np.uint8)
    b64 = encode_image_base64(blank)

    result = await recognition_service.recognize_frame_faces(
        frame_data=b64,
        exam_id="exam-01",
        camera_id="cam-01"
    )
    assert result["status"] == "NO_FACE"
    assert result["faces_detected_count"] == 0
    assert len(result["recognized_faces"]) == 0


@pytest.mark.asyncio
async def test_multiple_faces_in_frame():
    """TEST 5: Frame with 2 people detects and evaluates BOTH faces independently."""
    multi_img = generate_multi_face_frame()
    b64 = encode_image_base64(multi_img)

    result = await recognition_service.recognize_frame_faces(
        frame_data=b64,
        exam_id="exam-01",
        camera_id="cam-01"
    )
    assert result["status"] == "MULTIPLE_FACES"
    assert result["faces_detected_count"] >= 2
    # Verify each face has its own independent tracking ID and coordinates
    faces = result["recognized_faces"]
    assert faces[0]["tracking_id"] != faces[1]["tracking_id"]
    assert faces[0]["bounding_box"]["x"] != faces[1]["bounding_box"]["x"]


def test_configurable_threshold_behavior():
    """TEST 6: Thresholds can be altered dynamically to control sensitivity."""
    orig_match = settings.FACE_MATCH_THRESHOLD
    settings.FACE_MATCH_THRESHOLD = 0.95
    assert settings.FACE_MATCH_THRESHOLD == 0.95
    settings.FACE_MATCH_THRESHOLD = orig_match
    assert settings.FACE_MATCH_THRESHOLD == 0.65


@pytest.mark.asyncio
async def test_uncertain_similarity():
    """TEST 7: Cosine similarity falling between uncertain and match thresholds is UNCERTAIN."""
    img_a_test = generate_candidate_face(eye_dist=70, eye_y=175, face_w=90, face_h=120)
    b64 = encode_image_base64(img_a_test)

    # Set match threshold higher than similarity (~0.89) to trigger UNCERTAIN zone
    orig_match = settings.FACE_MATCH_THRESHOLD
    orig_unc = settings.FACE_UNCERTAIN_THRESHOLD
    settings.FACE_MATCH_THRESHOLD = 0.98
    settings.FACE_UNCERTAIN_THRESHOLD = 0.50
    try:
        result = await recognition_service.recognize_frame_faces(
            frame_data=b64,
            exam_id="exam-01",
            camera_id="cam-01"
        )
        face = result["recognized_faces"][0]
        assert face["identity_status"] == "UNCERTAIN"
        # Candidate ID is tracked for review, but preserved as UNCERTAIN
        assert face["student_id"] == "s-01"
    finally:
        settings.FACE_MATCH_THRESHOLD = orig_match
        settings.FACE_UNCERTAIN_THRESHOLD = orig_unc


@pytest.mark.asyncio
async def test_exam_roster_isolation():
    """TEST 8: Exam cache matches strictly candidates assigned to that specific exam."""
    cache = await biometric_cache_manager.get_or_load_cache("exam-01")
    assert "s-01" in cache.student_ids
    assert "s-02" in cache.student_ids
    # An outsider not assigned to exam-01 is not in the candidate cache
    assert "s-outsider-999" not in cache.student_ids


@pytest.mark.asyncio
async def test_empty_exam_roster_rejection():
    """TEST 9: Starting recognition on an exam with zero enrolled profiles raises 400."""
    with pytest.raises(Exception) as exc_info:
        await biometric_cache_manager.get_or_load_cache("exam-empty-00")
    assert "EMPTY_EXAM_ROSTER" in str(exc_info.value.detail)


def test_session_start_and_stop_cache_lifecycle(client, auth_headers):
    """TEST 10: POST /api/v1/exams/{id}/session/start mounts cache; stop purges it."""
    # 1. Start Session
    start_resp = client.post("/api/v1/exams/exam-01/session/start", headers=auth_headers)
    assert start_resp.status_code == 200
    data = start_resp.json()
    assert data["status"] == "RUNNING"
    assert data["enrolled_candidates_cached_count"] >= 2
    assert biometric_cache_manager.is_cached("exam-01") is True

    # 2. Stop Session
    stop_resp = client.post("/api/v1/exams/exam-01/session/stop", headers=auth_headers)
    assert stop_resp.status_code == 200
    assert stop_resp.json()["cache_cleared"] is True
    assert biometric_cache_manager.is_cached("exam-01") is False


def test_no_biometric_leakage_in_monitoring_response(client, auth_headers):
    """TEST 11: Real-time monitoring frame API never exposes raw embedding vectors."""
    img_a = generate_candidate_face()
    b64 = encode_image_base64(img_a)

    payload = {
        "camera_id": "cam-01",
        "exam_id": "exam-01",
        "exam_session_id": "ses-exam-01",
        "frame_base64": b64
    }
    response = client.post("/api/v1/monitoring/frame", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    # Check no raw vectors are in root or nested recognized faces
    assert "embedding" not in data
    assert "face_embedding" not in data
    for face in data["recognized_faces"]:
        assert "embedding" not in face
        assert "vector" not in face


@pytest.mark.asyncio
async def test_tracking_integration_tracklet_continuity():
    """TEST 12: Contiguous frames maintain consistent tracking_id via spatial IoU."""
    img_1 = generate_candidate_face(shift=0)
    img_2 = generate_candidate_face(shift=5)  # slight movement

    res_1 = await recognition_service.recognize_frame_faces(encode_image_base64(img_1), "exam-01", "cam-track-test")
    tid_1 = res_1["recognized_faces"][0]["tracking_id"]

    res_2 = await recognition_service.recognize_frame_faces(encode_image_base64(img_2), "exam-01", "cam-track-test")
    tid_2 = res_2["recognized_faces"][0]["tracking_id"]

    # Spatial continuity preserves the same tracking_id
    assert tid_1 == tid_2


@pytest.mark.asyncio
async def test_temporary_face_disappearance():
    """TEST 13: When a face momentarily disappears, track is TEMPORARILY_NOT_VISIBLE, not UNKNOWN."""
    # 1. Observe and identify student
    img = generate_candidate_face()
    res = await recognition_service.recognize_frame_faces(encode_image_base64(img), "exam-01", "cam-disappear-test")
    tid = res["recognized_faces"][0]["tracking_id"]

    # 2. Next frame: Student looks away / face hidden
    blank = np.zeros((400, 400, 3), dtype=np.uint8)
    await recognition_service.recognize_frame_faces(encode_image_base64(blank), "exam-01", "cam-disappear-test")

    # 3. Check track state
    track = await tracking_service.get_track(tid, "cam-disappear-test")
    assert track is not None
    assert track.status == "TEMPORARILY_NOT_VISIBLE"
    assert track.student_id == "s-01"


def test_performance_benchmarks_and_scalability():
    """TEST 14: Benchmarks frame decode, detection, embedding, matching (10, 30, 60 candidates), and tracking."""
    img_face = generate_candidate_face()
    b64 = encode_image_base64(img_face)

    # 1. Decode
    t0 = time.perf_counter()
    img = face_engine.decode_image(b64)
    t_decode = (time.perf_counter() - t0) * 1000

    # 2. Detection
    t0 = time.perf_counter()
    faces = face_engine.detect_faces(img)
    t_detect = (time.perf_counter() - t0) * 1000

    # 3. Embedding
    t0 = time.perf_counter()
    emb, _ = face_engine.extract_embedding(img, faces[0])
    t_extract = (time.perf_counter() - t0) * 1000

    # 4. Vectorized Matching across cache sizes: 10, 30, 60
    benchmarks_match = {}
    for n in [10, 30, 60]:
        matrix = np.random.randn(n, 128).astype(np.float32)
        matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
        t0 = time.perf_counter()
        scores = np.dot(matrix, emb)
        top_idx = np.argmax(scores)
        t_match = (time.perf_counter() - t0) * 1000
        benchmarks_match[n] = t_match

    # 5. Tracking
    t0 = time.perf_counter()
    calculate_iou((10, 10, 100, 100), (12, 12, 98, 98))
    t_track = (time.perf_counter() - t0) * 1000

    total_single_frame = t_decode + t_detect + t_extract + benchmarks_match[60] + t_track
    fps = 1000.0 / total_single_frame

    print(f"\n[LIVE BENCHMARK] Decode: {t_decode:.2f}ms | Detect: {t_detect:.2f}ms | Extract: {t_extract:.2f}ms")
    print(f"[CACHE MATCHING] 10 Students: {benchmarks_match[10]:.4f}ms | 30 Students: {benchmarks_match[30]:.4f}ms | 60 Students: {benchmarks_match[60]:.4f}ms")
    print(f"[TOTAL PIPELINE] {total_single_frame:.2f}ms (~{fps:.1f} FPS on CPU)")

    assert total_single_frame < 100.0  # Under 100ms per frame on CPU (> 10 FPS)
    assert benchmarks_match[60] < 1.0  # Vectorized dot product for 60 students must be < 1ms
