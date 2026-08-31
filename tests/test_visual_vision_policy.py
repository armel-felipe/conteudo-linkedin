from pathlib import Path
import re


SKILL_PATH = Path(".agents/skills/visao-nativa-primeiro/SKILL.md")
LINKEDIN_SKILL_PATH = Path(".agents/skills/publicar-linkedin/SKILL.md")


def visual_instruction_files() -> list[Path]:
    paths = list(Path(".agents/skills").glob("**/SKILL.md"))
    paths.extend(Path("docs/superpowers").glob("**/*.md"))
    markers = re.compile(
        r"image-analyzer|screenshot|vis[aã]o nativa|anexo.{0,30}imagem",
        flags=re.IGNORECASE,
    )
    return [
        path
        for path in paths
        if path != SKILL_PATH
        and markers.search(path.read_text(encoding="utf-8"))
    ]


def read_policy() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_every_visual_instruction_references_central_policy():
    files = visual_instruction_files()

    assert files, "expected project visual instruction files"
    missing = [str(path) for path in files if "visao-nativa-primeiro" not in path.read_text(encoding="utf-8")]

    assert not missing, f"visual instructions missing central policy reference: {missing}"


def test_linkedin_skill_does_not_delegate_before_native_analysis():
    text = LINKEDIN_SKILL_PATH.read_text(encoding="utf-8")
    start = text.index("## Visão")
    end = text.index("## Credenciais", start)
    vision = text[start:end]

    assert "visao-nativa-primeiro" in vision
    assert "Se o modelo hospedeiro não ler imagens, delegar" not in vision


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^### {re.escape(heading)}\n(?P<body>.*?)(?=^### |^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"missing section: {heading}"
    return match.group("body")


def test_native_model_has_exclusive_native_route():
    native = section(read_policy(), "Modelo com visão nativa")

    assert "Rota obrigatória: `native`." in native
    assert "image-analyzer" not in native


def test_protocol_orders_native_before_conditional_fallbacks():
    text = read_policy()

    assert text.index("### Modelo com visão nativa") < text.index("### Modelo sem visão nativa")
    assert text.index("### Modelo sem visão nativa") < text.index("### Falha da visão nativa")


def test_no_vision_model_has_image_analyzer_route():
    no_vision = section(read_policy(), "Modelo sem visão nativa")

    assert "Rota obrigatória: `image-analyzer`." in no_vision
    assert "não tente visão nativa" in no_vision


def test_native_failure_falls_back_and_fallback_failure_reports_limitation():
    native_failure = section(read_policy(), "Falha da visão nativa")
    fallback_failure = section(read_policy(), "Falha do image-analyzer").lower()

    assert "Rota obrigatória: `image-analyzer`." in native_failure
    assert "Motivo: `native_failed`." in native_failure
    assert "rota obrigatória: nenhuma." in fallback_failure
    assert "responda com uma limitação de leitura" in fallback_failure
    assert "não produza inferência" in fallback_failure


def test_unreadable_or_corrupt_image_never_produces_inference():
    unreadable = section(read_policy(), "Imagem ilegível ou corrompida").lower()

    assert "rota obrigatória: nenhuma." in unreadable
    assert "responda com uma limitação de leitura" in unreadable
    assert "não produza inferência" in unreadable


def test_metadata_allowlist_excludes_image_content_and_secrets():
    text = read_policy()
    allowed = section(text, "Campos permitidos nos metadados")
    forbidden = section(text, "Campos proibidos nos metadados")
    prohibited_values = (
        "conteúdo da imagem",
        "urls privadas",
        "credenciais",
        "tokens",
        "chaves de api",
        "qualquer outro segredo",
    )

    assert "`route`" in allowed
    assert "`reason`" in allowed
    assert "estado resumido" in allowed
    for value in prohibited_values:
        assert value not in allowed.lower()
        assert value in forbidden.lower()
