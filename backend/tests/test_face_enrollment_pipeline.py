import base64
import time
import cv2
import numpy as np
import pytest

from backend.app.services.face_engine import face_engine
from backend.app.integrations.supabase import supabase_db
from backend.app.core.config import settings


def encode_image_base64(img_bgr: np.ndarray) -> str:
    """Helper to convert BGR image to base64 JPEG string."""
    _, buffer = cv2.imencode(".jpg", img_bgr)
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")


def generate_single_face(w=400, h=400, x=200, y=200, rx=90, ry=120) -> np.ndarray:
    """Generates an image with a single synthetic face and landmarks."""
    img = np.ones((h, w, 3), dtype=np.uint8) * 220
    # Head contour
    cv2.ellipse(img, (x, y), (rx, ry), 0, 0, 360, (180, 200, 230), -1)
    # Eyes & Pupils
    cv2.circle(img, (x - 35, y - 25), 14, (50, 50, 50), -1)
    cv2.circle(img, (x + 35, y - 25), 14, (50, 50, 50), -1)
    cv2.circle(img, (x - 35, y - 25), 6, (255, 255, 255), -1)
    cv2.circle(img, (x + 35, y - 25), 6, (255, 255, 255), -1)
    # Eyebrows
    cv2.line(img, (x - 55, y - 45), (x - 15, y - 45), (40, 40, 40), 4)
    cv2.line(img, (x + 15, y - 45), (x + 55, y - 45), (40, 40, 40), 4)
    # Nose
    cv2.line(img, (x, y - 20), (x - 5, y + 15), (100, 100, 100), 3)
    cv2.line(img, (x - 5, y + 15), (x + 10, y + 15), (100, 100, 100), 3)
    # Mouth
    cv2.ellipse(img, (x, y + 55), (35, 15), 0, 0, 180, (40, 40, 180), 4)
    return img


def generate_multi_face() -> np.ndarray:
    """Generates an image with two distinct candidate faces."""
    img = np.ones((400, 700, 3), dtype=np.uint8) * 220
    # Face 1
    cv2.ellipse(img, (180, 200), (70, 90), 0, 0, 360, (180, 200, 230), -1)
    cv2.circle(img, (155, 180), 12, (50, 50, 50), -1)
    cv2.circle(img, (205, 180), 12, (50, 50, 50), -1)
    cv2.ellipse(img, (180, 240), (25, 10), 0, 0, 180, (40, 40, 180), 3)
    # Face 2
    cv2.ellipse(img, (500, 200), (70, 90), 0, 0, 360, (180, 200, 230), -1)
    cv2.circle(img, (475, 180), 12, (50, 50, 50), -1)
    cv2.circle(img, (525, 180), 12, (50, 50, 50), -1)
    cv2.ellipse(img, (500, 240), (25, 10), 0, 0, 180, (40, 40, 180), 3)
    return img


# ==============================================================================
# MODEL INTEGRATION TESTS: ENROLLMENT PIPELINE
# ==============================================================================

