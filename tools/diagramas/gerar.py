#!/usr/bin/env python3
"""Gera os desenhos do guia de montagem (docs/montagem/*.png).

Uso, na raiz do projeto:  python3 tools/diagramas/gerar.py
Precisa de Pillow e das fontes DejaVu.
"""
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / 'docs' / 'montagem'
S = 2  # desenha no dobro do tamanho e reduz, para suavizar

FUNDO = (250, 250, 246)
TINTA = (30, 30, 30)
APAGADO = (160, 160, 160)
TRILHA_AZUL = (185, 210, 248)
TRILHA_VERMELHA = (248, 196, 196)
CORES = {
    'preto': (20, 20, 20), 'vermelho': (215, 30, 30), 'amarelo': (235, 175, 0),
    'verde': (20, 145, 60), 'laranja': (240, 110, 0), 'roxo': (130, 50, 180),
    'marrom': (140, 85, 40), 'rosa': (225, 60, 145), 'azul': (25, 100, 215),
}


def fonte(tamanho, negrito=True):
    nome = 'DejaVuSans-Bold.ttf' if negrito else 'DejaVuSans.ttf'
    return ImageFont.truetype(f'/usr/share/fonts/truetype/dejavu/{nome}', tamanho * S)


class Tela:
    def __init__(self, largura, altura):
        self.tam = (largura, altura)
        self.im = Image.new('RGB', (largura * S, altura * S), FUNDO)
        self.d = ImageDraw.Draw(self.im)

    def caixa(self, x1, y1, x2, y2, cor, borda=TINTA, esp=3, raio=14):
        self.d.rounded_rectangle([x1 * S, y1 * S, x2 * S, y2 * S], raio * S,
                                 fill=cor, outline=borda, width=esp * S)

    def texto(self, x, y, t, tam=28, cor=TINTA, ancora='mm', negrito=True):
        self.d.text((x * S, y * S), t, font=fonte(tam, negrito), fill=cor, anchor=ancora)

    def bola(self, x, y, r, cor, borda=None, esp=2):
        self.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S],
                       fill=cor, outline=borda, width=esp * S if borda else 0)

    def linha(self, pontos, cor, esp):
        p = [(x * S, y * S) for x, y in pontos]
        self.d.line(p, fill=cor, width=esp * S, joint='curve')
        for x, y in pontos:
            self.bola(x, y, esp / 2, cor)

    def numero(self, x, y, n, cor):
        self.bola(x, y, 24, (255, 255, 255), cor, 5)
        self.texto(x, y, str(n), 26, cor)

    def salvar(self, nome):
        SAIDA.mkdir(parents=True, exist_ok=True)
        self.im.resize(self.tam, Image.LANCZOS).save(SAIDA / nome, optimize=True)


# ── Placa D1 mini vista de cima, USB para cima ───────────────────────────────
Y_PINOS = [250, 330, 410, 490, 570, 650, 730, 810]
ESQ = [('5V', ''), ('G', 'GND'), ('D4', '2'), ('D3', '0'),
       ('D2', '4'), ('D1', '5'), ('RX', ''), ('TX', '')]
DIR = [('3V3', ''), ('D8', '15'), ('D7', '13'), ('D6', '12'),
       ('D5', '14'), ('D0', '16'), ('A0', ''), ('RST', '')]
PINO = {n: (600, y) for (n, _), y in zip(ESQ, Y_PINOS)}
PINO.update({n: (1000, y) for (n, _), y in zip(DIR, Y_PINOS)})

# Botões: nome -> (centro x, centro y, pino, cor do fio)
BOTOES = {
    'MEDIR':      (1250, 660, 'D5', 'laranja'),
    'MAIS (+)':   (1250, 480, 'D6', 'roxo'),
    'MENOS (−)':  (1250, 300, 'D7', 'marrom'),
    'SELECIONAR': (250, 520, 'D3', 'rosa'),
    'CALCULAR':   (250, 300, 'D4', 'azul'),
}


def perna_sinal(nome):
    x, y = BOTOES[nome][:2]
    return (x + 75 if x < 800 else x - 75, y - 40)


def perna_gnd(nome):
    x, y = BOTOES[nome][:2]
    return (x - 75 if x < 800 else x + 75, y + 40)


