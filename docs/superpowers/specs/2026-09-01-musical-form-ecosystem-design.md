# Ecossistema sublime de formas musicais

## Visão

Cada música deve cultivar um ecossistema visual próprio do início ao fim. O VMMC não exige que a obra tenha graves intensos, instrumentos facilmente separáveis ou mudanças bruscas para produzir uma experiência rica. Ele aprende as proporções, delicadezas e relações daquela música e torna visível uma estrutura que apenas uma análise computacional com memória conseguiria acompanhar integralmente.

O corpo principal continua representando a trajetória global. Ao redor dele, qualquer quantidade de presenças pode emergir, interagir, gravitar, fundir-se, separar-se e desaparecer. Essas presenças podem corresponder a fontes prováveis, como voz ou baixo, a texturas incertas ou a forças expressivas compartilhadas. A relação musical importa mais que um rótulo instrumental.

## Princípios

### Sensibilidade relativa

Toda medição expressiva é relativa à história da própria música. Um sopro numa obra silenciosa pode ter a mesma relevância de uma explosão numa obra intensa. Limiares absolutos podem proteger contra ruído técnico, mas não decidem protagonismo musical.

### Contexto antes de reação

O sistema não é um `live-react`. Um crescendo não significa apenas aumento de volume; sua interpretação depende de preparação, repetição, tensão, participação das presenças e consequência posterior. A mesma assinatura instantânea pode produzir respostas diferentes conforme o caminho musical que a antecede.

### Identidade híbrida

Cada presença combina duas identidades:

- identidade sonora provável, baseada em assinatura tímbrica e temporal;
- identidade expressiva, baseada em função, gesto, clima e relações.

A identidade sonora pode permanecer incerta. A identidade expressiva deve continuar funcional mesmo sem reconhecer voz ou instrumento. O VMMC não apresenta como certeza uma classificação que DSP local não consegue sustentar.

### Liberdade sem contagem arbitrária

Não existe limite fixo de presenças. O custo visual e computacional será organizado por famílias, organismos compostos e níveis de detalhe, nunca pelo descarte de uma forma apenas porque uma contagem foi atingida. Formas semelhantes podem gravitar e fundir-se, preservando linhagem suficiente para uma separação futura.

### Continuidade e memória

Nascimento, mudança, fusão, separação e desaparecimento possuem histerese. Nenhuma presença oscila entre estados por pequenas variações de um quadro. Resíduos visuais preservam acontecimentos importantes mesmo depois que sua fonte deixa de dominar.

## Arquitetura conceitual

```text
quadros de áudio
        ↓
características instantâneas ampliadas
        ↓
paisagem adaptativa da música
        ↓
assinaturas + protagonismo + regimes contextuais
        ↓
campo expressivo contínuo
        ↓
ecologia de presenças com memória e relações
        ↓
morfologias, materiais e cores individuais
        ↓
geometria composta e renderização
```

### Paisagem adaptativa

A paisagem descreve o vocabulário corrente da música em múltiplas escalas temporais. Ela mantém distribuições e tendências de:

- energia e faixa dinâmica;
- centroide, distribuição e mudança espectral;
- harmonicidade, ruído, aspereza e densidade;
- ataques, sustentação, decaimento e periodicidade;
- estabilidade tímbrica e novidade;
- atividade, silêncio e respiração estrutural.

Cada valor instantâneo ganha uma versão relativa: desvio normalizado em relação ao curto, médio e longo prazo. A adaptação desacelera durante eventos muito novos para que o próprio evento não apague imediatamente sua relevância.

### Assinaturas sonoras

Uma assinatura é um vetor DSP compacto que descreve uma camada perceptiva sem afirmar necessariamente qual instrumento a produziu. Ela inclui perfil espectral, estrutura harmônica, envelope temporal, modulação, ruído e comportamento de ataque. Semelhança entre assinaturas permite reconhecer continuidade, retorno e transformação.

