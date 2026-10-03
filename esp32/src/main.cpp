/**
 * AI-Proctor: Smart Examination Surveillance System
 * ESP32 Hardware Beacon Firmware
 * 
 * Hardware: ESP32 Dev Module (WROOM-32)
 * Actuators:
 *   - High-luminance Alert LED (Configurable GPIO, default GPIO 2)
 *   - Resonant Piezoelectric Audio Buzzer (Configurable GPIO, default GPIO 4)
 * 
 * Communication:
 *   - Wi-Fi 802.11 b/g/n (WPA2)
 *   - HTTP REST over FastAPI backend
 *   - Device Authentication: X-ESP32-Key header
 *   - Idempotent Command Processing with Ring-Buffer Deduplication
 *   - Non-blocking state machine actuation
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "config.h"

// ==============================================================================
// GLOBAL STATE & TIMERS
// ==============================================================================
unsigned long lastHeartbeatTime = 0;
unsigned long lastPollTime = 0;
unsigned long bootTime = 0;

// Alarm Actuation State Machine
struct AlarmState {
    bool active;
    String commandId;
    String severity;
    String pattern;
    unsigned long startTime;
    unsigned long durationMs;
    unsigned long lastToggleTime;
    bool ledState;
    bool buzzerState;
} currentAlarm = {false, "", "", "", 0, 0, 0, false, false};

// Ring-Buffer for Idempotent Command Deduplication
String executedCommandIds[DEDUPLICATION_CACHE];
int deduplicationIndex = 0;

// ==============================================================================
// FORWARD DECLARATIONS
// ==============================================================================
void connectWiFi();
void registerDevice();
void sendHeartbeat();
void pollPendingCommands();
void processCommand(JsonObject cmd);
void sendAcknowledgment(const String& cmdId, const String& status, bool ledAct, bool buzzAct);
void updateAlarmActuation();
void startAlarm(const String& cmdId, const String& severity, const String& pattern, unsigned long durationMs, bool useLed, bool useBuzz);
void stopAlarm();
bool isCommandAlreadyProcessed(const String& cmdId);
void recordCommandProcessed(const String& cmdId);

// ==============================================================================
// SETUP & INITIALIZATION
// ==============================================================================
void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n=======================================================");
    Serial.println("  AI-PROCTOR: ESP32 ALERT BEACON FIRMWARE v1.0.0       ");
    Serial.println("=======================================================");
    Serial.printf("Configured LED Pin:    GPIO %d\n", LED_PIN);
    Serial.printf("Configured Buzzer Pin: GPIO %d\n", BUZZER_PIN);
    Serial.printf("Device Identifier:     %s\n", DEVICE_ID);

    // Initialize Actuator GPIOs
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);

    // Disable L293D Motor Driver EN (GPIO 22)
    pinMode(22, OUTPUT);
    digitalWrite(22, LOW);

    // Initialize Deduplication Cache
    for (int i = 0; i < DEDUPLICATION_CACHE; i++) {
        executedCommandIds[i] = "";
    }

    // Connect to Examination Hall Network
    connectWiFi();

    // Register with AI-Proctor Backend
    registerDevice();

    bootTime = millis();
    Serial.println("[BOOT] ESP32 Ready. Entering event & actuation loop.\n");
}

// ==============================================================================
// MAIN NON-BLOCKING EVENT LOOP
// ==============================================================================
void loop() {
    // 1. Maintain Wi-Fi Connectivity
    if (WiFi.status() != WL_CONNECTED) {
        connectWiFi();
    }

    unsigned long currentMillis = millis();

    // 2. Periodic Alive Heartbeat
    if (currentMillis - lastHeartbeatTime >= HEARTBEAT_INTERVAL_MS) {
        lastHeartbeatTime = currentMillis;
        sendHeartbeat();
    }

    // 3. Periodic Command Polling
    if (currentMillis - lastPollTime >= POLL_INTERVAL_MS) {
        lastPollTime = currentMillis;
        pollPendingCommands();
    }

    // 4. Update Alarm Actuation (Non-blocking LED & Buzzer pulsing)
    updateAlarmActuation();

    delay(10); // Minimal yield for RTOS task scheduler
}

// ==============================================================================
// WI-FI CONNECTION MANAGEMENT
// ==============================================================================
void connectWiFi() {
    if (WiFi.status() == WL_CONNECTED) return;

    Serial.printf("[WIFI] Connecting to SSID: %s ...\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        // Quick blink LED during connection phase
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
        attempts++;
    }

    digitalWrite(LED_PIN, LOW);

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n[WIFI] Connected Successfully!");
        Serial.printf("[WIFI] Assigned IP: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("[WIFI] Signal Strength (RSSI): %d dBm\n", WiFi.RSSI());
    } else {
        Serial.println("\n[WIFI] Connection timed out. Will retry in loop.");
    }
}

// ==============================================================================
// DEVICE REGISTRATION
// ==============================================================================
void registerDevice() {
    if (WiFi.status() != WL_CONNECTED) return;

    HTTPClient http;
    String url = String(BACKEND_BASE_URL) + "/devices/register";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-ESP32-Key", DEVICE_API_KEY);

    StaticJsonDocument<512> doc;
    doc["device_id"] = DEVICE_ID;
    doc["device_name"] = DEVICE_NAME;
    doc["device_type"] = "ESP32_ALERT_BEACON";
    doc["firmware_version"] = FIRMWARE_VERSION;
    doc["ip_address"] = WiFi.localIP().toString();
    doc["mac_address"] = WiFi.macAddress();
    doc["location"] = DEVICE_LOCATION;
    JsonArray caps = doc.createNestedArray("capabilities");
    caps.add("LED");
    caps.add("BUZZER");

    String requestBody;
    serializeJson(doc, requestBody);

    Serial.printf("[HTTP] POST %s\n", url.c_str());
    int httpResponseCode = http.POST(requestBody);

    if (httpResponseCode == 201 || httpResponseCode == 200) {
        Serial.printf("[REG] Successfully registered with backend (HTTP %d).\n", httpResponseCode);
    } else {
        Serial.printf("[REG] Registration failed (HTTP %d). Response: %s\n", httpResponseCode, http.getString().c_str());
    }
    http.end();
}

// ==============================================================================
// HEARTBEAT TELEMETRY
// ==============================================================================
void sendHeartbeat() {
    if (WiFi.status() != WL_CONNECTED) return;

    HTTPClient http;
    String url = String(BACKEND_BASE_URL) + "/devices/heartbeat";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-ESP32-Key", DEVICE_API_KEY);

    StaticJsonDocument<256> doc;
    doc["device_id"] = DEVICE_ID;
    doc["firmware_version"] = FIRMWARE_VERSION;
    doc["ip_address"] = WiFi.localIP().toString();
    doc["uptime_seconds"] = (millis() - bootTime) / 1000;
    doc["led_ready"] = true;
    doc["buzzer_ready"] = true;
    doc["rssi"] = WiFi.RSSI();

    String requestBody;
    serializeJson(doc, requestBody);

    int httpResponseCode = http.POST(requestBody);
    if (httpResponseCode == 200) {
        // Heartbeat acknowledged
    } else {
        Serial.printf("[HEARTBEAT] Warning: backend returned HTTP %d\n", httpResponseCode);
    }
    http.end();
}

// ==============================================================================
// COMMAND POLLING & EXECUTION
// ==============================================================================
void pollPendingCommands() {
    if (WiFi.status() != WL_CONNECTED) return;

    HTTPClient http;
    String url = String(BACKEND_BASE_URL) + "/devices/" + String(DEVICE_ID) + "/commands/pending";

    http.begin(url);
    http.addHeader("X-ESP32-Key", DEVICE_API_KEY);

    int httpResponseCode = http.GET();
    if (httpResponseCode == 200) {
        String payload = http.getString();
        if (payload.length() > 5 && payload != "[]") {
            DynamicJsonDocument doc(2048);
            DeserializationError error = deserializeJson(doc, payload);
            if (!error && doc.is<JsonArray>()) {
                JsonArray commands = doc.as<JsonArray>();
                for (JsonObject cmd : commands) {
                    processCommand(cmd);
                }
            }
        }
    }
    http.end();
}

// ==============================================================================
// COMMAND PROCESSING & IDEMPOTENCY
// ==============================================================================
void processCommand(JsonObject cmd) {
    String cmdId = cmd["command_id"].as<String>();
    String action = cmd["command"].as<String>();
    String severity = cmd["severity"].as<String>();
    String pattern = cmd["pattern"] | "PULSE";
    unsigned long durationMs = cmd["duration_ms"] | 3000;
    bool useLed = cmd["led"] | true;
    bool useBuzz = cmd["buzzer"] | true;

    Serial.printf("\n[CMD] Received Command: ID=%s, Action=%s, Severity=%s, Duration=%lums\n",
        cmdId.c_str(), action.c_str(), severity.c_str(), durationMs);

    // Idempotency Check
    if (isCommandAlreadyProcessed(cmdId)) {
        Serial.printf("[CMD] Duplicate command %s ignored. Returning ALREADY_PROCESSED.\n", cmdId.c_str());
        sendAcknowledgment(cmdId, "ALREADY_PROCESSED", false, false);
        return;
    }

    // Record as processed
    recordCommandProcessed(cmdId);

    // Dedicated Safe Hardware Verification: TEST_BUZZER
    if (action == "TEST_BUZZER" || action == "BUZZER_TEST") {
        Serial.println("[TEST_BUZZER] Starting safe buzzer test");
        digitalWrite(27, LOW);
        digitalWrite(14, LOW);
        digitalWrite(12, LOW);
        digitalWrite(13, LOW);

        digitalWrite(BUZZER_PIN, HIGH);
        Serial.println("[TEST_BUZZER] GPIO 15 HIGH");
        Serial.println("[TEST_BUZZER] Buzzer active for 300ms");
        delay(300);
        digitalWrite(BUZZER_PIN, LOW);
        Serial.println("[TEST_BUZZER] GPIO 15 LOW");
        Serial.println("[TEST_BUZZER] Buzzer OFF");

        sendAcknowledgment(cmdId, "ACKNOWLEDGED", false, true);
        return;
    }

    // Dedicated Safe Hardware Verification: TEST_LED_ALERT
    if (action == "TEST_LED_ALERT" || action == "LED_TEST") {
        Serial.println("[TEST_LED_ALERT] >>> EXECUTING TEST_LED_ALERT <<<");
        digitalWrite(BUZZER_PIN, LOW);
        Serial.println("[TEST_LED_ALERT] Buzzer GPIO 15 kept LOW");

        // DIAGNOSTIC SEQUENCE
        pinMode(22, OUTPUT);
        digitalWrite(22, LOW);
        Serial.println("[LED DIAGNOSTIC] L293D EN GPIO22 = LOW");

        pinMode(27, OUTPUT);
        pinMode(14, OUTPUT);
        pinMode(12, OUTPUT);
        pinMode(13, OUTPUT);

        digitalWrite(27, LOW);
        digitalWrite(14, LOW);
        digitalWrite(12, LOW);
        digitalWrite(13, LOW);

        // PHASE 1: Drive all 4 LEDs HIGH for 3 seconds
        digitalWrite(27, HIGH);
        Serial.println("[LED DIAGNOSTIC] LED1 GPIO27 = HIGH");
        digitalWrite(14, HIGH);
        Serial.println("[LED DIAGNOSTIC] LED2 GPIO14 = HIGH");
        digitalWrite(12, HIGH);
        Serial.println("[LED DIAGNOSTIC] LED3 GPIO12 = HIGH");
        digitalWrite(13, HIGH);
        Serial.println("[LED DIAGNOSTIC] LED4 GPIO13 = HIGH");
        Serial.println("[LED DIAGNOSTIC] All LEDs HIGH for 3 seconds");

        delay(3000);

        digitalWrite(27, LOW);
        digitalWrite(14, LOW);
        digitalWrite(12, LOW);
        digitalWrite(13, LOW);
        Serial.println("[LED DIAGNOSTIC] All LEDs LOW");
        Serial.println("[LED DIAGNOSTIC] Complete");

        sendAcknowledgment(cmdId, "ACKNOWLEDGED", true, false);
        return;
    }

    // Trigger Physical Actuation
    startAlarm(cmdId, severity, pattern, durationMs, useLed, useBuzz);

    // Send Immediate Acknowledgment to Backend
    sendAcknowledgment(cmdId, "ACKNOWLEDGED", useLed, useBuzz);
}

// ==============================================================================
// COMMAND ACKNOWLEDGEMENT
// ==============================================================================
void sendAcknowledgment(const String& cmdId, const String& status, bool ledAct, bool buzzAct) {
    if (WiFi.status() != WL_CONNECTED) return;

    HTTPClient http;
    String url = String(BACKEND_BASE_URL) + "/devices/" + String(DEVICE_ID) + "/ack";

    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-ESP32-Key", DEVICE_API_KEY);

    StaticJsonDocument<256> doc;
    doc["device_id"] = DEVICE_ID;
    doc["command_id"] = cmdId;
    doc["status"] = status;
    doc["led_activated"] = ledAct;
    doc["buzzer_activated"] = buzzAct;

    String requestBody;
    serializeJson(doc, requestBody);

    int httpResponseCode = http.POST(requestBody);
    Serial.printf("[ACK] Sent execution ACK for %s (Status: %s, HTTP %d)\n", cmdId.c_str(), status.c_str(), httpResponseCode);
    http.end();
}

// ==============================================================================
// HARDWARE ACTUATION STATE MACHINE (NON-BLOCKING)
// ==============================================================================
void startAlarm(const String& cmdId, const String& severity, const String& pattern, unsigned long durationMs, bool useLed, bool useBuzz) {
    currentAlarm.active = true;
    currentAlarm.commandId = cmdId;
    currentAlarm.severity = severity;
    currentAlarm.pattern = pattern;
    currentAlarm.startTime = millis();
    currentAlarm.durationMs = durationMs;
    currentAlarm.lastToggleTime = millis();
    currentAlarm.ledState = useLed;
    currentAlarm.buzzerState = useBuzz;

    // Immediately enable initial state
    digitalWrite(LED_PIN, currentAlarm.ledState ? HIGH : LOW);
    digitalWrite(BUZZER_PIN, currentAlarm.buzzerState ? HIGH : LOW);

    Serial.printf("[ACTUATOR] Alarm ACTIVE: Pattern=%s, Duration=%lums\n", pattern.c_str(), durationMs);
}

void updateAlarmActuation() {
    if (!currentAlarm.active) return;

    unsigned long now = millis();

    // Check if alarm duration has elapsed
    if (now - currentAlarm.startTime >= currentAlarm.durationMs) {
        stopAlarm();
        return;
    }

    // Determine toggle interval based on pattern
    unsigned long toggleInterval = 500; // Default PULSE: 500ms on / 500ms off
    if (currentAlarm.pattern == "RAPID") {
        toggleInterval = 200; // RAPID: 200ms on / 200ms off
    } else if (currentAlarm.pattern == "SINGLE") {
        toggleInterval = currentAlarm.durationMs; // Solid on
    }

    // Toggle states for flashing/beeping
    if (now - currentAlarm.lastToggleTime >= toggleInterval) {
        currentAlarm.lastToggleTime = now;
        currentAlarm.ledState = !currentAlarm.ledState;
        currentAlarm.buzzerState = !currentAlarm.buzzerState;

        digitalWrite(LED_PIN, currentAlarm.ledState ? HIGH : LOW);
        digitalWrite(BUZZER_PIN, currentAlarm.buzzerState ? HIGH : LOW);
    }
}

void stopAlarm() {
    currentAlarm.active = false;
    digitalWrite(LED_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);
    Serial.printf("[ACTUATOR] Alarm %s completed. Hardware reset to idle.\n", currentAlarm.commandId.c_str());
}

// ==============================================================================
// IDEMPOTENCY CACHE UTILITIES
// ==============================================================================
bool isCommandAlreadyProcessed(const String& cmdId) {
    for (int i = 0; i < DEDUPLICATION_CACHE; i++) {
        if (executedCommandIds[i] == cmdId) {
            return true;
        }
    }
    return false;
}

void recordCommandProcessed(const String& cmdId) {
    executedCommandIds[deduplicationIndex] = cmdId;
    deduplicationIndex = (deduplicationIndex + 1) % DEDUPLICATION_CACHE;
}
