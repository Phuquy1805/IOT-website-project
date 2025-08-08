#ifndef SERVO_H_
#define SERVO_H_

#include <ESP32Servo.h>

#ifndef SERVO_PIN
#define SERVO_PIN 14
#endif
#define SERVO_OPEN_DEG   90
#define SERVO_CLOSED_DEG  0

class DoorServo {
  public:
    void begin() { servo.attach(SERVO_PIN); servo.write(SERVO_CLOSED_DEG); open = false; }
    void openDoor()  { servo.write(SERVO_OPEN_DEG);   open = true; }
    void closeDoor() { servo.write(SERVO_CLOSED_DEG); open = false; }
    bool isOpen() const { return open; }
  private:
    Servo servo;
    bool  open = false;
};

static DoorServo door;

#endif