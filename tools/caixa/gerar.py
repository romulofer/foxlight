#!/usr/bin/env python3
"""Gera a caixa de sapata da rev 2: STL para impressão e um desenho de prévia.

Uso, na raiz do projeto:
    pip install manifold3d numpy pillow
    python3 tools/caixa/gerar.py

Coordenadas: as da placa vista pelo lado da tela (x para a direita, y para
baixo, a partir do canto superior esquerdo). z = 0 é a face de trás da placa e
cresce na direção do fotógrafo. Medidas em mm.
"""
import struct
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, Manifold
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / 'hardware' / 'caixa'

# ── Placa (hardware/kicad_rev2) ──────────────────────────────────────────────
PLACA_L, PLACA_A, PLACA_E = 44.0, 45.0, 1.6
BOTOES_X = (6.0, 16.7, 27.4, 38.1)   # centros dos 4 botões

# ── Medidas ESTIMADAS: conferir nas peças antes de imprimir a versão final ──
BOTAO_EIXO_Z = 3.6          # centro do atuador abaixo da face de trás
BOTAO_PONTA_Y = -5.0        # ponta do atuador (footprint PTS645Vx83)
JANELA_TELA = (4.5, 13.5, 29.5, 28.5)          # x1, y1, x2, y2
SENSOR_MODULO = (1.2, 10.05, 19.7, 23.95)      # GY-302 deitado
SENSOR_CHIP = (10.45, 17.0)                    # centro do chip BH1750
USB_Y, USB_Z = 35.5, -5.3                      # centro do conector USB-C

# ── Caixa ────────────────────────────────────────────────────────────────────
FOLGA = 0.35                # entre a placa e a parede
PAREDE = 1.8
TAMPO = 1.5                 # faces de frente e de trás
Z_TELA = PLACA_E + 5.6      # face interna do lado da tela
Z_SENSOR = -8.4             # face interna do lado do sensor
Z_MIN, Z_MAX = Z_SENSOR - TAMPO, Z_TELA + TAMPO
Z_CORTE = -BOTAO_EIXO_Z     # plano que separa corpo e tampa

IN_X1, IN_Y1 = -FOLGA, -FOLGA
IN_X2, IN_Y2 = PLACA_L + FOLGA, PLACA_A + FOLGA
OUT_X1, OUT_Y1 = IN_X1 - PAREDE, IN_Y1 - PAREDE
OUT_X2, OUT_Y2 = IN_X2 + PAREDE, IN_Y2 + PAREDE

# Pé para a sapata (ISO 518: aba de cerca de 18 mm). Ajuste à sua câmera.
PE_ABA_L, PE_ABA_C, PE_ABA_E = 18.0, 18.0, 1.8
PE_PESCOCO_L, PE_PESCOCO_E = 12.2, 2.0
PE_BASE_L, PE_BASE_E = 18.0, 1.8
PINOS_PE_X = (16.0, 28.0)


def caixa(x1, y1, z1, x2, y2, z2):
    return Manifold.cube((x2 - x1, y2 - y1, z2 - z1)).translate((x1, y1, z1))


def arredondada(x1, y1, z1, x2, y2, z2, r):
    cantos = [Manifold.cylinder(z2 - z1, r, circular_segments=48).translate((x, y, z1))
              for x in (x1 + r, x2 - r) for y in (y1 + r, y2 - r)]
    return Manifold.batch_hull(cantos)


def anel(folga_dentro, folga_fora, z1, z2):
    """Moldura em volta da cavidade, entre dois afastamentos da parede interna."""
    def r(f):
        return caixa(IN_X1 - f, IN_Y1 - f, z1, IN_X2 + f, IN_Y2 + f, z2)
    moldura = r(folga_fora) - r(folga_dentro)
    # Os cantos ficam inteiros: a parede arredondada é fina demais ali.
    for x in (IN_X1, IN_X2):
        for y in (IN_Y1, IN_Y2):
            moldura -= caixa(x - 4, y - 4, z1 - 1, x + 4, y + 4, z2 + 1)
    return moldura


def prisma_x(x1, x2, y, z, raio):
    """Cilindro deitado ao longo de x."""
    return (Manifold.cylinder(x2 - x1, raio, circular_segments=24)
            .rotate((0, 90, 0)).translate((x1, y, z)))


