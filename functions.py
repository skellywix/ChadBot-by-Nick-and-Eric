import random
import cv2 as cv
import time
import pyautogui as pag
import json
import inspect
import os
from pathlib import Path
import win32con
import win32gui
import win32ui
import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parent
DISABLE_SCALING = os.environ.get("CHADBOT_DISABLE_SCALING", "").lower() in {"1", "true", "yes", "on"}
_FUNCTIONS_PATH = Path(__file__).resolve()
_ORIGINAL_CV_IMREAD = cv.imread
_ORIGINAL_PAG_MOVE_TO = pag.moveTo
_ORIGINAL_PAG_MOVE = getattr(pag, "move", None)
_ORIGINAL_PAG_CLICK = pag.click
_ORIGINAL_PAG_RIGHT_CLICK = pag.rightClick
_ORIGINAL_PAG_DOUBLE_CLICK = pag.doubleClick
_ORIGINAL_PAG_SCREENSHOT = pag.screenshot
_ORIGINAL_PAG_PIXEL = getattr(pag, "pixel", None)
_ORIGINAL_PAG_PIXEL_MATCHES_COLOR = getattr(pag, "pixelMatchesColor", None)


def _env_positive_int(name, default):
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


BASE_WIDTH = _env_positive_int("CHADBOT_BASE_WIDTH", 1920)
BASE_HEIGHT = _env_positive_int("CHADBOT_BASE_HEIGHT", 1080)


def _current_screen_size():
    try:
        size = pag.size()
        if hasattr(size, "width") and hasattr(size, "height"):
            return int(size.width), int(size.height)
        return int(size[0]), int(size[1])
    except Exception:
        return BASE_WIDTH, BASE_HEIGHT


def coordinate_scale():
    if DISABLE_SCALING:
        return 1.0, 1.0
    width, height = _current_screen_size()
    if width <= 0 or height <= 0:
        return 1.0, 1.0
    return width / BASE_WIDTH, height / BASE_HEIGHT


def _scale_value(value, scale):
    return int(round(float(value) * scale))


def scale_point(x, y):
    sx, sy = coordinate_scale()
    return _scale_value(x, sx), _scale_value(y, sy)


def scale_delta(dx, dy):
    sx, sy = coordinate_scale()
    return _scale_value(dx, sx), _scale_value(dy, sy)


def unscale_point(x, y):
    sx, sy = coordinate_scale()
    return int(round(float(x) / sx)), int(round(float(y) / sy))


def scale_region(region):
    x, y, w, h = region
    sx, sy = coordinate_scale()
    return (
        _scale_value(x, sx),
        _scale_value(y, sy),
        max(1, _scale_value(w, sx)),
        max(1, _scale_value(h, sy)),
    )


def _caller_dir():
    for frame in inspect.stack()[2:]:
        try:
            candidate = Path(frame.filename).resolve()
        except OSError:
            continue
        if candidate != _FUNCTIONS_PATH:
            return candidate.parent
    return Path.cwd()


def resolve_asset_path(path, base_dir=None, must_exist=True):
    candidate = Path(path)
    if candidate.is_absolute():
        if must_exist and not candidate.exists():
            raise FileNotFoundError(f"File not found: {candidate}")
        return candidate

    search_dirs = []
    if base_dir:
        search_dirs.append(Path(base_dir))
    if os.environ.get("CHADBOT_SCRIPT_DIR"):
        search_dirs.append(Path(os.environ["CHADBOT_SCRIPT_DIR"]))
    search_dirs.extend([_caller_dir(), Path.cwd(), REPO_ROOT])

    for directory in search_dirs:
        resolved = (directory / candidate).resolve()
        if resolved.exists():
            return resolved

    fallback = (search_dirs[0] / candidate).resolve()
    if must_exist:
        raise FileNotFoundError(f"File not found: {path}")
    return fallback


def resolve_output_path(path, base_dir=None):
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    directory = Path(base_dir) if base_dir else _caller_dir()
    return (directory / candidate).resolve()


