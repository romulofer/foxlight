// I2C bus scanner for foxlight (SDA D2, SCL D1).
// Expect 0x23 (BH1750) and 0x3C (SSD1306). Open the serial monitor at 115200.
#include <Wire.h>


void setup() {
  Serial.begin(115200);
  Wire.begin(D2, D1);
}

void loop() {
  uint8_t found = 0;
  Serial.println(F("Scanning I2C bus..."));
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print(F("  device at 0x"));
      if (addr < 16) Serial.print('0');
      Serial.print(addr, HEX);
      if (addr == 0x23 || addr == 0x5C) Serial.print(F("  (BH1750)"));
      if (addr == 0x3C || addr == 0x3D) Serial.print(F("  (SSD1306)"));
      Serial.println();
      found++;
    }
  }
  if (!found) Serial.println(F("  nothing found: check wiring, power, pull-ups"));
  Serial.println();
  delay(3000);
}
