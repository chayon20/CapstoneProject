/*
  ESP32 + RS485 NPK (Modbus) + DHT22 + Capacitive Soil Moisture + pH
  -> POSTS JSON to Flask: http://<SERVER_HOST>:<SERVER_PORT>/api/ingest

  Arduino Libraries:
    - ModbusMaster by Doc Walker
    - DHT sensor library by Adafruit (+ Adafruit Unified Sensor)
    - ESP32 core's WiFi.h and HTTPClient.h
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ModbusMaster.h>
#include <DHT.h>

// ======================= USER CONFIG =======================
const char* WIFI_SSID     = "Pixel";
const char* WIFI_PASSWORD = "12341234";

// Your PC (running Flask) LAN IP. Example: 192.168.1.42
const char* SERVER_HOST   = "10.231.48.1";
const uint16_t SERVER_PORT = 8000;
const char* INGEST_PATH   = "/api/ingest";

// ======================= HARDWARE PINS ======================
#define MAX485_EN   25     // RE&DE tied to this
#define RXD2        16     // RS485: UART2 RX
#define TXD2        17     // RS485: UART2 TX

#define DHTPIN      4
#define DHTTYPE     DHT22

#define SOIL_PIN    34     // Capacitive moisture (ADC1)
#define PH_PIN      35     // pH analog (ADC1)

// ======================= GLOBALS ============================
ModbusMaster node;
DHT dht(DHTPIN, DHTTYPE);

// Moisture calibration (tweak to your probe)
int AIR_VALUE   = 3000;    // raw in air
int WATER_VALUE = 1200;    // raw fully wet

// pH conversion (linear; do 2‑point calibration)
const float PH_VREF  = 3.3f;   // ESP32 ADC full-scale ~3.3V
const int   PH_BITS  = 4095;   // 12-bit ADC
float PH_SLOPE  = -4.90f;
float PH_OFFSET = 15.00f;

// ======================= HELPERS ============================
void rs485PreTx()  { digitalWrite(MAX485_EN, HIGH); }
void rs485PostTx() { digitalWrite(MAX485_EN, LOW); }

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setHostname("esp32-npk");
  Serial.printf("Connecting to WiFi SSID: %s\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(400);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi connected!");
    Serial.print("ESP32 IP: "); Serial.println(WiFi.localIP());
    Serial.print("RSSI: "); Serial.println(WiFi.RSSI());
  } else {
    Serial.println("WiFi connection FAILED.");
  }
}

uint16_t readSoilRaw(uint8_t samples = 12, uint16_t delayMs = 4) {
  uint32_t acc = 0;
  for (uint8_t i = 0; i < samples; i++) {
    acc += analogRead(SOIL_PIN);
    delay(delayMs);
  }
  return (uint16_t)(acc / samples);
}

int soilPercentFromRaw(uint16_t raw) {
  if (AIR_VALUE == WATER_VALUE) return 0;
  float pct = 100.0f * ((float)AIR_VALUE - (float)raw) / ((float)AIR_VALUE - (float)WATER_VALUE);
  if (pct < 0)   pct = 0;
  if (pct > 100) pct = 100;
  return (int)(pct + 0.5f);
}

float readPhVoltage(uint8_t samples = 10, uint16_t delayMs = 30) {
  int buf[10];
  if (samples > 10) samples = 10;

  for (uint8_t i = 0; i < samples; i++) {
    buf[i] = analogRead(PH_PIN);
    delay(delayMs);
  }

  // sort ascending (tiny bubble-sort, ok for N<=10)
  for (uint8_t i = 0; i < samples - 1; i++) {
    for (uint8_t j = i + 1; j < samples; j++) {
      if (buf[i] > buf[j]) { int t = buf[i]; buf[i] = buf[j]; buf[j] = t; }
    }
  }

  // drop 2 low & 2 high if we have >=6 samples
  uint8_t start = (samples >= 6) ? 2 : 0;
  uint8_t end   = (samples >= 6) ? (samples - 2) : samples;

  uint32_t acc = 0;
  for (uint8_t i = start; i < end; i++) acc += buf[i];
  float avgCounts = (float)acc / (float)(end - start);

  return avgCounts * PH_VREF / (float)PH_BITS; // volts
}

String buildUrl(const char* host, uint16_t port, const char* path) {
  String url = "http://";
  url += host;
  url += ":";
  url += String(port);
  url += path;
  return url;
}

// ======================= SETUP =============================
void setup() {
  Serial.begin(115200);
  delay(300);

  // RS485 enable pin
  pinMode(MAX485_EN, OUTPUT);
  digitalWrite(MAX485_EN, LOW); // listen

  // UART2 for Modbus @ 9600 8N1
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);
  node.begin(1, Serial2); // slave id 1
  node.preTransmission(rs485PreTx);
  node.postTransmission(rs485PostTx);

  // Sensors
  dht.begin();
  analogSetPinAttenuation(SOIL_PIN, ADC_11db);
  analogSetPinAttenuation(PH_PIN,   ADC_11db);

  // WiFi
  connectWiFi();

  Serial.println(F("Setup complete. Will POST readings to /api/ingest every 5s."));
}

// ======================= LOOP ==============================
unsigned long lastPost = 0;
const unsigned long PERIOD_MS = 5000;

void loop() {
  if (millis() - lastPost < PERIOD_MS) {
    delay(50);
    return;
  }
  lastPost = millis();

  // Reconnect WiFi if needed
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi dropped, reconnecting...");
    connectWiFi();
    if (WiFi.status() != WL_CONNECTED) return;
  }

  // 1) Read NPK over Modbus (3 holding registers from 0x001E)
  uint16_t N=0, P=0, K=0;
  uint8_t mb = node.readHoldingRegisters(0x001E, 3);
  if (mb == node.ku8MBSuccess) {
    N = node.getResponseBuffer(0);
    P = node.getResponseBuffer(1);
    K = node.getResponseBuffer(2);
  } else {
    Serial.printf("Modbus error: %u (timeout=226)\n", mb);
  }

  // 2) DHT22
  float h = dht.readHumidity();
  float t = dht.readTemperature(); // °C

  // 3) Soil moisture
  uint16_t soilRaw = readSoilRaw();
  int soilPct = soilPercentFromRaw(soilRaw);

  // 4) pH
  float phVolt = readPhVoltage();
  float pH     = PH_SLOPE * phVolt + PH_OFFSET;

  // Log locally
  Serial.println(F("-------------------------------------------------"));
  Serial.printf("NPK   : N=%u P=%u K=%u (mg/kg)\n", N, P, K);
  Serial.printf("DHT22 : T=%.1f°C  RH=%.1f%%\n", t, h);
  Serial.printf("Soil  : raw=%u  moisture=%d%%\n", soilRaw, soilPct);
  Serial.printf("pH    : V=%.3f -> pH=%.2f\n", phVolt, pH);

  // 5) POST to Flask
  HTTPClient http;
  String url = buildUrl(SERVER_HOST, SERVER_PORT, INGEST_PATH);
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.setConnectTimeout(4000); // ms
  http.setTimeout(5000);        // ms

  // Minimal JSON (no external libs)
  String json = "{";
  json += "\"nitrogen\":"   + String(N) + ",";
  json += "\"phosphorus\":" + String(P) + ",";
  json += "\"potassium\":"  + String(K) + ",";
  json += "\"moisture\":"   + String(soilPct) + ",";
  json += "\"temperature\":" + String(isnan(t) ? 0.0 : t, 2) + ",";
  json += "\"humidity\":"    + String(isnan(h) ? 0.0 : h, 2) + ",";
  json += "\"ph\":"          + String(pH, 2);
  json += "}";

  Serial.printf("POST %s\n", url.c_str());
  int code = http.POST(json);
  if (code > 0) {
    String resp = http.getString();
    Serial.printf("HTTP %d | resp: %s\n", code, resp.c_str());
  } else {
    Serial.printf("HTTP POST failed: %s (%d)\n", http.errorToString(code).c_str(), code);
  }
  http.end();
}
