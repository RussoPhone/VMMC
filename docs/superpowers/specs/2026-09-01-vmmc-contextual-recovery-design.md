# Recuperação contextual do VMMC

## Objetivo

Entregar um protótipo Linux simples em que uma única forma represente o áudio atual, o histórico musical e seu próprio estado visual anterior. Dois instantes acusticamente semelhantes devem poder gerar respostas diferentes quando seus históricos forem diferentes.

## Recuperação do repositório

O conteúdo e o histórico Git de `vmmc/` serão promovidos para a raiz `VMMC/`. O Git externo vazio e os ambientes `.venv/`, `env/`, `v/`, `vmmc/.venv/` e `vmmc/venv/` são redundantes e serão removidos. Um único `.venv` recriável permanecerá ignorado.

## Arquitetura

```text
AudioInput -> AudioAnalyzer -> MusicalMemory -> VisualState -> Geometry -> Renderer
```

- `audio/input.py`: decodifica, reproduz e entrega quadros mono sequenciais; preserva os canais na saída.
- `audio/analyzer.py`: produz somente características instantâneas normalizadas.
- `memory/musical_memory.py`: deriva contexto temporal em escalas curta e média.
- `state/visual_state.py`: converte contexto em alvos e evolui um estado persistente amortecido.
- `geometry/`: transforma o estado visual em um blob único, contínuo e determinístico.
- `renderer/`: desenha vértices e debug; não conhece áudio ou contexto musical.
- `main.py`: monta o pipeline, encaminha todos os quadros acumulados e gerencia o ciclo de vida.

## Modelo contextual mínimo

`AudioFeatures` manterá amplitude, bandas espectrais, fluxo e onset local. As grandezas serão normalizadas de modo previsível e independente do tamanho do FFT.

`MusicalContext` representará:

- energia atual;
- média curta;
- média média;
- tendência curta;
- contraste entre o instante e o passado recente;
- atividade suavizada;
- persistência de intensidade;
- tensão derivada dessas relações.

A memória será dirigida por timestamps dos quadros, não pela taxa de renderização.

## Estado e geometria

O estado visual conterá escala, deformação, agitação, suavidade e rotação. Cada parâmetro terá alvo contextual, velocidade e amortecimento simples. O contexto não produzirá vértices diretamente.

A geometria partirá de um círculo radial fixo. Harmônicos com fase temporal contínua deformarão a mesma entidade; não haverá aleatoriedade independente por frame.

## Linux e renderização

SoundFile e SoundDevice permanecem responsáveis por decodificação e saída. Pygame permanece apenas para display, eventos e desenho. O renderer não dependerá de `pygame.mixer` e tolerará a indisponibilidade de `pygame.font` no Python 3.14 usando debug no terminal.

Caminhos inexistentes produzirão mensagens explícitas. A documentação usará caminhos Linux corretos e o interpretador do ambiente virtual.

## Observabilidade

O HUD ou terminal mostrará features instantâneas, médias contextuais, tendência, contraste, atividade, persistência, tensão e estado visual. A saída terminal será limitada para não inundar o console.

## Validação

Os testes devem comprovar:

1. analyzer finito, normalizado e coerente para silêncio e tons sintéticos;
2. mesma energia atual produz contextos diferentes após históricos calmo e intenso;
3. `VisualState` persiste e converge sem saltos;
4. backlog de áudio atualiza memória e estado em ordem;
5. geometria é contínua e recupera sua referência;
6. renderer não importa nem recebe conceitos musicais;
7. reprodução, empacotamento, compilação e testes funcionam no Linux.

Um smoke test manual com `cidade.wav` confirmará janela, som e HUD no dispositivo real.

## Fora de escopo

Microfone, IA, reconhecimento semântico, partículas, plugins, banco de dados, configuração complexa e troca arbitrária de renderer.