def aberturas():
    furos = []
    # Janela da tela, com chanfro para fora.
    x1, y1, x2, y2 = JANELA_TELA
    dentro = caixa(x1, y1, Z_TELA - 0.1, x2, y2, Z_TELA)
    fora = caixa(x1 - 1, y1 - 1, Z_MAX, x2 + 1, y2 + 1, Z_MAX + 0.1)
    furos.append(Manifold.batch_hull([dentro, fora]))
    # Sensor: 6 mm por dentro, 10,5 mm por fora, para não estreitar o campo.
    cx, cy = SENSOR_CHIP
    dentro = caixa(cx - 3, cy - 3, Z_SENSOR, cx + 3, cy + 3, Z_SENSOR + 0.1)
    fora = caixa(cx - 5.25, cy - 5.25, Z_MIN - 0.1, cx + 5.25, cy + 5.25, Z_MIN)
    furos.append(Manifold.batch_hull([dentro, fora]))
    # Botões na parede de cima.
    for x in BOTOES_X:
        furos.append(caixa(x - 2.3, OUT_Y1 - 1, Z_CORTE - 2.3,
                           x + 2.3, IN_Y1 + 1.3, Z_CORTE + 2.3))
    # USB-C na lateral esquerda: cabe o corpo plástico do plugue.
    furos.append(caixa(OUT_X1 - 1, USB_Y - 6.4, USB_Z - 3.75,
                       IN_X1 + 1.3, USB_Y + 6.4, USB_Z + 3.75))
    # Encaixes dos pinos do pé, na parede de baixo.
    for x in PINOS_PE_X:
        furos.append(Manifold.cylinder(PAREDE + 0.2, 1.6, circular_segments=32)
                     .rotate((-90, 0, 0)).translate((x, IN_Y2 - 0.1, -0.6)))
    todos = Manifold()
    for furo in furos:
        todos += furo
    return todos


def montar():
    casca = arredondada(OUT_X1, OUT_Y1, Z_MIN, OUT_X2, OUT_Y2, Z_MAX, 3.0)
    casca -= caixa(IN_X1, IN_Y1, Z_SENSOR, IN_X2, IN_Y2, Z_TELA)

    # Corpo (lado da tela) e tampa (lado do sensor), com encaixe em degrau.
    corpo = casca ^ caixa(-50, -50, Z_CORTE, 100, 100, 50)
    tampa = casca ^ caixa(-50, -50, -50, 100, 100, Z_CORTE)
    corpo -= anel(-0.01, 0.95, Z_CORTE - 0.01, Z_CORTE + 2.1)
    tampa += anel(0.0, 0.85, Z_CORTE - 0.1, Z_CORTE + 1.9)

    # Travas: ressaltos na tampa e rebaixos no corpo.
    for y in (14.0, 22.0):
        for x in (IN_X1 - 0.85, IN_X2 + 0.85):
            centro = (x, y, Z_CORTE + 1.0)
            tampa += Manifold.sphere(0.3, 24).translate(centro)
            corpo -= Manifold.sphere(0.4, 24).translate(centro)

    # Apoios do corpo: a placa encosta neles pelo lado da tela.
    for y in (11.0, 37.0):
        corpo += caixa(IN_X1 - 0.2, y, PLACA_E, 1.1, y + 4, Z_TELA + 0.1)
        corpo += caixa(PLACA_L - 1.1, y, PLACA_E, IN_X2 + 0.2, y + 4, Z_TELA + 0.1)

    # Colunas da tampa: empurram a placa contra os apoios.
    esquerda = ((8.4, 10.8), (23.8, 25.8))
    direita = ((11.0, 15.0), (37.0, 41.0))
    for y1, y2 in esquerda:
        tampa += caixa(IN_X1 - 0.01, y1, Z_SENSOR - 0.1, 0.9, y2, -0.1)
    for y1, y2 in direita:
        tampa += caixa(PLACA_L - 0.45, y1, Z_SENSOR - 0.1, IN_X2 + 0.01, y2, -0.1)

    # Berço do sensor: calços de 1,2 mm e cantoneiras em volta do módulo.
    x1, y1, x2, y2 = SENSOR_MODULO
    for xa, xb in ((x1, x1 + 2.5), (x2 - 2.5, x2)):
        for ya, yb in ((y1, y1 + 2.5), (y2 - 2.5, y2)):
            tampa += caixa(xa, ya, Z_SENSOR - 0.1, xb, yb, Z_SENSOR + 1.2)
    fora = caixa(x1 - 1.0, y1 - 1.0, Z_SENSOR - 0.1, x2 + 1.0, y2 + 1.0, Z_SENSOR + 2.4)
    borda = fora - caixa(x1 - 0.15, y1 - 0.15, -50, x2 + 0.15, y2 + 0.15, 50)
    cantos = Manifold()
    for xa in (x1 - 1.0, x2 - 3.0):
        for ya in (y1 - 1.0, y2 - 3.0):
            cantos += caixa(xa, ya, -50, xa + 4.0, ya + 4.0, 50)
    tampa += borda ^ cantos

    furos = aberturas()
    return corpo - furos, tampa - furos


