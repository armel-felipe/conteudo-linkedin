# Remediacao da Falha 3

## Escopo

Remediacao restrita a integracao/documentacao: `editorial_batch.py`,
`run-editorial-batch/SKILL.md`, schemas e testes/relatorio. `gauntlet_loop.py`,
scheduling, `content/approved` e publicacao LinkedIn nao foram alterados.

## Causas-raiz

1. O exemplo do evento documentava `result_path` dentro de `reviews/`, mas o
   contrato canonico grava o resultado em `results/<stage>-cycle-<NN>.yaml`.
2. O exemplo de review usava `evidence` e `author_connection`, que nao fazem
   parte da allowlist normativa de 14 criterios.
3. A validacao de commit aceitava campos extras. Embora um evento contendo
   somente `stage` e `cycle` ja fosse rejeitado, a forma permissiva deixava
   eventos commit-shaped incompletos passarem e contaminarem metricas se
   recebessem dados adicionais.

## TDD

### RED

Testes adicionados antes da correcao:

- `test_commit_event_requires_the_exact_complete_event_shape` falhou porque
  `_valid_commit_event` aceitava um campo extra.
- `test_batch_skill_documents_canonical_result_and_review_paths_and_criteria`
  falhou porque havia `result_path` em `reviews/` e criterios fora da
  allowlist.
- `test_commit_event_with_only_stage_and_cycle_is_not_a_metric_input` passou,
  confirmando a protecao existente contra o caso minimo; foi mantido como
  regressao explicita.

Saida RED: `1 failed` no teste estrutural e `1 failed` no teste documental;
`_update_metrics` nao promoveu o evento incompleto a ciclo.

### GREEN

- `_valid_commit_event` agora exige exatamente os campos canonicos, rejeitando
  payloads incompletos ou com campos extras antes da agregacao.
- Exemplos de skill/schema foram alinhados a `results/`, `reviews/`, paths
  canonicos e aos 14 criterios normativos.

Saida GREEN focada: `2 passed`.

## Validacao Gauntlet

Gate aplicado: ate 5 ciclos, `coverage >= 0.99`, todos os criterios `>=9/10`,
nenhum `hard_failure` e nenhuma questao critica/importante aberta. A rodada de
remediacao foi aprovada no primeiro ciclo de validacao deterministica; nao foi
necessario retry.

## Saidas

- Suíte completa: `171 passed`.
- `git diff --check`: passou.
- Busca por `result_path` incorreto e criterios `evidence`/`author_connection`
  em `run-editorial-batch/SKILL.md`: nenhum resultado.

## Rodada 2

### Causa-raiz

O exemplo de `phase: commit` continha somente identificacao, ciclo e
`result_path`; faltavam `artifact_path`, `review_path`, `committed_at`,
`result` e `review`. Alem disso, `datetime.fromisoformat` aceitava datas sem
hora e timestamps sem timezone, que nao sao commits auditaveis para metricas.

### TDD RED/GREEN

- RED: `test_incomplete_or_naive_commit_timestamps_never_enter_metrics` falhou
  porque timestamp naive era aceito por `_valid_commit_event`.
- GREEN: timestamps exigem ISO-8601 com timezone; eventos incompletos seguem
  fora da agregacao por validacao estrutural.
- O exemplo documental agora contem exatamente todos os campos exigidos e um
  `result`/`review` aprovado com as 14 chaves normativas.

### Validacao

- Focado: aprovado.
- Suíte completa: `170 passed`.
- `git diff --check`: passou.
- Gate: `coverage >= 0.99`, criterios `>=9/10`, zero hard failures e zero
  questoes criticas/importantes; aprovado sem retry adicional.
