import os
import sys

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox


from desktop_native.config import config_file


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Préstamos Biblioteca CSF")
    app.setQuitOnLastWindowClosed(False)

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

    from PySide6.QtCore import QTimer

    login = None
    window = None
    signed_out = False

    def show_login():
        nonlocal login, signed_out
        signed_out = False
        login = LoginDialog()
        login.finished.connect(login_finished)
        login.open()

    def login_finished(result):
        nonlocal login, window
        account = login.account
        login.deleteLater()
        login = None
        if result != QDialog.DialogCode.Accepted:
            app.quit()
            return

        window = LibraryWindow(account)
        window.logout_requested.connect(logout)
        window.closed.connect(window_closed)
        window.show()

    def logout():
        nonlocal signed_out
        signed_out = True
        window.close()

    def window_closed():
        nonlocal window
        window.deleteLater()
        window = None
        if signed_out:
            QTimer.singleShot(0, show_login)
        else:
            app.quit()

    show_login()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
