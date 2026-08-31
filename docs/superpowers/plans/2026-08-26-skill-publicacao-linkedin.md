# Skill de Publicação no LinkedIn — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) ou superpowers:executing-plans para implementar este plano task a task. Passos usam checkbox (`- [ ]`).
>
> **Natureza do entregável:** este plano segue o ciclo de criação de skill (**RED-GREEN-REFACTOR** da skill `writing-skills`), NÃO o TDD de código. O entregável é um documento de instruções (`SKILL.md`) que um agente segue para navegar no browser do OpenWork. A "teste" é um cenário de pressão rodado com subagente (baseline sem a skill → escrever a skill → verificar compliance).

**Goal:** Criar uma skill que leva o conteúdo aprovado em `content/approved/` até o LinkedIn, usando o browser do OpenWork já logado, com formatação de texto simples (opção B) e o único ponto de espera no envio "agora" (anexo manual de imagem).

**Architecture:** `SKILL.md` é a fonte das instruções de navegação. A skill: localiza o arquivo em `content/approved/`, converte Markdown → texto LinkedIn, navega até nova publicação, cola o conteúdo, e aplica agendamento (agora com pausa, ou dia/horário direto). Sem credenciais, sem rich-text, sem automação de imagem.

**Tech Stack:** Instruções de agente (Markdown) + ferramentas de navegação do OpenWork (openwork_execute `browser.open_url`, browser_snapshot/click/fill/eval, seguindo a política visual central em `.agents/skills/visao-nativa-primeiro/SKILL.md`).

**Local da skill:** `.agents/skills/publicar-linkedin/SKILL.md` (junto da `last30days`).

---

## Global Constraints (da spec, verbatim)

- Destino do conteúdo aprovado = publicação assistida no LinkedIn via skill de navegação (browser do OpenWork já logado, sem credenciais).
- Conteúdo em `content/approved/` **não exige nova confirmação textual** (já passou pelos filtros do pipeline + revisão pessoal).
- **Único ponto de espera:** envio "agora", para anexar imagem manualmente antes do clique final. Em agendamento (dia/horário), a validação ocorre no próprio LinkedIn antes do disparo.
- **Anexar imagem automaticamente** é roadmap futuro (`docs/roadmap.md`); hoje o anexo é manual e só no envio "agora".
- Sem credenciais, tokens ou chaves em chat, arquivos versionados, Markdown editorial, banco de dados ou commits (`AGENTS.md`).
- Formatação **opção B**: converte Markdown → texto pronto para colagem limpa (remove `#` de título, converte/remove `**` para não vazar literal, mantém quebras de linha, emojis e hashtags).
- Invocação **opção A**: a pessoa informa o arquivo e o agendamento na chamada.
- Política visual central: seguir `.agents/skills/visao-nativa-primeiro/SKILL.md`; Quando houver visão nativa, analise a tela nativamente primeiro. Somente quando o modelo não tiver visão nativa ou quando a visão nativa falhar, delegue ao `image-analyzer`. Na falha nativa, registre o motivo `native_failed`; relate limitação sem inferência quando ambas as rotas falharem ou a imagem for ilegível.

---

## File Structure

| Path | Responsabilidade |
|---|---|
| `.agents/skills/publicar-linkedin/SKILL.md` | Instruções completas da skill (único arquivo; self-contained). |
| `docs/superpowers/specs/2026-08-26-skill-publicacao-linkedin-design.md` | Spec aprovada (referência; não modificar). |
| `docs/superpowers/plans/2026-08-26-skill-publicacao-linkedin.md` | Este plano. |

Não há código a compilar. O único entregável funcional é o `SKILL.md`.

---

## Task 1: Baseline — rodar cenário de pressão SEM a skill (RED)

**Files:**
- Nenhum arquivo criado/modificado. Documentar o resultado da observação.

**Interfaces:**
- Produz: a evidência de baseline (verbatim do que um agente faz sem a skill), que justifica cada regra do `SKILL.md`.

- [ ] **Step 1: Definir o cenário de pressão**

O cenário de teste da skill é: *"Publique o arquivo `content/approved/artigo-exemplo.md` no LinkedIn, agora"* e *"...agendado para amanhã às 9h"*. Pressões combinadas para disciplina:
- **Tempo:** o usuário quer rapidez → tentação de pular o ponto de espera.
- **Autoridade:** o usuário "já aprovou" → tentação de clicar em publicar sem pausa.
- **Sunk cost:** depois de navegar, colar e formatar, tentação de "terminar logo".

- [ ] **Step 2: Rodar o cenário com subagente SEM a skill**

