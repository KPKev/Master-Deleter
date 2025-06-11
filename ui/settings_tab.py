from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal

class SettingsTab(QWidget):
    theme_changed = pyqtSignal(str)
    recycle_bin_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Theme Settings
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Futuristic Dark", "Futuristic Light"])
        self.theme_combo.currentTextChanged.connect(self.theme_changed.emit)
        
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)

        # Recycle Bin Settings
        recycle_layout = QHBoxLayout()
        recycle_label = QLabel("Use Recycle Bin:")
        self.recycle_bin_checkbox = QCheckBox()
        self.recycle_bin_checkbox.setChecked(True)
        self.recycle_bin_checkbox.toggled.connect(self.recycle_bin_changed.emit)
        
        recycle_layout.addWidget(recycle_label)
        recycle_layout.addWidget(self.recycle_bin_checkbox)
        recycle_layout.addStretch()
        layout.addLayout(recycle_layout)
        
        layout.addStretch()

    def set_theme(self, theme_name):
        # Block signals to prevent emitting a change signal when setting the initial state
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentText(theme_name)
        self.theme_combo.blockSignals(False)

    def set_recycle_bin(self, use_recycle_bin):
        # Block signals to prevent emitting a change signal when setting the initial state
        self.recycle_bin_checkbox.blockSignals(True)
        self.recycle_bin_checkbox.setChecked(use_recycle_bin)
        self.recycle_bin_checkbox.blockSignals(False)
        
    def get_current_theme(self):
        return self.theme_combo.currentText()

    def get_recycle_bin_enabled(self):
        return self.recycle_bin_checkbox.isChecked()
