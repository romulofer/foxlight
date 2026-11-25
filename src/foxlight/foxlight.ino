// foxlight: fotômetro para fotografia analógica.
// XIAO ESP32C6 ou Wemos D1 mini + BH1750 (sem difusor, apontado para a cena)
// + OLED SSD1306. O usuário define dois entre ISO, abertura e tempo; o medidor
// calcula o terceiro. Pinos em board.h, ligações no README.md.

#include "board.h"

#if defined(ARDUINO_ARCH_ESP8266)
#include <ESP8266WiFi.h>
#else
#include <esp_sleep.h>
#endif
#include <Wire.h>
#include <EEPROM.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <BH1750.h>
#include "exposure.h"
#include "battery.h"

// ── Configuração ─────────────────────────────────────────────────────────────
#define CALIBRATION       1.0f  // multiplica o lux (ver README, "Calibração")
#define DISPLAY_ROTATION  0     // 2 = tela de cabeça para baixo
#define OLED_ADDR         0x3C
#define SENSOR_ADDR       0x23
#define SLEEP_AFTER_MS    60000   // sem uso por este tempo, dorme

#define SAVE_DELAY_MS     2000
#define BATTERY_EVERY_MS  10000

Adafruit_SSD1306 display(128, 64, &Wire, -1, 400000UL, 400000UL);
BH1750 sensor;

// ── Estado ───────────────────────────────────────────────────────────────────
struct Settings {
  uint8_t magic;
  uint8_t target;               // campo calculado
  uint8_t selected;             // campo que +/- alteram
  int8_t  value[FIELD_COUNT];   // terços de stop, ver exposure.h
};

#define SETTINGS_MAGIC 0xF1

const Settings DEFAULTS = {
  SETTINGS_MAGIC, F_SHUTTER, F_APERTURE,
  { 6, 18, 21 }                 // ISO 400, f/8, 1/125
};

Settings cfg;

enum Reading { NOT_MEASURED, MEASURING, MEASURED, DARK, SATURATED, SENSOR_ERROR };

Reading  reading = NOT_MEASURED;
float    lux     = 0;
bool     dirty   = false;
uint32_t dirtyAt = 0;
uint32_t usedAt  = 0;       // último toque em um botão
int      batteryMv = 0;

// Antes das funções: o Arduino gera os protótipos no topo.
enum Press { NO_PRESS, SHORT_PRESS, LONG_PRESS };

struct Button {
  uint8_t  pin;
  bool     repeat;
  bool     stable;
  bool     lastRaw;
  uint32_t changedAt;
  uint32_t nextRepeat;
};

// ── Configurações salvas ─────────────────────────────────────────────────────
void loadSettings() {
  EEPROM.begin(sizeof(Settings));
  EEPROM.get(0, cfg);

  bool valid = cfg.magic == SETTINGS_MAGIC && cfg.target < FIELD_COUNT &&
               cfg.selected < FIELD_COUNT && cfg.selected != cfg.target;
  for (int i = 0; valid && i < FIELD_COUNT; i++)
    valid = cfg.value[i] >= FIELD_MIN[i] && cfg.value[i] <= FIELD_MAX[i];

  if (!valid) cfg = DEFAULTS;
}

void markDirty() {
  dirty   = true;
  dirtyAt = millis();
}

void saveNow() {
  if (!dirty) return;
  EEPROM.put(0, cfg);
  EEPROM.commit();
  dirty = false;
}

// Grava só depois de um tempo sem mudanças, para poupar a flash.
void saveIfIdle() {
  if (dirty && millis() - dirtyAt >= SAVE_DELAY_MS) saveNow();
}

