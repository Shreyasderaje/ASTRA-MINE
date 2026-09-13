/* ==========================================================================
 *  ASTRA-MINE  -  ESP32 Rover Controller Firmware  ("the reflexes")
 *  Team SUDARSHAN | SPPN Space Research Team
 * ==========================================================================
 *
 * Role of this board
 * ------------------
 * The Raspberry Pi 5 is the "brain" (AI, planning, dashboard). This ESP32 is
 * the low-level real-time controller: it receives velocity commands over USB
 * serial and handles motors, encoders, the IMU, battery telemetry and the
 * collection servo at a fixed 50 Hz loop - something Linux cannot do
 * reliably.
 *
 * Protocol (115200 baud, one JSON object per line, newline-terminated):
 *
 *   PC -> ESP32:   {"cmd":"vel","v":0.10,"w":0.30}     linear m/s, omega rad/s
 *                  {"cmd":"collect","ms":12000}        run scoop for N ms
 *                  {"cmd":"scoop","pwm":1500}          raw servo pulse (us)
 *                  {"cmd":"reset"}                     zero the odometry
 *                  {"cmd":"stop"}                      immediate stop
 *   ESP32 -> PC:   {"t":12.4,"x":0.512,"y":0.833,"h":1.21,"v":0.10,
 *                   "vbat":11.82,"cur":0.842,"wh":3.12,"tilt":4.2,
 *                   "enc":4821,"scoop":0}
 *                  every 100 ms
 *
 *   wh  = energy drawn from the battery since boot / since last reset (Wh),
 *         integrated by this firmware from INA219 readings - this is the
 *         measurement behind the project's headline metric (g/Wh).
 *
 * Failsafes
 *   - if no velocity command arrives for 600 ms the rover stops
 *   - tilt beyond 35 degrees stops the motors (tipped over / steep slope)
 *
 * Libraries (Arduino Library Manager):
 *   ESP32Servo            (Kevin Harrington)
 *   Adafruit INA219       (power monitor)
 *   Adafruit VL53L0X      (ToF obstacle sensor, optional but recommended)
 *   (MPU-6050 is accessed with raw Wire reads - no library needed)
 *
 * --------------------------------------------------------------------------
 *  PIN MAP  (also documented in docs/03-ASSEMBLY-AND-WIRING.md)
 * --------------------------------------------------------------------------
 *  TB6612FNG motor driver (recommended)      L298N alternative in comments
 *    AIN1  GPIO 13   (left motors dir)         IN1
 *    AIN2  GPIO 12                                 IN2
 *    PWMA  GPIO 14  (PWM left)                 ENA
 *    BIN1  GPIO 27   (right motors dir)        IN3
 *    BIN2  GPIO 26                                 IN4
 *    PWMB  GPIO 25  (PWM right)                ENB
 *    STBY  GPIO 33  (tie 3V3 if unused)
 *  Encoders (magnetic or optical, 1 per side)
 *    ENC_L GPIO 34  (input only)
 *    ENC_R GPIO 35  (input only)
 *  MPU-6050 IMU      I2C: SDA GPIO 21, SCL GPIO 22, AD0 -> GND (0x68)
 *  INA219            I2C (shared bus, 0x40), Vin+ in series with battery +
 *  VL53L0X ToF       I2C (shared bus, 0x29), forward-facing, reports "dist"
 *  Scoop servo       GPIO 32 (SG90/MG996R, power from 5V BEC, common GND!)
 *  Power:  2S/3S Li-ion -> TB6612 VM; buck 5V -> ESP32 5V pin + servo rail;
 *          Pi 5 powered by its own 5V/5A buck or official PSU.
 * ========================================================================== */

#include <Wire.h>
#include <ESP32Servo.h>
#include <Adafruit_INA219.h>
#include <Adafruit_VL53L0X.h>

/* ----------------------------- pin definitions --------------------------- */
#define PIN_AIN1 13
#define PIN_AIN2 12
#define PIN_PWMA 14
#define PIN_BIN1 27
#define PIN_BIN2 26
#define PIN_PWMB 25
#define PIN_STBY 33
#define PIN_ENC_L 34
#define PIN_ENC_R 35
#define PIN_SDA 21
#define PIN_SCL 22
#define PIN_SERVO 32

/* ----------------------------- rover constants --------------------------- */
const float WHEEL_RADIUS_M   = 0.033f;   // 65 mm wheels
const float WHEEL_BASE_M     = 0.18f;    // left-right wheel distance
const float ENC_TICKS_PER_REV = 20.0f;   // encoder disc holes * 2 channels
const float MAX_SPEED_MPS    = 0.12f;
const float MAX_OMEGA        = 1.6f;
const float TILT_LIMIT_DEG   = 35.0f;

/* ----------------------------- runtime state ----------------------------- */
volatile long encL = 0, encR = 0;
float pos_x = 0, pos_y = 0, heading = 0;    // odometry (metres, radians)
float cmd_v = 0, cmd_w = 0;                 // commanded velocities
unsigned long last_cmd_ms = 0;
unsigned long scoop_until = 0;
bool scooping = false;
bool tripped = false;                       // tilt / failsafe lockout

