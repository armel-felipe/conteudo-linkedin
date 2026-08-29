import json
import tempfile
import unittest
from pathlib import Path

from content_ops.db import Database
from content_ops.orchestration import (
    InvalidReviewResult,
    ReviewResult,
    WorkflowBlocked,
    can_complete_block,
    parse_review_result,
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

    def test_approved_and_feedback_results_are_structured(self):
        approved = parse_review_result(self.result())
        feedback = parse_review_result(self.result("feedback"))
        self.assertIsInstance(approved, ReviewResult)
        self.assertEqual(approved.decision, "approved")
        self.assertEqual(feedback.decision, "feedback")

    def test_invalid_reviewer_json_is_rejected(self):
        with self.assertRaises(InvalidReviewResult):
            parse_review_result('{"decision":"maybe"}')

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
        with self.assertRaises(WorkflowBlocked):
            can_complete_block(self.database, self.round_id, "B5", "missing.md", 1)
        self.database.start_block_cycle(self.round_id, "B5", "content/drafts/x.md")
        with self.assertRaises(WorkflowBlocked):
            can_complete_block(self.database, self.round_id, "B5", "content/drafts/x.md", 1)

    def test_completion_requires_matching_review_receipt(self):
        cycle_id = self.database.start_block_cycle(
            self.round_id, "B5", "content/drafts/x.md"
        )
        self.database.record_review_result(
            cycle_id, "revisor", "feedback", self.result("feedback")
        )
        with self.assertRaises(WorkflowBlocked):
            can_complete_block(self.database, self.round_id, "B5", "content/drafts/x.md", 1)

    def test_completion_rejects_out_of_order_duplicate_and_b7(self):
        cycle_id = self.database.start_block_cycle(
            self.round_id, "B5", "content/drafts/x.md"
        )
        self.database.record_review_result(cycle_id, "revisor", "approved", self.result())
        with self.assertRaises(WorkflowBlocked):
            can_complete_block(self.database, self.round_id, "B5", "content/drafts/x.md", 1)

        for block in ("B1", "B2", "B3", "B4"):
            self.database.record_workflow_event(self.round_id, block, "block_completed")
        can_complete_block(self.database, self.round_id, "B5", "content/drafts/x.md", 1)
        self.database.record_workflow_event(self.round_id, "B5", "block_completed")
        with self.assertRaises(WorkflowBlocked):
            can_complete_block(self.database, self.round_id, "B5", "content/drafts/x.md", 1)

        b7_id = self.database.start_block_cycle(self.round_id, "B7", "content/drafts/x.md")
        self.database.record_review_result(b7_id, "revisor", "approved", self.result())
        with self.assertRaises(WorkflowBlocked):
            can_complete_block(self.database, self.round_id, "B7", "content/drafts/x.md", 1)


if __name__ == "__main__":
    unittest.main()
