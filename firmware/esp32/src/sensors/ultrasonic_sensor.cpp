#include "ultrasonic_sensor.h"

// HC-SR04 pinout (adjust to match wiring harness)
const int ULTRASONIC_TRIG_PIN = 25;
const int ULTRASONIC_ECHO_PIN = 26;

// Inside depth of the bin in centimeters, used to convert distance to fill %.
const float BIN_DEPTH_CM = 100.0f;

void initUltrasonicSensor() {
  pinMode(ULTRASONIC_TRIG_PIN, OUTPUT);
  pinMode(ULTRASONIC_ECHO_PIN, INPUT);
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
}

// Raw distance from sensor to waste surface in centimeters; -1 on echo timeout.
static float readDistanceCm() {
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ULTRASONIC_ECHO_PIN, HIGH, 30000);
  if (duration == 0) {
    return -1.0f;
  }
  return (float)duration * 0.0343f / 2.0f;
}

float readFillLevelPercent() {
  float distanceCm = readDistanceCm();
  if (distanceCm < 0.0f) {
    Serial.println("[ultrasonic] echo timeout, reporting 0% fill");
    return 0.0f;
  }
  float fill = (1.0f - distanceCm / BIN_DEPTH_CM) * 100.0f;
  if (fill < 0.0f) fill = 0.0f;
  if (fill > 100.0f) fill = 100.0f;
  return fill;
}
