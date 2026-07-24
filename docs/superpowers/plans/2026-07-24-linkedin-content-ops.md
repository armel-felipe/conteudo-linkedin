# LinkedIn Content Ops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar uma operação local para importar o histórico do LinkedIn, propor pilares, pesquisar pautas, revisar rascunhos e agendar posts explicitamente aprovados.

**Architecture:** Markdown é a fonte editorial; SQLite indexa estados, IDs, agenda e métricas. A CLI Python `contentctl` é a única camada que pode chamar o Zernio.

**Tech Stack:** Python 3.12+, biblioteca padrão (`sqlite3`, `unittest`, `urllib.request`, `argparse`), Zernio REST API e comando local configurável do Last30days.

## Global Constraints

- Uso individual, sem painel web, multiusuário, integração Telegram ou publicação autônoma.
- Cadência inicial: duas postagens por semana, texto com imagem opcional.
- Markdown é o registro humano; SQLite é índice, nunca cópia única.
- Agendamento exige status SQLite `approved`, `approved: true` no Markdown e `--confirm` explícito.
- `ZERNIO_API_KEY` fica exclusivamente em `.env`; `.env`, `data/content.db` e `data/imports/` não entram no Git.
- Falha confirmada do Zernio leva a `failed`, sem retentativa automática. Resultado remoto não confirmável após o POST leva a `indeterminate`, bloqueia novos agendamentos e deve ser reconciliado com a mesma chave de idempotência; fuso padrão `America/Sao_Paulo`.
- A pasta ainda não tem Git: inicializá-lo antes do primeiro commit.

---

## File Structure

| Path | Responsibility |
|---|---|
| `AGENTS.md` | Contrato comum de operação para Codex e Hermes. |
| `README.md`, `.env.example`, `.gitignore`, `pyproject.toml` | Setup e segurança local. |
| `contentctl` | Launcher executável da CLI. |
| `src/content_ops/models.py` | Estados e dataclasses. |
| `src/content_ops/db.py` | Schema e consultas SQLite. |
| `src/content_ops/markdown.py` | Ler/gravar registros editoriais. |
| `src/content_ops/zernio.py` | Cliente REST do Zernio. |
| `src/content_ops/history.py`, `pillars.py`, `research.py` | Fundação editorial. |
| `src/content_ops/workflow.py`, `reporting.py`, `cli.py` | Fluxo seguro e interface. |
| `tests/test_*.py` | Testes sem API real. |

### Task 1: Bootstrap seguro e CLI mínima

**Files:** Create `README.md`, `AGENTS.md`, `.env.example`, `.gitignore`, `pyproject.toml`, `contentctl`, `src/content_ops/__init__.py`, `src/content_ops/cli.py`, `tests/test_cli_smoke.py`.

**Interfaces:** produz `./contentctl --help`; todos os comandos futuros usam `python3 -m content_ops.cli`.

- [ ] **Step 1: Inicializar Git e diretórios**

Run:

```bash
git init
mkdir -p src/content_ops tests research content/{ideas,drafts,approved,published} calendar data/imports docs
```

Expected: repositório Git e diretórios existem.

- [ ] **Step 2: Escrever teste primeiro**

Create `tests/test_cli_smoke.py`:

```python
import subprocess
import unittest

class CliSmokeTests(unittest.TestCase):
    def test_help_lists_history(self):
        result = subprocess.run(["./contentctl", "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("history", result.stdout)
```

- [ ] **Step 3: Confirmar falha**

Run: `python3 -m unittest tests.test_cli_smoke -v`

Expected: FAIL porque `contentctl` não existe.

- [ ] **Step 4: Implementar o mínimo**

Create `contentctl`:

```sh
#!/usr/bin/env sh
set -eu
exec python3 -m content_ops.cli "$@"
```

Create `src/content_ops/cli.py`:

```python
import argparse

def build_parser():
    parser = argparse.ArgumentParser(prog="contentctl")
    parser.add_subparsers(dest="command").add_parser("history")
    return parser

if __name__ == "__main__":
    build_parser().parse_args()
```

Run `chmod +x contentctl`. Add `.env`, `data/content.db`, `data/imports/`, `__pycache__/`, `.DS_Store` to `.gitignore`; add `ZERNIO_API_KEY=`, `ZERNIO_ACCOUNT_ID=`, `LAST30DAYS_COMMAND=` to `.env.example`. `AGENTS.md` must forbid credentials in chat/files and require user confirmation before scheduling.

- [ ] **Step 5: Confirmar passagem e commit**

Run: `PYTHONPATH=src python3 -m unittest tests.test_cli_smoke -v`

Expected: PASS.

```bash
git add README.md AGENTS.md .env.example .gitignore pyproject.toml contentctl src tests
git commit -m "chore: bootstrap content operations CLI"
```

### Task 2: Persistência e máquina de estados

**Files:** Create `src/content_ops/models.py`, `src/content_ops/db.py`, `tests/test_db.py`.

**Interfaces:** `Database(path).initialize()`, `upsert_post(external_id, title, status)`, `create_post(status, title)`, `transition_post(post_id, to_status)` e enum `PostStatus`.

- [ ] **Step 1: Escrever testes que falham**

```python
def test_upsert_is_idempotent_by_external_id(self):
    db.upsert_post("linkedin:1", "A", "published")
    db.upsert_post("linkedin:1", "A revisado", "published")
    self.assertEqual(db.count_posts(), 1)

def test_draft_cannot_jump_to_scheduled(self):
    post_id = db.create_post("draft", "Teste")
    with self.assertRaises(ValueError):
        db.transition_post(post_id, PostStatus.SCHEDULED)
```

- [ ] **Step 2: Rodar e observar falha**

Run: `PYTHONPATH=src python3 -m unittest tests.test_db -v`

Expected: FAIL com módulo ausente.

- [ ] **Step 3: Implementar schema e transições**

Criar tabelas `posts`, `pillars`, `research_reports`, `ideas`. `posts.external_id` é `UNIQUE`. Definir estados `idea`, `draft`, `in_review`, `approved`, `scheduled`, `published`, `rejected`, `archived`, `failed`, `indeterminate`. Permitir apenas `idea→draft|archived`, `draft→in_review|archived`, `in_review→approved|rejected|draft`, `approved→scheduled|indeterminate|draft`, `scheduled→published|failed`, `failed→approved|archived`, `indeterminate→scheduled|failed|archived`.

- [ ] **Step 4: Rodar testes e commit**

Run: `PYTHONPATH=src python3 -m unittest tests.test_db -v`

Expected: PASS.

```bash
git add src/content_ops/models.py src/content_ops/db.py tests/test_db.py
git commit -m "feat: add content workflow database"
```

### Task 3: Registros Markdown

**Files:** Create `src/content_ops/markdown.py`, `tests/test_markdown.py`.

**Interfaces:** `write_post_record(path, metadata, body)` e `read_post_record(path) -> tuple[dict, str]`.

- [ ] **Step 1: Escrever teste primeiro**

```python
def test_round_trips_metadata_and_body(self):
    write_post_record(path, {"status": "approved", "approved": True}, "Texto")
    metadata, body = read_post_record(path)
    self.assertTrue(metadata["approved"])
    self.assertEqual(body, "Texto")
```

- [ ] **Step 2: Confirmar falha**

Run: `PYTHONPATH=src python3 -m unittest tests.test_markdown -v`

Expected: FAIL com módulo ausente.

- [ ] **Step 3: Implementar sem dependência YAML**

Usar JSON delimitado por `---json` e `---`:

```python
path.write_text("---json\n" + json.dumps(metadata, ensure_ascii=False, indent=2) + "\n---\n\n" + body.strip() + "\n", encoding="utf-8")
```

