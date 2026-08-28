# Orquestrador Runtime — Plano 1: Indexação por rodada + comandos CLI

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fundação de código do orquestrador: banco v6 (rounds, round_id, label, ideas.sources) + comandos `contentctl bloco-ok` e `contentctl publish-complete`.

**Architecture:** Estende o SQLite existente (migração v5→v6) com a unidade de trabalho "rodada" e o aliás legível de pesquisa; adiciona dois comandos CLI mecânicos que o orquestrador (skill, Plano 2) invocará. Segue o padrão TDD do repo (testes em `tests/`, código em `src/content_ops/`).

**Tech Stack:** Python 3.12, SQLite (migrações versionadas via `PRAGMA user_version`), argparse (CLI), unittest/pytest.

## Global Constraints

- Python 3.12+ (`/Users/mac/.pyenv/shims/python3.12`).
- Rodar testes: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/ -q`
- `CURRENT_SCHEMA_VERSION` em `src/content_ops/db.py` sobe de 5 para 6.
- Label de pesquisa: `YYYY_MM_DD <pillar-slug> <detalhe-pesquisa>`, ≤50 caracteres.
- B7 é o único gate humano intocável (sem chave `APPROVAL_*`); B9 tem chave `APPROVAL_VALIDACAO`.
- Sem credenciais em chat, arquivos versionados, banco ou commits (AGENTS.md).
- Commits frequentes, mensagens no estilo do repo (`feat:`, `refactor:`, `fix:`).

---

### Task 1: Migração v6 — tabela `rounds` + colunas `round_id`/`label` em `research_reports` + `sources` em `ideas`

**Files:**
- Modify: `src/content_ops/db.py` (CURRENT_SCHEMA_VERSION, migrations tuple, `_migrate_to_v6`)
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: nada novo (migração pura).
- Produces: schema v6 com `rounds(id, created_at, pillar, status, plano_path)`, `research_reports.round_id` (FK), `research_reports.label` (TEXT), `ideas.sources` (TEXT NOT NULL DEFAULT '[]').

- [ ] **Step 1: Write the failing test**

Adicione em `tests/test_db.py` (classe `DatabaseTests`):

```python
    def test_initialize_migrates_round_and_label_columns(self):
        legacy_path = Path(self.temporary_directory.name) / "legacy-rounds.db"
        with sqlite3.connect(legacy_path) as connection:
            connection.execute(
                "CREATE TABLE research_reports ("
                "id INTEGER PRIMARY KEY, topic TEXT NOT NULL, path TEXT NOT NULL, "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, pillar TEXT)"
            )
            connection.execute(
                "CREATE TABLE ideas ("
                "id INTEGER PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'idea', "
                "pillar_id INTEGER, research_report_id INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "INSERT INTO research_reports (topic, path) VALUES ('IA', 'research/ia.md')"
            )

        from content_ops.db import CURRENT_SCHEMA_VERSION, Database

        Database(legacy_path).initialize()

        with sqlite3.connect(legacy_path) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            rr_cols = {row[1] for row in connection.execute("PRAGMA table_info(research_reports)")}
            ideas_cols = {row[1] for row in connection.execute("PRAGMA table_info(ideas)")}
        self.assertEqual(version, CURRENT_SCHEMA_VERSION)
        self.assertIn("rounds", tables)
        self.assertTrue({"round_id", "label"} <= rr_cols)
        self.assertIn("sources", ideas_cols)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_db.py::DatabaseTests::test_initialize_migrates_round_and_label_columns -v`
Expected: FAIL — `no such column: round_id` (ou `no such table: rounds`).

- [ ] **Step 3: Write minimal implementation**

Em `src/content_ops/db.py`:

```python
CURRENT_SCHEMA_VERSION = 6
```

Na tupla `migrations`, adicione `self._migrate_to_v6` após `self._migrate_to_v5`.

Adicione o método:

```python
    @classmethod
    def _migrate_to_v6(cls, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS rounds (
                id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                pillar TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                plano_path TEXT
            );
            """
        )
        cls._add_columns(
            connection,
            "research_reports",
            {
                "round_id": "INTEGER REFERENCES rounds(id)",
                "label": "TEXT",
            },
        )
        cls._add_columns(
            connection,
            "ideas",
            {"sources": "TEXT NOT NULL DEFAULT '[]'"},
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_db.py -q`
Expected: PASS (todos os testes do arquivo).

- [ ] **Step 5: Commit**

```bash
git add src/content_ops/db.py tests/test_db.py
git commit -m "feat: migração v6 — rounds, round_id/label em research_reports, sources em ideas"
```

---

### Task 2: Métodos de rodada no banco — `create_round`, `list_rounds`, `close_round`

**Files:**
- Modify: `src/content_ops/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: schema v6 (Task 1).
- Produces: `create_round(pillar: str, plano_path: str) -> int`, `list_rounds() -> list[sqlite3.Row]`, `close_round(round_id: int) -> None`.

- [ ] **Step 1: Write the failing test**

```python
    def test_round_lifecycle_create_list_close(self):
        round_id = self.db.create_round("Liderança e gestão de times", "runtime/rodadas/2026-08-28.md")
        self.assertIsInstance(round_id, int)

        rounds = self.db.list_rounds()
        self.assertEqual(len(rounds), 1)
        self.assertEqual(rounds[0]["pillar"], "Liderança e gestão de times")
        self.assertEqual(rounds[0]["status"], "open")

        self.db.close_round(round_id)
        self.assertEqual(self.db.list_rounds()[0]["status"], "closed")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_db.py::DatabaseTests::test_round_lifecycle_create_list_close -v`
Expected: FAIL — `AttributeError: 'Database' object has no attribute 'create_round'`.

- [ ] **Step 3: Write minimal implementation**

Em `src/content_ops/db.py`, após `list_research_reports`:

```python
    def create_round(self, pillar: str, plano_path: str) -> int:
        """Create an open work round and return its identifier."""
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO rounds (pillar, plano_path) VALUES (?, ?)",
                (pillar, plano_path),
            )
            return cursor.lastrowid

    def list_rounds(self) -> list[sqlite3.Row]:
        """Return all rounds ordered by creation."""
        with self._connect() as connection:
            return connection.execute(
                "SELECT id, created_at, pillar, status, plano_path FROM rounds ORDER BY id"
            ).fetchall()

    def close_round(self, round_id: int) -> None:
        """Mark a round as closed (all its blocks finished)."""
        with self._connect() as connection:
            connection.execute(
                "UPDATE rounds SET status = 'closed' WHERE id = ?", (round_id,)
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_db.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/content_ops/db.py tests/test_db.py
git commit -m "feat: ciclo de vida de rodadas (create/list/close)"
```

---

### Task 3: `label` e `round_id` no registro de pesquisa + listagem com label

**Files:**
- Modify: `src/content_ops/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: `create_research_report` existente (v5), schema v6 (Task 1).
- Produces: `create_research_report(topic, path, pillar=None, round_id=None, label=None) -> int`; `list_research_reports() -> list[tuple[str, str, str | None, int | None, str | None]]` (topic, path, pillar, round_id, label).

- [ ] **Step 1: Write the failing test**

```python
    def test_research_report_records_round_and_label(self):
        round_id = self.db.create_round("Liderança e gestão de times", "runtime/rodadas/x.md")
        self.db.create_research_report(
            "liderança em times de alta performance",
            "research/lideranca-times.md",
            pillar="Liderança e gestão de times",
            round_id=round_id,
            label="2026_08_28 lideranca-gestao-times cultura-times-alta-perf",
        )

        reports = self.db.list_research_reports()
        self.assertEqual(len(reports), 1)
        topic, path, pillar, rid, label = reports[0]
        self.assertEqual(rid, round_id)
        self.assertEqual(label, "2026_08_28 lideranca-gestao-times cultura-times-alta-perf")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_db.py::DatabaseTests::test_research_report_records_round_and_label -v`
Expected: FAIL — `TypeError: create_research_report() got an unexpected keyword argument 'round_id'`.

- [ ] **Step 3: Write minimal implementation**

Em `src/content_ops/db.py`, substitua `create_research_report`:

```python
    def create_research_report(
        self,
        topic: str,
        path: str,
        pillar: str | None = None,
        round_id: int | None = None,
        label: str | None = None,
    ) -> int:
        """Record a successfully captured research report."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO research_reports (topic, path, pillar, round_id, label)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    topic = excluded.topic,
                    pillar = excluded.pillar,
                    round_id = excluded.round_id,
                    label = excluded.label
                """,
                (topic, path, pillar, round_id, label),
            )
            return cursor.lastrowid
```

E substitua `list_research_reports`:

```python
    def list_research_reports(self) -> list[tuple[str, str, str | None, int | None, str | None]]:
        """Return (topic, path, pillar, round_id, label) for every captured report."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT topic, path, pillar, round_id, label FROM research_reports ORDER BY id"
            ).fetchall()
        return [(row["topic"], row["path"], row["pillar"], row["round_id"], row["label"]) for row in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_db.py tests/test_pillars.py -q`
Expected: PASS (ajuste `propose_pillars_from_research` se quebrar — ele desempacota 3 tuplas; veja Task 4).

- [ ] **Step 5: Commit**

```bash
git add src/content_ops/db.py tests/test_db.py
git commit -m "feat: label e round_id no registro de pesquisa"
```

---

### Task 4: Ajustar `propose_pillars_from_research` para a nova tupla (5 campos)

**Files:**
- Modify: `src/content_ops/pillars.py`
- Test: `tests/test_pillars.py`

**Interfaces:**
- Consumes: `list_research_reports()` agora retorna 5 campos (Task 3).
- Produces: `propose_pillars_from_research(database, limit=5)` inalterado em assinatura, mas desempacota 5 campos.

- [ ] **Step 1: Write the failing test**

Adicione em `tests/test_pillars.py` (classe `ResearchDrivenPillarTests`):

```python
    def test_proposes_pillars_ignores_round_and_label_fields(self):
        from content_ops.pillars import propose_pillars_from_research

        round_id = self.database.create_round("Liderança e gestão de times", "runtime/rodadas/x.md")
        self.database.create_research_report(
            "liderança em times de alta performance",
            "research/lideranca-times.md",
            pillar="Liderança e gestão de times",
            round_id=round_id,
            label="2026_08_28 lideranca-gestao-times cultura-times-alta-perf",
        )

        proposals = propose_pillars_from_research(self.database)

        self.assertEqual(proposals[0].name, "Liderança e gestão de times")
        self.assertEqual(proposals[0].evidence_ids, ("research/lideranca-times.md",))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_pillars.py::ResearchDrivenPillarTests::test_proposes_pillars_ignores_round_and_label_fields -v`
Expected: FAIL — `ValueError: too many values to unpack (expected 3)`.

- [ ] **Step 3: Write minimal implementation**

Em `src/content_ops/pillars.py`, em `propose_pillars_from_research`, troque o desempacotamento:

```python
    reports = database.list_research_reports()
    declared: dict[str, list[str]] = defaultdict(list)
    unassigned: list[tuple[str, str]] = []
    for topic, path, pillar, _round_id, _label in reports:
        if pillar:
            declared[pillar].append(path)
        else:
            unassigned.append((path, topic))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_pillars.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/content_ops/pillars.py tests/test_pillars.py
git commit -m "refactor: desempacotar 5 campos de list_research_reports"
```

---

### Task 5: `ideas.sources` — `create_idea` aceita fontes multi-pesquisa

**Files:**
- Modify: `src/content_ops/db.py`, `src/content_ops/workflow.py`, `src/content_ops/cli.py`
- Test: `tests/test_db.py`, `tests/test_cli_end_to_end.py`

**Interfaces:**
- Consumes: schema v6 `ideas.sources` (Task 1).
- Produces: `create_idea(database, research_path, pillar, angle, sources=None, ideas_directory=None)`; `ideas create --sources "path1,path2"` (opcional).

- [ ] **Step 1: Write the failing test**

Em `tests/test_db.py`:

```python
    def test_create_idea_stores_multi_research_sources(self):
        self.db.create_research_report("IA", "research/ia.md", pillar="IA aplicada")
        self.db.upsert_pillar("IA aplicada")
        self.db.approve_pillar("IA aplicada")
        import json

        idea_id = self.db.create_idea(
            "Ideia cruzada",
            "IA aplicada",
            "research/ia.md",
            sources=["research/ia.md", "research/ia2.md"],
        )

        with sqlite3.connect(self.path) as connection:
            sources = connection.execute(
                "SELECT sources FROM ideas WHERE id = ?", (idea_id,)
            ).fetchone()[0]
        self.assertEqual(json.loads(sources), ["research/ia.md", "research/ia2.md"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_db.py::DatabaseTests::test_create_idea_stores_multi_research_sources -v`
Expected: FAIL — `TypeError: create_idea() got an unexpected keyword argument 'sources'`.

- [ ] **Step 3: Write minimal implementation**

Em `src/content_ops/db.py`, `create_idea` — adicione parâmetro e persistência:

```python
    def create_idea(
        self,
        title: str,
        pillar: str,
        research_path: str,
        connection: sqlite3.Connection | None = None,
        sources: list[str] | None = None,
    ) -> int:
        """Persist an idea linked to one approved pillar and captured report."""
        if connection is None:
            with self.transaction() as transaction:
                return self.create_idea(
                    title, pillar, research_path, transaction, sources=sources
                )
        row = connection.execute(
            """
            SELECT pillars.id AS pillar_id, research_reports.id AS research_report_id
            FROM pillars CROSS JOIN research_reports
            WHERE pillars.name = ?
              AND pillars.approved = 1
              AND research_reports.path = ?
            """,
            (pillar, research_path),
        ).fetchone()
        if row is None:
            if connection.execute(
                "SELECT 1 FROM pillars WHERE name = ? AND approved = 0", (pillar,)
            ).fetchone():
                raise ValueError(f"Pillar {pillar!r} is not approved")
            raise ValueError("Pillar or research report does not exist")
        idea_key = hashlib.sha256(
            json.dumps(
                [title, pillar, research_path],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        sources_json = json.dumps(sources or [], ensure_ascii=False, sort_keys=True)
        connection.execute(
            """
            INSERT INTO ideas (
                title, pillar_id, research_report_id, idea_key, sources
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(idea_key) DO NOTHING
            """,
            (title, row["pillar_id"], row["research_report_id"], idea_key, sources_json),
        )
        idea_row = connection.execute(
            "SELECT id FROM ideas WHERE idea_key = ?", (idea_key,)
        ).fetchone()
        if idea_row is None:
            raise RuntimeError("Could not persist idea")
        return idea_row["id"]
```

Em `src/content_ops/workflow.py`, `create_idea` — repasse `sources`:

```python
def create_idea(
    database: Database,
    research_path: str,
    pillar: str,
    angle: str,
    ideas_directory: str | Path | None = None,
    sources: list[str] | None = None,
) -> dict[str, object]:
    """Create one deterministic idea and, when requested, its editorial record."""
    created_path: Path | None = None
    try:
        with database.transaction() as connection:
            idea_id = database.create_idea(
                angle, pillar, research_path, connection=connection, sources=sources
            )
            if ideas_directory is not None:
                idea_path = Path(ideas_directory) / f"idea-{idea_id}.md"
                idea_path.parent.mkdir(parents=True, exist_ok=True)
                if idea_path.exists():
                    _require_matching_record(idea_path, "idea_id", idea_id)
                else:
                    metadata = {
                        "idea_id": idea_id,
                        "status": PostStatus.IDEA.value,
                        "pillar": pillar,
                        "objective": "authority_and_job_opportunities",
                        "research_path": research_path,
                        "sources": [
                            {"type": "research", "path": p}
                            for p in (sources or [research_path])
                        ],
                        "suggested_time": None,
                    }
                    created_path = idea_path
                    write_post_record(idea_path, metadata, f"Ângulo: {angle}")
    except BaseException:
        if created_path is not None:
            created_path.unlink(missing_ok=True)
        raise
    return {
        "id": idea_id,
        "research_path": research_path,
        "pillar": pillar,
        "angle": angle,
    }
```

Em `src/content_ops/cli.py`, parser de `ideas create`:

```python
    idea_creation.add_argument(
        "--sources",
        help="Comma-separated research paths that sustain this idea (multi-pesquisa)",
    )
```

E no dispatch:

```python
            sources = None
            if arguments.sources:
                sources = [s.strip() for s in arguments.sources.split(",") if s.strip()]
            try:
                idea = create_idea(
                    database,
                    arguments.research,
                    arguments.pillar,
                    arguments.angle,
                    ideas_directory=repository_root / "content" / "ideas",
                    sources=sources,
                )
            except ValueError as error:
                parser.error(str(error))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_db.py tests/test_cli_end_to_end.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/content_ops/db.py src/content_ops/workflow.py src/content_ops/cli.py tests/test_db.py tests/test_cli_end_to_end.py
git commit -m "feat: ideias com fontes multi-pesquisa (ideas.sources)"
```

---

### Task 6: `contentctl bloco-ok` — registra validação do revisor

**Files:**
- Modify: `src/content_ops/cli.py`, `src/content_ops/db.py`
- Test: `tests/test_cli_end_to_end.py`, `tests/test_db.py`

**Interfaces:**
- Consumes: schema v6 (Task 1).
- Produces: tabela `block_validations(id, block, artifact_path, approved, created_at)`; comando `contentctl bloco-ok <bloco> <artefato>`.

- [ ] **Step 1: Write the failing test**

Em `tests/test_db.py`:

```python
    def test_block_validation_records_reviewer_approval(self):
        self.db.record_block_validation("B4", "research/lideranca-times.md")

        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT block, artifact_path, approved FROM block_validations WHERE block = ?",
                ("B4",),
            ).fetchone()
        self.assertEqual(row[0], "B4")
        self.assertEqual(row[1], "research/lideranca-times.md")
        self.assertEqual(row[2], 1)
```

Em `tests/test_cli_end_to_end.py`:

```python
    def test_bloco_ok_registers_reviewer_validation(self):
        output = self.run_cli(["bloco-ok", "B4", "research/ia.md"])

        self.assertIn("Registered validation for B4", output)
        with self.database._connect() as connection:
            row = connection.execute(
                "SELECT block, approved FROM block_validations WHERE block = ?", ("B4",)
            ).fetchone()
        self.assertEqual(row[0], "B4")
        self.assertEqual(row[1], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_db.py::DatabaseTests::test_block_validation_records_reviewer_approval tests/test_cli_end_to_end.py::EditorialCliEndToEndTests::test_bloco_ok_registers_reviewer_validation -v`
Expected: FAIL — `no such table: block_validations` / `invalid choice: 'bloco-ok'`.

- [ ] **Step 3: Write minimal implementation**

Em `src/content_ops/db.py`, `_migrate_to_v6` — adicione a tabela:

```python
            CREATE TABLE IF NOT EXISTS block_validations (
                id INTEGER PRIMARY KEY,
                block TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                approved INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
```

E o método:

```python
    def record_block_validation(self, block: str, artifact_path: str) -> None:
        """Record a reviewer's approval for one block's artifact."""
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO block_validations (block, artifact_path) VALUES (?, ?)",
                (block, artifact_path),
            )
```

Em `src/content_ops/cli.py`, parser:

```python
    blocks = commands.add_parser("bloco-ok", help="Register a reviewer's block validation")
    blocks.add_argument("bloco")
    blocks.add_argument("artefato")
```

E no dispatch (antes do bloco `pillars`):

```python
    if arguments.command == "bloco-ok":
        from content_ops.db import Database

        database = Database(repository_root / "data" / "content.db")
        database.initialize()
        database.record_block_validation(arguments.bloco, arguments.artefato)
        print(f"Registered validation for {arguments.bloco}.")
        return
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_db.py tests/test_cli_end_to_end.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/content_ops/db.py src/content_ops/cli.py tests/test_db.py tests/test_cli_end_to_end.py
git commit -m "feat: contentctl bloco-ok registra validação do revisor"
```

---

### Task 7: `contentctl publish-complete` — move approved→published

**Files:**
- Modify: `src/content_ops/cli.py`, `src/content_ops/db.py`, `src/content_ops/models.py`, `src/content_ops/workflow.py`
- Test: `tests/test_db.py`, `tests/test_cli_end_to_end.py`

**Interfaces:**
- Consumes: `ALLOWED_POST_TRANSITIONS` (models), `read_post_record`/`write_post_record` (markdown), `transition_post` (db).
- Produces: transição `APPROVED → PUBLISHED` permitida; `publish_complete(post_id, url, markdown_path, database)` em workflow; comando `contentctl publish-complete <post_id> <url>`.

- [ ] **Step 1: Write the failing test**

Em `tests/test_db.py`:

```python
    def test_approved_post_can_transition_to_published(self):
        from content_ops.models import PostStatus

        post_id = self.db.create_post(PostStatus.APPROVED, "Aprovado")
        self.db.transition_post(post_id, PostStatus.PUBLISHED)

        with sqlite3.connect(self.path) as connection:
            status = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (post_id,)
            ).fetchone()[0]
        self.assertEqual(status, "published")
```

Em `tests/test_cli_end_to_end.py`:

```python
    def test_publish_complete_moves_approved_to_published(self):
        from content_ops.markdown import write_post_record
        from content_ops.models import PostStatus

        post_id = self.database.create_post(PostStatus.APPROVED, "Artigo aprovado")
        source = self.root / "content" / "approved" / "artigo.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        write_post_record(
            source,
            {"post_id": post_id, "status": "approved", "approved": True, "pillar": "IA aplicada"},
            "Corpo do artigo",
        )

        output = self.run_cli(["publish-complete", str(post_id), "https://linkedin.com/posts/1"])

        self.assertIn("Published post", output)
        self.assertFalse(source.exists())
        published = self.root / "content" / "published" / "artigo.md"
        self.assertTrue(published.is_file())
        metadata, _ = read_post_record(published)
        self.assertEqual(metadata["status"], "published")
        self.assertEqual(metadata["published_url"], "https://linkedin.com/posts/1")
        with self.database._connect() as connection:
            status = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (post_id,)
            ).fetchone()[0]
        self.assertEqual(status, "published")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/test_db.py::DatabaseTests::test_approved_post_can_transition_to_published tests/test_cli_end_to_end.py::EditorialCliEndToEndTests::test_publish_complete_moves_approved_to_published -v`
Expected: FAIL — `Cannot transition post from approved to published` / `invalid choice: 'publish-complete'`.

- [ ] **Step 3: Write minimal implementation**

Em `src/content_ops/models.py`, adicione `PUBLISHED` às transições de `APPROVED`:

```python
    PostStatus.APPROVED: frozenset(
        {
            PostStatus.SCHEDULED,
            PostStatus.DRAFT,
            PostStatus.FAILED,
            PostStatus.INDETERMINATE,
            PostStatus.PUBLISHED,
        }
    ),
```

Em `src/content_ops/workflow.py`, adicione:

```python
def publish_complete(
    post_id: int,
    published_url: str,
    markdown_path: str | Path,
    database: Database,
) -> Path:
    """Move an approved record to content/published/ and record the publication."""
    path = Path(markdown_path)
    metadata, body = read_post_record(path)
    if metadata.get("status") != PostStatus.APPROVED.value or metadata.get("approved") is not True:
        raise SchedulingValidationError("Post is not approved")
    if not isinstance(published_url, str) or not published_url.startswith("https://"):
        raise SchedulingValidationError("published_url must be an https URL")
    published_path = path.parent.parent / "published" / path.name
    published_path.parent.mkdir(parents=True, exist_ok=True)
    updated = dict(metadata)
    updated["status"] = PostStatus.PUBLISHED.value
    updated["published_url"] = published_url
    try:
        with database.transaction() as connection:
            database.transition_post(post_id, PostStatus.PUBLISHED, connection)
            write_post_record(published_path, updated, body)
            path.unlink()
    except BaseException:
        if published_path.exists():
            published_path.unlink(missing_ok=True)
        raise
    return published_path
```

Em `src/content_ops/cli.py`, parser:

```python
    publish = commands.add_parser(
        "publish-complete", help="Move an approved post to content/published/"
    )
    publish.add_argument("post_id", type=int)
    publish.add_argument("url")
```

E no dispatch (junto ao bloco `review`/`schedule`):

```python
    if arguments.command == "publish-complete":
        from content_ops.db import Database
        from content_ops.workflow import (
            SchedulingValidationError,
            publish_complete,
        )

        database = Database(repository_root / "data" / "content.db")
        database.initialize()
        try:
            markdown_path = _find_post_markdown(repository_root, arguments.post_id)
            published_path = publish_complete(
                arguments.post_id,
                arguments.url,
                markdown_path,
                database,
            )
        except (SchedulingValidationError, ValueError) as error:
            parser.error(str(error))
        print(f"Published post {arguments.post_id} -> {published_path.relative_to(repository_root)}.")
        return
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/ -q`
Expected: PASS (suíte completa).

- [ ] **Step 5: Commit**

```bash
git add src/content_ops/models.py src/content_ops/workflow.py src/content_ops/cli.py tests/test_db.py tests/test_cli_end_to_end.py
git commit -m "feat: contentctl publish-complete move approved para published"
```

---

### Task 8: Migrar banco real + registrar rodada e labels das pesquisas existentes

**Files:**
- Modify: `data/content.db` (via `Database.initialize()`), `docs/pillars.md` (via `pillars propose`)

**Interfaces:**
- Consumes: Tasks 1–7.
- Produces: banco real em v6; rodada aberta com as 5 pesquisas de liderança; labels preenchidos.

- [ ] **Step 1: Migrar o banco real**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -c "from content_ops.db import Database; Database('data/content.db').initialize(); print('v6 ok')"`
Expected: `v6 ok`

- [ ] **Step 2: Criar rodada e associar pesquisas existentes**

Run:
```bash
PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -c "
from content_ops.db import Database
db = Database('data/content.db')
db.initialize()
round_id = db.create_round('Liderança e gestão de times', 'runtime/rodadas/2026-08-28.md')
import sqlite3
con = sqlite3.connect('data/content.db')
con.execute('UPDATE research_reports SET round_id = ?, label = ? WHERE path = ?',
    (round_id, '2026_08_28 lideranca-gestao-times cultura-times-alta-perf', 'research/2026-08-27--lideranca-em-times-de-alta-performance.md'))
con.execute('UPDATE research_reports SET round_id = ?, label = ? WHERE path = ?',
    (round_id, '2026_08_28 lideranca-gestao-times problem-solving-mckinsey', 'research/2026-08-27--problem-solving-metodologia-mckinsey.md'))
con.execute('UPDATE research_reports SET round_id = ?, label = ? WHERE path = ?',
    (round_id, '2026_08_28 lideranca-gestao-times linkedin-alta-perf', 'research/2026-08-28--linkedin-lideranca-times-alta-performance.md'))
con.commit()
print('round', round_id)
"
```
Expected: `round <id>`

- [ ] **Step 3: Re-propor pilares e confirmar aprovação preservada**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m content_ops.cli pillars propose`
Expected: `Proposed 2 pillars in docs/pillars.md.` — e `Liderança e gestão de times` segue `approved: true`.

- [ ] **Step 4: Rodar suíte completa**

Run: `PYTHONPATH="$PWD/src" /Users/mac/.pyenv/shims/python3.12 -m pytest tests/ -q`
Expected: `100 passed` (ou o total atual).

- [ ] **Step 5: Commit**

```bash
git add data/content.db docs/pillars.md
git commit -m "chore: migra banco para v6 e registra rodada inicial de liderança"
```

---

## Self-Review

**Cobertura do spec (Fase 1):**
- Indexação por rodada: Tasks 1–4, 8 (`rounds`, `round_id`, `label`, consultas).
- `ideas.sources` multi-pesquisa: Task 5.
- `bloco-ok`: Task 6.
- `publish-complete` (approved→published): Task 7.
- Gates `APPROVAL_*` no `.env`: **não implementado neste plano** — é leitura de config pela skill orquestradora (Plano 2), não código Python. Registrado no spec.
- Skill orquestradora + agentes: **Plano 2** (arquivos de instrução, sem código Python).
- Pesquisa multicanal com peso LinkedIn: **Plano 2** (contrato do executor B4).

**Placeholders:** nenhum — todos os passos têm código completo.

**Consistência de tipos:** `create_research_report` com 5 parâmetros (Task 3) é consumido por `propose_pillars_from_research` (Task 4) e pelo CLI (Task 3 do Plano 1 já existente — `research discover` chama com `pillar=arguments.pillar`, compatível). `list_research_reports` retorna 5 campos — Task 4 ajusta o único consumidor.