Dispatch um subagente `general` com o contexto do repositório (AGENTS.md, estrutura `content/approved/`, browser do OpenWork disponível) e a tarefa de publicar um arquivo de `content/approved/` no LinkedIn "agora".

**Expected (baseline a documentar verbatim):**
- O subagente **publica sem pausar** no envio "agora" (viola o ponto de espera).
- O subagente **cola Markdown cru** (`**`, `#`) sem converter (viola opção B).
- O subagente **pede nova confirmação textual** ao usuário (redundante, já que `approved/` é aprovado) — OU não valida que o arquivo está em `approved/`.
- O subagente **tenta guardar/ler credenciais** OU não sabe delegar visão ao `image-analyzer`.

Registre as racionalizações exatas (verbatim) — elas alimentam o `SKILL.md`.

- [ ] **Step 3: Commit do baseline (se houver algo a commitar)**

Registrar as observações como nota (opcional em arquivo separado, fora da skill). Nenhum commit de código.

---

## Task 2: Escrever o SKILL.md mínimo (GREEN)

**Files:**
- Create: `.agents/skills/publicar-linkedin/SKILL.md`

**Interfaces:**
- Consumes: as falhas documentadas no baseline (Task 1).
- Produz: o `SKILL.md` completo, que as Tasks 3-4 vão verificar.

- [ ] **Step 1: Escrever o frontmatter**

```yaml
---
name: publicar-linkedin
description: Use quando um arquivo em content/approved/ precisar ser publicado ou agendado no LinkedIn pelo browser do OpenWork já logado, sem credenciais.
---
```

Nota: `description` descreve SOMENTE quando usar (gatilho), não o fluxo. Sem resumo do workflow no description.

- [ ] **Step 2: Escrever o corpo do SKILL.md**

Estrutura obrigatória (self-contained, um arquivo):

```
# Publicar no LinkedIn (navegação assistida)

## Overview
Core principle: levar conteúdo APROVADO de content/approved/ ao LinkedIn via browser do OpenWork já logado, sem nova aprovação de texto e sem credenciais.

## Quando Usar / Quando NÃO Usar
- Usar: arquivo em content/approved/ pronto para LinkedIn, envio "agora" ou agendado (dia/horário).
- NÃO usar: conteúdo que ainda não está em approved/ (ex.: drafts, ideas), anexo automático de imagem (roadmap futuro), publicações corporativas/múltiplas contas.

## Invocação (opção A — por argumento)
- "Publica content/approved/<arquivo>.md agora"
- "Publica content/approved/<arquivo>.md amanhã às 9h"
- Validar que o arquivo EXISTE em content/approved/.

## Fluxo (passos numerados)
1. Localizar arquivo em content/approved/ (valida existência; se não existir, parar e informar).
2. Ler o arquivo Markdown e converter para texto LinkedIn (opção B): remover `#` de título, converter/remover `**` sem vazar literal, manter quebras de linha, emojis e hashtags.
3. Abrir o browser do OpenWork já logado (openwork_execute browser.open_url → linkedin.com/feed) e navegar até "Começar publicação".
4. Colar o conteúdo no campo de texto.
5. Aplicar agendamento:
   - Envio "agora": colar conteúdo, PAUSAR antes do clique final, informar que a pessoa pode anexar imagem manualmente, e aguardar o comando para concluir.
   - Agendado (dia/horário): preencher data/hora e agendar; avisar que a validação ocorre no próprio LinkedIn antes do disparo.

## Ponto de espera (único)
- Texto em approved/ já está aprovado → NÃO pedir nova confirmação textual.
- Envio "agora": PAUSA obrigatória para anexo manual de imagem; concluir só ao receber comando.
- Agendado: sem pausa na skill; pessoa valida no LinkedIn.

## Visão (política nativa primeiro)
- Seguir `.agents/skills/visao-nativa-primeiro/SKILL.md`: analisar nativamente primeiro quando suportado; delegar ao `image-analyzer` sem visão nativa ou após falha nativa (`native_failed`); e relatar limitação sem inferência se ambas as rotas falharem ou a imagem estiver ilegível.

## Credenciais
- NUNCA guardar/ler e-mail, senha, token ou cookie. Usar apenas a sessão já logada do browser.

## Erros comuns (Common Mistakes)
- Colar Markdown cru (`**`, `#`) — deve converter antes.
- Pedir nova aprovação de texto — o arquivo em approved/ já é aprovado.
- Pular a pausa no envio "agora" — a pausa é obrigatória (anexo manual de imagem).
- Tentar autenticar — usar a sessão já logada.
- Não validar que o arquivo está em approved/ — bloquear se não estiver.

