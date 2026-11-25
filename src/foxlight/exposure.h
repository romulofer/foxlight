// Matemática de exposição. Sem dependências do Arduino, testada no PC
// (test/exposure_test.cpp).
//
// Todos os valores são inteiros em terços de stop (escala APEX):
//   ISO      0 = ISO 100
//   abertura 0 = f/1.0
//   tempo    0 = 1 s, positivo = mais rápido
// Assim a exposição vira soma:  abertura + tempo = EV100 + ISO
#pragma once

#include <math.h>
#include <stdio.h>

enum Field { F_ISO, F_APERTURE, F_SHUTTER, FIELD_COUNT };

#define ISO_MIN      -12   // ISO 6
#define ISO_MAX       24   // ISO 25600
#define APERTURE_MIN   0   // f/1.0
#define APERTURE_MAX  36   // f/64
#define SHUTTER_MIN  -15   // 30 s
#define SHUTTER_MAX   39   // 1/8000

static const int FIELD_MIN[FIELD_COUNT] = { ISO_MIN, APERTURE_MIN, SHUTTER_MIN };
static const int FIELD_MAX[FIELD_COUNT] = { ISO_MAX, APERTURE_MAX, SHUTTER_MAX };

static const char *const ISO_LABELS[] = {
  "6", "8", "10", "12", "16", "20", "25", "32", "40", "50", "64", "80",
  "100", "125", "160", "200", "250", "320", "400", "500", "640", "800",
  "1000", "1250", "1600", "2000", "2500", "3200", "4000", "5000", "6400",
  "8000", "10000", "12800", "16000", "20000", "25600"
};

static const char *const APERTURE_LABELS[] = {
  "1.0", "1.1", "1.2", "1.4", "1.6", "1.8", "2.0", "2.2", "2.5", "2.8",
  "3.2", "3.5", "4.0", "4.5", "5.0", "5.6", "6.3", "7.1", "8", "9", "10",
  "11", "13", "14", "16", "18", "20", "22", "25", "29", "32", "36", "40",
  "45", "51", "57", "64"
};

static const char *const SHUTTER_LABELS[] = {
  "30s", "25s", "20s", "15s", "13s", "10s", "8s", "6s", "5s", "4s", "3.2s",
  "2.5s", "2s", "1.6s", "1.3s", "1s", "0.8s", "0.6s", "0.5s", "0.4s", "0.3s",
  "1/4", "1/5", "1/6", "1/8", "1/10", "1/13", "1/15", "1/20", "1/25", "1/30",
  "1/40", "1/50", "1/60", "1/80", "1/100", "1/125", "1/160", "1/200",
  "1/250", "1/320", "1/400", "1/500", "1/640", "1/800", "1/1000", "1/1250",
  "1/1600", "1/2000", "1/2500", "1/3200", "1/4000", "1/5000", "1/6400",
  "1/8000"
};

// Constante K de fotômetro refletido (cd/m2). ISO 2720 admite 10,6 a 13,4;
// 12,5 é o usado por Canon, Nikon e Sekonic.
#define REFLECTED_K          12.5f
// Ângulo sólido efetivo do BH1750 sem difusor, em sr: integral das curvas de
// direcionalidade do datasheet ROHM (figs. 4 e 5). Um receptor cosseno ideal
// daria pi; o sensor é um pouco mais fechado (diferença de 0,31 stop).
#define SENSOR_SOLID_ANGLE   2.53f

// EV (ISO 100) a partir do lux no sensor nu apontado para a cena.
// Cena uniforme: luminância L = lux / ângulo sólido. Equação refletida:
// EV100 = log2(L * 100 / K).
static inline float ev100FromLux(float lux) {
  return log2f(lux * 100.0f / (SENSOR_SOLID_ANGLE * REFLECTED_K));
}

// Calcula o campo `target` a partir dos outros dois. value[target] é ignorado.
// O resultado pode sair da faixa do campo; formatField() trata isso.
static inline int solveExposure(Field target, const int value[FIELD_COUNT], int ev) {
  switch (target) {
    case F_ISO:      return value[F_APERTURE] + value[F_SHUTTER] - ev;
    case F_APERTURE: return ev + value[F_ISO] - value[F_SHUTTER];
    default:         return ev + value[F_ISO] - value[F_APERTURE];
  }
}

// Texto de um valor, no máximo 7 caracteres. Fora da faixa vira "<min" ou
// ">max"; exposições além de 30 s mostram o tempo calculado.
static inline void formatField(char *buf, size_t n, Field field, int v) {
  const char *const *labels = field == F_ISO      ? ISO_LABELS
                            : field == F_APERTURE ? APERTURE_LABELS
                                                  : SHUTTER_LABELS;
  int lo = FIELD_MIN[field], hi = FIELD_MAX[field];

  if (field == F_SHUTTER) {
    if (v < lo) {
      float s = powf(2.0f, -v / 3.0f);
      if      (s < 99.5f)    snprintf(buf, n, "%.0fs", s);
      else if (s < 597.0f)   snprintf(buf, n, "%.1fm", s / 60.0f);
      else if (s < 5970.0f)  snprintf(buf, n, "%.0fm", s / 60.0f);
      else if (s < 356400.f) snprintf(buf, n, "%.0fh", s / 3600.0f);
      else                   snprintf(buf, n, ">99h");
      return;
    }
    // Mais curto que o mínimo: "menor que 1/8000".
    if (v > hi) { snprintf(buf, n, "<%s", labels[hi - lo]); return; }
  } else {
    if (v < lo) { snprintf(buf, n, "<%s", labels[0]);       return; }
    if (v > hi) { snprintf(buf, n, ">%s", labels[hi - lo]); return; }
  }
  snprintf(buf, n, "%s", labels[v - lo]);
}
