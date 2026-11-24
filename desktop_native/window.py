from datetime import date

from django.contrib.auth import authenticate
from django.db import DatabaseError
from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QDialog, QFormLayout, QHeaderView,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QTabBar,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from rest_framework.exceptions import ValidationError

from librosApp.models import Ejemplar
from .services import find_copies, find_loans, find_readers, register_loan
from .theme import STYLE


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Préstamos Biblioteca · Acceso")
        self.setMinimumWidth(400)
        self.setStyleSheet(STYLE)
        self.setObjectName("login")
        self.account = None
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        button = QPushButton("Ingresar")
        button.clicked.connect(self.sign_in)
        button.setDefault(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        heading = QLabel("Sistema de Biblioteca")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        layout.addWidget(QLabel("Inicia sesión como administrador o encargado."))
        form = QFormLayout()
        form.setVerticalSpacing(12)
        layout.addLayout(form)
        form.addRow("Usuario", self.username)
        password_row = QHBoxLayout()
        password_row.addWidget(self.password)
        show = QPushButton("Mostrar")
        show.setCheckable(True)
        show.setAutoDefault(False)

        def toggle_password(visible):
            self.password.setEchoMode(
                QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
            )
            show.setText("Ocultar" if visible else "Mostrar")

        show.toggled.connect(toggle_password)
        password_row.addWidget(show)
        button.setObjectName("primary")
        form.addRow("Contraseña", password_row)
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


class LoanDialog(QDialog):
    def __init__(self, account):
        super().__init__()
        self.account = account
        self.copies = []
        self.setWindowTitle("Nuevo préstamo")
        self.resize(770, 540)
        self.setStyleSheet(STYLE)
        self.loan = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        heading = QLabel("Nuevo préstamo")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

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
        save.setObjectName("success")
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(cancel)
        actions.addWidget(save)
        form.addRow(actions)
        self.feedback = QLabel()
        layout.addWidget(self.feedback)
        self.search_books()

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
        self.feedback.setText(f"{len(self.copies)} ejemplares encontrados (máximo 100).")

    def search_readers(self):
        self.readers.clear()
        query = self.reader_query.text().strip()
        if not query:
            self.feedback.setText("Escribe el nombre o RUT del lector.")
            return
        try:
            readers = list(find_readers(self.account, query))
        except DatabaseError:
            QMessageBox.critical(self, "Lectores", "No se pudo consultar la base de datos.")
            return
        for reader in readers:
            self.readers.addItem(f"{reader.nombre} ({reader.rut})", reader.pk)
        self.feedback.setText(f"{len(readers)} lectores encontrados (máximo 50).")

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
        self.loan = loan
        self.accept()


class RecordsPage(QWidget):
    def __init__(self, title, columns, search_hint, load, filters=(), action=None):
        super().__init__()
        self.load = load
        self.setObjectName("records")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

        toolbar = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText(search_hint)
        toolbar.addWidget(self.query, 1)
        search = QPushButton("Buscar")
        search.clicked.connect(self.refresh)
        self.query.returnPressed.connect(self.refresh)
        toolbar.addWidget(search)
        self.filter = QComboBox()
        for label, active in filters:
            self.filter.addItem(label, active)
        if filters:
            toolbar.addWidget(self.filter)
            self.filter.currentIndexChanged.connect(self.refresh)
        self.action_button = None
        if action:
            self.action_button = QPushButton("Nuevo préstamo")
            self.action_button.setObjectName("success")
            self.action_button.clicked.connect(action)
            toolbar.addWidget(self.action_button)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        layout.addWidget(self.table)
        self.feedback = QLabel()
        self.feedback.setObjectName("recordFeedback")
        layout.addWidget(self.feedback)

    def refresh(self):
        active = self.filter.currentData()
        if self.action_button:
            self.action_button.setVisible(active is not False)
        try:
            rows = list(self.load(self.query.text().strip(), active))
        except DatabaseError:
            self.table.setRowCount(0)
            self.feedback.setText("No se pudo consultar la base de datos.")
            return
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, value in enumerate(row):
                self.table.setItem(index, column, QTableWidgetItem(str(value)))
        if len(rows) == 1:
            self.feedback.setText("1 resultado")
        else:
            self.feedback.setText(f"{len(rows)} resultados" if rows else "Sin resultados.")


class LibraryWindow(QMainWindow):
    logout_requested = Signal()
    closed = Signal()

    def __init__(self, account):
        super().__init__()
        self.account = account
        self.setWindowTitle("Préstamos Biblioteca CSF")
        self.resize(1100, 680)
        self.setMinimumSize(760, 520)
        self.setStyleSheet(STYLE)

        container = QWidget()
        container.setObjectName("workspace")
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(0)

        hero = QWidget()
        hero.setObjectName("hero")
        banner = QVBoxLayout(hero)
        banner.setContentsMargins(18, 18, 18, 16)
        title = QLabel("Sistema de Préstamos para Biblioteca")
        title.setObjectName("heroTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner.addWidget(title)
        role = "Administrador" if account.is_superuser else "Encargado"
        level = "Administración" if account.is_superuser else account.encargado.get_nivel_display()
        subtitle = QLabel(f"Rol: {role}  ·  Nivel: {level}")
        subtitle.setObjectName("heroSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner.addWidget(subtitle)
        logout = QPushButton("Cerrar sesión")
        logout.setObjectName("logout")
        logout.clicked.connect(self.logout_requested)
        banner.addWidget(logout, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(hero)

        self.tabs = QTabBar()
        self.tabs.setDrawBase(False)
        self.tabs.setExpanding(True)
        self.pages = QStackedWidget()
        layout.addWidget(self.tabs)
        layout.addSpacing(16)
        layout.addWidget(self.pages, 1)

        books = RecordsPage(
            "Gestión de Libros", ["Título", "Autor", "Editorial", "Código", "Ejemplar", "Estado"],
            "Buscar por título, autor, editorial o código", self.book_rows,
        )
        self.loans = RecordsPage(
            "Gestión de Préstamos", ["Alumno", "Libro", "F. préstamo", "F. devolución", "Estado", "Días atraso"],
            "Buscar por alumno, libro o código", self.loan_rows,
            filters=(("Préstamos activos", True), ("Préstamos archivados", False)),
            action=self.new_loan,
        )
        readers = RecordsPage(
            "Gestión de Alumnos", ["Nombre", "Curso", "Correo", "RUT", "Teléfono"],
            "Buscar por nombre, RUT o correo", self.reader_rows,
            filters=(("Estudiantes activos", True), ("Estudiantes de baja", False)),
        )
        for label, page in (("Libros", books), ("Préstamos", self.loans), ("Alumnos", readers)):
            self.tabs.addTab(label)
            self.pages.addWidget(page)
        self.tabs.currentChanged.connect(self.show_page)
        self.tabs.setCurrentIndex(1)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed.emit()

    def show_page(self, index):
        self.pages.setCurrentIndex(index)
        self.pages.widget(index).refresh()

    def book_rows(self, query, _active):
        for copy in find_copies(self.account, query):
            book = copy.libro
            yield book.titulo, book.autor, book.editorial, book.codigo_libro, copy.codigo, copy.get_estado_display()

    def reader_rows(self, query, active):
        for reader in find_readers(self.account, query, active=active):
            yield reader.nombre, reader.curso, reader.email, reader.rut, reader.telefono

    def loan_rows(self, query, active):
        today = date.today()
        for loan in find_loans(self.account, query, active=active):
            days = loan.dias_atraso
            status = loan.get_estado_display()
            if loan.estado in {"P", "A"} and today > loan.fecha_devolucion:
                days = (today - loan.fecha_devolucion).days
                status = "Atrasado"
            yield (
                loan.usuario.nombre, loan.ejemplar.libro.titulo,
                loan.fecha_prestamo.strftime("%d/%m/%Y"), loan.fecha_devolucion.strftime("%d/%m/%Y"),
                status, days,
            )

    def new_loan(self):
        dialog = LoanDialog(self.account)
        dialog.setParent(self, Qt.WindowType.Dialog)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.loans.refresh()
            self.loans.feedback.setText(f"Préstamo {dialog.loan.pk} registrado.")
