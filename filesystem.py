import os
from PyQt5.QtWidgets import QFileSystemModel
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

class CustomFileSystemModel(QFileSystemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_map = {
            '.cpp': QIcon('img/cpp.png'),
            '.css': QIcon('img/css.png'),
            '.java': QIcon('img/java.png'),
            '.class': QIcon('img/classe.png'),
            '.php': QIcon('img/php.png'),
            '.html': QIcon('img/html.png'),
            '.js': QIcon('img/javascript.png'),
            '.png': QIcon('img/image.png'),
            '.jpg': QIcon('img/image.png'),
            '.jpeg': QIcon('img/image.png'),
            '.bmp': QIcon('img/image.png'),
            '.gif': QIcon('img/image.png'),
            '.py': QIcon('img/python.png'),
            '.rb': QIcon('img/ruby.png')
        }

    def data(self, index, role):
        if role == Qt.DecorationRole and index.column() == 0:
            file_path = self.filePath(index)
            _, ext = os.path.splitext(file_path)
            if ext in self.icon_map:
                return self.icon_map[ext]
        elif role == Qt.DisplayRole and index.column() == 0:
            return os.path.basename(self.filePath(index))
        return super().data(index, role)