`read_post_record` deve lançar `ValueError` para delimitadores ausentes, JSON não-objeto ou corpo vazio.

- [ ] **Step 4: Verificar e commit**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`

Expected: PASS.

```bash
git add src/content_ops/markdown.py tests/test_markdown.py
git commit -m "feat: add markdown editorial records"
```

### Task 4: Importação somente-leitura do histórico Zernio

**Files:** Create `src/content_ops/zernio.py`, `src/content_ops/history.py`, `tests/test_history.py`; modify `cli.py`, `README.md`.

**Interfaces:** `ZernioClient.list_external_posts(account_id)` e `import_history(client, db, import_dir)`. Esta tarefa não contém endpoint de criação de post.

- [ ] **Step 1: Criar teste com fake client**

```python
class FakeZernioClient:
    def list_external_posts(self, account_id):
        return [{"_id": "a1", "content": "Python e dados", "status": "published"}]

def test_import_writes_one_row_and_snapshot(self):
    import_history(FakeZernioClient(), db, "account", import_dir)
    self.assertEqual(db.count_posts(), 1)
    self.assertEqual(len(list(import_dir.glob("*.json"))), 1)
```

- [ ] **Step 2: Confirmar falha**

Run: `PYTHONPATH=src python3 -m unittest tests.test_history -v`

Expected: FAIL com `content_ops.history` ausente.

- [ ] **Step 3: Implementar cliente paginado e importador idempotente**

`ZernioClient` faz GET em `/api/v1/posts?source=external&accountId=<id>&page=<n>&limit=100`, adiciona `Authorization: Bearer`, pagina até o fim e lança `ZernioError(status, message)` para HTTP/JSON inválido. O importador grava resposta bruta em `data/imports/zernio-<timestamp>-page-<n>.json` e faz upsert por `linkedin:<_id>` como `published`.

Implementar `contentctl history import`, exigindo variáveis de ambiente, sem revelar valor da chave.

- [ ] **Step 4: Verificar e commit**

Run: `PYTHONPATH=src python3 -m unittest tests.test_history -v`

Expected: PASS.

Run: `PYTHONPATH=src ./contentctl history import`

Expected: código 2 e nomes das configurações faltantes, sem chamada de rede.

```bash
git add src/content_ops/zernio.py src/content_ops/history.py src/content_ops/cli.py tests/test_history.py README.md
git commit -m "feat: import LinkedIn history through Zernio"
```

### Task 5: Proposta e aprovação de até cinco pilares

**Files:** Create `src/content_ops/pillars.py`, `tests/test_pillars.py`; modify `cli.py`; create `docs/pillars.md`.

**Interfaces:** `propose_pillars(posts, limit=5) -> list[PillarProposal]`; `contentctl pillars propose`; `contentctl pillars approve <name>`.

- [ ] **Step 1: Escrever teste primeiro**

```python
def test_proposes_ranked_distinct_topics(self):
    proposals = propose_pillars(["Python para dados", "Dados em Python", "Carreira de engenharia"], limit=5)
    self.assertEqual(proposals[0].name, "Python e dados")
    self.assertLessEqual(len(proposals), 5)