Servo scoop;
Adafruit_INA219 ina219;
Adafruit_VL53L0X tof;
bool tof_ok = false;
float tof_dist_cm = -1.0f;                  // -1 = no valid reading
bool bump = false;                          // stalled: commanded motion, no wheel motion
float stall_s = 0.0f;

/* --------------------------- encoder ISRs (IRAM) -------------------------- */
void IRAM_ATTR isrL() { encL++; }
void IRAM_ATTR isrR() { encR++; }

/* ------------------------------- motor layer ------------------------------ */
// differential drive: v in m/s, w in rad/s -> left/right wheel speeds
void driveMotors(float v, float w) {
  if (tripped) { v = 0; w = 0; }
  float vl = v - w * WHEEL_BASE_M / 2.0f;
  float vr = v + w * WHEEL_BASE_M / 2.0f;
  // convert to PWM duty (-255..255)
  int pl = (int)(vl / MAX_SPEED_MPS * 255.0f);
  int pr = (int)(vr / MAX_SPEED_MPS * 255.0f);
  pl = constrain(pl, -255, 255);
  pr = constrain(pr, -255, 255);

  digitalWrite(PIN_AIN1, pl >= 0 ? HIGH : LOW);
  digitalWrite(PIN_AIN2, pl >= 0 ? LOW  : HIGH);
  ledcWrite(0, abs(pl));                    // channel 0 = PWMA
  digitalWrite(PIN_BIN1, pr >= 0 ? HIGH : LOW);
  digitalWrite(PIN_BIN2, pr >= 0 ? LOW  : HIGH);
  ledcWrite(1, abs(pr));                    // channel 1 = PWMB
}

/* ------------------------------ MPU-6050 raw ------------------------------ */
float gyro_z_bias = 0;
int16_t read16(uint8_t reg) {
  Wire.beginTransmission(0x68);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(0x68, 2);
  return (int16_t)((Wire.read() << 8) | Wire.read());
}
void mpuInit() {
  Wire.beginTransmission(0x68);
  Wire.write(0x6B); Wire.write(0);      // wake up
  Wire.endTransmission();
  delay(100);
  float bias = 0;
  for (int i = 0; i < 200; i++) {       // stationary gyro bias calibration
    bias += read16(0x47);
    delay(3);
  }
  gyro_z_bias = bias / 200.0f;
}
float mpuTiltDeg() {                     // accel roll estimate (pitch about y)
  float ax = read16(0x3B), ay = read16(0x3D), az = read16(0x3F);
  float pitch = atan2(-ax, sqrt(ay * ay + az * az)) * 57.2958f;
  return fabs(pitch);
}

/* ------------------------------ line parser ------------------------------- */
// A tiny fixed-protocol parser: finds "key":value pairs in a JSON object.
float jGet(const String &line, const char *key, float defv = 0.0f) {
  int k = line.indexOf(String("\"") + key + "\"");
  if (k < 0) return defv;
  int colon = line.indexOf(':', k);
  if (colon < 0) return defv;
  return line.substring(colon + 1).toFloat();
}
String jStr(const String &line, const char *key) {
  int k = line.indexOf(String("\"") + key + "\"");
  if (k < 0) return "";
  int q1 = line.indexOf('"', line.indexOf(':', k) + 1);
  int q2 = line.indexOf('"', q1 + 1);
  if (q1 < 0 || q2 < 0) return "";
  return line.substring(q1 + 1, q2);
}

/* --------------------------------- setup ---------------------------------- */
void setup() {
  Serial.begin(115200);

  pinMode(PIN_AIN1, OUTPUT); pinMode(PIN_AIN2, OUTPUT);
  pinMode(PIN_BIN1, OUTPUT); pinMode(PIN_BIN2, OUTPUT);
  pinMode(PIN_STBY, OUTPUT); digitalWrite(PIN_STBY, HIGH);
  ledcSetup(0, 20000, 8); ledcAttachPin(PIN_PWMA, 0);   // 20 kHz, 8-bit
  ledcSetup(1, 20000, 8); ledcAttachPin(PIN_PWMB, 1);
  driveMotors(0, 0);

  pinMode(PIN_ENC_L, INPUT_PULLUP);
  pinMode(PIN_ENC_R, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_L), isrL, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_R), isrR, CHANGE);

  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  mpuInit();
  ina219.begin();
  tof_ok = tof.begin();                   // VL53L0X on the shared I2C bus
  scoop.attach(PIN_SERVO, 600, 2400);
  scoop.writeMicroseconds(1500);          // scoop neutral

  Serial.println("{\"boot\":\"astra-mine-esp32\",\"fw\":1.1}");
}

/* ---------------------------------- loop ---------------------------------- */
unsigned long last_loop_us = 0, last_telemetry = 0;
float energy_wh = 0;

