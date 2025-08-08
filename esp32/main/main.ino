#include "header.h"
// #include "mqtt.h"
#include "cam.h"
#include "wifi_setup.h"
#include "servo_setup.h"

// ----- MQTT objects -----
WiFiClient espClient;
PubSubClient mqttClient(espClient);



static const char MQTT_TOPIC_LCD_COMMAND[]       PROGMEM = "/" MQTT_TOPIC_PREFIX "/lcd/command";
static const char MQTT_TOPIC_LCD_LOG[]           PROGMEM = "/" MQTT_TOPIC_PREFIX "/lcd/log";
static const char MQTT_TOPIC_SERVO_COMMAND[]     PROGMEM = "/" MQTT_TOPIC_PREFIX "/servo/command";
static const char MQTT_TOPIC_SERVO_LOG[]         PROGMEM = "/" MQTT_TOPIC_PREFIX "/servo/log";
static const char MQTT_TOPIC_FINGERPRINT_COMMAND[]    PROGMEM = "/" MQTT_TOPIC_PREFIX "/fingerprint/command";
static const char MQTT_TOPIC_FINGERPRINT_LOG[]        PROGMEM = "/" MQTT_TOPIC_PREFIX "/fingerprint/log";



void mqttConnect() {
  while (!mqttClient.connected()) {
    Serial.println("Attemping MQTT connection...");
    String clientId = "ESP32Client-" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("connected");
      mqttClient.subscribe(MQTT_TOPIC_LCD_COMMAND);
      mqttClient.subscribe(MQTT_TOPIC_SERVO_COMMAND);
      mqttClient.subscribe(MQTT_TOPIC_FINGERPRINT_COMMAND);

    } else {
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

inline void callback(char* topic, byte* payload, unsigned int len)
{
    String msg;
    msg.reserve(len);
    for (unsigned int i = 0; i < len; ++i) msg += (char)payload[i];

    Serial.printf("Topic: %s | Payload: %s\n", topic, msg.c_str());

    if (strcmp(topic, MQTT_TOPIC_SERVO_COMMAND) == 0) {
        handleServoCommand(msg);
    }
}

inline void handleServoCommand(const String& jsonText)
{
  /* 1 — parse */
    Serial.print("Handling servo command");
  StaticJsonDocument<128> doc;
  DeserializationError err = deserializeJson(doc, jsonText);
  if (err) {
      Serial.printf("Bad JSON in servo command: %s\n", err.c_str());
      return;                     // silently ignore
  }
  uint32_t cmdId  = doc["cmd_id"]    | 0;
  String   action = doc["action"] | "";

  /* 2 — execute */
  bool ok = true;
  if      (action.equalsIgnoreCase("open"))  door.openDoor();
  else if (action.equalsIgnoreCase("close")) door.closeDoor();
  else                                        ok = false;

  /* 3 — build log */
  StaticJsonDocument<256> logDoc;
  logDoc["created_at"] = (uint32_t)time(nullptr);
  logDoc["log_type"]   = "servo.status";
  logDoc["description"]= ok ? "State changed by Webserver's command." : "invalid command";
  logDoc["payload"]    = action;
  logDoc["topic"]      = MQTT_TOPIC_SERVO_COMMAND;
  logDoc["command_id"] = cmdId;   
  logDoc["related_log_id"] = nullptr;

  String payload;
  serializeJson(logDoc, payload);

  if (!mqttClient.connected())
          Serial.println("[servo] MQTT not connected!");

      bool sent = mqttClient.publish(MQTT_TOPIC_SERVO_LOG,
                                    payload.c_str(), true);

      Serial.printf("[servo] Publish %s (%u B) → %s\n",
                    MQTT_TOPIC_SERVO_LOG, payload.length(),
                    sent ? "OK" : "FAIL");
}


void setup() {
  Serial.begin(115200);

  door.begin();


  wifiSetup();

  // NTP time for proper filenames
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("Syncing time");
  uint32_t t0 = millis();
  while (time(nullptr) < 1700000000 && (millis() - t0) < 15000) { // ~2023
    Serial.print('.');
    delay(500);
  }
  Serial.println();
  delay(200);

  if (!cameraSetup()){
    return;
  }

  mqttClient.setBufferSize(1024);
  mqttClient.setServer(mqttServer, port);
  mqttClient.setCallback(callback);
  mqttClient.setKeepAlive(90);
}


void loop() {
  if (!mqttClient.connected()) {
    mqttConnect();
  }
  mqttClient.loop();

  unsigned long now = millis();
  if (now - lastCapture >= captureInterval) {
    lastCapture = now;
    cameraCapture(mqttClient);

  }
}
