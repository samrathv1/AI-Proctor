# AI-Proctor: ESP32 Hardware Alert Beacon Integration

This directory contains the production-ready C++ firmware for the **AI-Proctor Physical Examination Alert Beacon** based on the Espressif **ESP32 Dev Module (WROOM-32)**.

---

## 1. Hardware Architecture & Pinout

The beacon connects to the AI-Proctor FastAPI backend via 802.11 b/g/n Wi-Fi and provides physical alerting in examination halls whenever high-severity cheating events are detected.

### Wiring Diagram

```
                 +-----------------------+
                 |    ESP32 DEV MODULE   |
                 |                       |
                 |  [GPIO 2]             |
                 |     │                 |
                 |     ▼                 |
                 |  [ 330Ω ]             |
                 |     │                 |
                 |     ▼                 |
                 |   (LED) Red/Blue      |
                 |     │                 |
                 |    GND                |
                 |                       |
                 |  [GPIO 4]             |
                 |     │                 |
                 |     ▼                 |
                 |  [ 1kΩ ]              |
                 |     │                 |
                 |     ▼                 |
                 |  [Base of 2N2222 NPN] |
                 |     │                 |
                 |  Collector ──[BUZZER]── +5V (VIN)
                 |     │
                 |  Emitter ── GND
                 +-----------------------+
```

### Configurable Pin Assignments

| Component | Default GPIO Pin | Function | Configuration Macro (`include/config.h`) |
| :--- | :--- | :--- | :--- |
| **High-Luminance Alert LED** | `GPIO 2` | Visual strobe alert / connection status | `LED_PIN` |
| **Resonant Audio Buzzer** | `GPIO 4` | Audible alarm burst (2.7 kHz resonant) | `BUZZER_PIN` |
| **Status Indicator** | `GPIO 2` | Fast blink during Wi-Fi connection | Built-in |

*Note: Pins are fully configurable in [`include/config.h`](include/config.h) without modifying the core state machine.*

---

## 2. Communication Protocol & Security

### Why HTTP REST Was Selected
1. **Zero External Broker Dependency**: Eliminates the overhead, maintenance, and failure modes of managing a separate MQTT broker (e.g. Mosquitto) on institutional networks.
2. **NAT / Firewall Resilience**: Works over standard HTTP ports (80/8000) allowed by university firewalls, with both push and pull polling (`/commands/pending`).
3. **Native FastAPI Integration**: Directly participates in the authenticated API contracts, Pydantic validation, and Supabase database logging.

### Security Guarantees
- **Hardware Token Authentication**: All communication requires the `X-ESP32-Key` security token.
- **Privacy Enforcement**: The ESP32 receives **ZERO** student biometric embeddings, photos, or student identities. It receives only actuator instructions (`command_id`, `severity`, `pattern`, `duration_ms`).
- **Idempotency Guarantee**: Maintains a ring buffer of the last 32 `command_id`s. Duplicate network requests return `ALREADY_PROCESSED` without double-sounding the buzzer.

---

## 3. Flash & Build Instructions

### Option A: Using PlatformIO (Recommended)
1. Install [PlatformIO Core](https://platformio.org/) or the PlatformIO VS Code extension.
2. Connect the ESP32 via Micro-USB / USB-C.
3. Verify board port in `platformio.ini` (e.g. `upload_port = COMx` on Windows or `/dev/ttyUSBx` on Linux).
4. Build and upload:
   ```bash
   cd esp32
   pio run --target upload
   ```
5. Monitor serial output at 115200 baud:
   ```bash
   pio device monitor -b 115200
   ```

### Option B: Using Arduino IDE
1. Install the **esp32 by Espressif Systems** board package in Arduino IDE Boards Manager.
2. Install **ArduinoJson** (version 6.21.x) via Library Manager.
3. Select Board: **ESP32 Dev Module**.
4. Set Upload Speed: `921600`, Flash Frequency: `80MHz`.
5. Open `esp32/src/main.cpp`, ensure `include/config.h` is in the include path, and click **Upload**.

---

## 4. REST Endpoints Handled by Firmware

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/iot/devices/register` | Registers device on boot with IP and capabilities. |
| `POST` | `/api/v1/iot/devices/heartbeat` | Periodic alive telemetry (10s interval) updating `last_seen_at`. |
| `GET` | `/api/v1/iot/devices/{id}/commands/pending` | Retrieves queued actuation commands. |
| `POST` | `/api/v1/iot/devices/{id}/ack` | Reports execution status (`ACKNOWLEDGED` or `ALREADY_PROCESSED`). |
