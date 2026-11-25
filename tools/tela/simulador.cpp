// Desenha a tela do foxlight no PC, com a fonte da biblioteca Adafruit GFX.
// Usado por tools/tela/gerar.py. Escreve as telas de exemplo em formato PBM.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>

#define PROGMEM
#include "glcdfont.c"
#include "../../src/foxlight/ui.h"

struct Tela {
  uint8_t px[64][128] = {};
  int x = 0, y = 0, size = 1, color = 1;
  int fora = 0;                       // pontos desenhados fora da tela

  void ponto(int a, int b, int c) {
    if (a < 0 || a >= 128 || b < 0 || b >= 64) { if (c) fora++; return; }
    px[b][a] = c;
  }
  void setTextSize(int s)    { size = s; }
  void setTextColor(int c)   { color = c; }
  void setCursor(int a, int b) { x = a; y = b; }
  void fillRect(int a, int b, int w, int h, int c) {
    for (int j = 0; j < h; j++)
      for (int i = 0; i < w; i++)
        if (a + i >= 0) ponto(a + i, b + j, c);
  }
  void drawRect(int a, int b, int w, int h, int c) {
    fillRect(a, b, w, 1, c); fillRect(a, b + h - 1, w, 1, c);
    fillRect(a, b, 1, h, c); fillRect(a + w - 1, b, 1, h, c);
  }
  void print(const char *t) {
    for (; *t; t++, x += 6 * size)
      for (int col = 0; col < 5; col++) {
        uint8_t bits = font[(uint8_t)*t * 5 + col];
        for (int lin = 0; lin < 8; lin++)
          if (bits & (1 << lin))
            for (int j = 0; j < size; j++)
              for (int i = 0; i < size; i++)
                ponto(x + col * size + i, y + lin * size + j, color);
      }
  }
};

int main() {
  // reading, lux, {ISO, f/, T}, calculado, selecionado, bateria
  const ScreenState exemplos[] = {
    { MEASURED,     5200,   { 6, 15, 21 },    F_SHUTTER,  F_APERTURE, 80 },
    { MEASURED,     320,    { 6, 6, 18 },     F_APERTURE, F_SHUTTER,  55 },
    { MEASURED,     40,     { 6, 6, 21 },     F_ISO,      F_APERTURE, 20 },
    { NOT_MEASURED, 0,      { 6, 18, 21 },    F_SHUTTER,  F_ISO,      -1 },
    // casos extremos: textos mais longos
    { SATURATED,    121000, { 24, 0, 21 },    F_SHUTTER,  F_ISO,      100 },
    { MEASURED,     121000, { -12, 36, 39 },  F_ISO,      F_SHUTTER,  0 },
  };
  int ruim = 0;
  for (const ScreenState &e : exemplos) {
    Tela t;
    drawScreen(t, e);
    ruim += t.fora;
    printf("P1\n128 64\n");
    for (auto &linha : t.px) {
      for (int p : linha) printf("%d ", p);
      printf("\n");
    }
  }
  if (ruim) fprintf(stderr, "%d pontos fora da tela\n", ruim);
  return ruim ? 1 : 0;
}