```

- [ ] **Step 2: Confirmar falha**

Run: `PYTHONPATH=src python3 -m unittest tests.test_pillars -v`

Expected: FAIL com módulo ausente.

- [ ] **Step 3: Implementar classificação inicial transparente**

Normalizar stop words em português. Mapear `python|dados|data` para `Python e dados`, `carreira|emprego|entrevista` para `Carreira e oportunidades`, `ia|ai|llm` para `IA aplicada`; demais tópicos usam os dois termos úteis mais frequentes. Classificar por número de posts distintos e desempatar alfabeticamente. Gerar `docs/pillars.md` com nome, contagem, IDs de evidência e `approved: false`. Aprovação grava no SQLite e Markdown, recusa mais de cinco pilares aprovados.

- [ ] **Step 4: Verificar e commit**

Run: `PYTHONPATH=src python3 -m unittest tests.test_pillars -v`

Expected: PASS.

```bash
git add src/content_ops/pillars.py src/content_ops/cli.py docs/pillars.md tests/test_pillars.py
git commit -m "feat: propose editorial pillars from history"
```

### Task 6: Pesquisa recente, ideias e rascunhos rastreáveis

**Files:** Create `src/content_ops/research.py`, `src/content_ops/workflow.py`, `tests/test_workflow.py`; modify `cli.py`, `AGENTS.md`.

**Interfaces:** `capture_research(topic, command, target_path)`, `create_draft(database, idea, pillar, path)`; o banco é explícito para garantir que apenas pilares aprovados sejam usados.

- [ ] **Step 1: Escrever teste primeiro**

```python
def test_new_draft_is_traceable_and_unapproved(self):
    path = create_draft({"id": "idea-1", "research_path": "research/x.md", "angle": "..."}, "IA aplicada", draft_path)
    metadata, _ = read_post_record(path)
    self.assertEqual(metadata["status"], "draft")
    self.assertFalse(metadata["approved"])
    self.assertEqual(metadata["research_path"], "research/x.md")
```

- [ ] **Step 2: Confirmar falha**

Run: `PYTHONPATH=src python3 -m unittest tests.test_workflow -v`

Expected: FAIL porque `create_draft` não existe.

- [ ] **Step 3: Implementar fluxo editorial**

`capture_research` executa o `LAST30DAYS_COMMAND` configurado, grava stdout verbatim em `research/YYYY-MM-DD--<slug>.md` e recusa código diferente de zero sem criar ideia. `contentctl research discover` apenas captura pesquisa. `contentctl ideas create --research <path> --pillar <approved-pillar> --angle <texto>` cria ideia. `contentctl draft create <idea-id>` cria Markdown em `content/drafts/` com `status: draft`, `approved: false`, pilar, `objective: authority_and_job_opportunities`, caminho da pesquisa, `image_url: null` e `zernio_post_id: null`.

- [ ] **Step 4: Verificar e commit**

Run: `PYTHONPATH=src python3 -m unittest tests.test_workflow -v`

Expected: PASS.

```bash
git add src/content_ops/research.py src/content_ops/workflow.py src/content_ops/cli.py AGENTS.md tests/test_workflow.py
git commit -m "feat: create research-backed content drafts"
```

### Task 7: Aprovação explícita e agendamento seguro

**Files:** Modify `zernio.py`, `workflow.py`, `cli.py`; create `tests/test_scheduling.py`.

**Interfaces:** `approve_draft(post_id, markdown_path)` e `schedule_post(post_id, markdown_path, scheduled_for, confirmed, client)`; retorna ID Zernio ou lança `SchedulingValidationError` antes de HTTP.

- [ ] **Step 1: Escrever testes primeiro**

```python
def test_schedule_requires_both_approvals(self):
    with self.assertRaises(SchedulingValidationError):
        schedule_post(post_id, path, "2026-08-01T10:00:00", True, fake_client)
    self.assertEqual(fake_client.create_calls, 0)

def test_schedule_calls_client_only_after_confirmation(self):
    approve_db_and_markdown(post_id, path)
    self.assertEqual(schedule_post(post_id, path, "2026-08-01T10:00:00", True, fake_client), "z-1")
    self.assertEqual(fake_client.create_calls, 1)
