// Pinos e recursos de cada placa suportada.
//   XIAO ESP32C6  aparelho compacto (rev 2): 4 botões, bateria e sono profundo
//   D1 mini       protoboard e placa rev 1: 5 botões, só USB
#pragma once

#if defined(ARDUINO_ARCH_ESP8266)

#define PIN_SDA      D2
#define PIN_SCL      D1
#define PIN_MEASURE  D5
#define PIN_PLUS     D6
#define PIN_MINUS    D7
#define PIN_SELECT   D3   // GPIO0: não segurar ao ligar
#define PIN_CALC     D4   // GPIO2: não segurar ao ligar

#define HAS_CALC_BUTTON  1
#define HAS_BATTERY      0
#define HAS_SLEEP        0

#elif defined(ARDUINO_XIAO_ESP32C6)

#define PIN_SDA      D4
#define PIN_SCL      D5
#define PIN_MEASURE  D1   // GPIO1: acorda o aparelho; resistor de 100k ao 3V3
#define PIN_PLUS     D2
#define PIN_MINUS    D3
#define PIN_SELECT   D10  // botão "Modo": toque seleciona, segurar troca a incógnita
#define PIN_BATTERY  A0   // metade da tensão da bateria (2 x 200k)

#define HAS_CALC_BUTTON  0
#define HAS_BATTERY      1
#define HAS_SLEEP        1

#else
#error "Placa sem pinagem definida: use d1_mini ou XIAO_ESP32C6"
#endif