void loop() {
  unsigned long now_ms = millis();
  unsigned long now_us = micros();
  float dt = (now_us - last_loop_us) / 1e6f;
  last_loop_us = now_us;

  /* 1. parse any incoming commands */
  while (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (!line.length()) continue;
    String cmd = jStr(line, "cmd");
    if (cmd == "vel") {
      cmd_v = constrain(jGet(line, "v"), -MAX_SPEED_MPS, MAX_SPEED_MPS);
      cmd_w = constrain(jGet(line, "w"), -MAX_OMEGA, MAX_OMEGA);
      last_cmd_ms = now_ms;
    } else if (cmd == "collect") {
      scoop_until = now_ms + (unsigned long)jGet(line, "ms", 0);
      scooping = true;
      scoop.writeMicroseconds(600);       // drive scoop down/rotate
    } else if (cmd == "scoop") {
      scoop.writeMicroseconds((int)jGet(line, "pwm", 1500));
    } else if (cmd == "reset") {
      pos_x = pos_y = heading = 0;
      energy_wh = 0;
    } else if (cmd == "stop") {
      cmd_v = cmd_w = 0; scooping = false;
      scoop.writeMicroseconds(1500);
      last_cmd_ms = now_ms;
    }
  }

  /* 2. failsafes: command watchdog + tilt protection */
  if (now_ms - last_cmd_ms > 600 && cmd_v != 0) cmd_v = cmd_w = 0;
  float tilt = mpuTiltDeg();
  if (tilt > TILT_LIMIT_DEG) { cmd_v = cmd_w = 0; tripped = true; }

  /* 3. 50 Hz control + odometry */
  static unsigned long ctrl_ms = 0;
  if (now_ms - ctrl_ms >= 20) {
    ctrl_ms = now_ms;
    driveMotors(cmd_v, cmd_w);
    if (scooping && now_ms > scoop_until) {
      scooping = false;
      scoop.writeMicroseconds(1500);      // scoop back to neutral
    }

    /* odometry: dL/dR wheel arcs -> differential drive pose update */
    static long prevL = 0, prevR = 0;
    long dL = encL - prevL, dR = encR - prevR;
    prevL = encL; prevR = encR;
    float dl = dL / ENC_TICKS_PER_REV * 2.0f * PI * WHEEL_RADIUS_M;
    float dr = dR / ENC_TICKS_PER_REV * 2.0f * PI * WHEEL_RADIUS_M;
    float dc = (dl + dr) / 2.0f;
    float dtheta = (dr - dl) / WHEEL_BASE_M;
    // fuse gyro (gyro_z in deg/s, register 0x47 raw scaled 1/65.5)
    float gz = (read16(0x47) - gyro_z_bias) / 65.5f / 57.2958f;   // rad/s
    dtheta = 0.6f * dtheta + 0.4f * (gz * 0.02f);                 // complementary
    heading += dtheta;
    pos_x += dc * cosf(heading);
    pos_y += dc * sinf(heading);

    /* stall ("bump") detection: motors commanded but wheels not turning */
    if (fabs(cmd_v) > 0.02f && fabs(dc) < 0.0005f) {
      stall_s += 0.02f;
      if (stall_s > 0.6f) bump = true;    // pushed against a rock for 0.6 s
    } else {
      stall_s = 0.0f;
      bump = false;
    }
  }

  /* 3b. ToF distance every 60 ms (front obstacle range, centimetres) */
  static unsigned long tof_ms = 0;
  if (tof_ok && now_ms - tof_ms >= 60) {
    tof_ms = now_ms;
    VL53L0X_RangingMeasurementData_t m;
    tof.rangingTest(&m, false);
    tof_dist_cm = (m.RangeStatus == 0) ? m.RangeMilliMeter / 10.0f : -1.0f;
  }

  /* 4. energy integration (INA219, every loop is fine) */
  float bus_v = ina219.getBusVoltage_V() + ina219.getShuntVoltage_mV() / 1000.0f;
  float cur_a = ina219.getCurrent_mA() / 1000.0f;
  energy_wh += bus_v * cur_a * (dt / 3600.0f);

  /* 5. telemetry every 100 ms */
  if (now_ms - last_telemetry >= 100) {
    last_telemetry = now_ms;
    Serial.printf("{\"t\":%.1f,\"x\":%.3f,\"y\":%.3f,\"h\":%.2f,"
                  "\"v\":%.3f,\"vbat\":%.2f,\"cur\":%.3f,\"wh\":%.4f,"
                  "\"tilt\":%.1f,\"enc\":%ld,\"scoop\":%d,"
                  "\"dist\":%.1f,\"bump\":%d}\n",
                  now_ms / 1000.0f, pos_x, pos_y, heading, cmd_v,
                  bus_v, cur_a, energy_wh, tilt, encL, scooping ? 1 : 0,
                  tof_dist_cm, bump ? 1 : 0);
  }
}
