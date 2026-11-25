// Teste dos botões do foxlight: mostra na tela e na serial (115200) o estado
// de cada pino e quantas vezes foi acionado.
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

Adafruit_SSD1306 display(128, 64, &Wire, -1, 400000UL, 400000UL);

struct Pin { uint8_t gpio; const char *name; bool last; uint16_t count; };

Pin pins[] = {
  { D5, "D5 Medir",  false, 0 },
  { D6, "D6 +",      false, 0 },
  { D7, "D7 -",      false, 0 },
  { D3, "D3 Selec.", false, 0 },
  { D4, "D4 Calc.",  false, 0 },
};

void setup() {
  Serial.begin(115200);
  for (Pin &p : pins) pinMode(p.gpio, INPUT_PULLUP);
  Wire.begin(D2, D1);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.setTextColor(SSD1306_WHITE);
}

void loop() {
  display.clearDisplay();
  display.setCursor(0, 0);
  display.print(F("TESTE DE BOTOES"));

  int y = 16;
  for (Pin &p : pins) {
    bool down = digitalRead(p.gpio) == LOW;
    if (down && !p.last) {
      p.count++;
      Serial.println(p.name);
    }
    p.last = down;

    display.setCursor(0, y);
    display.print(p.name);
    display.setCursor(68, y);
    display.print(down ? F("ON") : F("--"));
    display.setCursor(98, y);
    display.print(p.count);
    y += 10;
  }

  display.display();
  delay(30);
}
