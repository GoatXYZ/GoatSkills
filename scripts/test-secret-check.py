#!/usr/bin/env python3
"""Exercise the secret-check wrapper and its narrow conformance-key exception."""

import base64
import json
import secrets
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


class SecretCheckTest(unittest.TestCase):
    def test_worktree_exception_and_deleted_history(self):
        with tempfile.TemporaryDirectory(prefix="goatskills-check-") as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "pls/scripts").mkdir(parents=True)
            for name in ("scripts/check-secrets", ".gitleaks.toml"):
                shutil.copy2(REPO / name, root / name)

            def git(*args):
                result = subprocess.run(
                    ["git", *args], cwd=root, capture_output=True, text=True,
                    timeout=20,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            def check(expected):
                result = subprocess.run(
                    [str(root / "scripts/check-secrets")], cwd=root.parent,
                    capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, expected, result.stderr)
                return result

            git("init", "-q")
            git("config", "user.name", "Secret-check fixture")
            git("config", "user.email", "fixture@example.com")
            (root / "README.md").write_text("Clean fixture\n")
            git("add", "README.md")
            git("commit", "-qm", "Clean fixture")

            keyfile = root / "pls/scripts/noise_sig.py"
            vector = base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
            keyfile.write_text("_VECTOR_KEY = " + json.dumps(vector) + "\n")
            check(0)

            other = root / "different.py"
            other.write_text(keyfile.read_text())
            check(1)
            other.unlink()

            keyfile.write_text(
                "_VECTOR_KEY = " + json.dumps(secrets.token_urlsafe(32)) + "\n"
            )
            check(1)

            git("add", "pls/scripts/noise_sig.py")
            git("commit", "-qm", "Synthetic credential fixture")
            git("rm", "-q", "pls/scripts/noise_sig.py")
            git("commit", "-qm", "Remove synthetic fixture")
            result = check(1)
            self.assertIn("commits scanned", result.stderr)


if __name__ == "__main__":
    unittest.main()