// ── Sensor ───────────────────────────────────────────────────────────────────
// Faz uma conversão. Retorna o lux ou -1 em erro. `saturated` indica que a
// contagem de 16 bits chegou no teto desta configuração.
float sample(BH1750::Mode mode, uint8_t mtreg, bool &saturated) {
  if (!sensor.setMTreg(mtreg) || !sensor.configure(mode)) return -1;

  uint32_t start = millis();
  while (!sensor.measurementReady(true) && millis() - start < 800) delay(1);

  float v = sensor.readLightLevel();
  if (v < 0) return -1;

  float ceiling = 65535.0f / 1.2f * 69.0f / mtreg;
  if (mode == BH1750::ONE_TIME_HIGH_RES_MODE_2) ceiling /= 2;
  saturated = v >= ceiling * 0.97f;
  return v;
}

// Três faixas: normal (até ~27 mil lx), baixa sensibilidade para luz forte
// (até ~121 mil lx) e alta sensibilidade para luz fraca (passo de ~0,1 lx).
void measure() {
  bool saturated = false;
  float v = sample(BH1750::ONE_TIME_HIGH_RES_MODE_2, 69, saturated);

  if (v >= 0 && saturated)
    v = sample(BH1750::ONE_TIME_HIGH_RES_MODE, 31, saturated);
  else if (v >= 0 && v < 10)
    v = sample(BH1750::ONE_TIME_HIGH_RES_MODE_2, 254, saturated);

  if      (v < 0)     reading = SENSOR_ERROR;
  else if (v == 0)    reading = DARK;
  else if (saturated) reading = SATURATED;
  else                reading = MEASURED;

  lux = v > 0 ? v * CALIBRATION : 0;
}

// ── Bateria ──────────────────────────────────────────────────────────────────
#if HAS_BATTERY
void readBattery() {
  uint32_t sum = 0;
  for (int i = 0; i < 16; i++) sum += analogReadMilliVolts(PIN_BATTERY);
  batteryMv = sum / 16 * 2;   // divisor 1:2
}

// Ícone de 16x8 no canto da faixa de cima.
void drawBattery() {
  if (batteryMv < BATTERY_ABSENT_MV) return;
  display.drawRect(112, 4, 14, 8, SSD1306_WHITE);
  display.fillRect(126, 6, 2, 4, SSD1306_WHITE);
  display.fillRect(114, 6, (batteryPercent(batteryMv) + 5) / 10, 4, SSD1306_WHITE);
}
#endif

// ── Botões ───────────────────────────────────────────────────────────────────
// Todos entre o pino e GND (ativo em LOW). Um evento por toque; os com
// `repeat` repetem enquanto segurados.
#define DEBOUNCE_MS       30
#define REPEAT_DELAY_MS  500
#define REPEAT_RATE_MS   150

#define LONG_PRESS_MS    600

enum {
  BTN_MEASURE, BTN_PLUS, BTN_MINUS, BTN_SELECT,
#if HAS_CALC_BUTTON
  BTN_CALC,
#endif
  BTN_COUNT
};

Button buttons[BTN_COUNT] = {
  { PIN_MEASURE, true,  HIGH, HIGH, 0, 0 },   // segurar = medição contínua
  { PIN_PLUS,    true,  HIGH, HIGH, 0, 0 },
  { PIN_MINUS,   true,  HIGH, HIGH, 0, 0 },
  { PIN_SELECT,  false, HIGH, HIGH, 0, 0 },
#if HAS_CALC_BUTTON
  { PIN_CALC,    false, HIGH, HIGH, 0, 0 },
#endif
};

bool buttonEvent(Button &b) {
  bool     raw = digitalRead(b.pin);
  uint32_t now = millis();

  if (raw != b.lastRaw) { b.lastRaw = raw; b.changedAt = now; }

  if (raw != b.stable && now - b.changedAt >= DEBOUNCE_MS) {
    b.stable = raw;
    if (raw == LOW) { b.nextRepeat = now + REPEAT_DELAY_MS; return true; }
  }

  // raw == LOW: sem repetição extra se soltou durante uma medição.
  if (b.repeat && raw == LOW && b.stable == LOW &&
      (int32_t)(now - b.nextRepeat) >= 0) {
    b.nextRepeat = now + REPEAT_RATE_MS;
    return true;
  }
  return false;
}

