# Geometria contextual expressiva do VMMC

## Objetivo

Evoluir o VMMC de um visualizador reativo para uma representação geométrica da sensação estrutural da música. O corpo visual começa neutro e muda de natureza conforme timbre, trajetória, contraste e estado residual.

O critério central é relacional: crescendo deve acumular pressão, drop deve liberar pressão anterior, pausa deve carregar o resíduo do que terminou e timbres diferentes devem alterar a qualidade física do mesmo corpo.

## Pipeline

```text
AudioInput
  -> AudioAnalyzer
  -> MusicalMemory / MusicalContext
  -> GestureEngine / GestureState
  -> MorphologyController / MorphologyState
  -> GeometrySnapshot
  -> Renderer
```

Responsabilidades:

- `audio/analyzer.py`: características acústicas instantâneas e estado local mínimo do FFT.
- `memory/musical_memory.py`: contexto temporal derivado do histórico.
- `expression/gesture_engine.py`: interpreta relações contextuais como gestos acoplados.
- `state/morphology.py`: mantém corpo, cor e resíduos com dinâmica persistente.
- `geometry/`: expressa a morfologia como corpo principal e fragmentos temporários.
- `renderer/`: desenha `GeometrySnapshot`; ignora áudio, contexto e gestos.
- `main.py`: conduz o pipeline e compõe o debug.

## Características acústicas

`AudioFeatures` preserva amplitude, graves, médios, agudos, fluxo e beat/onset. Acrescenta somente descritores baratos que alteram a morfologia:

- `spectral_centroid`: brilho espectral normalizado;
- `zero_crossing_rate`: aspereza/ruído de alta frequência;
- `spectral_density`: proporção de bins espectrais ativos;
- `spectral_stability`: semelhança local com o espectro anterior.

Esses descritores não reconhecem instrumentos. Eles formam qualidades contínuas que podem fazer um pad parecer fluido, um baixo parecer massivo e uma guitarra distorcida parecer áspera/angular sem rótulos semânticos.

## Contexto musical

`MusicalMemory` usa timestamps e duas janelas simples: curta, aproximadamente 2 segundos, e média, aproximadamente 12 segundos. `MusicalContext` contém:

- energia atual, curta e média;
- tendência de energia;
- atividade e tendência de atividade;
- novidade contextual;
- estabilidade;
- tensão acumulada;
- persistência de intensidade;
- centroid, ZCR e densidade suavizados;
- onset atual.

Novidade compara o instante com a janela curta. Estabilidade combina variação de energia, estabilidade espectral e baixa novidade. Tensão acumula quando energia/atividade crescem e relaxa mais lentamente quando o estímulo cessa. Isso fornece memória anterior ao gesto.

## Gestos expressivos acoplados

`GestureState` possui valores contínuos `0.0–1.0`:

- `pressure`;
- `release`;
- `impact`;
- `suspension`;
- `expansion`;
- `rupture`.

Eles não são sliders independentes nem uma enumeração. O motor mantém pressão residual e deriva um gesto a partir dos demais:

```text
contenção + crescimento -> pressão
pressão acumulada + novidade/onset -> impacto
impacto + novidade + aspereza -> ruptura
queda de tensão após pressão -> liberação
liberação + energia presente -> expansão
baixa energia após evento intenso -> suspensão
```

Acoplamentos obrigatórios:

- pressão inibe liberação enquanto ainda cresce;
- liberação consome pressão residual;
- impacto é modulado por contraste e contenção;
- expansão deriva principalmente de liberação, não de volume;
- estabilidade enfraquece impactos repetidos;
- suspensão depende de resíduo anterior;
- ruptura depende de impacto contextual, não de um threshold de grave.

Ataque e retorno usam constantes diferentes para permitir impacto rápido, pressão cumulativa e resíduo lento.

## Estado morfológico

`MorphologyState` é persistente e inicia neutro. Ele contém:

- `wave`, `mass`, `shard`, `noise`;
- `roughness`, `elasticity`, `symmetry`, `density`, `fluidity`;
- `expansion`, `compression`, `rotation`;
- `brightness`, `saturation`, `hue`, `color_stability`;
- `fragmentation` e `residue`.

A morfologia é um sistema acoplado:

