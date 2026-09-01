from pathlib import Path

import yaml


def test_checklist_has_required_verification_steps():
    data = yaml.safe_load(
        Path("docs/schemas/linkedin-scheduling-checklist.yaml").read_text()
    )
    required = {
        "approved_file",
        "content_converted",
        "date_time_confirmed",
        "final_preview_confirmed",
        "scheduled_list_confirmed",
    }
    assert required <= set(data)
