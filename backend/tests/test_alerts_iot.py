def test_create_alert_endpoint(client, auth_headers):
    payload = {
        "exam_session_id": "ses-01",
        "exam_id": "exam-01",
        "student_id": "s-01",
        "camera_id": "cam-01",
        "alert_type": "MOBILE_PHONE",
        "severity": "CRITICAL",
        "confidence": 95,
        "suspicion_score": 92,
        "title": "Unauthorized Mobile Phone In Examination Desk",
        "description": "High-confidence detection in candidate lap area.",
        "evidence_storage_path": "alert-evidence/evidence-alt-01.svg"
    }
    response = client.post("/api/v1/alerts", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["alert_type"] == "MOBILE_PHONE"
    assert data["severity"] == "CRITICAL"
    assert data["status"] == "OPEN"


def test_esp32_heartbeat_authorized(client, esp32_headers):
    payload = {
        "device_uid": "ESP32-HALL304-01",
        "ip_address": "192.168.1.10",
        "firmware_version": "v2.4.1-ai-proctor",
        "rssi": -55
    }
    response = client.post("/api/v1/iot/heartbeat", json=payload, headers=esp32_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"


def test_esp32_heartbeat_unauthorized(client):
    payload = {
        "device_uid": "ESP32-HALL304-01",
        "ip_address": "192.168.1.10",
        "firmware_version": "v2.4.1-ai-proctor"
    }
    # Missing X-ESP32-Key header
    response = client.post("/api/v1/iot/heartbeat", json=payload)
    assert response.status_code == 401


def test_camera_adapter_mounting(client, auth_headers):
    payload = {
        "camera_id": "cam-rtsp-01",
        "name": "CCTV Hall Center",
        "source_type": "IP_CAMERA",
        "source_reference": "rtsp://camera-stream.local/live",
        "target_fps": 30
    }
    response = client.post("/api/v1/cameras/adapter", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["camera_id"] == "cam-rtsp-01"
    assert data["pipeline_mode"] == "COMMON_AI_FRAME_PIPELINE"
    assert data["status"] == "MOUNTED"
