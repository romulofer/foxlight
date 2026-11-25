#!/usr/bin/env python3
"""Gera a caixa de sapata da rev 2: STL para impressão e um desenho de prévia.

Uso, na raiz do projeto:
    pip install manifold3d numpy pillow matplotlib
    python3 tools/caixa/gerar.py

O aparelho fica deitado sobre a câmera: tela para cima, sensor para a frente.

Coordenadas de desenho: as da placa vista de cima (x para a direita, y para
trás, na direção do fotógrafo, a partir do canto da frente à esquerda). z = 0 é
a face de baixo da placa e cresce para cima. Medidas em mm. Esse sistema é
"canhoto": tudo é espelhado em y (função `mundo`) antes de salvar ou desenhar.
"""
import struct
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, FillRule, Manifold
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / 'hardware' / 'caixa'

# ── Placa (hardware/kicad_rev2) ──────────────────────────────────────────────
PLACA_L, PLACA_P, PLACA_E = 50.0, 48.0, 1.6
FUROS_PLACA = ((3.0, 45.0), (47.0, 45.0))
BOTOES_TRAS_X = (13.5, 25.0, 36.5)      # ◄, OK, ►
BOTOES_LADO_Y = 28.0                    # Medir (esquerda) e Calcular (direita)
XIAO_Y = 28.0                           # centro da XIAO; USB na borda direita
# Botão C&K PTS645 de 90°, haste 9,5 mm (medido no modelo 3D do KiCad).
BOTAO_EIXO_Z = PLACA_E + 3.5            # centro da haste
BOTAO_TOPO_Z = PLACA_E + 7.0            # topo do corpo
BOTAO_PONTA = 5.0                       # quanto a haste passa da borda da placa

# ── Medidas ESTIMADAS: conferir nas peças antes de imprimir a versão final ──
JANELA_TELA = (12.5, 5.5, 37.5, 20.5)   # x1, y1, x2, y2
SENSOR_X = (15.75, 34.25)               # GY-302 em pé, atrás da parede da frente
SENSOR_Z = (-7.95, 5.95)
SENSOR_CHIP = (25.0, -1.0)              # centro do chip BH1750: x, z
USB_Z = -5.3                            # centro do conector USB-C

# ── Caixa ────────────────────────────────────────────────────────────────────
FOLGA = 0.35
PAREDE = 1.8
TAMPO = 1.5
VAO_SENSOR = 6.5                        # espaço do sensor à frente da placa
Z_BAIXO, Z_CIMA = -8.4, 9.0             # faces internas de baixo e de cima
Z_MIN, Z_MAX = Z_BAIXO - TAMPO, Z_CIMA + TAMPO
Z_CORTE = BOTAO_EIXO_Z                  # separa base e tampa

IN_X1, IN_X2 = -FOLGA, PLACA_L + FOLGA
IN_Y1, IN_Y2 = -VAO_SENSOR, PLACA_P + FOLGA
OUT_X1, OUT_X2 = IN_X1 - PAREDE, IN_X2 + PAREDE
OUT_Y1, OUT_Y2 = IN_Y1 - PAREDE, IN_Y2 + PAREDE

# Parafusos M2 x 14, de baixo para cima, rosqueando direto no plástico.
PARAFUSOS = ((3.0, -3.0), (47.0, -3.0)) + FUROS_PLACA
COLUNA_R = 2.8
ASSENTO_Z = Z_MIN + 2.5                 # onde a cabeça apoia

# Moldura em volta do sensor: corta a luz do céu sem estreitar demais o campo.
MOLDURA_FORA, MOLDURA_DENTRO, MOLDURA_P = 12.0, 10.0, 2.5

# Pé para a sapata (ISO 518: aba de cerca de 18 mm). Ajuste à sua câmera.
PE_ABA_L, PE_ABA_C, PE_ABA_E = 18.0, 18.0, 1.8
PE_PESCOCO_L, PE_PESCOCO_E = 12.2, 2.0
PE_BASE_L, PE_BASE_E = 18.0, 1.8
PINOS_PE_X = (19.0, 31.0)
PE_Y = (OUT_Y1 + OUT_Y2) / 2
PORCA_CHAVE, PORCA_E = 11.3, 5.8        # porca 1/4"-20 (11,1 x 5,6) com folga


def caixa(x1, y1, z1, x2, y2, z2):
    return Manifold.cube((x2 - x1, y2 - y1, z2 - z1)).translate((x1, y1, z1))


def cilindro(x, y, z1, z2, raio):
    return Manifold.cylinder(z2 - z1, raio, circular_segments=48).translate((x, y, z1))


