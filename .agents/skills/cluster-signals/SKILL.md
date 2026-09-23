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
- `research/topics/topics_*.yaml` (topics `published`/`archived` — histórico para o gate de novidade)

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
    novelty:
      verdict: new | revisited | duplicate
      vs_published: [topic_YYYYMMDD_NN]   # obrigatório se revisited
      delta: "O que este tema afirma que o publicado não afirmava"  # obrigatório se revisited
      new_case: "Evento/fonte posterior ao post publicado, se houver"
    status: candidate
```

## Gate de novidade (obrigatório)

Antes de criar um topic, comparar com o histórico (`published`/`archived`) e declarar `novelty`:

1. **`verdict: new`** — o fenômeno não foi tratado em nenhum post publicado. `vs_published` deve ficar vazio.
2. **`verdict: revisited`** — o fenômeno já foi tratado, mas há delta verificável. Exige `vs_published` (o topic anterior) e `delta` (a diferença afirmada). O delta precisa ser substantivo: não pode ser a tese anterior reescrita.
3. **`verdict: duplicate`** — é o mesmo tema sem delta. O topic nasce `duplicate` e **não entra no backlog**.

O único critério que dá garantia real de novidade é **evento novo**: um acontecimento posterior ao post publicado. Nesse caso, registrar em `new_case`. Sem evento novo, a novidade depende do delta declarado — que é verificável, mas não garantido.

O gate é **fail-closed**: topic sem `novelty` válido não é elegível para o Bloco 2, mesmo com `status: ready_for_research`.

## Fluxo

1. Ler todos os signals.
2. Agrupar por fenômeno comum (mesmo assunto, mesmo debate, mesma mudança).
3. Para cada grupo, formular: título, pergunta central, tese possível.
4. Avaliar a conexão com o autor (strong/medium/weak) usando memory/.
5. **Aplicar o gate de novidade**: comparar com `published`/`archived` e declarar `novelty` (ver seção acima).
6. Atualizar o status dos signals agrupados para `clustered` no arquivo de signals (`research/signals/signals_*.yaml`).
7. Salvar em `research/topics/topics_YYYY-MM-DD.yaml` com status `candidate`.

## Regras

- Um signal pode aparecer em no máximo 1 topic.
- Sinais que não formam grupo com ninguém ficam de fora (não forçar).
- Signals agrupados passam a `status: clustered`; topics nascem com `status: candidate`.
- A tese possível deve ser opinativa, não neutra.
- Todo topic carrega `novelty`; sem ele o topic não é elegível.
- Revisitar tema só é permitido com evento novo (`new_case`) ou delta declarado e verificado.
- Não pontuar aqui — scoring é do score-opportunities.
