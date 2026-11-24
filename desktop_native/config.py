"""Ubicación de la configuración de escritorio en el equipo del usuario."""

import os
from pathlib import Path


def config_file():
    if os.name == "nt":
        directory = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    else:
        directory = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return directory / "prestamos-biblioteca" / ".env"
