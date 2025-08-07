#ifndef MQTT_H
#define MQTT_H

#include <PubSubClient.h>
#include <header.h>

String MQTT_TOPIC_LCD_COMMAND = String("/") + MQTT_TOPIC_PREFIX + "/lcd/command";
String MQTT_TOPIC_LCD_LOG = String("/") + MQTT_TOPIC_PREFIX + "/lcd/log";

String MQTT_TOPIC_SERVO_COMMAND = String("/") + MQTT_TOPIC_PREFIX + "/servo/command";
String MQTT_TOPIC_SERVO_LOG = String("/") + MQTT_TOPIC_PREFIX + "/servo/log";

String MQTT_TOPIC_FINGERPRINT_COMMAND = String("/") + MQTT_TOPIC_PREFIX + "/fingerprint/command";
String MQTT_TOPIC_FINGERPRINT_LOG = String("/") + MQTT_TOPIC_PREFIX + "/fingerprint/log";



void mqttConnect(PubSubClient &mqttClient) {
  while (!mqttClient.connected()) {
    Serial.println("Attemping MQTT connection...");
    String clientId = "ESP32Client-" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("connected");
      mqttClient.subscribe(MQTT_TOPIC_LCD_COMMAND.c_str());
      mqttClient.subscribe(MQTT_TOPIC_LCD_LOG.c_str());

      mqttClient.subscribe(MQTT_TOPIC_SERVO_COMMAND.c_str());
      mqttClient.subscribe(MQTT_TOPIC_SERVO_LOG.c_str());

      mqttClient.subscribe(MQTT_TOPIC_FINGERPRINT_COMMAND.c_str());
      mqttClient.subscribe(MQTT_TOPIC_FINGERPRINT_LOG.c_str());

    } else {
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void callback(char* topic, byte* message, unsigned int length) {
  Serial.println(topic);
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)message[i];
  Serial.println(msg);
}

#endif