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
            start_block_cycle(self.database, self.round_id, block, "content/drafts/x.md")
            record_review(self.database, self.round_id, block, "content/drafts/x.md", 1, "revisor", self.result())
            complete_block(self.database, self.round_id, block, "content/drafts/x.md", 1)

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
            start_block_cycle(self.database, self.round_id, block, "content/drafts/x.md")
            record_review(self.database, self.round_id, block, "content/drafts/x.md", 1, "revisor", self.result())
            complete_block(self.database, self.round_id, block, "content/drafts/x.md", 1)
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
            start_block_cycle(other, round_id, block, "other.md")
            record_review(other, round_id, block, "other.md", 1, "revisor", self.result(artifact="other.md"))
            complete_block(other, round_id, block, "other.md", 1)
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


if __name__ == "__main__":
    unittest.main()
