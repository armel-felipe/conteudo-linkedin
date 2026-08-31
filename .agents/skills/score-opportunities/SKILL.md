---
name: score-opportunities
description: Use quando houver topics candidatos que precisem ser pontuados e ranqueados no backlog (etapa 2x/semana do pipeline de conteúdo LinkedIn).
---

# Score Opportunities

## Overview

Pontuar cada Topic candidato (0-10 por critério) e gerar o backlog ranqueado de oportunidades de conteúdo.

## Quando Usar / Quando NÃO Usar

- Usar: 2x/semana, após cluster-signals.
- NÃO usar: para pontuar signals individuais (só topics).

## Entrada

- `research/topics/topics_*.yaml`
- `config/scoring.yaml` (pesos)

## Critérios (0-10 cada)

freshness, relevance, debate, evidence, author_fit, originality, linkedin_fit

## Fórmula

score = freshness*0.15 + relevance*0.20 + debate*0.15 + evidence*0.10 + author_fit*0.20 + originality*0.10 + linkedin_fit*0.10 → 0-100

## Saída

`content/backlog.md` (formato da spec §15):

```markdown
# Content Backlog

## 92 — Título do tema

Pilares: IA Aplicada / Logística

Tese: ...

Por que agora: ...

Evidências disponíveis: N

Experiência pessoal relacionada: Alta | Média | Baixa

Status: Ready for research
```

## Fluxo

1. Ler topics e scoring.yaml.
2. Pontuar cada topic nos 7 critérios (0-10).
3. Calcular o score final (fórmula acima).
4. Ordenar por score decrescente.
5. Escrever o backlog com os top 5-10.
6. Atualizar o status do topic para `ready_for_research` quando entrar no backlog.

## Regras

- Pontuar com base nas evidências reais do topic (não no potencial imaginado).
- author_fit alto exige conexão real com memory/professional_experience.md.
- Não inflar notas para "empurrar" um tema favorito.
