---
name: discover-signals
description: Use quando for preciso encontrar sinais relevantes para o pipeline de conteúdo LinkedIn (descoberta diária de 20-50 sinais por frente).
---

# Discover Signals

## Overview

Encontrar acontecimentos, discussões e ideias relacionadas às frentes do projeto, respondendo: "Sobre o que profissionais inteligentes estão discutindo, discordando ou mudando de opinião?" — NÃO "o que está trending?".

## Quando Usar / Quando NÃO Usar

- Usar: descoberta diária de sinais; antes de cluster-signals.
- NÃO usar: criar posts; definir opinião final; inventar dados; resumir apenas notícias populares.

## Entrada

- `config/frentes.yaml` (frentes, prioridades, keywords, research_questions)
- Skill `last30days` (ferramenta primária de pesquisa)
- Busca web manual (webfetch) para imprensa/relatórios quando necessário

## Fluxo

1. Ler `config/frentes.yaml`.
2. Para cada frente (por prioridade), rodar `last30days` com as keywords da frente (uma rodada por frente ou por keyword-chave).
3. Complementar com busca web manual (webfetch) quando a frente exigir imprensa/relatórios (ex.: riscos/compliance, alimentos/sustentabilidade).
4. Para a frente IA Aplicada, aplicar as 7 perguntas de pesquisa (research_questions) ao avaliar cada candidato a signal.
5. Converter cada descoberta relevante em um Signal no formato abaixo.
6. Salvar em `research/signals/signals_YYYY-MM-DD.yaml` (data de hoje).

## Formato do Signal (YAML)

```yaml
id: signal_YYYYMMDD_NNN
title: "Título curto e específico"
pillar:
  - ia_aplicada
source:
  type: article | reddit | hn | youtube | report | linkedin | web
  publisher: Nome
  url: https://...
  published_at: YYYY-MM-DD
observation: "O que foi observado, em uma frase."
debate:
  side_a: "Posição A"
  side_b: "Posição B"
evidence:
  - "Evidência 1 (com fonte)"
  - "Evidência 2 (com fonte)"
possible_angle: "Ângulo possível para o autor"
author_connection: "Conexão com a experiência do autor (memory/professional_experience.md)"
scores:
  freshness: 0-10
  relevance: 0-10
  debate: 0-10
  evidence: 0-10
  author_fit: 0-10
created_at: YYYY-MM-DD
```

## Regras

- 20-50 signals por execução.
- NÃO inventar dados: todo signal tem fonte com URL.
- NÃO escrever posts nem definir opinião final.
- Sinais devem incluir: acontecimentos recentes, discussões com opiniões divergentes, mudanças de comportamento, novas tecnologias, pesquisas recentes, decisões controversas, cases, falhas, aprendizados, novas práticas.
- Para IA Aplicada: distinguir aplicações em produção, pilotos, promessas sem comprovação, resultados mensuráveis e problemas de implantação.
- Usar `pillar` com o nome da frente (chave do YAML de frentes).

## Erros comuns

- Confundir trending com debate real.
- Inventar evidências sem fonte.
- Escrever opinião final do autor no signal.
- Ignorar as 7 perguntas de IA na frente ia_aplicada.
