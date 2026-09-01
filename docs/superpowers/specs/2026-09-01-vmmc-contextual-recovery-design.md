# Estabilização do VMMC

## Objetivo

Deixar o protótipo simples, executável no Linux e suficiente para demonstrar sua hipótese: a mesma energia atual pode produzir uma forma diferente quando o histórico musical é diferente.

## Escopo

1. Promover o conteúdo e o histórico Git de `vmmc/` para a raiz `VMMC/`.
2. Remover o Git externo vazio e os ambientes virtuais redundantes; manter somente um `.venv` recriável e ignorado.
3. Preservar o pipeline atual:

   ```text
   AudioInput -> AudioAnalyzer -> MusicalMemory -> VisualState -> Geometry -> Renderer
   ```

4. Corrigir somente falhas que prejudiquem execução, observabilidade ou o teste contextual.
5. Remover o arquivo morto `audio/timbre.py` e pequenos resíduos evidentes.

## Comportamento mínimo

- O analyzer continua produzindo amplitude, bandas, fluxo e beat instantâneos.
- A memória continua pequena. Ela deve ao menos distinguir energia atual, média recente, tendência/contraste e atividade.
- O estado visual continua suavizado e persistente entre frames.
- A geometria continua sendo um único blob determinístico com deformação temporal contínua.
- O renderer recebe apenas vértices e linhas de debug.
- O `main.py` apenas conduz o pipeline e não perde quadros de áudio acumulados.

Não serão adicionados novos subsistemas, configuração sofisticada ou uma linguagem visual maior.

## Linux e debug

SoundFile/SoundDevice permanecem no áudio e Pygame permanece no desenho. O projeto não dependerá de `pygame.mixer`. Como `pygame.font` está quebrado no Pygame/Python 3.14 atual, o debug deve continuar disponível no terminal sem impedir janela ou som.

O README mostrará o comando inequívoco:

```bash
.venv/bin/python main.py ~/Videos/Youtube/cidade.wav
```

Caminhos Linux são sensíveis a maiúsculas e minúsculas.

## Validação

Testes pequenos devem confirmar:

1. analyzer retorna valores finitos entre `0.0` e `1.0` para entradas básicas;
2. históricos calmo e intenso, seguidos pela mesma feature instantânea, geram contextos diferentes;
3. esses contextos geram estados visuais diferentes e contínuos;
4. renderer permanece desacoplado de conceitos musicais;
5. testes existentes, compilação e instalação continuam funcionando.

Um smoke test curto com `cidade.wav` confirma som e janela no dispositivo real.

## Fora de escopo

Reempacotamento em `src/`, reescrita do analyzer, memória multiescala completa, novas dinâmicas físicas, troca de renderer, microfone, IA, partículas, plugins e interface complexa.
