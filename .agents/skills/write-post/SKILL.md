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

> **Organização de arquivos:** o draft nasce em `content/drafts/`. Quando o post é aprovado (`approval_humana`), ele é **movido literalmente** (git mv) de `content/drafts/` para `content/approved/`. Um arquivo de post vive em exatamente uma pasta de `content/` por vez.

## Regras de escrita

- Tamanho: 900–1500 caracteres / 150–250 palavras.
- Esqueleto obrigatório: ABERTURA → SITUAÇÃO → APLICAÇÃO → PROBLEMA → DECISÃO → APRENDIZADO → PERGUNTA.
- Abertura com frase forte e específica (nunca genérica).
- Experiência concreta > conceito.
- Uma ideia por post.
- Todo fato do post deve ter origem no brief (nunca inventar).
- Usar a voz e opiniões de memory/opinions.md e o estilo de memory/writing_style.md.
- Terminar o post com uma seção `## Fontes` listando as fontes usadas (título, URL, data), extraídas das evidências do brief.

## Contrato de revisão

O revisor deve retornar um objeto JSON conforme `docs/schemas/gauntlet-review.json`, sem campos extras. Os campos obrigatórios são `decision` (`approved` ou `feedback`), `coverage` (número entre 0 e 1), `criteria` (objeto não vazio com notas numéricas de 0 a 10), `hard_failures` (lista), `feedback` (lista de objetos com `criterion` e `message`) e `artifact` (caminho relativo não vazio do draft). Em aprovação, `coverage` deve ser `>= 0.99`, todos os critérios devem ser `>=9`, `hard_failures` deve ser uma lista vazia e `feedback` deve ser uma lista vazia. Em `feedback`, cada critério abaixo de 9 e a coverage abaixo de 0.99 precisam de feedback acionável. Qualquer `hard_failures` não vazio bloqueia.

## Critérios normativos do post

O revisor deve pontuar exatamente estes 14 critérios, cada um de 0 a 10, sem renomear, omitir ou acrescentar critérios:

1. Clareza
2. Força da abertura
3. Originalidade
4. Credibilidade
5. Uso de evidências
6. Risco de alucinação
7. Tom humano
8. Densidade
9. Relevância
10. Consistência com a voz do autor
11. Estrutura obrigatória
12. Pergunta final
13. Tamanho editorial
14. Rastreabilidade das fontes

O post só pode ser aprovado pelo Gauntlet quando todos os 14 critérios forem `>=9/10` e a coverage for `>= 0.99`. A aprovação agregada de 95% não substitui esses gates. O writer não pode avançar com critério abaixo do mínimo ou `hard_failures`.

Depois da correção no Gauntlet, executar obrigatoriamente duas passagens separadas de `escrita-humana`: `humanize_pass_1` → `humanize_review_1` → `humanize_pass_2` → `humanize_review_2`. Cada passagem deve ter seu próprio revisor e retornar o mesmo contrato JSON, com `artifact` relativo ao draft da passagem. Cada passagem precisa de aprovação independente; `hard_failures` de escrita-humana sobrepõem a pontuação agregada de 95% e bloqueiam a aprovação.

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
7. Salvar em `content/drafts/<topic_id>.md` e atualizar o status do topic para `drafted` no arquivo `research/topics/topics_*.yaml` correspondente apenas após os gates passarem. Após `approval_humana`, mover o arquivo para `content/approved/<topic_id>.md` (ver "Saída").
