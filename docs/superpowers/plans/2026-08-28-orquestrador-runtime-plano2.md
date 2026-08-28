# Orquestrador Runtime — Plano 2: Skill orquestradora + agentes executores/revisores + gates APPROVAL_*

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Camada 1 (skill orquestradora) e Camada 2 (agentes executores + revisores) do orquestrador de runtime, com gates `APPROVAL_*` configuráveis no `.env` — cobrindo o fluxo completo pesquisa → ideia → escrita → publicação.

**Architecture:** Estende o Plano 1 (banco v6 + `contentctl bloco-ok`/`publish-complete` já implementados). Cria a skill `.agents/skills/orquestrador-runtime/SKILL.md` que lê estado (banco + pastas + `.env`), define a rodada, dispara executor → aguarda revisor → abre gate humano quando a chave `APPROVAL_*` exigir. Cria os agentes `.agents/agents/<bloco>-executor/` e `.agents/agents/<bloco>-revisor/` (AGENT.md + memory.md) para os 9 blocos com executor/revisor; B7 e B9 são gates humanos sem agentes. Como os artefatos são arquivos de instrução (sem código Python), o ciclo TDD é um harness estrutural em `tests/test_orquestrador_runtime.py` que valida existência e conteúdo mínimo de cada arquivo.

**Tech Stack:** Markdown (SKILL.md, AGENT.md, memory.md), Python 3.12 + pytest (harness de validação estrutural), `.env` (chaves `APPROVAL_*`).

## Global Constraints

- Python 3.12+ (`/Users/mac/.pyenv/shims/python3.12`).
- Rodar testes: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/ -q`
- Branch: `feat/orquestrador-runtime-plano2` (criar a partir de `feat/orquestrador-runtime-plano1`).
- B7 é o único gate humano intocável (sem chave `APPROVAL_*`); B9 tem chave `APPROVAL_VALIDACAO`.
- Sem credenciais em chat, arquivos versionados, banco ou commits (AGENTS.md).
- Commits frequentes, mensagens no estilo do repo (`feat:`, `refactor:`, `fix:`).
- `.env` e `data/content.db` não entram no Git (convenção do repo).
- Pesquisa recente capturada somente pelo `LAST30DAYS_COMMAND`; stdout preservado verbatim.
- Link individual de cada postagem do LinkedIn capturado no momento da coleta (formato `/feed/update/urn:li:activity:...`).
- Agentes em `.agents/agents/<bloco>-executor/` e `.agents/agents/<bloco>-revisor/`; `memory.md` do revisor é OBRIGATÓRIO (versionado em git), do executor é opcional.
- Skill em `.agents/skills/orquestrador-runtime/SKILL.md`.

---

### Task 1: Harness de validação + skill orquestradora

**Files:**
- Create: `tests/test_orquestrador_runtime.py`
- Create: `.agents/skills/orquestrador-runtime/SKILL.md`

**Interfaces:**
- Consumes: nada novo (estrutura de pastas existente).
- Produces: harness estrutural com `BLOCKS: dict[str, str]` (vazio nesta task, preenchido nas tasks 2–10) e a skill orquestradora que lista os 11 blocos e o fluxo completo.

- [ ] **Step 1: Write the failing test**

Crie `tests/test_orquestrador_runtime.py`:

```python
"""Structural validation for the orchestrator runtime (Plano 2)."""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

BLOCKS: dict[str, str] = {}

APPROVAL_KEYS = [
    "APPROVAL_PILAR",
    "APPROVAL_PESQUISA",
    "APPROVAL_EXECUCAO",
    "APPROVAL_CRUZAMENTO",
    "APPROVAL_IDEACAO",
    "APPROVAL_ESCRITA",
    "APPROVAL_REFINAMENTO",
    "APPROVAL_VALIDACAO",
    "APPROVAL_PUBLICACAO",
]


