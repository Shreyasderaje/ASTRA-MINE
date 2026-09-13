/* ==========================================================================
 *  ASTRA-MINE  -  Processing Station Node  (optional, highly recommended)
 *  Team SUDARSHAN | SPPN Space Research Team
 * ==========================================================================
 *
 * Role of this board
 * ------------------
 * A second ESP32 sits at the processing station with an HX711 + load cell
 * under the collection bin. It weighs what the rover delivers and streams
 * the reading to the laptop/Pi over its own USB serial link - this is the
 * MEASURED number behind the headline metric (grams delivered per Wh),
 * instead of an estimate from the scoop timing.
 *
 * Protocol (115200 baud, one JSON object per line):
 *   PC -> STATION:  {"cmd":"tare"}           zero the scale (empty bin)
 *   STATION -> PC:  {"g":123.4}              grams in the bin, every 200 ms
 *
 * Libraries (Arduino Library Manager):
 *   HX711 (Bogdan Necula / bogde)
 *
 * Wiring:
 *   HX711 VCC -> 3V3, GND -> GND, DT -> GPIO 16, SCK -> GPIO 4
 *   Load cell: red E+, black E-, white A+, green A-  (check your cell!)
 *
 * Calibration:
 *   1. Upload, open Serial Monitor, tare with an empty bin.
 *   2. Place a known mass (e.g. a 100 g calibration weight) on the bin.
 *   3. Divide the raw reading by the true grams -> CALIBRATION_FACTOR.
 *      Repeat until readings match within ~2 g.
 * ========================================================================== */

#include "HX711.h"

#define PIN_DT  16
#define PIN_SCK 4

const float CALIBRATION_FACTOR = 420.0f;   // raw units per gram - CALIBRATE!
const float REPORT_INTERVAL_MS = 200.0f;

HX711 scale;
unsigned long last_report = 0;
float grams = 0.0f;

float jGet(const String &line, const char *key, float defv = 0.0f) {
  int k = line.indexOf(String("\"") + key + "\"");
  if (k < 0) return defv;
  int colon = line.indexOf(':', k);
  if (colon < 0) return defv;
  return line.substring(colon + 1).toFloat();
}

void tare() {
  scale.tare(10);                           // average 10 samples, zero
  grams = 0.0f;
  Serial.println("{\"tare\":\"ok\"}");
}

void setup() {
  Serial.begin(115200);
  scale.begin(PIN_DT, PIN_SCK);
  /* wait for the HX711 to come up (max 3 s) */
  for (int i = 0; i < 30 && !scale.is_ready(); i++) delay(100);
  scale.set_scale(CALIBRATION_FACTOR);
  tare();
  Serial.println("{\"boot\":\"astra-mine-station\",\"fw\":1.0}");
}

void loop() {
  /* commands */
  while (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() && line.indexOf("tare") >= 0) tare();
  }

  /* weigh continuously (HX711 is slow: ~10 samples/s) */
  if (scale.is_ready()) {
    float raw = scale.get_units(1);         // already divided by scale factor
    grams = 0.85f * grams + 0.15f * raw;    // light smoothing
  }

  /* report every 200 ms */
  if (millis() - last_report >= REPORT_INTERVAL_MS) {
    last_report = millis();
    Serial.printf("{\"g\":%.1f}\n", max(0.0f, grams));
  }
}
