"""Check the test entry point only accepts test labels."""

import subprocess
from pathlib import Path
from unittest import TestCase

SCRIPT = Path(__file__).resolve().parent.parent / "runtests"


class TestTestEntrypoint(TestCase):
    def test_rejects_options_and_non_test_modules(self):
        for argument in (
            "--settings=other",
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
