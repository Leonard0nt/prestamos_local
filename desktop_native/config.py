"""Ubicación de la configuración de escritorio en el equipo del usuario."""

import os
from pathlib import Path


def config_file():
    if os.name == "nt":
        directory = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    else:
        directory = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return directory / "prestamos-biblioteca" / ".env"


def load_desktop_environment(path):
    import environ

    if path.is_file():
        environ.Env.read_env(path)
    if not os.environ.get("DB_ENGINE"):
        os.environ["DB_ENGINE"] = "postgresql" if os.environ.get("DB_NAME") else "sqlite"