def load_image(path, flags=cv.IMREAD_UNCHANGED):
    resolved = resolve_asset_path(path)
    image = _ORIGINAL_CV_IMREAD(str(resolved), flags)
    if image is None:
        raise FileNotFoundError(f"Image not found or unreadable: {resolved}")
    return image


def _template_scales():
    explicit = os.environ.get("CHADBOT_TEMPLATE_SCALES")
    if explicit:
        scales = []
        for item in explicit.split(","):
            item = item.strip().lower()
            if not item:
                continue
            if "x" in item:
                sx, sy = item.split("x", 1)
                scales.append((float(sx), float(sy)))
            else:
                scale = float(item)
                scales.append((scale, scale))
    else:
        sx, sy = coordinate_scale()
        average = (sx + sy) / 2
        scales = [(1.0, 1.0), (sx, sy), (average, average), (sx, sx), (sy, sy)]
    normalized = []
    for sx, sy in scales:
        rounded = (round(sx, 3), round(sy, 3))
        if rounded[0] > 0 and rounded[1] > 0 and rounded not in normalized:
            normalized.append(rounded)
    return normalized


def _resize_template(template, scale):
    sx, sy = scale
    if sx == 1.0 and sy == 1.0:
        return template
    width = max(1, int(round(template.shape[1] * sx)))
    height = max(1, int(round(template.shape[0] * sy)))
    return cv.resize(template, (width, height), interpolation=getattr(cv, "INTER_AREA", cv.INTER_CUBIC))


def _best_template_match(haystack, needle, method=cv.TM_CCOEFF_NORMED):
    best = None
    for scale in _template_scales():
        scaled_needle = _resize_template(needle, scale)
        if scaled_needle.shape[0] > haystack.shape[0] or scaled_needle.shape[1] > haystack.shape[1]:
            continue
        result = cv.matchTemplate(haystack, scaled_needle, method)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)
        sqdiff_methods = {getattr(cv, "TM_SQDIFF", None), getattr(cv, "TM_SQDIFF_NORMED", None)}
        score = max_val if method not in sqdiff_methods else -min_val
        if best is None or score > best["score"]:
            best = {
                "score": score,
                "min_val": min_val,
                "max_val": max_val,
                "min_loc": min_loc,
                "max_loc": max_loc,
                "needle": scaled_needle,
                "scale": scale,
            }
    if best is None:
        raise ValueError("Template is larger than the search area at every candidate scale.")
    return best


def move_to(x, y=None, duration=0, *args, **kwargs):
    if y is None and isinstance(x, (tuple, list)):
        x, y = x
    sx, sy = scale_point(x, y)
    return _ORIGINAL_PAG_MOVE_TO(sx, sy, duration, *args, **kwargs)


def move_relative(x_offset=0, y_offset=0, duration=0, *args, **kwargs):
    if _ORIGINAL_PAG_MOVE is None:
        raise AttributeError("pyautogui.move is unavailable.")
    sx, sy = scale_delta(x_offset, y_offset)
    return _ORIGINAL_PAG_MOVE(sx, sy, duration, *args, **kwargs)


def click(x=None, y=None, *args, **kwargs):
    if y is None and isinstance(x, (tuple, list)):
        x, y = x
    if x is not None and y is not None:
        x, y = scale_point(x, y)
        return _ORIGINAL_PAG_CLICK(x, y, *args, **kwargs)
    return _ORIGINAL_PAG_CLICK(x=x, y=y, *args, **kwargs)


def right_click(x=None, y=None, *args, **kwargs):
    if y is None and isinstance(x, (tuple, list)):
        x, y = x
    if x is not None and y is not None:
        x, y = scale_point(x, y)
        return _ORIGINAL_PAG_RIGHT_CLICK(x, y, *args, **kwargs)
    return _ORIGINAL_PAG_RIGHT_CLICK(x=x, y=y, *args, **kwargs)


