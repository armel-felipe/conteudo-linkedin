---
name: write-post
description: Use quando um research brief estiver pronto e for preciso escrever o post do LinkedIn.
---

# Escrita do Post

## Overview

Escrever o post a partir do brief e da memória do autor. O writer NÃO pesquisa — escreve apenas com o material recebido.

## Quando Usar / Quando NÃO Usar

- Usar: quando o brief existir (status researched).
- NÃO usar: sem brief; para pesquisar (isso é do research-topic).

## Entrada obrigatória

- `research/briefs/<topic_id>.md`
- `memory/professional_experience.md`
- `memory/opinions.md`
- `memory/writing_style.md`

## Saída

`content/drafts/<topic_id>.md` — o post pronto para revisão.

> **Organização de arquivos:** o draft nasce e permanece em `content/drafts/`. O `approved` é um marco editorial lógico que **o humano carimba no QA (`qa-draft`)**, NÃO uma pasta de destino e NÃO algo que o writer decide: o arquivo não é movido para `content/approved/`. Ele só sai de `content/drafts/` quando for agendado/publicado (vai para `content/published/`) ou descartado por decisão humana (vai para `content/arquived/`).

## Regras de escrita

Aplicar integralmente `docs/guia-escrita.md`, fonte única das regras editoriais. Usar também a voz e as opiniões de `memory/professional_experience.md`, `memory/opinions.md` e `memory/writing_style.md`.

## Leitor-alvo e completude narrativa

Ver `docs/guia-escrita.md` (seções 3, 4, 5 e 9b) para leitor-alvo, completude narrativa, estrutura, variação de abertura, clareza operacional, percentuais e termos métricos.

## Contrato de revisão

O revisor deve retornar um objeto JSON conforme `docs/schemas/gauntlet-review.json`, sem campos extras. Além dos critérios, uma aprovação de artefato editorial exige `evidence` com contexto do leitor, cadeia causal, decisão, consequência, limites e anchors literais do texto. Em aprovação, `coverage` deve ser `>= 0.99`, todos os critérios devem ser `>=9`, `hard_failures` deve ser uma lista vazia e `feedback` deve ser uma lista vazia. Qualquer `hard_failures` não vazio bloqueia.

## Critérios normativos do post

Usar os critérios, gates e evidências definidos em `docs/guia-escrita.md` e `docs/schemas/gauntlet-review.json`. O writer não pode avançar com critério abaixo do mínimo ou `hard_failures`.

Depois da correção no Gauntlet, executar obrigatoriamente duas passagens separadas de `escrita-humana`: `humanize_pass_1` → `humanize_review_1` → `humanize_pass_2` → `humanize_review_2`. Cada passagem deve ter seu próprio revisor e retornar o mesmo contrato JSON, com `artifact` relativo ao draft da passagem. Cada passagem precisa de aprovação independente; `hard_failures` de escrita-humana sobrepõem a pontuação agregada de 95% e bloqueiam a aprovação.

## O que evitar

- Frases genéricas de IA: "Em um mundo cada vez mais...", "A inteligência artificial veio para...", "Mais do que nunca...", "Não é sobre X, é sobre Y...".
- Posts conceituais sem experiência concreta.
- Afirmações sem evidência no brief.

## Fluxo

1. Ler o brief e os 3 arquivos de memória.
2. Escolher o ângulo (dos "Possíveis ângulos" do brief) com melhor conexão com a experiência do autor.
3. Escrever o post seguindo o esqueleto e as regras.
4. **Verificar completude narrativa:** cada caso citado responde os 4 batimentos (promessa → quebra → reação → custo) e se sustenta para um leitor que não conhece a fonte. Caso incompleto: completar com material do brief ou remover.
5. Verificar tamanho: faixa preferencial de 900–1500 caracteres, aceitando até 3000 caracteres totais, incluindo `## Fontes`, quando o contexto exigir.
6. Adicionar a seção `## Fontes` ao final do post, com as fontes usadas (título, URL, data) extraídas das evidências do brief.
7. Submeter o draft ao Gauntlet com os 14 critérios e só então executar as duas passagens obrigatórias de `escrita-humana`, com review após cada passagem.
8. Salvar em `content/drafts/<topic_id>.md` e atualizar o status do topic para `drafted` no arquivo `research/topics/topics_*.yaml` correspondente apenas após os gates passarem. O draft **permanece `drafted`** — o writer não marca `approved` nem move o arquivo; isso cabe ao humano no QA (`qa-draft`).
