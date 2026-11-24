import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox


def config_file():
    if os.name == "nt":
        directory = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    else:
        directory = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return directory / "prestamos-biblioteca" / ".env"


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Préstamos Biblioteca CSF")

    import django
    import environ
    from django.core.exceptions import ImproperlyConfigured

    path = config_file()
    environ.Env.read_env(path)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prestamos_biblioteca.settings")
    try:
        django.setup()
    except ImproperlyConfigured as error:
        QMessageBox.critical(
            None, "Configuración", f"{error}\n\nConfigura la base de datos en:\n{path}"
        )
        return 1

    from desktop_native.window import LibraryWindow, LoginDialog

    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted:
        return 0

    window = LibraryWindow(login.account)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
