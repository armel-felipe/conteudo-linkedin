# Task 4 — Comparação paralela de scoring

## Status

`inconclusive`

Foi adicionada a interface pura `run_scoring(topics, weights)` em `score_opportunities.py`. Ela reutiliza a fórmula existente, aceita pesos explícitos, não altera os pesos ativos e retorna ordenação determinística por score total decrescente e `id` crescente em empates.

O relatório congelado está em `research/audits/scoring-parallel-2026-09-06.yaml`. A mesma amostra de cinco tópicos foi executada com os pesos atuais e com uma alternativa que prioriza evidência e relevância. A alternativa move `topic_20260901_03` da posição 3 para 2 e `topic_20260901_01` da posição 2 para 3; os demais permanecem no mesmo lugar.

## Amostra e método

Fonte única: `research/topics/topics_scored_2026-09-06.yaml`.

Fingerprint SHA-256: `sha256:df42334e58ce9a26222a768eb7bad4242833508b608992ffda7d2f8e8ddb0843`.

Os valores de entrada foram preservados. Não foram coletadas métricas, usado engagement ou alterados os pesos de `config/scoring.yaml`. A convenção de `rank_delta` é `current_rank - alternative_rank`: valor positivo indica subida no ranking alternativo; valor negativo indica queda.

## Rankings

| Rank atual | Tópico | Score atual | Rank alternativo | Score alternativo | Movimento |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `topic_20260901_02` | 69.75 | 1 | 75.12 | 0 |
| 2 | `topic_20260901_01` | 67.50 | 3 | 72.50 | -1 |
| 3 | `topic_20260901_03` | 65.70 | 2 | 72.70 | +1 |
| 4 | `topic_20260901_04` | 63.63 | 4 | 68.00 | 0 |
| 5 | `topic_20260901_05` | 58.75 | 5 | 63.25 | 0 |

## Critérios causadores

O principal ganho relativo da alternativa vem de `evidence` e `relevance`. As perdas vêm de `freshness` e `linkedin_fit`; `debate` e `originality` não mudam, e `author_fit` permanece zerado em todos os tópicos. A subida do tópico 3 ocorre porque ele tem evidência 6 contra 5 do tópico 1, enquanto mantém relevância suficiente para superar a diferença após a troca de pesos.

## Recomendação conservadora

`inconclusive`. Não substituir os pesos atuais. A comparação é útil como teste de sensibilidade, mas uma amostra de cinco tópicos, sem métricas de resultado e com `author_fit: 0` em todos os registros, não sustenta uma mudança operacional. Se houver interesse, a alternativa pode ser testada em uma rodada futura isolada, com amostra congelada própria e aprovação explícita, sem alterar o scoring ativo neste task.

## Testes

1. Comando solicitado:
   `PYTHONPATH=. pytest -q tests/test_score_opportunities.py tests/test_p2_3_audits.py`
2. Output:
   `........ [100%]`
   `8 passed in 0.07s`

## Concerns

- O relatório compara ranking e sensibilidade, não eficácia editorial; não há outcome independente nesta amostra.
- O arquivo de entrada já contém totais persistidos; a interface recalcula os totais pela fórmula ativa, resultando em `63.63` para o tópico 4.
- A alternativa é deliberadamente diagnóstica e não foi ativada.
- Alterações preexistentes no worktree foram preservadas.

## Verificação final

Comando executado:

`PYTHONPATH=. pytest -q tests/test_score_opportunities.py tests/test_p2_3_audits.py`

Output:

```text
........                                                                 [100%]
8 passed in 0.07s
```