def double_click(x=None, y=None, *args, **kwargs):
    if y is None and isinstance(x, (tuple, list)):
        x, y = x
    if x is not None and y is not None:
        x, y = scale_point(x, y)
        return _ORIGINAL_PAG_DOUBLE_CLICK(x, y, *args, **kwargs)
    return _ORIGINAL_PAG_DOUBLE_CLICK(x=x, y=y, *args, **kwargs)


def screenshot(imageFilename=None, region=None, *args, **kwargs):
    if region is not None:
        kwargs["region"] = scale_region(region)
    if imageFilename is not None:
        imageFilename = resolve_output_path(imageFilename)
    image = _ORIGINAL_PAG_SCREENSHOT(*args, **kwargs)
    if imageFilename is not None:
        if hasattr(image, "save"):
            image.save(imageFilename)
        else:
            Image.fromarray(np.asarray(image)).save(imageFilename)
    return image


def pixel(x, y):
    if _ORIGINAL_PAG_PIXEL is None:
        raise AttributeError("pyautogui.pixel is unavailable.")
    sx, sy = scale_point(x, y)
    return _ORIGINAL_PAG_PIXEL(sx, sy)


def pixel_matches_color(x, y, expected_rgb_color, tolerance=0):
    if _ORIGINAL_PAG_PIXEL_MATCHES_COLOR is None:
        raise AttributeError("pyautogui.pixelMatchesColor is unavailable.")
    sx, sy = scale_point(x, y)
    return _ORIGINAL_PAG_PIXEL_MATCHES_COLOR(sx, sy, expected_rgb_color, tolerance=tolerance)


def _cv_imread_compat(filename, flags=None):
    if flags is None:
        flags = getattr(cv, "IMREAD_COLOR", 1)
    try:
        filename = str(resolve_asset_path(filename))
    except (FileNotFoundError, TypeError):
        pass
    return _ORIGINAL_CV_IMREAD(filename, flags)


def install_portability_shims():
    if getattr(pag, "_chadbot_portability_shims", False):
        return
    pag.moveTo = move_to
    if _ORIGINAL_PAG_MOVE is not None:
        pag.move = move_relative
    pag.click = click
    pag.rightClick = right_click
    pag.doubleClick = double_click
    pag.screenshot = screenshot
    if _ORIGINAL_PAG_PIXEL is not None:
        pag.pixel = pixel
    if _ORIGINAL_PAG_PIXEL_MATCHES_COLOR is not None:
        pag.pixelMatchesColor = pixel_matches_color
    cv.imread = _cv_imread_compat
    pag._chadbot_portability_shims = True


install_portability_shims()


def r(a=0.25, b=0.75):  # Define function and define numbers
    """ Function returns a random number between a and b"""
    return random.uniform(a, b)  # Return numbers


def p(a=3, b=None):  # Define function and define numbers
    """ This function returns a random integer between a and b or -a and a, if b isn't specified"""
    if b is None:
        return random.randint(-a, a)  # Return integers
    else:
        return random.randint(a, b)


def initialize_pag():
    """ Function simply enables the pag failsafe"""
    pag.FAILSAFE = True  # Turn on failsafe
    print('Pyautogui failsafe enabled!')


def countdown(seconds=3):
    """ This function starts a simple countdown timer"""
    print(f'Starting', end='')
    for s in range(1, seconds + 1):
        print('.', end='')
        time.sleep(1)
    print(' now!')


def take_screenshot(area=(0, 0, 1920, 1080), save_img=False, img_name='screenshot.png'):
    """ This function takes a screenshot of a specified area of the screen and returns it ready for match template."""
    screenshot = pag.screenshot(region=area)
    if save_img:
        screenshot.save(resolve_output_path(img_name))
    screenshot = np.array(screenshot)
    screenshot = cv.cvtColor(screenshot, cv.COLOR_RGB2BGR)
    return screenshot


