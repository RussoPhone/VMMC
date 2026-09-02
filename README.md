# VMMC

Visualizador de música com memória contextual. O corpo geométrico central pode
cultivar um ecossistema de organismos sonoros, dissolver-se entre eles e voltar
a se recompor. Aparência e relações dependem tanto do instante atual quanto da
trajetória sonora e do estado visual anterior.

```text
áudio → características → memória → contexto → gestos → morfologia → geometria
```

Eventos breves deixam sementes; persistência ou retorno confirmam uma presença.
Presenças semelhantes gravitam, fundem-se com núcleos inicialmente distintos e
se assimilam gradualmente, mas voltam a se separar quando a música diverge.
Cada linhagem cultiva uma variação própria da linguagem orgânica original do
VMMC, sem usar uma tabela rígida de instrumento para forma.

O VMMC aprende uma paisagem relativa durante cada música. Assim, uma mudança
sutil pode ganhar força em uma faixa delicada sem exigir os mesmos valores
absolutos de uma gravação intensa. A escuta combina essa paisagem com
assinaturas sonoras probabilísticas — brilho, ruído, harmonicidade, ataque e
densidade — e regimes contextuais contínuos como construção, suspensão,
ruptura, clímax, liberação e transição. Essas dimensões podem coexistir; elas
não tentam impor um rótulo rígido de instrumento ao som.

Uma troca contínua de timbre continua pertencendo ao mesmo percurso musical.
Após 12 segundos de silêncio contextual, porém, o ciclo é encerrado; quando o
som retorna, uma nova paisagem começa a ser aprendida sem carregar indevidamente
o contexto da música anterior.

## Instalação no Arch Linux

Instale as bibliotecas de sistema:

```bash
sudo pacman -S --needed python python-pip portaudio libsndfile libpulse pipewire-pulse wireplumber tk
```

Crie o ambiente e instale o projeto:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .
```

## Uso

Abra diretamente uma música:

```bash
.venv/bin/vmmc caminho/para/musica.wav
# equivalente, útil durante o desenvolvimento:
.venv/bin/python main.py ~/Videos/Youtube/cidade.wav
```

No Linux, nomes de arquivo diferenciam maiúsculas de minúsculas:
`cidade.wav` e `Cidade.wav` são caminhos diferentes. A abreviação da pasta
pessoal também precisa da barra: use `~/Videos`, não `~Videos`.

Ou execute sem caminho para usar o seletor de arquivos:

```bash
.venv/bin/vmmc
```

Para visualizar em tempo real tudo o que toca na saída padrão do computador
(Spotify, navegador, jogos ou outros aplicativos), use:

```bash
.venv/bin/vmmc --system-audio
```

Esse modo captura o monitor da saída padrão por PipeWire/PulseAudio. Ele não
reproduz nem retransmite o áudio e permanece ativo mesmo durante silêncio, até
que a janela seja fechada. Os comandos `pactl` e `parec` são fornecidos pelo
pacote Arch `libpulse`.

Controles:

- `O`: abrir outra música;
- `Esc`: sair;
- maximizar ou redimensionar: use os controles normais da janela.

## Estrutura

- `audio/`: decodificação, reprodução e características instantâneas;
- `memory/`: contexto acumulado da música;
- `expression/`: gestos expressivos relacionados (pressão, impacto, liberação etc.);
- `state/`: morfologia persistente, cor e resíduos visuais;
- `geometry/`: corpo principal, deformação contínua e fragmentos temporários;
- `renderer/`: janela, HUD e desenho;
- `main.py`: coordenação do pipeline.

## Testes

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Os testes de áudio usam um stream em memória e não precisam tocar som.

Se `pygame.font` não estiver disponível, a janela e o som continuam
funcionando e os valores de debug são mostrados no terminal.

O HUD expõe cada etapa do pipeline em grupos (`AUDIO`, `CONTEXT`, `LANDSCAPE`,
`SIGNATURE`, `REGIME`, `GESTURES`, `MORPHOLOGY` e `COLOR`) para explicar por que
o corpo assumiu seu estado atual.

## Sem som no Arch Linux

Confirme que PipeWire/PulseAudio e o dispositivo padrão estão disponíveis:

```bash
pactl info
pactl get-default-sink
.venv/bin/python -m sounddevice
```

O programa encerra com uma mensagem clara se não conseguir abrir a saída; ele não continua silenciosamente em modo offline.

Para diagnosticar a captura do áudio do sistema, confirme o sink padrão e seu
monitor:

```bash
pactl get-default-sink
pactl list short sources
command -v parec
```
