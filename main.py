import sys
import os
import subprocess
import webbrowser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTreeView, QFileSystemModel, QSplitter, QTextEdit,
                             QTabWidget, QMenu, QAction, QInputDialog, QMessageBox, QLabel, QFileDialog, QVBoxLayout, QWidget)
from PyQt5.QtGui import (QIcon, QColor, QPalette, QFont, QFontMetrics, QPixmap, QDesktopServices)
from PyQt5.QtCore import (Qt, QDir, QProcess, QTimer, QUrl, QPoint)
from PyQt5.Qsci import (QsciScintilla, QsciLexerPython, QsciLexerJava, QsciLexerHTML, QsciLexerJavaScript,
                        QsciLexerCSS, QsciLexerCPP, QsciLexerRuby)

class CustomFileSystemModel(QFileSystemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_map = {
            '.cpp': QIcon('img/cpp.png'),
            '.css': QIcon('img/css.png'),
            '.java': QIcon('img/java.png'),
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.currentFile = ''
        self.projectPath = QDir.currentPath()
        self.process = None
        self.initUI()

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
        self.editor.setUtf8(True)  # Ensure the editor is in UTF-8 mode
        self.editor.setCaretForegroundColor(QColor("#00091a"))
        # Define a largura da tabulação para 4 espaços
        self.editor.setTabWidth(4) 
        # Conecta o evento de tecla pressionada do editorasdasd
        self.editor.keyPressEvent = self.editorKeyPressEvent

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

        lexer = QsciLexerPython()
        lexer.setDefaultFont(font)
        self.editor.setLexer(lexer)

        self.fileSystemModel = CustomFileSystemModel()
        self.fileSystemModel.setRootPath(self.projectPath)

        self.treeView = QTreeView()
        self.treeView.setModel(self.fileSystemModel)
        self.treeView.setRootIndex(self.fileSystemModel.index(self.projectPath))
        self.treeView.clicked.connect(self.onFileClicked)
        self.treeView.setHeaderHidden(True)
        self.treeView.setIndentation(10)
        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.showContextMenu)

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

        self.bottomTabWidget = QTabWidget()
        self.bottomTabWidget.addTab(self.console, "Output")
        self.bottomTabWidget.addTab(self.terminal, "Terminal")
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
        self.splitter1.addWidget(self.editor)
        self.splitter1.setSizes([200, 1000])
        self.splitter1.setHandleWidth(0)

        splitter2 = QSplitter(Qt.Vertical)
        splitter2.addWidget(self.splitter1)
        splitter2.addWidget(self.bottomTabWidget)
        splitter2.setSizes([580, 200])
        splitter2.setHandleWidth(0)

        self.setCentralWidget(splitter2)

        self.setupMenuBar()

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

        fileMenu.addAction(newFile)
        fileMenu.addAction(openFile)
        fileMenu.addAction(openFolder)
        fileMenu.addAction(saveFile)
        runMenu.addAction(runAction)
        gitMenu.addAction(gitCommit)
        gitMenu.addAction(gitPush)
        gitMenu.addAction(gitPull)

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

        phpCompiler = QAction(QIcon('img/php.png'),'PHP', self)
        phpCompiler.setStatusTip('Download PHP Compiler')
        phpCompiler.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://www.php.net/downloads')))

        jsCompiler = QAction(QIcon('img/javascript.png'),'JavaScript', self)
        jsCompiler.setStatusTip('Download JavaScript Compiler')
        jsCompiler.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('https://nodejs.org/en/download/package-manager')))

        compilerMenu.addAction(pythonCompiler)
        compilerMenu.addAction(javaCompiler)
        compilerMenu.addAction(cppCompiler)
        compilerMenu.addAction(rubyCompiler)
        compilerMenu.addAction(phpCompiler)
        compilerMenu.addAction(jsCompiler)

    def newFile(self):
        text, ok = QInputDialog.getText(self, 'New File', 'Enter file name:')
        if ok and text:
            self.currentFile = os.path.join(self.projectPath, text)
            with open(self.currentFile, 'w') as f:
                f.write('')
            self.editor.setText("")
            self.setWindowTitle(f"ScriptBliss - {self.currentFile}")
            self.treeView.setRootIndex(self.fileSystemModel.index(self.projectPath))

    def openFileDialog(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Open File", self.projectPath,
                                                  "All Files (*);;Python Files (*.py);;Java Files (*.java);;HTML Files (*.html);;JavaScript Files (*.js);;CSS Files (*.css);;C++ Files (*.cpp);;Ruby Files (*.rb);;Image Files (*.png *.jpg *.jpeg *.bmp *.gif)", options=options)
        if fileName:
            self.loadFile(fileName)

    def openFolderDialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder", QDir.currentPath())
        if folder:
            self.projectPath = folder
            self.fileSystemModel.setRootPath(folder)
            self.treeView.setRootIndex(self.fileSystemModel.index(folder))

    def loadFile(self, fileName):
        self.currentFile = fileName
        if fileName.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            self.displayImage(fileName)
        else:
            with open(fileName, 'r', encoding='utf-8') as f:
                code = f.read()
                self.editor.setText(code)
                self.setWindowTitle(f"ScriptBliss - {fileName}")


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

            # Restore the original self.editor if needed
            if self.splitter1.widget(1) != self.editor:
                self.splitter1.replaceWidget(1, self.editor)

    def displayImage(self, fileName):
        pixmap = QPixmap(fileName)
        self.imageViewer.setPixmap(pixmap)
        try:
            pixmap = QPixmap(fileName)
            imageLabel = QLabel()
            imageLabel.setPixmap(pixmap)
            imageLabel.setAlignment(Qt.AlignCenter)
            imageLabel.setStyleSheet("background-color: #1e1e3e;")

            # Create a new QWidget to hold the imageLabel
            imageWidget = QWidget()
            layout = QVBoxLayout(imageWidget)
            layout.addWidget(imageLabel)
            layout.setContentsMargins(0, 0, 0, 0)

            # Create a new QsciScintilla object to display the image
            imageEditor = QsciScintilla()
            imageEditor.setReadOnly(True)
            imageEditor.setText("")
            imageEditor.setMarginWidth(0, 0)
            imageEditor.setMarginWidth(1, 0)
            imageEditor.setMarginWidth(2, 0)
            imageEditor.setMinimumSize(pixmap.width(), pixmap.height())
            imageEditor.viewport().setBackgroundRole(QPalette.Dark)
            imageEditor.viewport().setAutoFillBackground(True)

            # Replace self.editor with the imageEditor
            self.splitter1.replaceWidget(1, self.imageViewer)
            self.imageEditor = imageEditor
            self.imageWidget = imageWidget
            self.imageEditor.setViewport(self.imageWidget)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to display image: {str(e)}")

    def saveFileDialog(self):
        if self.currentFile:
            fileName = self.currentFile
        else:
            options = QFileDialog.Options()
            fileName, _ = QFileDialog.getSaveFileName(self, "Save File", self.projectPath,
                                                      "All Files (*);;Python Files (*.py);;Java Files (*.java);;HTML Files (*.html);;JavaScript Files (*.js);;CSS Files (*.css);;C++ Files (*.cpp);;Ruby Files (*.rb)", options=options)
        if fileName:
            with open(fileName, 'w') as f:
                code = self.editor.text()
                f.write(code)
            self.currentFile = fileName
            self.setWindowTitle(f"ScriptBliss - {fileName}")

    def runCode(self):
        if self.currentFile:
            # Clear the output and terminal before executing the code
            self.console.clear()
            self.terminal.clear()

            if self.currentFile.endswith('.py'):
                command = f'python "{self.currentFile}"'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.MergedChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)
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
                    self.console.append(f"<span style='color:red;'>{compile_error}</span>")
                    return

                class_name = os.path.splitext(os.path.basename(self.currentFile))[0]
                run_command = f'java -cp "{os.path.dirname(self.currentFile)}" {class_name}'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.MergedChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)
                self.process.finished.connect(self.processFinished)
                self.process.start(run_command)

            elif self.currentFile.endswith('.cpp'):
                executable = self.currentFile[:-4]
                compile_command = f'g++ "{self.currentFile}" -o "{executable}"'
                run_command = f'"{executable}"'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.MergedChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)

                self.process.start(compile_command)
                self.process.waitForFinished()
                compile_output = self.process.readAllStandardOutput().data().decode()
                compile_error = self.process.readAllStandardError().data().decode()

                if compile_error:
                    self.console.append(f"<span style='color:red;'>{compile_error}</span>")
                    return

                self.process.start(run_command)
                self.process.finished.connect(self.processFinished)

            elif self.currentFile.endswith('.rb'):
                command = f'ruby "{self.currentFile}"'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.MergedChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)
                self.process.finished.connect(self.processFinished)
                self.process.start(command)

            elif self.currentFile.endswith('.php'):
                command = f'php "{self.currentFile}"'
                self.process = QProcess()
                self.process.setProcessChannelMode(QProcess.MergedChannels)
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
                self.process.setProcessChannelMode(QProcess.MergedChannels)
                self.process.readyReadStandardOutput.connect(self.updateConsoleOutput)
                self.process.readyReadStandardError.connect(self.updateConsoleOutput)
                self.process.finished.connect(self.processFinished)
                self.process.start(command)

            elif self.currentFile.endswith('.css'):
                self.console.append("Cannot execute CSS files directly.")

            else:
                self.console.append("Unsupported file format for direct execution.")
                return

        self.bottomTabWidget.setCurrentIndex(0)  # Switch to Output tab
        
    def updateConsoleOutput(self):
        output = self.process.readAllStandardOutput().data().decode()
        error = self.process.readAllStandardError().data().decode()
        if error:
            self.console.append(f"<span style='color:red;'>{error}</span>")
        else:
            self.console.append(output)

    def processFinished(self):
        if self.process.exitStatus() == QProcess.CrashExit:
            self.console.append("<span style='color:red;'>Process crashed.</span>")
        elif self.process.exitCode() != 0:
            self.console.append(f"<span style='color:red;'>Process finished with exit code {self.process.exitCode()}.</span>")
        else:
            self.console.append("<span style='color:green;'>Process finished successfully.</span>")

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
            if fileName.endswith(('.exe', '.zip')):
                QMessageBox.information(self, "Formato Incompatível", "Este tipo de arquivo não pode ser visualizado na IDE.")
            else:
                self.loadFile(fileName)


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

    def deleteFile(self, index=None):
        if index is None:
            index = self.treeView.currentIndex()
        filePath = self.fileSystemModel.filePath(index)
        if QMessageBox.question(self, 'Delete File', f'Are you sure you want to delete "{filePath}"?', QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            if os.path.isfile(filePath):
                os.remove(filePath)
            elif os.path.isdir(filePath):
                os.rmdir(filePath)
            self.treeView.setRootIndex(self.fileSystemModel.index(self.projectPath))

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
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())