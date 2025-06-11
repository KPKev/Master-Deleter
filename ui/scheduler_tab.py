from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QComboBox, 
                                 QDateTimeEdit, QLineEdit, QPushButton, QFileDialog)
from PyQt6.QtCore import QDateTime, pyqtSignal

class SchedulerTab(QWidget):
    schedule_settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        settings_layout = QHBoxLayout()
        self.schedule_enabled_checkbox = QCheckBox("Enable Scheduler")
        self.schedule_freq_combo = QComboBox()
        self.schedule_freq_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.schedule_time_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.schedule_time_edit.setDisplayFormat("hh:mm ap")

        self.schedule_path_input = QLineEdit()
        self.schedule_path_input.setPlaceholderText("Path to scan...")
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_for_path)

        settings_layout.addWidget(self.schedule_enabled_checkbox)
        settings_layout.addWidget(self.schedule_freq_combo)
        settings_layout.addWidget(self.schedule_time_edit)
        settings_layout.addWidget(self.schedule_path_input)
        settings_layout.addWidget(browse_button)
        layout.addLayout(settings_layout)

        auto_delete_layout = QHBoxLayout()
        self.auto_delete_checkbox = QCheckBox("Enable Automatic Deletion")
        self.auto_delete_checkbox.setToolTip("Automatically delete files in the 'Safe to Delete' category after a scheduled scan.")
        auto_delete_layout.addWidget(self.auto_delete_checkbox)
        auto_delete_layout.addStretch()
        layout.addLayout(auto_delete_layout)
        
        layout.addStretch()

        # Connect signals to a single handler
        self.schedule_enabled_checkbox.stateChanged.connect(self._emit_changes)
        self.schedule_freq_combo.currentIndexChanged.connect(self._emit_changes)
        self.schedule_time_edit.dateTimeChanged.connect(self._emit_changes)
        self.schedule_path_input.textChanged.connect(self._emit_changes)
        self.auto_delete_checkbox.stateChanged.connect(self._emit_changes)

    def _browse_for_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Path for Scheduled Scan")
        if directory:
            self.schedule_path_input.setText(directory)

    def _emit_changes(self):
        settings = self.get_schedule_settings()
        self.schedule_settings_changed.emit(settings)

    def get_schedule_settings(self):
        return {
            'enabled': self.schedule_enabled_checkbox.isChecked(),
            'frequency': self.schedule_freq_combo.currentText(),
            'time': self.schedule_time_edit.dateTime(),
            'path': self.schedule_path_input.text(),
            'auto_delete': self.auto_delete_checkbox.isChecked()
        }

    def set_schedule_settings(self, settings):
        # Block signals to prevent emitting signals when loading settings
        self.schedule_enabled_checkbox.blockSignals(True)
        self.schedule_freq_combo.blockSignals(True)
        self.schedule_time_edit.blockSignals(True)
        self.schedule_path_input.blockSignals(True)
        self.auto_delete_checkbox.blockSignals(True)

        self.schedule_enabled_checkbox.setChecked(settings.get('enabled', False))
        self.schedule_freq_combo.setCurrentText(settings.get('frequency', 'Daily'))
        self.schedule_time_edit.setDateTime(settings.get('time', QDateTime.currentDateTime()))
        self.schedule_path_input.setText(settings.get('path', ''))
        self.auto_delete_checkbox.setChecked(settings.get('auto_delete', False))

        # Unblock signals
        self.schedule_enabled_checkbox.blockSignals(False)
        self.schedule_freq_combo.blockSignals(False)
        self.schedule_time_edit.blockSignals(False)
        self.schedule_path_input.blockSignals(False)
        self.auto_delete_checkbox.blockSignals(False)

    def update_last_run(self, a, b):
        pass
