import importlib
import json
import sys
import types

import numpy as np
import pytest


def import_functions_with_stubs(monkeypatch, screen_size=(1920, 1080)):
    sys.modules.pop("functions", None)

    pag = types.ModuleType("pyautogui")
    pag.calls = []
    pag.screenshot_image = np.zeros((1, 1, 3), dtype=np.uint8)
    pag.FAILSAFE = False

    def screenshot(*args, region=None, **kwargs):
        pag.calls.append(("screenshot", region))
        return pag.screenshot_image

    def record_call(name):
        def call(*args, **kwargs):
            pag.calls.append((name, args, kwargs))
        return call

    pag.size = lambda: screen_size
    pag.screenshot = screenshot
    pag.moveTo = record_call("moveTo")
    pag.move = record_call("move")
    pag.click = record_call("click")
    pag.doubleClick = record_call("doubleClick")
    pag.rightClick = record_call("rightClick")
    pag.pixel = lambda x, y: (x, y, 0)
    pag.pixelMatchesColor = lambda x, y, expected_rgb_color, tolerance=0: (x, y) == (screen_size[0] // 2, screen_size[1] // 2)
    pag.mouseDown = record_call("mouseDown")
    pag.mouseUp = record_call("mouseUp")
    pag.keyDown = lambda key: pag.calls.append(("keyDown", key))
    pag.keyUp = lambda key: pag.calls.append(("keyUp", key))

    cv = types.ModuleType("cv2")
    cv.TM_CCOEFF_NORMED = 5
    cv.TM_SQDIFF = 0
    cv.TM_SQDIFF_NORMED = 1
    cv.IMREAD_UNCHANGED = -1
    cv.IMREAD_COLOR = 1
    cv.IMREAD_GRAYSCALE = 0
    cv.COLOR_RGB2BGR = 1
    cv.COLOR_BGR2HSV = 2
    cv.COLOR_BGR2GRAY = 3
    cv.COLOR_BGR2RGB = 4
    cv.THRESH_BINARY = 8
    cv.THRESH_OTSU = 16
    cv.LINE_4 = 4
    cv.MARKER_CROSS = 0
    cv.INTER_CUBIC = 2
    cv.INTER_AREA = 3
    cv.imread = lambda filename, flags=cv.IMREAD_COLOR: np.zeros((1, 1, 3), dtype=np.uint8)
    cv.resize = lambda image, size, interpolation=None: np.zeros((size[1], size[0], image.shape[2]), dtype=image.dtype)
    cv.cvtColor = lambda image, code: image

    monkeypatch.setitem(sys.modules, "pyautogui", pag)
    monkeypatch.setitem(sys.modules, "cv2", cv)
    monkeypatch.setitem(sys.modules, "win32con", types.SimpleNamespace(SRCCOPY=0))
    monkeypatch.setitem(sys.modules, "win32gui", types.ModuleType("win32gui"))
    monkeypatch.setitem(sys.modules, "win32ui", types.ModuleType("win32ui"))

    module = importlib.import_module("functions")
    return module, pag


@pytest.fixture(autouse=True)
def clean_functions_import():
    sys.modules.pop("functions", None)
    yield
    sys.modules.pop("functions", None)


def test_check_pixel_color_does_not_wrap_uint8_differences(monkeypatch):
    functions, pag = import_functions_with_stubs(monkeypatch)

    pag.screenshot_image = np.array([[[0, 0, 0]]], dtype=np.uint8)
    assert functions.check_pixel_color_in_area(target_color=(255, 255, 255), tolerance=5) is False

    pag.screenshot_image = np.array([[[252, 254, 255]]], dtype=np.uint8)
    assert functions.check_pixel_color_in_area(target_color=(255, 255, 255), tolerance=5) is True


def test_create_inv_grid_uses_width_for_x_and_height_for_y(monkeypatch):
    functions, _ = import_functions_with_stubs(monkeypatch)

    grid = functions.create_inv_grid(tl=(0, 0), br=(80, 70), rows=7, columns=4)

    assert grid["Slot 1"] == (10, 5)
    assert grid["Slot 4"] == (70, 5)
    assert grid["Slot 5"] == (10, 15)


def test_play_actions_releases_key_up_events(monkeypatch, tmp_path):
    functions, pag = import_functions_with_stubs(monkeypatch)
    monkeypatch.setattr(functions, "r", lambda *args: 0)
    monkeypatch.setattr(functions.time, "sleep", lambda seconds: None)

    recording_dir = tmp_path / "recordings"
    recording_dir.mkdir()
    recording_path = recording_dir / "actions.json"
    recording_path.write_text(
        json.dumps([
            {"time": 0, "type": "KeyDown", "button": "a", "pos": None},
            {"time": 0.01, "type": "KeyUp", "button": "a", "pos": None},
        ]),
        encoding="utf-8",
    )

    functions.play_actions("actions.json", new_path=recording_dir)

    assert ("keyDown", "a") in pag.calls
    assert ("keyUp", "a") in pag.calls
    assert pag.calls.index(("keyDown", "a")) < pag.calls.index(("keyUp", "a"))


def test_move_click_generates_random_offsets_per_call(monkeypatch):
    functions, pag = import_functions_with_stubs(monkeypatch)
    offsets = iter([1, 2, 3, 4])
    monkeypatch.setattr(functions, "p", lambda *args: next(offsets))
    monkeypatch.setattr(functions, "r", lambda *args: 0)
    monkeypatch.setattr(functions.time, "sleep", lambda seconds: None)

    functions.move_click(10, 20)
    functions.move_click(10, 20)

    move_calls = [call for call in pag.calls if call[0] == "moveTo"]
    assert move_calls[0][1] == (11, 22, 0)
    assert move_calls[1][1] == (13, 24, 0)


def test_pyautogui_shim_scales_raw_move_to(monkeypatch):
    functions, pag = import_functions_with_stubs(monkeypatch, screen_size=(960, 540))

    pag.moveTo(100, 200, 0.5)

    assert pag.calls[-1] == ("moveTo", (50, 100, 0.5), {})
    assert functions.scale_region((100, 200, 300, 400)) == (50, 100, 150, 200)


def test_click_shim_scales_tuple_coordinates(monkeypatch):
    _, pag = import_functions_with_stubs(monkeypatch, screen_size=(960, 540))

    pag.click((100, 200))

    assert pag.calls[-1] == ("click", (50, 100), {})


def test_take_screenshot_scales_region(monkeypatch):
    functions, pag = import_functions_with_stubs(monkeypatch, screen_size=(960, 540))
    pag.screenshot_image = np.zeros((10, 20, 3), dtype=np.uint8)

    image = functions.take_screenshot((100, 200, 300, 400))

    assert image.shape == (10, 20, 3)
    assert pag.calls[-1] == ("screenshot", (50, 100, 150, 200))


def test_resolve_asset_path_searches_repository(monkeypatch):
    functions, _ = import_functions_with_stubs(monkeypatch)

    assert functions.resolve_asset_path("README.md").name == "README.md"


def test_invalid_baseline_environment_falls_back(monkeypatch):
    monkeypatch.setenv("CHADBOT_BASE_WIDTH", "invalid")
    monkeypatch.setenv("CHADBOT_BASE_HEIGHT", "0")
    functions, _ = import_functions_with_stubs(monkeypatch)

    assert functions.BASE_WIDTH == 1920
    assert functions.BASE_HEIGHT == 1080