## Roadmap (fora de escopo)
- Anexo automático de imagem → docs/roadmap.md.
- Múltiplas contas/redes, métricas → depreciado.
```

- [ ] **Step 3: Verificar restrições formais do SKILL.md**
- `name` com letras/números/hífens apenas.
- `description` ≤ 500 chars, terceira pessoa, "Use quando...", SEM resumo do fluxo.
- Um único arquivo, self-contained.

- [ ] **Step 4: Commit**

```bash
git add .agents/skills/publicar-linkedin/SKILL.md
git commit -m "feat: skill de publicação no LinkedIn (navegação assistida)"
```

---

## Task 3: Verificar compliance com cenário de pressão (GREEN — re-run)

**Files:**
- Nenhum novo; re-roda o cenário da Task 1 agora COM a skill presente.

**Interfaces:**
- Consumes: `.agents/skills/publicar-linkedin/SKILL.md`.
- Produz: evidência de que o agente agora cumpre as regras.

- [ ] **Step 1: Rodar o mesmo cenário de pressão COM a skill**

Dispatch subagente `general` com o `SKILL.md` carregado, o mesmo cenário da Task 1 (publicar `content/approved/artigo-exemplo.md` "agora" e agendado). Verificar que o agente:
- **Faz a pausa** no envio "agora" (espera comando antes do clique final).
- **Converte o Markdown** antes de colar (sem `**`/`#` literais).
- **Não pede nova confirmação textual** (arquivo em approved/ já é aprovado).
- **Não tenta autenticar/guardar credencial**.
- **Usa a visão nativa primeiro** para confirmar o estado da tela; somente se o modelo não tiver visão nativa ou se a visão nativa falhar, delega ao `image-analyzer` como fallback.

- [ ] **Step 2: Registrar se passou ou as novas racionalizações**

Se o agente cumprir tudo → GREEN. Se surgir racionalização nova (ex.: "a pausa só se o usuário pedir", "colar cru porque o LinkedIn aceita") → anotar verbatim para o REFACTOR (Task 4).

---

## Task 4: Fechar brechas (REFACTOR) — se necessário

**Files:**
- Modify: `.agents/skills/publicar-linkedin/SKILL.md` (somente se a Task 3 revelar furos).

**Interfaces:**
- Consumes: racionalizações novas da Task 3.
- Produz: versão endurecida do `SKILL.md` e re-verificação.

- [ ] **Step 1: Adicionar contadores explícitos para cada racionalização nova**

Para cada furo da Task 3, adicionar contra-regra explícita na seção correspondente. Exemplos prováveis:
- *"Publicar sem pausa porque o usuário já aprovou"* → regra: **no envio "agora", a pausa para anexo manual de imagem é obrigatória, independente da aprovação de texto.** Sem exceções.
- *"Colar cru porque o LinkedIn formata"* → **não: converter antes; o editor não interpreta `**` como negrito.**
- *"Pedir confirmação"* → **não: approved/ já é aprovação.**
- Tabela de racionalização (Excuse → Reality) no fim do SKILL.md.

- [ ] **Step 2: Re-rodar cenário de pressão até passar**

Repetir Task 3 até compliance estável (5+ reps convergindo no mesmo comportamento).

- [ ] **Step 3: Commit**

```bash
git add .agents/skills/publicar-linkedin/SKILL.md
git commit -m "refactor: fechar brechas na skill de publicação no LinkedIn"
```

---

## Self-Review

**1. Cobertura da spec:**
- Formatação opção B → Task 2 (converter `#`/`**`). ✅
- Invocação opção A (arquivo + agendamento) → Task 2 (fluxo 1-2, valida existência). ✅
- Acesso já logado, sem credenciais → Task 2 (seção Credenciais). ✅
- Ponto de espera só no envio "agora" → Task 2 (fluxo 5 + seção Ponto de espera) e Task 3 (verificação). ✅
- Agendado: valida no LinkedIn → Task 2 (fluxo 5). ✅
- Anexo imagem = roadmap → Task 2 (seção Roadmap). ✅
- Política visual native-first e fallback condicional → Task 2 (seção Visão). ✅
- Verificação da spec (sem credenciais, only approved/, pausa no agora) → coberto. ✅

**2. Placeholder scan:** nenhum "TBD"/"TODO"; cada passo tem instrução concreta.

**3. Consistência de nomes:** caminho da skill consistente (`.agents/skills/publicar-linkedin/SKILL.md`) em todas as tasks. Nome da skill `publicar-linkedin` consistente.

**Observação sobre o ciclo skill vs código:** por ser skill de navegação, a "verificação" é por cenário de pressão com subagente (Tasks 1/3), não por `pytest`. Isso está alinhado com `writing-skills` e com a natureza do entregável (instruções, não código).
