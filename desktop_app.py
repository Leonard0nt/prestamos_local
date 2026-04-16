"""Inicia la aplicación Django como app de escritorio local con SQLite."""

from __future__ import annotations

import argparse
import os
import socket
import threading
from pathlib import Path


def find_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta la app en modo escritorio (webview + servidor local)."
    )
    parser.add_argument(
        "--runtime-dir",
        default=str(Path.home() / ".prestamos_local"),
        help="Carpeta para base SQLite y configuración local.",
    )
    parser.add_argument(
        "--sin-ventana",
        action="store_true",
        help="Inicia sólo servidor local (útil para pruebas sin GUI).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    runtime_dir = Path(args.runtime_dir).expanduser().resolve()
    runtime_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prestamos_biblioteca.settings")
    os.environ["APP_RUNTIME_DIR"] = str(runtime_dir)

    import django

    django.setup()

    from django.core.management import call_command

    # Asegura que la base SQLite local quede lista al iniciar el escritorio.
    call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)

    if args.sin_ventana:
        print(f"Base inicializada en: {runtime_dir / 'db.sqlite3'}")
        return

    from prestamos_biblioteca.wsgi import application
    from waitress import serve
    import webview

    host = "127.0.0.1"
    port = find_free_port(host)

    server = threading.Thread(
        target=serve,
        kwargs={"app": application, "listen": f"{host}:{port}"},
        daemon=True,
    )
    server.start()

    webview.create_window("Gestión de Biblioteca", f"http://{host}:{port}")
    webview.start()


if __name__ == "__main__":
    main()