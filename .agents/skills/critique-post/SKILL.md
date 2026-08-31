---
name: critique-post
description: Use quando um draft de post estiver pronto e precisar de crítica antes da aprovação.
---

# Crítica do Post

## Overview

Criticar a primeira versão do post antes da aprovação, procurando especificamente clichês de IA, falta de evidência e tom genérico.

## Quando Usar / Quando NÃO Usar

- Usar: após write-post, antes da aprovação.
- NÃO usar: para reescrever o post (apenas criticar); para validar texto já aprovado.

## Entrada

- `content/drafts/<topic_id>.md`
- `memory/writing_style.md` (regras do autor)

## Critérios

clareza, originalidade, credibilidade, tom humano, densidade, relevância, consistência, uso de evidências, risco de alucinação, linguagem genérica de IA

## Frases-clichê a procurar (quando usadas de forma genérica)

- "Em um mundo cada vez mais..."
- "A inteligência artificial veio para..."
- "Mais do que nunca..."
- "Não é sobre X, é sobre Y..."

## Saída

Lista de críticas por critério, com:
- O que está bom (manter)
- O que está fraco (corrigir)
- Risco de alucinação (afirmações sem origem no brief)
- Sugestão concreta de correção

## Fluxo

1. Ler o draft e o writing_style.md.
2. Avaliar cada critério (0-10) com justificativa.
3. Procurar frases-clichê e tom genérico.
4. Verificar que todo fato tem origem no brief (risco de alucinação).
5. Verificar tamanho (900-1500 caracteres) e esqueleto.
6. Entregar a lista de críticas. O executor corrige o draft; depois o post passa por `escrita-humana` e pela aprovação do autor.

## Regras

- Crítica específica, não genérica ("melhore o texto" é proibido).
- Não reescrever — apontar e sugerir.
- Se o draft estiver bom, dizer o que está bom (nem tudo é falha).
