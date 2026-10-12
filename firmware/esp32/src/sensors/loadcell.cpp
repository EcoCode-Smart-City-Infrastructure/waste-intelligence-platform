#include "loadcell.h"

// HX711 pinout
const int HX711_DT_PIN = 32;
const int HX711_SCK_PIN = 33;

// Calibration constants
const float CALIBRATION_FACTOR = 2280.0f;  // Adjust per sensor
const float TARE_WEIGHT = 0.0f;

void initLoadCell() {
  pinMode(HX711_DT_PIN, INPUT);
  pinMode(HX711_SCK_PIN, OUTPUT);
  digitalWrite(HX711_SCK_PIN, LOW);
}

// Read the raw 24-bit value from the HX711 (gain 128, channel A).
// Returns 0 on data-ready timeout.
static long readHx711Raw() {
  // Wait for the chip to signal data ready (DT goes low).
  unsigned long start = millis();
  while (digitalRead(HX711_DT_PIN) == HIGH) {
    if (millis() - start > 1000) {
      return 0;
    }
  }

  long value = 0;
  noInterrupts();
  for (int i = 0; i < 24; i++) {
    digitalWrite(HX711_SCK_PIN, HIGH);
    delayMicroseconds(1);
    value = (value << 1) | digitalRead(HX711_DT_PIN);
    digitalWrite(HX711_SCK_PIN, LOW);
    delayMicroseconds(1);
  }
  // One extra clock pulse sets gain 128 for the next read.
  digitalWrite(HX711_SCK_PIN, HIGH);
  delayMicroseconds(1);
  digitalWrite(HX711_SCK_PIN, LOW);
  interrupts();

  // Sign-extend the 24-bit two's complement value.
  if (value & 0x800000) {
    value |= 0xFF000000;
  }
  return value;
}

float readMassKg() {
  long raw = readHx711Raw();
  float massKg = ((float)raw / CALIBRATION_FACTOR) - TARE_WEIGHT;
  if (massKg < 0.0f) {
    massKg = 0.0f;
  }
  return massKg;
}

float getTareWeight() {
  return TARE_WEIGHT;
}

float getCalibrationFactor() {
  return CALIBRATION_FACTOR;
}
