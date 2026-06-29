import importlib
import sys
import types

import pytest


def import_recorder_with_stubs(monkeypatch):
    sys.modules.pop("Recorder", None)
    pynput = types.ModuleType("pynput")
    pynput.mouse = types.SimpleNamespace(Listener=object)
    pynput.keyboard = types.SimpleNamespace(Listener=object, Key=types.SimpleNamespace(f10="f10"))
    monkeypatch.setitem(sys.modules, "pynput", pynput)
    return importlib.import_module("Recorder")


@pytest.fixture(autouse=True)
def clean_recorder_import():
    sys.modules.pop("Recorder", None)
    yield
    sys.modules.pop("Recorder", None)


def test_build_output_path_stays_inside_recordings(monkeypatch, tmp_path):
    recorder = import_recorder_with_stubs(monkeypatch)

    assert recorder.build_output_path("bank_fish", tmp_path) == tmp_path / "bank_fish.json"
    assert recorder.build_output_path("bank_fish.json", tmp_path) == tmp_path / "bank_fish.json"


def test_build_output_path_rejects_paths(monkeypatch, tmp_path):
    recorder = import_recorder_with_stubs(monkeypatch)

    with pytest.raises(ValueError, match="filename"):
        recorder.build_output_path("../outside", tmp_path)

    with pytest.raises(ValueError, match="filename"):
        recorder.build_output_path(str(tmp_path / "outside"), tmp_path)


def test_click_positions_are_recorded_in_baseline_coordinates(monkeypatch):
    recorder = import_recorder_with_stubs(monkeypatch)
    pag = types.ModuleType("pyautogui")
    pag.size = lambda: (960, 540)
    monkeypatch.setitem(sys.modules, "pyautogui", pag)

    assert recorder.normalize_position(480, 270) == (960, 540)


def test_invalid_baseline_environment_falls_back(monkeypatch):
    monkeypatch.setenv("CHADBOT_BASE_WIDTH", "invalid")
    monkeypatch.setenv("CHADBOT_BASE_HEIGHT", "0")
    recorder = import_recorder_with_stubs(monkeypatch)

    assert recorder.BASE_WIDTH == 1920
    assert recorder.BASE_HEIGHT == 1080