def isolate_exact_yellow(bgr_image, tolerance=10):
    """
    Keep only pixels that are very close to pure yellow (BGR 255,255,0)
    tolerance: how many HSV units around the exact yellow to allow
    """
    # Convert BGR to HSV
    hsv = cv.cvtColor(bgr_image, cv.COLOR_BGR2HSV)

    # Pure yellow in BGR is (0, 255, 255) in HSV
    # Hue for yellow ~30, Saturation ~255, Value ~255
    # We'll allow a small tolerance for Hue/Sat/Val
    lower_yellow = np.array([30 - tolerance, 255 - tolerance, 255 - tolerance])
    upper_yellow = np.array([30 + tolerance, 255, 255])  # keep saturation/value at max

    # Create mask
    mask = cv.inRange(hsv, lower_yellow, upper_yellow)

    # Apply mask: keep yellow, black out everything else
    result = cv.bitwise_and(bgr_image, bgr_image, mask=mask)

    # Convert to grayscale
    gray = cv.cvtColor(result, cv.COLOR_BGR2GRAY)

    # Threshold to pure black and white
    _, thresh = cv.threshold(gray, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)

    return thresh


def prep_for_ocr(img):
    """Very simple preprocessing for single-color text on dark background."""
    # 1. Convert to grayscale
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    # 2. Small blur for stability (optional but helps)
    gray = cv.GaussianBlur(gray, (3, 3), 0)

    # 3. Otsu threshold — automatically separates bright text from dark bg
    _, thresh = cv.threshold(gray, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)

    # 4. Invert: text = white, background = black (OCR prefers this)
    thresh = 255 - thresh

    return thresh


def to_pil_and_resize(cv_image, x=5, y=5, resize=True):
    """Convert OpenCV grayscale/BGR image to PIL Image for pytesseract."""
    if resize:
        cv_image = cv.resize(cv_image, None, fx=x, fy=y, interpolation=cv.INTER_CUBIC)
    if len(cv_image.shape) == 2:  # grayscale
        return Image.fromarray(cv_image)
    else:  # BGR
        rgb_image = cv.cvtColor(cv_image, cv.COLOR_BGR2RGB)
        return Image.fromarray(rgb_image)


def move_click(x, y, move_duration=None, wait_duration=None, r1=None, r2=None, double_click=False):
    """ This function takes in x and y coordinates, and a movement and wait duration and executes actions."""
    move_duration = r() if move_duration is None else move_duration
    wait_duration = r() if wait_duration is None else wait_duration
    r1 = p() if r1 is None else r1
    r2 = p() if r2 is None else r2
    pag.moveTo(x + r1, y + r2, move_duration)
    if double_click:
        pag.doubleClick()
    else:
        pag.click()
    time.sleep(wait_duration)


def move_right_click(x, y, move_duration=None, wait_duration=None, r1=None, r2=None):
    """ This function takes in x and y coordinates, and a movement and wait duration and executes actions."""
    move_duration = r() if move_duration is None else move_duration
    wait_duration = r() if wait_duration is None else wait_duration
    r1 = p() if r1 is None else r1
    r2 = p() if r2 is None else r2
    pag.moveTo(x + r1, y + r2, move_duration)
    pag.rightClick()
    time.sleep(wait_duration)


def find_option(option_img, xy=(100, 100), search_window=(150, 50, 300, 300), t=0.88, test=False, img_name='s'):

    move_right_click(*xy)
    x = xy[0] - search_window[0] if xy[0] - search_window[0] >= 0 else 0
    y = xy[1] - search_window[1] if xy[1] - search_window[1] >= 0 else 0

    option = find(option_img, (x, y, search_window[2], search_window[3]), threshold=t,
                  save_img=test, img_name=img_name)
    return option
    # print(option)
    # move_click(option[0], option[1])
    # time.sleep(5 + r())


def check_pixel_color_in_area(
    search_region=(960, 540, 6, 6),
    target_color=(0, 255, 0),
    tolerance=5):
    """
    Checks if the target color exists within the specified area of the screen.
    Same behavior as the slow pixel-by-pixel version, but much faster.
    """
    x, y, w, h = search_region

    # 1. Grabs the region ONCE (instead of calling pixelMatchesColor repeatedly)
    img = pag.screenshot(region=(x, y, w, h))

    # 2. Convert image to NumPy array (H, W, 3)
    arr = np.array(img).astype(np.int16)

    # 3. Calculate absolute difference
    # arr is RGB, but pyautogui.pixelMatchesColor uses RGB too
    diff = np.abs(arr - np.array(target_color, dtype=np.int16))

    # 4. Check if all 3 channels are within tolerance
    match = np.all(diff <= tolerance, axis=2)

    # 5. Return True if ANY pixel matches
    return bool(np.any(match))