Indícios de voz, synth, baixo, guitarra, piano ou percussão influenciam a assinatura, mas permanecem probabilísticos e internos. A voz recebe atenção especial a sustentação harmônica, modulação, respiração, instabilidade e gesto, pois sua carga emocional não se reduz à presença de frequências vocais.

### Protagonismo e função contextual

Protagonismo resulta da combinação de novidade, persistência, contraste relativo, recorrência, ocupação espectral e efeito sobre o restante do campo. Uma assinatura pode assumir funções como fundo, impulso, resposta, protagonista, ruptura, sustentação ou resolução. As funções coexistem como pesos contínuos; não são estados mutuamente exclusivos.

### Regimes e razão musical

A memória acompanha regimes contextuais: estabilidade, construção, suspensão, ruptura, clímax, liberação e transição. Um crescendo adquire sentido pela trajetória entre regimes e pelas assinaturas que o constroem. O sistema não tenta declarar uma explicação humana definitiva; representa evidências temporais e relações que sustentam aquela interpretação.

## Ecologia de presenças

Uma perturbação breve começa no campo expressivo e no corpo principal. Persistência, retorno ou protagonismo permitem que ela germine uma presença. Cada presença possui:

- identificador e linhagem estáveis durante o ciclo musical;
- assinatura sonora suavizada e sua incerteza;
- idade, persistência, recorrência e resíduo;
- pesos de função contextual;
- estado expressivo, incluindo tensão, intimidade, peso, expansão, fragilidade e fluidez;
- relações de afinidade, contraste, sincronização, influência e ancestralidade;
- morfologia, material, cor, movimento e memória visual próprios.

### Gravitação e fusão

Afinidade tímbrica, sincronização temporal, função compartilhada e trajetória convergente produzem gravitação. A proximidade visual não depende somente de frequência ou volume. Fusão exige afinidade persistente e cria um organismo composto com memória das presenças constituintes.

Se a música voltar a distingui-las, a divergência de assinatura ou função produz separação gradual. A nova geometria carrega vestígios da união. Se permanecerem juntas até o final, a fusão integra a configuração final do ecossistema.

### Formas sem limite fixo

Presenças continuam semanticamente individuais mesmo quando a renderização usa um organismo composto. O estado mantém uma hierarquia de famílias; a geometria escolhe o nível de detalhe adequado ao tamanho, relevância e proximidade. O renderer recebe uma representação pronta e não decide quais identidades sobrevivem.

## Linguagem visual individual

Geometria e cor não serão escolhidas por uma tabela fixa `instrumento → forma`. Cada presença deriva um genoma visual contínuo de sua assinatura e trajetória:

- massa, escala, simetria e centro de gravidade;
- continuidade, elasticidade, fluidez e fragmentação;
- rugosidade, brilho, transparência e densidade aparente;
- perfil de ataque, pulsação, rotação e deslocamento;
- matiz, saturação, luminosidade e estabilidade cromática.

Baixo provável pode favorecer massa e gravidade; synth, continuidade elástica e transformação; voz, respiração, instabilidade e gesto; piano e guitarra, estruturas distintas de ataque, decaimento e harmônicos. São tendências derivadas, não moldes. Duas vozes em duas músicas não precisam produzir a mesma forma.

## Início, transição e fim

### Início

O corpo principal nasce quase neutro. A calibração começa imediatamente, mas usa estimativas robustas e incerteza explícita para não tratar os primeiros segundos como padrão definitivo. Presenças iniciais podem germinar enquanto a paisagem continua aprendendo.

### Transição contínua

Sem silêncio prolongado, não há reinício. Uma mixagem, medley ou passagem entre faixas reorganiza o mesmo ecossistema. Uma ruptura contextual profunda pode criar uma nova região e reduzir a influência da paisagem anterior, mas resíduos e relações preservam a transição.

### Silêncio e aquietamento

Silêncio é contextual: combina piso absoluto de segurança com energia suficientemente abaixo da paisagem recente. Durante o silêncio, movimento, tensão e brilho diminuem gradualmente; presenças podem aproximar-se, repousar ou completar fusões, sem perder imediatamente a memória.

