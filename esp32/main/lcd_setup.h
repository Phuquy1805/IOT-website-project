#ifndef LCD_H_
#define LCD_H_

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#ifndef LCD_SDA_PIN
#define LCD_SDA_PIN 13
#endif

#ifndef LCD_SCL_PIN
#define LCD_SCL_PIN 14
#endif

#define LCD_ADDRESS 0x27
#define LCD_COLS 16
#define LCD_ROWS 2

class LCD{
    //Attributes:
    private:
        LiquidCrystal_I2C lcd;
    public:
        LCD(){
            lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);
        }

        void begin(){
            Wire.begin(LCD_SDA_PIN, LCD_SCL_PIN);
            lcd.init();
            lcd.backlight();
            lcd.clear();
            lcd.setCursor(0,0);
            lcd.print("Ready ....");
        }

        void printMessage(const String& msg) {
            lcd.clear();
            if (msg.length() <= LCD_COLS) {
                lcd.setCursor(0, 0);
                lcd.print(msg);
            } else {
                // Cuộn dòng nếu dài hơn 16 ký tự
                for (int i = 0; i <= msg.length() - LCD_COLS; ++i) {
                lcd.setCursor(0, 0);
                lcd.print(msg.substring(i, i + LCD_COLS));
                delay(300);  // tốc độ cuộn
                }
            }
        }
}

#endif