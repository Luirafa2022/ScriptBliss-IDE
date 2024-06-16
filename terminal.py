import subprocess
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class Terminal(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet("background-color: #00092a; color: #c9dcff;")
        self.keyPressEvent = self.terminalKeyPressEvent

    def terminalKeyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            command = self.toPlainText().splitlines()[-1]
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate()
            self.append(output.decode() + error.decode())
        else:
            QTextEdit.keyPressEvent(self, event)