```

- [ ] **Step 2: Confirmar falha**

Run: `PYTHONPATH=src python3 -m unittest tests.test_scheduling -v`

Expected: FAIL porque o agendamento não existe.

- [ ] **Step 3: Implementar dois portões de segurança**

`contentctl review approve <post-id>` deve mover `in_review→approved` e atualizar o Markdown. Se a escrita falhar, restaurar estado anterior. `contentctl schedule <post-id> --at <ISO> --confirm` recusa sem `--confirm`, data passada, corpo vazio, pilar não aprovado, conta/chave ausente ou `image_url` que não seja HTTP(S). Antes do POST, gera e persiste uma chave UUID de idempotência no post. Chama POST `/api/v1/posts` com o cabeçalho `x-request-id` igual a essa chave, `content`, `scheduledFor`, `timezone: "America/Sao_Paulo"`, alvo LinkedIn com `accountId` e `mediaItems` somente com imagem. Sucesso salva ID e muda para `scheduled`; falha confirmada anterior ao envio muda para `failed`. Se o resultado de uma tentativa remota não puder ser confirmado ou persistido, muda para `indeterminate`, bloqueia novos POSTs e `contentctl schedule reconcile <post-id>` repete a chamada usando a mesma chave para recuperar o post original sem criar duplicata.

- [ ] **Step 4: Verificar e commit**

Run: `PYTHONPATH=src python3 -m unittest tests.test_scheduling -v`

Expected: PASS.

Run: `PYTHONPATH=src ./contentctl schedule 1 --at 2026-08-01T10:00:00`

Expected: código 2, mensagem `--confirm is required`, zero chamadas HTTP.

```bash
git add src/content_ops/zernio.py src/content_ops/workflow.py src/content_ops/cli.py tests/test_scheduling.py
git commit -m "feat: require explicit approval before scheduling"
```

### Task 8: Métricas, relatório semanal e verificação ponta a ponta

**Files:** Create `src/content_ops/reporting.py`, `tests/test_reporting.py`; modify `cli.py`, `README.md`, `AGENTS.md`.

**Interfaces:** `weekly_report(db, week_start) -> str` e `sync_published_post(client, db, post_id)`.

- [ ] **Step 1: Escrever teste primeiro**

```python
def test_weekly_report_counts_cadence(self):
    report = weekly_report(populated_database, date(2026, 7, 27))
    self.assertIn("Cadência: 2/2", report)
    self.assertIn("scheduled", report)
```

- [ ] **Step 2: Confirmar falha**

Run: `PYTHONPATH=src python3 -m unittest tests.test_reporting -v`

Expected: FAIL com módulo ausente.

- [ ] **Step 3: Implementar relatório e sync de leitura**

`contentctl report weekly --week 2026-07-27` conta estados na semana segunda-domingo em `America/Sao_Paulo`, exibe `Cadência: N/2`. `contentctl posts sync <post-id>` usa apenas GET de post Zernio, só muda `scheduled→published` se a API responder publicado, e salva `platformPostUrl` quando vier. Erro de rede não é publicação. Atualizar README com walkthrough que só agenda mediante `.env` real e `--confirm`; AGENTS deve exigir que o agente mostre texto, horário e conta alvo antes de sugerir o comando.

- [ ] **Step 4: Rodar verificação completa e commit**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`

Expected: todos os testes PASS.

Run: `PYTHONPATH=src ./contentctl --help && PYTHONPATH=src ./contentctl report weekly --week 2026-07-27`

Expected: ajuda lista grupos e relatório vazio sai com código zero após DB inicializado.

```bash
git add src/content_ops/reporting.py src/content_ops/cli.py tests/test_reporting.py README.md AGENTS.md
git commit -m "feat: report weekly content cadence"
```

## Plan self-review

- Cobertura: Tasks 1-3 fornecem contrato, segurança, banco, estados e registros Markdown; 4-5 tratam importação e pilares; 6-8 tratam Last30days, aprovação, agendamento, métricas e cadência.
- Limites: Hermes e Telegram permanecem externos e usam `AGENTS.md` mais `contentctl`.
- Segurança: nenhum endpoint de escrita é chamado antes dos dois estados de aprovação e `--confirm`.
- Consistência: `PostStatus`, `Database`, metadados Markdown, `ZernioClient`, `create_draft`, `approve_draft` e `schedule_post` são definidos antes de seus consumidores.
