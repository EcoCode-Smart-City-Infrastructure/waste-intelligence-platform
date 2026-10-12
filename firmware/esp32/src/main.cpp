#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>

#include "sensors/ultrasonic_sensor.h"
#include "sensors/loadcell.h"
#include "connectivity/mqtt_client.h"

namespace {
constexpr const char* WIFI_SSID = "WASTE_MESH_WIFI";
constexpr const char* WIFI_PASSWORD = "changeme";
constexpr uint32_t SENSOR_INTERVAL_MS = 30000;
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.println("Connecting to WiFi...");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");

  // Sensor initialization and MQTT setup
  initUltrasonicSensor();
  initLoadCell();
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