def arredondada(x1, y1, z1, x2, y2, z2, r):
    cantos = [cilindro(x, y, z1, z2, r)
              for x in (x1 + r, x2 - r) for y in (y1 + r, y2 - r)]
    return Manifold.batch_hull(cantos)


def moldura_xz(cx, cz, y1, y2, lado1, lado2):
    """Tronco de pirâmide ao longo de y, de um quadrado de lado1 ao de lado2."""
    def fatia(y, lado):
        m = lado / 2
        return caixa(cx - m, y - 0.005, cz - m, cx + m, y + 0.005, cz + m)
    return Manifold.batch_hull([fatia(y1, lado1), fatia(y2, lado2)])


def texto(frase, altura, x, y, giro=0):
    """Letras para rebaixar na face de cima, centradas em (x, y)."""
    fonte = FontProperties(family='DejaVu Sans', weight='bold')
    contornos = TextPath((0, 0), frase, size=altura, prop=fonte).to_polygons()
    todos = np.concatenate(contornos)
    meio = (todos.min(0) + todos.max(0)) / 2
    a = np.radians(giro)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    # y cresce para trás nas coordenadas de desenho: inverte para ler certo.
    prontos = [((c[:-1] - meio) @ rot.T) * (1, -1) + (x, y) for c in contornos]
    secao = CrossSection([p.tolist() for p in prontos], FillRule.EvenOdd)
    return Manifold.extrude(secao, 0.8).translate((0, 0, Z_MAX - 0.6))


def legendas():
    t = texto('foxlight', 5.0, 25.0, 31.0)
    t += texto('MEDIR', 2.6, 5.5, BOTOES_LADO_Y, 90)
    t += texto('CALC', 2.6, 44.5, BOTOES_LADO_Y, 90)
    for x, s in zip(BOTOES_TRAS_X, ('◀', 'OK', '▶')):
        t += texto(s, 2.8, x, 42.0)
    return t


def anel(folga_dentro, folga_fora, z1, z2):
    """Moldura em volta da cavidade, sem os cantos (ali ficam os parafusos)."""
    def r(f):
        return caixa(IN_X1 - f, IN_Y1 - f, z1, IN_X2 + f, IN_Y2 + f, z2)
    m = r(folga_fora) - r(folga_dentro)
    for x in (IN_X1, IN_X2):
        for y in (IN_Y1, IN_Y2):
            m -= caixa(x - 5, y - 5, z1 - 1, x + 5, y + 5, z2 + 1)
    return m


def aberturas():
    f = Manifold()
    # Janela da tela, com chanfro para fora.
    x1, y1, x2, y2 = JANELA_TELA
    f += Manifold.batch_hull([
        caixa(x1, y1, 7.1, x2, y2, Z_CIMA),
        caixa(x1 - 1.2, y1 - 1.2, Z_MAX, x2 + 1.2, y2 + 1.2, Z_MAX + 0.1)])
    # Sensor: abre de 6 mm por dentro para 8 mm por fora.
    cx, cz = SENSOR_CHIP
    f += moldura_xz(cx, cz, IN_Y1 + 0.1, OUT_Y1 - 0.01, 6.0, 8.0)
    # Botões: passagem das hastes. Na base o rasgo é aberto por cima, para a
    # placa descer.
    z1, z2 = BOTAO_EIXO_Z - 2.2, BOTAO_EIXO_Z + 2.2
    for x in BOTOES_TRAS_X:
        f += caixa(x - 2.2, IN_Y2 - 1.2, z1, x + 2.2, OUT_Y2 + 1, z2)
    y = BOTOES_LADO_Y
    f += caixa(OUT_X1 - 1, y - 2.2, z1, IN_X1 + 1.2, y + 2.2, z2)
    f += caixa(IN_X2 - 1.2, y - 2.2, z1, OUT_X2 + 1, y + 2.2, z2)
    # USB-C na lateral direita: cabe o corpo plástico do plugue.
    f += caixa(IN_X2 - 1.2, XIAO_Y - 6.4, USB_Z - 3.75,
               OUT_X2 + 1, XIAO_Y + 6.4, USB_Z + 3.75)
    # Canal por dentro da parede, para o conector descer junto com a placa.
    f += caixa(IN_X2 - 0.1, XIAO_Y - 4.8, USB_Z, IN_X2 + 0.95, XIAO_Y + 4.8,
               Z_CORTE + 2.2)
    # Furos cegos para os pinos do pé.
    for x in PINOS_PE_X:
        f += cilindro(x, PE_Y, Z_MIN - 0.1, Z_MIN + 1.2, 1.6)
    return f + legendas()


