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

## Regras de escrita

- Tamanho: 900–1500 caracteres / 150–250 palavras.
- Esqueleto obrigatório: ABERTURA → SITUAÇÃO → APLICAÇÃO → PROBLEMA → DECISÃO → APRENDIZADO → PERGUNTA.
- Abertura com frase forte e específica (nunca genérica).
- Experiência concreta > conceito.
- Uma ideia por post.
- Todo fato do post deve ter origem no brief (nunca inventar).
- Usar a voz e opiniões de memory/opinions.md e o estilo de memory/writing_style.md.
- Terminar o post com uma seção `## Fontes` listando as fontes usadas (título, URL, data), extraídas das evidências do brief.

## Gate de qualidade do post

O revisor deve pontuar estes 14 critérios, cada um de 0 a 10:

1. Abertura forte e específica.
2. Situação contextualizada com precisão.
3. Aplicação prática clara.
4. Problema ou tensão concreta.
5. Decisão explícita.
6. Aprendizado útil.
7. Pergunta final que convida ao debate.
8. Conexão autoral concreta.
9. Uma ideia central sem dispersão.
10. Voz e opiniões do autor preservadas.
11. Fatos rastreáveis ao brief.
12. Fontes completas e corretamente herdadas.
13. Ausência de padrões genéricos de IA.
14. Tamanho e esqueleto conformes.

O post só pode ser aprovado pelo Gauntlet quando todos os 14 critérios forem `>=9/10` e a coverage for `>99%`. A aprovação agregada de 95% não substitui esses gates. O writer não pode avançar com critério abaixo do mínimo ou hard failure.

Depois da correção no Gauntlet, executar obrigatoriamente duas passagens separadas de `escrita-humana`: `humanize_pass_1` → `humanize_review_1` → `humanize_pass_2` → `humanize_review_2`. Cada passagem deve ter seu próprio revisor e aprovação; hard failures de escrita-humana sobrepõem a pontuação agregada de 95% e bloqueiam a aprovação.

## O que evitar

- Frases genéricas de IA: "Em um mundo cada vez mais...", "A inteligência artificial veio para...", "Mais do que nunca...", "Não é sobre X, é sobre Y...".
- Posts conceituais sem experiência concreta.
- Afirmações sem evidência no brief.

## Fluxo

1. Ler o brief e os 3 arquivos de memória.
2. Escolher o ângulo (dos "Possíveis ângulos" do brief) com melhor conexão com a experiência do autor.
3. Escrever o post seguindo o esqueleto e as regras.
4. Verificar tamanho (900–1500 caracteres).
5. Adicionar a seção `## Fontes` ao final do post, com as fontes usadas (título, URL, data) extraídas das evidências do brief.
6. Submeter o draft ao Gauntlet com os 14 critérios e só então executar as duas passagens obrigatórias de `escrita-humana`, com review após cada passagem.
7. Salvar em `content/drafts/<topic_id>.md` e atualizar o status do topic para `drafted` no arquivo `research/topics/topics_*.yaml` correspondente apenas após os gates passarem.
