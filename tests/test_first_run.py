"""Tests for the five-state first-run connection model (task 1.4)."""

from __future__ import annotations

from blender_mcp import first_run as fr


class TestStateDetermination:
    def test_not_configured(self):
        state = fr.determine_state(fr.StateInput(registry_has_blender=False))
        assert state is fr.ConnectionState.NOT_CONFIGURED

    def test_server_unreachable(self):
        state = fr.determine_state(
            fr.StateInput(registry_has_blender=True, server_runnable=False)
        )
        assert state is fr.ConnectionState.SERVER_UNREACHABLE

    def test_addon_disconnected_via_socket(self):
        state = fr.determine_state(
            fr.StateInput(
                registry_has_blender=True,
                server_runnable=True,
                socket_reachable=False,
            )
        )
        assert state is fr.ConnectionState.ADDON_DISCONNECTED

    def test_addon_disconnected_via_roundtrip(self):
        state = fr.determine_state(
            fr.StateInput(
                registry_has_blender=True,
                server_runnable=True,
                socket_reachable=True,
                read_roundtrip_ok=False,
            )
        )
        assert state is fr.ConnectionState.ADDON_DISCONNECTED

    def test_ready(self):
        state = fr.determine_state(
            fr.StateInput(
                registry_has_blender=True,
                server_runnable=True,
                socket_reachable=True,
                read_roundtrip_ok=True,
            )
        )
        assert state is fr.ConnectionState.READY

    def test_degraded_when_credentials_missing(self):
        state = fr.determine_state(
            fr.StateInput(
                registry_has_blender=True,
                server_runnable=True,
                socket_reachable=True,
                read_roundtrip_ok=True,
                missing_credentials=["hyper3d"],
            )
        )
        assert state is fr.ConnectionState.DEGRADED

    def test_degraded_beats_ready_only_after_core_ok(self):
        # Credentials missing but socket down: the blocker is the addon.
        state = fr.determine_state(
            fr.StateInput(
                registry_has_blender=True,
                server_runnable=True,
                socket_reachable=False,
                missing_credentials=["hyper3d"],
            )
        )
        assert state is fr.ConnectionState.ADDON_DISCONNECTED

    def test_all_five_states_reachable(self):
        seen = {
            fr.determine_state(fr.StateInput(registry_has_blender=False)),
            fr.determine_state(
                fr.StateInput(registry_has_blender=True, server_runnable=False)
            ),
            fr.determine_state(
                fr.StateInput(
                    registry_has_blender=True, server_runnable=True, socket_reachable=False
                )
            ),
            fr.determine_state(
                fr.StateInput(
                    registry_has_blender=True,
                    server_runnable=True,
                    socket_reachable=True,
                    read_roundtrip_ok=True,
                )
            ),
            fr.determine_state(
                fr.StateInput(
                    registry_has_blender=True,
                    server_runnable=True,
                    socket_reachable=True,
                    read_roundtrip_ok=True,
                    missing_credentials=["sketchfab"],
                )
            ),
        }
        assert seen == set(fr.ConnectionState)

    def test_unknown_probes_resolve_conservatively(self):
        # No evidence at all: nothing positive, so never ready.
        assert fr.determine_state(fr.StateInput()) is fr.ConnectionState.NOT_CONFIGURED
        # Registry present but server unprobed: not ready either.
        assert (
            fr.determine_state(fr.StateInput(registry_has_blender=True))
            is fr.ConnectionState.SERVER_UNREACHABLE
        )
        # Server probed ok but socket unprobed: still not ready.
        assert (
            fr.determine_state(
                fr.StateInput(registry_has_blender=True, server_runnable=True)
            )
            is fr.ConnectionState.ADDON_DISCONNECTED
        )


