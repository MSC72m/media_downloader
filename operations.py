from PyQt5.QtCore import QObject, pyqtSignal
import random

class Operations(QObject):
    operation_done = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.entries = []

    def random_save_path(self):
        save = random.randint(50, 500)
        save_path = random.randint(save, 1000)
        return save_path

    def on_operation_done(self):
        self.operation_done.emit()

    def add_entry(self, entry_widget):
        if len(self.entries) > 9:
            return None

        self.entries.append(entry_widget)
        entry_widget.editingFinished.connect(self.on_entry_change)
        return entry_widget

    def on_entry_change(self):
        entry = self.sender()
        link = entry.text()
        if link and link not in self.entries:
            self.entries.append(link)
            print(self.entries)

operations = Operations()