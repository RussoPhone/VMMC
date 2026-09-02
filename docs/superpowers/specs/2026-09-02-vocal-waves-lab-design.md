# Laboratório de ondas vocais

## Objetivo

Criar o executável experimental `vmmc-vocal`, dedicado exclusivamente a
visualizar voz presente numa mixagem. Instrumentos ajudam a rejeitar falsos
positivos, mas não geram formas ou movimento visual.

## Fluxo

```text
áudio → características → memória vocal → gate conservador
      → estado vocal suavizado → linhas, ondas, parâmetros e grafos
```

O executável reutiliza arquivo e `--system-audio`, preservando a reprodução. Não
usa `PresenceTracker`, `EcosystemController`, `MorphologyController` nem geometria
instrumental.

## Gate conservador

O gate combina `vocal_evidence`, `vocal_intensity`, presença contextual,
harmonicidade, ruído e continuidade. Usa limiares distintos para abrir/fechar,
tempo mínimo de confirmação e decaimento suave. Sinais rejeitados aparecem apenas
como diagnóstico, nunca como expressão visual.

Esta etapa faz isolamento comportamental, não separação de stems; pode perder
vozes sutis para reduzir falsos positivos instrumentais.

## Visual

- onda vocal principal baseada no sinal mono recente, modulada pelo gate;
- linhas harmônicas secundárias;
- históricos de evidência, intensidade, pressão, continuidade e aspereza;
- espectro destacado apenas na faixa vocal;
- parâmetros numéricos, estado do gate e indicador de fundo rejeitado;
- ausência vocal dissolve todas as linhas expressivas gradualmente.

Não há corpo central, satélites ou forma reservada a instrumentos.

## Validação

Testes determinísticos cobrem gate, histerese, rejeição, decaimento e pipeline
exclusivo. O teste visual compara trechos vocais e instrumentais de uma mixagem,
confirmando silêncio visual expressivo durante o fundo instrumental.
