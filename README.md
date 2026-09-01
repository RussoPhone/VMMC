# VMMC

Visualizador de música com memória contextual. Uma única forma geométrica representa a música, mas sua aparência depende tanto do instante atual quanto da trajetória sonora e do estado visual anterior.

```text
áudio → características → memória musical → estado visual → geometria
```

## Instalação no Arch Linux

Instale as bibliotecas de sistema:

```bash
sudo pacman -S --needed python python-pip portaudio libsndfile pipewire-pulse wireplumber tk
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

Controles:

- `O`: abrir outra música;
- `Esc`: sair;
- maximizar ou redimensionar: use os controles normais da janela.

## Estrutura

- `audio/`: decodificação, reprodução e características instantâneas;
- `memory/`: contexto acumulado da música;
- `state/`: continuidade do estado visual;
- `geometry/`: forma base e deformação;
- `renderer/`: janela, HUD e desenho;
- `main.py`: coordenação do pipeline.

## Testes

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Os testes de áudio usam um stream em memória e não precisam tocar som.

Se `pygame.font` não estiver disponível, a janela e o som continuam
funcionando e os valores de debug são mostrados no terminal.

## Sem som no Arch Linux

Confirme que PipeWire/PulseAudio e o dispositivo padrão estão disponíveis:

```bash
pactl info
pactl get-default-sink
.venv/bin/python -m sounddevice
```

O programa encerra com uma mensagem clara se não conseguir abrir a saída; ele não continua silenciosamente em modo offline.
