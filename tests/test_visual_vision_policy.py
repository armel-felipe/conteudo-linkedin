from pathlib import Path


SKILL_PATH = Path(".agents/skills/visao-nativa-primeiro/SKILL.md")


def read_policy() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_native_vision_is_before_image_analyzer_fallback():
    text = read_policy()

    assert text.index("visão nativa") < text.index("image-analyzer")
    assert "falhar" in text.lower()
    assert "não invent" in text.lower()


def test_policy_defines_ordered_routes_and_unreadable_image_handling():
    text = read_policy().lower()

    assert text.index("visão nativa") < text.index("sem visão")
    assert text.index("sem visão") < text.index("falha da visão nativa")
    assert "native" in text
    assert "image-analyzer" in text
    assert "ilegível" in text or "corrompida" in text
    assert "limitação" in text
    assert "conteúdo inferido" in text or "conteúdo não" in text


def test_policy_requires_secret_free_internal_route_logging():
    text = read_policy().lower()

    assert "rota" in text
    assert "não armazen" in text or "não registrar" in text
    assert "imagem" in text
    assert "segredo" in text or "credencial" in text or "token" in text
