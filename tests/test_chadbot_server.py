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


def test_validate_edit_path_allows_new_safe_subfolder_file():
    path = server.validate_edit_path("scripts/new_bot/new_bot.py")

    assert path == Path(server.REPO_ROOT / "scripts" / "new_bot" / "new_bot.py")


def test_parse_args_rejects_remote_bind_without_opt_in():
    with pytest.raises(SystemExit):
        server.parse_args(["--host", "0.0.0.0"])

    args = server.parse_args(["--host", "0.0.0.0", "--allow-remote"])
    assert args.allow_remote is True
