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
Rejeite seleções numéricas zero ou negativas, seleções que resultem em fila vazia e listas explícitas com IDs duplicados após remover espaços. Uma seleção numérica maior que a quantidade elegível continua válida e seleciona todos os elegíveis.

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
queue_fingerprint: sha256:<64 lowercase hex characters>
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
  result_path: runs/run_20260901_001/topics/topic_c/results/brief_review_gauntlet-cycle-01.yaml
  last_artifact: research/briefs/topic_c.md
  input_fingerprint: sha256:4f8d7c2a91b0e6f3d1c5a8b7e2f9d4c6
  paths:
    - research/briefs/topic_c.md
    - runs/run_20260901_001/topics/topic_c/results/brief_review_gauntlet-cycle-01.yaml
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
    phase: commit
    idempotency_key: [run_20260901_001, topic_c, brief_review_gauntlet, 1]
    stage: brief_review_gauntlet
    cycle: 1
    artifact_path: research/briefs/topic_c.md
    result_path: runs/run_20260901_001/topics/topic_c/results/brief_review_gauntlet-cycle-01.yaml
    review_path: runs/run_20260901_001/topics/topic_c/reviews/cycle-01.yaml
    committed_at: "2026-09-01T10:30:00+00:00"
    result:
      decision: approved
      artifact: research/briefs/topic_c.md
    review:
      decision: approved
      coverage: 1.0
      criteria:
        clareza: 10
        força da abertura: 10
        originalidade: 10
        credibilidade: 10
        uso de evidências: 10
        risco de alucinação: 10
        tom humano: 10
        densidade: 10
        relevância: 10
        consistência com a voz do autor: 10
        estrutura obrigatória: 10
        pergunta final: 10
        tamanho editorial: 10
        rastreabilidade das fontes: 10
      hard_failures: []
      feedback: []
      artifact: research/briefs/topic_c.md
```

Cada `reviews/cycle-<NN>.yaml` usa o contrato do revisor. O `result_path` aponta sempre para `results/<stage>-cycle-<NN>.yaml`; o `review_path` aponta para `reviews/cycle-<NN>.yaml`.

```yaml
decision: approved
coverage: 1.0
criteria:
  clareza: 10
  força da abertura: 10
  originalidade: 10
  credibilidade: 10
  uso de evidências: 10
  risco de alucinação: 10
  tom humano: 10
  densidade: 10
  relevância: 10
  consistência com a voz do autor: 10
  estrutura obrigatória: 10
  pergunta final: 10
  tamanho editorial: 10
  rastreabilidade das fontes: 10
hard_failures: []
feedback: []
artifact: research/briefs/topic_c.md
```

## Execução sequencial

Processe um topic por vez. Para cada item, chame os stages normativos nesta ordem:

```text
research-topic → brief_review_gauntlet → write-post → critique-post
→ correction_gauntlet → humanize_pass_1 → humanize_review_1
→ humanize_pass_2 → humanize_review_2
```

Cada stage usa executor e revisor separados. Cada Gauntlet executa no máximo 5 ciclos, só aprova com `coverage >= 0.99` e todos os critérios `>=9/10`; resposta inválida, artefato ausente ou falha de validação bloqueia o topic. `brief_review_gauntlet` exige duas fontes independentes quando disponíveis e conexão explícita com a experiência do autor. `critique-post` produz feedback; a correção acontece no `correction_gauntlet`. `humanize_pass_1` e `humanize_pass_2` são obrigatórios e cada um precisa de seu próprio review.

O stage recebido deve ser igual ao `current_stage` persistido e todos os stages anteriores devem estar em `completed_stages`; execução fora de ordem é rejeitada. Depois de `humanize_review_2` (stage terminal do lote), `state.yaml` e o item da fila passam a `completed`, `current_stage` passa a `null`. **O lote termina no draft em revisão (`drafted`); ele NÃO marca `approved`** — a aprovação é decisão humana no QA (`qa-draft`), que acontece junto com o agendamento.

Se todos os stages de um topic já estiverem terminalizados com estado consistente, a retomada retorna o resultado estruturado `already_complete` e não executa callback, grava evento duplicado nem altera manifesto ou métricas. Quando a fila congelada não contém itens pendentes, o lote retorna `completed` estruturado. Estado `completed` incompleto ou divergente continua fail-closed como `completed_state_integrity`.

Não publique nem agende posts nesta skill: nunca chame `publicar-linkedin`.

## Checkpoints, Retomada, Idempotência e Falhas

Depois de cada stage, persista exatamente nesta ordem: `artefato` → `resultado` → `state.yaml` → `evento` em `runs/<run_id>/events.yaml` → `manifesto`. O resultado de cada revisor fica em `runs/<run_id>/topics/<topic_id>/reviews/cycle-<NN>.yaml`, com o schema de review (`decision`, `coverage`, `criteria`, `hard_failures`, `feedback`, `artifact`).

Uma escrita de checkpoint é válida somente quando o YAML parseia, `contract_version` é `"1"`, o status é conhecido, `run_id` e `topic_id` conferem com o caminho, o `result` contém o `artifact` correto e o `review` completo passa o gate, `last_artifact`, `result_path`, `review_path` e todos os `paths` são caminhos canônicos, relativos, sem `.`/`..`, dentro do workspace e existentes, `input_fingerprint` é um SHA-256, a etapa está em `completed_stages`, `current_stage` é consistente com o status terminal e `saved_at` está presente. Um estado `completed` também exige manifesto, commit, result, review, fingerprint e paths convergentes; ausência ou divergência gera o erro estruturado `completed_state_integrity`, preserva estado/manifesto/eventos/métricas e não vira `blocked`.

Escreva primeiro em arquivo temporário no mesmo diretório e renomeie atomicamente para cada artefato, resultado, `state.yaml`, `events.yaml`, review e `manifest.yaml`. O `manifest.yaml` é imutável depois de `queue_frozen: true`: `selection`, ordem, ids e scores não podem mudar. A gravação usa eventos `intent` e `commit`: se houver interrupção entre arquivos, um novo início detecta o `intent`, valida os arquivos existentes, completa somente o stage pendente e grava um único `commit` antes do manifesto. O `intent` também registra `artifact_fingerprint`, calculado antes da primeira escrita. A recuperação só completa quando artefato, resultado, review e fingerprint conferem integralmente; arquivos já válidos não são reescritos. Intent incompleto, resultado/review órfão, commit sem intent ou arquivo temporário produzem `blocked` com `failure_reasons` estruturados e preservam todos os arquivos. Nunca apague dados para corrigir um ciclo parcial. Ao reiniciar uma rodada, leia o manifesto e retome do último checkpoint válido; se o checkpoint não passar todas as validações, repita somente a etapa incompleta após corrigir o estado, sem recriar a fila.

Cada stage/ciclo usa a chave idempotente `(run_id, topic_id, stage, cycle)`. Se essa chave já tiver commit canônico, artefato, resultado, review e checkpoint válidos, não execute o stage novamente; qualquer divergência de payload, fingerprint, caminho ou evento bloqueia. Uma gravação repetida do mesmo resultado não cria evento, review ou arquivo duplicado nem altera a ordem da fila. O `intent` inclui e valida os paths, `result`, `review` e `artifact_fingerprint` do payload recebido; nunca autoriza sobrescrever um ciclo parcial divergente.

### Retomada e métricas do manifesto

Every stage writes an event after its artifact and state are valid. Every reviewer result is saved per cycle, including feedback and hard failures. A resumed run skips only stages with valid artifacts and passing reviews; **Never rerun an approved topic automatically**. If an approved topic needs new work, start a new run with an explicit selection.

The run manifest also records these metrics for the complete frozen queue. Only complete canonical commit events with valid `event_id`, timestamp, paths, `result.artifact == artifact_path`, an existing regular non-empty review file when the workspace root is available, a complete review and passing gate contribute; malformed or incomplete commit-shaped events are rejected and never affect metrics:

```yaml
metrics:
  queue_size: 3
  completed: 2
  blocked: 1
  cycles_per_stage:
    brief_review_gauntlet: 2
  reviewer_coverage: 1.0
  human_writing_conformity: 1.0
  time_to_approval: "PT42M"