def find(locate_img, area=(0, 0, 1920, 1080), threshold=0.50, save_img=False, img_name='screenshot.png'):
    """ This function takes in the name of an image file to search, and the search region, it will find the best
    match for the image within the taken screenshot. It returns the x and y coordinates for the location of the best
    match on screen."""
    haystack = take_screenshot(area, save_img=save_img, img_name=img_name)
    needle = load_image(locate_img, getattr(cv, "IMREAD_UNCHANGED", -1))
    best = _best_template_match(haystack, needle)
    if threshold is None or best["max_val"] > threshold:
        needle_w = round(best["needle"].shape[1] / 2)
        needle_h = round(best["needle"].shape[0] / 2)
        actual_area = scale_region(area)
        actual_location = (
            best["max_loc"][0] + needle_w + actual_area[0],
            best["max_loc"][1] + needle_h + actual_area[1],
        )
        return unscale_point(*actual_location)
    return None


def find_spots(locate_img, threshold=0.50, area=(0, 0, 1920, 1080)):
    """ This function takes in the name of an image file to search, and threshold for image recognition. It will return
    the locations of every match above the threshold."""
    haystack = take_screenshot(area)
    needle = load_image(locate_img, getattr(cv, "IMREAD_UNCHANGED", -1))
    locations = []
    for scale in _template_scales():
        scaled_needle = _resize_template(needle, scale)
        if scaled_needle.shape[0] > haystack.shape[0] or scaled_needle.shape[1] > haystack.shape[1]:
            continue
        result = cv.matchTemplate(haystack, scaled_needle, cv.TM_CCOEFF_NORMED)
        matches = np.where(result > threshold)
        locations.extend(unscale_point(x, y) for x, y in zip(*matches[::-1]))
    if locations:
        return sorted(set(locations))
    return None


def create_rectangles(locate_img, coordinates, group_threshold=1, eps=0.50):
    """ This function takes in the name of an image to read, coordinates for locations, and function parameters. It then
    creates and returns a list of lists containing the x and y coordinates and height and width of the rectangles."""
    if coordinates is None or len(coordinates) == 0:
        return []
    needle = load_image(locate_img, getattr(cv, "IMREAD_UNCHANGED", -1))
    rectangles = []
    for loc in coordinates:
        rect = [int(loc[0]), int(loc[1]), needle.shape[1], needle.shape[0]]
        rectangles.append(rect)
        rectangles.append(rect)
    rectangles, weights = cv.groupRectangles(rectangles, group_threshold, eps)
    return rectangles


def draw_rectangles(haystack, locations, show=True):
    """ This function takes in an imread image and a list of rectangles and draws and draws a rectangle around
    each search result."""
    if locations is not None and len(locations):
        line_color = (0, 0, 255)
        line_type = cv.LINE_4

        for (x, y, w, h) in locations:
            top_left = (x, y)
            bottom_right = (x + w, y + h)
            cv.rectangle(haystack, top_left, bottom_right, line_color, line_type)
        if show:
            cv.imshow('Matches', haystack)
            cv.waitKey()
    else:
        print('No matches :(')


def draw_markers(haystack, rectangles, show=True):
    """ This function takes in an imread image and a list of rectangles and draws and draws a marker on
        each search result."""
    if rectangles is not None and len(rectangles):
        marker_color = (255, 0, 255)
        marker_type = cv.MARKER_CROSS
        for (x, y, w, h) in rectangles:
            center = ((x + int(w/2)), y + int(h/2))
            cv.drawMarker(haystack, center, marker_color, marker_type)
        if show:
            cv.imshow('Matches', haystack)
            cv.waitKey()
    else:
        print('No matches :(')