// Botão Modo: um toque curto vale ao soltar; segurando, vale como toque longo
// uma única vez.
Press modeEvent(Button &b) {
  static bool     pending = false;
  static uint32_t since   = 0;

  if (buttonEvent(b)) { pending = true; since = millis(); }
  if (!pending) return NO_PRESS;

  if (b.stable == HIGH)                { pending = false; return SHORT_PRESS; }
  if (millis() - since >= LONG_PRESS_MS) { pending = false; return LONG_PRESS; }
  return NO_PRESS;
}

// ── Tela ─────────────────────────────────────────────────────────────────────
// Faixa de cima (16 px): lux e EV. Abaixo, uma linha por campo. A calculada
// aparece invertida com "=", a selecionada com ">".
void draw() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 4);

  switch (reading) {
    case NOT_MEASURED: display.print(F("Aperte MEDIR"));      break;
    case MEASURING:    display.print(F("Medindo..."));        break;
    case DARK:         display.print(F("Escuro demais"));     break;
    case SENSOR_ERROR: display.print(F("Erro no sensor"));    break;
    default:
      if (reading == SATURATED) display.print('>');
      display.print(F("lx "));
      display.print(lux, lux < 10 ? 1 : 0);
      display.setCursor(64, 4);
      display.print(F("EV "));
      display.print(ev100FromLux(lux), 1);
  }
#if HAS_BATTERY
  drawBattery();
#endif

  static const char *const NAMES[FIELD_COUNT] = { "ISO", "f/", "T" };
  display.setTextSize(2);

  for (int i = 0; i < FIELD_COUNT; i++) {
    int  y        = 17 + 16 * i;
    bool computed = i == cfg.target;
    char text[12]  = "--";

    if (!computed) {
      formatField(text, sizeof(text), (Field)i, cfg.value[i]);
    } else if (reading == MEASURED || reading == SATURATED) {
      int values[FIELD_COUNT] = { cfg.value[0], cfg.value[1], cfg.value[2] };
      int ev = lroundf(3.0f * ev100FromLux(lux));
      formatField(text, sizeof(text), (Field)i,
                  solveExposure((Field)i, values, ev));
    }

    if (computed) display.fillRect(0, y - 1, 128, 16, SSD1306_WHITE);
    display.setTextColor(computed ? SSD1306_BLACK : SSD1306_WHITE);

    display.setCursor(1, y);
    display.print(computed ? '=' : (i == cfg.selected ? '>' : ' '));
    display.setCursor(15, y);
    display.print(NAMES[i]);
    display.setCursor(127 - 12 * strlen(text), y);
    display.print(text);
  }

  display.display();
}

// ── Ações ────────────────────────────────────────────────────────────────────
// Próximo campo depois de `from`, pulando o calculado.
uint8_t nextSettable(uint8_t from) {
  do from = (from + 1) % FIELD_COUNT; while (from == cfg.target);
  return from;
}

// Calcula T -> f/ -> ISO -> T.
void cycleTarget() {
  cfg.target = (cfg.target + FIELD_COUNT - 1) % FIELD_COUNT;
  if (cfg.selected == cfg.target) cfg.selected = nextSettable(cfg.selected);
  markDirty();
}

void adjust(int step) {
  int i = cfg.selected;
  int v = constrain(cfg.value[i] + step, FIELD_MIN[i], FIELD_MAX[i]);
  if (v == cfg.value[i]) return;
  cfg.value[i] = v;
  markDirty();
}

// ── Sono ─────────────────────────────────────────────────────────────────────
#if HAS_SLEEP
// Desliga tela e sensor e dorme até o botão Medir. Ao acordar, o programa
// recomeça em setup().
void goToSleep() {
  saveNow();

  display.ssd1306_command(SSD1306_DISPLAYOFF);
  display.ssd1306_command(SSD1306_CHARGEPUMP);
  display.ssd1306_command(0x10);               // desliga o conversor da tela

  Wire.beginTransmission(SENSOR_ADDR);
  Wire.write(0x00);                            // BH1750: power down
  Wire.endTransmission();

  esp_sleep_enable_ext1_wakeup(1ULL << digitalPinToGPIONumber(PIN_MEASURE),
                               ESP_EXT1_WAKEUP_ANY_LOW);
  esp_deep_sleep_start();
}