# ── Fios ─────────────────────────────────────────────────────────────────────
# Cada fio: (passo, cor, caminho, de, até)
Y_GND, Y_VCC, Y_MOD = 940, 1020, 1190
FIOS = []


def fio(passo, cor, caminho, de, ate):
    FIOS.append((passo, cor, caminho, de, ate))


fio(1, 'preto', [PINO['G'], (560, 330), (560, 110), (60, 110), (60, 215)],
    'pino G (GND) da placa', 'trilha azul (−)')
fio(2, 'vermelho', [PINO['3V3'], (1040, 250), (1040, 70), (1570, 70), (1570, Y_VCC)],
    'pino 3V3 da placa', 'trilha vermelha (+)')

# Tela
fio(3, 'vermelho', [(260, Y_VCC), (260, Y_MOD)], 'VCC da tela', 'trilha vermelha (+)')
fio(3, 'preto', [(340, Y_GND), (340, Y_MOD)], 'GND da tela', 'trilha azul (−)')
fio(3, 'amarelo', [PINO['D1'], (420, 650), (420, Y_MOD)], 'SCL da tela', 'pino D1')
fio(3, 'verde', [PINO['D2'], (500, 570), (500, Y_MOD)], 'SDA da tela', 'pino D2')

# Sensor
fio(4, 'vermelho', [(960, Y_VCC), (960, Y_MOD)], 'VCC do sensor', 'trilha vermelha (+)')
fio(4, 'preto', [(1040, Y_GND), (1040, Y_MOD)], 'GND do sensor', 'trilha azul (−)')
fio(4, 'amarelo', [(420, 1120), (1120, 1120), (1120, Y_MOD)],
    'SCL do sensor', 'pino D1 (junto com o SCL da tela)')
fio(4, 'verde', [(500, 1070), (1200, 1070), (1200, Y_MOD)],
    'SDA do sensor', 'pino D2 (junto com o SDA da tela)')
fio(4, 'preto', [(1280, Y_GND), (1280, Y_MOD)], 'ADDR do sensor', 'trilha azul (−)')

# Botões, um por passo
CAMINHOS = {
    'MEDIR':      [PINO['D5'], (1120, 570), (1120, 620)],
    'MAIS (+)':   [PINO['D6'], (1120, 490), (1120, 440)],
    'MENOS (−)':  [PINO['D7'], (1080, 410), (1080, 260)],
    'SELECIONAR': [PINO['D3'], (400, 490), (400, 480)],
    'CALCULAR':   [PINO['D4'], (470, 410), (470, 260)],
}
for passo, nome in enumerate(BOTOES, start=5):
    pino, cor = BOTOES[nome][2:]
    fio(passo, cor, CAMINHOS[nome] + [perna_sinal(nome)],
        f'pino {pino}', f'uma perna do botão {nome}')
    borda = 60 if BOTOES[nome][0] < 800 else 1500
    fio(passo, 'preto', [perna_gnd(nome), (borda, perna_gnd(nome)[1])],
        f'perna na diagonal do botão {nome}', 'trilha azul (−)')

TITULOS = {
    1: 'Passo 1: o fio do GND',
    2: 'Passo 2: o fio da energia (3V3)',
    3: 'Passo 3: a tela',
    4: 'Passo 4: o sensor de luz',
    5: 'Passo 5: botão MEDIR',
    6: 'Passo 6: botão MAIS (+)',
    7: 'Passo 7: botão MENOS (−)',
    8: 'Passo 8: botão SELECIONAR',
    9: 'Passo 9: botão CALCULAR',
}


def conferir_com_firmware():
    """Os pinos desenhados têm de ser os mesmos do firmware."""
    placas = (RAIZ / 'src' / 'foxlight' / 'board.h').read_text()
    d1_mini = placas.split('ARDUINO_ARCH_ESP8266)')[1].split('#elif')[0]
    pinos = dict(re.findall(r'#define PIN_(\w+)\s+(D\d)', d1_mini))
    esperado = {'SDA': 'D2', 'SCL': 'D1', 'MEASURE': BOTOES['MEDIR'][2],
                'PLUS': BOTOES['MAIS (+)'][2], 'MINUS': BOTOES['MENOS (−)'][2],
                'SELECT': BOTOES['SELECIONAR'][2], 'CALC': BOTOES['CALCULAR'][2]}
    assert pinos == esperado, f'desenho {esperado} != firmware {pinos}'


