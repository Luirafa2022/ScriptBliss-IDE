import os
from PyQt5.QtGui import QColor, QFont, QFontMetrics
from PyQt5.Qsci import QsciScintilla, QsciLexerPython, QsciLexerJava, QsciLexerHTML, QsciLexerJavaScript, QsciLexerCSS, QsciLexerCPP, QsciLexerRuby
from PyQt5.QtCore import Qt

class Editor(QsciScintilla):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUtf8(True)
        self.setCaretForegroundColor(QColor("#00091a"))
        self.setTabWidth(4)
        self.keyPressEvent = self.editorKeyPressEvent

        font = QFont()
        font.setFamily('Consolas')
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.setFont(font)
        self.setMarginsFont(font)

        fontmetrics = QFontMetrics(font)
        self.setMarginWidth(0, fontmetrics.width("00000") + 6)
        self.setMarginLineNumbers(0, True)
        self.setMarginsBackgroundColor(QColor("#1e1e3e"))
        self.setMarginsForegroundColor(QColor("#ffffff"))

        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#dee8ff"))

    def editorKeyPressEvent(self, event):
        super(QsciScintilla, self).keyPressEvent(event)
        line, index = self.getCursorPosition()

        pairs = {
            Qt.Key_ParenLeft: ')',
            Qt.Key_BracketLeft: ']',
            Qt.Key_BraceLeft: '}',
            Qt.Key_QuoteDbl: '"',
            Qt.Key_Apostrophe: "'"
        }

        if event.key() in pairs:
            self.insert(pairs[event.key()])
            self.setCursorPosition(line, index)

    def setLexerForFile(self, fileName):
        lexers = {
            '.py': QsciLexerPython,
            '.java': QsciLexerJava,
            '.html': QsciLexerHTML,
            '.js': QsciLexerJavaScript,
            '.css': QsciLexerCSS,
            '.cpp': QsciLexerCPP,
            '.rb': QsciLexerRuby
        }
        _, ext = os.path.splitext(fileName)
        lexer_class = lexers.get(ext)
        if lexer_class:
            lexer = lexer_class()
            lexer.setDefaultFont(QFont("Consolas", 10))
            self.setLexer(lexer)
        else:
            self.setLexer(None)