void sleepIfIdle() {
  if (millis() - usedAt < SLEEP_AFTER_MS) return;
  // Ligado a um computador: fica acordado, para gravar e ver a serial.
  if (HWCDC::isPlugged()) return;
  // Botão preso: dormir acordaria na mesma hora.
  if (digitalRead(PIN_MEASURE) == LOW) return;
  goToSleep();
}
#endif

// ── Setup / loop ─────────────────────────────────────────────────────────────
void setup() {
#if defined(ARDUINO_ARCH_ESP8266)
  // Rádio desligado: menos consumo e menos ruído.
  WiFi.persistent(false);
  WiFi.mode(WIFI_OFF);
  WiFi.forceSleepBegin();
#else
  setCpuFrequencyMhz(80);   // o rádio nunca é ligado; 80 MHz bastam
#endif

  Serial.begin(115200);
  for (Button &b : buttons) pinMode(b.pin, INPUT_PULLUP);

  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(400000);

  // A biblioteca não detecta tela ausente: sonda o endereço antes, e assim a
  // tela pode ser ligada depois sem precisar resetar.
  while (Wire.beginTransmission(OLED_ADDR), Wire.endTransmission() != 0) {
    Serial.println(F("OLED nao encontrado (confira SDA, SCL e 0x3C)"));
    delay(1000);
  }
  // Último argumento: não reiniciar o I2C, que perderia os pinos escolhidos.
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR, true, false)) {
    Serial.println(F("Sem memoria para o buffer da tela"));
    while (true) delay(1000);
  }
  display.setRotation(DISPLAY_ROTATION);

  if (!sensor.begin(BH1750::ONE_TIME_HIGH_RES_MODE_2))
    Serial.println(F("BH1750 nao encontrado (ADDR->GND, 0x23)"));

  loadSettings();
#if HAS_BATTERY
  readBattery();
#endif
#if HAS_SLEEP
  // Acordado pelo botão Medir: já mostra uma leitura.
  if (esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_EXT1) measure();
#endif
  draw();
  usedAt = millis();
}

void loop() {
  bool changed = false;

  if (buttonEvent(buttons[BTN_PLUS]))  { adjust(+1); changed = true; }
  if (buttonEvent(buttons[BTN_MINUS])) { adjust(-1); changed = true; }

  switch (modeEvent(buttons[BTN_SELECT])) {
    case SHORT_PRESS:
      cfg.selected = nextSettable(cfg.selected);
      markDirty();
      changed = true;
      break;
    case LONG_PRESS:
      cycleTarget();
      changed = true;
      break;
    case NO_PRESS:
      break;
  }

#if HAS_CALC_BUTTON
  if (buttonEvent(buttons[BTN_CALC]))  { cycleTarget(); changed = true; }
#endif

  if (buttonEvent(buttons[BTN_MEASURE])) {
    // Na medição contínua mantém o valor anterior na tela, sem piscar.
    if (reading != MEASURED) { reading = MEASURING; draw(); }
    measure();
    changed = true;
  }

  for (const Button &b : buttons)
    if (b.stable == LOW) usedAt = millis();
  if (changed) usedAt = millis();

#if HAS_BATTERY
  static uint32_t batteryAt = 0;
  if (millis() - batteryAt >= BATTERY_EVERY_MS) {
    batteryAt = millis();
    readBattery();
    changed = true;
    // Não conta como uso: usedAt fica como está.
  }
#endif

  if (changed) draw();
  saveIfIdle();
#if HAS_SLEEP
  sleepIfIdle();
#endif
  delay(1);
}