def shift_camera_direction(direction='north', up=True):
    """ This function shifts the camera direction to a specific direction and can zoom out all the way."""
    pag.moveTo(1725 + p(-8, 8), 52 + p(-8, 8), r(0.25, 0.50))
    time.sleep(r(0.15, 0.20))
    if direction == 'north':
        pag.click()
    elif direction == 'east':
        pag.rightClick()
        time.sleep(r(0.10, 0.30))
        pag.move(0 + p(-5, 5), 42 + p(), r(0.15, 0.30))
        time.sleep(r(0.10, 0.30))
        pag.click()
    elif direction == 'south':
        pag.rightClick()
        time.sleep(r(0.10, 0.30))
        pag.move(0 + p(-5, 5), 57 + p(), r(0.15, 0.30))
        time.sleep(r(0.10, 0.30))
        pag.click()
    elif direction == 'west':
        pag.rightClick()
        time.sleep(r(0.10, 0.30))
        pag.move(0 + p(-5, 5), 72 + p(), r(0.15, 0.30))
        time.sleep(r(0.10, 0.30))
        pag.click()
    time.sleep(r(0.25, 1.5))
    if up:
        pag.keyDown('up')
        time.sleep(2)
        pag.keyUp('up')


def create_inv_grid(tl=(1683, 746), br=(1851, 998), rows=7, columns=4):
    grid = {}
    cell_w = int((br[0] - tl[0]) / columns)
    cell_h = int((br[1] - tl[1]) / rows)
    count = 0
    for row in range(tl[1], br[1], cell_h):
        for column in range(tl[0], br[0], cell_w):
            count += 1
            grid[f'Slot {count}'] = int(round(column + cell_w/2)), int(round(row + cell_h/2))
    return grid


def create_inv(n=28):
    inventory = create_inv_grid()
    inventory = dict(list(inventory.items())[:n])
    return inventory


def full_inventory():
    inv = create_inv(28)
    for cx, cy in inv.values():
        x = cx - 7
        y = cy - 8
        img = take_screenshot(area=(x, y, 20, 20))
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        if np.std(gray) < 2 or (gray.max() - gray.min()) < 5:
            return False  # found an empty slot
    return True  # no empty slots found


def slot_empty(slot=28, inv_size=28):
    inv = create_inv(inv_size)
    slot_xy = list(inv.items())[(slot - 1)][1]
    # print(slot_xy)
    x, y = slot_xy[0] - 7, slot_xy[1] - 8
    img = take_screenshot(area=(x, y, 20, 20))
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    if np.std(gray) < 2 or (gray.max() - gray.min()) < 5:
        return True  # found an empty slot
    return False  # no empty slots found
    # print(inv)


def wait_until(check_function, timeout=30, interval=0.25):
    start = time.time()
    while not check_function():
        if time.time() - start > timeout:
            raise TimeoutError("Condition was not met in time.")
        time.sleep(interval)
    return True


def convert_key(key):
    """ This function is a simple converter to translate pynput keys to pag readable keys"""
    key_map = {
        'alt_l': 'altleft',
        'alt_r': 'altright',
        'alt_gr': 'altright',
        'caps_lock': 'capslock',
        'ctrl_l': 'ctrlleft',
        'ctrl_r': 'ctrlright',
        'page_down': 'pagedown',
        'page_up': 'pageup',
        'shift_l': 'shiftleft',
        'shift_r': 'shiftright',
        'num_lock': 'numlock',
        'print_screen': 'printscreen',
        'scroll_lock': 'scrolllock'}
    # example: 'Key.F9' should return 'F9', 'w' should return as 'w'
    cleaned_key = key.replace('Key.', '')
    if cleaned_key in key_map:
        return key_map[cleaned_key]
    return cleaned_key


