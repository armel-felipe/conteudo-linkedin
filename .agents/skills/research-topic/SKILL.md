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
## Research questions da frente
## Limitações da pesquisa
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
9. Responder todas as research questions definidas para a frente, registrando também quando uma pergunta não puder ser respondida.
10. Salvar em `research/briefs/<topic_id>.md`, submeter o brief ao Gauntlet e só atualizar o status do topic para `researched` após aprovação no arquivo `research/topics/topics_*.yaml` correspondente.

## Contrato de revisão do brief

O revisor deve retornar um objeto JSON conforme `docs/schemas/gauntlet-review.json`, sem campos extras. Os campos obrigatórios são `decision` (`approved` ou `feedback`), `coverage` (número entre 0 e 1), `criteria` (objeto não vazio com notas numéricas de 0 a 10), `hard_failures` (lista), `feedback` (lista de objetos com `criterion` e `message`) e `artifact` (caminho relativo não vazio do brief). Em aprovação, `coverage` deve ser `>=0.99`, todos os critérios devem ser `>=9`, `hard_failures` deve ser uma lista vazia e `feedback` deve ser uma lista vazia. Em `feedback`, cada critério abaixo de 9 e a coverage abaixo de 0.99 precisam de feedback acionável. Qualquer `hard_failures` não vazio bloqueia.

## Regras

- NUNCA inventar dados: toda evidência tem fonte/URL/data.
- Separar fato de opinião e de tendência.
- Registrar explicitamente o que NÃO foi verificado (riscos).
- Usar duas fontes independentes quando disponíveis; não contar republicações da mesma apuração como fontes independentes.
- Incluir ao menos uma fonte primária quando disponível. Se não houver, registrar no brief uma justificativa explícita para a ausência e a limitação resultante.
- Responder todas as research questions da frente e registrar a conexão explícita com a experiência profissional do autor.
- Incluir uma seção de limitações com lacunas de cobertura, conflitos entre fontes e grau de confiança.
- O brief precisa da aprovação do Gauntlet antes de ser considerado `researched`; falha ou artefato incompleto mantém o topic bloqueado.
- O brief é a ÚNICA fonte de referência do write-post.
