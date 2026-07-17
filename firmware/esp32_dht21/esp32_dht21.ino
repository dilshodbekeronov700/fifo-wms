/*
 * WMS IoT — Harorat/Namlik sensori
 * Apparat: ESP32-S3-DevKitC-1 + DHT-21 (AM2301) + SSD1306 OLED (0.91", 128x32)
 *
 * Vazifa: DHT-21'dan harorat/namlik o'qish → OLED'da ko'rsatish →
 *         WMS backend'ga HTTP POST yuborish (/api/v1/sensors/ingest).
 *
 * Kutubxonalar (Arduino Library Manager):
 *   - DHT sensor library (Adafruit)
 *   - Adafruit Unified Sensor
 *   - Adafruit SSD1306 + Adafruit GFX
 *
 * Ulanish:
 *   DHT-21 DATA -> GPIO 4   (10k pull-up DATA<->3V3)
 *   OLED SDA    -> GPIO 8   (S3 default I2C SDA)
 *   OLED SCL    -> GPIO 9   (S3 default I2C SCL)
 *   Hammasi 3V3 + GND
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>

// ─── SOZLAMALAR (o'zgartiring) ──────────────────────────────────────────────
const char* WIFI_SSID     = "Perfectum 2.4G";
const char* WIFI_PASS     = "12345678";
const char* WMS_URL       = "http://192.168.0.105:8000/api/v1/sensors/ingest";
const char* DEVICE_KEY    = "esp32-gp-001";   // WMS'da sensor yaratganda kiritilgan key
const unsigned long INTERVAL_MS = 30000;       // 30 soniyada bir yuborish
const bool TEST_MODE = false;                  // production: faqat real DHT qiymati yuboriladi

// ─── Pinlar ─────────────────────────────────────────────────────────────────
#define DHTPIN   4
#define DHTTYPE  DHT21
#define SDA_PIN  8
#define SCL_PIN  9
#define OLED_W   128
#define OLED_H   32
#define OLED_ADDR 0x3C

DHT dht(DHTPIN, DHTTYPE);
Adafruit_SSD1306 display(OLED_W, OLED_H, &Wire, -1);

unsigned long lastSend = 0;

void showOled(float t, float h, const char* status) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("WMS Sensor");
  display.setCursor(80, 0);
  display.print(status);
  display.setTextSize(2);
  display.setCursor(0, 14);
  if (isnan(t)) display.print("--");
  else { display.print(t, 1); display.print((char)247); display.print("C"); }
  display.setTextSize(1);
  display.setCursor(90, 20);
  if (!isnan(h)) { display.print(h, 0); display.print("%"); }
  display.display();
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries++ < 40) {
    delay(250);
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);
  dht.begin();
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("OLED topilmadi");
  }
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.print("Ulanmoqda...");
  display.display();
  connectWifi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();

  float t = dht.readTemperature();
  float h = dht.readHumidity();

  // ── Diagnostika: har siklda holatni Serial'ga chiqaramiz ──
  bool wifiOk = (WiFi.status() == WL_CONNECTED);
  Serial.printf("[diag] WiFi=%s IP=%s | DHT t=%.1f h=%.1f %s\n",
                wifiOk ? "OK" : "NO",
                wifiOk ? WiFi.localIP().toString().c_str() : "-",
                t, h,
                (isnan(t) || isnan(h)) ? "(DHT o'qilmadi — sim/pull-up tekshiring)" : "");

  // TEST rejimi: DHT o'qilmasa fake qiymat (99.9/99) — tarmoqni tekshirish uchun
  float tSend = isnan(t) ? (TEST_MODE ? 99.9 : t) : t;
  float hSend = isnan(h) ? (TEST_MODE ? 99.0 : h) : h;

  unsigned long now = millis();
  if (now - lastSend >= INTERVAL_MS && !isnan(tSend) && !isnan(hSend)) {
    lastSend = now;
    t = tSend; h = hSend;
    const char* status = "...";
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(WMS_URL);
      http.addHeader("Content-Type", "application/json");
      String body = String("{\"device_key\":\"") + DEVICE_KEY +
                    "\",\"temperature\":" + String(t, 1) +
                    ",\"humidity\":" + String(h, 1) + "}";
      int code = http.POST(body);
      status = (code == 200) ? "OK" : "ERR";
      Serial.printf("POST %d: %s\n", code, body.c_str());
      http.end();
    } else {
      status = "NoWiFi";
    }
    showOled(t, h, status);
  } else {
    showOled(t, h, WiFi.status() == WL_CONNECTED ? "live" : "NoWiFi");
  }
  delay(2000);
}
