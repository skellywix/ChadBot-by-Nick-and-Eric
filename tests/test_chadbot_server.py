from pathlib import Path

import pytest

from chadbot import server


def test_resolve_repo_path_rejects_traversal():
    with pytest.raises(ValueError, match="inside the repository"):
        server.resolve_repo_path("../outside.py")


def test_validate_edit_path_rejects_binary_assets():
    with pytest.raises(ValueError, match="not allowed"):
        server.validate_edit_path("scripts/minnows/minnow.png")


def test_discover_scripts_includes_core_and_activity_scripts():
    paths = {item["path"] for item in server.discover_scripts()}

    assert "Recorder.py" in paths
    assert "scripts/anglerfish/anglerfish.py" in paths
    assert "chadbot/server.py" not in paths


def test_build_script_command_runs_from_script_directory():
    script_path = server.REPO_ROOT / "scripts" / "anglerfish" / "anglerfish.py"

    command, cwd, env = server.build_script_command(script_path, args=["--dry-run"])

    assert command[:3] == [server.sys.executable, "-u", "anglerfish.py"]
    assert command[-1] == "--dry-run"
    assert cwd == script_path.parent
    assert str(server.REPO_ROOT) in env["PYTHONPATH"]
    assert env["CHADBOT_REPO_ROOT"] == str(server.REPO_ROOT)
    assert env["CHADBOT_SCRIPT_DIR"] == str(script_path.parent)
    assert env["CHADBOT_SCRIPT_PATH"] == str(script_path)


def test_build_script_command_applies_runtime_settings(monkeypatch, tmp_path):
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(server, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(server, "RUNTIME_ROOT", tmp_path)
    server.save_runtime_settings({
        "baseWidth": 1280,
        "baseHeight": 720,
        "disableScaling": True,
        "templateScales": "1,0.75",
    })
    script_path = server.REPO_ROOT / "scripts" / "anglerfish" / "anglerfish.py"

    _, _, env = server.build_script_command(script_path)

    assert env["CHADBOT_BASE_WIDTH"] == "1280"
    assert env["CHADBOT_BASE_HEIGHT"] == "720"
    assert env["CHADBOT_DISABLE_SCALING"] == "1"
    assert env["CHADBOT_TEMPLATE_SCALES"] == "1,0.75"


def test_portability_config_uses_safe_defaults(monkeypatch):
    monkeypatch.setenv("CHADBOT_BASE_WIDTH", "nope")
    monkeypatch.setenv("CHADBOT_BASE_HEIGHT", "-1")
    monkeypatch.delenv("CHADBOT_TEMPLATE_SCALES", raising=False)

    config = server.portability_config()

    assert config["baseWidth"] == 1920
    assert config["baseHeight"] == 1080
    assert config["templateScales"] == "auto"
    assert "CHADBOT_SCRIPT_DIR" in config["assetLookup"]


def test_runtime_settings_roundtrip_and_reset(monkeypatch, tmp_path):
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(server, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(server, "RUNTIME_ROOT", tmp_path)

    saved = server.save_runtime_settings({
        "baseWidth": 1600,
        "baseHeight": 900,
        "disableScaling": True,
        "templateScales": "1,0.5",
    })

    assert settings_path.exists()
    assert saved == server.load_runtime_settings()
    assert server.reset_runtime_settings()["baseWidth"] == 1920
    assert not settings_path.exists()


def test_normalize_settings_parses_bool_strings_and_template_scales():
    settings = server.normalize_settings({
        "baseWidth": "1280",
        "baseHeight": "720",
        "disableScaling": "false",
        "templateScales": "1, 0.75, 1.25x0.8",
    })

    assert settings == {
        "baseWidth": 1280,
        "baseHeight": 720,
        "disableScaling": False,
        "templateScales": "1,0.75,1.25x0.8",
    }


def test_normalize_settings_rejects_invalid_dimensions():
    with pytest.raises(ValueError, match="positive"):
        server.normalize_settings({"baseWidth": 0, "baseHeight": "bad"})


def test_normalize_settings_rejects_invalid_template_scales():
    with pytest.raises(ValueError, match="Template scales"):
        server.normalize_settings({"templateScales": "1,nope"})

    with pytest.raises(ValueError, match="Template scales"):
        server.normalize_settings({"templateScales": "0x1"})


def test_normalize_settings_rejects_non_object_payload():
    with pytest.raises(ValueError, match="JSON object"):
        server.normalize_settings(["not", "an", "object"])


def test_save_runtime_settings_rejects_non_object_payload(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(server, "RUNTIME_ROOT", tmp_path)

    with pytest.raises(ValueError, match="JSON object"):
        server.save_runtime_settings([])


def test_validate_edit_path_allows_new_safe_subfolder_file():
    path = server.validate_edit_path("scripts/new_bot/new_bot.py")

    assert path == Path(server.REPO_ROOT / "scripts" / "new_bot" / "new_bot.py")


def test_parse_args_rejects_remote_bind_without_opt_in():
    with pytest.raises(SystemExit):
        server.parse_args(["--host", "0.0.0.0"])

    args = server.parse_args(["--host", "0.0.0.0", "--allow-remote"])
    assert args.allow_remote is True
