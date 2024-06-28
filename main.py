import sys
import os
import re
import tempfile
import subprocess
import webbrowser
import codecs
import shutil
from PyQt5.QtWidgets import (QApplication, QScrollArea, QMainWindow, QTreeView, QAbstractItemView, QFileSystemModel, QSplitter, QTextEdit,
                             QTabWidget, QMenu, QAction, QInputDialog, QMessageBox, QLabel, QFileDialog, QVBoxLayout, QWidget)
from PyQt5.QtGui import (QIcon, QColor, QPalette, QFont, QFontMetrics, QPixmap, QDesktopServices, QDrag, QCursor)
from PyQt5.QtCore import (Qt, QDir, QProcess, QTimer, QUrl, QPoint, QMimeData, QFileInfo, pyqtSignal)
from PyQt5.Qsci import (QsciScintilla, QsciLexerPython, QsciLexerJava, QsciLexerHTML, QsciLexerJavaScript,
                        QsciLexerCSS, QsciLexerCPP, QsciLexerRuby)
from PyQt5.QtWidgets import QToolBar, QAction

class DraggableTreeView(QTreeView):
    dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.MoveAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                source_path = url.toLocalFile()
                links.append(source_path)
                target_index = self.indexAt(event.pos())
                if target_index.isValid():
                    target_path = self.model().filePath(target_index)
                    if self.model().isDir(target_index):
                        target_dir = target_path
                    else:
                        target_dir = os.path.dirname(target_path)
                else:
                    target_dir = self.model().rootPath()
                
                # Move o arquivo
                try:
                    shutil.move(source_path, target_dir)
                except Exception as e:
                    print(f"Erro ao mover arquivo: {e}")
            
            self.dropped.emit(links)
            self.model().setRootPath(self.model().rootPath())  # Atualiza a visualização
        else:
            super().dropEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                drag = QDrag(self)
                mime = QMimeData()
                urls = [QUrl.fromLocalFile(self.model().filePath(index))]
                mime.setUrls(urls)
                drag.setMimeData(mime)
                drag.exec_(Qt.MoveAction)
        else:
            super().mouseMoveEvent(event)