# ── Desenho principal ────────────────────────────────────────────────────────
def pecas(t):
    # Placa
    t.caixa(600, 140, 1000, 860, (36, 90, 170))
    t.caixa(720, 100, 880, 190, (190, 190, 190))
    t.texto(800, 145, 'USB', 30)
    t.texto(800, 400, 'Wemos', 38, (255, 255, 255))
    t.texto(800, 450, 'D1 mini', 38, (255, 255, 255))
    t.texto(800, 520, 'chips para cima', 22, (210, 225, 255), negrito=False)
    t.caixa(650, 760, 950, 845, (28, 70, 135), raio=6)
    t.texto(800, 802, 'antena', 24, (210, 225, 255))
    for lado, lista, x, ancora, dx in (('e', ESQ, 600, 'lm', 28), ('d', DIR, 1000, 'rm', -28)):
        for (nome, gpio), y in zip(lista, Y_PINOS):
            t.bola(x, y, 15, (245, 200, 60), TINTA, 3)
            t.texto(x + dx, y - (10 if gpio else 0), nome, 30, (255, 255, 255), ancora)
            if gpio:
                t.texto(x + dx, y + 20, f'({gpio})', 18, (190, 210, 255), ancora)
    # Trilhas da protoboard
    t.linha([(60, 215), (60, Y_GND), (1500, Y_GND), (1500, 340)], TRILHA_AZUL, 30)
    t.linha([(200, Y_VCC), (1570, Y_VCC)], TRILHA_VERMELHA, 30)
    t.texto(790, Y_GND - 34, 'trilha AZUL  (−)  = GND', 26, CORES['azul'])
    t.texto(790, Y_VCC - 34, 'trilha VERMELHA  (+)  = 3V3', 26, CORES['vermelho'])
    # Botões
    for nome, (x, y, pino, _) in BOTOES.items():
        t.caixa(x - 75, y - 60, x + 75, y + 60, (225, 225, 225))
        t.bola(x, y - 8, 30, (60, 60, 60))
        t.texto(x, y + 42, nome, 18)
        for p in (perna_sinal(nome), perna_gnd(nome)):
            t.bola(*p, 13, (245, 200, 60), TINTA, 3)
    # Tela
    t.caixa(180, Y_MOD, 640, 1480, (25, 60, 130))
    t.caixa(215, 1270, 605, 1445, (10, 10, 20))
    t.texto(410, 1335, 'TELA (OLED)', 32, (255, 255, 255))
    t.texto(410, 1385, 'SSD1306', 24, (180, 200, 255))
    for nome, x in zip(('VCC', 'GND', 'SCL', 'SDA'), (260, 340, 420, 500)):
        t.bola(x, Y_MOD, 14, (245, 200, 60), TINTA, 3)
        t.texto(x, Y_MOD + 42, nome, 24, (255, 255, 255))
    # Sensor
    t.caixa(900, Y_MOD, 1360, 1480, (25, 60, 130))
    t.caixa(1090, 1300, 1170, 1370, (30, 30, 30), raio=6)
    t.texto(1130, 1420, 'SENSOR DE LUZ (BH1750)', 24, (255, 255, 255))
    for nome, x in zip(('VCC', 'GND', 'SCL', 'SDA', 'ADDR'), (960, 1040, 1120, 1200, 1280)):
        t.bola(x, Y_MOD, 14, (245, 200, 60), TINTA, 3)
        t.texto(x, Y_MOD + 42, nome, 22, (255, 255, 255))


