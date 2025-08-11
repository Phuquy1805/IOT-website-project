#include "header.h"
// #include "mqtt.h"
#include "cam.h"
#include "wifi_setup.h"
#include "servo_setup.h"
#include "lcd_setup.h"
#include "fingerprint_setup.h"

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>

// SoftwareSerial for AS608
SoftwareSerial softSerial(FINGERPRINT_RX, FINGERPRINT_TX);
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&softSerial);

// ----- MQTT objects -----
WiFiClient espClient;
PubSubClient mqttClient(espClient);

static DoorServo door;
static LCD lcd;

// Topics (prefix comes from your build/env: MQTT_TOPIC_PREFIX)
static const char MQTT_TOPIC_LCD_COMMAND[] PROGMEM = "/" MQTT_TOPIC_PREFIX "/lcd/command";
static const char MQTT_TOPIC_LCD_LOG[] PROGMEM = "/" MQTT_TOPIC_PREFIX "/lcd/log";
static const char MQTT_TOPIC_SERVO_COMMAND[] PROGMEM = "/" MQTT_TOPIC_PREFIX "/servo/command";
static const char MQTT_TOPIC_SERVO_LOG[] PROGMEM = "/" MQTT_TOPIC_PREFIX "/servo/log";
static const char MQTT_TOPIC_FINGERPRINT_COMMAND[] PROGMEM = "/" MQTT_TOPIC_PREFIX "/fingerprint/command";
static const char MQTT_TOPIC_FINGERPRINT_LOG[] PROGMEM = "/" MQTT_TOPIC_PREFIX "/fingerprint/log";

// ---------- Forward declarations ----------
void mqttConnect();
void callback(char *topic, byte *payload, unsigned int len);
void handleServoCommand(const String &jsonText);
void handleFingerprintCommand(const String &jsonText);
uint8_t getFingerprintEnroll(uint32_t cmd_id);
void checkFingerprintScanner();
void publishFingerprintLog(const char *log_type, const char *description, const char *payload, uint32_t cmd_id);

