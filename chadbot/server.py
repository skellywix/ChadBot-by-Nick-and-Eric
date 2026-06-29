"""Local web control server for ChadBot.

The server intentionally uses only the Python standard library so the UI can
run before the automation dependencies are installed.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = Path(__file__).resolve().parent / "ui"
RUNTIME_ROOT = Path(__file__).resolve().parent / "runtime"

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


def env_positive_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def portability_config() -> dict:
    template_scales = os.environ.get("CHADBOT_TEMPLATE_SCALES", "").strip()
    return {
        "baseWidth": env_positive_int("CHADBOT_BASE_WIDTH", 1920),
        "baseHeight": env_positive_int("CHADBOT_BASE_HEIGHT", 1080),
        "scalingDisabled": os.environ.get("CHADBOT_DISABLE_SCALING", "").lower() in {"1", "true", "yes", "on"},
        "templateScales": template_scales or "auto",
        "assetLookup": ["base_dir", "CHADBOT_SCRIPT_DIR", "caller", "cwd", "repo"],
        "repoRoot": str(REPO_ROOT),
    }


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


def is_discoverable_script(path: Path) -> bool:
    if path.suffix.lower() != ".py":
        return False
    rel_parts = path.relative_to(REPO_ROOT).parts
    if set(rel_parts) & EXCLUDED_DIRS:
        return False
    if rel_parts[0] == "scripts":
        return True
    return path.name in CORE_SCRIPTS


def discover_scripts(root: Path = REPO_ROOT) -> list[dict]:
    scripts: list[Path] = []
    for name in CORE_SCRIPTS:
        script = root / name
        if script.exists():
            scripts.append(script)
    scripts.extend(sorted((root / "scripts").glob("**/*.py")) if (root / "scripts").exists() else [])

    items = []
    for script in sorted({path.resolve() for path in scripts}):
        if not is_relative_to(script, root) or not is_discoverable_script(script):
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


def discover_editable_files(root: Path = REPO_ROOT) -> list[dict]:
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
    env["CHADBOT_REPO_ROOT"] = str(REPO_ROOT)
    env["CHADBOT_SCRIPT_DIR"] = str(cwd)
    env["CHADBOT_SCRIPT_PATH"] = str(script_path)
    return [sys.executable, "-u", script_path.name, *run_args], cwd, env


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
        elif path == "/api/files/tree":
            self._json({"files": discover_editable_files()})
        elif path == "/api/files/read":
            relative_path = self._first_query_value(query, "path")
            file_path = validate_edit_path(relative_path, must_exist=True)
            self._json({"path": repo_relative(file_path), "content": file_path.read_text(encoding="utf-8")})
        elif path == "/api/process/status":
            self._json(self.manager.status())
        elif path == "/api/process/logs":
            after = int(self._first_query_value(query, "after", default="0"))
            self._json(self.manager.logs(after=after))
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
        elif path == "/api/checks/run":
            self._json(run_check(payload.get("check", "")))
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
        return json.loads(self.rfile.read(length).decode("utf-8"))

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


def create_server(host: str, port: int) -> ChadBotServer:
    server = ChadBotServer((host, port), ChadBotHandler)
    server.process_manager = ProcessManager()
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
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
