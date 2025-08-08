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

const char* IMGBB_API_KEY = "0123456789abcdef0123456789abcdef";

const char* mqttServer = "172.20.10.2";  //!<------------------ REPLACE ME ------------------>!//
int port = 1883;

unsigned long lastCapture = 0;
const unsigned long captureInterval = 10000; // 10s

#define MQTT_TOPIC_PREFIX "23127004_23127113_23127165"



// ===================================================

#endif