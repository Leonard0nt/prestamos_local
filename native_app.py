import os
import sys

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox


from desktop_native.config import config_file


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
