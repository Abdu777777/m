import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ProductionSecretKeySettingsTests(SimpleTestCase):
    def run_settings_import(self, secret_key):
        env = os.environ.copy()
        env["DEBUG"] = "False"
        env.pop("SECRET_KEY", None)
        if secret_key is not None:
            env["SECRET_KEY"] = secret_key
        return subprocess.run(
            [sys.executable, "-c", "import config.settings"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_production_refuses_missing_secret_key(self):
        result = self.run_settings_import(None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Set a strong SECRET_KEY", result.stderr)

    def test_production_refuses_short_secret_key(self):
        result = self.run_settings_import("short-key")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("at least 50 characters", result.stderr)

    def test_production_accepts_long_secret_key(self):
        result = self.run_settings_import("x" * 64)
        self.assertEqual(result.returncode, 0, result.stderr)