class TestStateCopy:
    def test_every_state_has_title_message_action(self):
        for state in fr.ConnectionState:
            copy = fr.state_copy(state)
            assert set(copy) == {"title", "message", "action"}
            for value in copy.values():
                assert value.strip()

    def test_copy_contains_no_paths_or_credentials(self):
        assert fr.all_copy_sanitized() == {}

    def test_non_ready_states_have_unique_recovery_actions(self):
        assert fr.unique_recovery_actions()

    def test_ready_action_is_noop(self):
        assert fr.state_copy(fr.ConnectionState.READY)["action"] == "无需处理。"

    def test_rendered_line_includes_state_id(self):
        line = fr.render_state_line(fr.ConnectionState.ADDON_DISCONNECTED)
        assert line.startswith("[addon_disconnected]")

    def test_sanitizer_catches_paths_and_credentials(self):
        assert fr.copy_is_sanitized("/home/alice/registry.yaml") != []
        assert fr.copy_is_sanitized("api_key: abc") != []
        assert fr.copy_is_sanitized("see https://internal.example.com") != []
        assert fr.copy_is_sanitized("append to ~/.mcp-gateway/registry.yaml") != []
        assert fr.copy_is_sanitized("在 Blender 中启动连接") == []


class TestRegistryScan:
    def test_detects_blender_entry(self):
        text = (
            "version: 1\n"
            "gateway:\n  host: 127.0.0.1\n  port: 8080\n"
            "servers:\n"
            "  blender:\n"
            "    enabled: true\n"
            "    transport: stdio\n"
        )
        assert fr.registry_mentions_blender(text) is True

    def test_no_servers_block(self):
        text = "version: 1\ngateway:\n  host: 127.0.0.1\n"
        assert fr.registry_mentions_blender(text) is False

    def test_other_server_only(self):
        text = "servers:\n  gitea-mcp:\n    enabled: true\n"
        assert fr.registry_mentions_blender(text) is False

    def test_nested_key_is_not_a_server(self):
        text = "servers:\n  other:\n    blender: fake\n"
        assert fr.registry_mentions_blender(text) is False

    def test_comment_lines_ignored(self):
        text = "servers:\n  # blender: commented out\n  other:\n    enabled: true\n"
        assert fr.registry_mentions_blender(text) is False

    def test_disabled_entry_detected(self):
        text = "servers:\n  blender:\n    enabled: false\n"
        assert fr.registry_disabled_blender(text) is True
        assert fr.registry_mentions_blender(text) is True

    def test_enabled_entry_not_disabled(self):
        text = "servers:\n  blender:\n    enabled: true\n"
        assert fr.registry_disabled_blender(text) is False

    def test_missing_entry_not_disabled(self):
        assert fr.registry_disabled_blender("servers:\n  other:\n    enabled: false\n") is False


class TestJourneyScript:
    def _load_script(self):
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parents[1] / "scripts" / "blender_first_run.py"
        spec = importlib.util.spec_from_file_location("blender_first_run", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_snippet_subcommand_prints_fragment(self, capsys):
        module = self._load_script()
        assert module.main(["snippet"]) == 0
        out = capsys.readouterr().out
        assert out.startswith("servers:")
        assert "namespace: blender" in out

    def test_state_subcommand_reports_not_configured(self, capsys, tmp_path):
        module = self._load_script()
        code = module.main(
            ["state", "--registry", str(tmp_path / "absent.yaml"), "--json"]
        )
        assert code == 2
        data = __import__("json").loads(capsys.readouterr().out)
        assert data["state"] == "not_configured"
        assert data["probes"]["registry_has_blender"] is None

    def test_state_subcommand_configured_registry_without_addon(self, capsys, tmp_path):
        # In the test environment Blender's addon is never listening, so a
        # configured registry must resolve to addon_disconnected (server
        # launches locally, socket does not answer).
        module = self._load_script()
        registry = tmp_path / "registry.yaml"
        registry.write_text(
            "servers:\n  blender:\n    enabled: true\n    transport: stdio\n",
            encoding="utf-8",
        )
        code = module.main(["state", "--registry", str(registry), "--json"])
        assert code == 2
        data = __import__("json").loads(capsys.readouterr().out)
        assert data["probes"]["registry_has_blender"] is True
        assert data["probes"]["server_runnable"] is True
        assert data["probes"]["socket_reachable"] is False
        assert data["state"] == "addon_disconnected"
        assert data["action"]

    def test_probe_socket_refuses_non_loopback(self):
        module = self._load_script()
        assert module.probe_socket(host="10.0.0.5") is None
