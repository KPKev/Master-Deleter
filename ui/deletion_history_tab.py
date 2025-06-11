import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout)
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from core.deletion_logger import DELETION_LOG_FILE

class DeletionHistoryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Top controls
        top_bar = QHBoxLayout()
        refresh_button = QPushButton("Refresh History")
        refresh_button.clicked.connect(self.populate_history)
        open_log_button = QPushButton("Open Log File Location")
        open_log_button.clicked.connect(self.open_log_location)
        
        top_bar.addWidget(refresh_button)
        top_bar.addStretch()
        top_bar.addWidget(open_log_button)
        layout.addLayout(top_bar)

        # Log display
        self.history_view = QTextBrowser()
        self.history_view.setOpenExternalLinks(True)
        self.history_view.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
        layout.addWidget(self.history_view)
        
        self.populate_history()

    def populate_history(self):
        self.history_view.clear()
        if os.path.exists(DELETION_LOG_FILE):
            try:
                with open(DELETION_LOG_FILE, 'r', encoding='utf-8') as f:
                    # Read the file and display it
                    self.history_view.setText(f.read())
                    # Scroll to the bottom
                    self.history_view.verticalScrollBar().setValue(self.history_view.verticalScrollBar().maximum())
            except Exception as e:
                self.history_view.setText(f"Error reading deletion history file: {e}")
        else:
            self.history_view.setText("No deletion history found.")

    def open_log_location(self):
        log_dir = os.path.dirname(DELETION_LOG_FILE)
        if os.path.exists(log_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(log_dir)) 