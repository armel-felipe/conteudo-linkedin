# Task 3 — Comparação de scores com decisões editoriais

## Status

`inconclusive`

O artefato foi corrigido em `research/audits/scoring-comparison-2026-09-06.yaml`. A amostra contém cinco tópicos. Quatro têm divergência entre o status do score e o status do backlog; todos os casos permanecem `inconclusive`. O status agregado é `inconclusive` porque não existe resultado editorial independente e comparável para todos os tópicos.

## Escopo e fontes

Foram usados somente artefatos persistidos:

- `research/topics/topics_scored_2026-09-06.yaml`: scores congelados e statuses dos tópicos.
- `content/backlog.md`: confirmação dos itens e status persistido no backlog.
- `research/briefs/topic_20260901_03.md`: evidências e limitações do tópico 3.
- `research/briefs/topic_20260901_04.md`: evidências e limitações do tópico 4.
- `research/audits/source-quality-2026-09-06.yaml`: auditoria de qualidade das fontes do tópico 4.

Não foram usados engagement, métricas de LinkedIn, inferências a partir de conteúdo não persistido ou alteração de topics, signals ou posts.

O fingerprint congelado dos arquivos, concatenados na ordem registrada no YAML e sem separadores, é `sha256:09a8624dbd8441478bd5092586bf8f1c01aaef604fa090a427de726c2cbc2541`.

## Comparação

| Topic | Score previsto | `score_status` | `backlog_status` | Qualidade observada | Classificação |
| --- | ---: | --- | --- | --- | --- |
| `topic_20260901_01` | 67.5 | `approved` | `ready_for_research` | `unresolved` | `inconclusive` |
| `topic_20260901_02` | 69.75 | `approved` | `ready_for_research` | `not_observed` | `inconclusive` |
| `topic_20260901_03` | 65.7 | `approved` | `ready_for_research` | `strong_verified_mechanisms` | `inconclusive` |
| `topic_20260901_04` | 63.63 | `approved` | `ready_for_research` | `weak_public_evidence` | `inconclusive` |
| `topic_20260901_05` | 58.75 | `ready_for_research` | `ready_for_research` | `not_observed` | `inconclusive` |

### `topic_20260901_01`

O score está `approved`, mas o backlog permanece `ready_for_research`. Não há brief nem auditoria de fontes deste tópico. A divergência e a qualidade observada não podem ser resolvidas, então o caso é `inconclusive`.

Referências: `research/topics/topics_scored_2026-09-06.yaml:2-27`; `content/backlog.md:3-15`.

### `topic_20260901_02`

É o maior score da amostra (`69.75`), mas o score está `approved` enquanto o backlog permanece `ready_for_research`. Os artefatos persistidos não trazem brief ou auditoria de fontes. A ausência de evidência não prova qualidade fraca; o caso foi reclassificado como `inconclusive`.

Referências: `research/topics/topics_scored_2026-09-06.yaml:28-51`; `content/backlog.md:3-15`.

### `topic_20260901_03`

O score está `approved`, mas o backlog permanece `ready_for_research`. O brief e as fontes persistidas verificam mecanismos técnicos de governança, incluindo artefatos, isolamento e observabilidade, mas isso não mede adoção, impacto ou qualidade editorial contra um resultado independente. O caso é `inconclusive`.

Referências: `research/topics/topics_scored_2026-09-06.yaml:52-74`; `research/briefs/topic_20260901_03.md:17-36`; `research/briefs/topic_20260901_03.md:68-81`.

### `topic_20260901_04`

O score está `approved`, mas o backlog permanece `ready_for_research`. O brief descreve painéis, promoção comercial e relatos sem métricas independentes de adoção. A auditoria confirma limitações de verificabilidade e qualidade em parte das fontes. O caso permanece `inconclusive`.

Referências: `research/topics/topics_scored_2026-09-06.yaml:75-98`; `research/briefs/topic_20260901_04.md:15-20`; `research/briefs/topic_20260901_04.md:91-114`; `research/audits/source-quality-2026-09-06.yaml:18-85`.

### `topic_20260901_05`

O score é o menor da amostra (`58.75`), mas o tópico ainda está `ready_for_research` e não possui brief ou auditoria de fontes observável. Não há base persistida para afirmar qualidade forte ou fraca, portanto o caso é `inconclusive`.

Referências: `research/topics/topics_scored_2026-09-06.yaml:99-120`; `content/backlog.md:59-71`.

## Concerns

- Quatro tópicos divergem entre `score_status` e `backlog_status`; todos os casos afetados foram classificados como `inconclusive`.
- A ausência de brief ou auditoria não foi usada como prova de qualidade fraca; por isso `topic_20260901_02` não é `false_positive`.
- A amostra não contém um tópico de score baixo com evidência forte e verificada; por isso nenhum `false_negative` foi atribuído.
- Os briefs disponíveis cobrem apenas os tópicos 3 e 4; a ausência dos demais foi tratada como incerteza, não como evidência negativa.
- A auditoria de fontes disponível tem escopo principal no tópico 4; seus resultados não foram extrapolados para os outros tópicos.
- `author_fit: 0` aparece em todos os tópicos congelados e reduz a capacidade de comparar o score com desempenho observado.

## Testes

1. RED confirmado antes do artefato:
   `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py::test_scoring_comparison_is_frozen_and_labels_uncertainty`
   Resultado: falhou com `FileNotFoundError` porque `research/audits/scoring-comparison-2026-09-06.yaml` não existia.
2. GREEN confirmado depois do artefato:
   Mesmo comando.
   Resultado: `1 passed`.
3. O teste adicionado em `tests/test_p2_3_audits.py` verifica fingerprint recalculado, `sample_paths` existentes, campos/status/classificações permitidos, referências não vazias e ausência de `engagement`.
4. Suíte completa:
   `PYTHONPATH=. pytest -q`
   Resultado: `286 passed, 2 failed`. As falhas estão fora do escopo, em `tests/test_scheduling_checklist.py::test_checklist_registration_gate_has_explicit_types_and_failure_state` e `tests/test_scheduling_skill.py::test_manual_scheduling_matrix_and_receipt_are_non_sensitive_and_complete`, relacionadas a artefatos de scheduling já alterados no worktree.

5. Verificação final desta correção:
   `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py`
   Resultado: `3 passed`.

## Correção da revisão final

- Cada tópico agora possui `editorial_decision`: divergências entre `score_status` e `backlog_status` recebem `inconclusive`; o tópico 5 preserva `ready_for_research` porque os status coincidem.
- `score_status` e `backlog_status` foram preservados.
- O teste exige `editorial_decision`, verifica sua consistência com os status persistidos, reconcilia as listas do resumo com as classificações individuais, valida referências que são paths existentes e exige justificativa estrutural para classificações `inconclusive`.
- `summary.inconclusive_topics` permanece exatamente alinhado aos cinco tópicos classificados como `inconclusive`.

### Teste solicitado

Comando:

```text
PYTHONPATH=. pytest -q tests/test_p2_3_audits.py
```

Saída:

```text
...                                                                      [100%]
3 passed in 0.06s
```
