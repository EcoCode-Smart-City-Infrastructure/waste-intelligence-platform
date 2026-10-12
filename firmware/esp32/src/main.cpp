#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>

#include "sensors/ultrasonic_sensor.h"
#include "connectivity/mqtt_client.h"

namespace {
// Wi-Fi credentials come from build flags (-DWIFI_SSID=... -DWIFI_PASSWORD=...);
// the defaults below are for local bench testing only and must be overridden
// for any real deployment.
#ifndef WIFI_SSID
#define WIFI_SSID "WASTE_MESH_WIFI"
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "changeme"
#endif
constexpr const char* kWifiSsid = WIFI_SSID;
constexpr const char* kWifiPassword = WIFI_PASSWORD;
constexpr uint32_t SENSOR_INTERVAL_MS = 30000;
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);

  WiFi.begin(kWifiSsid, kWifiPassword);
  Serial.println("Connecting to WiFi...");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");

  // Sensor initialization and MQTT setup
  initUltrasonicSensor();
  mqttClientBegin();
}

void loop() {
  static uint32_t lastReadMs = 0;
  uint32_t now = millis();

  if (now - lastReadMs >= SENSOR_INTERVAL_MS) {
    lastReadMs = now;

    float fillLevel = readFillLevelPercent();
    float massKg = readMassKg();

    StaticJsonDocument<256> payload;
    payload["sensor_id"] = "esp32-bin-001";
    payload["fill_level_percent"] = fillLevel;
    payload["mass_kg"] = massKg;
    payload["timestamp"] = millis();

    String jsonString;
    serializeJson(payload, jsonString);
    publishTelemetry(jsonString);
  }

  mqttLoop();
  delay(100);
}