def desenhar(passo, nome_arquivo, titulo):
    """passo=None desenha tudo colorido."""
    t = Tela(1620, 1560)
    pecas(t)
    antigos = [f for f in FIOS if passo is not None and f[0] < passo]
    novos = [f for f in FIOS if passo is None or f[0] == passo]
    for _, _, caminho, *_ in antigos:
        t.linha(caminho, APAGADO, 7)
    for _, cor, caminho, *_ in novos:
        t.linha(caminho, (255, 255, 255), 17)  # contorno: separa cruzamentos
        t.linha(caminho, CORES[cor], 9)
    # Bolinhas: onde o fio realmente se liga a uma trilha ou a outro fio.
    for _, cor, caminho, *_ in novos:
        for ponto in (caminho[0], caminho[-1]):
            if ponto[1] in (Y_GND, Y_VCC, 1070, 1120) or ponto[0] in (60, 1500):
                t.bola(*ponto, 13, CORES[cor])
    # Pontas dos fios ficam por cima das peças.
    for _, cor, caminho, *_ in novos:
        for ponto in (caminho[0], caminho[-1]):
            t.bola(*ponto, 10, CORES[cor])
    if passo is not None:
        for i, (_, cor, caminho, *_) in enumerate(novos, start=1):
            if passo in (3, 4):  # fios para as peças: número junto ao pino
                t.numero(caminho[-1][0], 1153, i, CORES[cor])
                continue
            a, b = max(zip(caminho, caminho[1:]),
                       key=lambda s: abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))
            t.numero((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, i, CORES[cor])
    t.texto(810, 1520, titulo, 40)
    t.salvar(nome_arquivo)


def como_protoboard():
    t = Tela(1500, 760)
    t.texto(375, 45, 'Furos ligados por dentro', 36)
    for linha in range(5):
        y = 140 + linha * 70
        for grupo, x0, cor in ((0, 110, (150, 215, 160)), (1, 420, (160, 190, 240))):
            t.caixa(x0 - 25, y - 22, x0 + 4 * 55 + 25, y + 22, cor, cor)
            for c in range(5):
                t.bola(x0 + c * 55, y, 11, (50, 50, 50))
        t.texto(45, y, str(linha + 1), 24)
    t.caixa(370, 105, 380, 455, (180, 180, 180), (180, 180, 180), raio=2)
    t.texto(375, 520, 'Os 5 furos da mesma fileira, do', 28)
    t.texto(375, 560, 'mesmo lado, são um fio só.', 28)
    t.texto(375, 620, 'Para ligar num pino, enfie o jumper', 26, negrito=False)
    t.texto(375, 655, 'em outro furo da mesma fileira.', 26, negrito=False)
    t.texto(375, 710, 'O vão do meio NÃO liga os lados.', 28, CORES['vermelho'])

    t.d.line([(760 * S, 30 * S), (760 * S, 730 * S)], fill=APAGADO, width=4 * S)
    t.texto(1130, 45, 'Como ligar um botão', 36)
    t.caixa(1115, 120, 1145, 520, (200, 200, 200), (200, 200, 200), raio=2)
    t.texto(1130, 100, 'vão do meio', 20, negrito=False)
    t.caixa(1010, 220, 1250, 420, (225, 225, 225))
    t.bola(1130, 320, 55, (60, 60, 60))
    usadas = {(960, 245): CORES['laranja'], (1300, 395): CORES['preto']}
    for p in ((960, 245), (1300, 245), (960, 395), (1300, 395)):
        t.linha([(p[0], p[1]), (1010 if p[0] < 1130 else 1250, p[1])], (140, 140, 140), 8)
        cor = usadas.get(p)
        t.bola(*p, 20, cor or (255, 255, 255), TINTA, 3)
    t.linha([(960, 245), (830, 245)], CORES['laranja'], 9)
    t.linha([(1300, 395), (1440, 395)], CORES['preto'], 9)
    t.texto(870, 205, 'ao pino', 26, CORES['laranja'])
    t.texto(1390, 440, 'ao GND', 26)
    t.texto(1130, 560, 'Use DUAS pernas na DIAGONAL.', 30)
    t.texto(1130, 610, 'As outras duas ficam sem fio.', 28, negrito=False)
    t.texto(1130, 660, 'Botão sempre "apertado"?', 26, negrito=False)
    t.texto(1130, 695, 'Gire-o um quarto de volta.', 26, negrito=False)
    t.salvar('00-protoboard-e-botao.png')


def bateria():
    t = Tela(1820, 1010)
    t.texto(910, 40, 'Energia por bateria  (NUNCA TESTADO · só com um adulto)', 36,
            CORES['vermelho'])

    def peca(x1, y1, x2, y2, nome, sub=''):
        t.caixa(x1, y1, x2, y2, (220, 230, 245))
        t.texto((x1 + x2) / 2, (y1 + y2) / 2 - (18 if sub else 0), nome, 30)
        if sub:
            t.texto((x1 + x2) / 2, (y1 + y2) / 2 + 24, sub, 22, negrito=False)

    def ponto(x, y, rotulo, dx=0, dy=0, ancora='mm'):
        t.bola(x, y, 14, (245, 200, 60), TINTA, 3)
        t.texto(x + dx, y + dy, rotulo, 24, TINTA, ancora)

    def cabo(cor, caminho, n):
        t.linha(caminho, (255, 255, 255), 17)
        t.linha(caminho, CORES[cor], 9)
        a, b = max(zip(caminho, caminho[1:]),
                   key=lambda s: abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))
        t.numero((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, n, CORES[cor])

    peca(60, 300, 300, 640, 'PILHA', '14500 Li-ion')
    peca(480, 300, 760, 640, 'CARREGADOR', '500 mA, com proteção')
    peca(960, 110, 1180, 230, 'CHAVE', 'liga / desliga')
    peca(1000, 420, 1240, 720, 'CONVERSOR', 'saída 5,0 V')
    peca(1620, 420, 1770, 720, 'D1 mini')

    cabo('vermelho', [(300, 360), (480, 360)], 1)
    cabo('preto', [(300, 580), (480, 580)], 2)
    cabo('laranja', [(760, 360), (860, 360), (860, 170), (960, 170)], 3)
    cabo('laranja', [(1180, 170), (1230, 170), (1230, 320), (940, 320), (940, 480), (1000, 480)], 4)
    cabo('preto', [(760, 580), (880, 580), (880, 660), (1000, 660)], 5)
    cabo('vermelho', [(1240, 480), (1365, 480)], 6)
    cabo('vermelho', [(1495, 480), (1620, 480)], 7)
    cabo('preto', [(1240, 660), (1620, 660)], 8)
    # Diodo: a listra aponta para o D1 mini.
    t.caixa(1360, 455, 1500, 505, (35, 35, 35), raio=8)
    t.caixa(1462, 457, 1482, 503, (225, 225, 225), (225, 225, 225), esp=1, raio=1)
    t.texto(1430, 545, 'diodo 1N5819', 24)
    t.texto(1430, 580, 'LISTRA virada', 24)
    t.texto(1430, 615, 'para o D1 mini', 24)

    ponto(300, 360, '+', -30, 0)
    ponto(300, 580, '−', -30, 0)
    ponto(480, 360, 'B+', 40, 34)
    ponto(480, 580, 'B−', 40, -34)
    ponto(760, 360, 'OUT+', -55, 34)
    ponto(760, 580, 'OUT−', -55, -34)
    ponto(960, 170, '')
    ponto(1180, 170, '')
    ponto(1000, 480, 'IN+', 45, -28)
    ponto(1000, 660, 'IN−', 45, 28)
    ponto(1240, 480, 'OUT+', -55, -28)
    ponto(1240, 660, 'OUT−', -60, 28)
    ponto(1620, 480, '5V', 40, 0)
    ponto(1620, 660, 'G', 36, 0)

    t.texto(60, 800, 'Antes de encaixar o D1 mini: ligue a chave e meça a saída do conversor. Tem de dar 5,0 V.', 28, ancora='lm')
    t.texto(60, 855, 'Chave DESLIGADA para carregar e para plugar o USB do D1 mini.', 28, ancora='lm')
    t.texto(60, 910, 'Pilha invertida ou fios encostando podem causar fogo.', 28, CORES['vermelho'], 'lm')
    t.texto(60, 965, 'Opcional (já previsto na placa): resistor de 100 k entre o fio 4 e o pino A0.', 24, ancora='lm', negrito=False)
    t.salvar('10-bateria.png')


if __name__ == '__main__':
    conferir_com_firmware()
    como_protoboard()
    desenhar(None, '00-tudo.png', 'Tudo ligado')
    for n, titulo in TITULOS.items():
        desenhar(n, f'{n:02d}-passo.png', titulo)
    bateria()
    # Lista de fios por passo, para conferir o texto do guia.
    for passo, cor, _, de, ate in FIOS:
        print(passo, cor, '|', de, '->', ate)