Após 12 segundos contínuos de silêncio, o ciclo musical é encerrado. O ecossistema encontra uma configuração final, preservada brevemente como resíduo. O próximo som inicia um novo ciclo com nova paisagem. Um ruído isolado abaixo do critério de atividade musical não reinicia a contagem.

## Limites dos componentes

- `audio/analyzer.py` amplia características instantâneas DSP, mas não mantém paisagem ou identidades longas.
- `memory/musical_memory.py` mantém paisagem adaptativa, regimes, silêncio contextual e evidências temporais.
- Um módulo focado em `expression/` manterá assinaturas persistentes, protagonismo e relações da ecologia.
- `state/` manterá morfologia global, morfologias individuais, genomas visuais e resíduos.
- `geometry/` transformará o estado em corpos, organismos compostos, ligações e fragmentos.
- `renderer/` desenhará somente o snapshot recebido e continuará sem interpretar música.
- `main.py` coordenará interfaces públicas e drenará todos os quadros em ordem.

## Desempenho e determinismo

A primeira implementação usa somente DSP local com NumPy e biblioteca padrão. Não depende de internet, modelo neural ou serviço externo. Um modelo local opcional pode complementar identidades sonoras futuramente, sem substituir a base DSP.

O estado sem limite fixo não autoriza crescimento descontrolado de custo por quadro. Atualizações relacionais usam vizinhança e hierarquia, evitando comparação quadrática global quando a ecologia cresce. Níveis de detalhe reduzem custo geométrico sem apagar presenças. Entradas e estados iguais produzem snapshots iguais.

## Erros e observabilidade

Valores DSP devem permanecer finitos e normalizados onde o contrato exigir. Incerteza de identidade é dado, não exceção. O HUD de desenvolvimento exporá paisagem relativa, regime, silêncio, protagonismo e contagens por nível de detalhe, sem transformar o renderer em analisador.

Falhas reais de entrada continuam explícitas. Sobrecarga interna não descarta quadros de memória; otimiza representação e desenho.

## Estratégia de testes

Os testes usam sequências sintéticas e características construídas com resultados esperados independentes da implementação. Devem provar pelo menos:

- o mesmo instante ganha relevância diferente após histórias diferentes;
- detalhes sutis emergem numa paisagem calma;
- intensidade constante não permanece eternamente nova;
- um crescendo preparado difere de um pico isolado;
- uma assinatura que retorna recupera continuidade;
- identidade sonora incerta ainda produz função expressiva;
- formas semelhantes gravitam e fundem somente após afinidade persistente;
- divergência posterior separa um organismo preservando linhagem;
- qualquer quantidade de presenças pode existir semanticamente;
- 12 segundos de silêncio encerram o ciclo, mas 11,99 segundos não;
- transição contínua reorganiza o ecossistema sem reiniciá-lo;
- nenhuma defasagem de renderização faz a memória pular quadros;
- comportamento e geometria permanecem determinísticos.

## Marcos de implementação

### Marco 1: escuta adaptativa

Ampliar DSP e memória para produzir paisagem relativa, assinatura compacta, protagonismo, regimes contextuais e ciclo de silêncio de 12 segundos. Esse marco termina com dados públicos testados e observáveis no HUD, ainda sem criar múltiplos corpos persistentes.

### Marco 2: ecologia

Introduzir presenças persistentes, campo expressivo, relações, gravitação, famílias, fusão, separação e configuração final. O corpo principal continua funcionando durante a migração.

### Marco 3: linguagem visual

Adicionar genomas visuais individuais, morfologias por presença, organismos compostos, níveis de detalhe e geometria relacional. O renderer recebe o snapshot composto sem acessar contexto musical.

Cada marco possui plano, testes e commits próprios. O plano imediatamente seguinte cobre somente o Marco 1 para manter revisão e execução controláveis.

## Fora de escopo inicial

- reconhecimento categórico garantido de instrumentos;
- transcrição de letra ou fala;
- inferência neural de emoção;
- internet, APIs musicais ou modelos remotos;
- separação completa de stems;
- limites fixos de presenças como mecanismo de desempenho.
