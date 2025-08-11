#ifndef LCD_H_
#define LCD_H_

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#ifndef LCD_SDA_PIN
#define LCD_SDA_PIN 13   // NOTE: GPIO2 is a boot strap; avoid using it for SCL if you can.
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
#ifndef LCD_SCROLL_INTERVAL_MS
#define LCD_SCROLL_INTERVAL_MS 250  // speed of marquee steps
#endif

class LCD {
  private:
    LiquidCrystal_I2C lcd_;
    String msg_;               // full message (may contain '\n')
    String line0_;             // what we currently draw on row 0
    String line1_;             // what we currently draw on row 1
    uint32_t lastStep_ = 0;    // last marquee tick time
    uint16_t pos_ = 0;         // marquee window offset
    bool scrolling_ = false;   // are we scrolling row 0?
    bool dirty_ = true;        // needs a redraw

    // pad/truncate helper to exactly LCD_COLS chars (prevents ghost chars)
    static String window(const String& s, uint16_t start, uint16_t width) {
      String out;
      if (start < s.length()) out = s.substring(start, min<uint16_t>(start + width, s.length()));
      while ((int)out.length() < (int)width) out += ' ';
      return out;
    }

    void drawIfDirty() {
      if (!dirty_) return;
      // Write row 0
      lcd_.setCursor(0, 0);
      lcd_.print(window(line0_, 0, LCD_COLS));
      // Write row 1 if present
      if (LCD_ROWS > 1) {
        lcd_.setCursor(0, 1);
        lcd_.print(window(line1_, 0, LCD_COLS));
      }
      dirty_ = false;
    }

  public:
    LCD() : lcd_(LCD_ADDRESS, LCD_COLS, LCD_ROWS) {}

    void begin() {
      Wire.begin(LCD_SDA_PIN, LCD_SCL_PIN, 50000);   // keep I2C slow on ESP32-CAM
      lcd_.init();                                   // or lcd_.begin(LCD_COLS, LCD_ROWS) for some forks
      lcd_.backlight();
      printMessage(F("Ready ...."));                 // non-blocking now
    }

    // Set a new message. If it contains '\n', we show 2 lines (no scrolling).
    // If it's longer than LCD_COLS without '\n', we marquee on the first row.
    void printMessage(const String& msg) {
      msg_ = msg;
      // Split into at most two lines by first newline
      int nl = msg_.indexOf('\n');
      if (nl >= 0) {
        line0_ = msg_.substring(0, nl);
        line1_ = msg_.substring(nl + 1);
        scrolling_ = false;          // no scrolling in two-line mode
      } else {
        line0_ = msg_;
        line1_ = "";                 // clear second row
        scrolling_ = (line0_.length() > LCD_COLS);
      }
      // Reset marquee and redraw immediately
      pos_ = 0;
      lastStep_ = millis();
      dirty_ = true;
      drawIfDirty();                 // show first frame right away
    }

    // Call this frequently from loop() — non-blocking.
    void update() {
      // Only marquee if a single-line message exceeds the width
      if (scrolling_) {
        uint32_t now = millis();
        if (now - lastStep_ >= LCD_SCROLL_INTERVAL_MS) {
          lastStep_ = now;
          // Advance scrolling window (one char)
          pos_++;
          // Build the current window; when we reach the end, loop with a space gap
          // e.g., "Hello World" -> "Hello World ··· "
          const String gap = "   ";
          String scrollBuf = line0_ + gap;
          if (pos_ > scrollBuf.length()) pos_ = 0;

          String frame = window(scrollBuf, pos_, LCD_COLS);
          // Only touch row 0; row 1 stays blank
          lcd_.setCursor(0, 0);
          lcd_.print(frame);
        }
      } else {
        // Nothing to scroll; ensure initial draw happened
        drawIfDirty();
      }
    }
};



#endif
