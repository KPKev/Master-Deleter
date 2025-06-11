import os
import logging
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLineEdit, QTreeView, QFileDialog, QMessageBox)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor
from PyQt6.QtCore import Qt, QThread

from core.empty_folder_finder import EmptyFolderFinderWorker
from core.deleter import Deleter

class EmptyFolderFinderTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.empty_folder_thread = None
        self.empty_folder_worker = None
        self.deleter_thread = None
        self.deleter = None
        self.found_folders = []  # Track found folders during scan

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        top_bar_layout = QHBoxLayout()
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select a folder to scan...")
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_folder)
        self.scan_button = QPushButton("Scan for Empty Folders")
        self.scan_button.clicked.connect(self.start_scan)
        self.delete_button = QPushButton("Delete Selected Folders")
        self.delete_button.clicked.connect(self.delete_selected)
        
        top_bar_layout.addWidget(self.path_input, 1)
        top_bar_layout.addWidget(browse_button)
        top_bar_layout.addWidget(self.scan_button)
        top_bar_layout.addWidget(self.delete_button)
        layout.addLayout(top_bar_layout)

        self.results_tree = QTreeView()
        self.results_model = QStandardItemModel()
        self.results_model.setHorizontalHeaderLabels(["Empty Folder Path"])
        self.results_tree.setModel(self.results_model)
        self.results_tree.header().setSectionsMovable(True)
        self.results_model.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.results_tree)
    
    def browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder to Scan for Empty Folders")
        if directory:
            self.path_input.setText(directory)

    def start_scan(self):
        scan_path = self.path_input.text()
        if not scan_path or not os.path.isdir(scan_path):
            QMessageBox.warning(self, "Invalid Path", "Please select a valid folder to scan.")
            return

        self.scan_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.results_model.clear()
        self.found_folders.clear()  # Clear previous results
        self.main_window.update_status(f"Scanning for empty folders in {scan_path}...")

        self.empty_folder_thread = QThread()
        self.empty_folder_worker = EmptyFolderFinderWorker(scan_path, self.main_window.exclusions)
        self.empty_folder_worker.moveToThread(self.empty_folder_thread)

        # Connect to collect folders as they're found
        self.empty_folder_worker.empty_folder_found.connect(self.on_folder_found)
        # Connect to handle scan completion
        self.empty_folder_worker.scan_finished.connect(self.on_scan_finished)
        self.empty_folder_worker.scan_finished.connect(self.empty_folder_thread.quit)
        self.empty_folder_worker.deleteLater()
        self.empty_folder_thread.finished.connect(self.empty_folder_thread.deleteLater)

        self.empty_folder_thread.started.connect(self.empty_folder_worker.run)
        self.empty_folder_thread.start()

    def on_folder_found(self, folder_path):
        """Called when a single empty folder is found"""
        self.found_folders.append(folder_path)
        logging.info(f"Empty folder found: {folder_path}")
        # Add it to the UI immediately for real-time feedback
        item = QStandardItem(folder_path)
        item.setCheckable(True)
        item.setEditable(False)
        
        # Apply visual highlighting for restored folders (green)
        normalized_path = os.path.normpath(folder_path)
        if hasattr(self.main_window, 'recently_restored_files') and normalized_path in self.main_window.recently_restored_files:
            logging.info(f"Visual highlighting: Applying green highlighting to restored folder {folder_path}")
            item.setBackground(QColor(0, 200, 0))
            item.setForeground(QColor(255, 255, 255))  # White text for visibility
        
        self.results_model.appendRow(item)

    def on_scan_finished(self, folder_count):
        """Called when the scan is complete"""
        logging.info(f"Empty folder scan complete. Found {folder_count} folders.")
        self.scan_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        
        if folder_count == 0:
            self.main_window.update_status("No empty folders found.")
        else:
            self.main_window.update_status(f"Found {folder_count} empty folders.")

        # Refresh highlighting after scan completes (for restoration cases)
        self.refresh_visual_highlighting()
        
        self.main_window.resize_tree_columns(self.results_tree)

    def delete_selected(self):
        checked_folders = []
        for i in range(self.results_model.rowCount()):
            item = self.results_model.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                folder_path = item.text()
                checked_folders.append({
                    'path': folder_path,
                    'size': 0,  # Folders have 0 size for deletion purposes
                    'type': 'dir',  # Mark as directory
                    'category': 'Empty Folders',  # Category for tracking
                    'name': os.path.basename(folder_path)
                })
        
        if not checked_folders:
            QMessageBox.warning(self, "No Folders Selected", "Please select the empty folders you wish to delete.")
            return

        reply = QMessageBox.question(self, 'Confirm Deletion',
                                     f"Are you sure you want to delete {len(checked_folders)} empty folders?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No: 
            return
        
        logging.info(f"Empty folder deletion: Starting deletion of {len(checked_folders)} folders")
        
        # Use the main window's robust deletion system
        self.main_window.delete_selected_files(checked_folders)
        # Connect to the main window's deletion completion handler
        self.main_window.connect_empty_folder_deletion_finished(self.on_deletion_finished)

    def on_deletion_finished(self, succeeded_items, failed_items):
        """Handle completion of empty folder deletion"""
        succeeded_count = len(succeeded_items)
        failed_count = len(failed_items)
        
        if succeeded_count > 0:
            self.main_window.update_status(f"Deleted {succeeded_count} empty folders successfully.")
            
            # Remove successfully deleted folders from the display
            succeeded_paths = {item['path'] for item in succeeded_items}
            rows_to_remove = []
            
            for i in range(self.results_model.rowCount()):
                item = self.results_model.item(i)
                if item and item.text() in succeeded_paths:
                    rows_to_remove.append(i)
            
            # Remove rows in reverse order to maintain indices
            for row in reversed(rows_to_remove):
                self.results_model.removeRow(row)
                
        if failed_count > 0:
            self.main_window.update_status(f"Failed to delete {failed_count} folders. Check logs for details.")
            
        # Re-enable the delete button if there are still items
        self.delete_button.setEnabled(self.results_model.rowCount() > 0)
        
        if succeeded_count > 0 and self.results_model.rowCount() == 0:
            self.main_window.update_status("All empty folders deleted successfully!")

    def refresh_visual_highlighting(self):
        """Refresh visual highlighting for all displayed folders"""
        for i in range(self.results_model.rowCount()):
            item = self.results_model.item(i)
            if item:
                folder_path = item.text()
                normalized_path = os.path.normpath(folder_path)
                
                # Check for restoration highlighting (green)
                if hasattr(self.main_window, 'recently_restored_files') and normalized_path in self.main_window.recently_restored_files:
                    logging.info(f"Visual highlighting: Applying green highlighting to restored folder {folder_path}")
                    item.setBackground(QColor(0, 200, 0))
                    item.setForeground(QColor(255, 255, 255))
                else:
                    # Clear any existing highlighting
                    item.setBackground(QColor())
                    item.setForeground(QColor())

    def on_item_changed(self, item):
        if item.isCheckable():
            any_checked = self.is_any_item_checked()
            self.delete_button.setEnabled(any_checked)

    def is_any_item_checked(self):
        for i in range(self.results_model.rowCount()):
            if self.results_model.item(i).checkState() == Qt.CheckState.Checked:
                return True
        return False

    def stop_worker(self):
        if self.empty_folder_thread and self.empty_folder_thread.isRunning():
            self.empty_folder_worker.stop()
            self.empty_folder_thread.quit()
            self.empty_folder_thread.wait()
        if self.deleter_thread and self.deleter_thread.isRunning():
            # The deleter doesn't have a stop method, we just wait
            self.deleter_thread.quit()
            self.deleter_thread.wait() 