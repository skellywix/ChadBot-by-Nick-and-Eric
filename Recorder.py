from argparse import ArgumentParser
from pathlib import Path
from pynput import mouse, keyboard
from time import time
import json
import os


OUTPUT_FILENAME = 'bank_fish'
# Declare mouse_listener globally so that keyboard on release can stop it
mouse_listener = None
# Declare start_time globally so that the callback functions can reference it
start_time = None
# Keep track of unreleased keys to prevent over_reporting press events
unreleased_keys = []
# Storing all input events
input_events = []
# Store click event
unreleased_click = False
DISABLE_SCALING = os.environ.get("CHADBOT_DISABLE_SCALING", "").lower() in {"1", "true", "yes", "on"}


def env_positive_int(name, default):
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


BASE_WIDTH = env_positive_int("CHADBOT_BASE_WIDTH", 1920)
BASE_HEIGHT = env_positive_int("CHADBOT_BASE_HEIGHT", 1080)


class EventType:
    KEYDOWN = 'KeyDown'
    KEYUP = 'KeyUp'
    CLICKDOWN = 'clickDown'
    CLICKUP = 'clickUp'
    MOUSEMOVE = 'moveTo'


def record_event(event_type, event_time, button, pos=None):
    global input_events
    input_events.append({'time': event_time,
                         'type': event_type,
                         'button': str(button),
                         'pos': pos})
    if event_type == EventType.CLICKDOWN or event_type == EventType.CLICKUP:
        print(f'{event_type} on {button} pos {pos} at {event_time}')
    else:
        print(f'{event_type} on {button} at {event_time}')


def normalize_position(x, y):
    if DISABLE_SCALING:
        return int(round(x)), int(round(y))
    try:
        import pyautogui as pag

        size = pag.size()
        width = int(size.width) if hasattr(size, "width") else int(size[0])
        height = int(size.height) if hasattr(size, "height") else int(size[1])
    except Exception:
        return int(round(x)), int(round(y))
    if width <= 0 or height <= 0:
        return int(round(x)), int(round(y))
    return int(round(x * BASE_WIDTH / width)), int(round(y * BASE_HEIGHT / height))


def on_press(key):
    # We only want to record first key press event until that key has been released
    global unreleased_keys
    if key in unreleased_keys:
        return
    else:
        unreleased_keys.append(key)
    try:
        record_event(EventType.KEYDOWN, elapsed_time(), key.char)
    except AttributeError:
        record_event(EventType.KEYDOWN, elapsed_time(), key)


def on_release(key):
    # Mark key as no longer pressed
    global unreleased_keys
    try:
        unreleased_keys.remove(key)
    except ValueError:
        print(f'ERROR: {key} not in unreleased_keys')
    try:
        record_event(EventType.KEYUP, elapsed_time(), key.char)
    except AttributeError:
        record_event(EventType.KEYUP, elapsed_time(), key)

    if key == keyboard.Key.f10:
        # Stop mouse listener
        mouse_listener.stop()
        # Stop keyboard listener
        return False
        # raise keyboard.Listener.StopException


def on_click(x, y, button, pressed):
    pos = normalize_position(x, y)
    if pressed:
        record_event(EventType.CLICKDOWN, elapsed_time(), button, pos)
    if not pressed:
        record_event(EventType.CLICKUP, elapsed_time(), button, pos)


def run_listeners():
    global mouse_listener
    global start_time
    start_time = time()
    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()
    mouse_listener.wait()

    with keyboard.Listener(
            on_press=on_press,
            on_release=on_release) as listener:
        listener.join()


def elapsed_time():
    global start_time
    if start_time is None:
        return 0
    return time() - start_time


def parse_args():
    parser = ArgumentParser(description="Record mouse and keyboard events to a JSON playback file.")
    parser.add_argument(
        "-o",
        "--output",
        default=OUTPUT_FILENAME,
        help="Output filename without .json. Defaults to bank_fish.",
    )
    return parser.parse_args()


def build_output_path(output_filename, output_dir=None):
    output_dir = Path(output_dir) if output_dir else Path(__file__).resolve().parent / 'Recordings'
    output_name = Path(output_filename)
    if (
        output_name.is_absolute()
        or output_name.parent != Path('.')
        or not output_name.name
        or output_name.name in {'.', '..'}
    ):
        raise ValueError("Output must be a filename, not a path.")
    if output_name.suffix != '.json':
        output_name = output_name.with_name(f'{output_name.name}.json')
    return output_dir / output_name.name


def main(output_filename=OUTPUT_FILENAME):
    run_listeners()
    print(f'Recording duration: {elapsed_time()} seconds')
    global input_events
    print(json.dumps(input_events))

    filepath = build_output_path(output_filename)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open('w', encoding='utf-8') as outfile:
        json.dump(input_events, outfile, indent=4)


if __name__ == "__main__":
    args = parse_args()
    main(args.output)
