"""Keep the CI failure bot aligned with the workflow it monitors."""

import re
from pathlib import Path
from unittest import TestCase


class CiFailureWorkflowTests(TestCase):
    def test_failure_bot_matches_ci_workflow_name(self):
        workflows = Path(__file__).resolve().parent.parent / ".github" / "workflows"
        ci = (workflows / "ci.yml").read_text()
        bot = (workflows / "bot-ci-failure.yml").read_text()
        name = re.search(r"(?m)^name: (.+)$", ci).group(1)
        self.assertIn(f'workflows: ["{name}"]', bot)
        self.assertIn(f"github.event.workflow_run.name == '{name}'", bot)
