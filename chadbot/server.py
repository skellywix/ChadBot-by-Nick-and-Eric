"""Local web control server for ChadBot.

The server intentionally uses only the Python standard library so the UI can
run before the automation dependencies are installed.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import math
import mimetypes
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import parse_qs, unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = Path(__file__).resolve().parent / "ui"
RUNTIME_ROOT = Path(__file__).resolve().parent / "runtime"
SETTINGS_PATH = RUNTIME_ROOT / "settings.json"

EDITABLE_EXTENSIONS = {
    ".json",
    ".md",
    ".css",
    ".html",
    ".js",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "venv",
}
CORE_SCRIPTS = ("Recorder.py", "video_capture.py", "world_hopper.py")
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
DEFAULT_BASE_WIDTH = 1920
DEFAULT_BASE_HEIGHT = 1080
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off", ""}
IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png"}
SCRIPT_ASSET_EXTENSIONS = IMAGE_EXTENSIONS | {".csv", ".json", ".txt"}
READ_PATH_CALLS = {
    "cv.imread",
    "cv2.imread",
    "f.find",
    "f.find_all",
    "f.find_option",
    "f.find_spots",
    "f.play_actions",
    "functions.find",
    "functions.find_all",
    "functions.find_option",
    "functions.find_spots",
    "functions.play_actions",
    "open",
}
WRITE_PATH_CALLS = {
    "cv.imwrite",
    "cv2.imwrite",
    "pag.screenshot",
    "pyautogui.screenshot",
}
FOLDER_PATH_CALLS = {
    "os.listdir",
}
REQUIREMENTS_FILES = (REPO_ROOT / "requirements.txt", REPO_ROOT / "requirements-dev.txt")
RUNTIME_DEPENDENCIES = (
    {"id": "pyautogui", "label": "PyAutoGUI", "module": "pyautogui", "required": True},
    {"id": "opencv", "label": "OpenCV", "module": "cv2", "required": True},
    {"id": "numpy", "label": "NumPy", "module": "numpy", "required": True},
    {"id": "pillow", "label": "Pillow", "module": "PIL", "required": True},
    {"id": "pynput", "label": "pynput", "module": "pynput", "required": True},
    {"id": "pytesseract", "label": "pytesseract", "module": "pytesseract", "required": True},
    {"id": "pywin32", "label": "pywin32", "module": "win32gui", "required": True},
)


def env_positive_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def environment_default_settings() -> dict:
    template_scales = os.environ.get("CHADBOT_TEMPLATE_SCALES", "").strip()
    return {
        "baseWidth": env_positive_int("CHADBOT_BASE_WIDTH", DEFAULT_BASE_WIDTH),
        "baseHeight": env_positive_int("CHADBOT_BASE_HEIGHT", DEFAULT_BASE_HEIGHT),
        "disableScaling": normalize_bool(os.environ.get("CHADBOT_DISABLE_SCALING", ""), default=False),
        "templateScales": template_scales,
    }


def normalize_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in TRUE_VALUES:
            return True
        if lowered in FALSE_VALUES:
            return False
    raise ValueError("Disable scaling must be true or false.")


def _format_scale(value: float) -> str:
    return f"{value:g}"


def normalize_template_scales(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    normalized = []
    for item in text.split(","):
        item = item.strip().lower()
        if not item:
            continue
        try:
            if "x" in item:
                sx_raw, sy_raw = item.split("x", 1)
                sx = float(sx_raw)
                sy = float(sy_raw)
                if not math.isfinite(sx) or not math.isfinite(sy) or sx <= 0 or sy <= 0:
                    raise ValueError
                normalized.append(f"{_format_scale(sx)}x{_format_scale(sy)}")
            else:
                scale = float(item)
                if not math.isfinite(scale) or scale <= 0:
                    raise ValueError
                normalized.append(_format_scale(scale))
        except ValueError:
            raise ValueError("Template scales must be positive numbers like 1,0.75,1.25 or 0.75x0.8.")
    return ",".join(normalized)


def normalize_settings(payload: dict | None = None, defaults: dict | None = None) -> dict:
    if payload is not None and not isinstance(payload, dict):
        raise ValueError("Settings payload must be a JSON object.")
    source = {**(defaults or environment_default_settings()), **(payload or {})}
    try:
        base_width = int(source.get("baseWidth", DEFAULT_BASE_WIDTH))
        base_height = int(source.get("baseHeight", DEFAULT_BASE_HEIGHT))
    except (TypeError, ValueError):
        raise ValueError("Base width and height must be positive integers.")
    if base_width <= 0 or base_height <= 0:
        raise ValueError("Base width and height must be positive integers.")

    template_scales = normalize_template_scales(source.get("templateScales", ""))
    disable_scaling = normalize_bool(source.get("disableScaling", False))
    return {
        "baseWidth": base_width,
        "baseHeight": base_height,
        "disableScaling": disable_scaling,
        "templateScales": template_scales,
    }


def load_runtime_settings() -> dict:
    defaults = environment_default_settings()
    if not SETTINGS_PATH.exists():
        return normalize_settings(defaults)
    try:
        payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Settings file is invalid JSON: {SETTINGS_PATH}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Settings file must contain a JSON object.")
    return normalize_settings(payload, defaults=defaults)


def save_runtime_settings(payload: dict) -> dict:
    settings = normalize_settings(payload, defaults=environment_default_settings())
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings


def reset_runtime_settings() -> dict:
    if SETTINGS_PATH.exists():
        SETTINGS_PATH.unlink()
    return normalize_settings(environment_default_settings())


def apply_runtime_environment(env: dict, settings: dict) -> None:
    env["CHADBOT_BASE_WIDTH"] = str(settings["baseWidth"])
    env["CHADBOT_BASE_HEIGHT"] = str(settings["baseHeight"])
    env["CHADBOT_DISABLE_SCALING"] = "1" if settings["disableScaling"] else "0"
    template_scales = settings["templateScales"].strip()
    if template_scales:
        env["CHADBOT_TEMPLATE_SCALES"] = template_scales
    else:
        env.pop("CHADBOT_TEMPLATE_SCALES", None)


def portability_config(settings: dict | None = None) -> dict:
    settings = settings or load_runtime_settings()
    return {
        "baseWidth": settings["baseWidth"],
        "baseHeight": settings["baseHeight"],
        "scalingDisabled": settings["disableScaling"],
        "templateScales": settings["templateScales"] or "auto",
        "assetLookup": ["base_dir", "CHADBOT_SCRIPT_DIR", "caller", "cwd", "repo"],
        "repoRoot": str(REPO_ROOT),
        "settingsPath": str(SETTINGS_PATH),
    }


def module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def screen_size_probe() -> dict:
    try:
        import pyautogui  # type: ignore[import-not-found]

        size = pyautogui.size()
        if hasattr(size, "width") and hasattr(size, "height"):
            width, height = int(size.width), int(size.height)
        else:
            width, height = int(size[0]), int(size[1])
    except Exception as exc:
        return {"available": False, "error": str(exc)}
    return {"available": width > 0 and height > 0, "width": width, "height": height}


def status_from_checks(checks: list[dict]) -> str:
    statuses = {check["status"] for check in checks}
    if "error" in statuses:
        return "error"
    if "warn" in statuses:
        return "warn"
    return "ok"


def count_repo_files(extensions: set[str], roots: tuple[Path, ...] | None = None) -> int:
    roots = roots or (REPO_ROOT,)
    count = 0
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("**/*"):
            if not path.is_file():
                continue
            rel_parts = path.relative_to(REPO_ROOT).parts if is_relative_to(path.resolve(), REPO_ROOT) else path.parts
            if set(rel_parts) & EXCLUDED_DIRS:
                continue
            if path.suffix.lower() in extensions:
                count += 1
    return count


def runtime_directory_status() -> dict:
    target = RUNTIME_ROOT if RUNTIME_ROOT.exists() else RUNTIME_ROOT.parent
    writable = target.exists() and os.access(target, os.W_OK)
    return {
        "status": "ok" if writable else "warn",
        "label": "Runtime storage",
        "detail": f"Settings and logs use {RUNTIME_ROOT}",
    }


def runtime_diagnostics(
    module_checker=module_available,
    executable_checker=shutil.which,
    screen_probe=screen_size_probe,
) -> dict:
    settings = load_runtime_settings()
    scripts = discover_scripts()
    editable_files = discover_editable_files()
    dependencies = []
    missing_required = []
    checks = [
        {
            "status": "ok",
            "label": "Python runtime",
            "detail": f"{platform.python_version()} at {sys.executable}",
        }
    ]

    for dependency in RUNTIME_DEPENDENCIES:
        available = bool(module_checker(dependency["module"]))
        status = "ok" if available else "error" if dependency["required"] else "warn"
        dependencies.append({
            "id": dependency["id"],
            "label": dependency["label"],
            "module": dependency["module"],
            "required": dependency["required"],
            "status": status,
        })
        if not available and dependency["required"]:
            missing_required.append(dependency["label"])

    if missing_required:
        checks.append({
            "status": "error",
            "label": "Python packages",
            "detail": f"Missing: {', '.join(missing_required)}",
        })
    else:
        checks.append({
            "status": "ok",
            "label": "Python packages",
            "detail": f"{len(dependencies)} automation packages found",
        })

    tesseract_path = executable_checker("tesseract")
    checks.append({
        "status": "ok" if tesseract_path else "warn",
        "label": "Tesseract app",
        "detail": str(tesseract_path) if tesseract_path else "Not on PATH; OCR scripts may fail.",
    })

    screen = screen_probe()
    if screen.get("available"):
        width = int(screen["width"])
        height = int(screen["height"])
        scale_x = width / settings["baseWidth"]
        scale_y = height / settings["baseHeight"]
        screen.update({
            "baselineWidth": settings["baseWidth"],
            "baselineHeight": settings["baseHeight"],
            "scaleX": round(scale_x, 3),
            "scaleY": round(scale_y, 3),
        })
        checks.append({
            "status": "ok",
            "label": "Screen access",
            "detail": f"{width} x {height}; scale {scale_x:.2f} x {scale_y:.2f}",
        })
    else:
        screen.update({
            "baselineWidth": settings["baseWidth"],
            "baselineHeight": settings["baseHeight"],
        })
        checks.append({
            "status": "warn",
            "label": "Screen access",
            "detail": screen.get("error") or "PyAutoGUI screen size is unavailable.",
        })

    checks.append({
        "status": "ok" if scripts else "error",
        "label": "Script discovery",
        "detail": f"{len(scripts)} runnable scripts found",
    })
    checks.append(runtime_directory_status())

    assets = {
        "scripts": len(scripts),
        "editableFiles": len(editable_files),
        "imageFiles": count_repo_files(IMAGE_EXTENSIONS),
        "recordings": count_repo_files({".json"}, roots=(REPO_ROOT / "Recordings", REPO_ROOT / "scripts")),
    }
    return {
        "status": status_from_checks(checks),
        "generatedAt": time.time(),
        "environment": {
            "python": platform.python_version(),
            "executable": sys.executable,
            "platform": platform.platform(),
            "repoRoot": str(REPO_ROOT),
            "runtimeRoot": str(RUNTIME_ROOT),
        },
        "settings": settings,
        "screen": screen,
        "dependencies": dependencies,
        "assets": assets,
        "checks": checks,
    }


def setup_requirements_command() -> list[str]:
    missing_files = [path for path in REQUIREMENTS_FILES if not path.exists()]
    if missing_files:
        missing = missing_files[0].resolve()
        label = repo_relative(missing) if is_relative_to(missing, REPO_ROOT) else str(missing)
        raise FileNotFoundError(f"Missing requirements file: {label}")
    command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"]
    for path in REQUIREMENTS_FILES:
        command.extend(["-r", str(path)])
    return command


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def resolve_repo_path(relative_path: str) -> Path:
    if not relative_path:
        raise ValueError("Path is required.")
    candidate = Path(unquote(relative_path))
    if candidate.is_absolute():
        raise ValueError("Absolute paths are not allowed.")

    resolved = (REPO_ROOT / candidate).resolve()
    if not is_relative_to(resolved, REPO_ROOT):
        raise ValueError("Path must stay inside the repository.")

    parts = set(resolved.relative_to(REPO_ROOT).parts)
    if parts & EXCLUDED_DIRS:
        raise ValueError("Path points to an excluded directory.")
    return resolved


def validate_edit_path(relative_path: str, must_exist: bool = False) -> Path:
    path = resolve_repo_path(relative_path)
    if path.suffix.lower() not in EDITABLE_EXTENSIONS:
        raise ValueError(f"Editing {path.suffix or 'extensionless files'} is not allowed.")
    if must_exist and not path.exists():
        raise FileNotFoundError(f"File not found: {relative_path}")
    if must_exist and not path.parent.exists():
        raise FileNotFoundError(f"Directory not found: {repo_relative(path.parent)}")
    return path


def is_discoverable_script(path: Path, root: Path | None = None) -> bool:
    root = (root or REPO_ROOT).resolve()
    path = path.resolve()
    if path.suffix.lower() != ".py":
        return False
    if not is_relative_to(path, root):
        return False
    rel_parts = path.relative_to(root).parts
    if not rel_parts:
        return False
    if set(rel_parts) & EXCLUDED_DIRS:
        return False
    if rel_parts[0] == "scripts":
        return True
    return path.name in CORE_SCRIPTS


def discover_scripts(root: Path | None = None) -> list[dict]:
    root = (root or REPO_ROOT).resolve()
    scripts: list[Path] = []
    for name in CORE_SCRIPTS:
        script = root / name
        if script.exists():
            scripts.append(script)
    scripts.extend(sorted((root / "scripts").glob("**/*.py")) if (root / "scripts").exists() else [])

    items = []
    for script in sorted({path.resolve() for path in scripts}):
        if not is_relative_to(script, root) or not is_discoverable_script(script, root=root):
            continue
        rel = script.relative_to(root).as_posix()
        rel_parts = Path(rel).parts
        group = "Core" if rel_parts[0] != "scripts" else rel_parts[1].replace("_", " ").title()
        items.append(
            {
                "id": rel,
                "name": script.stem.replace("_", " ").title(),
                "path": rel,
                "group": group,
                "modified": script.stat().st_mtime,
            }
        )
    return items


def discover_editable_files(root: Path | None = None) -> list[dict]:
    root = (root or REPO_ROOT).resolve()
    files = []
    for path in sorted(root.glob("**/*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if set(rel_parts) & EXCLUDED_DIRS:
            continue
        if path.suffix.lower() not in EDITABLE_EXTENSIONS:
            continue
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "name": path.name,
                "folder": Path(*rel_parts[:-1]).as_posix() if len(rel_parts) > 1 else "",
                "modified": path.stat().st_mtime,
                "size": path.stat().st_size,
            }
        )
    return files


def build_script_command(script_path: Path, args: list[str] | None = None) -> tuple[list[str], Path, dict]:
    if not is_discoverable_script(script_path):
        raise ValueError("Only discovered Python bot scripts can be started.")
    run_args = [str(arg) for arg in (args or [])]
    cwd = script_path.parent
    env = os.environ.copy()
    current_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(REPO_ROOT) if not current_pythonpath else f"{REPO_ROOT}{os.pathsep}{current_pythonpath}"
    env["PYTHONUNBUFFERED"] = "1"
    apply_runtime_environment(env, load_runtime_settings())
    env["CHADBOT_REPO_ROOT"] = str(REPO_ROOT)
    env["CHADBOT_SCRIPT_DIR"] = str(cwd)
    env["CHADBOT_SCRIPT_PATH"] = str(script_path)
    return [sys.executable, "-u", script_path.name, *run_args], cwd, env


def ast_call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = ast_call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return ast_call_name(node.func)
    return ""


def normalize_call_name(name: str, aliases: dict[str, str]) -> str:
    if not name:
        return ""
    parts = name.split(".")
    if parts[0] in aliases:
        replacement = aliases[parts[0]].split(".")
        parts = [*replacement, *parts[1:]]
    return ".".join(parts)


def collect_import_metadata(tree: ast.AST) -> tuple[list[str], dict[str, str], bool]:
    imports: set[str] = set()
    aliases: dict[str, str] = {}
    imports_functions = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                imports.add(module)
                aliases[alias.asname or module] = alias.name
                if module == "functions":
                    imports_functions = True
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if module:
                imports.add(module)
            if module == "functions":
                imports_functions = True
                for alias in node.names:
                    aliases[alias.asname or alias.name] = f"functions.{alias.name}"

    return sorted(imports), aliases, imports_functions


def is_absolute_reference(value: object) -> bool:
    if isinstance(value, Path):
        return value.is_absolute()
    text = str(value)
    return PureWindowsPath(text).is_absolute() or PurePosixPath(text).is_absolute()


def path_value(value: Path | str, hardcoded_absolute: bool = False) -> dict:
    return {
        "value": value,
        "hardcoded_absolute": hardcoded_absolute or (isinstance(value, str) and is_absolute_reference(value)),
    }


def path_value_text(value: dict) -> str:
    raw = value["value"]
    if isinstance(raw, Path):
        try:
            resolved = raw.resolve()
            if is_relative_to(resolved, REPO_ROOT):
                return repo_relative(resolved)
        except OSError:
            pass
    return str(raw)


def combine_path_values(left: dict, right: dict) -> dict:
    left_value = left["value"]
    right_value = right["value"]
    combined = Path(left_value) / str(right_value) if not isinstance(left_value, Path) else left_value / str(right_value)
    return path_value(combined, bool(left["hardcoded_absolute"] or right["hardcoded_absolute"]))


def literal_int(node: ast.AST) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    return None


def evaluate_path_expression(node: ast.AST, assignments: dict[str, dict], script_path: Path) -> dict | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return path_value(node.value, is_absolute_reference(node.value))
    if isinstance(node, ast.Name):
        if node.id == "__file__":
            return path_value(script_path)
        return assignments.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = evaluate_path_expression(node.left, assignments, script_path)
        right = evaluate_path_expression(node.right, assignments, script_path)
        if left and right:
            return combine_path_values(left, right)
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "parents":
        base = evaluate_path_expression(node.value.value, assignments, script_path)
        index = literal_int(node.slice)
        if base and index is not None:
            try:
                return path_value(Path(base["value"]).parents[index], bool(base["hardcoded_absolute"]))
            except IndexError:
                return None
    if isinstance(node, ast.Attribute):
        base = evaluate_path_expression(node.value, assignments, script_path)
        if base and node.attr == "parent":
            return path_value(Path(base["value"]).parent, bool(base["hardcoded_absolute"]))
    if isinstance(node, ast.Call):
        call_name = ast_call_name(node.func)
        if call_name in {"Path", "pathlib.Path"} and node.args:
            return evaluate_path_expression(node.args[0], assignments, script_path)
        if call_name in {"str", "builtins.str"} and node.args:
            return evaluate_path_expression(node.args[0], assignments, script_path)
        if call_name == "os.path.dirname" and node.args:
            source = evaluate_path_expression(node.args[0], assignments, script_path)
            if source:
                return path_value(Path(source["value"]).parent, bool(source["hardcoded_absolute"]))
        if call_name == "os.path.join":
            resolved_parts = [evaluate_path_expression(arg, assignments, script_path) for arg in node.args]
            current = None
            for part in resolved_parts:
                if not part:
                    break
                current = part if current is None else combine_path_values(current, part)
            return current
        if isinstance(node.func, ast.Attribute) and node.func.attr == "resolve":
            base = evaluate_path_expression(node.func.value, assignments, script_path)
            if base:
                return path_value(Path(base["value"]).resolve(), bool(base["hardcoded_absolute"]))
    return None


def collect_path_assignments(tree: ast.AST, script_path: Path) -> dict[str, dict]:
    assignments: dict[str, dict] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            value = evaluate_path_expression(node.value, assignments, script_path)
            if not value:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            value = evaluate_path_expression(node.value, assignments, script_path) if node.value else None
            if value:
                assignments[node.target.id] = value
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional_args = node.args.posonlyargs + node.args.args
            defaults = node.args.defaults
            default_offset = len(positional_args) - len(defaults)
            for index, default in enumerate(defaults):
                target = positional_args[default_offset + index]
                value = evaluate_path_expression(default, assignments, script_path)
                if value:
                    assignments[target.arg] = value
    return assignments


def path_values_from_node(node: ast.AST, assignments: dict[str, dict], script_path: Path) -> list[dict]:
    direct = evaluate_path_expression(node, assignments, script_path)
    if direct:
        return [direct]
    if isinstance(node, ast.Call) and ast_call_name(node.func) == "os.path.join":
        values = []
        for arg in node.args:
            part = evaluate_path_expression(arg, assignments, script_path)
            if part:
                values.append(part)
        return values
    return []


def unresolved_name_reference(node: ast.AST, assignments: dict[str, dict]) -> bool:
    return isinstance(node, ast.Name) and node.id not in assignments


def has_asset_extension(value: object) -> bool:
    return Path(str(value)).suffix.lower() in SCRIPT_ASSET_EXTENSIONS


def looks_like_path_reference(value: dict, force: bool = False) -> bool:
    raw = value["value"]
    if force:
        return True
    if is_absolute_reference(raw):
        return True
    text = str(raw)
    return has_asset_extension(text)


def candidate_reference_paths(value: dict, script_path: Path) -> list[Path]:
    raw = value["value"]
    if isinstance(raw, Path):
        path = raw
    else:
        path = Path(str(raw))

    if is_absolute_reference(raw):
        return [path]
    candidates = [script_path.parent / path, REPO_ROOT / path]
    if path.name == str(path) and path.suffix.lower() in SCRIPT_ASSET_EXTENSIONS and script_path.parent.exists():
        for child in sorted(script_path.parent.iterdir()):
            if child.is_dir() and child.name not in EXCLUDED_DIRS:
                candidates.append(child / path)
    return candidates


def resolved_reference_label(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        resolved = path.resolve()
        return repo_relative(resolved) if is_relative_to(resolved, REPO_ROOT) else str(resolved)
    except OSError:
        return str(path)


def make_asset_reference(value: dict, script_path: Path, usage: str, line: int) -> dict:
    candidates = candidate_reference_paths(value, script_path)
    existing = next((candidate for candidate in candidates if candidate.exists()), None)
    selected = existing or (candidates[0] if candidates else None)
    if existing:
        status = "ok"
    elif usage == "write":
        status = "generated"
    else:
        status = "missing"
    return {
        "value": path_value_text(value),
        "line": line,
        "usage": usage,
        "status": status,
        "absolute": bool(value["hardcoded_absolute"]),
        "resolved": resolved_reference_label(selected),
    }


def script_metadata(script_path: Path) -> dict:
    rel = repo_relative(script_path)
    rel_parts = Path(rel).parts
    group = "Core" if rel_parts[0] != "scripts" else rel_parts[1].replace("_", " ").title()
    return {
        "id": rel,
        "name": script_path.stem.replace("_", " ").title(),
        "path": rel,
        "group": group,
    }


def analyze_script(relative_script: str) -> dict:
    script_path = resolve_repo_path(relative_script)
    if not script_path.exists():
        raise FileNotFoundError(f"File not found: {relative_script}")
    if not is_discoverable_script(script_path):
        raise ValueError("Only discovered Python bot scripts can be analyzed.")

    source = script_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=repo_relative(script_path))
    except SyntaxError as exc:
        return {
            "script": script_metadata(script_path),
            "status": "error",
            "imports": [],
            "importsFunctions": False,
            "assetReferences": [],
            "warnings": [{
                "status": "error",
                "label": "Syntax error",
                "detail": exc.msg,
                "line": exc.lineno or 0,
            }],
            "summary": {"assets": 0, "missing": 0, "warnings": 1},
        }

    imports, aliases, imports_functions = collect_import_metadata(tree)
    assignments = collect_path_assignments(tree, script_path)
    references: list[dict] = []
    warnings: list[dict] = []
    seen_references: set[tuple[str, int, str]] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        raw_name = ast_call_name(node.func)
        name = normalize_call_name(raw_name, aliases)
        if name in WRITE_PATH_CALLS:
            usage = "write"
        elif name.endswith(".save"):
            usage = "write"
        elif name in FOLDER_PATH_CALLS:
            usage = "folder"
        elif name in READ_PATH_CALLS:
            usage = "read"
        else:
            usage = "reference"

        path_args: list[tuple[ast.AST, str]] = []
        if usage != "reference":
            max_args = 2 if name.endswith("play_actions") else 1
            path_args.extend((arg, usage) for arg in node.args[:max_args])
            for keyword in node.keywords:
                if keyword.arg not in {"filename", "img_name", "new_path", "path"}:
                    continue
                keyword_usage = "write" if keyword.arg == "img_name" else "folder" if keyword.arg == "new_path" else usage
                path_args.append((keyword.value, keyword_usage))
        else:
            path_args.extend((arg, usage) for arg in node.args)

        resolved_any = False
        for arg, arg_usage in path_args:
            for value in path_values_from_node(arg, assignments, script_path):
                force = arg_usage != "reference"
                if not looks_like_path_reference(value, force=force):
                    continue
                resolved_any = True
                reference = make_asset_reference(value, script_path, arg_usage, getattr(arg, "lineno", getattr(node, "lineno", 0)))
                key = (reference["value"], reference["line"], reference["usage"])
                if key in seen_references:
                    continue
                seen_references.add(key)
                references.append(reference)

        unresolved_dynamic = all(unresolved_name_reference(arg, assignments) for arg, _ in path_args)
        if usage in {"read", "folder"} and path_args and not resolved_any and not unresolved_dynamic:
            warnings.append({
                "status": "warn",
                "label": "Dynamic path",
                "detail": f"{name} uses a path that could not be statically resolved.",
                "line": getattr(node, "lineno", 0),
            })

    for reference in references:
        if reference["status"] == "missing":
            warnings.append({
                "status": "error",
                "label": "Missing asset",
                "detail": f"{reference['value']} was not found from the script folder or repo root.",
                "line": reference["line"],
            })
        if reference["absolute"]:
            warnings.append({
                "status": "warn",
                "label": "Hardcoded path",
                "detail": f"{reference['value']} is absolute and may fail on another computer.",
                "line": reference["line"],
            })

    if ("pyautogui" in imports or "cv2" in imports) and not imports_functions and script_path.name not in CORE_SCRIPTS:
        warnings.append({
            "status": "warn",
            "label": "Portability helpers",
            "detail": "Import functions.py helpers so scaling and script-relative assets stay consistent.",
            "line": 1,
        })

    references.sort(key=lambda item: (item["status"] != "missing", item["value"], item["line"]))
    warnings.sort(key=lambda item: (item["status"] != "error", item["line"], item["label"]))
    missing_count = sum(1 for reference in references if reference["status"] == "missing")
    checks = warnings or [{"status": "ok"}]
    return {
        "script": script_metadata(script_path),
        "status": status_from_checks(checks),
        "imports": imports,
        "importsFunctions": imports_functions,
        "assetReferences": references,
        "warnings": warnings,
        "summary": {
            "assets": len(references),
            "missing": missing_count,
            "warnings": len(warnings),
        },
    }


def compact_script_analysis(analysis: dict) -> dict:
    return {
        "script": analysis["script"],
        "status": analysis["status"],
        "summary": analysis["summary"],
        "importsFunctions": analysis["importsFunctions"],
        "warnings": analysis["warnings"][:3],
    }


def analyze_scripts() -> dict:
    analyses = [compact_script_analysis(analyze_script(script["path"])) for script in discover_scripts()]
    counts = {"ok": 0, "warn": 0, "error": 0}
    for analysis in analyses:
        counts[analysis["status"]] = counts.get(analysis["status"], 0) + 1
    return {
        "generatedAt": time.time(),
        "counts": counts,
        "analyses": analyses,
    }


class ProcessManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._process: subprocess.Popen | None = None
        self._active_script: str | None = None
        self._started_at: float | None = None
        self._logs: deque[dict] = deque(maxlen=2000)
        self._next_log_id = 0

    def _append_log(self, text: str, level: str = "info") -> None:
        with self._lock:
            self._next_log_id += 1
            self._logs.append(
                {
                    "id": self._next_log_id,
                    "time": time.time(),
                    "level": level,
                    "text": text.rstrip("\n"),
                }
            )

    def is_running(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def start(self, relative_script: str, args: list[str] | None = None) -> dict:
        script_path = resolve_repo_path(relative_script)
        command, cwd, env = build_script_command(script_path, args)

        with self._lock:
            if self.is_running():
                raise RuntimeError("A bot script is already running.")
            self._logs.clear()
            self._process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._active_script = repo_relative(script_path)
            self._started_at = time.time()
            self._append_log(f"Started {self._active_script}")

        threading.Thread(target=self._read_output, daemon=True).start()
        return self.status()

    def _read_output(self) -> None:
        process = self._process
        if process is None:
            return
        try:
            if process.stdout:
                for line in process.stdout:
                    self._append_log(line, level="output")
            return_code = process.wait()
            self._append_log(f"Process exited with code {return_code}", level="exit")
        finally:
            with self._lock:
                if self._process is process:
                    self._process = None

    def stop(self) -> dict:
        with self._lock:
            process = self._process
            if process is None or process.poll() is not None:
                self._process = None
                return self.status()
            self._append_log("Stopping process", level="warn")
            process.terminate()

        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self._append_log("Process did not exit after terminate; killing it", level="warn")
            process.kill()
            process.wait(timeout=5)

        with self._lock:
            if self._process is process:
                self._process = None
        return self.status()

    def status(self) -> dict:
        with self._lock:
            running = self._process is not None and self._process.poll() is None
            return {
                "running": running,
                "script": self._active_script,
                "startedAt": self._started_at,
                "uptime": (time.time() - self._started_at) if running and self._started_at else 0,
            }

    def logs(self, after: int = 0) -> dict:
        with self._lock:
            logs = [entry for entry in self._logs if entry["id"] > after]
            latest = self._next_log_id
        return {"latest": latest, "logs": logs}


class SetupManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._process: subprocess.Popen | None = None
        self._started_at: float | None = None
        self._finished_at: float | None = None
        self._return_code: int | None = None
        self._logs: deque[dict] = deque(maxlen=3000)
        self._next_log_id = 0

    def _append_log(self, text: str, level: str = "info") -> None:
        with self._lock:
            self._next_log_id += 1
            self._logs.append(
                {
                    "id": self._next_log_id,
                    "time": time.time(),
                    "level": level,
                    "text": text.rstrip("\n"),
                }
            )

    def is_running(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def install_requirements(self) -> dict:
        command = setup_requirements_command()

        with self._lock:
            if self.is_running():
                raise RuntimeError("Setup is already running.")
            self._logs.clear()
            self._started_at = time.time()
            self._finished_at = None
            self._return_code = None
            self._append_log("Installing Python requirements")
            self._append_log(" ".join(command))
            self._process = subprocess.Popen(
                command,
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

        threading.Thread(target=self._read_output, daemon=True).start()
        return self.status()

    def _read_output(self) -> None:
        process = self._process
        if process is None:
            return
        try:
            if process.stdout:
                for line in process.stdout:
                    self._append_log(line, level="output")
            return_code = process.wait()
            self._append_log(f"Setup exited with code {return_code}", level="exit" if return_code == 0 else "error")
            with self._lock:
                self._return_code = return_code
                self._finished_at = time.time()
        finally:
            with self._lock:
                if self._process is process:
                    self._process = None

    def status(self) -> dict:
        with self._lock:
            running = self._process is not None and self._process.poll() is None
            return {
                "running": running,
                "startedAt": self._started_at,
                "finishedAt": self._finished_at,
                "returnCode": self._return_code,
                "uptime": (time.time() - self._started_at) if running and self._started_at else 0,
            }

    def logs(self, after: int = 0) -> dict:
        with self._lock:
            logs = [entry for entry in self._logs if entry["id"] > after]
            latest = self._next_log_id
        return {"latest": latest, "logs": logs}

    def stop(self) -> dict:
        with self._lock:
            process = self._process
            if process is None or process.poll() is not None:
                self._process = None
                return self.status()
            self._append_log("Stopping setup process", level="warn")
            process.terminate()

        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self._append_log("Setup did not exit after terminate; killing it", level="warn")
            process.kill()
            process.wait(timeout=5)

        with self._lock:
            self._return_code = process.returncode
            self._finished_at = time.time()
            if self._process is process:
                self._process = None
        return self.status()


def run_check(check_name: str) -> dict:
    commands = {
        "compile": [sys.executable, "-m", "compileall", "-q", "."],
        "pytest": [sys.executable, "-m", "pytest"],
    }
    if check_name not in commands:
        raise ValueError("Unknown validation check.")

    started = time.time()
    result = subprocess.run(
        commands[check_name],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
    return {
        "check": check_name,
        "returnCode": result.returncode,
        "duration": round(time.time() - started, 2),
        "output": result.stdout,
    }


class ChadBotHandler(BaseHTTPRequestHandler):
    server_version = "ChadBot/1.0"

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self._handle_api_get(parsed.path, parse_qs(parsed.query))
            else:
                self._serve_static(parsed.path)
        except Exception as exc:
            self._send_error(exc)

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            if not parsed.path.startswith("/api/"):
                self._json({"error": "Not found"}, status=404)
                return
            self._handle_api_post(parsed.path, self._read_json())
        except Exception as exc:
            self._send_error(exc)

    @property
    def manager(self) -> ProcessManager:
        return self.server.process_manager  # type: ignore[attr-defined]

    @property
    def setup_manager(self) -> SetupManager:
        return self.server.setup_manager  # type: ignore[attr-defined]

    def _handle_api_get(self, path: str, query: dict) -> None:
        if path == "/api/health":
            self._json({
                "name": "ChadBot",
                "status": "Ready",
                "root": str(REPO_ROOT),
                "local": True,
                "portability": portability_config(),
            })
        elif path == "/api/scripts":
            status = self.manager.status()
            scripts = discover_scripts()
            for script in scripts:
                script["running"] = status["running"] and status["script"] == script["path"]
            self._json({"scripts": scripts, "status": status})
        elif path == "/api/scripts/analyze":
            relative_path = self._first_query_value(query, "path")
            self._json({"analysis": analyze_script(relative_path)})
        elif path == "/api/scripts/analysis":
            self._json({"scriptHealth": analyze_scripts()})
        elif path == "/api/files/tree":
            self._json({"files": discover_editable_files()})
        elif path == "/api/settings":
            settings = load_runtime_settings()
            self._json({"settings": settings, "portability": portability_config(settings)})
        elif path == "/api/diagnostics":
            self._json({"diagnostics": runtime_diagnostics()})
        elif path == "/api/files/read":
            relative_path = self._first_query_value(query, "path")
            file_path = validate_edit_path(relative_path, must_exist=True)
            self._json({"path": repo_relative(file_path), "content": file_path.read_text(encoding="utf-8")})
        elif path == "/api/process/status":
            self._json(self.manager.status())
        elif path == "/api/process/logs":
            after = int(self._first_query_value(query, "after", default="0"))
            self._json(self.manager.logs(after=after))
        elif path == "/api/setup/status":
            self._json(self.setup_manager.status())
        elif path == "/api/setup/logs":
            after = int(self._first_query_value(query, "after", default="0"))
            self._json(self.setup_manager.logs(after=after))
        else:
            self._json({"error": "Not found"}, status=404)

    def _handle_api_post(self, path: str, payload: dict) -> None:
        if path == "/api/process/start":
            self._json(self.manager.start(payload.get("path", ""), args=payload.get("args") or []))
        elif path == "/api/process/stop":
            self._json(self.manager.stop())
        elif path == "/api/files/write":
            relative_path = payload.get("path", "")
            content = payload.get("content", "")
            if not isinstance(content, str):
                raise ValueError("File content must be a string.")
            file_path = validate_edit_path(relative_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            self._json({"path": repo_relative(file_path), "saved": True, "modified": file_path.stat().st_mtime})
        elif path == "/api/settings":
            action = payload.get("action")
            settings_payload = payload["settings"] if "settings" in payload else payload
            settings = reset_runtime_settings() if action == "reset" else save_runtime_settings(settings_payload)
            self._json({"settings": settings, "portability": portability_config(settings)})
        elif path == "/api/checks/run":
            self._json(run_check(payload.get("check", "")))
        elif path == "/api/setup/install":
            self._json(self.setup_manager.install_requirements())
        else:
            self._json({"error": "Not found"}, status=404)

    def _serve_static(self, request_path: str) -> None:
        relative = unquote(request_path.lstrip("/")) or "index.html"
        if relative.endswith("/"):
            relative += "index.html"
        target = (UI_ROOT / relative).resolve()
        if not is_relative_to(target, UI_ROOT) or not target.exists() or not target.is_file():
            self._json({"error": "Not found"}, status=404)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, exc: Exception) -> None:
        status = 404 if isinstance(exc, FileNotFoundError) else 400 if isinstance(exc, ValueError) else 500
        self._json({"error": str(exc), "type": exc.__class__.__name__}, status=status)

    @staticmethod
    def _first_query_value(query: dict, key: str, default: str | None = None) -> str:
        values = query.get(key)
        if not values:
            if default is not None:
                return default
            raise ValueError(f"Missing query parameter: {key}")
        return values[0]

    def log_message(self, format: str, *args) -> None:
        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        with (RUNTIME_ROOT / "server.log").open("a", encoding="utf-8") as log:
            log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {format % args}\n")


class ChadBotServer(ThreadingHTTPServer):
    process_manager: ProcessManager
    setup_manager: SetupManager


def create_server(host: str, port: int) -> ChadBotServer:
    server = ChadBotServer((host, port), ChadBotHandler)
    server.process_manager = ProcessManager()
    server.setup_manager = SetupManager()
    return server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ChadBot local control UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow binding to a non-loopback host. This exposes file editing and script controls.",
    )
    args = parser.parse_args(argv)
    if args.host not in LOOPBACK_HOSTS and not args.allow_remote:
        parser.error("Non-loopback hosts require --allow-remote because ChadBot can edit files and start scripts.")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    server = create_server(args.host, args.port)
    print(f"ChadBot running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping ChadBot")
    finally:
        server.process_manager.stop()
        server.setup_manager.stop()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
