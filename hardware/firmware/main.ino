#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>
#include <WebServer.h>
#include <Preferences.h>

// ── Pin Definitions (Seeed Studio XIAO ESP32-C6) ──
// Standard SPI Pins for XIAO ESP32-C6
#define SCK_PIN         19  // D8
#define MISO_PIN        20  // D9
#define MOSI_PIN        18  // D10
#define SS_PIN          17  // D7 (SDA on RC522)
#define RST_PIN         16  // D6

// Indicators
#define BUZZER_PIN      21  // D3
#define LED_GREEN       0   // D0
#define LED_RED         1   // D1
#define LED_BLUE        2   // D2

// ── Setup MFRC522 & Preferences ──
MFRC522 mfrc522(SS_PIN, RST_PIN);
Preferences preferences;
WebServer server(80);

// ── Global Configuration Variables ──
String hubId = "SS-HUB-0001"; // Fallback, normally set via portal
String backendUrl = "http://192.168.1.100:8000";
String wifiSSID = "";
String wifiPass = "";

// ── State Variables ──
bool inConfigMode = false;
unsigned long lastScanTime = 0;
const unsigned long SCAN_COOLDOWN = 3000; // 3 seconds cooldown between scans

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  // Init Pins
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
  
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_RED, LOW);
  digitalWrite(LED_BLUE, HIGH); // Blue indicates booting/connecting
  
  // Init SPI explicitly for XIAO ESP32-C6
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, SS_PIN);
  
  // Init RFID
  mfrc522.PCD_Init();
  Serial.println("\n[INIT] MFRC522 RFID reader initialized");

  // Load Config
  preferences.begin("ss-hub", false);
  wifiSSID = preferences.getString("ssid", "");
  wifiPass = preferences.getString("pass", "");
  hubId = preferences.getString("hubId", "SS-HUB-0001");
  backendUrl = preferences.getString("url", "http://192.168.1.100:8000");

  if (wifiSSID == "") {
    Serial.println("[INIT] No WiFi config found. Starting AP Config Mode.");
    startConfigMode();
  } else {
    Serial.println("[INIT] Connecting to WiFi: " + wifiSSID);
    WiFi.begin(wifiSSID.c_str(), wifiPass.c_str());
    
    int retries = 0;
    while (WiFi.status() != WL_CONNECTED && retries < 20) {
      delay(500);
      Serial.print(".");
      retries++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\n[INIT] WiFi connected! IP: " + WiFi.localIP().toString());
      digitalWrite(LED_BLUE, LOW);
      digitalWrite(LED_GREEN, HIGH);
      delay(1000);
      digitalWrite(LED_GREEN, LOW);
    } else {
      Serial.println("\n[INIT] WiFi connection failed. Starting AP Config Mode.");
      startConfigMode();
    }
  }
}

void loop() {
  if (inConfigMode) {
    server.handleClient();
    // Blink Blue to indicate AP mode
    static unsigned long lastBlink = 0;
    if (millis() - lastBlink > 1000) {
      digitalWrite(LED_BLUE, !digitalRead(LED_BLUE));
      lastBlink = millis();
    }
    return;
  }

  // Ensure WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_BLUE, HIGH);
    return;
  }
  digitalWrite(LED_BLUE, LOW);

  // Look for new RFID cards
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }

  // Select one of the cards
  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  // Cooldown check
  if (millis() - lastScanTime < SCAN_COOLDOWN) {
    mfrc522.PICC_HaltA();
    return;
  }
  lastScanTime = millis();

  // Read UID
  String uidString = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (mfrc522.uid.uidByte[i] < 0x10) uidString += "0";
    uidString += String(mfrc522.uid.uidByte[i], HEX);
    if (i < mfrc522.uid.size - 1) uidString += ":";
  }
  uidString.toUpperCase();
  
  Serial.println("[SCAN] Card detected UID: " + uidString);
  processScan(uidString);

  // Halt PICC
  mfrc522.PICC_HaltA();
}

// ── Process Scan via API ──
void processScan(String uid) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[ERROR] No WiFi connection.");
    errorFeedback();
    return;
  }

  HTTPClient http;
  String url = backendUrl + "/api/rfid/scan";
  http.begin(url);
  http.setTimeout(10000); // Increase timeout to 10 seconds for Firebase operations
  http.addHeader("Content-Type", "application/json");

  // Create JSON payload
  StaticJsonDocument<200> doc;
  doc["hub_id"] = hubId;
  doc["raw_card_uid"] = uid; // Fixed payload key to match FastAPI backend
  
  String requestBody;
  serializeJson(doc, requestBody);
  
  Serial.println("[API] POST " + url);
  Serial.println("[API] Payload: " + requestBody);

  int httpResponseCode = http.POST(requestBody);

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("[API] Response Code: " + String(httpResponseCode));
    Serial.println("[API] Response: " + response);
    
    if (httpResponseCode == 200) {
      successFeedback();
    } else {
      errorFeedback();
    }
  } else {
    Serial.println("[API] Request failed: " + http.errorToString(httpResponseCode));
    errorFeedback();
  }
  http.end();
}

// ── Feedback Functions ──
void successFeedback() {
  digitalWrite(LED_GREEN, HIGH);
  tone(BUZZER_PIN, 2000, 100);
  delay(150);
  tone(BUZZER_PIN, 3000, 150);
  delay(150);
  digitalWrite(LED_GREEN, LOW);
}

void errorFeedback() {
  digitalWrite(LED_RED, HIGH);
  tone(BUZZER_PIN, 500, 300);
  delay(400);
  digitalWrite(LED_RED, LOW);
}

// ── Web Portal Configuration (Captive Portal style) ──
void startConfigMode() {
  inConfigMode = true;
  WiFi.mode(WIFI_AP);
  String apName = "SwasthyaHub_" + hubId;
  WiFi.softAP(apName.c_str(), "admin123");
  
  Serial.println("[AP] Access Point started: " + apName);
  Serial.println("[AP] IP Address: " + WiFi.softAPIP().toString());
  
  server.on("/", HTTP_GET, []() {
    String html = "<html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>Hub Config</title></head>";
    html += "<body style='font-family:sans-serif; padding:20px;'><h2>Swasthya Sathi Hub Config</h2>";
    html += "<form action='/save' method='POST'>";
    html += "WiFi SSID:<br><input type='text' name='ssid' value='" + wifiSSID + "'><br><br>";
    html += "WiFi Password:<br><input type='password' name='pass'><br><br>";
    html += "Hub ID:<br><input type='text' name='hubId' value='" + hubId + "'><br><br>";
    html += "Backend API URL:<br><input type='text' name='url' value='" + backendUrl + "'><br><br>";
    html += "<input type='submit' value='Save & Restart' style='padding:10px 20px; background:#10b981; color:#fff; border:none; border-radius:5px;'>";
    html += "</form></body></html>";
    server.send(200, "text/html", html);
  });
  
  server.on("/save", HTTP_POST, []() {
    String newSsid = server.arg("ssid");
    String newPass = server.arg("pass");
    String newHubId = server.arg("hubId");
    String newUrl = server.arg("url");
    
    preferences.putString("ssid", newSsid);
    preferences.putString("pass", newPass);
    preferences.putString("hubId", newHubId);
    preferences.putString("url", newUrl);
    
    server.send(200, "text/html", "<html><body style='font-family:sans-serif; padding:20px;'><h2>Saved!</h2><p>Restarting hub...</p></body></html>");
    delay(2000);
    ESP.restart();
  });
  
  server.begin();
}
