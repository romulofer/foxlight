#!/usr/bin/env python3
"""Gera hardware/imagens/rev2_tela.png com as telas desenhadas pelo firmware.

Uso, na raiz do projeto:  python3 tools/tela/gerar.py
Precisa de g++, Pillow e da biblioteca "Adafruit GFX Library" do Arduino.
"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[2]
GFX = Path.home() / 'Arduino' / 'libraries' / 'Adafruit_GFX_Library'
TITULOS = ['Calcula o tempo', 'Calcula a abertura', 'Calcula o ISO', 'Ao ligar']
ESCALA, MARGEM = 4, 20


def main():
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / 'simulador'
        subprocess.run(['g++', '-std=c++11', '-Wall', '-I', str(GFX), '-o', str(exe),
                        str(RAIZ / 'tools' / 'tela' / 'simulador.cpp')], check=True)
        saida = subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout

    telas = []
    for bloco in saida.split('P1\n')[1:]:
        pontos = bloco.split()[2:]
        im = Image.new('RGB', (128, 64), (8, 10, 16))
        im.putdata([(150, 220, 255) if p == '1' else (8, 10, 16) for p in pontos])
        telas.append(im.resize((128 * ESCALA, 64 * ESCALA), Image.NEAREST))

    L, A = 128 * ESCALA, 64 * ESCALA
    folha = Image.new('RGB', (2 * L + 3 * MARGEM, 2 * (A + 36) + 3 * MARGEM), (245, 245, 240))
    d = ImageDraw.Draw(folha)
    fonte = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    for i, (titulo, tela) in enumerate(zip(TITULOS, telas)):
        x = MARGEM + (i % 2) * (L + MARGEM)
        y = MARGEM + (i // 2) * (A + 36 + MARGEM)
        d.text((x + L / 2, y + 12), titulo, font=fonte, fill=(30, 30, 30), anchor='mm')
        folha.paste(tela, (x, y + 36))
    destino = RAIZ / 'hardware' / 'imagens' / 'rev2_tela.png'
    folha.save(destino, optimize=True)
    print(destino.relative_to(RAIZ))


if __name__ == '__main__':
    main()
