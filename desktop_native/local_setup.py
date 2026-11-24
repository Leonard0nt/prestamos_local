"""Prepara el catálogo local y solicita la primera cuenta de administrador."""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AdminUserCreationForm
from django.core.management import call_command
from django.db import DatabaseError, connections
from django.db.migrations.executor import MigrationExecutor
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
)


def prepare_local_database():
    database = settings.DATABASES["default"]
    if database["ENGINE"] != "django.db.backends.sqlite3":
        return True

    Path(database["NAME"]).parent.mkdir(parents=True, exist_ok=True)
    executor = MigrationExecutor(connections["default"])
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        call_command("migrate", interactive=False, verbosity=0)
    if get_user_model().objects.filter(is_active=True, is_superuser=True).exists():
        return True
    return AdministratorDialog().exec() == QDialog.DialogCode.Accepted


class AdministratorDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crear administrador")
        layout = QFormLayout(self)
        layout.addRow(QLabel("Crea la cuenta para iniciar sesión en esta biblioteca local."))
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.confirmation = QLineEdit()
        for field in (self.password, self.confirmation):
            field.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Usuario", self.username)
        layout.addRow("Contraseña", self.password)
        layout.addRow("Repetir contraseña", self.confirmation)
        self.errors = QLabel()
        self.errors.setWordWrap(True)
        layout.addRow(self.errors)
        buttons = QDialogButtonBox()
        buttons.addButton("Crear cuenta", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.create_account)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def create_account(self):
        form = AdminUserCreationForm({
            "username": self.username.text().strip(),
            "password1": self.password.text(),
            "password2": self.confirmation.text(),
            "usable_password": "true",
        })
        if not form.is_valid():
            self.errors.setText("\n".join(
                message for errors in form.errors.values() for message in errors
            ))
            return
        account = form.save(commit=False)
        account.is_staff = True
        account.is_superuser = True
        try:
            account.save()
        except DatabaseError:
            self.errors.setText("No se pudo guardar la cuenta. Revisa el usuario e inténtalo de nuevo.")
            return
        self.accept()
