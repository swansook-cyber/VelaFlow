from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ProjectStorageRootTest(unittest.TestCase):
    def _run(self, value: str | None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("VELAFLOW_PROJECT_DATA_ROOT", None)
        if value is not None:
            env["VELAFLOW_PROJECT_DATA_ROOT"] = value
        return subprocess.run(
            [sys.executable, "-c", "from core.paths import PROJECT_DATA_ROOT; print(PROJECT_DATA_ROOT)"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_default_stays_in_checkout(self) -> None:
        result = self._run(None)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), Path(__file__).resolve().parents[1] / "project_data")

    def test_existing_absolute_directory_is_shared(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            result = self._run(str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()), root)

    def test_invalid_path_fails_instead_of_creating_storage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing"
            result = self._run(str(missing))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("VELAFLOW_PROJECT_DATA_ROOT must be an existing absolute directory", result.stderr)
            self.assertFalse(missing.exists())
            relative = self._run("project_data")
            self.assertNotEqual(relative.returncode, 0)


if __name__ == "__main__":
    unittest.main()
