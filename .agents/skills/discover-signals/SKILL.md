---
name: discover-signals
description: Use quando for preciso encontrar sinais relevantes para o pipeline de conteúdo LinkedIn (descoberta diária de 20-50 sinais).
---

# Descoberta de Sinais

## Overview

Encontrar acontecimentos, discussões e ideias relacionadas às frentes do projeto, respondendo: "Sobre o que profissionais inteligentes estão discutindo, discordando ou mudando de opinião?" — NÃO "o que está trending?".

## Quando Usar / Quando NÃO Usar

- Usar: descoberta diária de sinais; antes de cluster-signals.
- NÃO usar: criar posts; definir opinião final; inventar dados; resumir apenas notícias populares.

## Entrada

- `config/frentes.yaml` (frentes, prioridades, keywords, research_questions, exploratory_questions)
- Skill `last30days` (ferramenta primária de pesquisa)
- Busca web manual (webfetch) para imprensa/relatórios quando necessário

## Fluxo

1. Ler `config/frentes.yaml`.
2. Em modo diversidade, dividir aproximadamente metade das queries entre as keywords atuais e metade entre as `exploratory_questions` da frente. As perguntas devem buscar mudança, conflito, consequência, comportamento, redistribuição de poder ou prática contraintuitiva, sempre com recência e evidência.
3. Para cada frente (por prioridade), rodar `last30days` com as queries selecionadas (uma rodada por frente ou por pergunta-chave).
4. Complementar com busca web manual (webfetch) quando a frente exigir imprensa/relatórios (ex.: riscos/compliance, alimentos/sustentabilidade).
5. Para a frente IA Aplicada, aplicar as perguntas de pesquisa (research_questions) da frente, conforme `config/frentes.yaml` ao avaliar cada candidato a signal.
6. Classificar, quando houver evidência suficiente, `diversity.context`, `diversity.mechanism`, `diversity.actor` e `diversity.change_type`. Se não houver segurança, usar `unknown`; não inventar classificação.
7. Converter cada descoberta relevante em um Signal no formato abaixo.
8. Salvar em `research/signals/signals_YYYY-MM-DD.yaml` (data de hoje).

## Formato do Signal (YAML)

```yaml
id: signal_YYYYMMDD_NNN
title: "Título curto e específico"
pillars:
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
  originality: 0-10
  linkedin_fit: 0-10
created_at: YYYY-MM-DD
status: discovered
diversity:
  context: [varejo]
  mechanism: [confianca]
  actor: [gestor]
  change_type: [falha]
```

## Regras

- 20-50 signals por execução.
- NÃO inventar dados: todo signal tem fonte com URL.
- NÃO escrever posts nem definir opinião final.
- Sinais devem incluir: acontecimentos recentes, discussões com opiniões divergentes, mudanças de comportamento, novas tecnologias, pesquisas recentes, decisões controversas, cases, falhas, aprendizados, novas práticas.
- Para IA Aplicada: distinguir aplicações em produção, pilotos, promessas sem comprovação, resultados mensuráveis e problemas de implantação.
- Usar `pillars` com o nome da frente (chave do YAML de frentes).
- O modo diversidade varia o mecanismo e o recorte dentro da mesma frente; não cria sinais genéricos ou evergreen.

## Erros comuns

- Confundir trending com debate real.
- Inventar evidências sem fonte.
- Escrever opinião final do autor no signal.
- Ignorar as research_questions da frente ia_aplicada.