def play_actions(filename, new_path=None):
    """ This function reads json 'recording' files"""
    previous_position = None
    filepath = resolve_asset_path(filename, base_dir=new_path)
    with filepath.open('r', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        for index, action in enumerate(data):
            start_time = time.time()
            if action['button'] == 'Key.f10':
                break
            # Perform action
            elif action['type'] == 'KeyDown':
                key = convert_key(action['button'])
                # key = key[4:] if key[:4] == 'Key.' else key
                pag.keyDown(key)
            elif action['type'] == 'KeyUp':
                key = convert_key(action['button'])
                # key = key[4:] if key[:4] == 'Key.' else key
                pag.keyUp(key)

            elif action['type'] == 'clickDown':
                previous_position = (action['pos'][0], action['pos'][1])
                pag.moveTo(action['pos'][0] + p(-4, 4), action['pos'][1] + p(-4, 4), duration=r(0.25, 0.70))
                pag.mouseDown()
            elif action['type'] == 'clickUp':
                if previous_position == (action['pos'][0], action['pos'][1]):
                    pag.mouseUp()
                else:
                    pag.moveTo(action['pos'][0] + p(-4, 4), action['pos'][1] + p(-4, 4), duration=r(0.25, 1.00))
                    pag.mouseUp()

            # Sleep until next action
            try:
                next_action = data[index + 1]
            except IndexError:
                break
            elapsed_time = time.time() - start_time
            wait_time = next_action['time'] - action['time']
            if wait_time >= 0:
                wait_time -= elapsed_time
                if wait_time < 0:
                    wait_time = 0
                if action['type'] == 'clickDown':
                    time.sleep(wait_time)
                else:
                    time.sleep(wait_time + r(0, 0.30))
            else:
                raise Exception('Unexpected action ordering.')


class WindowCapture:

    # Properties
    w = 0
    h = 0
    hwnd = None
    cropped_x = 0
    cropped_y = 0
    offset_x = 0
    offset_y = 0

    def __init__(self, window_name=None, area=(0, 0, 1920, 1080)):

        # Determine hwnd (window name)
        if window_name is None:
            self.hwnd = win32gui.GetDesktopWindow()
        else:
            self.hwnd = win32gui.FindWindow(None, window_name)
            if not self.hwnd:
                raise Exception(f'Window not found: {window_name}')

        # account for the window border and titlebar and cut them off if window name
        if window_name:
            window_rect = win32gui.GetWindowRect(self.hwnd)
            print(window_rect)
            self.w = window_rect[2] - window_rect[0]
            self.h = window_rect[3] - window_rect[1]
            border_pixels = 8
            titlebar_pixels = 30
            self.w = self.w - (border_pixels * 2)
            self.h = self.h - titlebar_pixels - border_pixels
            self.cropped_x = border_pixels
            self.cropped_y = titlebar_pixels
            # set the cropped coordinates offset, so we can translate screenshot
            # images into actual screen positions
            self.offset_x = window_rect[0] + self.cropped_x
            self.offset_y = window_rect[1] + self.cropped_y
        else:
            # area = ( x coordinate, y coordinate, width of area, height of area)
            scaled_area = scale_region(area)
            self.w, self.h, self.cropped_x, self.cropped_y = (
                scaled_area[2],
                scaled_area[3],
                scaled_area[0],
                scaled_area[1],
            )
            self.offset_x = self.cropped_x
            self.offset_y = self.cropped_y

    def get_screenshot(self):
        # screenshot_name = "debug.bmp"  # set this
        # get the window image data
        wDC = win32gui.GetWindowDC(self.hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, self.w, self.h)
        cDC.SelectObject(dataBitMap)
        cDC.BitBlt((0, 0), (self.w, self.h), dcObj, (self.cropped_x, self.cropped_y), win32con.SRCCOPY)

        # save screenshot
        # dataBitMap.SaveBitmapFile(cDC, screenshot_name)
        signedIntsArray = dataBitMap.GetBitmapBits(True)
        screencapture = np.frombuffer(signedIntsArray, dtype='uint8')
        screencapture.shape = (self.h, self.w, 4)

        # Free Resources
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())

        # drop the alpha channel, or cv.matchTemplate() will throw an error like:
        #   error: (-215:Assertion failed) (depth == CV_8U || depth == CV_32F) && type == _templ.type()
        #   && _img.dims() <= 2 in function 'cv::matchTemplate'
        screencapture = screencapture[..., :3]

        # make image C_CONTIGUOUS to avoid errors that look like:
        #   File ... in draw_rectangles
        #   TypeError: an integer is required (got type tuple)
        # see the discussion here:
        # https://github.com/opencv/opencv/issues/14866#issuecomment-580207109
        screencapture = np.ascontiguousarray(screencapture)
        return screencapture

    @staticmethod
    def list_window_names():
        def winEnumHandler(hwnd):
            if win32gui.IsWindowVisible(hwnd):
                print(hex(hwnd), win32gui.GetWindowText(hwnd))

        win32gui.EnumWindows(winEnumHandler, None)

    # translate a pixel position on a screenshot image to a pixel position on the screen.
    # pos = (x, y)
    # WARNING: if you move the window being captured after execution is started, this will
    # return incorrect coordinates, because the window position is only calculated in
    # the __init__ constructor.
    def get_screen_position(self, pos):
        return pos[0] + self.offset_x, pos[1] + self.offset_y


