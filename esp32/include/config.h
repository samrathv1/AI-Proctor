/**
 * AI-Proctor: Smart Examination Surveillance System
 * ESP32 Hardware Beacon Configuration Header
 * 
 * Configures GPIO pins, network endpoints, authentication keys, and timing intervals.
 */

#ifndef CONFIG_H
#define CONFIG_H

// ==============================================================================
// 1. HARDWARE PIN DEFINITIONS (CONFIGURABLE)
// ==============================================================================
#ifndef LED_PIN
#define LED_PIN 27           // EDU-ROBO Onboard LED-1 (GPIO 27)
#endif

#ifndef BUZZER_PIN
#define BUZZER_PIN 15        // EDU-ROBO Onboard 5V Buzzer (GPIO 15)
#endif

#ifndef BUZZER_PWM_CHANNEL
#define BUZZER_PWM_CHANNEL 0
#endif

#ifndef BUZZER_PWM_FREQ
#define BUZZER_PWM_FREQ 2700 // 2.7 kHz resonant audio frequency
#endif

#ifndef BUZZER_PWM_RES
#define BUZZER_PWM_RES 8     // 8-bit PWM resolution (0-255)
#endif

// ==============================================================================
// 2. WI-FI & NETWORK PARAMETERS
// ==============================================================================
// Default credentials - override via compiler flags or serial provisioning in production
#ifndef WIFI_SSID
#define WIFI_SSID "Galaxy A07 5G 4892"
#endif

#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "JayshreeRam"
#endif

// FastAPI Backend URL Endpoint (Default local development IP)
#ifndef BACKEND_BASE_URL
#define BACKEND_BASE_URL "http://10.173.104.11:8000/api/v1/iot"
#endif

// ==============================================================================
// 3. DEVICE IDENTIFICATION & HARDWARE SECURITY
// ==============================================================================
#ifndef DEVICE_ID
#define DEVICE_ID "ESP32-HALL304-01"
#endif

#ifndef DEVICE_NAME
#define DEVICE_NAME "Hall 304 Main Alert Beacon"
#endif

#ifndef DEVICE_LOCATION
#define DEVICE_LOCATION "Hall 304 - Engineering Wing B"
#endif

#ifndef FIRMWARE_VERSION
#define FIRMWARE_VERSION "1.0.0"
#endif

// Hardware Authentication Token sent in X-ESP32-Key header
#ifndef DEVICE_API_KEY
#define DEVICE_API_KEY "esp32-beacon-token"
#endif

// ==============================================================================
// 4. TIMING & PROTOCOL CONFIGURATION
// ==============================================================================
#define HEARTBEAT_INTERVAL_MS 10000 // 10 seconds between heartbeats
#define POLL_INTERVAL_MS      1000  // 1 second command polling interval
#define DEDUPLICATION_CACHE   32    // Ring buffer capacity for recently executed command IDs

#endif // CONFIG_H
