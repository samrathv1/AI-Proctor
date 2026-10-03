from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from backend.app.models.requests import (
    IoTCommandRequest,
    IoTHeartbeatRequest,
    IoTDeviceRegisterRequest,
    IoTCommandAckRequest,
    IoTManualTestRequest
)
from backend.app.models.responses import (
    IoTCommandResponse,
    IoTDeviceStatusResponse,
    IoTDeviceRegisterResponse,
    IoTCommandAckResponse,
    IoTCommandPayload
)
from backend.app.services.iot_service import iot_service
from backend.app.core.security import verify_api_key, verify_esp32_key

router = APIRouter(prefix="/iot", tags=["ESP32 Hardware"])


# ==============================================================================
# 1. HARDWARE REGISTRATION & HEARTBEAT
# ==============================================================================

@router.post("/devices/register", response_model=IoTDeviceRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_iot_device(
    request: IoTDeviceRegisterRequest,
    _: str = Depends(verify_esp32_key)
):
    """
    Registers an ESP32 hardware device on boot or network reconnection.
    Authenticated via dedicated hardware token header (X-ESP32-Key).
    """
    return await iot_service.register_device(request)


@router.post("/heartbeat", status_code=status.HTTP_200_OK)
@router.post("/devices/heartbeat", status_code=status.HTTP_200_OK)
async def device_heartbeat(
    request: IoTHeartbeatRequest,
    _: str = Depends(verify_esp32_key)
):
    """
    Receive telemetry and alive pings directly from ESP32 microcontrollers.
    Authenticated via dedicated hardware token header (X-ESP32-Key).
    Updates last_seen_at without duplicate database insertion.
    """
    success = await iot_service.register_heartbeat(request)
    return {"status": "acknowledged", "updated": success}


# ==============================================================================
# 2. DEVICE INVENTORY & HEALTH TELEMETRY
# ==============================================================================

@router.get("/devices", response_model=List[IoTDeviceStatusResponse])
async def list_iot_devices(_: str = Depends(verify_api_key)):
    """
    Retrieve telemetry and connection states of ESP32 examination hall beacons.
    Dynamically reports ONLINE / OFFLINE based on heartbeat timeout tolerance.
    """
    return await iot_service.list_devices()


@router.get("/devices/{device_id}", response_model=IoTDeviceStatusResponse)
async def get_iot_device(
    device_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Retrieve live health status of a specific ESP32 beacon.
    """
    return await iot_service.get_device_status(device_id)


# ==============================================================================
# 3. COMMAND POLLING & EXECUTION ACKNOWLEDGEMENT
# ==============================================================================

@router.get("/devices/{device_id}/commands/pending", response_model=List[IoTCommandPayload])
async def get_pending_commands_for_device(
    device_id: str,
    _: str = Depends(verify_esp32_key)
):
    """
    Endpoint for ESP32 microcontrollers to retrieve pending queued actuation commands.
    """
    return await iot_service.get_pending_commands(device_id)


@router.post("/devices/{device_id}/ack", response_model=IoTCommandAckResponse)
async def acknowledge_device_command(
    device_id: str,
    request: IoTCommandAckRequest,
    _: str = Depends(verify_esp32_key)
):
    """
    ESP32 command execution acknowledgment.
    Guarantees idempotency: returns ALREADY_PROCESSED if duplicate ACK received.
    """
    if request.device_id != device_id:
        request.device_id = device_id
    return await iot_service.acknowledge_command(request)


# ==============================================================================
# 4. MANUAL HARDWARE VERIFICATION & TEST
# ==============================================================================

@router.post("/devices/{device_id}/test", response_model=IoTCommandPayload)
async def execute_hardware_test(
    device_id: str,
    request: IoTManualTestRequest,
    _: str = Depends(verify_api_key)
):
    """
    Manual hardware actuation test without generating fake exam cheating events.
    Actions: LED_TEST | BUZZER_TEST | FULL_ALARM_TEST.
    """
    return await iot_service.execute_manual_test(device_id, request)


@router.post("/command", response_model=IoTCommandResponse)
async def dispatch_hardware_command(
    request: IoTCommandRequest,
    _: str = Depends(verify_api_key)
):
    """
    Dispatch buzzer or multi-color LED commands directly to registered ESP32 units.
    """
    return await iot_service.send_command(request)