def test_valid_single_face_enrollment(client, auth_headers):
    """TEST 1: Valid single-face image successfully enrolls with real biometric vector."""
    face_img = generate_single_face()
    b64 = encode_image_base64(face_img)

    payload = {
        "student_id": "s-01",
        "image_base64": b64,
        "notes": "Testing real enrollment pipeline"
    }
    response = client.post("/api/v1/enrollment/face", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["student_id"] == "s-01"
    assert data["status"] == "VERIFIED"
    assert data["quality_score"] > 35.0
    assert data["model_version"] == settings.FACE_MODEL_VERSION
    assert "face_embedding" not in data


def test_no_face_image_rejection(client, auth_headers):
    """TEST 2: Blank image with no faces is rejected with NO_FACE."""
    blank = np.zeros((400, 400, 3), dtype=np.uint8)
    b64 = encode_image_base64(blank)

    payload = {
        "student_id": "s-01",
        "image_base64": b64
    }
    response = client.post("/api/v1/enrollment/face", json=payload, headers=auth_headers)
    assert response.status_code == 400
    assert "NO_FACE" in response.json()["detail"]


def test_multiple_face_image_rejection(client, auth_headers):
    """TEST 3: Image with multiple faces is rejected with MULTIPLE_FACES."""
    multi = generate_multi_face()
    b64 = encode_image_base64(multi)

    payload = {
        "student_id": "s-01",
        "image_base64": b64
    }
    response = client.post("/api/v1/enrollment/face", json=payload, headers=auth_headers)
    assert response.status_code == 400
    assert "MULTIPLE_FACES" in response.json()["detail"]


def test_corrupt_image_rejection(client, auth_headers):
    """TEST 4: Corrupted base64 payload is rejected with INVALID_IMAGE."""
    payload = {
        "student_id": "s-01",
        "image_base64": "data:image/jpeg;base64,not_valid_image_base64_data_xyz!!!"
    }
    response = client.post("/api/v1/enrollment/face", json=payload, headers=auth_headers)
    assert response.status_code == 400
    assert "INVALID_IMAGE" in response.json()["detail"]


def test_very_small_face_rejection(client, auth_headers):
    """TEST 5: Face dimensions below MIN_FACE_SIZE are rejected."""
    # Force a tiny face by using face_engine directly or testing size threshold
    img = np.ones((100, 100, 3), dtype=np.uint8) * 200
    cv2.circle(img, (50, 50), 15, (50, 50, 50), -1)  # tiny 30x30 circle
    b64 = encode_image_base64(img)

    payload = {
        "student_id": "s-01",
        "image_base64": b64
    }
    response = client.post("/api/v1/enrollment/face", json=payload, headers=auth_headers)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "NO_FACE" in detail or "FACE_TOO_SMALL" in detail


def test_poor_quality_blurred_image_rejection(client, auth_headers):
    """TEST 6: Heavily blurred image fails quality validation with LOW_QUALITY."""
    face_img = generate_single_face()
    blurred = cv2.GaussianBlur(face_img, (51, 51), 30)
    b64 = encode_image_base64(blurred)

    payload = {
        "student_id": "s-01",
        "image_base64": b64
    }
    response = client.post("/api/v1/enrollment/face", json=payload, headers=auth_headers)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "LOW_QUALITY" in detail or "NO_FACE" in detail


def test_unknown_student_rejection(client, auth_headers):
    """TEST 7: Enrolling an unknown student ID yields 404 Not Found."""
    face_img = generate_single_face()
    b64 = encode_image_base64(face_img)

    payload = {
        "student_id": "non-existent-student-9999",
        "image_base64": b64
    }
    response = client.post("/api/v1/enrollment/face", json=payload, headers=auth_headers)
    assert response.status_code == 404


def test_embedding_generation_and_dimension():
    """TEST 8: Real face recognition model extracts embedding vector."""
    face_img = generate_single_face()
    faces = face_engine.detect_faces(face_img)
    assert len(faces) == 1
    embedding, aligned = face_engine.extract_embedding(face_img, faces[0])
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape in [(128,), (512,)]
    assert aligned.shape == (112, 112, 3)


def test_embedding_l2_normalization():
    """TEST 9: Embedding vectors are strictly L2-normalized (norm == 1.0)."""
    face_img = generate_single_face()
    faces = face_engine.detect_faces(face_img)
    embedding, _ = face_engine.extract_embedding(face_img, faces[0])
    l2_norm = np.linalg.norm(embedding)
    assert abs(l2_norm - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_database_persistence_and_retrieval():
    """TEST 10: Face profile persists to storage and is retrievable by exam."""
    face_img = generate_single_face()
    faces = face_engine.detect_faces(face_img)
    embedding, _ = face_engine.extract_embedding(face_img, faces[0])
    emb_bytes = embedding.tobytes()

    success, is_reenroll = await supabase_db.save_student_face_profile(
        student_id="s-02",
        embedding_bytes=emb_bytes,
        model_version=settings.FACE_MODEL_VERSION,
        quality_score=94.5
    )
    assert success is True

    # Retrieve exam profiles
    profiles = await supabase_db.get_exam_face_profiles("exam-01")
    assert "s-02" in profiles
    retrieved_vec = np.frombuffer(profiles["s-02"], dtype=np.float32)
    assert np.allclose(embedding, retrieved_vec, atol=1e-5)


@pytest.mark.asyncio
async def test_reenrollment_updates_existing_record():
    """TEST 11: Re-enrolling a student updates existing profile and flags is_reenrollment."""
    face_img = generate_single_face()
    faces = face_engine.detect_faces(face_img)
    embedding, _ = face_engine.extract_embedding(face_img, faces[0])

    # Initial enrollment
    await supabase_db.save_student_face_profile("s-03", embedding.tobytes(), "v1", 85.0)

    # Re-enrollment
    success, is_reenroll = await supabase_db.save_student_face_profile(
        student_id="s-03",
        embedding_bytes=embedding.tobytes(),
        model_version="v2",
        quality_score=92.0
    )
    assert success is True
    assert is_reenroll is True


def test_biometric_data_never_leaked_in_api(client, auth_headers):
    """TEST 12: API responses never contain raw embeddings, vectors, or binary blobs."""
    face_img = generate_single_face()
    b64 = encode_image_base64(face_img)

    res = client.post(
        "/api/v1/enrollment/face",
        json={"student_id": "s-01", "image_base64": b64},
        headers=auth_headers
    )
    data = res.json()
    assert "face_embedding" not in data
    assert "embedding" not in data
    assert "vector" not in data


def test_unauthorized_enrollment(client):
    """TEST 13: Enrollment without valid API key header is rejected with 401 or 403."""
    face_img = generate_single_face()
    b64 = encode_image_base64(face_img)
    payload = {"student_id": "s-01", "image_base64": b64}

    # Missing header
    res_no_key = client.post("/api/v1/enrollment/face", json=payload)
    assert res_no_key.status_code == 401

    # Wrong key
    res_bad_key = client.post("/api/v1/enrollment/face", json=payload, headers={"X-API-Key": "invalid"})
    assert res_bad_key.status_code == 403


def test_threshold_configuration_behavior():
    """TEST 14: Biometric thresholds are configurable and match specifications."""
    assert settings.FACE_MATCH_THRESHOLD == 0.65
    assert settings.FACE_UNCERTAIN_THRESHOLD == 0.45
    assert settings.MIN_FACE_SIZE == 60
    assert settings.MIN_QUALITY_SCORE == 35.0


def test_invalid_image_format(client, auth_headers):
    """TEST 15: Non-image or corrupted text payloads fail gracefully."""
    res = client.post(
        "/api/v1/enrollment/face",
        json={"student_id": "s-01", "image_base64": "hello-world-not-base64"},
        headers=auth_headers
    )
    assert res.status_code == 400
    assert "INVALID_IMAGE" in res.json()["detail"]


def test_performance_benchmarking():
    """TEST 16: Performance benchmarking of real face pipeline on CPU."""
    face_img = generate_single_face()
    b64 = encode_image_base64(face_img)

    # 1. Decode time
    t0 = time.perf_counter()
    img = face_engine.decode_image(b64)
    t_decode = (time.perf_counter() - t0) * 1000

    # 2. Detect time
    t0 = time.perf_counter()
    faces = face_engine.detect_faces(img)
    t_detect = (time.perf_counter() - t0) * 1000
    assert len(faces) == 1

    # 3. Quality score time
    t0 = time.perf_counter()
    score, details = face_engine.calculate_quality_score(img, faces[0]["box"], faces[0]["confidence"])
    t_quality = (time.perf_counter() - t0) * 1000

    # 4. Extract embedding time
    t0 = time.perf_counter()
    embedding, _ = face_engine.extract_embedding(img, faces[0])
    t_extract = (time.perf_counter() - t0) * 1000

    total_time = t_decode + t_detect + t_quality + t_extract

    print(f"\n[BENCHMARK] Decode: {t_decode:.2f}ms | Detect (YuNet): {t_detect:.2f}ms | "
          f"Quality: {t_quality:.2f}ms | Extract (SFace): {t_extract:.2f}ms | "
          f"Total: {total_time:.2f}ms")

    assert total_time < 500.0  # Must be fast on CPU (< 500ms)
    assert score > 35.0