def montar():
    casca = arredondada(OUT_X1, OUT_Y1, Z_MIN, OUT_X2, OUT_Y2, Z_MAX, 4.0)
    casca -= caixa(IN_X1, IN_Y1, Z_BAIXO, IN_X2, IN_Y2, Z_CIMA)

    base = casca ^ caixa(-60, -60, -60, 120, 120, Z_CORTE)
    tampa = casca ^ caixa(-60, -60, Z_CORTE, 120, 120, 60)

    # Encaixe em degrau: veda a luz e alinha as duas metades.
    tampa -= anel(-0.01, 0.95, Z_CORTE - 0.01, Z_CORTE + 2.1)
    base += anel(0.0, 0.85, Z_CORTE - 0.1, Z_CORTE + 1.9)

    # Colunas dos parafusos. Atrás, a placa fica presa entre elas.
    for x, y in PARAFUSOS:
        tem_placa = (x, y) in FUROS_PLACA
        topo_base = 0.0 if tem_placa else PLACA_E
        base += cilindro(x, y, Z_BAIXO - 0.1, topo_base, COLUNA_R)
        tampa += cilindro(x, y, PLACA_E, Z_CIMA + 0.1, COLUNA_R)
    # Apoios da borda da frente da placa.
    for xa, xb in ((IN_X1 - 0.01, 1.4), (PLACA_L - 1.4, IN_X2 + 0.01)):
        base += caixa(xa, 0.2, Z_BAIXO - 0.1, xb, 4.0, 0.0)
        tampa += caixa(xa, 0.2, PLACA_E, xb, 4.0, Z_CIMA + 0.1)

    # Aro por dentro da janela, até quase encostar no vidro.
    x1, y1, x2, y2 = JANELA_TELA
    tampa += (caixa(x1 - 1.2, y1 - 1.2, 7.2, x2 + 1.2, y2 + 1.2, Z_CIMA + 0.1)
              - caixa(x1, y1, 0, x2, y2, 20))

    # Berço do sensor: o módulo entra por cima, entre dois trilhos.
    (sx1, sx2), (sz1, _) = SENSOR_X, SENSOR_Z
    for xa, xb in ((sx1 - 1.2, sx1 - 0.15), (sx2 + 0.15, sx2 + 1.2)):
        base += caixa(xa, IN_Y1 - 0.1, Z_BAIXO - 0.1, xb, -3.9, Z_CORTE - 0.2)
    for xa, xb in ((sx1 - 0.2, sx1 + 2.0), (sx2 - 2.0, sx2 + 0.2)):
        base += caixa(xa, IN_Y1 - 0.1, Z_BAIXO - 0.1, xb, IN_Y1 + 1.2, sz1 + 2.5)
        base += caixa(xa, IN_Y1 - 0.1, Z_BAIXO - 0.1, xb, -4.0, sz1 - 0.05)

    # Moldura do sensor, para fora da parede da frente.
    cx, cz = SENSOR_CHIP
    fora, dentro = MOLDURA_FORA / 2, MOLDURA_DENTRO / 2
    base += (caixa(cx - fora, OUT_Y1 - MOLDURA_P, cz - fora,
                   cx + fora, OUT_Y1 + 0.1, cz + fora)
             - caixa(cx - dentro, OUT_Y1 - 10, cz - dentro,
                     cx + dentro, OUT_Y1 + 0.1, cz + dentro))

    # Furos dos parafusos: passagem e assento na base, rosca na tampa.
    furos = aberturas()
    for x, y in PARAFUSOS:
        furos += cilindro(x, y, Z_MIN - 1, ASSENTO_Z, 2.2)
        furos += cilindro(x, y, ASSENTO_Z - 0.1, PLACA_E + 0.01, 1.2)
        furos += cilindro(x, y, PLACA_E - 0.01, Z_CIMA - 0.8, 0.85)
    return base - furos, tampa - furos


# ── Pés ──────────────────────────────────────────────────────────────────────
def _pinos(p, topo):
    meio = sum(PINOS_PE_X) / 2
    for x in PINOS_PE_X:
        p += cilindro(x - meio, 0, topo - 0.01, topo + 1.1, 1.45)
    return p


def pe_sapata():
    """Pé direto: aba embaixo (z = 0), colado sob a caixa."""
    def placa(largura, z1, z2):
        return caixa(-largura / 2, -PE_ABA_C / 2, z1, largura / 2, PE_ABA_C / 2, z2)

    z1, z2 = PE_ABA_E, PE_ABA_E + PE_PESCOCO_E
    z3 = z2 + PE_BASE_E
    p = placa(PE_ABA_L, 0, z1) + placa(PE_PESCOCO_L, z1 - 0.01, z2) \
        + placa(PE_BASE_L, z2 - 0.01, z3)
    return _pinos(p, z3)


