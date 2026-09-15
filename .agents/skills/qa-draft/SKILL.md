---
name: qa-draft
description: Use quando um draft de post estiver em content/drafts/ e o autor humano quiser revisar, aprovar, pedir modificação ou descartar. Aprovar é decisão exclusiva do humano; o agendamento/publicação ocorre em invocação explícita do Bloco 3.
---

# QA de Draft — Revisão humana

## Overview

Revisão humana de drafts do pipeline. O autor decide o destino de cada draft em `content/drafts/` e o agente executa a ação correspondente. **Aprovar é decisão exclusiva do humano; o agente nunca marca `approved` sozinho.**

## Quando Usar / Quando NÃO Usar

- Usar: após o Bloco 2 (drafts com status `drafted`) e antes de publicar/agendar (Bloco 3), quando o autor quer revisar um ou mais drafts.
- NÃO usar: para gerar novos drafts (isso é do Bloco 2); para publicar/agendar (isso é do Bloco 3); para editar código.

## Entrada

- Drafts em `content/drafts/` com status `drafted` (o autor informa qual ou quais).
- `memory/writing_style.md`, `memory/opinions.md`, `memory/professional_experience.md` para orientar ajustes.
- O brief correspondente em `research/briefs/` quando precisar conferir fatos/fontes.

## Fluxo

1. Listar os drafts em `content/drafts/` e confirmar com o autor qual(ais) estão sendo revisados.
2. Apresentar o(s) draft(s) para leitura do autor.
3. Receber a decisão do autor sobre cada draft:
   - **Aprovar** (com data/hora de agendamento).
   - **Pedir modificação** (com instrução específica).
   - **Editar direto** (autor edita e informa ações ao agente).
   - **Descartar**.
4. Aplicar a decisão conforme a decisão de QA abaixo.

## Decisões de QA

### Aprovar (marco editorial)

Aprovar e agendar são etapas distintas: a aprovação humana marca o topic como `approved`; o arquivo continua em `content/drafts/` até a confirmação do Bloco 3.

- **Antes de agendar, verificar conflitos** rodando `python scheduling_registry.py --check`. Isso lê os markers `<!-- agendado: ... -->` de todos os posts e detecta:
  - **Conflito de horário**: dois posts no mesmo horário (ex.: tentar agendar para 10/09 10:00 quando outro post já ocupa esse horário).
  - **Conflito de conteúdo**: o mesmo texto agendado duas vezes.
  - Se houver conflito, **não agendar**; propor ao autor outro horário ou outro post.
- Marcar o topic como `approved` no arquivo `research/topics/topics_*.yaml`.
- Invocar explicitamente o Bloco 3 (`publicar-linkedin`) quando houver data/hora de agendamento.
- Após a confirmação do agendamento, **mover literalmente** o arquivo de `content/drafts/` para `content/published/` (git mv / mv), registrando o marker `<!-- agendado: ... -->`.
- Não é necessário aguardar a publicação real; basta o agendamento ter sido feito corretamente.

### Pedir modificação

- Registrar a instrução do autor (ex.: "passar escrita-humana no parágrafo 3", "ajustar limite de caracteres", "deixar mais direto na abertura").
- O agente ajusta o draft conforme a instrução; se o autor pedir, rodar `escrita-humana` e revalidar (brief, tamanho 900–1500 car, `## Fontes`).
- O draft permanece `drafted`; re-apresentar ao autor para nova decisão.

### Editar direto (autor)

- O autor edita o arquivo em `content/drafts/` e informa ações ao agente (ex.: "rodar escrita-humana", "ajustar limite de caracteres", "conferir fontes").
- O agente executa as ações pedidas e revalida o draft.
- O draft permanece `drafted` até o autor aprovar.

### Descartar

- Mover literalmente o arquivo de onde estiver para `content/arquived/` (git mv / mv).
- Marcar o topic como `archived` no arquivo `research/topics/topics_*.yaml`.
- O material sai do fluxo de aprovação e não é mais considerado.

## Regras

- `approved` só é carimbado pelo humano; o arquivo pode permanecer aprovado em `content/drafts/` até o Bloco 3.
- O Bloco 3 move o arquivo de `content/drafts/` para `content/published/` somente após a confirmação no LinkedIn.
- Descartar move para `content/arquived/` (decisão exclusiva do autor).
- Não publicar nem agendar dentro do QA; após a aprovação, o Bloco 3 é invocado explicitamente.
- Revalidar tamanho (900–1500 caracteres / 150–250 palavras) e presença de `## Fontes` após qualquer ajuste.
