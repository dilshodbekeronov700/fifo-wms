# ESP32 Harorat/Namlik Sensori — O'rnatish

Apparat: **ESP32-S3-DevKitC-1** + **DHT-21 (AM2301)** + **SSD1306 OLED 0.91"**

## 1. Ulanish (simlar)
| Komponent | Pin | ESP32-S3 |
|---|---|---|
| DHT-21 VCC | + | 3V3 |
| DHT-21 GND | − | GND |
| DHT-21 DATA | data | GPIO 4 (+10k pull-up 3V3 ga) |
| OLED VCC | + | 3V3 |
| OLED GND | − | GND |
| OLED SDA | SDA | GPIO 8 |
| OLED SCL | SCL | GPIO 9 |

## 2. Arduino IDE sozlash
1. **Boards Manager** → `esp32` (Espressif) o'rnating
2. Board: **ESP32S3 Dev Module**
3. **Library Manager** → o'rnating:
   - DHT sensor library (Adafruit)
   - Adafruit Unified Sensor
   - Adafruit SSD1306
   - Adafruit GFX Library

## 3. Kodni sozlash (`esp32_dht21.ino`)
```cpp
WIFI_SSID   = "sizning_wifi"
WIFI_PASS   = "parol"
WMS_URL     = "http://192.168.0.105:8000/api/v1/sensors/ingest"   // Mac IP
DEVICE_KEY  = "esp32-gp-001"   // WMS'da sensor yaratganda bergan key
```

## 4. WMS'da sensor yaratish
WMS → **Harorat (IoT)** → "Sensor qo'shish":
- Nom: masalan "Sklad-1 harorat"
- **Device key:** firmware'dagi `DEVICE_KEY` bilan bir xil (`esp32-gp-001`)
- Temp min/max, namlik chegaralari

## 5. Yuklash va test
1. ESP32'ni USB orqali ulang → kodni **Upload**
2. Serial Monitor (115200) → `POST 200: {...}` ko'rinishi kerak
3. OLED'da harorat/namlik + "OK" status
4. WMS → Harorat (IoT) sahifasida jonli qiymat 30s ichida paydo bo'ladi

## Eslatma
- Mac IP o'zgarsa (`ipconfig getifaddr en0`), `WMS_URL` ni yangilang
- Bir nechta sensor: har biriga alohida `DEVICE_KEY` + WMS'da alohida sensor
- Interval: `INTERVAL_MS` (default 30s)
