---
name: run-editorial-batch
description: Use quando for necessário executar uma rodada editorial com um ou mais topics prontos para pesquisa, mantendo fila, checkpoints e falhas por topic persistentes.
---

# Rodada Editorial em Lote

## Objetivo

Executar uma fila editorial congelada de topics `ready_for_research`, um por vez, sem depender do contexto da conversa. A entrada é `content/backlog.md` e `research/topics/topics_*.yaml`; a saída é `runs/<run_id>/manifest.yaml` e o estado persistente de cada topic na fila.

## Seleção

Aceite exatamente uma forma de seleção:

```text
--topics 1
--topics N
--topics all
--topics topic_a,topic_b
```

- `1` seleciona o melhor topic elegível.
- `N` seleciona os N melhores topics elegíveis.
- `all` seleciona todos os topics elegíveis.
- A lista separada por vírgulas seleciona somente os ids informados, na ordem explícita.

Considere somente topics com status `ready_for_research`. Para seleção numérica ou `all`, ordene por score decrescente e use um desempate determinístico pelo `topic_id`. Para ids explícitos, valide que cada id existe e está `ready_for_research`; não substitua ids inválidos por outros topics.

Exemplo de resolução para uma seleção numérica:

<!-- selection-example -->
```yaml
requested: "--topics 3"
eligible_topic_ids:
  - topic_c
  - topic_d
  - topic_a
ignored:
  topic_b: candidate
```

`topic_c` e `topic_d` empatam no score e são ordenados pelo `topic_id`. `topic_b` é filtrado antes da ordenação por não estar pronto.

Antes do primeiro processamento, congele a seleção no `manifest.yaml`, incluindo `run_id`, timestamp, argumento original, score e ordem da fila. Não reordene nem acrescente topics durante a rodada.

O formato mínimo do manifesto é:

<!-- manifest-example -->
```yaml
path: runs/run_20260901_001/manifest.yaml
contract_version: "1"
run_id: run_20260901_001
created_at: "2026-09-01T10:00:00Z"
selection: "--topics 3"
queue_frozen: true
queue:
  - topic_id: topic_c
    position: 1
    score: 92
    status: queued
    current_stage: research-topic
  - topic_id: topic_d
    position: 2
    score: 92
    status: queued
    current_stage: research-topic
  - topic_id: topic_a
    position: 3
    score: 81
    status: queued
    current_stage: research-topic
topics: {}
```

O estado por topic fica em `runs/<run_id>/topics/<topic_id>/state.yaml`:

<!-- state-example -->
```yaml
path: runs/run_20260901_001/topics/topic_c/state.yaml
contract_version: "1"
run_id: run_20260901_001
topic_id: topic_c
status: running
current_stage: write-post
completed_stages:
  - research-topic
  - brief_review_gauntlet
checkpoint:
  stage: brief_review_gauntlet
  cycle: 1
  result:
    decision: approved
    artifact: research/briefs/topic_c.md
  last_artifact: research/briefs/topic_c.md
  input_fingerprint: sha256:4f8d7c2a91b0e6f3d1c5a8b7e2f9d4c6
  paths:
    - research/briefs/topic_c.md
    - runs/run_20260901_001/topics/topic_c/reviews/cycle-01.yaml
  saved_at: "2026-09-01T10:30:00Z"
```

Cada execução também cria:

```text
runs/<run_id>/manifest.yaml
runs/<run_id>/events.yaml
runs/<run_id>/topics/<topic_id>/state.yaml
runs/<run_id>/topics/<topic_id>/reviews/cycle-01.yaml
```

`events.yaml` mantém eventos append-only com a versão do contrato e a chave idempotente:

```yaml
contract_version: "1"
events:
  - event_id: evt_0001
    idempotency_key: [run_20260901_001, topic_c, brief_review_gauntlet, 1]
    stage: brief_review_gauntlet
    cycle: 1
    result_path: runs/run_20260901_001/topics/topic_c/reviews/cycle-01.yaml
```

Cada `reviews/cycle-<NN>.yaml` usa o contrato do revisor:

```yaml
decision: approved
coverage: 1.0
criteria:
  evidence: 9
  author_connection: 10
hard_failures: []
feedback: []
artifact: research/briefs/topic_c.md
```

## Execução sequencial

Processe um topic por vez. Para cada item, chame os stages normativos nesta ordem:

