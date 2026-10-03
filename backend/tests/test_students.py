import io
import cv2
import numpy as np


def test_get_student_success(client, auth_headers):
    response = client.get("/api/v1/students/s-01", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "s-01"
    assert data["name"] == "Dev Sharma"
    assert data["roll_number"] == "CS-2026-042"
    # CRITICAL SECURITY ASSERTION: No biometric embedding leaked
    assert "face_embedding" not in data
    assert "embedding" not in data


def test_get_student_not_found(client, auth_headers):
    response = client.get("/api/v1/students/non-existent-student", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_exam_roster_success(client, auth_headers):
    response = client.get("/api/v1/students/exam/exam-01", headers=auth_headers)
    assert response.status_code == 200
    roster = response.json()
    assert isinstance(roster, list)
    assert len(roster) >= 3
    # Check candidate fields
    first = roster[0]
    assert "student_id" in first
    assert "seat_number" in first
    assert "risk_score" in first


def test_get_exam_roster_not_found(client, auth_headers):
    response = client.get("/api/v1/students/exam/invalid-exam-999", headers=auth_headers)
    assert response.status_code == 404


def test_student_auth_unauthorized(client):
    # Missing API key header
    response = client.get("/api/v1/students/s-01")
    assert response.status_code == 401

    # Invalid API key header
    response = client.get("/api/v1/students/s-01", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403


# ==============================================================================
# PROMPT 8: REAL STUDENT IDENTITY, LOGIN & ENROLLMENT TESTS
# ==============================================================================

def test_student_registration_and_login_flow(client, auth_headers):
    # 1. Register a new candidate
    reg_payload = {
        "name": "Priya Patel",
        "roll_number": "CS-2026-088",
        "email": "priya.patel@institution.edu",
        "class_name": "CS-2026",
        "department": "Computer Science & Engineering"
    }
    reg_res = client.post("/api/v1/students/register", json=reg_payload, headers=auth_headers)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["name"] == "Priya Patel"
    assert reg_data["roll_number"] == "CS-2026-088"
    new_student_id = reg_data["id"]

    # 2. Duplicate registration rejected
    dup_res = client.post("/api/v1/students/register", json=reg_payload, headers=auth_headers)
    assert dup_res.status_code == 409

    # 3. Student Login by Roll Number
    login_res = client.post("/api/v1/students/login", json={"identifier": "CS-2026-088"}, headers=auth_headers)
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["success"] is True
    assert login_data["student"]["id"] == new_student_id
    assert login_data["face_enrolled"] is False
    assert login_data["enrollment_status"] == "PENDING"

    # 4. Student Login by Email
    login_email_res = client.post("/api/v1/students/login", json={"identifier": "priya.patel@institution.edu"}, headers=auth_headers)
    assert login_email_res.status_code == 200

    # 5. Check Initial Face Enrollment Status
    status_res = client.get(f"/api/v1/students/{new_student_id}/face/status", headers=auth_headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["enrollment_status"] == "PENDING"
    assert status_data["has_embedding"] is False


def test_photo_upload_enrollment_and_login_status_update(client, auth_headers):
    # Register candidate
    reg_payload = {
        "name": "Vikram Singh",
        "roll_number": "CS-2026-077",
        "email": "vikram.singh@institution.edu"
    }
    reg_res = client.post("/api/v1/students/register", json=reg_payload, headers=auth_headers)
    assert reg_res.status_code == 201
    sid = reg_res.json()["id"]

    # Generate valid portrait face
    from backend.tests.test_face_enrollment_pipeline import generate_single_face
    img = generate_single_face()
    _, buf = cv2.imencode(".jpg", img)
    file_bytes = buf.tobytes()

    # Option A: Photo Upload
    files = {"file": ("portrait.jpg", file_bytes, "image/jpeg")}
    data = {"notes": "Uploaded via admissions portal"}
    upload_res = client.post(
        f"/api/v1/students/{sid}/face/enroll/upload",
        files=files,
        data=data,
        headers=auth_headers
    )
    assert upload_res.status_code == 200
    enroll_data = upload_res.json()
    assert enroll_data["status"] == "VERIFIED"
    assert enroll_data["student_id"] == sid
    assert enroll_data["quality_score"] > 50.0

    # Check updated face status
    status_res = client.get(f"/api/v1/students/{sid}/face/status", headers=auth_headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["enrollment_status"] == "ENROLLED"
    assert status_data["has_embedding"] is True

    # Re-login should now reflect face_enrolled: True
    login_res = client.post("/api/v1/students/login", json={"identifier": "CS-2026-077"}, headers=auth_headers)
    assert login_res.status_code == 200
    assert login_res.json()["face_enrolled"] is True
    assert login_res.json()["enrollment_status"] == "ENROLLED"


def test_photo_upload_invalid_type_and_empty(client, auth_headers):
    # Invalid file type (.txt)
    files = {"file": ("notes.txt", b"not an image", "text/plain")}
    res = client.post(
        "/api/v1/students/s-01/face/enroll/upload",
        files=files,
        headers=auth_headers
    )
    assert res.status_code == 400
    assert "invalid file type" in res.json()["detail"].lower()

    # Empty file
    empty_files = {"file": ("empty.jpg", b"", "image/jpeg")}
    empty_res = client.post(
        "/api/v1/students/s-01/face/enroll/upload",
        files=empty_files,
        headers=auth_headers
    )
    assert empty_res.status_code == 400


def test_webcam_base64_enrollment_and_live_recognition(client, auth_headers):
    # 1. Register Candidate
    reg_payload = {
        "name": "Aarav Sharma",
        "roll_number": "CS-2026-055",
        "email": "aarav.sharma@institution.edu"
    }
    reg_res = client.post("/api/v1/students/register", json=reg_payload, headers=auth_headers)
    assert reg_res.status_code == 201
    sid = reg_res.json()["id"]

    # 2. Option B: Webcam Base64 Enrollment with unique biometric face geometry
    from backend.tests.test_face_enrollment_pipeline import generate_single_face
    img = generate_single_face(w=450, h=450, x=225, y=225, rx=80, ry=130)
    _, buf = cv2.imencode(".jpg", img)
    import base64
    b64_img = "data:image/jpeg;base64," + base64.b64encode(buf).decode("utf-8")

    enroll_payload = {
        "student_id": sid,
        "image_base64": b64_img
    }
    enroll_res = client.post(
        f"/api/v1/students/{sid}/face/enroll",
        json=enroll_payload,
        headers=auth_headers
    )
    assert enroll_res.status_code == 200
    assert enroll_res.json()["status"] == "VERIFIED"
    assert enroll_res.json()["student_id"] == sid

    # 3. Check Database Enrollment Status
    status_res = client.get(f"/api/v1/students/{sid}/face/status", headers=auth_headers)
    assert status_res.status_code == 200
    assert status_res.json()["enrollment_status"] == "ENROLLED"
    assert status_res.json()["has_embedding"] is True

    # 4. Live Frame Recognition: Submit same candidate face in an exam frame
    frame_payload = {
        "camera_id": "cam-webcam-01",
        "exam_session_id": "ses-exam-01",
        "exam_id": "exam-01",
        "frame_base64": b64_img
    }
    mon_res = client.post("/api/v1/monitoring/frame", json=frame_payload, headers=auth_headers)
    assert mon_res.status_code == 200
    mon_data = mon_res.json()
    assert mon_data["faces_detected_count"] >= 1
    
    # Must identify Aarav Sharma
    recognized_faces = mon_data.get("recognized_faces", [])
    assert len(recognized_faces) >= 1
    target = recognized_faces[0]
    assert target["identity_status"] == "IDENTIFIED"
    assert target["student_id"] == sid
    assert target["student_name"] == "Aarav Sharma"
    assert "tracking_id" in target


def test_cctv_multi_person_independent_identities(client, auth_headers):
    """
    Verifies that CCTV frames with multiple candidates:
    1. Do not require pre-login on the camera.
    2. Track all faces independently without stopping after the first face.
    3. Enrolled faces are IDENTIFIED while non-enrolled faces remain UNKNOWN.
    """
    from backend.tests.test_face_enrollment_pipeline import generate_multi_face
    img = generate_multi_face()
    _, buf = cv2.imencode(".jpg", img)
    import base64
    b64_multi = "data:image/jpeg;base64," + base64.b64encode(buf).decode("utf-8")

    cctv_payload = {
        "camera_id": "cctv-hall304-01",
        "exam_session_id": "ses-exam-01",
        "exam_id": "exam-01",
        "frame_base64": b64_multi
    }
    res = client.post("/api/v1/monitoring/frame", json=cctv_payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    faces = data.get("recognized_faces", [])
    assert len(faces) >= 2, "CCTV frame must detect and track multiple candidates independently"

    # Verify each has a unique tracking ID
    track_ids = [f["tracking_id"] for f in faces]
    assert len(set(track_ids)) == len(track_ids), "Each person in frame must receive an independent tracking ID"

    # Non-enrolled candidates must have identity_status UNKNOWN with student_id=None and student_name=None
    unknown_faces = [f for f in faces if f["identity_status"] == "UNKNOWN"]
    for unk in unknown_faces:
        assert unk["student_id"] is None
        assert unk["student_name"] is None


