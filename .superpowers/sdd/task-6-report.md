# Task 6 Report: Skill `discover-signals`

## What I implemented

Created `.agents/skills/discover-signals/SKILL.md` with the exact contents specified in the task brief (verbatim, no modifications). The skill:

- Has valid frontmatter: `name: discover-signals` and `description` starting with "Use quando".
- Covers Overview, Quando Usar / Quando NÃO Usar, Entrada, Fluxo, Formato do Signal (YAML), Regras, Erros comuns (7 `## ` sections).
- Consumes `config/frentes.yaml` and the `last30days` skill as primary research tool.
- Produces `research/signals/signals_YYYY-MM-DD.yaml` with 20-50 signals in the spec §8 format.
- Applies the 7 research_questions for the IA Aplicada frente.
- Enforces "NUNCA inventar dados" (every signal has a source with URL).

## What I tested

Verification commands from the brief:

```
python3 -c "import yaml; d=yaml.safe_load(open('.agents/skills/discover-signals/SKILL.md').read().split('---')[1]); assert d['name']=='discover-signals'; assert d['description'].startswith('Use quando'); print('OK')"
grep -c "^## " .agents/skills/discover-signals/SKILL.md
```

Output:
```
OK
7
```

Both checks passed: frontmatter valid (OK), section count 7 (≥ 6 required).

## Files changed

- Created: `.agents/skills/discover-signals/SKILL.md` (76 lines)

## Self-review findings

- Completeness: SKILL.md created with exact contents from the brief. ✓
- Quality: frontmatter valid (name + description starting with "Use quando"). ✓
- Discipline: no extra files created (YAGNI). ✓
- Verification: frontmatter check OK, section count 7 ≥ 6. ✓
- Did not touch deleted files from the old system or other skills in `.agents/skills/`.

## Issues or concerns

None.
