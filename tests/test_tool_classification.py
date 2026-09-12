"""Tests for the tool security classification table (task 1.1).

The gate these enforce: an upstream sync that adds an unclassified tool must
fail verification instead of silently shipping an unclassified surface.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from blender_mcp import tool_classification as tc

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestTableIntegrity:
    def test_every_tool_has_valid_level(self):
        for name, level in tc.TOOL_CLASSIFICATION.items():
            assert level in tc.LEVELS, f"{name} has invalid level {level!r}"

    def test_table_matches_live_server_registration(self):
        registered = asyncio.run(tc.registered_tool_names())
        problems = tc.classification_errors(registered)
        assert problems == []

    def test_exec_and_generate_tools_exist(self):
        assert tc.tools_for_level("exec") == ["execute_blender_code"]
        assert set(tc.tools_for_level("generate")) == {
            "generate_hyper3d_model_via_text",
            "generate_hyper3d_model_via_images",
            "generate_hunyuan3d_model",
        }

    def test_unclassified_tool_fails(self):
        problems = tc.classification_errors(
            set(tc.TOOL_CLASSIFICATION) | {"shiny_new_upstream_tool"}
        )
        assert len(problems) == 1
        assert "shiny_new_upstream_tool" in problems[0]
        assert "unclassified" in problems[0]

    def test_dropped_classification_fails(self):
        table = dict(tc.TOOL_CLASSIFICATION)
        del table["set_texture"]
        problems = tc.classification_errors(set(tc.TOOL_CLASSIFICATION), table)
        assert any("unclassified" in p and "set_texture" in p for p in problems)

    def test_table_entry_not_registered_fails(self):
        table = dict(tc.TOOL_CLASSIFICATION)
        table["retired_upstream_tool"] = "read"
        problems = tc.classification_errors(set(tc.TOOL_CLASSIFICATION), table)
        assert any("unknown" in p and "retired_upstream_tool" in p for p in problems)

    def test_invalid_level_fails(self):
        table = dict(tc.TOOL_CLASSIFICATION)
        table["set_texture"] = "superuser"
        problems = tc.classification_errors(set(table), table)
        assert any("invalid classification levels" in p for p in problems)


class TestExportProfileGuard:
    def test_default_export_excludes_generate_and_exec(self):
        tools = tc.default_export_tools()
        assert tc.tools_for_level("exec")[0] not in tools
        for tool in tc.tools_for_level("generate"):
            assert tool not in tools

    def test_default_export_within_gateway_cap(self):
        assert len(tc.default_export_tools()) <= tc.GATEWAY_MAX_PUBLIC_TOOLS

    def test_assert_exportable_rejects_exec(self):
        with pytest.raises(ValueError, match="execute_blender_code"):
            tc.assert_exportable(tc.default_export_tools() + ["execute_blender_code"])

    def test_assert_exportable_rejects_generate(self):
        with pytest.raises(ValueError, match="generate_hunyuan3d_model"):
            tc.assert_exportable(["generate_hunyuan3d_model"])

    def test_assert_exportable_rejects_unknown_tool(self):
        with pytest.raises(ValueError, match="missing from the classification"):
            tc.assert_exportable(["get_scene_info", "not_a_real_tool"])


class TestJsonArtifact:
    def test_artifact_exists_and_matches_module(self):
        problems = tc.json_artifact_matches_module()
        assert problems == []

    def test_artifact_round_trip(self, tmp_path):
        path = tc.export_json(tmp_path / "classification.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema"] == tc.JSON_SCHEMA_NAME
        assert data["counts"]["total"] == len(tc.TOOL_CLASSIFICATION)
        for level in tc.LEVELS:
            assert data["tools"][level] == tc.tools_for_level(level)
        assert tc.json_artifact_matches_module(path) == []
        assert tc.json_artifact_in_sync(path)[0]

    def test_stale_artifact_detected(self, tmp_path):
        path = tmp_path / "classification.json"
        tc.export_json(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["tools"]["read"] = payload["tools"]["read"] + ["bogus_tool"]
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        assert tc.json_artifact_matches_module(path) != []
        assert not tc.json_artifact_in_sync(path)[0]

    def test_missing_artifact_detected(self, tmp_path):
        assert tc.json_artifact_matches_module(tmp_path / "absent.json") != []


class TestCredentialHeuristic:
    def test_missing_credentials_detected_without_values(self, monkeypatch):
        for var in tc.PROVIDER_CREDENTIAL_ENV_VARS.values():
            monkeypatch.delenv(var, raising=False)
        assert tc.missing_provider_credentials() == ["hyper3d", "polypizza", "sketchfab"]

    def test_configured_sources_omitted(self, monkeypatch):
        for var in tc.PROVIDER_CREDENTIAL_ENV_VARS.values():
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("BLENDERMCP_HYPER3D_API_KEY", "set")
        assert tc.missing_provider_credentials() == ["polypizza", "sketchfab"]

    def test_explicit_env_map(self):
        assert tc.missing_provider_credentials(env={}) == ["hyper3d", "polypizza", "sketchfab"]
        assert (
            tc.missing_provider_credentials(
                env={"BLENDERMCP_SKETCHFAB_API_KEY": "x"}
            )
            == ["hyper3d", "polypizza"]
        )


class TestVerifyScript:
    def _load_verify_module(self):
        import importlib.util

        path = REPO_ROOT / "scripts" / "verify_tool_classification.py"
        spec = importlib.util.spec_from_file_location("verify_tool_classification", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_verify_script_passes(self):
        module = self._load_verify_module()
        assert asyncio.run(module.collect_problems()) == []
        assert module.main() == 0