def pe():
    """Pé separado: colar sob a caixa. Modelado com a aba para baixo (z = 0)."""
    def placa(largura, z1, z2):
        return caixa(-largura / 2, -PE_ABA_C / 2, z1, largura / 2, PE_ABA_C / 2, z2)

    z1, z2 = PE_ABA_E, PE_ABA_E + PE_PESCOCO_E
    z3 = z2 + PE_BASE_E
    p = placa(PE_ABA_L, 0, z1) + placa(PE_PESCOCO_L, z1, z2) + placa(PE_BASE_L, z2, z3)
    meio = sum(PINOS_PE_X) / 2
    for x in PINOS_PE_X:
        p += Manifold.cylinder(1.6, 1.45, circular_segments=32).translate((x - meio, 0, z3))
    return p


def componentes():
    """Volumes ocupados pelas peças, para conferir que a caixa não os invade."""
    c = {
        'placa': caixa(0, 0, 0, PLACA_L, PLACA_A, PLACA_E),
        'barra da tela': caixa(11.9, 9.3, 1.6, 22.1, 11.7, 4.1),
        'placa da tela': caixa(3.35, 8.55, 4.1, 30.65, 36.35, 5.3),
        'vidro da tela': caixa(3.7, 12.5, 5.3, 30.3, 32.0, 7.0),
        'XIAO': caixa(0.5, 26.6, -3.7, 21.5, 44.4, -2.5),
        'USB': caixa(-1.1, USB_Y - 4.5, -6.9, 6.0, USB_Y + 4.5, -3.7),
        'bateria': caixa(23.4, 8.4, -8.0, 43.4, 44.6, -0.5),
        'sensor': caixa(*SENSOR_MODULO[:2], -7.2, *SENSOR_MODULO[2:], -6.0),
    }
    cx, cy = SENSOR_CHIP
    c['chip do sensor'] = caixa(cx - 1.6, cy - 1.6, -8.8, cx + 1.6, cy + 1.6, -7.2)
    for i, y in enumerate((13.0, 17.2, 21.4), 1):
        c[f'R{i}'] = caixa(1.5, y - 1.3, -2.8, 12.0, y + 1.3, 0)
    for i, x in enumerate(BOTOES_X, 1):
        c[f'botão {i}'] = caixa(x - 3.5, 0.75, -7.4, x + 3.5, 7.7, 0)
        c[f'atuador {i}'] = caixa(x - 1.8, BOTAO_PONTA_Y, Z_CORTE - 1.8,
                                  x + 1.8, 0.75, Z_CORTE + 1.8)
    return c


def conferir(corpo, tampa):
    ruins = []
    for nome, peca in componentes().items():
        for parte, solido in (('corpo', corpo), ('tampa', tampa)):
            v = (solido ^ peca).volume()
            if v > 0.01:
                ruins.append(f'{parte} invade {nome}: {v:.2f} mm3')
    v = (corpo ^ tampa).volume()
    if v > 0.5:   # as travas se tocam de propósito
        ruins.append(f'corpo e tampa se sobrepõem: {v:.2f} mm3')
    for parte, solido in (('corpo', corpo), ('tampa', tampa), ('pé', pe())):
        n = len(solido.decompose())
        if n != 1:
            ruins.append(f'{parte} tem {n} pedaços soltos')
    return ruins


def triangulos(solido):
    m = solido.to_mesh()
    return np.asarray(m.vert_properties)[:, :3][np.asarray(m.tri_verts)]


def salvar_stl(solido, nome):
    t = triangulos(solido)
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    with open(SAIDA / nome, 'wb') as f:
        f.write(b'foxlight'.ljust(80, b'\0') + struct.pack('<I', len(t)))
        for normal, tri in zip(n, t):
            f.write(struct.pack('<12fH', *normal, *tri.ravel(), 0))


