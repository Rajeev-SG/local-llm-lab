import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]

class SecureSetupTests(unittest.TestCase):
    def test_compose_is_pinned_and_volume_is_named(self):
        compose = (ROOT / "compose.openwebui.yaml").read_text()
        self.assertNotRegex(compose, r"open-webui:main|open-webui:latest")
        self.assertIn("/app/backend/data", compose)
        self.assertIn("OPENAI_API_KEYS", compose)
        self.assertIn("WEBUI_SECRET_KEY", compose)
        self.assertIn("open-terminal", compose)
        self.assertNotIn("OPEN_TERMINAL_ALLOWED_DOMAINS", compose)
        self.assertIn("127.0.0.1:", compose)
        self.assertIn(":ro", compose)
        self.assertNotIn("/var/run/docker.sock", compose)

    def test_allowlist_has_no_shell_operation_or_secret(self):
        data = json.loads((ROOT / "config/bridge-allowlist.json").read_text())
        self.assertNotIn("shell", data["operations"])
        self.assertNotIn("OPENROUTER_API_KEY", (ROOT / "config/bridge-allowlist.json").read_text())
        self.assertEqual(sorted(data["runbooks"]), ["docs/openwebui-rollback.md", "docs/openwebui-secure-setup.md"])

    def test_bridge_discovery_is_allowlisted(self):
        result = subprocess.run(["python3", str(ROOT / "scripts/bridge.py"), "discover"], capture_output=True, text=True, check=True)
        self.assertIn("local.complete", result.stdout)
        self.assertNotIn("run-shell", result.stdout)

    def test_cloud_operation_requires_environment_key(self):
        env = {key: value for key, value in os.environ.items() if key != "OPENROUTER_API_KEY"}
        result = subprocess.run(["python3", str(ROOT / "scripts/bridge.py"), "cloud.models"], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("required", result.stderr)

if __name__ == "__main__":
    unittest.main()