- massa favorece densidade, compressão e movimento lento;
- wave + fluidity restauram continuidade e simetria;
- shard + roughness criam pontas, fissuras e fragmentação;
- compressão acumulada prepara expansão;
- angularidade e fluidez competem, mas podem coexistir;
- elasticidade governa quanto o corpo ultrapassa e retorna;
- resíduo retém rugosidade/deformação após eventos fortes;
- cor deriva do mesmo campo: brilho segue energia suavizada, saturação segue intensidade/tensão, hue drift segue mudança espectral, estabilidade cromática segue estabilidade musical.

O controlador usa alvos derivados de contexto + gesto e interpolação com ataque/retorno diferentes. `dt` é limitado para evitar saltos após pausas da janela.

## Geometria e aparecimento

O corpo principal continua sendo uma malha radial, mas combina famílias harmônicas coerentes:

- wave controla ondulações largas;
- mass controla raio, densidade visual e inércia;
- shard controla pontas angulares;
- noise/roughness controlam detalhe fino determinístico;
- symmetry controla o equilíbrio entre lados;
- compression e expansion alteram a chegada da forma, não apenas sua escala.

Fases evoluem continuamente no tempo. Não há `random()` por frame.

`GeometrySnapshot` contém vértices do corpo, cor de preenchimento/contorno e zero ou poucos fragmentos. Ruptura forte pode destacar segmentos da borda como fragmentos persistentes. Cada fragmento possui origem, velocidade, idade e retorno/dissolução determinísticos. Fragmentos continuam pertencendo perceptivamente à mesma entidade e possuem limite pequeno.

Modos de aparecimento emergem dos gestos:

- pressão -> compressão e tensão de borda;
- release -> descompressão;
- expansion -> crescimento estrutural;
- rupture -> fissura/fragmentação;
- suspension -> movimento lento com resíduo;
- estabilidade -> retorno progressivo à continuidade.

## Renderer e debug

O renderer recebe somente `GeometrySnapshot` e linhas de texto. Ele desenha o corpo, fragmentos e cores fornecidas sem importar `audio`, `memory` ou `expression`.

O debug é agrupado:

```text
AUDIO: energy bass mid high flux centroid zcr
CONTEXT: short medium trend novelty stability tension
GESTURES: pressure release impact suspension expansion rupture
MORPHOLOGY: wave mass shard noise roughness elasticity fluidity symmetry
COLOR: hue saturation brightness stability
```

O fallback de terminal permanece limitado em frequência.

## Comportamentos de referência

### Crescendo

Energia e atividade crescentes elevam pressão, compressão, densidade, saturação e tensão de borda. A forma parece preparar instabilidade, não apenas aumentar.

### Drop ou refrão

Onset/novidade sob pressão residual produz impacto, liberação e expansão. A mesma energia sem crescendo anterior gera resposta menor.

### Pausa

Energia baixa após intensidade produz suspensão. Movimento cai rapidamente, enquanto rugosidade, fragmentos e compressão desaparecem lentamente.

### Repetição

Onsets repetidos em contexto estável perdem novidade. O corpo estabiliza em torno do padrão em vez de repetir explosões idênticas.

## Validação

Testes determinísticos devem confirmar:

1. novos descritores acústicos são finitos e normalizados;
2. contexto distingue curto/médio prazo, novidade, estabilidade e tensão;
3. crescendo acumula mais pressão que energia estável equivalente;
4. drop após crescendo produz mais release/expansion que o mesmo instante sem pressão;
5. pausa após intensidade produz suspensão e resíduo;
6. onsets repetidos perdem impacto contextual;
7. morfologia permanece em `0–1`, evolui continuamente e retém resíduo;
8. geometria é determinística, contínua e limita fragmentos;
9. renderer permanece desacoplado;
10. backlog de áudio atravessa contexto, gesto e morfologia em ordem;
11. testes existentes e reprodução Linux continuam funcionando.

O smoke test final usa uma música real e observa som, janela, debug e coerência de crescendo/liberação.

## Fora de escopo

Redes neurais, classificação emocional, reconhecimento de instrumentos, embeddings, LLM, plugins, banco de dados, interface complexa, dezenas de objetos e partículas genéricas.
