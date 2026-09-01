# Remediação da Falha 2

## Escopo

Execução iniciada com Loop Gauntlet de no máximo cinco rodadas. `gauntlet_loop.py`, agendamento, artefatos editoriais e publicação não foram alterados.

## Investigação de causa raiz

1. Idempotência confiava na existência de arquivos e no checkpoint, mas o commit não carregava cópias canônicas de `result` e `review`.
2. Recuperação de `intent` escrevia arquivos preexistentes sem compará-los com o payload do ciclo.
3. Transições aceitavam `blocked` e estados terminais inconsistentes.
4. Checkpoints e eventos validavam somente parte dos IDs e caminhos.
5. `_update_metrics` tratava qualquer evento `commit` com `stage`, `cycle` ou `coverage` como real.
6. `_valid_review` verificava apenas a estrutura, não o gate editorial.
7. Manifesto congelado não tinha fingerprint da fila imutável.
8. Métricas eram calculadas a partir de eventos não autenticados por payloads persistidos.

## TDD e reproduções

Foram adicionados testes focados em `tests/test_batch_skill.py` para cada falha: review adulterado, recuperação parcial divergente, estados terminal/blocked, paths e IDs, commit incompleto, review abaixo do gate, adulteração do manifesto e métricas canônicas. Cada reprodução foi executada antes da correção e apresentou falha esperada.

## Correções mínimas

- Fingerprint SHA-256 da fila imutável (`topic_id`, `position`, `score`) e validação de IDs, posições, status e estágio.
- Checkpoint exige `review`, `review_path` e lista canônica de paths, além de consistência entre status e `current_stage`.
- Commit persiste e valida `result` e `review`; divergências bloqueiam idempotência.
- Recuperação com `intent` não sobrescreve arquivos parciais divergentes.
- Estados `blocked` e `completed` não transitam; bloqueio exige estágio canônico.
- Eventos commit incompletos são rejeitados; métricas usam somente commits completos.
- `persist_stage` aplica `approved`, cobertura mínima de `0.99`, critérios no mínimo `9`, zero hard failure e zero feedback aberto.

## Rodada 2

Os achados P1 foram reproduzidos antes das alterações com regressões de ausência de gravação, paths `..`, intent divergente, status desconhecido, evento incompleto e checkpoint sem gate. A correção valida result/review/gate antes de qualquer escrita, rejeita paths não canônicos, inclui payload no intent, valida `event_id`/timestamp/review e recalcula métricas exclusivamente com commits válidos. `checkpoint_valid` reaplica o gate editorial completo.

## Verificação Gauntlet

- Gate: `coverage >= 0.99`.
- Gate: nenhum `hard_failure`.
- Gate: nenhuma questão crítica/importante aberta.
- Limite: até cinco rodadas; sem alteração em `gauntlet_loop.py`.
