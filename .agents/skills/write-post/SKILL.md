---
name: write-post
description: Use quando um research brief estiver pronto e for preciso escrever o post do LinkedIn (900-1500 caracteres, esqueleto fixo).
---

# Write Post

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

## Regras de escrita

- Tamanho: 900–1500 caracteres / 150–250 palavras.
- Esqueleto obrigatório: ABERTURA → SITUAÇÃO → APLICAÇÃO → PROBLEMA → DECISÃO → APRENDIZADO → PERGUNTA.
- Abertura com frase forte e específica (nunca genérica).
- Experiência concreta > conceito.
- Uma ideia por post.
- Todo fato do post deve ter origem no brief (nunca inventar).
- Usar a voz e opiniões de memory/opinions.md e o estilo de memory/writing_style.md.
- Terminar o post com uma seção `## Fontes` listando as fontes usadas (título, URL, data), extraídas das evidências do brief.

## O que evitar

- Frases genéricas de IA: "Em um mundo cada vez mais...", "A inteligência artificial veio para...", "Mais do que nunca...", "Não é sobre X, é sobre Y...".
- Posts conceituais sem experiência concreta.
- Afirmações sem evidência no brief.

## Fluxo

1. Ler o brief e os 3 arquivos de memória.
2. Escolher o ângulo (dos "Possíveis ângulos" do brief) com melhor conexão com a experiência do autor.
3. Escrever o post seguindo o esqueleto e as regras.
4. Verificar tamanho (900-1500 caracteres).
5. Adicionar a seção `## Fontes` ao final do post, com as fontes usadas (título, URL, data) extraídas das evidências do brief.
6. Salvar em `content/drafts/<topic_id>.md` e atualizar status do topic para `drafted`.
