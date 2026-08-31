# Política de visão nativa antes do fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Garantir que todas as tarefas visuais tentem a visão nativa do modelo hospedeiro antes de delegar ao `image-analyzer`.

**Architecture:** Uma skill central define o protocolo de decisão e a ordem native→fallback. Skills visuais do projeto referenciam esse protocolo; o runtime OpenCode decide se o modelo tem visão, sem detecção artificial ou alteração de configuração de modelo.

**Tech Stack:** Markdown, skills OpenCode, testes estruturais em Python/pytest.

## Global Constraints

- A política vale para todas as skills e tarefas visuais do projeto, não apenas para `publicar-linkedin`.
- Modelo com visão deve analisar diretamente e não chamar `image-analyzer` antes da tentativa nativa.
- Modelo sem visão delega ao `image-analyzer`.
- Falha técnica da visão nativa aciona `image-analyzer` como fallback.
- Imagem ilegível/corrompida não pode gerar conteúdo inventado.
- O runtime OpenCode é a fonte da decisão sobre a capacidade nativa disponível.
- Logs de rota não podem conter dados privados da imagem, credenciais ou tokens.

---

## Mapa de arquivos

- Create: `.agents/skills/visao-nativa-primeiro/SKILL.md` — protocolo central reutilizável.
- Modify: `.agents/skills/publicar-linkedin/SKILL.md` — referência à política e remoção de ordem conflitante.
- Modify: `docs/superpowers/plans/2026-08-26-skill-publicacao-linkedin.md` — alinhamento da documentação.
- Modify: `docs/superpowers/specs/2026-08-26-skill-publicacao-linkedin-design.md` — alinhamento da especificação.
- Create: `tests/test_visual_vision_policy.py` — testes estruturais do contrato.

### Task 1: Criar a política central de visão

**Files:**
- Create: `.agents/skills/visao-nativa-primeiro/SKILL.md`
- Test: `tests/test_visual_vision_policy.py`

**Interfaces:**
- Produces the shared protocol text consumed by all visual skills.
- Defines route labels `native` and `image-analyzer` and fallback reasons.

- [ ] **Step 1: Write failing structural tests**

Create tests that read the central skill and assert the ordered rules: native attempt first, no-vision delegation, native-failure fallback, unreadable-image handling, no fabrication, route labels, and secret-free logging.

```python
def test_native_vision_is_before_image_analyzer_fallback():
    text = Path(".agents/skills/visao-nativa-primeiro/SKILL.md").read_text()
    assert text.index("visão nativa") < text.index("image-analyzer")
    assert "falhar" in text
    assert "não invent" in text.lower()
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python3.12 -m pytest tests/test_visual_vision_policy.py -v`

Expected: FAIL because the shared skill does not exist.

- [ ] **Step 3: Write the minimal central skill**

Add frontmatter and a protocol that explicitly distinguishes `native`, `image-analyzer` for no-vision models, and fallback after native failure. State that unreadable/corrupt images produce a limitation message and no inferred content. Define internal route metadata without storing image contents or secrets.

- [ ] **Step 4: Run the focused test**

Run: `python3.12 -m pytest tests/test_visual_vision_policy.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/visao-nativa-primeiro/SKILL.md tests/test_visual_vision_policy.py
git commit -m "feat: define native vision fallback policy"
```

### Task 2: Integrar todas as skills e documentos visuais

**Files:**
- Modify: `.agents/skills/publicar-linkedin/SKILL.md`
- Modify: `docs/superpowers/plans/2026-08-26-skill-publicacao-linkedin.md`
- Modify: `docs/superpowers/specs/2026-08-26-skill-publicacao-linkedin-design.md`
- Test: `tests/test_visual_vision_policy.py`

**Interfaces:**
- Consumes `.agents/skills/visao-nativa-primeiro/SKILL.md`.
- Produces references from every project visual skill/document to the central policy.

- [ ] **Step 1: Add failing integration assertions**

Extend the test to find project skill files containing visual-task instructions and assert each references `visao-nativa-primeiro`. Assert `publicar-linkedin` no longer instructs unconditional delegation before native analysis.

- [ ] **Step 2: Run the test and verify it fails**

Run: `python3.12 -m pytest tests/test_visual_vision_policy.py -v`

Expected: FAIL because the existing LinkedIn skill and documents still describe unconditional delegation.

- [ ] **Step 3: Update the LinkedIn skill**

Replace the current vision section with a reference to the central protocol. Keep the existing screenshot/navigation responsibilities, but state: analyze natively first when supported; delegate only for no-vision or native failure; report limitations when neither route works.

- [ ] **Step 4: Update design and plan documents**

Replace wording that says to delegate vision unconditionally with the native-first policy reference and the exact fallback conditions. Do not modify publication pause or image-attachment behavior.

- [ ] **Step 5: Run the integration tests**

Run: `python3.12 -m pytest tests/test_visual_vision_policy.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/publicar-linkedin/SKILL.md docs/superpowers/plans/2026-08-26-skill-publicacao-linkedin.md docs/superpowers/specs/2026-08-26-skill-publicacao-linkedin-design.md tests/test_visual_vision_policy.py
git commit -m "docs: apply native vision policy to visual skills"
```

### Task 3: Cobertura de falhas, rastreabilidade e suíte final

**Files:**
- Modify: `.agents/skills/visao-nativa-primeiro/SKILL.md`
- Modify: `tests/test_visual_vision_policy.py`

**Interfaces:**
- Produces an acceptance matrix for native success, no vision, native failure, fallback failure, unreadable image, and secret-free route records.

- [ ] **Step 1: Add failing acceptance checks**

Assert the central skill contains explicit handling for all five failure/success routes and forbids persisting image contents, credentials, and tokens in route metadata.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `python3.12 -m pytest tests/test_visual_vision_policy.py -v`

Expected: FAIL for any missing acceptance wording.

- [ ] **Step 3: Complete the policy text**

Document the exact user-facing behavior for native success, no-vision delegation, native failure fallback, fallback failure, and unreadable/corrupt input. Keep route metadata limited to route, fallback reason, delegation mode, and readability limitation.

- [ ] **Step 4: Run focused and full suites**

Run: `python3.12 -m pytest tests/test_visual_vision_policy.py -v` and `python3.12 -m pytest -q`.

Expected: focused tests and the full existing suite pass.

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/visao-nativa-primeiro/SKILL.md tests/test_visual_vision_policy.py
git commit -m "test: cover native vision fallback routes"
```

## Final verification

Run:

```bash
python3.12 -m pytest -q
git diff --check
```

Completion requires all tests to pass and every visual skill in the repository to reference the central native-first policy.
