import cv2
import numpy as np
from backend.tests.test_face_enrollment_pipeline import generate_single_face, encode_image_base64


def test_enrollment_real_face_verified(client, auth_headers):
    face_img = generate_single_face()
    b64 = encode_image_base64(face_img)
    payload = {
        "student_id": "s-01",
        "image_base64": b64,
        "notes": "Testing face enrollment verified state"
    }
    response = client.post("/api/v1/enrollment/face", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["student_id"] == "s-01"
    assert data["status"] == "VERIFIED"
    assert data["quality_score"] > 35.0
    # STRICT REQUIREMENT: No biometric vector leaked
    assert "face_embedding" not in data


def test_enrollment_invalid_student(client, auth_headers):
    face_img = generate_single_face()
    b64 = encode_image_base64(face_img)
    payload = {
        "student_id": "unknown-student-999",
        "image_base64": b64
    }
    response = client.post("/api/v1/enrollment/face", json=payload, headers=auth_headers)
    assert response.status_code == 404


def test_enrollment_missing_or_corrupt_image(client, auth_headers):
    payload = {
        "student_id": "s-01",
        "image_base64": "too-short"
    }
    response = client.post("/api/v1/enrollment/face", json=payload, headers=auth_headers)
    assert response.status_code == 400
