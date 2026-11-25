// Desenho da tela (128x64). Não depende do hardware: `Tela` precisa só de
// setTextSize, setTextColor, setCursor, print(const char*), fillRect e
// drawRect, como as bibliotecas Adafruit. O simulador em tools/tela usa isto.
#pragma once
#include <string.h>
#include "exposure.h"

enum Reading { NOT_MEASURED, MEASURING, MEASURED, DARK, SATURATED, SENSOR_ERROR };

struct ScreenState {
  Reading reading;
  float   lux;
  int     value[FIELD_COUNT];   // terços de stop
  int     target;               // campo calculado
  int     selected;             // campo que ◄ ► alteram
  int     battery;              // 0 a 100, ou -1 sem bateria
};

#define UI_ON   1
#define UI_OFF  0

// Valor como aparece na tela: a abertura ganha o prefixo "f/".
static inline void fieldText(char *buf, size_t n, int field, int v) {
  char t[8];                    // formatField usa no máximo 7 letras
  formatField(t, sizeof(t), (Field)field, v);
  snprintf(buf, n, "%s%s", field == F_APERTURE ? "f/" : "", t);
}

template <class Tela>
void printAt(Tela &d, int x, int y, const char *text, bool inverted = false) {
  if (inverted) d.fillRect(x - 2, y - 1, 6 * (int)strlen(text) + 3, 9, UI_ON);
  d.setTextColor(inverted ? UI_OFF : UI_ON);
  d.setCursor(x, y);
  d.print(text);
}

// Linha de cima: EV e lux, ou o aviso do estado. Ícone da bateria à direita.
template <class Tela>
void drawHeader(Tela &d, const ScreenState &s) {
  char buf[20];
  switch (s.reading) {
    case NOT_MEASURED: printAt(d, 0, 0, "Aperte MEDIR");   break;
    case MEASURING:    printAt(d, 0, 0, "Medindo...");     break;
    case DARK:         printAt(d, 0, 0, "Escuro demais");  break;
    case SENSOR_ERROR: printAt(d, 0, 0, "Erro no sensor"); break;
    default:
      snprintf(buf, sizeof(buf), "EV %.1f", ev100FromLux(s.lux));
      printAt(d, 0, 0, buf);
      snprintf(buf, sizeof(buf), "%slx %.*f", s.reading == SATURATED ? ">" : "",
               s.lux < 10 ? 1 : 0, s.lux);
      printAt(d, 48, 0, buf);
  }
  if (s.battery < 0) return;
  d.drawRect(112, 0, 14, 7, UI_ON);
  d.fillRect(126, 2, 2, 3, UI_ON);
  d.fillRect(114, 2, (s.battery + 5) / 10, 3, UI_ON);
}

// De cima para baixo: cabeçalho; os dois valores definidos (o selecionado
// invertido); o resultado em letras grandes; e a régua do valor selecionado,
// com o anterior e o próximo.
template <class Tela>
void drawScreen(Tela &d, const ScreenState &s) {
  char buf[12];
  d.setTextSize(1);
  drawHeader(d, s);

  bool first = true;
  for (int i = 0; i < FIELD_COUNT; i++) {
    if (i == s.target) continue;
    char line[20];
    fieldText(buf, sizeof(buf), i, s.value[i]);
    snprintf(line, sizeof(line), "%s%s", i == F_ISO ? "ISO " : "", buf);
    int x = first ? 2 : 127 - 6 * (int)strlen(line);
    printAt(d, x, 9, line, i == s.selected);
    first = false;
  }

  bool known = s.reading == MEASURED || s.reading == SATURATED;
  strcpy(buf, "--");
  if (known) {
    int ev = lroundf(3.0f * ev100FromLux(s.lux));
    fieldText(buf, sizeof(buf), s.target,
              solveExposure((Field)s.target, s.value, ev));
  }
  int width = 18 * (int)strlen(buf);            // tamanho 3: 18 px por letra
  int x = (128 - width) / 2;
  if (s.target == F_ISO) {                      // "ISO" pequeno ao lado
    x = (128 - width - 20) / 2;
    printAt(d, x, 33, "ISO");
    x += 20;
  }
  d.setTextSize(3);
  printAt(d, x, 22, buf);
  d.setTextSize(1);

  const int y = 54;
  int sel = s.selected, v = s.value[sel];
  printAt(d, 0, y, "<");
  printAt(d, 122, y, ">");
  if (v > FIELD_MIN[sel]) {
    fieldText(buf, sizeof(buf), sel, v - 1);
    printAt(d, 9, y, buf);
  }
  fieldText(buf, sizeof(buf), sel, v);
  printAt(d, 64 - 3 * (int)strlen(buf), y, buf, true);
  if (v < FIELD_MAX[sel]) {
    fieldText(buf, sizeof(buf), sel, v + 1);
    printAt(d, 119 - 6 * (int)strlen(buf), y, buf);
  }
}
