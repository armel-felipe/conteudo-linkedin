# Task 5 Report — AGENTS.md (contrato de operação)

## What I implemented

Created `AGENTS.md` at the repo root with the exact contents from the task brief:
- Projeto (pipeline agentico manual, fluxo completo)
- 7 regras centrais (nunca começar por "sobre o que escrever?", artefatos persistentes, pesquisa separada de redação, LinkedIn complementar, specs de post, escrita-humana, nunca inventar dados)
- Skills section referencing `mapa.md`
- Estrutura (config/, research/, content/, memory/)
- Segurança (.env/credenciais, publicação via browser OpenWork)
- Estados de conteúdo (discovered → … → archived)

The old AGENTS.md was already deleted in the working tree (part of the project restart). The new file replaces it; the commit records the deletion + new content as a modification, which is correct per the task.

## What I tested

Verification command from the brief:
```
grep -c "mapa.md" AGENTS.md
```
Output: `1` (≥1 reference to `mapa.md` — PASS)

Additionally verified the file content is byte-identical to the brief's code block (diff excluding the markdown fences): `MATCH: content identical to brief`.

## Files changed

- `AGENTS.md` (created, 35 lines)

## Commit

- `8baac43` — docs: contrato de operação (AGENTS.md)

## Self-review

- Completeness: AGENTS.md created with exact contents — PASS
- Quality: 7 regras centrais, referência a mapa.md, estrutura, segurança, estados — all present — PASS
- Discipline: no extra files created (YAGNI) — PASS
- Verification: grep -c "mapa.md" → 1 — PASS

## Issues / concerns

None. Note: the commit shows "35 insertions, 35 deletions" because git tracked the new AGENTS.md as a modification of the deleted old one — expected and correct.