class Vision:

    # properties
    needle_img = None
    needle_w = 0
    needle_h = 0
    method = None

    # constructor
    def __init__(self, needle_img_path, method=cv.TM_CCOEFF_NORMED):
        # load the image we're trying to match
        # https://docs.opencv.org/4.2.0/d4/da8/group__imgcodecs.html
        self.needle_img = load_image(needle_img_path, getattr(cv, "IMREAD_UNCHANGED", -1))

        # Save the dimensions of the needle image
        self.needle_w = self.needle_img.shape[1]
        self.needle_h = self.needle_img.shape[0]

        # There are 6 methods to choose from:
        # TM_CCOEFF, TM_CCOEFF_NORMED, TM_CCORR, TM_CCORR_NORMED, TM_SQDIFF, TM_SQDIFF_NORMED
        self.method = method

    def find(self, haystack_img, threshold=0.5, debug_mode=None):
        # Run the match at the current screen scale so templates recorded at
        # 1920x1080 still work on smaller or larger displays.
        rectangles = []
        for scale in _template_scales():
            needle = _resize_template(self.needle_img, scale)
            if needle.shape[0] > haystack_img.shape[0] or needle.shape[1] > haystack_img.shape[1]:
                continue
            result = cv.matchTemplate(haystack_img, needle, self.method)
            locations = np.where(result >= threshold)
            for loc in zip(*locations[::-1]):
                rect = [int(loc[0]), int(loc[1]), needle.shape[1], needle.shape[0]]
                # Add every box twice so groupRectangles keeps single, non-overlapping boxes.
                rectangles.append(rect)
                rectangles.append(rect)

        rectangles, weights = cv.groupRectangles(rectangles, groupThreshold=1, eps=0.5)

        points = []
        if len(rectangles):
            line_color = (0, 255, 0)
            line_type = cv.LINE_4
            marker_color = (255, 0, 255)
            marker_type = cv.MARKER_CROSS

            # Loop over all the rectangles
            for (x, y, w, h) in rectangles:

                # Determine the center position
                center_x = x + int(w/2)
                center_y = y + int(h/2)
                # Save the points
                points.append(unscale_point(center_x, center_y))

                if debug_mode == 'rectangles':
                    # Determine the box position
                    top_left = (x, y)
                    bottom_right = (x + w, y + h)
                    # Draw the box
                    cv.rectangle(haystack_img, top_left, bottom_right, color=line_color,
                                 lineType=line_type, thickness=2)
                elif debug_mode == 'points':
                    # Draw the center point
                    cv.drawMarker(haystack_img, (center_x, center_y),
                                  color=marker_color, markerType=marker_type,
                                  markerSize=40, thickness=2)

        if debug_mode:
            cv.imshow('Matches', haystack_img)
            # cv.waitKey()
            # cv.imwrite('result_click_point.jpg', haystack_img)

        return points
