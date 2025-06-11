from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTextEdit, QScrollArea)
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import os

class PreviewPanel(QWidget):
    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.setMinimumHeight(200)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.preview_widget = QLabel("Select a file to preview")
        self.preview_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.preview_widget)
        
        self.layout.addWidget(self.scroll_area)
        self.is_dark_theme = False

    def set_preview(self, path):
        if not path or not os.path.isfile(path):
            self.show_message("Not a file or no file selected.")
            return

        # Check if it's an image
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            # Scale it to fit the label while maintaining aspect ratio
            self.preview_widget.setPixmap(pixmap.scaled(
                self.preview_widget.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ))
            self.scroll_area.setWidget(self.preview_widget) # Ensure the label is the widget
        # Check if it's a text file
        elif self.is_text_file(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(4096) # Read first 4KB
                    
                    text_preview = QTextEdit()
                    text_preview.setReadOnly(True)
                    text_preview.setPlainText(content)
                    
                    # Apply theme to the new text widget
                    bg_color = "#2E2F30" if self.is_dark_theme else "#F0F0F0"
                    fg_color = "white" if self.is_dark_theme else "black"
                    text_preview.setStyleSheet(f"background-color: {bg_color}; color: {fg_color}; border: none;")

                    # Clean up the old widget before creating a new one
                    old_widget = self.scroll_area.takeWidget()
                    if old_widget:
                        old_widget.deleteLater()
                    self.scroll_area.setWidget(text_preview)

            except Exception as e:
                self.show_message(f"Could not read text file:\n{e}")
        else:
            self.show_message("Preview not available for this file type.")

    def show_message(self, message):
        # Clean up the old widget before creating a new one
        old_widget = self.scroll_area.takeWidget()
        if old_widget:
            old_widget.deleteLater()
            
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bg_color = "#2E2F30" if self.is_dark_theme else "#F0F0F0"
        fg_color = "white" if self.is_dark_theme else "black"
        label.setStyleSheet(f"background-color: {bg_color}; color: {fg_color};")
        self.scroll_area.setWidget(label)

    def set_theme(self, is_dark):
        self.is_dark_theme = is_dark
        # Update the theme of the current widget in the scroll area
        current_widget = self.scroll_area.widget()
        if current_widget:
            bg_color = "#2E2F30" if is_dark else "#F0F0F0"
            fg_color = "white" if is_dark else "black"
            current_widget.setStyleSheet(f"background-color: {bg_color}; color: {fg_color}; border: none;")

    def is_text_file(self, path):
        try:
            # A simple check to see if the file can be opened as text
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                f.read(1024)
            return True
        except Exception:
            return False 