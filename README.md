# ChadBot by Nick and Eric

ChadBot is a local control center for Windows desktop automation scripts built around PyAutoGUI, OpenCV template matching, and keyboard/mouse recording playback.

The scripts appear to target RuneLite / Old School RuneScape workflows. They move the mouse, click UI elements, read pixels, match screenshots against image templates, replay recorded inputs, and in a few places extract digits from world-list screenshots.

The project now includes a browser-based UI so the bot can be edited, validated, started, stopped, and monitored without opening an IDE.

## ChadBot UI

Start the local control center:

```powershell
python -m chadbot.server
```

Then open:

```text
http://127.0.0.1:8765
```

The UI provides:

- Script discovery across the core scripts and `scripts/` activity folders.
- Start and stop controls for bot scripts.
- Live stdout/stderr logs from the running bot process.
- A file tree and editor for safe in-repo changes to `.py`, `.json`, `.txt`, `.md`, `.toml`, `.yaml`, `.yml`, `.html`, `.css`, and `.js` files.
- Save and revert controls for fast bot iteration.
- One-click `Pytest` and `Compile` validation.

Safety boundaries:

- The UI runs locally by default on `127.0.0.1`.
- Non-loopback hosts require an explicit `--allow-remote` flag because the UI can edit files and start scripts.
- Script execution is limited to discovered Python bot scripts in the repository.
- File editing is constrained to allowed text/code extensions inside the repository.
- Validation commands are allowlisted.
- No arbitrary shell command endpoint is exposed.

## What Is In The Repo

- `chadbot/`: local web control server and UI.
- `functions.py`: shared helper functions for screenshots, pixel checks, template matching, inventory-slot coordinates, recording playback, and Win32 window capture.
- `Recorder.py`: records mouse and keyboard events into JSON files under `Recordings/`. Press `F10` to stop recording.
- `world_hopper.py`: reads RuneLite world-list rows, filters candidate worlds by membership, activity, population, ping, and a local cooldown travel log.
- `digit_extractor.py`: small image-template digit reader used by the world hopper.
- `video_capture.py`: live OpenCV capture loop for detecting a template image on screen.
- `scripts/`: individual automation scripts for activities such as agility courses, fishing, mining, construction, blast furnace, world hopping support, and inventory sorting.
- `testing/` and `opencv/`: older experiments and learning scripts.

## Safety And Usage Notes

These scripts can click, type, scroll, and move the mouse on your active desktop. Run them only in a controlled local environment.

- PyAutoGUI's fail-safe is enabled by `functions.initialize_pag()`. Move the mouse to a screen corner to interrupt PyAutoGUI actions.
- Bot coordinates are treated as a 1920x1080 baseline and are scaled at runtime to the current screen size.
- Image templates and recordings are resolved from the script folder, current working directory, or repository root, so scripts can be started from the UI or from another folder.
- RuneLite UI layout, client zoom, plugin overlays, and inventory/bank positions still need to be consistent with the template images each script uses.
- Automation may violate the rules or terms of the software or service being automated. Confirm permission before using these scripts.

## Portability Controls

`functions.py` installs compatibility shims when imported by a script. Existing raw `pyautogui.moveTo`, `click`, `rightClick`, `doubleClick`, `screenshot`, `pixel`, `pixelMatchesColor`, and `cv2.imread` calls then use the same path resolution and coordinate scaling as the shared helpers.

Default coordinate baseline:

```text
1920x1080
```

Override it only when a script was authored against a different baseline:

```powershell
$env:CHADBOT_BASE_WIDTH = "2560"
$env:CHADBOT_BASE_HEIGHT = "1440"
```

Disable scaling for troubleshooting:

```powershell
$env:CHADBOT_DISABLE_SCALING = "1"
```

OpenCV matching tries the current screen scale automatically. To force specific template scales:

```powershell
$env:CHADBOT_TEMPLATE_SCALES = "1,0.75,1.25,0.75x0.8"
```

When scripts are started from the ChadBot UI, the process also receives:

- `CHADBOT_REPO_ROOT`
- `CHADBOT_SCRIPT_DIR`
- `CHADBOT_SCRIPT_PATH`

## Setup

Use Python 3.10+ on Windows.

```powershell
cd C:\Users\Eric\Desktop\Pyautogui
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Some OCR scripts use `pytesseract`, which also requires the Tesseract OCR application installed on the machine and available on `PATH`.

## Recording And Playback

Record a new action sequence:

```powershell
python Recorder.py --output bank_fish
```

Stop with `F10`. The file is written to `Recordings\bank_fish.json`.

Replay a recording from Python:

```python
import functions as f

f.initialize_pag()
f.countdown(3)
f.play_actions("Recordings/bank_fish.json")
```

For script-local recordings:

```python
from pathlib import Path
import functions as f

script_dir = Path(__file__).resolve().parent
f.play_actions("bank_fish.json", new_path=script_dir)
```

## Development

Run the lightweight regression tests:

```powershell
python -m pytest
```

Run a syntax check across the repository:

```powershell
python -m compileall -q .
```

The tests stub GUI dependencies so they can run on machines without PyAutoGUI, pywin32, or OpenCV installed.
