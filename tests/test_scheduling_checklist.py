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
        "browser_attempted",
        "route_attempted",
    }
    assert required <= set(data)


def test_checklist_registration_gate_has_explicit_types_and_failure_state():
    data = yaml.safe_load(
        Path("docs/schemas/linkedin-scheduling-checklist.yaml").read_text()
    )
    assert isinstance(data["scheduled_list_confirmed"], bool)
    assert isinstance(data["timestamp_registered"], bool)
    assert data["failure_state"] is None
    assert isinstance(data["requested_timestamp"], str)
    assert isinstance(data["displayed_timestamp"], str)
    # Após um agendamento real confirmado, o timestamp pode estar registrado.
    # Quando registrado, hora solicitada e exibida devem coincidir; quando não,
    # ambas devem estar vazias.
    if data["timestamp_registered"]:
        assert data["requested_timestamp"] != ""
        assert data["requested_timestamp"] == data["displayed_timestamp"]
    else:
        assert data["requested_timestamp"] == ""
        assert data["displayed_timestamp"] == ""
