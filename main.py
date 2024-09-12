import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
                             QLineEdit, QListWidget, QInputDialog, QMessageBox, QLabel)
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QObject
from urllib.parse import urlparse
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning


from twitter import download_twitter_media
from instagram import download_instagram_video
from youtube import download_youtube_video
from pinterest import download_pinterest_image


warnings.simplefilter('ignore', InsecureRequestWarning)

class WorkerSignals(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

class DownloadWorker(QRunnable):
    def __init__(self, link, save_name):
        super().__init__()
        self.link = link
        self.save_name = save_name
        self.signals = WorkerSignals()

    def run(self):
        try:
            perform_operation(self.link, self.save_name, self.signals.progress.emit)
            self.signals.finished.emit(self.save_name)
        except Exception as e:
            self.signals.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Media Downloader")
        self.setGeometry(100, 100, 800, 600)
        self.downloading_links = set()
        self.threadpool = QThreadPool()
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Title Label
        title_label = QLabel("Media Downloader")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #ffffff; margin: 20px 0;")
        main_layout.addWidget(title_label)

        # URL Input
        input_layout = QHBoxLayout()
        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText("Enter a URL")
        self.url_entry.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 2px solid #333;
                border-radius: 12px;
                padding: 10px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border: 2px solid #4a90e2;
            }
        """)
        input_layout.addWidget(self.url_entry)

        # Add Button
        self.add_button = QPushButton("Add")
        self.add_button.setStyleSheet(self.get_button_style("#4a90e2"))
        self.add_button.setFixedSize(120, 40)
        input_layout.addWidget(self.add_button)

        main_layout.addLayout(input_layout)

        # List of added links
        self.links_list = QListWidget()
        self.links_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 2px solid #333;
                border-radius: 8px;
                font-size: 14px;
                padding: 10px;
            }
            QListWidget::item {
                background-color: #333;
                border-radius: 6px;
                margin-bottom: 5px;
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
            }
        """)
        main_layout.addWidget(self.links_list)

        # Buttons
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("Download All")
        self.download_button.setStyleSheet(self.get_button_style("#27ae60"))
        button_layout.addWidget(self.download_button)

        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.setStyleSheet(self.get_button_style("#e74c3c"))
        button_layout.addWidget(self.remove_button)

        main_layout.addLayout(button_layout)

        # Status Label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #ffffff; font-size: 16px;")
        main_layout.addWidget(self.status_label)

        # Connect signals to slots
        self.download_button.clicked.connect(self.on_download_click)
        self.add_button.clicked.connect(self.add_entry)
        self.remove_button.clicked.connect(self.remove_entry)
        self.url_entry.returnPressed.connect(self.add_entry)

        # Apply dark theme
        self.set_dark_theme()

    def set_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QLabel {
                color: #ffffff;
            }
        """)

    def get_button_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 12px;
                padding: 10px;
                min-width: 140px;
            }}
            QPushButton:hover {{
                background-color: {color};
            }}
            QPushButton:pressed {{
                background-color: {color};
            }}
        """

    def add_entry(self):
        link = self.url_entry.text().strip()
        if not link:
            QMessageBox.warning(self, "Empty URL", "Please enter a URL to add.")
            return

        name, ok = QInputDialog.getText(self, "Link Name", "Enter a name for this link:")
        if ok and name:
            self.links_list.addItem(f"{name} | {link}")
            self.url_entry.clear()
        else:
            QMessageBox.warning(self, "No Name", "A name is required to add the link.")

    def remove_entry(self):
        current_item = self.links_list.currentItem()
        if current_item:
            self.links_list.takeItem(self.links_list.row(current_item))

    def on_download_click(self):
        if self.links_list.count() == 0:
            QMessageBox.warning(self, "No URLs", "Please add at least one URL to download.")
            return

        self.download_button.setEnabled(False)
        self.status_label.setText("Downloading...")
        self.process_next_download()

    def process_next_download(self):
        if self.links_list.count() > 0:
            item_text = self.links_list.item(0).text()
            name, link = item_text.split(" | ")

            if link in self.downloading_links:
                return

            self.downloading_links.add(link)

            worker = DownloadWorker(link, name)
            worker.signals.finished.connect(self.on_download_finished)
            worker.signals.error.connect(self.on_operation_error)
            self.threadpool.start(worker)
        else:
            self.download_button.setEnabled(True)
            self.url_entry.setEnabled(True)
            self.status_label.setText("All downloads completed")

    def on_download_finished(self, save_name):
        self.links_list.takeItem(0)
        link = save_name.split(" | ")[1] if " | " in save_name else save_name
        self.downloading_links.discard(link)
        QMessageBox.information(self, "Success", f"Download completed for {save_name}!")
        self.process_next_download()

    def on_operation_error(self, error_message):
        QMessageBox.critical(self, "Error", f"An error occurred: {error_message}")
        item = self.links_list.takeItem(0)
        if item:
            link = item.text().split(" | ")[1] if " | " in item.text() else item.text()
            self.downloading_links.discard(link)
        self.process_next_download()

    def closeEvent(self, event):
        if self.threadpool.activeThreadCount() > 0:
            reply = QMessageBox.question(self, 'Quit', 'Downloads are in progress. Quit anyway?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.threadpool.clear()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def perform_operation(link, save_name, progress_callback):
    parsed_url = urlparse(link)
    domain = parsed_url.netloc

    if 'x.com' in domain or 'twitter.com' in domain:
        download_twitter_media(link, save_name, progress_callback)
    elif 'instagram.com' in domain:
        download_instagram_video(link, save_name, progress_callback)
    elif 'youtube.com' in domain or 'youtu.be' in domain:
        download_youtube_video(link, save_name, progress_callback)
    elif 'pinterest.com' in domain:
        download_pinterest_image(link, save_name, progress_callback)
    else:
        raise ValueError(f"Unsupported domain: {domain}")

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()