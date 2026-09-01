# Reprodução de áudio no Linux e janela redimensionável

## Objetivo

Restaurar a reprodução audível e sincronizada no Arch Linux, eliminar os travamentos introduzidos pelo backend atual e tornar o caminho de áudio seguro para futuras funções como troca de faixa, pausa, seleção de dispositivo e análises mais sofisticadas. A janela deve ser redimensionável e oferecer maximização quando o gerenciador de janelas suportar esse controle.

## Contexto confirmado

O host usa PipeWire 1.6.8 com compatibilidade PulseAudio, WirePlumber e PortAudio. O `sounddevice` enxerga o dispositivo ALSA `default`, que aponta para o headset USB configurado como sink padrão. Portanto, ausência de dispositivo ou de servidor de áudio não é a causa principal.

O código atual contém estas regressões:

- `AudioInput.get_next_frame()` segura um `threading.Lock` e chama `get_position_seconds()`, que tenta adquirir o mesmo lock não reentrante. O primeiro quadro trava.
- O callback escolhe as amostras a partir de tempo de parede. Jitter de agendamento pode repetir ou pular amostras.
- `main.py` acessa `_mixer_available`, embora o backend novo só defina `_device_available`.
- Falhas de saída são convertidas silenciosamente em modo offline, fazendo a aplicação parecer funcionar sem explicar por que não produz som.
- Ao trocar de arquivo, o stream anterior não é explicitamente encerrado.
- A janela é criada sem `pygame.RESIZABLE`, então o gerenciador não oferece maximização e a geometria não acompanha mudanças de tamanho.

## Abordagem escolhida

Manter `sounddevice` como backend de saída e `soundfile` como decodificador. O callback de PortAudio será dirigido por um cursor monotônico de amostras, não por relógio de parede. Reprodução, análise e interface gráfica dependerão de uma API pública pequena de `AudioInput`; nenhuma camada externa consultará atributos internos do backend.

As alternativas rejeitadas são voltar ao `pygame.mixer`, que mantém relógios diferentes para reprodução e análise, ou iniciar `ffplay`, que adiciona um processo externo e dificulta controle e sincronização.

## Componentes e responsabilidades

### `audio/input.py`

`AudioInput` carregará o arquivo uma vez como matriz `float32` bidimensional. Os canais originais serão preservados para reprodução; uma visão mono será derivada apenas para análise.

O construtor aceitará opcionalmente uma fábrica de streams. A produção usará `sounddevice.OutputStream`; testes usarão um stream determinístico em memória. Abrir o dispositivo será responsabilidade de `play()`, evitando efeitos externos durante a simples leitura do arquivo.

O callback copiará blocos contíguos a partir de `_playback_cursor`, preencherá o restante com silêncio no último bloco e avançará o cursor exatamente pela quantidade consumida. O callback de finalização apenas sinalizará o término; operações potencialmente bloqueantes como `stop()` e `close()` ocorrerão fora da thread de áudio.

`get_next_frame()` observará uma fotografia curta do cursor e entregará quadros mono sequenciais ainda não analisados. Assim, uma queda temporária de FPS não apaga a trajetória musical: o `main` poderá drenar todos os quadros disponíveis antes de desenhar. O último quadro será preenchido com zeros para manter tamanho constante.

A classe exporá `PlaybackState` (`STOPPED`, `PLAYING`, `FINISHED`, `FAILED`), `state`, `error_message`, `get_position_seconds()`, `get_next_frame()`, `is_finished()` e `stop()`. Estado interno de stream ou disponibilidade de dispositivo não fará parte do contrato público.

Falhas ao abrir ou iniciar a saída lançarão `AudioPlaybackError` com uma mensagem acionável e colocarão a instância em `FAILED`. Não haverá fallback silencioso por padrão. Isso impede que uma falha futura se manifeste apenas como ausência de som.

### `main.py`

O laço principal usará apenas a API pública. Em cada iteração, drenará os quadros já reproduzidos em ordem e atualizará análise e memória para cada quadro antes de renderizar o estado mais recente.

A troca de arquivo encerrará o `AudioInput` anterior antes de criar o próximo. O encerramento da aplicação ficará protegido por `try/finally`, garantindo a liberação do stream e do Pygame mesmo diante de erro.

Se a reprodução falhar, o programa exibirá a causa no terminal e encerrará de forma limpa, em vez de continuar em silêncio. O HUD derivará o texto de áudio de `PlaybackState`.

### `renderer/renderer.py`

A janela será criada com `pygame.RESIZABLE`. Um cálculo único de viewport atualizará largura, altura, centro e raio sempre que o tamanho real da superfície mudar. O polígono continuará centralizado e manterá proporções ao maximizar, restaurar ou redimensionar.

## Concorrência e sincronização

O lock protegerá apenas fotografias e atualizações curtas de cursores e estado. Nenhum método público chamará outro método que tente readquirir o mesmo lock. Nenhuma chamada bloqueante ao backend acontecerá enquanto o lock estiver seguro.

O cursor de reprodução mede amostras enviadas ao dispositivo. A posição visual pode anteceder a onda audível pela latência fixa do buffer de PortAudio, mas não deriva com o tempo nem pula blocos por jitter. Compensação de latência poderá ser adicionada posteriormente sem mudar a interface pública.

## Empacotamento e operação no Arch Linux

Um `pyproject.toml` declarará Python, NumPy, SoundFile, SoundDevice e Pygame, além do comando `vmmc`. O README descreverá os pacotes de sistema `portaudio`, `libsndfile`, `pipewire-pulse`, `wireplumber` e `tk`, criação do ambiente virtual, instalação editável, execução, controles e diagnóstico básico.

Ambientes virtuais e bytecode serão ignorados pelo Git. A verificação revelou que bytecode já rastreado, recompilado entre revisões do Python 3.14, bloqueava importações de forma intermitente; por isso esses artefatos serão removidos do índice sem depender da limpeza dos diretórios locais.

## Testes

Os testes usarão `unittest`, disponível na biblioteca padrão, e um stream falso que executa o callback real contra buffers em memória. Eles cobrirão:

- blocos consecutivos sem repetição ou salto;
- preservação de estéreo na saída e conversão mono apenas na análise;
- consulta de posição e entrega de quadro sem deadlock;
- drenagem sequencial de quadros mesmo quando vários ficaram disponíveis;
- transições de estado, fim natural, falha ao iniciar e `stop()` idempotente;
- HUD baseado na API pública, sem atributos privados;
- criação redimensionável e atualização do viewport.

Cada comportamento será introduzido por um teste que falha pela razão esperada antes da mudança de produção. A verificação final executará a suíte completa, importação/compilação, instalação editável local e um smoke test do pipeline com WAV sintético. A confirmação auditiva em dispositivo real será registrada separadamente caso a sandbox não possa acessar a sessão gráfica.

## Documentação para agentes

O README será curto e voltado a usuários e contribuidores. `AGENTS.md` registrará a ideia central, os invariantes do pipeline, limites entre componentes, comandos verificados e o bloco de orientação automática do Project Memory com o ID estável `vmmc`. Caminhos absolutos permanecerão somente na configuração local do Project Memory.

Ao concluir, `Current State.md` e `Handoff.md` no cofre serão atualizados com resultados verificados; decisões arquiteturais serão promovidas apenas com evidência dos testes e do código final.
