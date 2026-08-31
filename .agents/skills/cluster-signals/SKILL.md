---
name: cluster-signals
description: Use quando houver signals coletados que precisem ser agrupados em temas (etapa 2x/semana do pipeline de conteúdo LinkedIn).
---

# Clusterização de Sinais

## Overview

Agrupar Signals que tratam do mesmo fenômeno em Topics, cada um com pergunta central e tese possível.

## Quando Usar / Quando NÃO Usar

- Usar: 2x/semana, quando houver signals acumulados.
- NÃO usar: com poucos signals (menos de ~10) — aguardar acúmulo.

## Entrada

- `research/signals/signals_*.yaml` (todos os signals não clusterizados)

## Saída

`research/topics/topics_YYYY-MM-DD.yaml`:

```yaml
topics:
  - id: topic_YYYYMMDD_01
    title: "Título do tema"
    pillars:
      - ia_aplicada
    signals:
      - signal_YYYYMMDD_001
      - signal_YYYYMMDD_002
    central_question: "Pergunta central do tema"
    possible_thesis: "Tese possível"
    author_connection: strong | medium | weak
    status: candidate
```

## Fluxo

1. Ler todos os signals.
2. Agrupar por fenômeno comum (mesmo assunto, mesmo debate, mesma mudança).
3. Para cada grupo, formular: título, pergunta central, tese possível.
4. Avaliar a conexão com o autor (strong/medium/weak) usando memory/.
5. Atualizar o status dos signals agrupados para `clustered` no arquivo de signals (`research/signals/signals_*.yaml`).
6. Salvar em `research/topics/topics_YYYY-MM-DD.yaml` com status `candidate`.

## Regras

- Um signal pode aparecer em no máximo 1 topic.
- Sinais que não formam grupo com ninguém ficam de fora (não forçar).
- Signals agrupados passam a `status: clustered`; topics nascem com `status: candidate`.
- A tese possível deve ser opinativa, não neutra.
- Não pontuar aqui — scoring é do score-opportunities.
