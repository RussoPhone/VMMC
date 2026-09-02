# VocalField comportamental — desenho

## Objetivo

Validar visualmente a hipótese de que a voz funciona melhor como uma influência
comportamental contínua sobre o ecossistema do que como outra forma geométrica.
A primeira versão deve ser pequena, observável e reversível, reutilizando as
características vocais já calculadas pelo pipeline.

## Princípios

- A voz não cria organismo, corpo, partícula, centro espacial ou geometria própria.
- O campo modifica temporariamente movimento, relações e morfologia das formas
  existentes, sem reescrever a identidade persistente de cada linhagem.
- Entrada e saída vocal usam ataque e decaimento suaves; nenhum efeito deve ligar
  ou desligar abruptamente.
- `radius` representa alcance comportamental no ecossistema, não um raio físico
  desenhado na cena.
- Colisões evitam sobreposição acidental, mas cedem progressivamente quando duas
  formas estão se fundindo e assimilando.

## Componente `VocalField`

Um `VocalFieldController` em `expression/vocal_field.py` recebe um
`MusicalContext` por quadro de análise e mantém um `VocalField` imutável com cinco
canais normalizados entre zero e um:

- `intensity`: energia expressiva atual da voz, baseada principalmente em
  `vocal_activity` e sustentada por `vocal_presence`;
- `radius`: alcance comportamental, ampliado por presença vocal persistente,
  intensidade e protagonismo musical;
- `roughness`: qualidade vocal áspera, derivada de presença vocal combinada com
  ruído, ataques e atividade espectral;
- `continuity`: continuidade vocal, combinando presença suavizada, continuidade
  da assinatura e estabilidade;
- `pressure`: força tensional da voz, combinando intensidade, tensão contextual,
  crescimento e clímax.

Cada canal aproxima-se de seu alvo com taxas diferentes de ataque e liberação.
Quando a evidência vocal desaparece, todos os canais decaem gradualmente. O
controlador não interpreta ausência de voz como uma nova presença.

## Alcance comportamental

O campo não possui coordenadas. O `EcosystemController` ordena organismos de
forma determinística por relevância comportamental, considerando visibilidade e
protagonismo. `radius` abre progressivamente o alcance do campo nessa ordem:
organismos mais relevantes recebem influência primeiro; com maior alcance, a
influência se espalha continuamente pelo restante do ecossistema.

O peso final de cada organismo combina alcance e `intensity`. Não haverá um corte
binário que faça uma forma entrar ou sair subitamente do campo.

## Efeito nas formas

O campo gera modificadores transitórios por organismo, mantidos no estado do
ecossistema e expostos no snapshot:

- voz suave e contínua aumenta coesão, fluidez e continuidade do movimento;
- voz intensa e pressionada aumenta tensão, impulso e deformação;
- voz áspera aumenta a irregularidade superficial;
- voz protagonista, por meio de `radius`, distribui influência a mais formas;
- ausência vocal conduz todos os modificadores suavemente de volta a zero.

O `VisualGenome` continua sendo a identidade base. A geometria combina o genoma
com os modificadores vocais somente ao gerar o quadro atual. Isso evita que uma
passagem vocal altere permanentemente uma linhagem ou torne todas as formas
iguais.

Para a primeira versão, os efeitos visuais ficam limitados a:

- movimento: coesão, amortecimento orgânico e impulso;
- superfície: fluidez, deformação tensional e rugosidade;
- relações: reforço moderado de coesão, sem criar ou classificar uma presença
  vocal.

Cor, nascimento de organismos e lógica de detecção de presenças permanecem fora
do escopo.

## Colisão com gradiente de assimilação

Cada par de organismos usa seus raios visuais estimados para detectar
interpenetração. Quando há sobreposição, o controlador aplica uma repulsão suave
e simétrica, preservando massa e evitando saltos.

A força de colisão é modulada pela relação entre o par:

```text
sem fusão ───────── fusão parcial ───────── assimilação completa
repulsão total        repulsão reduzida          sem colisão
```

O fator de repulsão diminui continuamente com `fusion` e, sobretudo, com
`assimilation`. A distância mínima efetiva também encolhe no mesmo gradiente.
Assim, formas distintas deixam de se sobrepor por acidente, enquanto formas em
fusão atravessam uma aproximação contínua até poderem ocupar o mesmo espaço ao
serem assimiladas.

A resolução será determinística, limitada por quadro e robusta quando dois
centros coincidirem. Ela altera posição e velocidade no estado físico, não os
vértices diretamente no renderer.

## Fluxo de dados

```text
AudioFeatures vocal_evidence/vocal_intensity
                 ↓
MusicalContext vocal_activity/vocal_presence + assinatura/regimes
                 ↓
VocalFieldController → VocalField suavizado
                 ↓
EcosystemController → peso e efeito por organismo + colisões graduais
                 ↓
EcosystemSnapshot → estado físico, efeitos vocais e métricas de debug
                 ↓
EcosystemGeometryBuilder → genoma + efeito vocal transitório
                 ↓
Renderer/HUD
```

`main.py` apenas coordena essas interfaces públicas. Ao trocar de faixa, cria um
novo controlador do campo junto com os demais componentes contextuais.

## Debug observável

O HUD gráfico ou, quando `pygame.font` não estiver disponível, o debug textual
deve permitir comparar a cadeia completa:

- `VOCAL FEATURES`: `evidence` e `intensity` instantâneos;
- `VOCAL FIELD`: `intensity`, `radius`, `roughness`, `continuity` e `pressure`;
- `VOCAL EFFECT`: quantidade de organismos alcançados, influência média e
  máxima, fluidez, tensão e rugosidade aplicadas;
- `COLLISION`: quantidade de contatos e maior repulsão aplicada.

As métricas pertencem ao snapshot público do ecossistema. O HUD não acessa
atributos privados de controladores.

## Testes e validação

O desenvolvimento seguirá ciclos de teste primeiro. Testes determinísticos devem
comprovar:

1. derivação limitada e semanticamente coerente dos cinco canais;
2. ataque e decaimento contínuos, inclusive após ausência vocal;
3. alcance graduado entre vários organismos, sem criação de forma vocal;
4. influência vocal transitória sobre movimento e parâmetros geométricos;
5. separação suave de formas não relacionadas que se sobrepõem;
6. redução contínua da colisão conforme fusão e assimilação aumentam;
7. métricas públicas suficientes para reconstruir no debug a cadeia de causa e
   efeito;
8. integração no pipeline sem perder quadros de áudio nem alterar a ordem das
   camadas existentes.

Após a suíte automatizada e `compileall`, a hipótese será avaliada visualmente
com uma faixa que contenha entradas, sustentações, trechos ásperos e ausências de
voz. O critério desta etapa é perceber influência coerente sobre formas já
existentes sem enxergar uma entidade geométrica reservada à voz.

## Fora do escopo

- separação de fonte vocal ou modelo de aprendizado de máquina;
- localização espacial real da voz;
- forma, aura ou partículas exclusivas para voz;
- classificação de cantor, letra, emoção ou técnica vocal;
- persistência do efeito vocal no `VisualGenome`;
- calibração definitiva dos coeficientes expressivos.

