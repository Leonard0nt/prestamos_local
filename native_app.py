import os
import sys

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox


from desktop_native.config import config_file, load_desktop_environment


def main():
    light_mode = "--ligero" in sys.argv
    if not light_mode:
        from desktop_native.full_window import LibraryBrowser, register_scheme

        register_scheme()
    app = QApplication([arg for arg in sys.argv if arg != "--ligero"])
    app.setApplicationName("Préstamos Biblioteca CSF")
    app.setQuitOnLastWindowClosed(False)

    import django
    from django.core.exceptions import ImproperlyConfigured
    from django.db import DatabaseError

    path = config_file()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prestamos_biblioteca.settings")
    try:
        load_desktop_environment(path)
        django.setup()
        from desktop_native.local_setup import prepare_local_database

        if not prepare_local_database():
            return 0
    except (DatabaseError, ImproperlyConfigured, OSError, ValueError) as error:
        QMessageBox.critical(
            None, "Configuración", f"{error}\n\nConfigura la base de datos en:\n{path}"
        )
        return 1

    if not light_mode:
        from django.conf import settings
        from django.core.wsgi import get_wsgi_application
        from desktop_native.bridge import HOST

        settings.ALLOWED_HOSTS = [HOST]
        app.setQuitOnLastWindowClosed(True)
        browser = LibraryBrowser(get_wsgi_application(), path)
        browser.show()
        result = app.exec()
        browser.dispose()
        return result

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
