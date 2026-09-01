# Captura contextual do áudio do sistema

## Objetivo

Permitir que o VMMC reaja em tempo real ao áudio reproduzido na saída padrão do computador. A fonte pode ser Spotify, navegador, jogo ou qualquer outro aplicativo. A integração não depende de URLs, credenciais ou APIs desses serviços.

O primeiro ambiente suportado é Arch Linux com PipeWire e a camada compatível com PulseAudio (`pipewire-pulse`). O modo atual de abrir e reproduzir arquivos locais permanece disponível e inalterado.

## Interface

O comando abaixo inicia a captura da saída padrão:

```bash
.venv/bin/vmmc --system-audio
```

Sem esse argumento, o comportamento atual continua: um caminho abre o arquivo indicado e a ausência de caminho abre o seletor de arquivos.

O modo ao vivo permanece ativo até a janela ser fechada. Ele não encerra quando uma faixa ou aplicativo para de produzir som, pois silêncio é uma entrada válida e a saída do sistema não possui um fim natural.

## Arquitetura

Um novo componente `audio/live_input.py` será responsável somente por descobrir e capturar a saída padrão, armazenar amostras e entregar quadros mono sequenciais. `audio/input.py` continuará responsável pela decodificação e reprodução de arquivos.

O componente ao vivo implementará a parte da interface consumida por `main.py`: iniciar, parar, obter o próximo quadro, consultar estado e informar se terminou. Diferenças específicas da fonte serão encapsuladas, permitindo que o pipeline interpretativo permaneça comum aos dois modos.

O fluxo será:

```text
sink padrão do PipeWire/PulseAudio
        ↓
monitor do sink descoberto por pactl
        ↓
PCM capturado por parec em thread dedicada
        ↓
buffer sequencial com cursor de amostras
        ↓
AudioFrame mono
        ↓
análise → memória → gestos → morfologia → geometria
```

## Descoberta e captura

Na inicialização, `pactl get-default-sink` identificará o sink padrão. A fonte de captura será o monitor correspondente, normalmente `<sink>.monitor`. A implementação confirmará a existência desse monitor na listagem de fontes antes de iniciar a captura.

`parec` será iniciado para produzir PCM mono `float32` com taxa de amostragem explícita. A captura mono é adequada porque o modo ao vivo não reproduz o sinal; ele somente o envia para análise. O processo externo será tratado como uma dependência de I/O, com comandos e argumentos construídos como listas, sem shell.

Uma thread dedicada fará somente leitura bloqueante da saída de `parec` e inserção das amostras no buffer. Ela não executará análise musical, renderização ou fechamento complexo. O laço principal continuará drenando todos os quadros disponíveis em ordem.

## Tempo e continuidade

Cada quadro será indexado por um cursor monotônico de amostras capturadas. Seu timestamp será `início_do_quadro / samplerate`; relógio de parede não determinará limites ou índices de quadros.

O buffer preservará amostras ainda não consumidas quando a renderização atrasar. O pipeline processará todos os quadros completos transcorridos, em sequência, mantendo o contexto musical e o estado anterior da forma. Não haverá descarte intencional de quadros para alcançar o tempo atual.

O tamanho do quadro continuará derivado da duração usada pelo VMMC, inicialmente `1/30` de segundo. Fragmentos de bytes que não completem uma amostra serão mantidos até a próxima leitura, e fragmentos de amostras que não completem um quadro permanecerão no buffer.

## Ciclo de vida e concorrência

`play()` iniciará a descoberta, o processo e a thread de captura. Chamadas repetidas enquanto a captura estiver ativa não criarão processos adicionais.

`stop()` será idempotente. Ele sinalizará a parada, encerrará o processo de captura, aguardará a thread fora de locks compartilhados e liberará seus recursos. Nenhum lock será mantido ao chamar operações que possam bloquear ou tentar adquirir o mesmo lock.

Ao contrário de um arquivo, a captura do sistema não transita naturalmente para `FINISHED`. Ela permanece `PLAYING` durante silêncio e só para por solicitação do usuário ou falha. `is_finished()` permanecerá falso durante uma sessão saudável.

## Erros

Falhas serão explícitas e resultarão em `AudioPlaybackError` ou em um erro específico compatível tratado por `main.py`. As mensagens distinguirão pelo menos:

- `pactl` ou `parec` ausente;
- impossibilidade de descobrir o sink padrão;
- monitor correspondente inexistente;
- falha ao iniciar `parec`;
- término inesperado do processo de captura.

Não haverá fallback silencioso para microfone, outro dispositivo ou modo de arquivo. Uma mudança do sink padrão durante a execução não provocará troca automática na primeira versão; o usuário poderá reiniciar o modo para capturar o novo sink.

## Integração com a aplicação

O parsing da linha de comando reconhecerá `--system-audio` como uma fonte, sem tratá-lo como caminho. `main.py` criará a entrada adequada por uma função pública de composição e não acessará atributos privados.

O HUD exibirá uma descrição da fonte, como `Áudio do sistema`, e o estado da captura. O controle `O` continuará abrindo um arquivo local; ao selecionar um arquivo, a captura anterior será parada antes da troca, respeitando o ciclo de vida já estabelecido.

## Testes

O desenvolvimento seguirá TDD. Os testes não dependerão de PipeWire, PulseAudio, Spotify ou dispositivo físico. As fronteiras de subprocesso e leitura serão injetáveis, usando processos e streams determinísticos em memória.

Os comportamentos cobertos serão:

- descoberta do monitor da saída padrão a partir de respostas controladas;
- erro quando comandos, sink ou monitor não estão disponíveis;
- conversão de bytes PCM em quadros com índices e timestamps exatos;
- preservação de fragmentos entre leituras;
- entrega de todos os quadros acumulados em ordem;
- captura contínua durante silêncio;
- término inesperado do capturador como falha explícita;
- `play()` e `stop()` idempotentes e sem deadlock;
- seleção de `--system-audio` e integração com o pipeline sem hardware real;
- troca segura da captura ao vivo para um arquivo local.

A verificação final executará toda a suíte de `unittest` e `compileall` conforme `AGENTS.md`.

## Fora de escopo

Esta primeira versão não inclui:

- leitura ou autenticação de links do Spotify;
- controle de reprodução do Spotify;
- suporte nativo a Windows ou macOS;
- seleção gráfica de fontes;
- troca automática quando a saída padrão muda;
- reprodução ou retransmissão do áudio capturado.
