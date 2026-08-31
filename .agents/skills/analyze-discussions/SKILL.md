---
name: analyze-discussions
description: Use quando um signal do pipeline de conteúdo LinkedIn merecer aprofundamento do debate antes de virar tema (etapa opcional entre discover-signals e cluster-signals).
---

# Análise de Discussões

## Overview

Aprofundar o debate de um Signal: mapear a pergunta central, as posições em conflito, o desacordo real e a oportunidade de conteúdo.

## Quando Usar / Quando NÃO Usar

- Usar: quando um signal tem debate rico e merece análise antes da clusterização; sob demanda.
- NÃO usar: para todo signal (a maioria já nasce com debate suficiente no discover-signals).

## Entrada

- 1 Signal (id, observation, debate, evidence, possible_angle)

## Saída (bloco `discussion:` anexado ao signal)

```yaml
discussion:
  question: "Qual é a pergunta central do debate?"
  position_a: "Posição A"
  position_b: "Posição B"
  disagreement: "Onde está o conflito real (ex.: custo vs qualidade)?"
  unanswered_question: "Pergunta que ninguém respondeu bem ainda?"
  content_opportunity: "Oportunidade de conteúdo para o autor"
```

## Fluxo

1. Ler o signal.
2. Identificar a pergunta central do debate.
3. Mapear as posições em conflito (A e B) — sem tomar partido.
4. Identificar o desacordo real (o que está em jogo).
5. Identificar a pergunta em aberto (o que ninguém respondeu bem).
6. Avaliar a oportunidade de conteúdo para o autor (usando memory/professional_experience.md e opinions.md).
7. Anexar o bloco `discussion:` ao signal no arquivo YAML.

## Regras

- Não tomar partido na análise — mapear o debate, não vencê-lo.
- A oportunidade de conteúdo deve conectar com a experiência/opinião do autor.
- Se o signal não tiver debate real, dizer isso em vez de forçar um.