class CustomFileSystemModel(QFileSystemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_map = {
            '.cpp': QIcon('img/cpp.png'),
            '.css': QIcon('img/css.png'),
            '.java': QIcon('img/java.png'),
            '.class': QIcon('img/classe.png'),
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.currentFile = ''
        self.projectPath = QDir.currentPath()
        self.process = None
        self.welcomeWidget = None
        self.initUI()
        self.debugToolbar = QToolBar("Debug Toolbar")
        self.addToolBar(self.debugToolbar)
        self.debugToolbar.setVisible(False)  # Inicialmente, a barra de ferramentas está oculta 
        self.setupDebugToolbar()
        self.setupAutocomplete()
        self.setupSyntaxCheck()
        self.syntaxCheckTimer = QTimer()
        self.syntaxCheckTimer.setSingleShot(True)
        self.syntaxCheckTimer.timeout.connect(self.checkSyntax)
        self.editor.textChanged.connect(self.startSyntaxCheckTimer)
        self.editor.setMarkerBackgroundColor(QColor("#ff0000"), 8)
        self.editor.markerDefine(QsciScintilla.RightTriangle, 8)

        # Configure o indicador para sublinhar erros
        self.ERROR_INDICATOR = 8
        self.editor.indicatorDefine(QsciScintilla.SquiggleIndicator, self.ERROR_INDICATOR)
        self.editor.setIndicatorForegroundColor(QColor("red"), self.ERROR_INDICATOR)

    def setupSyntaxCheck(self):
        self.syntaxCheckTimer = QTimer()
        self.syntaxCheckTimer.setSingleShot(True)
        self.syntaxCheckTimer.timeout.connect(self.checkSyntax)

    def showProblem(self, e):
        # Limpe indicadores anteriores
        self.editor.clearIndicatorRange(0, 0, self.editor.lines(), 0, self.ERROR_INDICATOR)
        
        # Adicione o novo indicador
        line = e.lineno - 1
        start = e.offset - 1 if e.offset else 0
        self.editor.fillIndicatorRange(line, start, line, self.editor.lineLength(line), self.ERROR_INDICATOR)
        
        problem = f"Line {e.lineno}: {e.msg}"
        self.problemsWidget.append(problem)
        self.bottomTabWidget.setCurrentIndex(2)  # Muda para a aba "Problems"

    def clearProblems(self):
        # Limpe todos os indicadores no editor
        self.editor.clearIndicatorRange(0, 0, self.editor.lines(), len(self.editor.text()), self.ERROR_INDICATOR)
        self.problemsWidget.clear()

    def startSyntaxCheckTimer(self):
        self.syntaxCheckTimer.start(1000)  # Verifica a sintaxe após 1 segundo de inatividade

    def checkSyntax(self):
        if not self.currentFile:
            return

        self.clearProblems()
        code = self.editor.text()
        file_extension = os.path.splitext(self.currentFile)[1].lower()

        if file_extension == '.py':
            self.checkPythonSyntax(code)
        elif file_extension == '.cpp':
            self.checkCppSyntax(code)
        elif file_extension == '.js':
            self.checkJavaScriptSyntax(code)
        elif file_extension == '.java':
            self.checkJavaSyntax(code)
        elif file_extension == '.rb':
            self.checkRubySyntax(code)

    def checkPythonSyntax(self, code):
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            self.showProblem(e)

    def checkCppSyntax(self, code):
        process = subprocess.Popen(['g++', '-fsyntax-only', '-x', 'c++', '-'], stdin=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        _, stderr = process.communicate(input=code)

        if stderr:
            for line in stderr.splitlines():
                if ': error:' in line:
                    parts = line.split(':')
                    line_num = int(parts[1])
                    error_msg = ':'.join(parts[3:]).strip()
                    self.showProblem(SyntaxError(error_msg, ('<string>', line_num, 0, code.splitlines()[line_num-1])))

    def checkJavaScriptSyntax(self, code):
        try:
            import esprima
            esprima.parseScript(code)
        except esprima.Error as e:
            line_num = e.lineNumber
            error_msg = str(e)
            self.showProblem(SyntaxError(error_msg, ('<string>', line_num, 0, code.splitlines()[line_num-1])))

    def checkJavaSyntax(self, code):
        # Extrair o nome da classe pública (se existir)
        class_match = re.search(r'public\s+class\s+(\w+)', code)
        class_name = class_match.group(1) if class_match else 'Main'

        # Criar um arquivo temporário com o nome correto
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, f"{class_name}.java")
            with open(file_path, 'w') as temp_file:
                temp_file.write(code)

            # Compilar o arquivo Java
            process = subprocess.Popen(['javac', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            _, stderr = process.communicate()

            if stderr:
                errors = stderr.splitlines()
                for error in errors:
                    # Ignorar avisos sobre o nome do arquivo
                    if "should be declared in a file named" in error:
                        continue
                    
                    # Procurar por padrões de erro
                    match = re.search(r'(.+\.java):(\d+): error: (.*)', error)
                    if match:
                        _, reported_line_num, error_msg = match.groups()
                        try:
                            reported_line_num = int(reported_line_num)
                            code_lines = code.splitlines()
                            
                            # Usar diretamente o número da linha reportada
                            actual_line_num = reported_line_num
                            
                            if 1 <= actual_line_num <= len(code_lines):
                                error_line = code_lines[actual_line_num-1]
                            else:
                                error_line = ''
                            
                            self.showProblem(SyntaxError(error_msg, ('<string>', actual_line_num, 0, error_line)))
                        except ValueError:
                            self.showProblem(SyntaxError(error_msg, ('<string>', 1, 0, '')))
                    else:
                        # Se não conseguirmos extrair as informações do erro, mostramos a mensagem completa
                        self.showProblem(SyntaxError(error.strip(), ('<string>', 1, 0, '')))

    def checkRubySyntax(self, code):
        process = subprocess.Popen(['ruby', '-c'], stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        _, stderr = process.communicate(input=code)

        if stderr:
            for line in stderr.splitlines():
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 3:
                        try:
                            line_num = int(parts[1])
                            error_msg = ':'.join(parts[2:]).strip()
                            code_lines = code.splitlines()
                            if 1 <= line_num <= len(code_lines):
                                error_line = code_lines[line_num-1]
                            else:
                                error_line = ''
                            self.showProblem(SyntaxError(error_msg, ('<string>', line_num, 0, error_line)))
                        except ValueError:
                            # Se não conseguirmos converter o número da linha para inteiro, apenas mostramos o erro sem a linha específica
                            self.showProblem(SyntaxError(line.strip(), ('<string>', 1, 0, '')))
                    else:
                        # Se não conseguirmos separar a linha em partes suficientes, mostramos o erro completo
                        self.showProblem(SyntaxError(line.strip(), ('<string>', 1, 0, '')))

    def setupStatusBar(self):
        self.statusBar = self.statusBar()
        self.statusBar.setStyleSheet("background-color: #00031c; color: #e0e0ff;")

        self.lineColLabel = QLabel("Line 1, Col 1")
        self.encodingLabel = QLabel("UTF-8")
        self.languageLabel = QLabel("Plain Text")

        self.statusBar.addPermanentWidget(self.lineColLabel)
        self.statusBar.addPermanentWidget(self.encodingLabel)
        self.statusBar.addPermanentWidget(self.languageLabel)

    def updateLineColInfo(self):
        line, col = self.editor.getCursorPosition()
        self.lineColLabel.setText(f"Line {line + 1}, Col {col + 1}")

    def updateFileInfo(self):
        if self.currentFile:
            _, ext = os.path.splitext(self.currentFile)
            self.encodingLabel.setText(self.detectEncoding(self.currentFile))
            self.languageLabel.setText(self.getLanguage(ext))
        else:
            self.encodingLabel.setText("UTF-8")
            self.languageLabel.setText("Plain Text")

    def detectEncoding(self, file_path):
        encodings = ['utf-8', 'iso-8859-1', 'windows-1252', 'ascii']
        for enc in encodings:
            try:
                with codecs.open(file_path, 'r', encoding=enc) as f:
                    f.read()
                return enc.upper()
            except UnicodeDecodeError:
                continue
        return "Unknown"

    def getLanguage(self, ext):
        languages = {
            '.py': 'Python',
            '.java': 'Java',
            '.html': 'HTML',
            '.js': 'JavaScript',
            '.css': 'CSS',
            '.cpp': 'C++',
            '.rb': 'Ruby'
        }
        return languages.get(ext, 'Plain Text')

    def setupDebugToolbar(self):
        nextAction = QAction(QIcon('img/next.png'), 'Next', self)
        nextAction.setStatusTip('Execute next line')
        nextAction.triggered.connect(lambda: self.sendDebugCommand('n'))
        self.debugToolbar.addAction(nextAction)

        stepAction = QAction(QIcon('img/step.png'), 'Step', self)
        stepAction.setStatusTip('Step into function')
        stepAction.triggered.connect(lambda: self.sendDebugCommand('s'))
        self.debugToolbar.addAction(stepAction)

        continueAction = QAction(QIcon('img/continue.png'), 'Continue', self)
        continueAction.setStatusTip('Continue execution')
        continueAction.triggered.connect(lambda: self.sendDebugCommand('c'))
        self.debugToolbar.addAction(continueAction)

        listAction = QAction(QIcon('img/list.png'), 'List', self)
        listAction.setStatusTip('List code around current line')
        listAction.triggered.connect(lambda: self.sendDebugCommand('l'))
        self.debugToolbar.addAction(listAction)

        breakAction = QAction(QIcon('img/break.png'), 'Break', self)
        breakAction.setStatusTip('Set breakpoint')
        breakAction.triggered.connect(lambda: self.sendDebugCommand('b'))
        self.debugToolbar.addAction(breakAction)

        printAction = QAction(QIcon('img/print.png'), 'Print', self)
        printAction.setStatusTip('Print variable value')
        printAction.triggered.connect(lambda: self.sendDebugCommand('p'))
        self.debugToolbar.addAction(printAction)

        quitAction = QAction(QIcon('img/quit.png'), 'Quit', self)
        quitAction.setStatusTip('Quit debugger')
        quitAction.triggered.connect(lambda: self.sendDebugCommand('q'))
        self.debugToolbar.addAction(quitAction)

    def sendDebugCommand(self, command):
        if self.process and self.process.state() == QProcess.Running:
            self.process.write((command + '\n').encode())
            self.bottomTabWidget.setCurrentIndex(0)  # Switch to Output tab
    def initUI(self):
        self.setWindowTitle("ScriptBliss")
        self.setWindowIcon(QIcon('img/logo.png'))
        self.setGeometry(100, 100, 1200, 800)
        self.showMaximized()

        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(30, 30, 60))
        dark_palette.setColor(QPalette.WindowText, QColor("#e0e0ff"))
        dark_palette.setColor(QPalette.Base, QColor(20, 20, 40))
        dark_palette.setColor(QPalette.AlternateBase, QColor(40, 40, 60))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, QColor("#e0e0ff"))
        dark_palette.setColor(QPalette.Button, QColor(45, 45, 70))
        dark_palette.setColor(QPalette.ButtonText, QColor("#e0e0ff"))
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(dark_palette)

        self.editor = QsciScintilla()
        self.imageViewer = QLabel()
        self.imageViewer.setAlignment(Qt.AlignCenter)
        self.imageViewer.setStyleSheet("background-color: #1e1e3e;")

        # Crie o widget de boas-vindas
        self.welcomeWidget = QLabel()
        self.welcomeWidget.setPixmap(QPixmap('img/logo_inicio.png'))
        self.welcomeWidget.setAlignment(Qt.AlignCenter)
        self.welcomeWidget.setStyleSheet("background-color: #1e1e3e;")

        self.editor.setUtf8(True)  # Ensure the editor is in UTF-8 mode
        self.editor.setCaretForegroundColor(QColor("#00091a"))
        # Define a largura da tabulação para 4 espaços
        self.editor.setTabWidth(4) 
        # Conecta o evento de tecla pressionada do editor
        self.editor.keyPressEvent = self.editorKeyPressEvent
        self.editor.cursorPositionChanged.connect(self.updateLineColInfo)

        font = QFont()
        font.setFamily('Consolas')  # This font is good for a wide range of UTF-8 characters
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.editor.setFont(font)
        self.editor.setMarginsFont(font)

        fontmetrics = QFontMetrics(font)
        self.editor.setMarginsFont(font)
        self.editor.setMarginWidth(0, fontmetrics.width("00000") + 6)
        self.editor.setMarginLineNumbers(0, True)
        self.editor.setMarginsBackgroundColor(QColor("#1e1e3e"))
        self.editor.setMarginsForegroundColor(QColor("#ffffff"))

        self.editor.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.editor.setCaretLineVisible(True)
        self.editor.setCaretLineBackgroundColor(QColor("#dee8ff"))
        self.editor.setIndentationsUseTabs(False)
        self.editor.setIndentationGuides(True)
        self.editor.setTabIndents(True)
        self.editor.setAutoIndent(True)

        lexer = QsciLexerPython()
        lexer.setDefaultFont(font)
        self.editor.setLexer(lexer)

        self.fileSystemModel = CustomFileSystemModel()
        self.fileSystemModel.setRootPath(self.projectPath)

        self.treeView = DraggableTreeView()
        self.treeView.setModel(self.fileSystemModel)
        self.treeView.setRootIndex(self.fileSystemModel.index(self.projectPath))
        self.treeView.clicked.connect(self.onFileClicked)
        self.treeView.setHeaderHidden(True)
        self.treeView.setIndentation(10)
        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.showContextMenu)
        self.treeView.dropped.connect(self.onDropped)

        self.treeView.setColumnHidden(1, True)
        self.treeView.setColumnHidden(2, True)
        self.treeView.setColumnHidden(3, True)

        self.treeView.setMinimumWidth(200)
        self.treeView.setMaximumWidth(200)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(font)
        self.console.setStyleSheet("background-color: #00091a; color: #c9dcff;")

        self.terminal = QTextEdit()
        self.terminal.setReadOnly(False)
        self.terminal.setFont(font)
        self.terminal.setStyleSheet("background-color: #00092a; color: #c9dcff;")
        self.terminal.keyPressEvent = self.terminalKeyPressEvent

        self.problemsWidget = QTextEdit()
        self.problemsWidget.setReadOnly(True)
        self.problemsWidget.setStyleSheet("background-color: #00093a; color: #ff8c8c;")
        
        self.bottomTabWidget = QTabWidget()
        self.bottomTabWidget.addTab(self.console, "Output")
        self.bottomTabWidget.addTab(self.terminal, "Terminal")
        self.bottomTabWidget.addTab(self.problemsWidget, "Problems")
        self.bottomTabWidget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #1e1e3e;
                background-color: #1e1e3e;
            }
            QTabBar::tab {
                background-color: #1e1e3e;
                color: #e0e0ff;
                padding: 5px;
                border: 1px solid #1e1e3e;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #2e2e5e;
                border: 1px solid #2e2e5e;
                border-bottom: 1px solid #1e1e3e;
            }
            QTabBar::tab:hover {
                background-color: #2e2e5e;
            }
        """)

        self.splitter1 = QSplitter(Qt.Horizontal)
        self.splitter1.addWidget(self.treeView)
        self.splitter1.addWidget(self.welcomeWidget)
        self.splitter1.setSizes([200, 1000])
        self.splitter1.setHandleWidth(0)

        splitter2 = QSplitter(Qt.Vertical)
        splitter2.addWidget(self.splitter1)
        splitter2.addWidget(self.bottomTabWidget)
        splitter2.setSizes([580, 200])
        splitter2.setHandleWidth(0)

        self.setCentralWidget(splitter2)

        self.setupMenuBar()
        self.setupStatusBar()

    def setupAutocomplete(self):
        self.editor.setAutoCompletionSource(QsciScintilla.AcsAll)
        self.editor.setAutoCompletionThreshold(1)
        self.editor.setAutoCompletionCaseSensitivity(False)
        self.editor.setAutoCompletionReplaceWord(True)

    def onDropped(self, links):
        for link in links:
            info = QFileInfo(link)
            if info.isDir():
                QMessageBox.information(self, "Dropped directory", "Dropping directories is not supported")
            else:
                newDir = self.treeView.model().filePath(self.treeView.indexAt(self.treeView.viewport().mapFromGlobal(QCursor.pos())))
                newPath = os.path.join(newDir, info.fileName())
                if newPath != link:  # Não mova se for o mesmo local
                    try:
                        shutil.move(link, newPath)
                    except Exception as e:
                        print("Ok")
        
    def editorKeyPressEvent(self, event):
        super(QsciScintilla, self.editor).keyPressEvent(event)

        # Obter a posição atual do cursor
        line, index = self.editor.getCursorPosition()

        if event.key() == Qt.Key_ParenLeft:  # (
            self.editor.insert(")")
            self.editor.setCursorPosition(line, index)

        elif event.key() == Qt.Key_BracketLeft:  # [
            self.editor.insert("]")
            self.editor.setCursorPosition(line, index)

        elif event.key() == Qt.Key_BraceLeft:  # {
            self.editor.insert("}")
            self.editor.setCursorPosition(line, index)

        elif event.key() == Qt.Key_QuoteDbl:  # "
            self.editor.insert('"')
            self.editor.setCursorPosition(line, index)

        elif event.key() == Qt.Key_Apostrophe:  # '
            self.editor.insert("'")
            self.editor.setCursorPosition(line, index)

    def setupMenuBar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #1e1e3e;
                color: #e0e0ff;
            }
            QMenuBar::item {
                background-color: #1e1e3e;
                color: #e0e0ff;
            }
            QMenuBar::item:selected {
                background-color: #2e2e5e;
            }
            QMenu {
                background-color: #1e1e3e;
                color: #e0e0ff;
            }
            QMenu::item:selected {
                background-color: #2e2e5e;
            }
        """)
        fileMenu = menubar.addMenu('&File')
        runMenu = menubar.addMenu('&Run')
        gitMenu = menubar.addMenu('&Git')
        compilerMenu = menubar.addMenu('&Compilers')

        newFile = QAction(QIcon('img/new.png'), 'New', self)
        newFile.setShortcut('Ctrl+N')
        newFile.setStatusTip('Create new file')
        newFile.triggered.connect(self.newFile)

        newFolderAction = QAction(QIcon('img/new_folder.png'), 'New Folder', self)
        newFolderAction.setShortcut('Ctrl+Shift+N')
        newFolderAction.setStatusTip('Create new folder')
        newFolderAction.triggered.connect(lambda: self.createFolder(self.treeView.rootIndex()))

        openFile = QAction(QIcon('img/open.png'), 'Open', self)
        openFile.setShortcut('Ctrl+O')
        openFile.setStatusTip('Open existing file')
        openFile.triggered.connect(self.openFileDialog)

        openFolder = QAction(QIcon('img/folder.png'), 'Open Folder', self)
        openFolder.setShortcut('Ctrl+Shift+O')
        openFolder.setStatusTip('Open folder as project')
        openFolder.triggered.connect(self.openFolderDialog)

        saveFile = QAction(QIcon('img/save.png'), 'Save', self)
        saveFile.setShortcut('Ctrl+S')
        saveFile.setStatusTip('Save current file')
        saveFile.triggered.connect(self.saveFileDialog)

        self.autosaveAction = QAction(QIcon('img/autosave.png'), 'Enable Autosave', self)
        self.autosaveAction.setCheckable(True)
        self.autosaveAction.setStatusTip('Toggle autosave functionality')
        self.autosaveAction.triggered.connect(self.toggleAutosave)

        runAction = QAction(QIcon('img/run.png'), 'Run Code', self)
        runAction.setShortcut('Ctrl+R')
        runAction.setStatusTip('Run Code')
        runAction.triggered.connect(self.runCode)

        gitCommit = QAction(QIcon('img/commit.png'), 'Commit', self)
        gitCommit.setStatusTip('Commit changes')
        gitCommit.triggered.connect(self.gitCommit)

        gitPush = QAction(QIcon('img/push.png'), 'Push', self)
        gitPush.setStatusTip('Push changes')
        gitPush.triggered.connect(self.gitPush)

        gitPull = QAction(QIcon('img/pull.png'), 'Pull', self)
        gitPull.setStatusTip('Pull changes')
        gitPull.triggered.connect(self.gitPull)

        cloneRepo = QAction(QIcon('img/clone.png'), 'Clone Repository', self)
        cloneRepo.setStatusTip('Clone a repository from GitHub')
        cloneRepo.triggered.connect(self.cloneRepository)

        debugMenu = menubar.addMenu('&Debug')
        debugAction = QAction(QIcon('img/debug.png'), 'Debug Code', self)
        debugAction.setShortcut('Ctrl+Shift+R')
        debugAction.setStatusTip('Debug Code')
        debugAction.triggered.connect(self.debugCode)
        debugMenu.addAction(debugAction)

        fileMenu.addAction(newFile)
        fileMenu.addAction(newFolderAction)
        fileMenu.addAction(openFile)
        fileMenu.addAction(openFolder)
        fileMenu.addAction(saveFile)
        fileMenu.addAction(self.autosaveAction)
        runMenu.addAction(runAction)
        gitMenu.addAction(gitCommit)
        gitMenu.addAction(gitPush)
        gitMenu.addAction(gitPull)
        gitMenu.addAction(cloneRepo)

        # Compilers Menu
        pythonCompiler = QAction(QIcon('img/python.png'),'Python', self)
        pythonCompiler.setStatusTip('Download Python Compiler')
        pythonCompiler.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://www.python.org/downloads/')))

        javaCompiler = QAction(QIcon('img/java.png'),'Java', self)
        javaCompiler.setStatusTip('Download Java Compiler')
        javaCompiler.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://www.oracle.com/java/technologies/javase-jdk11-downloads.html')))

        cppCompiler = QAction(QIcon('img/cpp.png'),'C++', self)
        cppCompiler.setStatusTip('Download C++ Compiler')
        cppCompiler.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://www.mingw-w64.org/downloads/')))

        rubyCompiler = QAction(QIcon('img/ruby.png'),'Ruby', self)
        rubyCompiler.setStatusTip('Download Ruby Compiler')
        rubyCompiler.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://www.ruby-lang.org/en/downloads/')))

        jsCompiler = QAction(QIcon('img/javascript.png'),'JavaScript', self)
        jsCompiler.setStatusTip('Download JavaScript Compiler')
        jsCompiler.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://nodejs.org/en/download/package-manager')))

        compilerMenu.addAction(pythonCompiler)
        compilerMenu.addAction(javaCompiler)
        compilerMenu.addAction(cppCompiler)
        compilerMenu.addAction(rubyCompiler)
        compilerMenu.addAction(jsCompiler)

    def debugCode(self):
        if self.currentFile and self.currentFile.endswith('.py'):
            self.console.clear()
            self.terminal.clear()

            command = f'python -m pdb "{self.currentFile}"'
            self.process = QProcess()
            self.process.setProcessChannelMode(QProcess.SeparateChannels)
            self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
            self.process.readyReadStandardError.connect(self.updateConsoleOutput)
            self.process.finished.connect(self.processFinished)
            self.process.start(command)

            self.debugToolbar.setVisible(True)  # Mostrar a barra de ferramentas de depuração
            self.bottomTabWidget.setCurrentIndex(0)  # Switch to Output tab

    def newFile(self):
        text, ok = QInputDialog.getText(self, 'New File', 'Enter file name:')
        if ok and text:
            self.currentFile = os.path.join(self.projectPath, text)
            with open(self.currentFile, 'w') as f:
                f.write('')
            self.editor.setText("")
            self.setWindowTitle(f"ScriptBliss - {self.currentFile}")
            self.treeView.setRootIndex(self.fileSystemModel.index(self.projectPath))
            self.updateFileInfo()

    def openFileDialog(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Open File", self.projectPath,
                                                  "All Files (*);;Python Files (*.py);;Java Files (*.java);;HTML Files (*.html);;JavaScript Files (*.js);;CSS Files (*.css);;C++ Files (*.cpp);;Ruby Files (*.rb);;Image Files (*.png *.jpg *.jpeg *.bmp *.gif)", options=options)
        if fileName:
            self.loadFile(fileName)
            self.updateTreeViewForFile(fileName)
            self.updateFileInfo()

    def openFolderDialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder", QDir.currentPath())
        if folder:
            self.projectPath = folder
            self.fileSystemModel.setRootPath(folder)
            self.treeView.setRootIndex(self.fileSystemModel.index(folder))
            
            # Limpar o editor
            self.editor.clear()
            self.currentFile = ''
            self.setWindowTitle("ScriptBliss")
            
            # Limpar console e terminal
            self.console.clear()
            self.terminal.clear()
            
            # Restaurar o widget de boas-vindas
            self.splitter1.replaceWidget(1, self.welcomeWidget)
            
            self.updateFileInfo()

    def loadFile(self, fileName):
        self.console.clear()
        self.terminal.clear()
        self.clearProblems()
        self.currentFile = fileName
        if fileName.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            self.displayImage(fileName)
        else:
            encodings = ['utf-8', 'iso-8859-1', 'windows-1252', 'ascii']
            for encoding in encodings:
                try:
                    with codecs.open(fileName, 'r', encoding=encoding) as f:
                        code = f.read()
                        self.editor.setText(code.rstrip('\n')) 
                        self.setWindowTitle(f"ScriptBliss - {fileName}")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                QMessageBox.critical(self, "Error", f"Unable to decode the file {fileName} with any of the attempted encodings.")
                return

            # Set the appropriate lexer based on the file extension
            if fileName.endswith('.py'):
                lexer = QsciLexerPython()
            elif fileName.endswith('.java'):
                lexer = QsciLexerJava()
            elif fileName.endswith('.html'):
                lexer = QsciLexerHTML()
            elif fileName.endswith('.js'):
                lexer = QsciLexerJavaScript()
            elif fileName.endswith('.css'):
                lexer = QsciLexerCSS()
            elif fileName.endswith('.cpp'):
                lexer = QsciLexerCPP()
            elif fileName.endswith('.rb'):
                lexer = QsciLexerRuby()
            else:
                lexer = None

            if lexer:
                lexer.setDefaultFont(QFont("Consolas", 10))
                self.editor.setLexer(lexer)

            self.updateFileInfo()

            # Substitua o widget de boas-vindas pelo editor
            if self.splitter1.widget(1) != self.editor:
                self.splitter1.replaceWidget(1, self.editor)

        self.updateTreeViewForFile(fileName)

    def updateTreeViewForFile(self, fileName):
        # Obter o diretório do arquivo
        fileDir = os.path.dirname(fileName)
        
        # Definir o diretório do arquivo como raiz do treeView
        self.fileSystemModel.setRootPath(fileDir)
        self.treeView.setRootIndex(self.fileSystemModel.index(fileDir))
        
        # Expandir até o arquivo selecionado
        index = self.fileSystemModel.index(fileName)
        self.treeView.scrollTo(index)
        self.treeView.setCurrentIndex(index)
        self.treeView.expand(index.parent())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'imageLabel') and hasattr(self, 'scrollArea'):
            self.updateImageSize()

    def updateImageSize(self):
        if self.currentFile and self.currentFile.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            available_size = self.splitter1.widget(1).size()
            pixmap = QPixmap(self.currentFile)
            scaled_pixmap = pixmap.scaled(available_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.imageLabel.setPixmap(scaled_pixmap)

    def displayImage(self, fileName):
        try:
            pixmap = QPixmap(fileName)
            
            # Get the size of the splitter widget where the image will be displayed
            available_size = self.splitter1.widget(1).size()
            
            # Scale the pixmap to fit within the available size while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(available_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Create a new QLabel to hold the scaled image
            imageLabel = QLabel()
            imageLabel.setPixmap(scaled_pixmap)
            imageLabel.setAlignment(Qt.AlignCenter)
            imageLabel.setStyleSheet("background-color: #1e1e3e;")
            
            # Create a scroll area to allow scrolling if the image is still larger than the available space
            scrollArea = QScrollArea()
            scrollArea.setWidget(imageLabel)
            scrollArea.setWidgetResizable(True)
            scrollArea.setStyleSheet("background-color: #1e1e3e;")
            
            # Replace the current widget in the splitter with the scroll area
            self.splitter1.replaceWidget(1, scrollArea)
            
            # Store references to the new widgets
            self.imageLabel = imageLabel
            self.scrollArea = scrollArea
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to display image: {str(e)}")

        # Update the window title
        self.setWindowTitle(f"ScriptBliss - {fileName}")

    def saveFileDialog(self):
        if self.currentFile:
            fileName = self.currentFile
        else:
            options = QFileDialog.Options()
            fileName, _ = QFileDialog.getSaveFileName(self, "Save File", self.projectPath,
                                                    "All Files (*);;Python Files (*.py);;Java Files (*.java);;HTML Files (*.html);;JavaScript Files (*.js);;CSS Files (*.css);;C++ Files (*.cpp);;Ruby Files (*.rb)", options=options)
        if fileName:
            with open(fileName, 'w', newline='') as f:  # Add newline='' parameter
                code = self.editor.text()
                f.write(code.rstrip('\n'))  # Remove trailing newlines before saving
            self.currentFile = fileName
            self.setWindowTitle(f"ScriptBliss - {fileName}")

    def toggleAutosave(self, checked):
        if checked:
            self.autosaveTimer = QTimer(self)
            self.autosaveTimer.timeout.connect(self.autosave)
            self.autosaveTimer.start(1000)  # Autosave every 1 seconds
            self.autosaveAction.setText('Autosave Enabled')
        else:
            if hasattr(self, 'autosaveTimer'):
                self.autosaveTimer.stop()
            self.autosaveAction.setText('Enable Autosave')

    def autosave(self):
        if self.currentFile:
            with open(self.currentFile, 'w', newline='') as f:  # Add newline='' parameter
                code = self.editor.text()
                f.write(code.rstrip('\n'))  # Remove trailing newlines before saving

    def runCode(self):
        if self.currentFile:
            self.console.clear()
            self.terminal.clear()

            if self.currentFile.endswith('.py'):
                # Detecta a codificação do arquivo
                encodings = ['utf-8', 'iso-8859-1', 'windows-1252', 'ascii']
                detected_encoding = None
                for encoding in encodings:
                    try:
                        with codecs.open(self.currentFile, 'r', encoding=encoding) as f:
                            f.read()
                        detected_encoding = encoding
                        break
                    except UnicodeDecodeError:
                        continue
                
                if detected_encoding:
                    command = f'python -X utf8=0 -c "import codecs; exec(codecs.open(\'{self.currentFile}\', encoding=\'{detected_encoding}\').read())"'
                else:
                    command = f'python "{self.currentFile}"'
                
                self.process = QProcess(self)
                self.process.setProcessChannelMode(QProcess.SeparateChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleError)
                self.process.finished.connect(self.processFinished)
                self.process.start(command)

            elif self.currentFile.endswith('.java'):
                compile_command = f'javac "{self.currentFile}"'
                self.process = QProcess()
                self.process.start(compile_command)
                self.process.waitForFinished()
                compile_output = self.process.readAllStandardOutput().data().decode()
                compile_error = self.process.readAllStandardError().data().decode()

                if compile_error:
                    self.console.append(f"<span style='color:#ff8c8c;'>{compile_error}</span>")
                    return

                class_name = os.path.splitext(os.path.basename(self.currentFile))[0]
                run_command = f'java -cp "{os.path.dirname(self.currentFile)}" {class_name}'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.SeparateChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)
                self.process.finished.connect(self.processFinished)
                self.process.start(run_command)

            elif self.currentFile.endswith('.cpp'):
                executable = self.currentFile[:-4]
                compile_command = f'g++ "{self.currentFile}" -o "{executable}"'
                run_command = f'"{executable}"'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.SeparateChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)

                self.process.start(compile_command)
                self.process.waitForFinished()
                compile_output = self.process.readAllStandardOutput().data().decode()
                compile_error = self.process.readAllStandardError().data().decode()

                if compile_error:
                    self.console.append(f"<span style='color: #ff8c8c;'>{compile_error}</span>")
                    return

                self.process.start(run_command)
                self.process.finished.connect(self.processFinished)

            elif self.currentFile.endswith('.rb'):
                command = f'ruby "{self.currentFile}"'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.SeparateChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)
                self.process.finished.connect(self.processFinished)
                self.process.start(command)

            elif self.currentFile.endswith('.html'):
                html_file_path = f'file://{os.path.abspath(self.currentFile)}'
                webbrowser.open(html_file_path)
                self.console.append(f"Opened {self.currentFile} in the default web browser.")

            elif self.currentFile.endswith('.js'):
                # Ensure Node.js is installed and the path is correct
                command = f'node "{self.currentFile}"'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.SeparateChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)
                self.process.finished.connect(self.processFinished)
                self.process.start(command)
   
            elif self.currentFile.endswith('.css'):
                self.console.append("Cannot execute CSS files directly.")

            else:
                self.console.append("Unsupported file format for direct execution.")
                return
            
        self.debugToolbar.setVisible(False)  # Ocultar a barra de ferramentas de depuração
        self.bottomTabWidget.setCurrentIndex(0)  # Switch to Output tab

    def updateConsoleOutput(self):
        if not self.process:
            return

        encodings = ['utf-8', 'cp1252', 'iso-8859-1', 'ascii']
        
        for encoding in encodings:
            try:
                output = self.process.readAllStandardOutput().data().decode(encoding)
                if output:
                    self.console.append(f"<span style='color: #c9dcff;'>{output}</span>")
                return
            except UnicodeDecodeError:
                continue
        
        self.console.append("<span style='color: #ff8c8c;'>Failed to decode output. Try converting the file to UTF-8.</span>")
   
    def updateConsoleError(self):
        if not self.process:
            return

        encodings = ['utf-8', 'cp1252', 'iso-8859-1', 'ascii']
        
        for encoding in encodings:
            try:
                error = self.process.readAllStandardError().data().decode(encoding)
                if error:
                    self.console.append(f"<span style='color: #ff8c8c;'>{error}</span>")
                return
            except UnicodeDecodeError:
                continue
        
        self.console.append("<span style='color: #ff8c8c;'>Failed to decode error output. Try converting the file to UTF-8.</span>")
        
    def processFinished(self):
        if not self.process:
            return

        exit_code = self.process.exitCode()
        exit_status = self.process.exitStatus()

        if exit_status == QProcess.CrashExit:
            self.console.append("<span style='color: #ff8c8c;'>Process crashed.</span>")
        elif exit_code != 0:
            self.console.append(f"<span style='color: #ff8c8c;'>Process finished with exit code {exit_code}. Check the output above for error details.</span>")
        else:
            self.console.append("<span style='color: #c9dcff;'>Process finished successfully.</span>")

        # Capture any remaining output
        self.updateConsoleOutput()
        self.updateConsoleError()

        self.debugToolbar.setVisible(False)
        self.process = None

    def cloneRepository(self):
        repo_url, ok = QInputDialog.getText(self, 'Clone Repository', 'Enter repository URL:')
        if ok and repo_url:
            target_path = QFileDialog.getExistingDirectory(self, "Select Directory to Clone Into")
            if target_path:
                process = QProcess()
                process.setWorkingDirectory(target_path)
                process.start('git', ['clone', repo_url])
                process.finished.connect(lambda: self.updateTreeView(target_path))

    def updateTreeView(self, path):
        self.projectPath = path
        self.fileSystemModel.setRootPath(path)
        self.treeView.setRootIndex(self.fileSystemModel.index(path))

    def gitCommit(self):
        message, ok = QInputDialog.getText(self, 'Git Commit', 'Enter commit message:')
        if ok and message:
            process = QProcess()
            process.start(f'git commit -am "{message}"')
            process.waitForFinished()
            output = process.readAllStandardOutput().data().decode()
            error = process.readAllStandardError().data().decode()
            self.console.append(output + '\n' + error)

    def gitPush(self):
        process = QProcess()
        process.start('git push')
        process.waitForFinished()
        output = process.readAllStandardOutput().data().decode()
        error = process.readAllStandardError().data().decode()
        self.console.append(output + '\n' + error)

    def gitPull(self):
        process = QProcess()
        process.start('git pull')
        process.waitForFinished()
        output = process.readAllStandardOutput().data().decode()
        error = process.readAllStandardError().data().decode()
        self.console.append(output + '\n' + error)

    def onFileClicked(self, index):
        if not self.fileSystemModel.isDir(index):
            fileName = self.fileSystemModel.filePath(index)
            if fileName.endswith(('.exe', '.zip', '.class')):
                QMessageBox.information(self, "Incompatible format", "This file type cannot be viewed in the IDE.")
            else:
                self.loadFile(fileName)
                self.treeView.setRootIndex(self.fileSystemModel.index(self.projectPath))


    def terminalKeyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            command = self.terminal.toPlainText().splitlines()[-1]
            if self.process and self.process.state() == QProcess.Running:
                self.process.write((command + '\n').encode())
                self.bottomTabWidget.setCurrentIndex(0)  # Switch to Output tab
            else:
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, error = process.communicate()
                self.terminal.append(output.decode() + error.decode())
        else:
            QTextEdit.keyPressEvent(self.terminal, event)

    def showContextMenu(self, point: QPoint):
        index = self.treeView.indexAt(point)
        if index.isValid():
            contextMenu = QMenu(self)
            deleteAction = QAction(QIcon('img/delete.png'), 'Delete', self)
            deleteAction.triggered.connect(lambda: self.deleteFile(index))
            renameAction = QAction(QIcon('img/rename.png'), 'Rename', self)
            renameAction.triggered.connect(lambda: self.renameFile(index))
            contextMenu.addAction(deleteAction)
            contextMenu.addAction(renameAction)
            contextMenu.exec_(self.treeView.mapToGlobal(point))

    def createFolder(self, parentIndex):
        folderName, ok = QInputDialog.getText(self, 'Create Folder', 'Enter folder name:')
        if ok and folderName:
            parentPath = self.fileSystemModel.filePath(parentIndex)
            newFolderPath = os.path.join(parentPath, folderName)
            try:
                os.mkdir(newFolderPath)
                self.treeView.setExpanded(parentIndex, True)
                newIndex = self.fileSystemModel.index(newFolderPath)
                self.treeView.scrollTo(newIndex)
                self.treeView.setCurrentIndex(newIndex)
            except OSError as e:
                self.showErrorMessage("Error", f"Failed to create folder: {str(e)}")

    def deleteFile(self, index=None):
        if index is None:
            index = self.treeView.currentIndex()
        filePath = self.fileSystemModel.filePath(index)
        if QMessageBox.question(self, 'Delete', f'Are you sure you want to delete "{filePath}"?', QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                if os.path.isfile(filePath):
                    os.remove(filePath)
                elif os.path.isdir(filePath):
                    import shutil
                    shutil.rmtree(filePath)
                self.treeView.setRootIndex(self.fileSystemModel.index(self.projectPath))
            except OSError as e:
                self.showErrorMessage("Error", f"Failed to delete: {str(e)}")

        # Limpar o editor
        self.editor.clear()
        self.currentFile = ''
        self.setWindowTitle("ScriptBliss")
        
        # Limpar console e terminal
        self.console.clear()
        self.terminal.clear()

        # Restaurar o widget de boas-vindas
        self.splitter1.replaceWidget(1, self.welcomeWidget)

    def renameFile(self, index=None):
        if index is None:
            index = self.treeView.currentIndex()
        
        filePath = self.fileSystemModel.filePath(index)
        baseName = os.path.basename(filePath)
        dirName = os.path.dirname(filePath)
        
        while True:
            newName, ok = QInputDialog.getText(self, 'Rename File', 'Enter new name:', text=baseName)
            
            if not ok or not newName:
                # Usuário cancelou ou não digitou um nome
                return
            
            if newName == baseName:
                # O nome fornecido é o mesmo que o atual
                QMessageBox.information(self, "Rename File", "The new name is the same as the current name.")
                continue
            
            newFilePath = os.path.join(dirName, newName)
            
            if os.path.exists(newFilePath):
                # O arquivo com o novo nome já existe
                QMessageBox.warning(self, "Rename File", "A file with this name already exists. Please choose a different name.")
            else:
                # Tudo certo para renomear
                try:
                    os.rename(filePath, newFilePath)
                    # Atualiza a visualização do diretório no tree view
                    self.treeView.setRootIndex(self.fileSystemModel.index(self.projectPath))
                    return
                except OSError as e:
                    QMessageBox.critical(self, "Rename File", f"Failed to rename file: {e}")
                    return

if __name__ == '__main__':
    def exception_hook(exctype, value, traceback):
        print(exctype, value, traceback)
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)

    sys._excepthook = sys.excepthook
    sys.excepthook = exception_hook
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())