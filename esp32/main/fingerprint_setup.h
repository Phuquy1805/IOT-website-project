#ifndef FINGERPRINT_H
#define FINGERPRINT_H



#include <Adafruit_Fingerprint.h>
#include <SoftwareSerial.h>

// ----- AS608 wiring -----
// Sensor RX -> ESP32 TX (GPIO 15)
// Sensor TX -> ESP32 RX (GPIO 14)
#define FINGERPRINT_RX 14  // to sensor TX
#define FINGERPRINT_TX 15  // to sensor RX

#define FINGERPRINT_CAPACITY 150

#endif