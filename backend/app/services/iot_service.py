import uuid
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

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
    IoTCommandPayload,
    IoTDeviceRegisterResponse,
    IoTCommandAckResponse
)
from backend.app.integrations.supabase import supabase_db
from backend.app.core.logging import logger
from backend.app.core.config import settings


class IoTService:
    """
    ESP32 IoT Hardware Management & Alert Actuation Service.
    
    RESPONSIBILITIES:
    1. Device Registration & Heartbeat Health Tracking.
    2. Online / Offline state transitions based on heartbeat timeout & tolerance.
    3. Severity-based alert policy (LOW/MED ignored, HIGH/CRITICAL dispatched).
    4. Hardware actuation pattern selection (LED flashing + Buzzer burst).
    5. Alert cooldown & idempotent command delivery (Zero duplicate buzzers).
    6. Non-blocking resilience: AI proctoring continues seamlessly even if hardware is offline.
    7. Command lifecycle: QUEUED -> SENT -> DELIVERED -> ACKNOWLEDGED / ALREADY_PROCESSED.
    """

    def __init__(self, heartbeat_timeout_seconds: int = 30):
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        
        # In-memory device registry
        self._devices: Dict[str, Dict[str, Any]] = {}
        
        # Pending commands per device: {device_id: [IoTCommandPayload]}
        self._pending_commands: Dict[str, List[IoTCommandPayload]] = {}
        
        # Command tracking: {command_id: Dict[str, Any]}
        self._commands: Dict[str, Dict[str, Any]] = {}
        
        # Idempotency acknowledgment cache: set of command_ids
        self._acknowledged_commands: set = set()
        
        # Cooldown tracker: {(device_id, alert_type): last_dispatch_timestamp}
        self._cooldown_tracker: Dict[tuple, float] = {}

        # Initialize default examination hall beacon
        self._init_default_beacon()

    def _init_default_beacon(self):
        default_id = "ESP32-HALL304-01"
        self._devices[default_id] = {
            "id": "00000000-0000-0000-0000-000000000301",
            "device_id": default_id,
            "device_uid": default_id,
            "device_name": "Hall 304 Main Alert Beacon",
            "device_type": "ESP32_ALERT_BEACON",
            "location": "Hall 304 - Engineering Wing B",
            "ip_address": "192.168.1.10",
            "firmware_version": "v2.4.1-ai-proctor",
            "status": "ONLINE",
            "buzzer_status": "READY",
            "led_status": "NORMAL",
            "capabilities": ["LED", "BUZZER"],
            "uptime_seconds": 18420,
            "last_seen_at": datetime.now(timezone.utc),
            "last_command_id": None,
            "last_command_status": None,
        }
        self._pending_commands[default_id] = []

    # ==========================================================================
    # 1. DEVICE REGISTRATION & DISCOVERY
    # ==========================================================================

    async def register_device(self, request: IoTDeviceRegisterRequest) -> IoTDeviceRegisterResponse:
        """
        Registers an ESP32 hardware device on boot or network reconnection.
        """
        device_id = request.device_id
        now = datetime.now(timezone.utc)
        
        device_record = {
            "id": str(uuid.uuid4()),
            "device_id": device_id,
            "device_uid": device_id,
            "device_name": request.device_name,
            "device_type": request.device_type,
            "location": request.location,
            "ip_address": request.ip_address,
            "firmware_version": request.firmware_version,
            "status": "ONLINE",
            "buzzer_status": "READY",
            "led_status": "NORMAL",
            "capabilities": request.capabilities,
            "uptime_seconds": 0,
            "last_seen_at": now,
            "last_command_id": None,
            "last_command_status": None,
        }
        
        self._devices[device_id] = device_record
        if device_id not in self._pending_commands:
            self._pending_commands[device_id] = []

        logger.info(f"Registered ESP32 device '{device_id}' at IP {request.ip_address} (Firmware: {request.firmware_version})")
        return IoTDeviceRegisterResponse(
            device_id=device_id,
            device_name=request.device_name,
            status="ONLINE",
            registered_at=now,
            message="Device successfully registered with AI-Proctor backend."
        )

    # ==========================================================================
    # 2. HEARTBEAT & ONLINE / OFFLINE HEALTH
    # ==========================================================================

    async def register_heartbeat(self, request: IoTHeartbeatRequest) -> bool:
        """
        Updates device last-seen timestamp and online status without creating duplicate rows.
        """
        device_id = request.device_id or request.device_uid or "ESP32-HALL304-01"
        now = datetime.now(timezone.utc)
        
        if device_id in self._devices:
            dev = self._devices[device_id]
            dev["status"] = "ONLINE"
            dev["last_seen_at"] = now
            dev["ip_address"] = request.ip_address
            dev["firmware_version"] = request.firmware_version
            if request.uptime_seconds is not None:
                dev["uptime_seconds"] = request.uptime_seconds
            if request.led_ready is not None:
                dev["led_status"] = "READY" if request.led_ready else "ERROR"
            if request.buzzer_ready is not None:
                dev["buzzer_status"] = "READY" if request.buzzer_ready else "ERROR"
        else:
            # Auto-register newly discovered device
            self._devices[device_id] = {
                "id": str(uuid.uuid4()),
                "device_id": device_id,
                "device_uid": device_id,
                "device_name": f"Beacon-{device_id}",
                "device_type": "ESP32_ALERT_BEACON",
                "location": "Examination Hall",
                "ip_address": request.ip_address,
                "firmware_version": request.firmware_version,
                "status": "ONLINE",
                "buzzer_status": "READY",
                "led_status": "READY",
                "capabilities": ["LED", "BUZZER"],
                "uptime_seconds": request.uptime_seconds or 0,
                "last_seen_at": now,
                "last_command_id": None,
                "last_command_status": None,
            }
            self._pending_commands[device_id] = []

        # Mirror to Supabase if configured
        await supabase_db.update_device_heartbeat(
            device_uid=device_id,
            ip_address=request.ip_address,
            firmware_version=request.firmware_version
        )
        return True

    def _evaluate_device_status(self, device_id: str) -> str:
        """
        Dynamically computes ONLINE / OFFLINE status based on heartbeat timeout tolerance.
        """
        if device_id not in self._devices:
            return "OFFLINE"
        
        dev = self._devices[device_id]
        last_seen = dev.get("last_seen_at")
        if not last_seen:
            dev["status"] = "OFFLINE"
            return "OFFLINE"

        elapsed = (datetime.now(timezone.utc) - last_seen).total_seconds()
        # Small tolerance: allow up to 2 missed intervals (2 * heartbeat_timeout)
        tolerance = self.heartbeat_timeout_seconds * 1.5
        if elapsed > tolerance:
            dev["status"] = "OFFLINE"
            return "OFFLINE"
        
        return dev.get("status", "ONLINE")

    async def get_device_status(self, device_id: str = "ESP32-HALL304-01") -> IoTDeviceStatusResponse:
        """
        Returns full hardware status, including dynamic online/offline detection.
        """
        # Fallback to first available if specific ID not found
        if device_id not in self._devices and len(self._devices) > 0:
            device_id = list(self._devices.keys())[0]

        if device_id in self._devices:
            dev = self._devices[device_id]
            current_status = self._evaluate_device_status(device_id)
            return IoTDeviceStatusResponse(
                id=dev.get("id", str(uuid.uuid4())),
                device_uid=dev.get("device_uid", device_id),
                device_name=dev.get("device_name", "Hall Beacon"),
                location=dev.get("location", "Hall 304"),
                ip_address=dev.get("ip_address", "192.168.1.10"),
                status=current_status,
                buzzer_status=dev.get("buzzer_status", "READY"),
                led_status=dev.get("led_status", "NORMAL"),
                firmware_version=dev.get("firmware_version", "1.0.0"),
                capabilities=dev.get("capabilities", ["LED", "BUZZER"]),
                uptime_seconds=dev.get("uptime_seconds", 0),
                last_seen_at=dev.get("last_seen_at"),
                last_command_id=dev.get("last_command_id"),
                last_command_status=dev.get("last_command_status")
            )
        
        return IoTDeviceStatusResponse(
            id=str(uuid.uuid4()),
            device_uid=device_id,
            device_name=f"Beacon {device_id}",
            location="Hall 304",
            ip_address="0.0.0.0",
            status="OFFLINE",
            buzzer_status="DISABLED",
            led_status="OFF",
            last_seen_at=None
        )

    async def list_devices(self) -> List[IoTDeviceStatusResponse]:
        """Lists all registered IoT devices with current live status."""
        results = []
        for dev_id in list(self._devices.keys()):
            results.append(await self.get_device_status(dev_id))
        return results

    # ==========================================================================
    # 3. ALERT DISPATCH & SEVERITY RULES
    # ==========================================================================

    async def dispatch_alert_for_infraction(
        self,
        alert_data: Dict[str, Any],
        device_id: Optional[str] = None
    ) -> Optional[IoTCommandPayload]:
        """
        Connects AI-Proctor Alert System to Physical ESP32 Hardware.
        
        RULES:
        - LOW / MEDIUM: No physical hardware actuation.
        - HIGH: LED flash (500ms) + short buzzer (3000ms), PULSE pattern.
        - CRITICAL: Rapid LED flash (200ms) + repeating buzzer (5000ms), RAPID pattern.
        - Cooldown: Enforces configured cooldown interval between alarms.
        - Idempotency: Every command is issued with a unique command_id.
        - Fault-Tolerance: If ESP32 is offline, AI alert remains valid; logs hardware unavailable.
        """
        severity = alert_data.get("severity", "LOW").upper()
        alert_type = alert_data.get("alert_type", "GENERAL")
        alert_id = alert_data.get("id") or alert_data.get("alert_id")
        exam_session_id = alert_data.get("exam_session_id")

        # Severity Filter Policy
        if severity not in ["HIGH", "CRITICAL"]:
            logger.debug(f"Alert {alert_id} severity '{severity}' does not meet physical actuation threshold. Skipping ESP32 trigger.")
            return None

        # Resolve target device
        target_device = device_id
        if not target_device or target_device not in self._devices:
            # Pick first registered device
            target_device = list(self._devices.keys())[0] if self._devices else "ESP32-HALL304-01"

        # Cooldown Check
        cooldown_key = (target_device, alert_type)
        now_ts = time.time()
        cooldown_duration = getattr(settings, "ALERT_COOLDOWN_SECONDS", 30)
        
        last_dispatch = self._cooldown_tracker.get(cooldown_key, 0.0)
        if now_ts - last_dispatch < cooldown_duration:
            logger.info(
                f"Alert cooldown active for ({target_device}, {alert_type}). "
                f"Elapsed: {now_ts - last_dispatch:.1f}s < {cooldown_duration}s. Suppressing duplicate physical buzzer."
            )
            return None

        # Update cooldown
        self._cooldown_tracker[cooldown_key] = now_ts

        # Configure hardware pattern based on severity
        if severity == "CRITICAL":
            duration_ms = 5000
            pattern = "RAPID"
        else: # HIGH
            duration_ms = 3000
            pattern = "PULSE"

        command_id = f"cmd-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        payload = IoTCommandPayload(
            command_id=command_id,
            command="ALERT",
            alert_id=alert_id,
            severity=severity,
            led=True,
            buzzer=True,
            duration_ms=duration_ms,
            pattern=pattern,
            created_at=now
        )

        # Check device online status
        device_state = self._evaluate_device_status(target_device)
        cmd_status = "QUEUED" if device_state == "ONLINE" else "FAILED_DEVICE_OFFLINE"

        if device_state != "ONLINE":
            logger.warning(
                f"AI Alert {alert_id} generated HIGH/CRITICAL event, but ESP32 '{target_device}' is {device_state}. "
                f"Hardware actuation unavailable; AI surveillance continues uninterrupted."
            )
        else:
            if target_device not in self._pending_commands:
                self._pending_commands[target_device] = []
            self._pending_commands[target_device].append(payload)
            logger.info(f"Dispatched physical {severity} alert command {command_id} to ESP32 '{target_device}'.")

        # Track command status
        self._commands[command_id] = {
            "command_id": command_id,
            "device_id": target_device,
            "alert_id": alert_id,
            "exam_session_id": exam_session_id,
            "severity": severity,
            "status": cmd_status,
            "created_at": now,
            "payload": payload.model_dump()
        }

        # Update device last command
        if target_device in self._devices:
            self._devices[target_device]["last_command_id"] = command_id
            self._devices[target_device]["last_command_status"] = cmd_status

        # Insert audit record in Supabase
        try:
            await supabase_db.insert_iot_event(
                device_id=target_device,
                event_type="BUZZER_TRIGGER" if severity == "CRITICAL" else "LED_ALARM",
                command=f"ACTIVATE_{severity}_{pattern}",
                status=cmd_status,
                exam_session_id=exam_session_id,
                alert_id=alert_id
            )
        except Exception as e:
            logger.warning(f"Could not persist IoT event to Supabase: {e}")

        return payload

    # ==========================================================================
    # 4. COMMAND ACKNOWLEDGEMENT & IDEMPOTENCY
    # ==========================================================================

    async def acknowledge_command(self, request: IoTCommandAckRequest) -> IoTCommandAckResponse:
        """
        Receives execution acknowledgment from ESP32.
        Idempotent: If duplicate ACK received, returns ALREADY_PROCESSED.
        """
        command_id = request.command_id
        device_id = request.device_id
        now = datetime.now(timezone.utc)

        # Idempotency check
        if command_id in self._acknowledged_commands:
            logger.info(f"ESP32 duplicate ACK received for command {command_id}. Returning ALREADY_PROCESSED.")
            return IoTCommandAckResponse(
                command_id=command_id,
                device_id=device_id,
                status="ALREADY_PROCESSED",
                acknowledged_at=now,
                message="Command was previously processed and acknowledged."
            )

        self._acknowledged_commands.add(command_id)

        # Update command record
        if command_id in self._commands:
            self._commands[command_id]["status"] = "ACKNOWLEDGED"
            self._commands[command_id]["acknowledged_at"] = now
            self._commands[command_id]["led_activated"] = request.led_activated
            self._commands[command_id]["buzzer_activated"] = request.buzzer_activated

        # Update device status
        if device_id in self._devices:
            dev = self._devices[device_id]
            dev["last_command_id"] = command_id
            dev["last_command_status"] = "ACKNOWLEDGED"
            dev["last_seen_at"] = now
            dev["buzzer_status"] = "TRIGGERED" if request.buzzer_activated else "READY"
            dev["led_status"] = "ALERT" if request.led_activated else "NORMAL"

        logger.info(f"Command {command_id} acknowledged by ESP32 '{device_id}' (LED={request.led_activated}, Buzzer={request.buzzer_activated}).")
        return IoTCommandAckResponse(
            command_id=command_id,
            device_id=device_id,
            status="ACKNOWLEDGED",
            acknowledged_at=now,
            message="Command execution confirmed by hardware."
        )

    # ==========================================================================
    # 5. PENDING COMMAND RETRIEVAL (POLLING / CONSUMER)
    # ==========================================================================

    async def get_pending_commands(self, device_id: str) -> List[IoTCommandPayload]:
        """
        Pulls queued commands for an ESP32 microcontroller and marks them DELIVERED.
        """
        if device_id not in self._pending_commands:
            return []
        
        commands = list(self._pending_commands[device_id])
        self._pending_commands[device_id].clear()
        
        for cmd in commands:
            if cmd.command_id in self._commands:
                self._commands[cmd.command_id]["status"] = "DELIVERED"
        
        return commands

    # ==========================================================================
    # 6. MANUAL HARDWARE TEST
    # ==========================================================================

    async def execute_manual_test(
        self,
        device_id: str,
        request: IoTManualTestRequest
    ) -> IoTCommandPayload:
        """
        Manual test dispatch for hardware verification without creating fake exam cheating events.
        Actions: LED_TEST | BUZZER_TEST | FULL_ALARM_TEST
        """
        if device_id not in self._devices:
            self._init_default_beacon()
            device_id = "ESP32-HALL304-01"

        command_id = f"test-{uuid.uuid4().hex[:10]}"
        action = request.action.upper()
        duration_ms = request.duration_ms or 3000

        if action in ["LED_TEST", "TEST_LED_ALERT"]:
            led = True
            buzzer = False
            pattern = "SINGLE"
            cmd_action = "TEST_LED_ALERT"
        elif action in ["BUZZER_TEST", "TEST_BUZZER"]:
            led = False
            buzzer = True
            pattern = "SINGLE"
            cmd_action = "TEST_BUZZER"
            duration_ms = 300
        else: # FULL_ALARM_TEST
            led = True
            buzzer = True
            pattern = "RAPID"
            cmd_action = "TEST"

        now = datetime.now(timezone.utc)
        payload = IoTCommandPayload(
            command_id=command_id,
            command=cmd_action,
            alert_id=None,
            severity="TEST",
            led=led,
            buzzer=buzzer,
            duration_ms=duration_ms,
            pattern=pattern,
            created_at=now
        )

        if device_id not in self._pending_commands:
            self._pending_commands[device_id] = []
        self._pending_commands[device_id].append(payload)

        self._commands[command_id] = {
            "command_id": command_id,
            "device_id": device_id,
            "alert_id": None,
            "status": "QUEUED",
            "created_at": now,
            "payload": payload.model_dump()
        }

        if device_id in self._devices:
            self._devices[device_id]["last_command_id"] = command_id
            self._devices[device_id]["last_command_status"] = "TEST_DISPATCHED"

        logger.info(f"Manual {action} command {command_id} queued for ESP32 '{device_id}' ({duration_ms}ms).")
        return payload

    # Legacy compatibility method for POST /api/v1/iot/command
    async def send_command(self, request: IoTCommandRequest) -> IoTCommandResponse:
        now = datetime.now(timezone.utc)
        command_id = f"cmd-{uuid.uuid4().hex[:12]}"
        
        payload = IoTCommandPayload(
            command_id=command_id,
            command=request.command,
            alert_id=request.alert_id,
            severity=request.severity or "HIGH",
            led=True,
            buzzer="BUZZER" in request.command or request.command == "ALERT",
            duration_ms=request.duration_ms or 1500,
            pattern=request.pattern or "PULSE",
            created_at=now
        )

        device_id = request.device_id
        if device_id not in self._pending_commands:
            self._pending_commands[device_id] = []
        self._pending_commands[device_id].append(payload)

        event = await supabase_db.insert_iot_event(
            device_id=request.device_id,
            event_type=request.command if request.command in [
                "HEARTBEAT", "BUZZER_TRIGGER", "LED_WARNING", "LED_ALARM", "DEVICE_CONNECTED", "DEVICE_DISCONNECTED"
            ] else "BUZZER_TRIGGER",
            command=f"EXECUTE_{request.command}",
            status="QUEUED",
            exam_session_id=request.exam_session_id,
            alert_id=request.alert_id,
        )

        return IoTCommandResponse(
            event_id=event.get("id", str(uuid.uuid4())),
            device_id=request.device_id,
            command=request.command,
            status="QUEUED",
            timestamp=now,
            command_payload=payload
        )


iot_service = IoTService()
