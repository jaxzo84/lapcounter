#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

const int SENSOR_PIN = 2;     // digital input från break-beam mottagare
const unsigned long DEBOUNCE_MS = 150; // spärrtid efter trigger (justera)
unsigned long lastTrigger = 0;
unsigned long lastEdge = 0;
float lastLapSec = 0.0;
float bestLapSec = 9999.0;
bool firstPass = true;

void setup() {
  pinMode(SENSOR_PIN, INPUT_PULLUP);
  Serial.begin(115200);

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED hittas inte");
    for(;;);
  }
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0,0);
  display.println("Varvraknare klar");
  display.display();
  delay(800);
  display.clearDisplay();
  lastTrigger = millis();
}

void loop() {
  int val = digitalRead(SENSOR_PIN);
  unsigned long now = millis();

  if (val == HIGH) {
    if (now - lastEdge > DEBOUNCE_MS) {
      lastEdge = now;

      if (!firstPass) {
        unsigned long dt = now - lastTrigger;   // ms
        lastLapSec = dt / 1000.0;

        if (lastLapSec > 0.05 && lastLapSec < 9999) {
          if (lastLapSec < bestLapSec) bestLapSec = lastLapSec;

          // --- SEND TO PC: just the milliseconds as an integer line ---
          Serial.println(dt);
        }
      } else {
        firstPass = false;
      }

      lastTrigger = now;

      // OLED display
      display.clearDisplay();
      display.setCursor(0,0);
      display.print("Senaste: ");
      display.print(lastLapSec, 3);
      display.println(" s");
      display.print("Basta:   ");
      if (bestLapSec < 9999) display.print(bestLapSec, 3);
      else display.print("---");
      display.println(" s");
      display.display();
    }

    while (digitalRead(SENSOR_PIN) == HIGH) {
      delay(5);
    }
  }
}