// ==========================================
// MQTT connect
// ==========================================
void mqttConnect()
{
  while (!mqttClient.connected())
  {
    Serial.print("Attemping MQTT connection...");
    Serial.println(mqttServer);

    String clientId = "ESP32Client-" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str()))
    {
      Serial.println("connected");
      mqttClient.subscribe(MQTT_TOPIC_LCD_COMMAND);
      mqttClient.subscribe(MQTT_TOPIC_SERVO_COMMAND);
      mqttClient.subscribe(MQTT_TOPIC_FINGERPRINT_COMMAND);
    }
    else
    {
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

// ==========================================
// MQTT callback
// ==========================================
void callback(char *topic, byte *payload, unsigned int len)
{
  String msg;
  msg.reserve(len);
  for (unsigned int i = 0; i < len; ++i)
    msg += (char)payload[i];

  Serial.printf("Topic: %s | Payload: %s\n", topic, msg.c_str());

  if (strcmp(topic, MQTT_TOPIC_SERVO_COMMAND) == 0)
  {
    handleServoCommand(msg);
  }
  else if (strcmp(topic, MQTT_TOPIC_FINGERPRINT_COMMAND) == 0)
  {
    handleFingerprintCommand(msg);
  }
  else
  {
    // ignore other topics or add handlers later
  }
}

// ==========================================
// Handle servo command
// ==========================================
void handleServoCommand(const String &jsonText)
{
  /* 1 — parse */
  Serial.println("Handling servo command");
  StaticJsonDocument<128> doc;
  DeserializationError err = deserializeJson(doc, jsonText);
  if (err)
  {
    Serial.printf("Bad JSON in servo command: %s\n", err.c_str());
    return; // silently ignore
  }
  uint32_t cmdId = doc["cmd_id"] | 0;
  String action = doc["action"] | "";

  /* 2 — execute */
  bool ok = true;
  if (action.equalsIgnoreCase("open"))
    door.openDoor();
  else if (action.equalsIgnoreCase("close"))
    door.closeDoor();
  else
    ok = false;

  /* 3 — build & publish log */
  StaticJsonDocument<256> logDoc;
  logDoc["created_at"] = (uint32_t)time(nullptr);
  logDoc["log_type"] = "servo.status";
  logDoc["description"] = ok ? "State changed by Webserver's command." : "invalid command";
  logDoc["payload"] = action;
  logDoc["topic"] = MQTT_TOPIC_SERVO_COMMAND;
  logDoc["command_id"] = cmdId;
  logDoc["related_log_id"] = nullptr;

  String payload;
  serializeJson(logDoc, payload);

  if (!mqttClient.connected())
    Serial.println("[servo] MQTT not connected!");

  bool sent = mqttClient.publish(MQTT_TOPIC_SERVO_LOG, payload.c_str(), true);

  Serial.printf("[servo] Publish %s (%u B) → %s\n",
                MQTT_TOPIC_SERVO_LOG, payload.length(),
                sent ? "OK" : "FAIL");
}

// ==========================================
// Handle fingerprint command (e.g., enroll)
// ==========================================
void handleFingerprintCommand(const String &jsonText)
{
  StaticJsonDocument<128> doc;
  DeserializationError err = deserializeJson(doc, jsonText);
  if (err)
  {
    Serial.printf("Bad JSON in fingerprint command: %s\n", err.c_str());
    return;
  }
  uint32_t cmdId = doc["cmd_id"] | 0;
  String action = doc["action"] | "";

  if (action.equalsIgnoreCase("enroll"))
  {
    Serial.println("Starting fingerprint enrollment process...");
    getFingerprintEnroll(cmdId);
  }

  else if (action.equalsIgnoreCase("delete"))
  {
    int id_to_delete = doc["id"] | -1;
    if (id_to_delete != -1)
    {
      Serial.printf("Starting fingerprint deletion for ID #%d...\n", id_to_delete);
      deleteFingerprint(id_to_delete, cmdId);
    }
  }
}

// ==========================================
// Enroll fingerprint
// Returns new ID or error code
// ==========================================
uint8_t getFingerprintEnroll(uint32_t cmd_id)
{

  // ----- Bước 1: Tìm ID còn trống -----
  int id = 1;
  while (finger.loadModel(id) == FINGERPRINT_OK)
  {
    id++;
    if (id >= FINGERPRINT_CAPACITY) { 
      const char* msg = "Fingerprint database is full.";
      Serial.println(msg);
      publishFingerprintLog("enroll.error", msg, "", cmd_id);
      return FINGERPRINT_PACKETRECIEVEERR;
    }
  }
  // Tại đây, `id` chính là vị trí trống đầu tiên.
  // Các dòng thông báo thành công đã được xóa khỏi đây.

  // ----- Bước 2: Bắt đầu quá trình đăng ký cho ID đã tìm được -----
  Serial.printf("Enrolling for ID #%d\n", id);
  publishFingerprintLog("enroll.progress", "Enrolling. Please place your finger on the scanner.", String(id).c_str(), cmd_id);

  // Chờ lấy ảnh 1
  while (finger.getImage() != FINGERPRINT_OK)
    ;
  if (finger.image2Tz(1) != FINGERPRINT_OK)
  {
    const char *msg = "Failed to capture first image.";
    Serial.println(msg);
    publishFingerprintLog("enroll.error", msg, "", cmd_id);
    return FINGERPRINT_PACKETRECIEVEERR;
  }
  Serial.println("Image 1 taken");
  publishFingerprintLog("enroll.progress", "Image 1 captured. Please remove your finger.", "", cmd_id);

  delay(2000); // Chờ người dùng nhấc tay ra
  while (finger.getImage() != FINGERPRINT_NOFINGER)
    ;

  // Chờ lấy ảnh 2
  Serial.println("Place same finger again");
  publishFingerprintLog("enroll.progress", "Please place the same finger again.", "", cmd_id);

  while (finger.getImage() != FINGERPRINT_OK)
    ;
  if (finger.image2Tz(2) != FINGERPRINT_OK)
  {
    const char *msg = "Failed to capture second image.";
    Serial.println(msg);
    publishFingerprintLog("enroll.error", msg, "", cmd_id);
    return FINGERPRINT_PACKETRECIEVEERR;
  }
  Serial.println("Image 2 taken");

  // ----- Bước 3: Tạo model và lưu vào bộ nhớ -----
  if (finger.createModel() != FINGERPRINT_OK)
  {
    const char *msg = "Failed to create model.";
    Serial.println(msg);
    publishFingerprintLog("enroll.error", msg, "", cmd_id);
    return FINGERPRINT_PACKETRECIEVEERR;
  }

  if (finger.storeModel(id) != FINGERPRINT_OK)
  {
    const char *msg = "Failed to store model.";
    Serial.println(msg);
    publishFingerprintLog("enroll.error", msg, "", cmd_id);
    return FINGERPRINT_PACKETRECIEVEERR;
  }

  // ----- Bước 4: Thông báo thành công (CHỈ THỰC HIỆN MỘT LẦN DUY NHẤT) -----
  Serial.printf("ID %d stored!\n", id);
  // Tạo payload JSON để gửi đi
  String success_payload = "{\"id\":" + String(id) + "}";
  publishFingerprintLog("enroll.success", "Successfully enrolled new fingerprint.", success_payload.c_str(), cmd_id);

  return id; // Trả về ID vừa đăng ký thành công
}

// // ==========================================
// // Poll fingerprint sensor & publish search result
// // ==========================================
void checkFingerprintScanner()
{
  if (finger.getImage() != FINGERPRINT_OK)
  {
    return; // no finger
  }
  if (finger.image2Tz() != FINGERPRINT_OK)
  {
    Serial.println("Error capturing image for search");
    publishFingerprintLog("match.error", "Failed converting image to characteristics.", "", 0);
    return;
  }
  if (finger.fingerSearch() != FINGERPRINT_OK)
  {
    Serial.println("Finger not found");
    publishFingerprintLog("match.fail", "Scan failed: not found.", "", 0);
    delay(1000);
    return;
  }

  // Found
  Serial.print("Found ID #");
  Serial.print(finger.fingerID);
  Serial.print(" with confidence ");
  Serial.println(finger.confidence);

  String payload = "{\"id\":" + String(finger.fingerID) + ", \"confidence\":" + String(finger.confidence) + "}";
  publishFingerprintLog("match.success", "Match successful.", payload.c_str(), 0);

  door.openDoor();
  delay(5000);
  door.closeDoor();
}

// THÊM HÀM MỚI ĐỂ XÓA VÂN TAY
void deleteFingerprint(int id, uint32_t cmd_id)
{
  uint8_t result = finger.deleteModel(id);

  String payload = "{\"id\":" + String(id) + "}";

  if (result == FINGERPRINT_OK)
  {
    Serial.printf("Successfully deleted fingerprint ID #%d\n", id);
    publishFingerprintLog("delete.success", "Fingerprint deleted successfully.", payload.c_str(), cmd_id);
  }
  else
  {
    Serial.printf("Failed to delete fingerprint. Error code: %d\n", result);
    publishFingerprintLog("delete.error", "Failed to delete fingerprint.", payload.c_str(), cmd_id);
  }
}

// ==========================================
/* Publish fingerprint log via MQTT */
// ==========================================
void publishFingerprintLog(const char *log_type, const char *description, const char *payload, uint32_t cmd_id)
{
  // Hiển thị thông báo lên LCD (nếu có)
  lcd.printMessage(description);

  StaticJsonDocument<256> logDoc;
  logDoc["created_at"] = (uint32_t)time(nullptr);
  logDoc["log_type"]   = log_type;
  logDoc["description"]= description;
  logDoc["payload"]    = payload;

  if (cmd_id > 0) {
    logDoc["command_id"] = cmd_id;
  }

  String output;
  serializeJson(logDoc, output);

  if (!mqttClient.connected()) {
    Serial.println("[FINGERPRINT LOG] MQTT not connected!");
    return;
  }

  bool sent = mqttClient.publish(MQTT_TOPIC_FINGERPRINT_LOG, output.c_str(), true);
  Serial.printf("[FINGERPRINT LOG] Publish %s -> %s\n", output.c_str(), sent ? "OK" : "FAIL");
}

void setup()
{
  Serial.begin(115200);
  pinMode(SERVO_PIN, OUTPUT);

  lcd.begin(); // if you have LCD
  door.begin();
  wifiSetup();

  // NTP time for proper filenames
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("Syncing time");
  uint32_t t0 = millis();
  while (time(nullptr) < 1700000000 && (millis() - t0) < 15000)
  { // ~2023
    Serial.print('.');
    delay(500);
  }
  Serial.println();

  // Init AS608 serial + lib
  softSerial.begin(57600); // default baud for AS608
  delay(100);
  finger.begin(57600); // ensure lib uses same baud
  finger.emptyDatabase();

  if (finger.verifyPassword())
  {
    Serial.println("Found fingerprint sensor!");
  }
  else
  {
    Serial.println("Did not find fingerprint sensor :(");
    // optional: halt or retry
  }

  mqttClient.setBufferSize(2048);
  mqttClient.setServer(mqttServer, port); // provided by your headers/env
  mqttClient.setCallback(callback);
  mqttClient.setKeepAlive(90);

  if (!cameraSetup())
  {
    Serial.println("Camera init failed; halting camera features.");
  }
}

// ==========================================
// loop
// ==========================================
void loop()
{
  if (!mqttClient.connected())
  {
    mqttConnect();
  }
  mqttClient.loop();
  checkFingerprintScanner();

  // unsigned long now = millis();
  // if (now - lastCapture >= captureInterval) {
  //   lastCapture = now;
  //   cameraCapture(mqttClient);
  // }
}
