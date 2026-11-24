STYLE = """
QWidget#workspace { background: #f4f7fb; color: #202734; }
QDialog, QWidget#records { background: #ffffff; color: #202734; }
QWidget#records { border: 1px solid #dfe6ee; border-radius: 12px; }
QWidget#hero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3795e2, stop:1 #19d1d5);
    border-top-left-radius: 15px;
    border-top-right-radius: 15px;
}
QLabel#heroTitle { color: white; font-size: 28px; font-weight: 700; }
QLabel#heroSubtitle { color: white; font-size: 14px; padding-bottom: 6px; }
QLabel#sectionTitle { color: #202734; font-size: 23px; font-weight: 700; }
QLabel#recordFeedback { color: #526278; padding: 2px; }
QTabBar { background: #e8edf3; }
QTabBar::tab {
    background: #e8edf3; color: #202734; font-weight: 600; font-size: 15px;
    padding: 12px 26px; border-bottom: 3px solid transparent;
}
QTabBar::tab:selected { background: #eef3f9; color: #1565bc; border-bottom-color: #4f9cf5; }
QTabBar::tab:hover { background: #dde5ef; }
QLineEdit, QComboBox, QDateEdit {
    background: white; color: #202734; border: 1px solid #cbd5e1;
    border-radius: 5px; min-height: 30px; padding: 2px 8px;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border-color: #3795e2; }
QPushButton {
    background: #f4f7fb; color: #253348; border: 1px solid #cbd5e1;
    border-radius: 5px; min-height: 30px; padding: 2px 12px; font-weight: 600;
}
QPushButton:hover { background: #e1ebf7; }
QPushButton#primary { background: #0d6efd; color: white; border-color: #0d6efd; }
QPushButton#primary:hover { background: #0a58ca; }
QPushButton#success { background: #198754; color: white; border-color: #198754; }
QPushButton#success:hover { background: #146c43; }
QPushButton#logout { background: #ffffff; color: #253348; min-height: 24px; }
QTableWidget {
    background: white; alternate-background-color: #f4f7fb; color: #202734;
    border: 1px solid #dfe6ee; gridline-color: #dfe6ee; selection-background-color: #d9ebff;
    selection-color: #202734;
}
QHeaderView::section { background: #212529; color: white; padding: 8px; border: 0; font-weight: 600; }
"""
