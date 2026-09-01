from pathlib import Path


def test_scheduling_skill_contains_visual_and_reschedule_contract():
    text = Path(".agents/skills/publicar-linkedin/SKILL.md").read_text()
    for phrase in ["Playwright", "image-analyzer", "Alterar agenda", "selecionar novamente", "Publicações agendadas"]:
        assert phrase in text