def pe_porca():
    """Base com porca 1/4"-20 presa, para um adaptador de sapata comprado."""
    altura = PORCA_E + 1.7
    p = caixa(-10, -9, 0, 10, 9, altura)
    raio = PORCA_CHAVE / np.sqrt(3)
    p -= Manifold.cylinder(PORCA_E + 0.1, raio, circular_segments=6) \
        .translate((0, 0, altura - PORCA_E))
    p -= cilindro(0, 0, -1, altura, 3.4)
    return _pinos(p, altura)


def componentes():
    """Volumes ocupados pelas peças, para conferir que a caixa não os invade."""
    c = {
        'placa': caixa(0, 0, 0, PLACA_L, PLACA_P, PLACA_E),
        'barra da tela': caixa(19.9, 1.3, 1.6, 30.1, 3.7, 4.1),
        'placa da tela': caixa(11.35, 0.55, 4.1, 38.65, 28.35, 5.3),
        'vidro da tela': caixa(11.7, 4.5, 5.3, 38.3, 24.0, 7.0),
        'XIAO': caixa(28.5, XIAO_Y - 8.9, -3.7, 49.5, XIAO_Y + 8.9, -2.5),
        'USB': caixa(44.0, XIAO_Y - 4.5, -6.9, 51.1, XIAO_Y + 4.5, -3.7),
        'bateria': caixa(7.1, 4.8, -8.0, 27.1, 40.8, -0.5),
        'pinos da bateria': caixa(28.0, 8.0, -6.0, 30.0, 14.0, 0),
        'módulo do sensor': caixa(SENSOR_X[0], -5.3, SENSOR_Z[0],
                                  SENSOR_X[1], -4.1, SENSOR_Z[1]),
    }
    cx, cz = SENSOR_CHIP
    c['chip do sensor'] = caixa(cx - 1.6, -6.9, cz - 1.6, cx + 1.6, -5.3, cz + 1.6)
    for i, y in enumerate((9.0, 13.0, 17.0), 1):
        c[f'R{i}'] = caixa(32.5, y - 1.3, -2.8, 44.5, y + 1.3, 0)
    z1, z2 = PLACA_E, BOTAO_TOPO_Z
    e1, e2 = BOTAO_EIXO_Z - 1.6, BOTAO_EIXO_Z + 1.6
    for i, x in enumerate(BOTOES_TRAS_X, 1):
        c[f'botão de trás {i}'] = caixa(x - 3.7, PLACA_P - 7.7, z1,
                                        x + 3.7, PLACA_P - 0.75, z2)
        c[f'haste de trás {i}'] = caixa(x - 1.6, PLACA_P - 0.75, e1,
                                        x + 1.6, PLACA_P + BOTAO_PONTA, e2)
    y = BOTOES_LADO_Y
    c['botão Medir'] = caixa(0.75, y - 3.7, z1, 7.7, y + 3.7, z2)
    c['haste Medir'] = caixa(-BOTAO_PONTA, y - 1.6, e1, 0.75, y + 1.6, e2)
    c['botão Calcular'] = caixa(PLACA_L - 7.7, y - 3.7, z1, PLACA_L - 0.75, y + 3.7, z2)
    c['haste Calcular'] = caixa(PLACA_L - 0.75, y - 1.6, e1,
                                PLACA_L + BOTAO_PONTA, y + 1.6, e2)
    return c


def conferir(base, tampa):
    ruins = []
    for nome, peca in componentes().items():
        for parte, solido in (('base', base), ('tampa', tampa)):
            v = (solido ^ peca).volume()
            if v > 0.01:
                ruins.append(f'{parte} invade {nome}: {v:.2f} mm3')
    v = (base ^ tampa).volume()
    if v > 0.5:
        ruins.append(f'base e tampa se sobrepõem: {v:.2f} mm3')
    partes = (('base', base), ('tampa', tampa), ('pé', pe_sapata()),
              ('pé de porca', pe_porca()))
    for parte, solido in partes:
        n = len(solido.decompose())
        if n != 1:
            ruins.append(f'{parte} tem {n} pedaços soltos')
    return ruins


def mundo(solido):
    """Das coordenadas de desenho para as reais (y para a frente)."""
    return solido.mirror((0, 1, 0))


def triangulos(solido):
    m = solido.to_mesh()
    return np.asarray(m.vert_properties)[:, :3][np.asarray(m.tri_verts)]