class OrquestradorRuntimeStructureTests(unittest.TestCase):
    def test_skill_exists(self):
        skill = REPO_ROOT / ".agents" / "skills" / "orquestrador-runtime" / "SKILL.md"
        self.assertTrue(skill.is_file(), "orquestrador-runtime skill missing")

    def test_skill_covers_all_blocks(self):
        skill = (
            REPO_ROOT / ".agents" / "skills" / "orquestrador-runtime" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for block in BLOCKS:
            self.assertIn(block, skill, f"skill does not mention {block}")

    def test_each_block_has_executor_and_revisor(self):
        for block, slug in BLOCKS.items():
            executor = REPO_ROOT / ".agents" / "agents" / f"{slug}-executor" / "AGENT.md"
            revisor = REPO_ROOT / ".agents" / "agents" / f"{slug}-revisor" / "AGENT.md"
            self.assertTrue(executor.is_file(), f"{block} executor missing")
            self.assertTrue(revisor.is_file(), f"{block} revisor missing")

    def test_reviewers_have_memory(self):
        for block, slug in BLOCKS.items():
            memory = REPO_ROOT / ".agents" / "agents" / f"{slug}-revisor" / "memory.md"
            self.assertTrue(memory.is_file(), f"{block} revisor memory missing")

    def test_agent_files_have_required_sections(self):
        for block, slug in BLOCKS.items():
            for role in ("executor", "revisor"):
                path = REPO_ROOT / ".agents" / "agents" / f"{slug}-{role}" / "AGENT.md"
                content = path.read_text(encoding="utf-8")
                self.assertIn("## Contrato", content, f"{block} {role} missing Contrato")
                self.assertIn("## Processo", content, f"{block} {role} missing Processo")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -v`
Expected: FAIL — `orquestrador-runtime skill missing` (arquivo não existe).

- [ ] **Step 3: Write minimal implementation**

Crie `.agents/skills/orquestrador-runtime/SKILL.md`:

```markdown
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -q`
Expected: PASS (5 testes; `BLOCKS` vazio faz os testes de blocos passarem trivialmente).

- [ ] **Step 5: Commit**

```bash
git add tests/test_orquestrador_runtime.py .agents/skills/orquestrador-runtime/SKILL.md
git commit -m "feat: skill orquestradora de runtime + harness de validação estrutural"
```

---

### Task 2: Agentes B1 (Convoca)

**Files:**
- Create: `.agents/agents/orquestrador-runtime-executor/AGENT.md`
- Create: `.agents/agents/orquestrador-runtime-revisor/AGENT.md`
- Create: `.agents/agents/orquestrador-runtime-revisor/memory.md`
- Create: `runtime/rodadas/.gitkeep`
- Modify: `tests/test_orquestrador_runtime.py` (adicionar `"B1": "orquestrador-runtime"` a `BLOCKS`)

**Interfaces:**
- Consumes: skill orquestradora (Task 1).
- Produces: executor/revisor de B1; `BLOCKS["B1"] = "orquestrador-runtime"` no harness.

- [ ] **Step 1: Write the failing test**

Em `tests/test_orquestrador_runtime.py`, troque:

```python
BLOCKS: dict[str, str] = {}
```

por:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -v`
Expected: FAIL — `B1 executor missing` (e `B1 revisor missing`, `B1 revisor memory missing`).

- [ ] **Step 3: Write minimal implementation**

Crie `.agents/agents/orquestrador-runtime-executor/AGENT.md`:

```markdown
---
name: orquestrador-runtime-executor
description: Executor do bloco B1 (Convoca) — produz o plano de rodada.
---

# Executor B1 — Convoca

## Input
- Skill orquestradora invocada.
- Estado atual: banco (data/content.db), pastas content/, .env.

## Processo
1. Ler o estado: pilares aprovados, pesquisas da rodada ativa, ideias, drafts, approved.
2. Definir a rodada: quais blocos rodam nesta chamada, validando pré-condições.
3. Escrever o plano de rodada em `runtime/rodadas/<ts>.md` com:
   - Rodada (id, pilar, status).
   - Blocos a executar e ordem.
   - Pré-condições de cada bloco.
   - Gates APPROVAL_* aplicáveis.

## Formato de saída
- Artefato: `runtime/rodadas/<ts>.md` (plano de rodada).
- Estado: rodada criada no banco via `Database.create_round`.

## Contrato
- O plano é coerente com o estado real (não inventar pilares/pesquisas).
- B7 (escolha) é sempre humano — nunca listado como gate automático.
- Sem credenciais em chat, arquivos, banco ou commits.
```

Crie `.agents/agents/orquestrador-runtime-revisor/AGENT.md`:

```markdown
---
name: orquestrador-runtime-revisor
description: Revisor do bloco B1 (Convoca) — valida o plano de rodada.
---

# Revisor B1 — Convoca

## O que validar
- O plano de rodada existe em `runtime/rodadas/`.
- Os blocos listados têm pré-condições satisfeitas pelo estado real.
- A ordem respeita a sequência B1→B2→B3→B4→[B3-B4]→B5→B6→B7→B8→B10→B9→B11.
- B7 não é tratado como gate automático.
- Nenhuma credencial no plano.

## Formato de feedback
- Aprovado: `contentctl bloco-ok B1 <plano>`.
- Feedback: itens com o que corrigir, referenciando o contrato.

## Memória
- Lições de revisões passadas ficam em memory.md (versionado em git).
```

Crie `.agents/agents/orquestrador-runtime-revisor/memory.md`:

```markdown
# Memória do revisor B1

Sem feedbacks registrados ainda. Registre aqui toda correção humana sobre o plano de rodada.
```

Crie `runtime/rodadas/.gitkeep` (arquivo vazio) para versionar a pasta de planos de rodada.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_orquestrador_runtime.py .agents/agents/orquestrador-runtime-executor/AGENT.md .agents/agents/orquestrador-runtime-revisor/AGENT.md .agents/agents/orquestrador-runtime-revisor/memory.md runtime/rodadas/.gitkeep
git commit -m "feat: agentes do bloco B1 (Convoca) — executor e revisor"
```

---

### Task 3: Agentes B2 (Pilar)

**Files:**
- Create: `.agents/agents/pilar-executor/AGENT.md`
- Create: `.agents/agents/pilar-revisor/AGENT.md`
- Create: `.agents/agents/pilar-revisor/memory.md`
- Modify: `tests/test_orquestrador_runtime.py` (adicionar `"B2": "pilar"` a `BLOCKS`)

**Interfaces:**
- Consumes: skill orquestradora (Task 1).
- Produces: executor/revisor de B2; `BLOCKS["B2"] = "pilar"` no harness.

- [ ] **Step 1: Write the failing test**

Em `tests/test_orquestrador_runtime.py`, troque:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
}
```

por:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -v`
Expected: FAIL — `B2 executor missing` (e demais).

- [ ] **Step 3: Write minimal implementation**

Crie `.agents/agents/pilar-executor/AGENT.md`:

```markdown
---
name: pilar-executor
description: Executor do bloco B2 (Pilar) — escolhe o pilar editorial.
---

# Executor B2 — Pilar

## Input
- `docs/pillars.md` com ≥1 pilar aprovado.
- Banco: `pillars` (name, approved).

## Processo
1. Ler os pilares aprovados do banco/docs.
2. Apresentar as opções ao usuário (ou escolher conforme a invocação).
3. Confirmar o pilar escolhido.

## Formato de saída
- Pilar escolhido (nome exato como no banco).
- Estado: nenhuma escrita — apenas seleção.

## Contrato
- A lista de opções é fiel ao banco (não inventar pilares).
- Só pilares com approved=true são elegíveis.
```

Crie `.agents/agents/pilar-revisor/AGENT.md`:

```markdown
---
name: pilar-revisor
description: Revisor do bloco B2 (Pilar) — valida a escolha do pilar.
---

# Revisor B2 — Pilar

## O que validar
- O pilar escolhido existe no banco com approved=true.
- O nome é exato (case-sensitive) ao do banco.
- Nenhum pilar não aprovado foi escolhido.

## Formato de feedback
- Aprovado: `contentctl bloco-ok B2 <pilar>`.
- Feedback: itens com o que corrigir.

## Memória
- Lições de revisões passadas ficam em memory.md (versionado em git).
```

Crie `.agents/agents/pilar-revisor/memory.md`:

```markdown
# Memória do revisor B2

Sem feedbacks registrados ainda. Registre aqui toda correção humana sobre a escolha de pilar.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_orquestrador_runtime.py .agents/agents/pilar-executor/AGENT.md .agents/agents/pilar-revisor/AGENT.md .agents/agents/pilar-revisor/memory.md
git commit -m "feat: agentes do bloco B2 (Pilar) — executor e revisor"
```

---

### Task 4: Agentes B3 (Pesquisa MECE)

**Files:**
- Create: `.agents/agents/pesquisa-mece-executor/AGENT.md`
- Create: `.agents/agents/pesquisa-mece-revisor/AGENT.md`
- Create: `.agents/agents/pesquisa-mece-revisor/memory.md`
- Modify: `tests/test_orquestrador_runtime.py` (adicionar `"B3": "pesquisa-mece"` a `BLOCKS`)

**Interfaces:**
- Consumes: skill orquestradora (Task 1).
- Produces: executor/revisor de B3; `BLOCKS["B3"] = "pesquisa-mece"` no harness.

- [ ] **Step 1: Write the failing test**

Em `tests/test_orquestrador_runtime.py`, troque:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
}
```

por:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -v`
Expected: FAIL — `B3 executor missing` (e demais).

- [ ] **Step 3: Write minimal implementation**

Crie `.agents/agents/pesquisa-mece-executor/AGENT.md`:

```markdown
---
name: pesquisa-mece-executor
description: Executor do bloco B3 (Pesquisa MECE) — seleciona pesquisas mutuamente exclusivas e coletivamente exaustivas.
---

# Executor B3 — Pesquisa MECE

## Input
- Pilar escolhido (B2).
- Banco: `research_reports` (topic, path, pillar, round_id, label).

## Processo
1. Consultar o acervo de pesquisas do pilar (e entre pilares) para dedupe MECE.
2. Propor pesquisa(s) selecionada(s) + opção "outra".
3. Se existe algo similar:
   - (a) transferir para outro pilar, ou
   - (b) criar condições que diferenciem a pesquisa da existente (ajustar enfoque/pilar).

## Formato de saída
- Pesquisa(s) selecionada(s) com tema + enfoque.
- Opção "outra" quando aplicável.
- Estado: nenhuma escrita — apenas seleção.

## Contrato
- Exclusividade verificada contra o acervo inteiro, não só o da rodada.
- Cobertura: as pesquisas propostas cobrem o pilar sem sobreposição.
```

Crie `.agents/agents/pesquisa-mece-revisor/AGENT.md`:

```markdown
---
name: pesquisa-mece-revisor
description: Revisor do bloco B3 (Pesquisa MECE) — valida exclusividade e cobertura.
---

# Revisor B3 — Pesquisa MECE

## O que validar
- As pesquisas propostas não duplicam o acervo existente (dedupe MECE).
- A exclusividade foi verificada contra o acervo inteiro, não só o da rodada.
- A cobertura cobre o pilar sem lacunas óbvias.
- A opção "outra" foi oferecida quando aplicável.

## Formato de feedback
- Aprovado: `contentctl bloco-ok B3 <pesquisa>`.
- Feedback: itens com o que corrigir.

## Memória
- Lições de revisões passadas ficam em memory.md (versionado em git).
```

Crie `.agents/agents/pesquisa-mece-revisor/memory.md`:

```markdown
# Memória do revisor B3

Sem feedbacks registrados ainda. Registre aqui toda correção humana sobre a seleção MECE.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_orquestrador_runtime.py .agents/agents/pesquisa-mece-executor/AGENT.md .agents/agents/pesquisa-mece-revisor/AGENT.md .agents/agents/pesquisa-mece-revisor/memory.md
git commit -m "feat: agentes do bloco B3 (Pesquisa MECE) — executor e revisor"
```

---

### Task 5: Agentes B4 (Executa pesquisa)

**Files:**
- Create: `.agents/agents/pesquisa-executor/AGENT.md`
- Create: `.agents/agents/pesquisa-revisor/AGENT.md`
- Create: `.agents/agents/pesquisa-revisor/memory.md`
- Modify: `tests/test_orquestrador_runtime.py` (adicionar `"B4": "pesquisa"` a `BLOCKS`)

**Interfaces:**
- Consumes: skill orquestradora (Task 1); `LAST30DAYS_COMMAND` (config), `contentctl research discover` (Plano 1).
- Produces: executor/revisor de B4; `BLOCKS["B4"] = "pesquisa"` no harness.

- [ ] **Step 1: Write the failing test**

Em `tests/test_orquestrador_runtime.py`, troque:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
}
```

por:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -v`
Expected: FAIL — `B4 executor missing` (e demais).

- [ ] **Step 3: Write minimal implementation**

Crie `.agents/agents/pesquisa-executor/AGENT.md`:

```markdown
---
name: pesquisa-executor
description: Executor do bloco B4 (Executa pesquisa) — captura pesquisa multicanal com peso no LinkedIn.
---

# Executor B4 — Executa pesquisa

## Input
- Pilar escolhido (B2).
- Pesquisa aprovada (B3): tema + enfoque.
- Rodada ativa: `rounds.id`.

## Processo
1. Capturar pesquisa multicanal com peso no LinkedIn:
   - Começar pelo LinkedIn (fonte de maior peso na síntese).
   - Complementar com last30days (YouTube, Reddit, HN, TikTok, etc.).
2. Executar `LAST30DAYS_COMMAND` (configurado no .env) e preservar o stdout verbatim.
3. Registrar o link individual de cada postagem do LinkedIn (formato /feed/update/urn:li:activity:...), abrindo cada post e capturando a URL da barra de endereço no momento da coleta.
4. Gravar relatório em `research/<ts>-<slug>.md`.
5. Registrar no banco: `contentctl research discover <topic> --pillar <pilar>` + round_id/label.

## Formato de saída
- Artefato: `research/<ts>-<slug>.md` (relatório completo).
- Estado: row em `research_reports` com pillar, round_id, label.
- Label: `YYYY_MM_DD <pillar-slug> <detalhe-pesquisa>` (≤50 caracteres).

## Contrato
- O stdout do LAST30DAYS_COMMAND é preservado verbatim — não sintetizar internamente.
- O link individual de cada postagem do LinkedIn é capturado no momento da coleta.
- Sem credenciais em chat, arquivos, banco ou commits.
```

Crie `.agents/agents/pesquisa-revisor/AGENT.md`:

```markdown
---
name: pesquisa-revisor
description: Revisor do bloco B4 (Executa pesquisa) — valida a captura.
---

# Revisor B4 — Executa pesquisa

## O que validar
- O relatório existe em `research/` e o stdout do LAST30DAYS_COMMAND foi preservado verbatim.
- A pesquisa começa pelo LinkedIn e o link individual de cada postagem foi capturado.
- O registro no banco tem pillar, round_id e label (≤50 chars).
- Sem credenciais vazadas.

## Formato de feedback
- Aprovado: `contentctl bloco-ok B4 <artefato>`.
- Feedback: itens com o que corrigir, referenciando o contrato.

## Memória
- Lições de revisões passadas ficam em memory.md (versionado em git).
```

Crie `.agents/agents/pesquisa-revisor/memory.md`:

```markdown
# Memória do revisor B4

Sem feedbacks registrados ainda. Registre aqui toda correção humana sobre a captura de pesquisa.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_orquestrador_runtime.py .agents/agents/pesquisa-executor/AGENT.md .agents/agents/pesquisa-revisor/AGENT.md .agents/agents/pesquisa-revisor/memory.md
git commit -m "feat: agentes do bloco B4 (Executa pesquisa) — executor e revisor"
```

---

### Task 6: Agentes B5 (Cruzamento)

**Files:**
- Create: `.agents/agents/cruzamento-executor/AGENT.md`
- Create: `.agents/agents/cruzamento-revisor/AGENT.md`
- Create: `.agents/agents/cruzamento-revisor/memory.md`
- Modify: `tests/test_orquestrador_runtime.py` (adicionar `"B5": "cruzamento"` a `BLOCKS`)

**Interfaces:**
- Consumes: skill orquestradora (Task 1); `research_reports WHERE round_id = ?` (Plano 1).
- Produces: executor/revisor de B5; `BLOCKS["B5"] = "cruzamento"` no harness.

- [ ] **Step 1: Write the failing test**

Em `tests/test_orquestrador_runtime.py`, troque:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
}
```

por:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
    "B5": "cruzamento",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -v`
Expected: FAIL — `B5 executor missing` (e demais).

- [ ] **Step 3: Write minimal implementation**

Crie `.agents/agents/cruzamento-executor/AGENT.md`:

```markdown
---
name: cruzamento-executor
description: Executor do bloco B5 (Cruzamento) — cruza as pesquisas da rodada.
---

# Executor B5 — Cruzamento

## Input
- Rodada ativa com ≥2 pesquisas (`research_reports WHERE round_id = ?`).
- Relatórios em `research/`.

## Processo
1. Ler todas as pesquisas da rodada (não escolhidas uma a uma).
2. Identificar concordâncias, discordâncias e lacunas.
3. Gravar documento em `content/drafts/cruzamento-<rodada>.md`.

## Formato de saída
- Artefato: `content/drafts/cruzamento-<rodada>.md` com seções:
  - Mapa dos temas.
  - Concordâncias.
  - Discordâncias/contrapontos.
  - Lacunas (viram novas pesquisas/ideias).

## Contrato
- O documento cobre TODAS as pesquisas da rodada.
- Cada afirmação referencia a pesquisa de origem (path).
```

Crie `.agents/agents/cruzamento-revisor/AGENT.md`:

```markdown
---
name: cruzamento-revisor
description: Revisor do bloco B5 (Cruzamento) — valida a cobertura do cruzamento.
---

# Revisor B5 — Cruzamento

## O que validar
- O documento cobre todas as pesquisas da rodada.
- Concordâncias/discordâncias/lacunas estão presentes.
- Cada afirmação referencia a pesquisa de origem.

## Formato de feedback
- Aprovado: `contentctl bloco-ok B5 <artefato>`.
- Feedback: itens com o que corrigir.

## Memória
- Lições de revisões passadas ficam em memory.md (versionado em git).
```

Crie `.agents/agents/cruzamento-revisor/memory.md`:

```markdown
# Memória do revisor B5

Sem feedbacks registrados ainda. Registre aqui toda correção humana sobre o cruzamento.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_orquestrador_runtime.py .agents/agents/cruzamento-executor/AGENT.md .agents/agents/cruzamento-revisor/AGENT.md .agents/agents/cruzamento-revisor/memory.md
git commit -m "feat: agentes do bloco B5 (Cruzamento) — executor e revisor"
```

---

### Task 7: Agentes B6 (Ideação)

**Files:**
- Create: `.agents/agents/ideacao-executor/AGENT.md`
- Create: `.agents/agents/ideacao-revisor/AGENT.md`
- Create: `.agents/agents/ideacao-revisor/memory.md`
- Modify: `tests/test_orquestrador_runtime.py` (adicionar `"B6": "ideacao"` a `BLOCKS`)

**Interfaces:**
- Consumes: skill orquestradora (Task 1); `contentctl ideas create --sources` (Plano 1).
- Produces: executor/revisor de B6; `BLOCKS["B6"] = "ideacao"` no harness.

- [ ] **Step 1: Write the failing test**

Em `tests/test_orquestrador_runtime.py`, troque:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
    "B5": "cruzamento",
}
```

por:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
    "B5": "cruzamento",
    "B6": "ideacao",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -v`
Expected: FAIL — `B6 executor missing` (e demais).

- [ ] **Step 3: Write minimal implementation**

Crie `.agents/agents/ideacao-executor/AGENT.md`:

```markdown
---
name: ideacao-executor
description: Executor do bloco B6 (Ideação) — gera ideias ancoradas nas pesquisas.
---

# Executor B6 — Ideação

## Input
- Cruzamento validado (B5).
- Rodada ativa.

## Processo
1. Derivar ideias do documento de cruzamento.
2. Para cada ideia, registrar no banco via `contentctl ideas create --research <path> --pillar <pilar> --angle <ângulo> --sources <paths>`.
3. Gravar registro editorial em `content/ideas/`.

## Formato de saída
- Ideias em `content/ideas/` + banco (status `idea`).
- Cada ideia com `sources` (JSON com todos os paths que sustentam a ideia).

## Contrato
- Cada ideia é ancorada em pelo menos uma pesquisa da rodada.
- Fontes multi-pesquisa são registradas em `ideas.sources`.
- Sem credenciais em chat, arquivos, banco ou commits.
```

Crie `.agents/agents/ideacao-revisor/AGENT.md`:

```markdown
---
name: ideacao-revisor
description: Revisor do bloco B6 (Ideação) — valida o ancoramento das ideias.
---

# Revisor B6 — Ideação

## O que validar
- Cada ideia está ancorada em pelo menos uma pesquisa da rodada.
- As fontes (ideas.sources) correspondem às pesquisas citadas.
- O status no banco é `idea`.

## Formato de feedback
- Aprovado: `contentctl bloco-ok B6 <artefato>`.
- Feedback: itens com o que corrigir.

## Memória
- Lições de revisões passadas ficam em memory.md (versionado em git).
```

Crie `.agents/agents/ideacao-revisor/memory.md`:

```markdown
# Memória do revisor B6

Sem feedbacks registrados ainda. Registre aqui toda correção humana sobre a ideação.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_orquestrador_runtime.py .agents/agents/ideacao-executor/AGENT.md .agents/agents/ideacao-revisor/AGENT.md .agents/agents/ideacao-revisor/memory.md
git commit -m "feat: agentes do bloco B6 (Ideação) — executor e revisor"
```

---

### Task 8: Agentes B8 (Escrita)

**Files:**
- Create: `.agents/agents/escrita-executor/AGENT.md`
- Create: `.agents/agents/escrita-revisor/AGENT.md`
- Create: `.agents/agents/escrita-revisor/memory.md`
- Modify: `tests/test_orquestrador_runtime.py` (adicionar `"B8": "escrita"` a `BLOCKS`)

**Interfaces:**
- Consumes: skill orquestradora (Task 1); `contentctl draft create` (Plano 1).
- Produces: executor/revisor de B8; `BLOCKS["B8"] = "escrita"` no harness.

- [ ] **Step 1: Write the failing test**

Em `tests/test_orquestrador_runtime.py`, troque:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
    "B5": "cruzamento",
    "B6": "ideacao",
}
```

por:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
    "B5": "cruzamento",
    "B6": "ideacao",
    "B8": "escrita",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -v`
Expected: FAIL — `B8 executor missing` (e demais).

- [ ] **Step 3: Write minimal implementation**

Crie `.agents/agents/escrita-executor/AGENT.md`:

```markdown
---
name: escrita-executor
description: Executor do bloco B8 (Escrita) — escreve o texto base do post.
---

# Executor B8 — Escrita

## Input
- Ideias selecionadas (B7, humano).
- Pesquisas de origem.

## Processo
1. Escrever texto de 1000–2000 caracteres.
2. Anexar fontes (≤5, com peso) ao final.
3. Gravar em `content/drafts/` via `contentctl draft create <idea_id>` e editar o corpo.

## Formato de saída
- Texto em `content/drafts/` (status `draft`).
- Fontes: ≤5, com peso, referenciando as pesquisas.

## Contrato
- Texto no limite de 1000–2000 caracteres.
- Fontes corretas e ancoradas nas pesquisas.
- Sem credenciais em chat, arquivos, banco ou commits.
```

Crie `.agents/agents/escrita-revisor/AGENT.md`:

```markdown
---
name: escrita-revisor
description: Revisor do bloco B8 (Escrita) — valida texto e fontes.
---

# Revisor B8 — Escrita

## O que validar
- Texto entre 1000 e 2000 caracteres.
- Fontes ≤5, com peso, corretas e ancoradas nas pesquisas.
- O draft está em content/drafts/ com status draft.

## Formato de feedback
- Aprovado: `contentctl bloco-ok B8 <artefato>`.
- Feedback: itens com o que corrigir.

## Memória
- Lições de revisões passadas ficam em memory.md (versionado em git).
```

Crie `.agents/agents/escrita-revisor/memory.md`:

```markdown
# Memória do revisor B8

Sem feedbacks registrados ainda. Registre aqui toda correção humana sobre a escrita.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_orquestrador_runtime.py .agents/agents/escrita-executor/AGENT.md .agents/agents/escrita-revisor/AGENT.md .agents/agents/escrita-revisor/memory.md
git commit -m "feat: agentes do bloco B8 (Escrita) — executor e revisor"
```

---

### Task 9: Agentes B10 (Escrita-humana)

**Files:**
- Create: `.agents/agents/escrita-humana-executor/AGENT.md`
- Create: `.agents/agents/escrita-humana-revisor/AGENT.md`
- Create: `.agents/agents/escrita-humana-revisor/memory.md`
- Modify: `tests/test_orquestrador_runtime.py` (adicionar `"B10": "escrita-humana"` a `BLOCKS`)

**Interfaces:**
- Consumes: skill orquestradora (Task 1).
- Produces: executor/revisor de B10; `BLOCKS["B10"] = "escrita-humana"` no harness.

- [ ] **Step 1: Write the failing test**

Em `tests/test_orquestrador_runtime.py`, troque:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
    "B5": "cruzamento",
    "B6": "ideacao",
    "B8": "escrita",
}
```

por:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
    "B5": "cruzamento",
    "B6": "ideacao",
    "B8": "escrita",
    "B10": "escrita-humana",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -v`
Expected: FAIL — `B10 executor missing` (e demais).

- [ ] **Step 3: Write minimal implementation**

Crie `.agents/agents/escrita-humana-executor/AGENT.md`:

```markdown
---
name: escrita-humana-executor
description: Executor do bloco B10 (Escrita-humana) — refina o texto base com voz humana.
---

# Executor B10 — Escrita-humana

## Input
- Texto base revisado (B8).
- Pesquisas de origem.

## Processo
1. Refinar o texto para ficar mais claro, direto e humano, preservando a voz.
2. Respeitar delta ≤15% em relação ao texto base.
3. Reanexar as fontes ao final.

## Formato de saída
- Texto refinado em `content/drafts/`.
- Fontes reanexadas (≤5, com peso).

## Contrato
- Delta ≤15% em relação ao texto base.
- Fontes intactas (mesmas do texto base).
- Sem credenciais em chat, arquivos, banco ou commits.
```

Crie `.agents/agents/escrita-humana-revisor/AGENT.md`:

```markdown
---
name: escrita-humana-revisor
description: Revisor do bloco B10 (Escrita-humana) — valida delta e fontes.
---

# Revisor B10 — Escrita-humana

## O que validar
- Delta ≤15% em relação ao texto base.
- Fontes intactas (mesmas do texto base).
- O texto ficou mais humano sem perder a voz.

## Formato de feedback
- Aprovado: `contentctl bloco-ok B10 <artefato>`.
- Feedback: itens com o que corrigir.

## Memória
- Lições de revisões passadas ficam em memory.md (versionado em git).
```

Crie `.agents/agents/escrita-humana-revisor/memory.md`:

```markdown
# Memória do revisor B10

Sem feedbacks registrados ainda. Registre aqui toda correção humana sobre o refinamento.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_orquestrador_runtime.py .agents/agents/escrita-humana-executor/AGENT.md .agents/agents/escrita-humana-revisor/AGENT.md .agents/agents/escrita-humana-revisor/memory.md
git commit -m "feat: agentes do bloco B10 (Escrita-humana) — executor e revisor"
```

---

### Task 10: Agentes B11 (Publica)

**Files:**
- Create: `.agents/agents/publicar-linkedin-executor/AGENT.md`
- Create: `.agents/agents/publicar-linkedin-revisor/AGENT.md`
- Create: `.agents/agents/publicar-linkedin-revisor/memory.md`
- Modify: `tests/test_orquestrador_runtime.py` (adicionar `"B11": "publicar-linkedin"` a `BLOCKS`)

**Interfaces:**
- Consumes: skill orquestradora (Task 1); skill `publicar-linkedin` (existente); `contentctl publish-complete` (Plano 1).
- Produces: executor/revisor de B11; `BLOCKS["B11"] = "publicar-linkedin"` no harness.

- [ ] **Step 1: Write the failing test**

Em `tests/test_orquestrador_runtime.py`, troque:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
    "B5": "cruzamento",
    "B6": "ideacao",
    "B8": "escrita",
    "B10": "escrita-humana",
}
```

por:

```python
BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
    "B5": "cruzamento",
    "B6": "ideacao",
    "B8": "escrita",
    "B10": "escrita-humana",
    "B11": "publicar-linkedin",
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -v`
Expected: FAIL — `B11 executor missing` (e demais).

- [ ] **Step 3: Write minimal implementation**

Crie `.agents/agents/publicar-linkedin-executor/AGENT.md`:

```markdown
---
name: publicar-linkedin-executor
description: Executor do bloco B11 (Publica) — publica conteúdo aprovado no LinkedIn.
---

# Executor B11 — Publica

## Input
- Texto aprovado em `content/approved/` (B9, humano).
- Skill `publicar-linkedin` (browser do OpenWork já logado, sem credenciais).

## Processo
1. Usar a skill `publicar-linkedin` para publicar/agendar o conteúdo aprovado.
2. Após a publicação, registrar: `contentctl publish-complete <post_id> <url>`.
3. Confirmar que o arquivo moveu de `content/approved/` para `content/published/`.

## Formato de saída
- Post publicado no LinkedIn.
- Estado: arquivo em `content/published/` + status `published` no banco.

## Contrato
- O conteúdo publicado vem somente de `content/approved/`.
- Sem nova confirmação textual (o texto já foi aprovado no pipeline).
- Sem credenciais em chat, arquivos, banco ou commits.
```

Crie `.agents/agents/publicar-linkedin-revisor/AGENT.md`:

```markdown
---
name: publicar-linkedin-revisor
description: Revisor do bloco B11 (Publica) — valida a publicação.
---

# Revisor B11 — Publica

## O que validar
- O post foi publicado no LinkedIn (URL válida).
- O arquivo moveu de content/approved/ para content/published/.
- O status no banco é `published`.

## Formato de feedback
- Aprovado: `contentctl bloco-ok B11 <artefato>`.
- Feedback: itens com o que corrigir.

## Memória
- Lições de revisões passadas ficam em memory.md (versionado em git).
```

Crie `.agents/agents/publicar-linkedin-revisor/memory.md`:

```markdown
# Memória do revisor B11

Sem feedbacks registrados ainda. Registre aqui toda correção humana sobre a publicação.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_orquestrador_runtime.py .agents/agents/publicar-linkedin-executor/AGENT.md .agents/agents/publicar-linkedin-revisor/AGENT.md .agents/agents/publicar-linkedin-revisor/memory.md
git commit -m "feat: agentes do bloco B11 (Publica) — executor e revisor"
```

---

### Task 11: Gates APPROVAL_* no .env + validação final

**Files:**
- Modify: `.env.example`
- Modify: `.env` (local, NÃO commitado — gitignored)
- Modify: `tests/test_orquestrador_runtime.py` (adicionar `test_env_example_has_all_approval_keys`)

**Interfaces:**
- Consumes: skill orquestradora (Task 1) que lê as chaves `APPROVAL_*`.
- Produces: 9 chaves `APPROVAL_*` com default `human` em `.env.example` e `.env`.

- [ ] **Step 1: Write the failing test**

Em `tests/test_orquestrador_runtime.py`, adicione o método à classe `OrquestradorRuntimeStructureTests` (antes de `if __name__ == "__main__":`):

```python
    def test_env_example_has_all_approval_keys(self):
        env = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        for key in APPROVAL_KEYS:
            self.assertIn(key, env, f".env.example missing {key}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py::OrquestradorRuntimeStructureTests::test_env_example_has_all_approval_keys -v`
Expected: FAIL — `.env.example missing APPROVAL_PILAR`.

- [ ] **Step 3: Write minimal implementation**

Em `.env.example`, troque:

```
ZERNIO_API_KEY=
ZERNIO_ACCOUNT_ID=
LAST30DAYS_COMMAND=
```

por:

```
ZERNIO_API_KEY=
ZERNIO_ACCOUNT_ID=
LAST30DAYS_COMMAND=
APPROVAL_PILAR=human
APPROVAL_PESQUISA=human
APPROVAL_EXECUCAO=human
APPROVAL_CRUZAMENTO=human
APPROVAL_IDEACAO=human
APPROVAL_ESCRITA=human
APPROVAL_REFINAMENTO=human
APPROVAL_VALIDACAO=human
APPROVAL_PUBLICACAO=human
```

No `.env` local (gitignored, NÃO commitado), adicione as mesmas 9 linhas `APPROVAL_*=human` ao final do arquivo, preservando as chaves existentes (`ZERNIO_API_KEY`, `ZERNIO_ACCOUNT_ID`, `LAST30DAYS_COMMAND`).

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_orquestrador_runtime.py -q`
Expected: PASS (6 testes).

- [ ] **Step 5: Rodar suíte completa**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/ -q`
Expected: `110 passed` (ou o total atual + 6 do harness).

- [ ] **Step 6: Commit**

```bash
git add .env.example tests/test_orquestrador_runtime.py
git commit -m "feat: gates APPROVAL_* configuráveis no .env (default human)"
```

---

## Self-Review

**Cobertura do spec (Fase 1):**
- Skill orquestradora (Camada 1): Task 1 — fluxo, blocos, gates, ciclo de revisão, invocação.
- Agentes executores + revisores com memória (Camada 2): Tasks 2–10 — B1, B2, B3, B4, B5, B6, B8, B10, B11 (9 blocos com executor/revisor; `memory.md` do revisor obrigatório).
- B7 e B9 (gates humanos): sem agentes — tratados na skill (Task 1) e na ordem de execução.
- Pesquisa multicanal com peso no LinkedIn: Task 5 (B4) — contrato do executor com LinkedIn primeiro + link individual de cada postagem.
- Gates `APPROVAL_*` configuráveis (default `human`): Task 11 + leitura na skill (Task 1).
- Banco v5→v6, `contentctl bloco-ok`, `contentctl publish-complete`: já implementados no Plano 1 (não reimplementados aqui).

**Placeholders:** nenhum — todos os arquivos têm conteúdo completo.

**Consistência de tipos/nomes:** os slugs dos agentes em `BLOCKS` (harness) batem com os nomes de diretório `.agents/agents/<slug>-executor/` e `.agents/agents/<slug>-revisor/` e com os nomes de executor/revisor na tabela de blocos da skill. As chaves `APPROVAL_*` no harness (`APPROVAL_KEYS`) batem com as do `.env.example` e com a coluna Gate da skill. B7 não tem chave (sempre humano); B9 tem `APPROVAL_VALIDACAO` — consistente com o spec.
