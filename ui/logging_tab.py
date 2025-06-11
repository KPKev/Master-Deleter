import logging
import os
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QComboBox, QPushButton, QLabel)
from PyQt6.QtCore import pyqtSignal, Qt, pyqtSlot, QUrl
from PyQt6.QtGui import QColor, QFont, QDesktopServices

LOG_LEVELS = {
    "DEBUG": (logging.DEBUG, QColor("gray")),
    "INFO": (logging.INFO, QColor("black")),
    "WARNING": (logging.WARNING, QColor("orange")),
    "ERROR": (logging.ERROR, QColor("red")),
    "CRITICAL": (logging.CRITICAL, QColor("purple")),
}

class QtLogHandler(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = parent
        self.widget.setReadOnly(True)

    def emit(self, record):
        level, color = LOG_LEVELS.get(record.levelname, ("INFO", QColor("black")))
        self.widget.textColor = color
        self.widget.append(self.format(record))

class LoggingTab(QWidget):
    log_level_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paused = False
        self.buffer = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        level_label = QLabel("Log Level:")
        self.level_combo = QComboBox()
        self.level_combo.addItems(LOG_LEVELS.keys())
        self.level_combo.setCurrentText("INFO")
        self.level_combo.currentTextChanged.connect(self.set_log_level)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.setCheckable(True)
        self.pause_button.clicked.connect(self.toggle_pause)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_logs)

        controls_layout.addWidget(level_label)
        controls_layout.addWidget(self.level_combo)
        controls_layout.addStretch()
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(clear_button)
        
        layout.addLayout(controls_layout)
        
        # Log Browser
        self.log_browser = QTextBrowser()
        self.log_browser.setFont(QFont("Courier", 10))
        layout.addWidget(self.log_browser)

    @pyqtSlot(str)
    def set_log_level(self, level_name):
        level, _ = LOG_LEVELS.get(level_name, ("INFO", QColor("black")))
        self.log_level_changed.emit(level)

    @pyqtSlot(bool)
    def toggle_pause(self, checked):
        self.paused = checked
        self.pause_button.setText("Resume" if checked else "Pause")
        if not checked:
            for record in self.buffer:
                self.append_log(record)
            self.buffer.clear()

    @pyqtSlot(object)
    def append_log(self, record):
        if self.paused:
            self.buffer.append(record)
            return
            
        level, color = LOG_LEVELS.get(record.levelname.upper(), ("INFO", QColor("black")))
        
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')

        self.log_browser.setTextColor(color)
        self.log_browser.append(log_format.format(record))
        self.log_browser.verticalScrollBar().setValue(self.log_browser.verticalScrollBar().maximum())

    def clear_logs(self):
        self.log_browser.clear()