def salvar_stl(solido, nome):
    solido = solido.translate((0, 0, -solido.bounding_box()[2]))
    t = triangulos(solido)
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    with open(SAIDA / nome, 'wb') as f:
        f.write(b'foxlight'.ljust(80, b'\0') + struct.pack('<I', len(t)))
        for normal, tri in zip(n, t):
            f.write(struct.pack('<12fH', *normal, *tri.ravel(), 0))


# ── Prévia ───────────────────────────────────────────────────────────────────
def desenhar(pecas, giro, elevacao, tam=(600, 480), escala=6.0):
    """Projeção ortográfica com z-buffer. `pecas`: lista de (sólido, cor).

    Com giro 0 a câmera está atrás do aparelho (lugar do fotógrafo).
    """
    S = 2
    L, A = tam[0] * S, tam[1] * S
    cor_img = np.full((A, L, 3), 250, dtype=np.uint8)
    fundo = np.full((A, L), -1e9)
    g, e = np.radians(giro), np.radians(elevacao)
    de_pe = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])
    ry = np.array([[np.cos(g), 0, np.sin(g)], [0, 1, 0], [-np.sin(g), 0, np.cos(g)]])
    rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    rot = rx @ ry @ de_pe
    prontas = [(triangulos(mundo(s)), cor) for s, cor in pecas]
    todos = np.concatenate([t.reshape(-1, 3) for t, _ in prontas])
    centro = (todos.min(0) + todos.max(0)) / 2
    luz = np.array([-0.35, 0.65, 0.68])
    luz /= np.linalg.norm(luz)
    for t, cor in prontas:
        for tri in (t - centro) @ rot.T:
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


def previa(base, tampa):
    corpo, escuro, tinta = (105, 110, 120), (45, 45, 50), (235, 235, 230)
    meio = sum(PINOS_PE_X) / 2
    altura = PE_ABA_E + PE_PESCOCO_E + PE_BASE_E
    pe = pe_sapata().translate((meio, PE_Y, Z_MIN - altura))
    hastes = Manifold()
    for nome, peca in componentes().items():
        if nome.startswith('haste'):
            hastes += peca
    x1, y1, x2, y2 = JANELA_TELA
    tela = caixa(x1, y1, 6.8, x2, y2, 7.0)
    # Preenchimento claro dos rebaixos, só para o texto aparecer no desenho.
    letras = legendas() ^ caixa(-60, -60, Z_MAX - 0.6, 120, 120, Z_MAX - 0.1)
    montado = [(base, corpo), (tampa, corpo), (pe, escuro), (hastes, escuro),
               (tela, (30, 60, 110)), (letras, tinta)]
    vistas = [
        ('Visto pelo fotógrafo', desenhar(montado, -30, 38)),
        ('Visto pela frente (sensor)', desenhar(montado, 155, 22)),
        ('Base aberta', desenhar([(base, corpo)], -25, 52)),
        ('Tampa, por dentro', desenhar([(tampa, corpo)], -25, -55)),
    ]
    fonte = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    folha = Image.new('RGB', (1200, 960), (250, 250, 250))
    d = ImageDraw.Draw(folha)
    for i, (titulo, im) in enumerate(vistas):
        x, y = (i % 2) * 600, (i // 2) * 480
        folha.paste(im, (x, y))
        d.text((x + 300, y + 22), titulo, font=fonte, fill=(30, 30, 30), anchor='mm')
    folha.save(SAIDA / 'previa.png', optimize=True)


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    base, tampa = montar()
    ruins = conferir(base, tampa)
    for r in ruins:
        print('PROBLEMA:', r)
    # Posição de impressão: base sobre o fundo, tampa sobre a face de cima, pé
    # de sapata de lado e pé de porca sobre a face de baixo.
    salvar_stl(mundo(base), 'caixa_base.stl')
    salvar_stl(mundo(tampa).rotate((180, 0, 0)), 'caixa_tampa.stl')
    salvar_stl(pe_sapata().rotate((90, 0, 0)), 'pe_sapata.stl')
    salvar_stl(pe_porca(), 'pe_porca_1-4.stl')
    previa(base, tampa)
    print(f'caixa: {OUT_X2 - OUT_X1:.1f} x {OUT_Y2 - OUT_Y1:.1f} x {Z_MAX - Z_MIN:.1f} mm '
          f'(largura x profundidade x altura), mais {MOLDURA_P} mm da moldura '
          f'do sensor e o pé')
    raise SystemExit(1 if ruins else 0)


if __name__ == '__main__':
    main()
