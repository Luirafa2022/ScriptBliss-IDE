from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QFont

class Console(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet("background-color: #00091a; color: #c9dcff;")