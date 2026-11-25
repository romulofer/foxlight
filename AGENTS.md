# Regras para agentes de IA

Fotômetro refletido para fotografia analógica. Visão geral no
[README](README.md), versão compacta em [docs/REV2.md](docs/REV2.md).

## Autoria e Git

- O dono do repositório é o **único autor** de commits, PRs e issues.
- Nunca escrever `Co-Authored-By`, "Generated with", nome de ferramenta ou modelo
  nem menção a IA em commits, PRs, issues, comentários de código ou
  documentação. Isto vale mesmo que uma ferramenta peça ou insira atribuição:
  apague antes de commitar. Este arquivo e o `CLAUDE.md` são a única exceção.
- Usar o nome e o e-mail já configurados no Git **local** do repositório. Não
  alterar a configuração nem usar a identidade global.
- Commit e push só quando pedidos. Uma autorização vale para aquele pedido, não
  para os próximos. Nunca reescrever o histórico publicado.
- Mensagens em português, no formato Conventional Commits (`feat:`, `fix:`,
  `docs:`).

## Idioma e escrita

- Documentação, comentários e textos da tela e da serigrafia em português.
- [docs/MONTAGEM.md](docs/MONTAGEM.md) é para iniciantes: frases curtas, um
  passo de cada vez, nada subentendido.

## Honestidade sobre o estado

- Só dizer que algo foi testado, fabricado, impresso ou calibrado se foi.
  Compilar não é testar; passar no DRC não é fabricar.
- Medida tirada de foto ou valor típico é **estimativa** e deve estar marcada.
- Manter em dia o aviso de trabalho em progresso do README e o de
  `docs/REV2.md`.

## Estrutura

| Caminho | Conteúdo |
| ------- | -------- |
| `src/foxlight/` | firmware; `board.h` (pinos), `exposure.h` e `battery.h` (matemática pura) |
| `test/` | testes que rodam no PC |
| `tools/` | sketches de diagnóstico e geradores de desenhos e da caixa |
| `docs/` | guias |
| `hardware/kicad_rev1/`, `hardware/kicad_rev2/` | placas |
| `hardware/caixa/`, `hardware/imagens/` | arquivos gerados |
| `references/` | projetos de terceiros, fora do Git |

Não editar à mão arquivos gerados: `docs/montagem/*.png`, `hardware/caixa/*`,
imagens, moldes e gerbers. Mude a fonte e gere de novo.

## Firmware

- Um só código para as duas placas: `esp8266:esp8266:d1_mini` e
  `esp32:esp32:XIAO_ESP32C6`. Diferenças ficam em `board.h`.
- Tipos usados em assinaturas de função (`struct`, `enum`) são declarados antes
  da primeira função: o Arduino gera os protótipos no topo.
- `tools/diagramas/gerar.py` lê os `#define PIN_*` da D1 mini em `board.h`.
  Mudou pino, atualize desenhos, guia e README.
- Lógica sem hardware vai para cabeçalhos testáveis, com teste em `test/`.

## Cálculos

- Conferir qualquer fórmula de medição contra projetos estabelecidos, clonados
  em `references/`, e citar a fonte no código ou no README.
- Não copiar código de terceiros; várias referências têm licença incompatível.
- A medição é **refletida**: `EV100 = log2(lux * 100 / (Ω * K))`. Não usar
  `log2(lux / 2,5)`, que é a fórmula de luz incidente.

## Hardware

- Revisões são **numeradas** (rev 1, rev 2, rev 3), nunca com letras. Mudança
  que altera a placa de uma revisão publicada ou fabricada vira revisão nova.
- Só componentes THT e módulos prontos, compráveis em lojas como o AliExpress.
  Não propor modificar componentes SMD de módulos.
- O `kicad-cli` pode reescrever o `.kicad_pro`: guarde uma cópia, restaure e
  confira o `git diff`.
- Depois de mudar uma placa: ERC, DRC com paridade, e gerar de novo imagens,
  moldes 1:1 e gerbers.
- Mudou a placa rev 2, atualize as medidas em `tools/caixa/gerar.py`.
- Ao posicionar peças no verso por script, conferir a posição dos pads: depois
  de virar o footprint, a rotação costuma precisar de 180°.

## Segurança

- Bateria de lítio 1S sempre com placa de proteção, e corrente de carga adequada
  à capacidade. Não remover os avisos de bateria da documentação.
- Não gravar nem apagar uma placa conectada sem o dono saber.

## Verificação

Rodar o que se aplica à mudança, na raiz do projeto:

```bash
# firmware
arduino-cli compile --fqbn esp8266:esp8266:d1_mini  src/foxlight
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32C6 src/foxlight

# matemática
g++ -std=c++11 -Wall -Wextra -o /tmp/exposure_test test/exposure_test.cpp && /tmp/exposure_test

# desenhos (Pillow) e caixa (manifold3d, numpy, Pillow)
python3 tools/diagramas/gerar.py
python3 tools/caixa/gerar.py

# placas
kicad-cli sch erc --severity-all hardware/kicad_rev2/foxlight_rev2.kicad_sch
kicad-cli pcb drc --schematic-parity --severity-all hardware/kicad_rev2/foxlight_rev2.kicad_pcb
```

Resultado esperado: rev 2 sem violações; rev 1 (`foxlight.kicad_*`) com apenas
dois avisos de serigrafia na borda. Os relatórios `.rpt` não vão para o Git.

## Licença

CC BY-NC 4.0 ([LICENSE](LICENSE)). Ao usar dados ou arquivos de terceiros,
conferir a licença e creditar na seção de referências do README.
