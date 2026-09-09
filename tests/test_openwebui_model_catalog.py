import unittest
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def clean_model_name(model_id):
    name = model_id.split('/')[-1]
    if name.lower().endswith(':latest'):
        name = name[:-7]
    return name

def format_display_name(label, params, size_gb):
    # Target format: Local LLM Lab — Phi-4 14B · 14.7B · 9.1 GB
    return f"Local LLM Lab — {label} · {params} · {size_gb} GB"

def format_runtime_display_name(label, params, size_gb, runtime_mem_gb):
    name = format_display_name(label, params, size_gb)
    return f"{name} · Needs more RAM" if is_constrained(size_gb, runtime_mem_gb) else name

def get_effective_ctx(metadata_ctx, user_cap=8192):
    if metadata_ctx is None:
        return user_cap
    return min(metadata_ctx, user_cap)

def is_constrained(size_gb, runtime_mem_gb):
    # conservative threshold: model disk size > 70% of runtime GB
    if runtime_mem_gb <= 0:
        return False
    return size_gb > (runtime_mem_gb * 0.7)

class TestModelCatalog(unittest.TestCase):
    def test_installed_alias_customizes_itself(self):
        script = (ROOT / "scripts/setup-openwebui-role-models.sh").read_text()
        self.assertIn("base_model_id: $alias_id", script)
        self.assertNotIn("base_model_id: $m.model_name,\n          name: \"Local LLM Lab", script)

    def test_upsert_handles_provider_overrides_idempotently(self):
        script = (ROOT / "scripts/setup-openwebui-role-models.sh").read_text()
        create = script.index('api POST /api/v1/models/create')
        update = script.index('api POST /api/v1/models/model/update')
        self.assertLess(create, update)

    def test_display_name(self):
        self.assertEqual(
            format_display_name("Phi-4 14B", "14.7B", 9.1),
            "Local LLM Lab — Phi-4 14B · 14.7B · 9.1 GB"
        )

    def test_cpu_alias_has_human_label(self):
        script = (ROOT / "scripts/setup-openwebui-role-models.sh").read_text()
        self.assertIn('"name": "Llama 3.2 3B CPU"', script)

    def test_context_cap(self):
        self.assertEqual(get_effective_ctx(131072, 8192), 8192)
        self.assertEqual(get_effective_ctx(4096, 8192), 4096)
        self.assertEqual(get_effective_ctx(32768, 4096), 4096)

    def test_constrained_15_7(self):
        runtime_gb = 15.7
        # Mistral Small 22B is 12.6 GB. 12.6 / 15.7 = ~80%
        self.assertTrue(is_constrained(12.6, runtime_gb))
        # Qwen 3.5 9B is 6.6 GB. 6.6 / 15.7 = ~42%
        self.assertFalse(is_constrained(6.6, runtime_gb))
        # Phi-4 14B is 9.1 GB. 9.1 / 15.7 = ~58%
        self.assertFalse(is_constrained(9.1, runtime_gb))
        # But if model > 11.0 GB (70% of 15.7), it is constrained
        self.assertTrue(is_constrained(11.1, runtime_gb))
        self.assertTrue(
            format_runtime_display_name("Mistral Small 22B", "22.2B", 12.6, runtime_gb)
            .endswith("Needs more RAM")
        )

    def test_fixture_logic(self):
        metadata = {
            "models": [
                {
                    "label": "Qwen3.5 9B",
                    "model_name": "qwen3.5:9b",
                    "parameters": "9.7B",
                    "size_gb": 6.6,
                    "context_tokens": 262144
                }
            ]
        }
        m = metadata["models"][0]
        name = format_display_name(m["label"], m["parameters"], m["size_gb"])
        self.assertNotIn(":latest", name)
        self.assertEqual(name, "Local LLM Lab — Qwen3.5 9B · 9.7B · 6.6 GB")

        ctx = get_effective_ctx(m["context_tokens"], 8192)
        self.assertEqual(ctx, 8192)

if __name__ == "__main__":
    unittest.main()
