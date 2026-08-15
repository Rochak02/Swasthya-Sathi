// ================================================================
//  LiteWing Drone Demo Firmware — Swasthya Sathi
//  Board: ESP32-S3 (LiteWing V2.5C)
//  Purpose: Connect to WiFi, start HTTP server, spin motors
//           on /spin command from website button press.
//
//  Motor GPIO Pins (from LiteWing V2.5C schematic):
//    Motor 1 (Front-Left):  GPIO 4
//    Motor 2 (Front-Right): GPIO 5
//    Motor 3 (Back-Right):  GPIO 6
//    Motor 4 (Back-Left):   GPIO 7
//
//  ⚠️ SAFETY: SPIN_SPEED is set to 35 (out of 255).
//     At this value, propellers barely rotate — drone will NOT lift off.
//     This is intentional for demo/presentation purposes only.
// ================================================================

#include <WiFi.h>
#include <WebServer.h>

// ── ⚙️  CONFIGURE THESE BEFORE UPLOADING ─────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";      // <-- Change this
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";  // <-- Change this
// ─────────────────────────────────────────────────────────────────

// ── LiteWing V2.5C Motor Pins (ESP32-S3 GPIO) ────────────────────
#define MOTOR_FL  4   // Front-Left
#define MOTOR_FR  5   // Front-Right
#define MOTOR_BR  6   // Back-Right
#define MOTOR_BL  7   // Back-Left

// ── PWM Configuration ─────────────────────────────────────────────
// ESP32-S3 uses the newer ledcAttach API (Arduino Core 3.x)
// If you get errors with ledcAttach, use the older ledcSetup/ledcAttachPin combo
#define PWM_FREQ       5000  // 5 kHz — ideal for brushed DC motors
#define PWM_RESOLUTION 8     // 8-bit = values 0-255

// ── Demo Speed Settings ────────────────────────────────────────────
// Increased to 100 so motors visibly spin. (REMOVE PROPS FIRST!)
#define SPIN_SPEED       100
#define SPIN_DURATION_MS 3000   // Spin for 3 seconds then auto-stop

// ── Web Server on port 80 ─────────────────────────────────────────
WebServer server(80);

// ── LED Pin (built-in on LiteWing ESP32-S3) ───────────────────────
#define LED_PIN 38  // Built-in LED (WS2812 or GPIO38 depending on version)

// ═════════════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\n[DRONE] LiteWing Swasthya Sathi Demo Starting...");

  // ── Initialize Motor PWM ────────────────────────────────────────
  // Using new ESP32 Arduino Core 3.x API
  ledcAttach(MOTOR_FL, PWM_FREQ, PWM_RESOLUTION);
  ledcAttach(MOTOR_FR, PWM_FREQ, PWM_RESOLUTION);
  ledcAttach(MOTOR_BR, PWM_FREQ, PWM_RESOLUTION);
  ledcAttach(MOTOR_BL, PWM_FREQ, PWM_RESOLUTION);

  // Safety: Ensure all motors are OFF at boot
  stopMotors();
  Serial.println("[DRONE] Motors initialized and stopped.");

  // ── Connect to WiFi ─────────────────────────────────────────────
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("[WIFI] Connecting to: ");
  Serial.println(WIFI_SSID);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 30) {
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] ✅ Connected!");
    Serial.print("[WIFI] Drone IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.println("[WIFI] 👆 Copy this IP into the website settings!");
  } else {
    Serial.println("\n[WIFI] ❌ Connection FAILED. Check credentials and retry.");
    // Blink fast to show error
    while (true) {
      delay(200);
    }
  }

  // ── HTTP Routes ─────────────────────────────────────────────────

  // GET / — Health check (browser can confirm drone is online)
  server.on("/", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(200, "application/json",
      "{\"status\":\"online\",\"drone\":\"LiteWing\",\"project\":\"Swasthya Sathi\"}");
  });

  // GET /spin — Triggered by the website's "Test Drone Spin" button
  server.on("/spin", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");  // Allow cross-origin from website
    server.send(200, "application/json",
      "{\"status\":\"spinning\",\"speed\":" + String(SPIN_SPEED) + ",\"duration_ms\":" + String(SPIN_DURATION_MS) + "}");

    Serial.println("[DRONE] 🚁 /spin command received from website!");
    Serial.print("[DRONE] Spinning motors at speed: ");
    Serial.print(SPIN_SPEED);
    Serial.println("/255 for 3 seconds...");

    // Spin motors slowly (demo speed — will NOT fly)
    spinMotors(SPIN_SPEED);
    delay(SPIN_DURATION_MS);
    stopMotors();

    Serial.println("[DRONE] ✅ Spin complete. Motors stopped.");
  });

  // OPTIONS — Handle CORS preflight requests from browser
  server.on("/spin", HTTP_OPTIONS, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.sendHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
    server.sendHeader("Access-Control-Allow-Headers", "*");
    server.send(200, "text/plain", "");
  });

  // GET /status — Returns drone status as JSON
  server.on("/status", HTTP_GET, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    String ip = WiFi.localIP().toString();
    server.send(200, "application/json",
      "{\"status\":\"online\",\"ip\":\"" + ip + "\",\"wifi\":\"" + String(WIFI_SSID) + "\",\"rssi\":" + String(WiFi.RSSI()) + "}");
  });

  server.begin();
  Serial.println("[HTTP] ✅ Web server started on port 80.");
  Serial.println("[HTTP] Test URL: http://" + WiFi.localIP().toString() + "/spin");
  Serial.println("[INFO] Waiting for commands from Swasthya Sathi website...");
}

// ═════════════════════════════════════════════════════════════════
void loop() {
  server.handleClient();
}

// ── Motor Control Functions ───────────────────────────────────────
void spinMotors(int speed) {
  // Write same PWM value to all 4 motors
  ledcWrite(MOTOR_FL, speed);
  ledcWrite(MOTOR_FR, speed);
  ledcWrite(MOTOR_BR, speed);
  ledcWrite(MOTOR_BL, speed);
}

void stopMotors() {
  ledcWrite(MOTOR_FL, 0);
  ledcWrite(MOTOR_FR, 0);
  ledcWrite(MOTOR_BR, 0);
  ledcWrite(MOTOR_BL, 0);
}
