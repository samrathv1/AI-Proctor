import pytest
import time
from datetime import datetime, timezone, timedelta
from backend.app.services.iot_service import iot_service


def test_device_registration(client, esp32_headers):
    payload = {
        "device_id": "ESP32-TEST-REG-01",
        "device_name": "Test Room Beacon",
        "device_type": "ESP32_ALERT_BEACON",
        "firmware_version": "1.0.0",
        "ip_address": "192.168.1.155",
        "location": "Room 101",
        "capabilities": ["LED", "BUZZER"]
    }
    response = client.post("/api/v1/iot/devices/register", json=payload, headers=esp32_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["device_id"] == "ESP32-TEST-REG-01"
    assert data["status"] == "ONLINE"


def test_device_heartbeat_updates_status(client, esp32_headers, auth_headers):
    device_id = "ESP32-TEST-HB-01"
    # 1. Register
    reg_payload = {
        "device_id": device_id,
        "device_name": "Heartbeat Test Node",
        "firmware_version": "1.0.0",
        "ip_address": "192.168.1.120"
    }
    client.post("/api/v1/iot/devices/register", json=reg_payload, headers=esp32_headers)

    # 2. Send Heartbeat
    hb_payload = {
        "device_id": device_id,
        "firmware_version": "1.0.1",
        "ip_address": "192.168.1.121",
        "uptime_seconds": 3600,
        "led_ready": True,
        "buzzer_ready": True
    }
    hb_res = client.post("/api/v1/iot/devices/heartbeat", json=hb_payload, headers=esp32_headers)
    assert hb_res.status_code == 200
    assert hb_res.json()["status"] == "acknowledged"

    # 3. Check device status
    status_res = client.get(f"/api/v1/iot/devices/{device_id}", headers=auth_headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["status"] == "ONLINE"
    assert status_data["firmware_version"] == "1.0.1"
    assert status_data["uptime_seconds"] == 3600


def test_offline_detection_on_timeout():
    device_id = "ESP32-TEST-TIMEOUT-01"
    # Register in service
    iot_service._devices[device_id] = {
        "device_id": device_id,
        "device_uid": device_id,
        "status": "ONLINE",
        "last_seen_at": datetime.now(timezone.utc) - timedelta(seconds=120) # 2 minutes ago
    }
    
    # Dynamic status evaluation should return OFFLINE because > 30s * 1.5 tolerance
    status = iot_service._evaluate_device_status(device_id)
    assert status == "OFFLINE"


@pytest.mark.asyncio
async def test_alert_severity_policy_and_dispatch():
    device_id = "ESP32-TEST-ALERT-01"
    # Ensure device is registered and marked online
    iot_service._devices[device_id] = {
        "device_id": device_id,
        "device_uid": device_id,
        "status": "ONLINE",
        "last_seen_at": datetime.now(timezone.utc)
    }
    iot_service._pending_commands[device_id] = []

    # 1. LOW severity alert -> Should NOT trigger ESP32
    low_alert = {"id": "alt-low-01", "severity": "LOW", "alert_type": "GAZE_DRIFT"}
    res_low = await iot_service.dispatch_alert_for_infraction(low_alert, device_id=device_id)
    assert res_low is None

    # 2. MEDIUM severity alert -> Should NOT trigger ESP32
    med_alert = {"id": "alt-med-01", "severity": "MEDIUM", "alert_type": "HEAD_TURN"}
    res_med = await iot_service.dispatch_alert_for_infraction(med_alert, device_id=device_id)
    assert res_med is None

    # 3. HIGH severity alert -> Should trigger PULSE pattern for 3000ms
    high_alert = {"id": "alt-high-01", "severity": "HIGH", "alert_type": "MOBILE_PHONE"}
    res_high = await iot_service.dispatch_alert_for_infraction(high_alert, device_id=device_id)
    assert res_high is not None
    assert res_high.severity == "HIGH"
    assert res_high.pattern == "PULSE"
    assert res_high.duration_ms == 3000
    assert res_high.led is True
    assert res_high.buzzer is True


@pytest.mark.asyncio
async def test_alert_cooldown_prevents_buzzer_spam():
    device_id = "ESP32-TEST-COOLDOWN-01"
    iot_service._devices[device_id] = {
        "device_id": device_id,
        "device_uid": device_id,
        "status": "ONLINE",
        "last_seen_at": datetime.now(timezone.utc)
    }
    iot_service._pending_commands[device_id] = []
    # Clear cooldown tracker
    iot_service._cooldown_tracker.clear()

    # First HIGH alert -> Dispatches successfully
    alert_1 = {"id": "alt-cd-01", "severity": "HIGH", "alert_type": "PHONE_ON_DESK"}
    res_1 = await iot_service.dispatch_alert_for_infraction(alert_1, device_id=device_id)
    assert res_1 is not None

    # Immediate second HIGH alert of same type -> Suppressed by cooldown
    alert_2 = {"id": "alt-cd-02", "severity": "HIGH", "alert_type": "PHONE_ON_DESK"}
    res_2 = await iot_service.dispatch_alert_for_infraction(alert_2, device_id=device_id)
    assert res_2 is None # Blocked by cooldown!


def test_command_polling_and_acknowledgment(client, esp32_headers):
    device_id = "ESP32-TEST-ACK-01"
    # Register device
    reg_payload = {"device_id": device_id, "device_name": "Ack Test Node", "ip_address": "192.168.1.180"}
    client.post("/api/v1/iot/devices/register", json=reg_payload, headers=esp32_headers)

    # Queue a manual test command
    from backend.app.models.responses import IoTCommandPayload
    cmd_id = f"cmd-ack-test-{int(time.time())}"
    payload = IoTCommandPayload(
        command_id=cmd_id,
        command="ALERT",
        severity="HIGH",
        led=True,
        buzzer=True,
        duration_ms=3000,
        pattern="PULSE",
        created_at=datetime.now(timezone.utc)
    )
    iot_service._pending_commands[device_id].append(payload)
    iot_service._commands[cmd_id] = {"command_id": cmd_id, "status": "QUEUED"}

    # 1. ESP32 polls for pending commands
    poll_res = client.get(f"/api/v1/iot/devices/{device_id}/commands/pending", headers=esp32_headers)
    assert poll_res.status_code == 200
    cmds = poll_res.json()
    assert len(cmds) >= 1
    assert any(c["command_id"] == cmd_id for c in cmds)

    # 2. ESP32 acknowledges command execution
    ack_payload = {
        "device_id": device_id,
        "command_id": cmd_id,
        "status": "ACKNOWLEDGED",
        "led_activated": True,
        "buzzer_activated": True
    }
    ack_res = client.post(f"/api/v1/iot/devices/{device_id}/ack", json=ack_payload, headers=esp32_headers)
    assert ack_res.status_code == 200
    ack_data = ack_res.json()
    assert ack_data["status"] == "ACKNOWLEDGED"

    # 3. Idempotency test: Send duplicate ACK -> Should return ALREADY_PROCESSED
    dup_res = client.post(f"/api/v1/iot/devices/{device_id}/ack", json=ack_payload, headers=esp32_headers)
    assert dup_res.status_code == 200
    assert dup_res.json()["status"] == "ALREADY_PROCESSED"


def test_manual_hardware_test_endpoints(client, auth_headers):
    device_id = "ESP32-TEST-MANUAL-01"
    iot_service._init_default_beacon()

    # 1. LED Test
    led_res = client.post(
        f"/api/v1/iot/devices/{device_id}/test",
        json={"action": "LED_TEST", "duration_ms": 1500},
        headers=auth_headers
    )
    assert led_res.status_code == 200
    assert led_res.json()["led"] is True
    assert led_res.json()["buzzer"] is False

    # 2. Buzzer Test
    buzz_res = client.post(
        f"/api/v1/iot/devices/{device_id}/test",
        json={"action": "BUZZER_TEST", "duration_ms": 1000},
        headers=auth_headers
    )
    assert buzz_res.status_code == 200
    assert buzz_res.json()["led"] is False
    assert buzz_res.json()["buzzer"] is True

    # 3. Full Alarm Test
    full_res = client.post(
        f"/api/v1/iot/devices/{device_id}/test",
        json={"action": "FULL_ALARM_TEST", "duration_ms": 2500},
        headers=auth_headers
    )
    assert full_res.status_code == 200
    assert full_res.json()["led"] is True
    assert full_res.json()["buzzer"] is True


def test_device_auth_security(client):
    # Attempt register without auth key -> 401
    res_no_key = client.post("/api/v1/iot/devices/register", json={"device_id": "NO-AUTH"})
    assert res_no_key.status_code == 401

    # Attempt register with wrong key -> 403
    res_wrong_key = client.post(
        "/api/v1/iot/devices/register",
        json={"device_id": "WRONG-KEY"},
        headers={"X-ESP32-Key": "invalid-token"}
    )
    assert res_wrong_key.status_code == 403


def test_ai_alert_succeeds_even_if_esp32_offline(client, auth_headers):
    """
    FAULT TOLERANCE TEST:
    Verifies that AI alert generation remains 100% resilient and successful
    even when the physical ESP32 beacon is offline or disconnected.
    """
    # Force default beacon offline
    for dev in iot_service._devices.values():
        dev["last_seen_at"] = datetime.now(timezone.utc) - timedelta(minutes=10)
        dev["status"] = "OFFLINE"

    alert_payload = {
        "exam_session_id": "ses-offline-test-01",
        "exam_id": "exam-01",
        "student_id": "s-01",
        "camera_id": "cam-01",
        "alert_type": "MOBILE_PHONE",
        "severity": "CRITICAL",
        "confidence": 98,
        "suspicion_score": 95,
        "title": "Severe Infraction: Phone In Hand",
        "description": "Candidate holding phone while beacon is disconnected.",
        "evidence_storage_path": "alert-evidence/offline-test.svg"
    }

    # Posting the alert must succeed without throwing 500 error!
    res = client.post("/api/v1/alerts", json=alert_payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["alert_type"] == "MOBILE_PHONE"
    assert data["severity"] == "CRITICAL"
    assert data["status"] == "OPEN"
