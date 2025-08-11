#ifndef LCD_H_
#define LCD_H_

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#ifndef LCD_SDA_PIN
#define LCD_SDA_PIN 13
#endif

#ifndef LCD_SCL_PIN
#define LCD_SCL_PIN 2
#endif

#ifndef LCD_ADDRESS
#define LCD_ADDRESS 0x27
#endif

#ifndef LCD_COLS
#define LCD_COLS 16
#endif

#ifndef LCD_ROWS
#define LCD_ROWS 2
#endif

class LCD {
  private:
    LiquidCrystal_I2C lcd_;  // rename to avoid confusion
  public:
    LCD() : lcd_(LCD_ADDRESS, LCD_COLS, LCD_ROWS) {}

    void begin() {
      Wire.begin(LCD_SDA_PIN, LCD_SCL_PIN, 50000);   // ESP32 overload is OK
      lcd_.init();                            // for Frank de Brabander’s lib
      // If your fork uses begin(cols, rows) instead of init():
      // lcd_.begin(LCD_COLS, LCD_ROWS);
      lcd_.backlight();
      lcd_.clear();
      lcd_.setCursor(0, 0);
      lcd_.print("Ready ....");
    }

    void printMessage(const String& msg) {
      lcd_.clear();
      if (msg.length() <= LCD_COLS) {
        lcd_.setCursor(0, 0);
        lcd_.print(msg);
      } else {
        for (int i = 0; i <= msg.length() - LCD_COLS; ++i) {
          lcd_.setCursor(0, 0);
          lcd_.print(msg.substring(i, i + LCD_COLS));
          delay(300);
        }
      }
    }
};

static LCD lcd;

#endif
