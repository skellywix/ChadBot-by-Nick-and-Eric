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


def test_runtime_diagnostics_reports_missing_dependency(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(server, "RUNTIME_ROOT", tmp_path)

    diagnostics = server.runtime_diagnostics(
        module_checker=lambda module: module != "cv2",
        executable_checker=lambda name: None,
        screen_probe=lambda: {"available": True, "width": 1920, "height": 1080},
    )

    assert diagnostics["status"] == "error"
    assert any(dependency["module"] == "cv2" and dependency["status"] == "error" for dependency in diagnostics["dependencies"])
    assert any(check["label"] == "Python packages" and "OpenCV" in check["detail"] for check in diagnostics["checks"])
    assert any(check["label"] == "Tesseract app" and check["status"] == "warn" for check in diagnostics["checks"])


def test_runtime_diagnostics_reports_screen_scale(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(server, "RUNTIME_ROOT", tmp_path)
    server.save_runtime_settings({"baseWidth": 1000, "baseHeight": 500})

    diagnostics = server.runtime_diagnostics(
        module_checker=lambda module: True,
        executable_checker=lambda name: "C:/Tools/tesseract.exe",
        screen_probe=lambda: {"available": True, "width": 2000, "height": 1000},
    )

    assert diagnostics["status"] == "ok"
    assert diagnostics["screen"]["scaleX"] == 2
    assert diagnostics["screen"]["scaleY"] == 2
    assert diagnostics["assets"]["scripts"] == len(server.discover_scripts())


def test_setup_requirements_command_is_allowlisted(monkeypatch, tmp_path):
    requirements = tmp_path / "requirements.txt"
    dev_requirements = tmp_path / "requirements-dev.txt"
    requirements.write_text("PyAutoGUI\n", encoding="utf-8")
    dev_requirements.write_text("pytest\n", encoding="utf-8")
    monkeypatch.setattr(server, "REQUIREMENTS_FILES", (requirements, dev_requirements))

    command = server.setup_requirements_command()

    assert command[:5] == [server.sys.executable, "-m", "pip", "install", "--disable-pip-version-check"]
    assert command.count("-r") == 2
    assert str(requirements) in command
    assert str(dev_requirements) in command


def test_setup_requirements_command_rejects_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "REQUIREMENTS_FILES", (tmp_path / "missing.txt",))

    with pytest.raises(FileNotFoundError, match="Missing requirements file"):
        server.setup_requirements_command()


def test_setup_manager_install_requirements_runs_fixed_command(monkeypatch, tmp_path):
    requirements = tmp_path / "requirements.txt"
    dev_requirements = tmp_path / "requirements-dev.txt"
    requirements.write_text("PyAutoGUI\n", encoding="utf-8")
    dev_requirements.write_text("pytest\n", encoding="utf-8")
    monkeypatch.setattr(server, "REQUIREMENTS_FILES", (requirements, dev_requirements))
    captured = {}

    class FakeProcess:
        def __init__(self):
            self.stdout = ["installed\n"]
            self.returncode = None

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            self.returncode = 0
            return 0

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return FakeProcess()

    class ImmediateThread:
        def __init__(self, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            self.target()

    monkeypatch.setattr(server.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(server.threading, "Thread", ImmediateThread)

    manager = server.SetupManager()
    status = manager.install_requirements()

    assert captured["command"] == server.setup_requirements_command()
    assert captured["kwargs"]["cwd"] == server.REPO_ROOT
    assert "shell" not in captured["kwargs"]
    assert status["running"] is False
    assert status["returnCode"] == 0
    assert any("installed" in entry["text"] for entry in manager.logs()["logs"])


def test_validate_edit_path_allows_new_safe_subfolder_file():
    path = server.validate_edit_path("scripts/new_bot/new_bot.py")

    assert path == Path(server.REPO_ROOT / "scripts" / "new_bot" / "new_bot.py")


def test_parse_args_rejects_remote_bind_without_opt_in():
    with pytest.raises(SystemExit):
        server.parse_args(["--host", "0.0.0.0"])

    args = server.parse_args(["--host", "0.0.0.0", "--allow-remote"])
    assert args.allow_remote is True
