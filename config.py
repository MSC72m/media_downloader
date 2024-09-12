import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class DownloadThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, link):
        super().__init__()
        self.link = link

    def run(self):
        try:
            perform_operation(self.link)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Social Media Toolkit")
        self.setGeometry(100, 100, 500, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText("Enter a URL")
        layout.addWidget(self.url_entry)

        button_layout = QHBoxLayout()
        self.download_button = QPushButton("Analyze URL and Download")
        self.download_button.clicked.connect(self.on_button_click)
        button_layout.addWidget(self.download_button)

        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.add_entry)
        button_layout.addWidget(self.add_button)

        layout.addLayout(button_layout)

        self.entries = []
        self.entry_count = 0

    def on_button_click(self):
        link = self.url_entry.text()
        self.download_button.setEnabled(False)
        self.thread = DownloadThread(link)
        self.thread.finished.connect(self.on_operation_done)
        self.thread.error.connect(self.on_operation_error)
        self.thread.start()

    def on_operation_done(self):
        self.download_button.setEnabled(True)

    def on_operation_error(self, error_message):
        self.download_button.setEnabled(True)
        # Show error message (you might want to use QMessageBox here)
        print(f"Error: {error_message}")

    def add_entry(self):
        if self.entry_count > 9:
            return

        new_entry = QLineEdit()
        new_entry.setPlaceholderText("Enter a URL")
        self.layout().addWidget(new_entry)
        self.entry_count += 1
        self.entries.append(new_entry)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()