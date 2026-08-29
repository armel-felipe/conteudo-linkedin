import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from content_ops.db import Database
from content_ops.orchestration import (
    InvalidReviewResult,
    ReviewResult,
    WorkflowBlocked,
    can_complete_block,
    complete_block,
    parse_review_result,
    record_review,
    record_human_completion,
    start_block_cycle,
    redact_event_payload,
    resume_round,
    validate_block_order,
)


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.database = Database(self.root / "data" / "content.db")
        self.database.initialize()
        self.artifact = self.root / "content" / "drafts" / "x.md"
        self.artifact.parent.mkdir(parents=True)
        self.artifact.write_text("draft", encoding="utf-8")
        self.round_id = self.database.create_round("Pilar", "runtime/rodadas/1.md")

    def tearDown(self):
        self.directory.cleanup()

    def result(self, decision="approved", **overrides):
        value = {
            "decision": decision,
            "artifact": "content/drafts/x.md",
            "feedback": [] if decision == "approved" else ["melhorar"],
            "checks": [{"name": "qualidade", "status": "pass", "evidence": "ok"}],
        }
        value.update(overrides)
        return json.dumps(value)

    def complete_prior_blocks(self, blocks):
        for block in blocks:
            reference = "Pilar escolhido" if block == "B2" else "content/drafts/x.md"
            if block == "B2":
                self.database.replace_pillars([("Pilar escolhido", 1, ("post:1",))])
                self.database.approve_pillar("Pilar escolhido")
            start_block_cycle(self.database, self.round_id, block, reference)
            record_review(
                self.database, self.round_id, block, reference, 1, "revisor",
                self.result(artifact=reference),
            )
            complete_block(self.database, self.round_id, block, reference, 1)

    def test_approved_and_feedback_results_are_structured(self):
        approved = parse_review_result(self.result())
        feedback = parse_review_result(self.result("feedback"))
        self.assertIsInstance(approved, ReviewResult)
        self.assertEqual(approved.decision, "approved")
        self.assertEqual(feedback.decision, "feedback")

    def test_invalid_reviewer_json_is_rejected(self):
        with self.assertRaises(InvalidReviewResult):
            parse_review_result('{"decision":"maybe"}')
        with self.assertRaises(InvalidReviewResult):
            parse_review_result("not-json")

    def test_review_result_requires_checks_and_feedback_list(self):
        with self.assertRaises(InvalidReviewResult):
            parse_review_result(self.result(checks=[]))
        with self.assertRaises(InvalidReviewResult):
            parse_review_result(self.result(feedback="not-a-list"))
        with self.assertRaises(InvalidReviewResult):
            parse_review_result(self.result(checks=[{"name": "x"}]))

    def test_block_order_rejects_skips_and_duplicates(self):
        with self.assertRaises(WorkflowBlocked):
            validate_block_order({"B1"}, "B3")
        with self.assertRaises(WorkflowBlocked):
            validate_block_order({"B1", "B2"}, "B2")
        validate_block_order({"B1", "B2"}, "B3")

    def test_completion_requires_existing_artifact_and_approved_receipt(self):
        self.complete_prior_blocks(("B1", "B2", "B3", "B4"))
        with self.assertRaises(WorkflowBlocked):
            can_complete_block(self.database, self.round_id, "B5", "missing.md", 1)
        self.database.start_block_cycle(self.round_id, "B5", "content/drafts/x.md")
        with self.assertRaises(WorkflowBlocked):
            can_complete_block(self.database, self.round_id, "B5", "content/drafts/x.md", 1)

    def test_completion_requires_matching_review_receipt(self):
        self.complete_prior_blocks(("B1", "B2", "B3", "B4"))
        cycle_id = self.database.start_block_cycle(
            self.round_id, "B5", "content/drafts/x.md"
        )
        self.database.record_review_result(
            cycle_id, "revisor", "feedback", self.result("feedback")
        )
        with self.assertRaises(WorkflowBlocked):
            can_complete_block(self.database, self.round_id, "B5", "content/drafts/x.md", 1)

    def test_completion_rejects_out_of_order_duplicate_and_b7(self):
        self.complete_prior_blocks(("B1", "B2", "B3", "B4"))
        cycle_id = self.database.start_block_cycle(
            self.round_id, "B5", "content/drafts/x.md"
        )
        self.database.record_review_result(cycle_id, "revisor", "approved", self.result())
        can_complete_block(self.database, self.round_id, "B5", "content/drafts/x.md", 1)

        complete_block(self.database, self.round_id, "B5", "content/drafts/x.md", 1)
        with self.assertRaises(WorkflowBlocked):
            can_complete_block(self.database, self.round_id, "B5", "content/drafts/x.md", 1)

        self.complete_prior_blocks(("B6",))
        b7_id = self.database.start_block_cycle(self.round_id, "B7", "content/drafts/x.md")
        with self.assertRaises(WorkflowBlocked):
            self.database.record_review_result(b7_id, "revisor", "approved", self.result())
        with self.assertRaises(WorkflowBlocked):
            can_complete_block(self.database, self.round_id, "B7", "content/drafts/x.md", 1)

    def test_completion_api_checks_and_records_once(self):
        for block in ("B1", "B2", "B3", "B4"):
            reference = "Pilar escolhido" if block == "B2" else "content/drafts/x.md"
            if block == "B2":
                self.database.replace_pillars([("Pilar escolhido", 1, ("post:1",))])
                self.database.approve_pillar("Pilar escolhido")
            start_block_cycle(self.database, self.round_id, block, reference)
            record_review(self.database, self.round_id, block, reference, 1, "revisor", self.result(artifact=reference))
            complete_block(self.database, self.round_id, block, reference, 1)
        start_block_cycle(self.database, self.round_id, "B5", "content/drafts/x.md")
        record_review(self.database, self.round_id, "B5", "content/drafts/x.md", 1, "revisor", self.result())
        complete_block(self.database, self.round_id, "B5", "content/drafts/x.md", 1)
        with self.assertRaises(WorkflowBlocked):
            complete_block(self.database, self.round_id, "B5", "content/drafts/x.md", 1)

    def test_cycle_start_validates_and_limits_three_cycles(self):
        self.complete_prior_blocks(("B1", "B2", "B3", "B4"))
        with patch.dict(os.environ, {"ORCHESTRATOR_MAX_REVIEW_CYCLES": "3"}):
            for cycle in range(1, 4):
                start_block_cycle(self.database, self.round_id, "B5", "content/drafts/x.md")
            with self.assertRaises(WorkflowBlocked):
                start_block_cycle(self.database, self.round_id, "B5", "content/drafts/x.md")
        with self.assertRaises(WorkflowBlocked):
            start_block_cycle(self.database, self.round_id, "NOPE", "content/drafts/x.md")
        with self.assertRaises(WorkflowBlocked):
            start_block_cycle(self.database, self.round_id, "B6", "missing.md")

    def test_cycle_start_allows_future_artifact_only_for_early_blocks(self):
        for block in ("B1", "B2", "B3"):
            artifact = "Pilar escolhido" if block == "B2" else f"future/{block}.md"
            if block == "B2":
                self.database.replace_pillars([("Pilar escolhido", 1, ("post:1",))])
                self.database.approve_pillar("Pilar escolhido")
            cycle = start_block_cycle(self.database, self.round_id, block, artifact)
            self.assertEqual(cycle, 1)
            if block != "B2":
                path = self.root / artifact
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("artifact", encoding="utf-8")
            result = self.result(artifact=artifact)
            result = json.loads(result)
            record_review(self.database, self.round_id, block, artifact, cycle, "revisor", json.dumps(result))
            complete_block(self.database, self.round_id, block, artifact, cycle)
        with self.assertRaises(WorkflowBlocked):
            start_block_cycle(self.database, self.round_id, "B4", "future/B4.md")

    def test_future_artifact_is_still_required_before_review_and_completion(self):
        start_block_cycle(self.database, self.round_id, "B1", "future/B1.md")
        with self.assertRaises(WorkflowBlocked):
            record_review(self.database, self.round_id, "B1", "future/B1.md", 1, "revisor", self.result())
        with self.assertRaises(WorkflowBlocked):
            can_complete_block(self.database, self.round_id, "B1", "future/B1.md", 1)

    def test_invalid_cycle_limit_configuration_fails_closed(self):
        with patch.dict(os.environ, {"ORCHESTRATOR_MAX_REVIEW_CYCLES": "invalid"}):
            with self.assertRaises(WorkflowBlocked):
                start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")

    def test_cycle_start_rejects_unknown_round_closed_round_and_invalid_order(self):
        with self.assertRaises(WorkflowBlocked):
            start_block_cycle(self.database, 999, "B1", "content/drafts/x.md")
        with self.assertRaises(WorkflowBlocked):
            start_block_cycle(self.database, self.round_id, "B3", "content/drafts/x.md")
        self.complete_prior_blocks(
            ("B1", "B2", "B3", "B4", "B5", "B6")
        )
        start_block_cycle(self.database, self.round_id, "B7", "content/drafts/x.md")
        record_human_completion(self.database, self.round_id, "B7", "content/drafts/x.md", "idea-1")
        self.complete_prior_blocks(("B8", "B10", "B9", "B11"))
        self.database.close_round(self.round_id)
        with self.assertRaises(WorkflowBlocked):
            start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")

    def test_cycle_start_rejects_block_already_completed(self):
        self.complete_prior_blocks(("B1",))
        with self.assertRaises(WorkflowBlocked):
            start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")

    def test_repeated_review_result_is_blocked_across_cycles(self):
        self.complete_prior_blocks(("B1", "B2", "B3", "B4"))
        start_block_cycle(self.database, self.round_id, "B5", "content/drafts/x.md")
        record_review(self.database, self.round_id, "B5", "content/drafts/x.md", 1, "revisor", self.result("feedback"))
        start_block_cycle(self.database, self.round_id, "B5", "content/drafts/x.md")
        with self.assertRaises(WorkflowBlocked):
            record_review(self.database, self.round_id, "B5", "content/drafts/x.md", 2, "revisor", self.result("feedback"))

    def test_review_rejects_closed_round_and_invalid_order(self):
        self.complete_prior_blocks(("B1", "B2", "B3", "B4", "B5", "B6"))
        start_block_cycle(self.database, self.round_id, "B7", "content/drafts/x.md")
        record_human_completion(self.database, self.round_id, "B7", "content/drafts/x.md", "idea-1")
        self.complete_prior_blocks(("B8", "B10", "B9", "B11"))
        self.database.close_round(self.round_id)
        with self.assertRaises(WorkflowBlocked):
            record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 1, "revisor", self.result())

        other = Database(self.root / "data" / "other.db")
        other.initialize()
        round_id = other.create_round("Pilar", "round.md")
        (self.root / "other.md").write_text("draft", encoding="utf-8")
        for block in ("B1", "B2"):
            reference = "Outro pilar" if block == "B2" else "other.md"
            if block == "B2":
                other.replace_pillars([("Outro pilar", 1, ("post:1",))])
                other.approve_pillar("Outro pilar")
            start_block_cycle(other, round_id, block, reference)
            record_review(other, round_id, block, reference, 1, "revisor", self.result(artifact=reference))
            complete_block(other, round_id, block, reference, 1)
        other.start_block_cycle(round_id, "B3", "other.md")
        with self.assertRaises(WorkflowBlocked):
            record_review(other, round_id, "B3", "other.md", 1, "revisor", self.result())

    def test_b7_human_completion_is_persisted_without_reviewer_approval(self):
        self.complete_prior_blocks(("B1", "B2", "B3", "B4", "B5", "B6"))
        start_block_cycle(self.database, self.round_id, "B7", "content/drafts/x.md")
        event_id = record_human_completion(self.database, self.round_id, "B7", "content/drafts/x.md", "idea-1")
        self.assertIsInstance(event_id, int)
        state = self.database.latest_block_state(self.round_id, "B7")
        self.assertEqual(state["event"], "human_completed")
        self.assertEqual(json.loads(state["payload_json"]), {
            "artifact": "content/drafts/x.md", "cycle": 1, "selection": "idea-1"
        })

        start_block_cycle(self.database, self.round_id, "B8", "content/drafts/x.md")

    def test_human_completion_requires_matching_b7_cycle(self):
        self.complete_prior_blocks(("B1", "B2", "B3", "B4", "B5", "B6"))
        with self.assertRaises(WorkflowBlocked):
            record_human_completion(self.database, self.round_id, "B7", "content/drafts/x.md", "idea-1")
        start_block_cycle(self.database, self.round_id, "B7", "content/drafts/x.md")
        with self.assertRaises(WorkflowBlocked):
            record_human_completion(self.database, self.round_id, "B7", "other.md", "idea-1")

    def test_public_review_and_event_apis_reject_invalid_workflow_state(self):
        with self.assertRaises(InvalidReviewResult):
            record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 1, "r", "not-json")
        with self.assertRaises(ValueError):
            self.database.record_workflow_event(
                self.round_id, "B1", "block_completed", '{"cycle": 1}'
            )
        with self.assertRaises(ValueError):
            self.database.record_workflow_event(
                self.round_id, "B7", "human_completed", '{"selection": "idea-1"}'
            )
        with self.assertRaises(ValueError):
            self.database.record_block_validation("B1", "content/drafts/x.md")

    def test_redact_event_payload_removes_secret_shaped_values_recursively(self):
        payload = {
            "OPENAI_API_KEY": "key",
            "nested": {"session_TOKEN": "token", "PASSWORD": "password"},
            "headers": [{"AUTH_TOKEN": "auth", "CT0": "ct0", "safe": "ok"}],
        }

        redacted = redact_event_payload(payload)

        self.assertEqual(redacted["OPENAI_API_KEY"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["session_TOKEN"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["PASSWORD"], "[REDACTED]")
        self.assertEqual(redacted["headers"][0]["AUTH_TOKEN"], "[REDACTED]")
        self.assertEqual(redacted["headers"][0]["CT0"], "[REDACTED]")
        self.assertEqual(redacted["headers"][0]["safe"], "ok")
        self.assertEqual(payload["OPENAI_API_KEY"], "key")

    def test_resume_after_cycle_start_returns_review_state(self):
        start_block_cycle(self.database, self.round_id, "B1", "future/B1.md")

        self.assertEqual(resume_round(self.database, self.round_id), "review:B1")

    def test_resume_after_feedback_returns_next_cycle_and_rejects_unchanged_feedback(self):
        artifact = self.root / "content" / "drafts" / "x.md"
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        feedback = self.result("feedback")
        record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 1, "revisor", feedback)

        self.assertEqual(resume_round(self.database, self.round_id), "start:B1:2")
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        with self.assertRaises(WorkflowBlocked):
            record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 2, "revisor", feedback)

    def test_resume_after_approval_requires_completion_and_duplicate_completion_is_blocked(self):
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 1, "revisor", self.result())

        self.assertEqual(resume_round(self.database, self.round_id), "complete:B1")
        complete_block(self.database, self.round_id, "B1", "content/drafts/x.md", 1)
        self.assertEqual(resume_round(self.database, self.round_id), "start:B2")
        with self.assertRaises(WorkflowBlocked):
            complete_block(self.database, self.round_id, "B1", "content/drafts/x.md", 1)

    def test_approved_cycle_rejects_any_later_review_and_stays_complete(self):
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 1, "revisor", self.result())

        with self.assertRaises(WorkflowBlocked):
            record_review(
                self.database, self.round_id, "B1", "content/drafts/x.md", 1,
                "revisor-2", self.result("feedback"),
            )

        self.assertEqual(resume_round(self.database, self.round_id), "complete:B1")

    def test_resume_records_timeout_as_failed_and_never_advances(self):
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        self.database.record_workflow_failure(self.round_id, "B1", "timeout", {"PASSWORD": "secret"})

        self.assertEqual(resume_round(self.database, self.round_id), "blocked")
        state = self.database.latest_block_state(self.round_id, "B1")
        self.assertEqual(state["event"], "failed")
        self.assertNotIn("secret", state["payload_json"])

    def test_resume_keeps_b7_human_only(self):
        self.complete_prior_blocks(("B1", "B2", "B3", "B4", "B5", "B6"))
        start_block_cycle(self.database, self.round_id, "B7", "content/drafts/x.md")

        self.assertEqual(resume_round(self.database, self.round_id), "human:B7")

    def test_resume_invalid_round_is_blocked(self):
        with self.assertRaises(WorkflowBlocked):
            resume_round(self.database, 999)

    def test_old_cycle_cannot_be_reviewed_or_completed_after_new_cycle_starts(self):
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 1, "revisor", self.result())
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")

        with self.assertRaises(WorkflowBlocked):
            record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 1, "revisor", self.result())
        with self.assertRaises(WorkflowBlocked):
            complete_block(self.database, self.round_id, "B1", "content/drafts/x.md", 1)

    def test_invalid_review_persists_sanitized_failure_before_raising(self):
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")

        with self.assertRaises(InvalidReviewResult):
            record_review(
                self.database, self.round_id, "B1", "content/drafts/x.md", 1,
                "revisor", '{"PASSWORD":"do-not-store"',
            )

        state = self.database.latest_block_state(self.round_id, "B1")
        self.assertEqual(state["event"], "failed")
        self.assertNotIn("do-not-store", state["payload_json"])

    def test_feedback_can_be_followed_by_changed_approval(self):
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 1, "revisor", self.result("feedback"))
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 2, "revisor", self.result())

        self.assertEqual(resume_round(self.database, self.round_id), "complete:B1")

    def test_resume_blocks_after_review_cycle_limit(self):
        with patch.dict(os.environ, {"ORCHESTRATOR_MAX_REVIEW_CYCLES": "1"}):
            start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
            record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 1, "revisor", self.result("feedback"))
            self.assertEqual(resume_round(self.database, self.round_id), "blocked")
        self.assertEqual(self.database.latest_block_state(self.round_id, "B1")["event"], "blocked")

    def test_redaction_removes_secret_patterns_inside_strings(self):
        redacted = redact_event_payload({
            "message": "token=abc api_key = xyz password=last-secret",
            "nested": ["TOKEN=inner", {"safe": "api-key=another"}],
        })

        serialized = json.dumps(redacted)
        for secret in ("abc", "xyz", "last-secret", "inner", "another"):
            self.assertNotIn(secret, serialized)

    def test_secret_artifact_is_blocked_before_review_and_completion(self):
        self.artifact.write_text("API_KEY=leak\nconteudo", encoding="utf-8")
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")

        with self.assertRaises(WorkflowBlocked):
            record_review(
                self.database, self.round_id, "B1", "content/drafts/x.md", 1,
                "revisor", self.result(),
            )
        with self.assertRaises(WorkflowBlocked):
            complete_block(self.database, self.round_id, "B1", "content/drafts/x.md", 1)
        self.assertEqual(self.database.latest_block_state(self.round_id, "B1")["event"], "blocked")

    def test_b2_selection_completes_without_a_file(self):
        self.database.replace_pillars([("IA aplicada", 1, ("post:1",))])
        self.database.approve_pillar("IA aplicada")
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 1, "r", self.result())
        complete_block(self.database, self.round_id, "B1", "content/drafts/x.md", 1)

        start_block_cycle(self.database, self.round_id, "B2", "IA aplicada")
        result = self.result(artifact="IA aplicada")
        record_review(self.database, self.round_id, "B2", "IA aplicada", 1, "r", result)
        complete_block(self.database, self.round_id, "B2", "IA aplicada", 1)
        self.assertEqual(resume_round(self.database, self.round_id), "start:B3")

    def test_b2_approved_pillar_names_may_contain_path_separators(self):
        self.database.replace_pillars([
            ("Dados/Python", 1, ("post:1",)),
            (r"IA\aplicada", 1, ("post:2",)),
        ])
        self.database.approve_pillar("Dados/Python")
        self.database.approve_pillar(r"IA\aplicada")
        for pillar in ("Dados/Python", r"IA\aplicada"):
            round_id = self.database.create_round(pillar, "round.md")
            start_block_cycle(self.database, round_id, "B1", "content/drafts/x.md")
            record_review(self.database, round_id, "B1", "content/drafts/x.md", 1, "r", self.result())
            complete_block(self.database, round_id, "B1", "content/drafts/x.md", 1)
            start_block_cycle(self.database, round_id, "B2", pillar)
            record_review(
                self.database, round_id, "B2", pillar, 1, "r",
                self.result(artifact=pillar),
            )
            complete_block(self.database, round_id, "B2", pillar, 1)

    def test_old_cycle_is_stale_even_when_new_cycle_has_a_different_artifact(self):
        other = self.root / "content" / "drafts" / "y.md"
        other.write_text("draft 2", encoding="utf-8")
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 1, "r", self.result("feedback"))
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/y.md")

        with self.assertRaises(WorkflowBlocked):
            record_review(self.database, self.round_id, "B1", "content/drafts/x.md", 1, "r", self.result())

    def test_divergent_review_persists_blocked_state_and_resume_does_not_retry(self):
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        with self.assertRaises(WorkflowBlocked):
            record_review(
                self.database, self.round_id, "B1", "content/drafts/x.md", 1,
                "r", self.result(artifact="content/drafts/other.md"),
            )
        self.assertEqual(self.database.latest_block_state(self.round_id, "B1")["event"], "blocked")
        self.assertEqual(resume_round(self.database, self.round_id), "blocked")

    def test_missing_artifact_persists_blocked_state(self):
        start_block_cycle(self.database, self.round_id, "B1", "future/missing.md")
        with self.assertRaises(WorkflowBlocked):
            record_review(
                self.database, self.round_id, "B1", "future/missing.md", 1,
                "r", self.result(artifact="future/missing.md"),
            )
        self.assertEqual(self.database.latest_block_state(self.round_id, "B1")["event"], "blocked")
        self.assertEqual(resume_round(self.database, self.round_id), "blocked")

    def test_unreadable_artifact_during_review_persists_generic_blocked_state(self):
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        with patch("pathlib.Path.read_text", side_effect=OSError("private artifact bytes")):
            with self.assertRaises(WorkflowBlocked):
                record_review(
                    self.database, self.round_id, "B1", "content/drafts/x.md", 1,
                    "revisor", self.result(),
                )

        state = self.database.latest_block_state(self.round_id, "B1")
        self.assertEqual(state["event"], "blocked")
        self.assertNotIn("private artifact bytes", state["payload_json"])
        self.assertEqual(resume_round(self.database, self.round_id), "blocked")

    def test_undecodable_artifact_during_completion_persists_generic_blocked_state(self):
        start_block_cycle(self.database, self.round_id, "B1", "content/drafts/x.md")
        with patch("pathlib.Path.read_text", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "private bytes")):
            with self.assertRaises(WorkflowBlocked):
                complete_block(self.database, self.round_id, "B1", "content/drafts/x.md", 1)

        state = self.database.latest_block_state(self.round_id, "B1")
        self.assertEqual(state["event"], "blocked")
        self.assertNotIn("private bytes", state["payload_json"])
        self.assertEqual(resume_round(self.database, self.round_id), "blocked")

    def test_workflow_event_api_allows_only_valid_cycle_or_review_events(self):
        start_block_cycle(self.database, self.round_id, "B1", "future/B1.md")
        event_id = self.database.record_workflow_event(
            self.round_id, "B1", "cycle_started",
            '{"cycle":1,"artifact":"future/B1.md"}',
        )
        self.assertIsInstance(event_id, int)
        with self.assertRaisesRegex(ValueError, "workflow-block-complete"):
            self.database.record_workflow_event(self.round_id, "B1", "block_completed")

    def test_failure_logs_redact_all_secret_patterns(self):
        event_id = self.database.record_workflow_failure(
            self.round_id, "B1", "executor log API_KEY=one TOKEN=two CT0=three AUTH_TOKEN=four PASSWORD=five",
        )
        self.assertIsInstance(event_id, int)
        payload = self.database.latest_block_state(self.round_id, "B1")["payload_json"]
        for secret in ("one", "two", "three", "four", "five"):
            self.assertNotIn(secret, payload)


if __name__ == "__main__":
    unittest.main()
