
from django.contrib.auth import authenticate
from django.db import DatabaseError
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QDialog, QFormLayout, QHeaderView,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from rest_framework.exceptions import ValidationError

from librosApp.models import Ejemplar
from .services import find_copies, find_readers, register_loan


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Préstamos Biblioteca · Acceso")
        self.account = None
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        button = QPushButton("Ingresar")
        button.clicked.connect(self.sign_in)
        button.setDefault(True)
        form = QFormLayout(self)
        form.addRow("Usuario", self.username)
        form.addRow("Contraseña", self.password)
        form.addRow(button)

    def sign_in(self):
        try:
            account = authenticate(
                username=self.username.text().strip(), password=self.password.text()
            )
            if account is None or not (
                account.is_superuser or getattr(account, "encargado", None)
            ):
                QMessageBox.warning(self, "Acceso", "Credenciales inválidas o perfil sin acceso.")
                return
        except DatabaseError:
            QMessageBox.critical(self, "Conexión", "Revisa la conexión con la base de datos.")
            return
        self.account = account
        self.accept()


class LibraryWindow(QMainWindow):
    def __init__(self, account):
        super().__init__()
        self.account = account
        self.copies = []
        self.setWindowTitle("Préstamos Biblioteca CSF")
        self.resize(820, 550)

        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(f"Catálogo y préstamos · {account.get_username()}"))

        self.book_query = QLineEdit()
        self.book_query.setPlaceholderText("Título, autor o código")
        search = QPushButton("Buscar libros")
        search.clicked.connect(self.search_books)
        self.book_query.returnPressed.connect(self.search_books)
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.book_query)
        search_layout.addWidget(search)
        layout.addLayout(search_layout)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Título", "Autor", "Ejemplar", "Estado"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        form = QFormLayout()
        layout.addLayout(form)
        self.reader_query = QLineEdit()
        self.reader_query.setPlaceholderText("Nombre o RUT")
        reader_search = QPushButton("Buscar lectores")
        reader_search.clicked.connect(self.search_readers)
        self.reader_query.returnPressed.connect(self.search_readers)
        reader_layout = QHBoxLayout()
        reader_layout.addWidget(self.reader_query)
        reader_layout.addWidget(reader_search)
        form.addRow("Buscar lector", reader_layout)
        self.readers = QComboBox()
        form.addRow("Lector", self.readers)

        self.due_date = QDateEdit(QDate.currentDate().addDays(12))
        self.due_date.setMinimumDate(QDate.currentDate())
        self.due_date.setCalendarPopup(True)
        self.due_date.setDisplayFormat("dd/MM/yyyy")
        form.addRow("Devolución", self.due_date)

        self.level = QComboBox()
        if account.is_superuser:
            self.level.addItem("Selecciona un nivel", None)
            self.level.addItem("Básica", "BASICA")
            self.level.addItem("Media", "MEDIA")
            form.addRow("Nivel del préstamo", self.level)

        save = QPushButton("Registrar préstamo")
        save.clicked.connect(self.save_loan)
        form.addRow(save)
        self.statusBar().showMessage("Busca un libro o pulsa Buscar libros para listar el catálogo.")

    def search_books(self):
        try:
            self.copies = list(find_copies(self.account, self.book_query.text().strip()))
        except DatabaseError:
            QMessageBox.critical(self, "Catálogo", "No se pudo consultar la base de datos.")
            return
        self.table.setRowCount(len(self.copies))
        self.table.clearSelection()
        self.table.setCurrentCell(-1, -1)
        for row, copy in enumerate(self.copies):
            columns = (copy.libro.titulo, copy.libro.autor, copy.codigo, copy.get_estado_display())
            for column, value in enumerate(columns):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.statusBar().showMessage(f"{len(self.copies)} ejemplares encontrados (máximo 100).")

    def search_readers(self):
        self.readers.clear()
        query = self.reader_query.text().strip()
        if not query:
            self.statusBar().showMessage("Escribe el nombre o RUT del lector.")
            return
        try:
            readers = list(find_readers(self.account, query))
        except DatabaseError:
            QMessageBox.critical(self, "Lectores", "No se pudo consultar la base de datos.")
            return
        for reader in readers:
            self.readers.addItem(f"{reader.nombre} ({reader.rut})", reader.pk)
        self.statusBar().showMessage(f"{len(readers)} lectores encontrados (máximo 50).")

    def save_loan(self):
        row = self.table.currentRow()
        reader_id = self.readers.currentData()
        level = self.level.currentData()
        if row < 0 or reader_id is None or (self.account.is_superuser and not level):
            QMessageBox.information(self, "Préstamo", "Selecciona un ejemplar, un lector y el nivel cuando corresponda.")
            return
        copy = self.copies[row]
        if copy.estado != Ejemplar.ESTADO_DISPONIBLE:
            QMessageBox.warning(self, "Préstamo", "El ejemplar seleccionado no está disponible.")
            return
        try:
            loan = register_loan(
                self.account, copy.pk, reader_id, self.due_date.date().toPython(), level
            )
        except (ValueError, ValidationError) as error:
            QMessageBox.warning(self, "Préstamo", str(error))
            return
        except DatabaseError:
            QMessageBox.critical(self, "Préstamo", "No se pudo guardar en la base de datos.")
            return
        self.search_books()
        self.due_date.setDate(QDate.currentDate().addDays(12))
        self.statusBar().showMessage(f"Préstamo {loan.pk} registrado.")
