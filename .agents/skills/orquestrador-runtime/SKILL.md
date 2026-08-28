---
name: orquestrador-runtime
description: Orquestra o pipeline editorial local (pesquisa → ideia → escrita → publicação) em rodadas, disparando executores, validando com revisores e respeitando gates humanos configuráveis via APPROVAL_*.
---

# Orquestrador de runtime do pipeline editorial

## Overview

O orquestrador coordena os blocos processuais do pipeline editorial local. A cada invocação ele:
1. Lê o estado (banco SQLite + pastas content/ + .env).
2. Define a rodada: quais blocos rodam nesta chamada, validando pré-condições.
3. Dispara executor → aguarda revisor → abre gate humano quando a chave APPROVAL_* exigir.
4. Registra validações via `contentctl bloco-ok` e avança o estado.

## Quando Usar / Quando NÃO Usar

- Usar: para executar qualquer etapa do pipeline editorial (pesquisa, ideação, escrita, revisão, publicação).
- NÃO usar: para editar código do pipeline, para publicar conteúdo fora de content/approved/, para tarefas não editoriais.

## Blocos processuais

| Bloco | Nome | Executor | Revisor | Gate |
|---|---|---|---|---|
| B1 | Convoca | orquestrador-runtime-executor | orquestrador-runtime-revisor | humano confirma plano |
| B2 | Pilar | pilar-executor | pilar-revisor | APPROVAL_PILAR |
| B3 | Pesquisa MECE | pesquisa-mece-executor | pesquisa-mece-revisor | APPROVAL_PESQUISA |
| B4 | Executa pesquisa | pesquisa-executor | pesquisa-revisor | APPROVAL_EXECUCAO |
| B5 | Cruzamento | cruzamento-executor | cruzamento-revisor | APPROVAL_CRUZAMENTO |
| B6 | Ideação | ideacao-executor | ideacao-revisor | APPROVAL_IDEACAO |
| B7 | Escolha | humano (sempre) | — | sempre human |
| B8 | Escrita | escrita-executor | escrita-revisor | APPROVAL_ESCRITA |
| B10 | Escrita-humana | escrita-humana-executor | escrita-humana-revisor | APPROVAL_REFINAMENTO |
| B9 | Valida | humano | — | APPROVAL_VALIDACAO |
| B11 | Publica | publicar-linkedin-executor | publicar-linkedin-revisor | APPROVAL_PUBLICACAO |

## Ordem real de execução

B1 → B2 → B3 → B4 → [repetir B3-B4] → B5 → B6 → [GATE] B7 → B8 → B10 → B9 → B11

## Leitura de estado

- Banco: `data/content.db` (via `contentctl` e consultas diretas).
- Pastas: `research/`, `content/ideas/`, `content/drafts/`, `content/approved/`, `content/published/`.
- Config: `.env` (chaves APPROVAL_*).

## Gates APPROVAL_*

Cada bloco com gate lê a chave correspondente no `.env`:
- `human` (default): após o revisor aprovar, o orquestrador PAUSA e pede confirmação humana.
- `agent`: a validação do revisor é suficiente; o orquestrador avança sem pausa.

B7 é sempre humano — não há chave.

## Ciclo de revisão (por bloco)

1. Executor entrega artefato + dados de saída padronizados.
2. Revisor lê o contrato do bloco (AGENT.md) + sua memory.md.
3. Se memória ambígua/contraditória → revisor clarifica antes de revisar.
4. Valida contra requisitos; decide aprovado ou feedback.
5. Feedback → executor ajusta → revisor reavalia (loop).
6. Aprovado → `contentctl bloco-ok <bloco> <artefato>` → orquestrador avança ou abre gate humano.

## Invocação

- "Roda o pipeline para o pilar X" → B1→B11 conforme pré-condições.
- "Executa a pesquisa Y" → B3→B4.
- "Escreve o post da ideia Z" → B8→B10→B9.
- "Publica content/approved/<arquivo>.md" → B11.

## Erros comuns

- Pular o revisor: todo trabalho de executor passa por revisor antes de qualquer aprovação.
- Pular B7: a escolha de ideias é sempre humana.
- Publicar fora de approved/: o conteúdo publicado vem somente de content/approved/.
- Sintetizar pesquisa: o stdout do LAST30DAYS_COMMAND é preservado verbatim.
