// Testes de src/foxlight/exposure.h no PC:
//   g++ -std=c++11 -Wall -Wextra -o /tmp/exposure_test test/exposure_test.cpp && /tmp/exposure_test
#include <cstdio>
#include <cstring>
#include "../src/foxlight/exposure.h"

static int failures = 0;

#define CHECK(c) do { if (!(c)) { printf("FALHOU %s:%d  %s\n", __FILE__, __LINE__, #c); failures++; } } while (0)

static void checkText(int line, Field f, int v, const char *want) {
  char got[12];
  formatField(got, sizeof got, f, v);
  if (strcmp(got, want) != 0) {
    printf("FALHOU linha %d: \"%s\", esperado \"%s\"\n", line, got, want);
    failures++;
  }
}
#define TEXT(f, v, want) checkText(__LINE__, f, v, want)

#define COUNT(a) ((int)(sizeof(a) / sizeof(a[0])))

int main() {
  // Cada tabela cobre exatamente a sua faixa.
  CHECK(COUNT(ISO_LABELS)      == ISO_MAX      - ISO_MIN      + 1);
  CHECK(COUNT(APERTURE_LABELS) == APERTURE_MAX - APERTURE_MIN + 1);
  CHECK(COUNT(SHUTTER_LABELS)  == SHUTTER_MAX  - SHUTTER_MIN  + 1);

  // Pontos de referência das tabelas (stops inteiros).
  TEXT(F_ISO, 0, "100");       TEXT(F_ISO, 6, "400");
  TEXT(F_APERTURE, 6, "2.0");  TEXT(F_APERTURE, 18, "8");   TEXT(F_APERTURE, 24, "16");
  TEXT(F_SHUTTER, 0, "1s");    TEXT(F_SHUTTER, 6, "1/4");   TEXT(F_SHUTTER, 21, "1/125");

  // EV 15 refletido = luminância de 4096 cd/m2.
  CHECK(fabs(ev100FromLux(4096.0f * SENSOR_SOLID_ANGLE) - 15.0f) < 1e-3);

  // Referência cruzada (addrummond/mlm, units.c): com receptor cosseno ideal,
  // refletida = log2(lux / 2,5) + log2(100 / 15,7). Aqui soma-se a correção
  // do ângulo do BH1750.
  float cruzado = log2f(1000.0f / 2.5f) + log2f(100.0f / 15.7f)
                + log2f(3.14159265f / SENSOR_SOLID_ANGLE);
  CHECK(fabs(ev100FromLux(1000.0f) - cruzado) < 0.01f);

  // Sunny 16: EV 15, ISO 100, f/16 -> ~1/125. Cada incógnita fecha a conta.
  int v[FIELD_COUNT] = { 0, 24, 21 };
  CHECK(solveExposure(F_SHUTTER,  v, 45) == 21);
  CHECK(solveExposure(F_APERTURE, v, 45) == 24);
  CHECK(solveExposure(F_ISO,      v, 45) == 0);

  // Um stop a menos de luz dobra o tempo ou o ISO.
  CHECK(solveExposure(F_SHUTTER, v, 42) == 18);
  CHECK(solveExposure(F_ISO,     v, 42) == 3);

  // Fora da faixa.
  TEXT(F_ISO, ISO_MIN - 1, "<6");               TEXT(F_ISO, ISO_MAX + 1, ">25600");
  TEXT(F_APERTURE, -1, "<1.0");                 TEXT(F_APERTURE, 37, ">64");
  TEXT(F_SHUTTER, SHUTTER_MAX + 1, "<1/8000");
  TEXT(F_SHUTTER, -18, "64s");                  TEXT(F_SHUTTER, -21, "2.1m");
  TEXT(F_SHUTTER, -30, "17m");                  TEXT(F_SHUTTER, -39, "2h");
  TEXT(F_SHUTTER, -90, ">99h");

  // Nenhum texto passa de 7 caracteres (cabe na tela).
  for (int f = 0; f < FIELD_COUNT; f++)
    for (int i = -150; i <= 150; i++) {
      char b[32];
      formatField(b, sizeof b, (Field)f, i);
      CHECK(strlen(b) <= 7);
    }

  if (failures) { printf("%d falha(s)\n", failures); return 1; }
  printf("todos os testes passaram\n");
  return 0;
}
