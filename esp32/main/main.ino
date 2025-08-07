#include "header.h"
#include "mqtt.h"
#include "cam.h"
#include "wifi_setup.h"

// ----- MQTT objects -----
WiFiClient espClient;
PubSubClient mqttClient(espClient);


void setup() {
  Serial.begin(115200);


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

  mqttClient.setServer(mqttServer, port);
  mqttClient.setCallback(callback);
  mqttClient.setKeepAlive(90);
}


void loop() {
  if (!mqttClient.connected()) {
    mqttConnect(mqttClient);
  }
  mqttClient.loop();

  unsigned long now = millis();
  if (now - lastCapture >= captureInterval) {
    lastCapture = now;
    cameraCapture(mqttClient);

  }
}
