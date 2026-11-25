// Estimativa de carga de uma célula Li-ion/LiPo pela tensão.
#pragma once

// Abaixo disto não há bateria ligada ao divisor.
#define BATTERY_ABSENT_MV  2500

// Percentual aproximado pela curva de descarga típica, com pouca carga ligada.
// Serve para o ícone da tela, não como medida precisa.
static inline int batteryPercent(int mv) {
  static const int MV[]  = { 3300, 3600, 3700, 3750, 3800, 3900, 4000, 4100, 4200 };
  static const int PCT[] = {    0,    5,   15,   30,   45,   65,   80,   90,  100 };
  const int n = sizeof(MV) / sizeof(MV[0]);

  if (mv <= MV[0]) return 0;
  for (int i = 1; i < n; i++)
    if (mv < MV[i])
      return PCT[i - 1] +
             (mv - MV[i - 1]) * (PCT[i] - PCT[i - 1]) / (MV[i] - MV[i - 1]);
  return 100;
}
