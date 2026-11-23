"""Test the shared CI and test entry-point conventions."""

import os
import re
import subprocess
from pathlib import Path
from unittest import TestCase

SCRIPT = Path(__file__).resolve().parent.parent / "runtests"


class CiStandardizationTests(TestCase):
    def test_rejects_options_and_non_test_modules(self):
        for argument in (
            "--settings=other",
            "--testrunner=other.Runner",
            "os.system",
            "tests.test_foo;id",
            "tests.test_basic.BasicTests.setUpClass",
            "tests.test_basic.MinicompressStorage",
        ):
            with self.subTest(argument=argument):
                result = subprocess.run(
                    [str(SCRIPT), argument], capture_output=True, text=True
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unsupported", result.stderr.lower())

    def test_runs_a_selected_test(self):
        result = subprocess.run(
            [str(SCRIPT), "tests.test_basic.BasicTests.test_import_storage"],
            cwd=SCRIPT.parent,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ran 1 test", result.stderr)

    def test_returns_a_failure_for_a_missing_test(self):
        result = subprocess.run(
            [str(SCRIPT), "tests.test_basic.BasicTests.test_missing"],
            cwd=SCRIPT.parent,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("test_missing", result.stderr)

    def test_failure_bot_uses_ci_workflow(self):
        workflows = SCRIPT.parent / ".github" / "workflows"
        ci = (workflows / "ci.yml").read_text()
        bot = (workflows / "bot-ci-failure.yml").read_text()
        name = re.search(r"(?m)^name: (.+)$", ci).group(1)
        self.assertIn(f'workflows: ["{name}"]', bot)
        self.assertIn(
            "github.event.workflow_run.path == '.github/workflows/ci.yml'", bot
        )

    def test_uses_test_settings_despite_caller_environment(self):
        result = subprocess.run(
            [str(SCRIPT), "tests.test_basic.BasicTests.test_import_storage"],
            cwd=SCRIPT.parent,
            env={**os.environ, "DJANGO_SETTINGS_MODULE": "untrusted_settings"},
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ran 1 test", result.stderr)
