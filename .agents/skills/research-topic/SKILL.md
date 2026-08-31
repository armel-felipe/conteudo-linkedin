---
name: research-topic
description: Use quando um topic do backlog for escolhido para virar post e precisar de pesquisa aprofundada (gera o research brief).
---

# Pesquisa de Tema

## Overview

Pesquisa aprofundada de um topic escolhido, produzindo um brief confiável com fatos, números, estudos, opiniões, contrapontos e riscos — tudo rastreável.

## Quando Usar / Quando NÃO Usar

- Usar: apenas quando um topic for escolhido para virar post (status ready_for_research).
- NÃO usar: para descobrir sinais (isso é do discover-signals); para escrever o post (isso é do write-post).

## Entrada

- `topic_id` (ex.: topic_20260831_01)
- O topic correspondente em `research/topics/`
- Os signals do topic em `research/signals/`
- Skill `last30days` + busca web manual (webfetch)

## Saída

`research/briefs/<topic_id>.md` (formato da spec §17):

```markdown
# Research Brief

## Tema
## Pergunta
## Tese potencial
## O que está acontecendo
## Evidências
### Evidência 1
Fonte: | URL: | Data:
Resumo:
### Evidência 2
...
## Argumentos favoráveis
## Argumentos contrários
## Pontos ainda incertos
## Conexão com experiência profissional
## Possíveis ângulos
1. 2. 3.
## Riscos de afirmações não verificadas
```

## Fluxo

1. Ler o topic e seus signals.
2. Re-rodar `last30days` no tema (aprofundado).
3. Abrir as URLs dos signals (webfetch) e extrair fatos/números.
4. Buscar imprensa/relatórios/estudos complementares (webfetch).
5. Para IA Aplicada, aplicar as research_questions da frente (em `config/frentes.yaml`).
6. Preencher o brief com TODAS as evidências rastreáveis (fonte, URL, data).
7. Listar argumentos favoráveis e contrários, pontos incertos e riscos.
8. Conectar com memory/professional_experience.md.
9. Salvar em `research/briefs/<topic_id>.md` e atualizar o status do topic para `researched` no arquivo `research/topics/topics_*.yaml` correspondente.

## Regras

- NUNCA inventar dados: toda evidência tem fonte/URL/data.
- Separar fato de opinião e de tendência.
- Registrar explicitamente o que NÃO foi verificado (riscos).
- O brief é a ÚNICA fonte de referência do write-post.