```

The metric keys mean queue size, completed and blocked topics, cycles per stage, reviewer coverage, human-writing conformity, and elapsed time to draft completion. `reviewer_coverage` is the arithmetic mean of `coverage` from every persisted review event in the run; `human_writing_conformity` is the arithmetic mean from only `humanize_review_1` and `humanize_review_2`; `cycles_per_stage` is the highest cycle number committed for each stage; and `time_to_approval` is the ISO-8601 duration from manifest `created_at` to the `humanize_review_2` commit timestamp, or `null` before the draft is complete. Metrics are updated in the manifest without changing the frozen queue.

Se uma etapa falhar por execução ou revisão, registre o erro, fingerprint do artefato, último review, feedback e `cycle_count`, marque o topic como `blocked` e persista o checkpoint antes de continuar para o próximo item da fila. Ao retomar, preserve esses campos e recomece no mesmo `current_stage` sem zerar ciclos ou feedback. Uma falha individual não interrompe a rodada nem libera o topic para a etapa seguinte. Corrupção ou divergência de um estado já `completed` é terminal `completed_state_integrity`: não altera arquivos, métricas ou callbacks e não pode ser reclassificada como `blocked`. Ao final, o manifest deve registrar o resultado de todos os itens, inclusive `blocked`, e a aprovação humana continua sendo necessária antes de qualquer publicação.

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
```

`publicar-linkedin` não faz parte da sequência e nunca é chamada por esta skill.

Scheduling remains outside this batch and belongs to the separate LinkedIn publishing plan. The batch finishes with `humanize_review_2` (draft em revisão); publication or scheduling requires an explicit later call to `publicar-linkedin`, preceded by human approval in the QA (`qa-draft`).

## Checklist Rápido

| Momento | Verificação |
|---|---|
| Seleção | somente `ready_for_research`; score e desempate determinísticos |
| Início | fila congelada em `runs/<run_id>/manifest.yaml` |
| Cada etapa | artefato e estado persistidos antes de avançar |
| Falha | `blocked` persistido; continuar para o próximo topic |
| Fim | draft em revisão (`drafted`) registrado; nenhuma publicação automática |

## Erros Comuns

- Processar topics em paralelo ou alterar a fila depois do congelamento.
- Pesquisar um topic que não está `ready_for_research`.
- Pular qualquer review ou uma das duas passagens de `escrita-humana`.
- Marcar `approved` dentro do lote — aprovação é decisão humana no QA (`qa-draft`).
- Recomeçar do início em vez de retomar do checkpoint válido.
- Chamar `publicar-linkedin` dentro da rodada.
