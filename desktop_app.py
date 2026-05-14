#!/usr/bin/env python3
"""
Launcher de escritorio (pywebview) para la app Django del repositorio.

Flujo:
1) Inicia Django en segundo plano usando Waitress.
2) Espera a que el servidor responda.
3) Abre una ventana nativa apuntando a /login/.
4) Al cerrar la ventana, termina el servidor Django.

Recomendado para:
- Ejecución normal desde VSCode / terminal.
- Ejecución empaquetada con PyInstaller.
"""

from __future__ import annotations

import ctypes
import os
import socket
import sys
import threading
import time
from pathlib import Path

import webview


HOST = "127.0.0.1"
PORT = 8765
START_PATH = "/login/"
WINDOW_TITLE = "PrestamosBibliotecaCSF"
START_TIMEOUT_SECONDS = 25
WINDOW_WIDTH = 1165
WINDOW_HEIGHT = 668


def _is_frozen() -> bool:
    """
    Detecta si el programa está corriendo como ejecutable creado por PyInstaller.
    """
    return bool(getattr(sys, "frozen", False))


def _runtime_base_dir() -> Path:
    """
    Directorio base de ejecución.

    - Script normal:
      carpeta donde está este archivo .py

    - PyInstaller:
      carpeta donde está el .exe
    """
    if _is_frozen():
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def _find_project_root() -> Path | None:
    """
    Intenta ubicar la raíz del proyecto buscando manage.py.

    Cubre casos:
    - ejecución directa desde el repositorio
    - ejecución desde dist/
    - ejecución desde dist/nombre_app/
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


def _wait_for_port(host: str, port: int, timeout_seconds: int) -> bool:
    """
    Espera hasta que el servidor local esté escuchando en el puerto indicado.
    """
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)

            if sock.connect_ex((host, port)) == 0:
                return True

        time.sleep(0.25)

    return False


def _load_env_file(env_file: Path) -> None:
    """
    Carga variables desde un archivo .env simple.

    Formato esperado:
    CLAVE=valor

    También acepta:
    CLAVE="valor"
    CLAVE='valor'
    """
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def _write_log(message: str) -> None:
    """
    Escribe logs simples en desktop_app.log, junto al .exe o junto al script.
    """
    try:
        logfile = _runtime_base_dir() / "desktop_app.log"

        with logfile.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

    except Exception:
        # No detenemos la app si falla el log.
        pass


def _show_error(message: str, title: str = "Desktop App Error") -> None:
    """
    Muestra un error visual en Windows.
    Si falla, imprime por consola.
    """
    if os.name == "nt":
        try:
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
            return
        except Exception:
            pass

    print(message, file=sys.stderr)


def _start_embedded_django_server(root: Path):
    """
    Inicia Django dentro del mismo proceso usando Waitress.

    Ventaja:
    - No depende de ejecutar manage.py runserver.
    - No necesita abrir un segundo proceso Python.
    - Funciona mejor para apps empaquetadas con PyInstaller.
    """
    _load_env_file(root / ".env")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prestamos_biblioteca.settings")

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        from django.core.wsgi import get_wsgi_application
    except Exception as exc:
        raise RuntimeError(f"No se pudo importar Django: {exc}") from exc

    try:
        application = get_wsgi_application()
    except Exception as exc:
        raise RuntimeError(f"No se pudo cargar la aplicación WSGI de Django: {exc}") from exc

    try:
        from waitress.server import create_server
    except Exception as exc:
        raise RuntimeError(
            "No se pudo importar Waitress. "
            "Instala la dependencia con: pip install waitress"
        ) from exc

    try:
        waitress_server = create_server(
            application,
            host=HOST,
            port=PORT,
            threads=8,
        )

        server_thread = threading.Thread(
            target=waitress_server.run,
            daemon=True,
        )

        server_thread.start()

        _write_log(f"Servidor Django iniciado con Waitress en http://{HOST}:{PORT}")

        return {
            "type": "waitress",
            "server": waitress_server,
            "thread": server_thread,
        }

    except Exception as exc:
        raise RuntimeError(f"No se pudo iniciar Waitress: {exc}") from exc


def _stop_embedded_django_server(server_handle) -> None:
    """
    Detiene el servidor Waitress cuando se cierra la ventana.
    """
    if not server_handle:
        return

    server = server_handle.get("server")

    if server is None:
        return

    try:
        server.close()
        _write_log("Servidor Django detenido correctamente.")
    except Exception as exc:
        _write_log(f"No se pudo detener correctamente el servidor: {exc}")


def main() -> int:
    root = _find_project_root()

    if root is None:
        message = (
            "No se encontró manage.py.\n\n"
            "Verifica que este archivo o el .exe estén ubicados dentro del proyecto "
            "o en una carpeta cercana a manage.py."
        )
        _write_log(message)
        _show_error(message)
        return 1

    _write_log(f"Raíz del proyecto detectada: {root}")

    embedded_server = None

    try:
        embedded_server = _start_embedded_django_server(root)
    except Exception as exc:
        error_message = (
            "No fue posible iniciar Django con Waitress.\n\n"
            "Revisa el archivo desktop_app.log para más detalles."
        )

        _write_log(error_message)
        _write_log(str(exc))
        _show_error(error_message)

        return 1

    if not _wait_for_port(HOST, PORT, START_TIMEOUT_SECONDS):
        if embedded_server is not None:
            _stop_embedded_django_server(embedded_server)

        error_message = (
            "No fue posible iniciar Django dentro del tiempo esperado.\n\n"
            "Revisa el archivo desktop_app.log para más detalles."
        )

        _write_log(error_message)
        _show_error(error_message)

        return 1

    webview.create_window(
        title=WINDOW_TITLE,
        url=f"http://{HOST}:{PORT}{START_PATH}",
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(WINDOW_WIDTH, WINDOW_HEIGHT),
    )

    try:
        webview.start(gui="edgechromium", debug=False)
    finally:
        if embedded_server is not None:
            _stop_embedded_django_server(embedded_server)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