```text
research-topic → brief_review_gauntlet → write-post → critique-post
→ correction_gauntlet → humanize_pass_1 → humanize_review_1
→ humanize_pass_2 → humanize_review_2 → approval_humana
```

Cada stage usa executor e revisor separados. Cada Gauntlet executa no máximo 5 ciclos, só aprova com `coverage >99%` e todos os critérios `>=9/10`; resposta inválida, artefato ausente ou falha de validação bloqueia o topic. `brief_review_gauntlet` exige duas fontes independentes quando disponíveis e conexão explícita com a experiência do autor. `critique-post` produz feedback; a correção acontece no `correction_gauntlet`. `humanize_pass_1` e `humanize_pass_2` são obrigatórios e cada um precisa de seu próprio review.

Não publique nem agende posts nesta skill: nunca chame `publicar-linkedin`.

## Checkpoints, Retomada, Idempotência e Falhas

Depois de cada stage, persista exatamente nesta ordem: `artefato` → `resultado` → `state.yaml` → `evento` em `runs/<run_id>/events.yaml` → `manifesto`. O resultado de cada revisor fica em `runs/<run_id>/topics/<topic_id>/reviews/cycle-<NN>.yaml`, com o schema de review (`decision`, `coverage`, `criteria`, `hard_failures`, `feedback`, `artifact`).

Uma escrita de checkpoint é válida somente quando o YAML parseia, `contract_version` é `"1"`, `run_id` e `topic_id` conferem com o caminho, o `result` existe, `last_artifact` e todos os `paths` são relativos ao workspace e existem, `input_fingerprint` é um SHA-256, a etapa está em `completed_stages` e `saved_at` está presente.

Escreva primeiro em arquivo temporário no mesmo diretório e renomeie atomicamente para `manifest.yaml` ou `state.yaml`. O `manifest.yaml` é imutável depois de `queue_frozen: true`: `requested`, ordem, ids e scores não podem mudar. Ao reiniciar uma rodada, leia o manifesto e retome do último checkpoint válido; se o checkpoint não passar todas as validações, repita somente a etapa incompleta após corrigir o estado, sem recriar a fila.

Cada stage/ciclo usa a chave idempotente `(run_id, topic_id, stage, cycle)`. Se essa chave já tiver artefato, resultado e review válidos, não execute o stage novamente; apenas avance a partir do checkpoint. Uma gravação repetida do mesmo resultado não cria evento, review ou arquivo duplicado nem altera a ordem da fila.

Se uma etapa falhar, registre o erro e o artefato mais recente, marque o topic como `blocked` e persista o checkpoint antes de continuar para o próximo item da fila. Uma falha individual não interrompe a rodada nem libera o topic para a etapa seguinte. Ao final, o manifest deve registrar o resultado de todos os itens, inclusive `blocked`, e a aprovação humana continua sendo necessária antes de qualquer publicação.

Exemplo de falha sem interromper a fila:

<!-- failure-example -->
```yaml
queue:
  - topic_id: topic_a
    status: blocked
  - topic_id: topic_b
    status: completed
execution_order:
  - topic_a
  - topic_b
```

## Sequência Canônica

O lote registra e executa a sequência abaixo exatamente nesta ordem:

<!-- stage-sequence-example -->
```yaml
stages:
  - research-topic
  - brief_review_gauntlet
  - write-post
  - critique-post
  - correction_gauntlet
  - humanize_pass_1
  - humanize_review_1
  - humanize_pass_2
  - humanize_review_2
  - approval_humana
```

`publicar-linkedin` não faz parte da sequência e nunca é chamada por esta skill.

## Checklist Rápido

| Momento | Verificação |
|---|---|
| Seleção | somente `ready_for_research`; score e desempate determinísticos |
| Início | fila congelada em `runs/<run_id>/manifest.yaml` |
| Cada etapa | artefato e estado persistidos antes de avançar |
| Falha | `blocked` persistido; continuar para o próximo topic |
| Fim | aprovação humana registrada; nenhuma publicação automática |

## Erros Comuns

- Processar topics em paralelo ou alterar a fila depois do congelamento.
- Pesquisar um topic que não está `ready_for_research`.
- Pular qualquer review, uma das duas passagens de `escrita-humana` ou a aprovação humana.
- Recomeçar do início em vez de retomar do checkpoint válido.
- Chamar `publicar-linkedin` dentro da rodada.
