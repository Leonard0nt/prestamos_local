#!/usr/bin/env python3
"""
Launcher de escritorio (pywebview) para la app Django del repositorio.

Flujo:
1) Inicia Django en segundo plano (manage.py runserver).
2) Espera a que el servidor responda.
3) Abre una ventana nativa apuntando a /login/.
4) Al cerrar la ventana, termina el servidor Django.
"""

from __future__ import annotations

import atexit
import ctypes
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import webview

HOST = "127.0.0.1"
PORT = 8000
START_PATH = "/login/"
WINDOW_TITLE = "PrestamosBibliotecaCSF"
START_TIMEOUT_SECONDS = 25


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _runtime_base_dir() -> Path:
    """
    Directorio base de ejecución.
    - Script normal: carpeta de desktop_app.py
    - PyInstaller: carpeta donde está el .exe
    """
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _find_project_root() -> Path | None:
    """
    Intenta ubicar la raíz del proyecto buscando `manage.py`.
    Cubre casos:
    - ejecución directa desde repo
    - ejecución de .exe desde ./dist
    - cwd distinto al del ejecutable
    """
    base = _runtime_base_dir()
    candidates = [
        Path.cwd().resolve(),
        base,
        base.parent,
        base.parent.parent,
    ]

    visited: set[Path] = set()
    for candidate in candidates:
        if candidate in visited:
            continue
        visited.add(candidate)
        if (candidate / "manage.py").exists():
            return candidate
    return None


def _python_executable() -> str:
    # Script normal: respeta venv activo.
    if not _is_frozen():
        return sys.executable

    # PyInstaller: sys.executable apunta al .exe, no al intérprete Python.
    explicit = os.environ.get("PYTHON_EXECUTABLE")
    if explicit:
        return explicit

    for candidate in ("python", "python3", "py"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    # Fallback final; el error real aparecerá en el arranque del subprocess.
    return sys.executable


def _wait_for_port(host: str, port: int, timeout_seconds: int) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.25)
    return False


def _terminate_process(process: subprocess.Popen[bytes] | subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    if os.name == "nt":
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        return

    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def _show_error(message: str, title: str = "Desktop App Error") -> None:
    if os.name == "nt":
        try:
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
            return
        except Exception:
            pass
    print(message, file=sys.stderr)


def _write_log(message: str) -> None:
    try:
        logfile = _runtime_base_dir() / "desktop_app.log"
        with logfile.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception:
        # Evita romper el flujo por problemas de logging.
        pass


def main() -> int:
    root = _find_project_root()
    if root is None:
        message = (
            "No se encontró manage.py.\n\n"
            "Si ejecutas el .exe desde /dist, verifica que la carpeta del proyecto "
            "contenga manage.py en el directorio padre."
        )
        _write_log(message)
        _show_error(message)
        return 1

    manage_py = root / "manage.py"
    _write_log(f"Raíz detectada: {root}")

    runserver_cmd = [
        _python_executable(),
        str(manage_py),
        "runserver",
        f"{HOST}:{PORT}",
    ]

    process = subprocess.Popen(
        runserver_cmd,
        cwd=str(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    atexit.register(_terminate_process, process)

    if not _wait_for_port(HOST, PORT, START_TIMEOUT_SECONDS):
        _terminate_process(process)
        stderr_output = ""
        if process.stderr is not None:
            try:
                stderr_output = process.stderr.read()
            except Exception:
                stderr_output = ""
        error_message = (
            "No fue posible iniciar Django dentro del tiempo esperado.\n\n"
            "Revisa el archivo desktop_app.log para más detalles."
        )
        _write_log(error_message)
        if stderr_output.strip():
            _write_log(stderr_output.strip())
        _show_error(error_message)
        return 1

    webview.create_window(
        title=WINDOW_TITLE,
        url=f"http://{HOST}:{PORT}{START_PATH}",
        min_size=(900, 650),
    )

    try:
        webview.start()
    finally:
        _terminate_process(process)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())