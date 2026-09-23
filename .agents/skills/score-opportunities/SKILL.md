---
name: score-opportunities
description: Use quando houver topics candidatos que precisem ser pontuados e ranqueados no backlog (etapa 2x/semana do pipeline de conteúdo LinkedIn).
---

# Pontuação de Oportunidades

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

score = (freshness*0.15 + relevance*0.20 + debate*0.15 + evidence*0.10 + author_fit*0.20 + originality*0.10 + linkedin_fit*0.10) * 10 → 0-100

Cada critério é avaliado de 0 a 10; a soma ponderada (máximo 10) é multiplicada por 10 para o score final em escala 0-100.

## Saída

Duas saídas obrigatórias:

1. `content/backlog.md` (formato da spec §15)
2. `research/topics/topics_YYYY-MM-DD.html` — **visualização navegável dos temas (obrigatória)**

### HTML de temas (obrigatório)

Ao fim da pontuação, gerar `research/topics/topics_YYYY-MM-DD.html` com um card por topic contendo: score em destaque, título, `topic_id`, pilar(es), tese, pergunta central, barras dos 7 critérios, nº de sinais, conexão com o autor e links para os artefatos (`topics_*.yaml`, `signals_*.yaml`, `content/backlog.md`). Separar visualmente os temas `ready_for_research` dos `candidate`. O arquivo é versionado junto com os topics. Sem ele, a etapa não está concluída.

### Backlog

`content/backlog.md` (formato da spec §15):

```markdown
# Content Backlog

## 92 — Título do tema

Pilares: IA Aplicada / Logística

Tese: ...

Por que agora: ...

Evidências disponíveis: N

Experiência pessoal relacionada: Alta | Média | Baixa

Status: ready_for_research
```

## Fluxo

1. Ler topics e scoring.yaml.
2. Pontuar cada topic nos 7 critérios (0-10).
3. Calcular o score final (fórmula acima).
4. Ordenar por score decrescente.
5. Escrever o backlog com os top 5-10.
6. Atualizar o status do topic para `ready_for_research` no arquivo `research/topics/topics_*.yaml` quando entrar no backlog.
7. Gerar `research/topics/topics_YYYY-MM-DD.html` com a visualização navegável dos temas (obrigatório).

## Regras

- Pontuar com base nas evidências reais do topic (não no potencial imaginado).
- author_fit alto exige conexão real com memory/professional_experience.md.
- Não inflar notas para "empurrar" um tema favorito.
- O HTML de temas é obrigatório e versionado: sem ele, a etapa não está concluída.
