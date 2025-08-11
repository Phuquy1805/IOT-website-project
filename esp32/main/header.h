#ifndef HEADER_H
#define HEADER_H


#include <Arduino.h>
#include <WiFiManager.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include <PubSubClient.h>

// ================== YOUR SETTINGS ==================

const char* IMGBB_API_KEY = "dc4a619f11ee6e591eba5db7cb696557";

const char* mqttServer = "192.168.1.6";  //!<------------------ REPLACE ME ------------------>!//
int port = 1883;

unsigned long lastCapture = 0;
const unsigned long captureInterval = 10000; // 10s

#define MQTT_TOPIC_PREFIX "23127004_23127113_23127165"



// ===================================================

#endif