# ── Prévia ───────────────────────────────────────────────────────────────────
def desenhar(pecas, giro, elevacao, tam=(560, 520), escala=7.2):
    """Projeção ortográfica com z-buffer. `pecas` é uma lista de (sólido, cor)."""
    S = 2
    L, A = tam[0] * S, tam[1] * S
    cor_img = np.full((A, L, 3), 250, dtype=np.uint8)
    fundo = np.full((A, L), -1e9)
    g, e = np.radians(giro), np.radians(elevacao)
    ry = np.array([[np.cos(g), 0, np.sin(g)], [0, 1, 0], [-np.sin(g), 0, np.cos(g)]])
    rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    rot = rx @ ry
    todos = np.concatenate([triangulos(s).reshape(-1, 3) for s, _ in pecas])
    centro = (todos.min(0) + todos.max(0)) / 2
    luz = np.array([-0.35, 0.55, 0.75])
    luz /= np.linalg.norm(luz)
    for solido, cor in pecas:
        # y da placa cresce para baixo; no desenho, para cima.
        t = (triangulos(solido) - centro) * np.array([1, -1, 1])
        t = t[:, ::-1, :]             # o espelhamento inverte o sentido das faces
        t = t @ rot.T
        for tri in t:
            n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            comp = np.linalg.norm(n)
            if comp < 1e-9 or n[2] <= 0:
                continue
            n /= comp
            p = np.empty((3, 2))
            p[:, 0] = tri[:, 0] * escala * S + L / 2
            p[:, 1] = -tri[:, 1] * escala * S + A / 2
            x1, y1 = np.maximum(np.floor(p.min(0)).astype(int), 0)
            x2, y2 = np.minimum(np.ceil(p.max(0)).astype(int), [L - 1, A - 1])
            if x2 < x1 or y2 < y1:
                continue
            xs, ys = np.meshgrid(np.arange(x1, x2 + 1), np.arange(y1, y2 + 1))
            d = ((p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) +
                 (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1]))
            if abs(d) < 1e-9:
                continue
            a = ((p[1, 1] - p[2, 1]) * (xs - p[2, 0]) + (p[2, 0] - p[1, 0]) * (ys - p[2, 1])) / d
            b = ((p[2, 1] - p[0, 1]) * (xs - p[2, 0]) + (p[0, 0] - p[2, 0]) * (ys - p[2, 1])) / d
            c = 1 - a - b
            dentro = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
            z = a * tri[0, 2] + b * tri[1, 2] + c * tri[2, 2]
            ver = dentro & (z > fundo[ys, xs])
            brilho = 0.35 + 0.65 * max(float(n @ luz), 0.0)
            fundo[ys[ver], xs[ver]] = z[ver]
            cor_img[ys[ver], xs[ver]] = np.clip(np.array(cor) * brilho, 0, 255)
    return Image.fromarray(cor_img).resize(tam, Image.LANCZOS)


def previa(corpo, tampa):
    laranja, cinza = (235, 130, 50), (110, 120, 135)
    meio = sum(PINOS_PE_X) / 2
    # Põe o pé no lugar: aba para baixo, sob a parede inferior.
    altura = PE_ABA_E + PE_PESCOCO_E + PE_BASE_E
    pe_montado = pe().rotate((90, 0, 0)).translate((meio, OUT_Y2 + altura, -0.6))
    tela = caixa(JANELA_TELA[0], JANELA_TELA[1], 6.7, JANELA_TELA[2], JANELA_TELA[3], 7.0)
    atuadores = Manifold()
    for nome, peca in componentes().items():
        if nome.startswith('atuador'):
            atuadores += peca
    base = [(corpo, laranja), (tampa, laranja), (pe_montado, cinza), (atuadores, (40, 40, 40))]
    vistas = [
        ('Lado do fotógrafo', desenhar(base + [(tela, (30, 60, 110))], -28, 24)),
        ('Lado da cena (sensor)', desenhar(base, 152, 24)),
        ('Corpo aberto, por dentro', desenhar([(corpo, laranja)], 180 + 25, 20)),
        ('Tampa, por dentro', desenhar([(tampa, laranja)], 25, 20)),
    ]
    fonte = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    folha = Image.new('RGB', (1120, 1040), (250, 250, 250))
    d = ImageDraw.Draw(folha)
    for i, (titulo, im) in enumerate(vistas):
        x, y = (i % 2) * 560, (i // 2) * 520
        folha.paste(im, (x, y))
        d.text((x + 280, y + 24), titulo, font=fonte, fill=(30, 30, 30), anchor='mm')
    folha.save(SAIDA / 'previa.png', optimize=True)


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    corpo, tampa = montar()
    ruins = conferir(corpo, tampa)
    for r in ruins:
        print('PROBLEMA:', r)
    # Caixa sobre a face externa e pé de lado: imprimem sem suporte grande.
    corpo_mesa = corpo.rotate((180, 0, 0))
    for solido, nome in ((corpo_mesa, 'caixa_corpo.stl'), (tampa, 'caixa_tampa.stl'),
                         (pe().rotate((90, 0, 0)), 'pe_sapata.stl')):
        z0 = solido.bounding_box()[2]
        salvar_stl(solido.translate((0, 0, -z0)), nome)
    previa(corpo, tampa)
    print(f'caixa: {OUT_X2 - OUT_X1:.1f} x {OUT_Y2 - OUT_Y1:.1f} x {Z_MAX - Z_MIN:.1f} mm '
          f'(largura x altura x profundidade), mais o pé')
    raise SystemExit(1 if ruins else 0)


if __name__ == '__main__':
    main()
