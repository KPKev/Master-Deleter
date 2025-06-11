import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTreeView, QSplitter, QHBoxLayout, QMessageBox, QLabel,
    QLineEdit, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor
import os
import logging

from core.duplicate_finder import DuplicateFinderWorker
from ui.preview_panel import PreviewPanel

class DuplicateFinderTab(QWidget):
    delete_requested = pyqtSignal(list)

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.worker_thread = None
        self.worker = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Path selection bar
        path_bar = QHBoxLayout()
        path_bar.addWidget(QLabel("Scan Path:"))
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select a folder to scan for duplicates...")
        self.browse_button = QPushButton("Browse")
        
        path_bar.addWidget(self.path_input)
        path_bar.addWidget(self.browse_button)
        layout.addLayout(path_bar)
        
        # Top bar
        top_bar = QHBoxLayout()
        self.scan_button = QPushButton("Scan for Duplicates")
        self.scan_button.setObjectName("scan_button")
        self.delete_button = QPushButton("Delete Selected")
        self.keep_newest_button = QPushButton("Keep Newest in Each Set")
        
        top_bar.addWidget(self.scan_button)
        top_bar.addWidget(self.delete_button)
        top_bar.addWidget(self.keep_newest_button)
        top_bar.addStretch(1)
        layout.addLayout(top_bar)
        
        self.status_label = QLabel("Ready to find duplicates. Select a path and click Scan.")
        layout.addWidget(self.status_label)

        # Main content area
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Results Tree
        self.tree = QTreeView()
        self.tree.setHeaderHidden(True)
        self.model = QStandardItemModel()
        self.tree.setModel(self.model)
        
        # Preview Panel
        self.preview_panel = PreviewPanel()

        splitter.addWidget(self.tree)
        splitter.addWidget(self.preview_panel)
        splitter.setSizes([400, 200])
        layout.addWidget(splitter)

        # Connect signals
        self.browse_button.clicked.connect(self.browse_folder)
        self.scan_button.clicked.connect(self.start_scan)
        self.delete_button.clicked.connect(self.request_deletion)
        self.keep_newest_button.clicked.connect(self.select_all_but_newest)
        self.tree.selectionModel().selectionChanged.connect(self.on_selection_changed)

    def browse_folder(self):
        """Open folder dialog to select scan path"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan for Duplicates")
        if folder:
            self.path_input.setText(folder)
            logging.info(f"Duplicate finder path set to: {folder}")

    def start_scan(self):
        start_path = self.path_input.text()
        if not start_path or not os.path.isdir(start_path):
            QMessageBox.warning(self, "Invalid Path", "Please select a valid folder to scan for duplicates.")
            return

        # Stop any existing scan
        if hasattr(self, 'worker') and self.worker:
            self.worker.stop()
        if hasattr(self, 'worker_thread') and self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait(1000)  # Wait up to 1 second

        self.set_ui_enabled(False)
        self.status_label.setText(f"Scanning for duplicates in {start_path}...")
        self.model.clear()
        
        try:
            self.worker_thread = QThread()
            self.worker = DuplicateFinderWorker(start_path, self.main_window.exclusions)
            self.worker.moveToThread(self.worker_thread)

            # Connect signals with error handling
            self.worker_thread.started.connect(self.worker.run)
            self.worker.scan_finished.connect(self.on_scan_finished)
            self.worker.progress_update.connect(self.update_status)
            self.worker.duplicates_found.connect(self.populate_tree)

            # Cleanup connections
            self.worker.scan_finished.connect(self.worker_thread.quit)
            self.worker.scan_finished.connect(lambda: self.cleanup_worker())
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            
            logging.info(f"Starting duplicate scan on path: {start_path}")
            self.worker_thread.start()
            
        except Exception as e:
            logging.error(f"Failed to start duplicate scan: {e}")
            self.set_ui_enabled(True)
            self.status_label.setText("Failed to start duplicate scan.")
            QMessageBox.critical(self, "Scan Error", f"Failed to start duplicate scan: {e}")

    def cleanup_worker(self):
        """Clean up worker references"""
        try:
            if hasattr(self, 'worker') and self.worker:
                self.worker.deleteLater()
                self.worker = None
        except Exception as e:
            logging.warning(f"Error cleaning up duplicate worker: {e}")

    def set_ui_enabled(self, enabled):
        self.scan_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)
        self.keep_newest_button.setEnabled(enabled)

    def update_status(self, message):
        self.status_label.setText(message)

    def on_scan_finished(self):
        self.set_ui_enabled(True)
        
        # Check if this scan was triggered by restoration
        if hasattr(self, '_restoration_scan_active') and self._restoration_scan_active:
            self._restoration_scan_active = False
            
            # Count restored duplicates for feedback
            restored_count = 0
            for i in range(self.model.rowCount()):
                parent_item = self.model.item(i)
                if parent_item:
                    for j in range(parent_item.rowCount()):
                        name_item = parent_item.child(j, 0)
                        if name_item and name_item.foreground().color().name() == '#00ff00':  # Green text
                            restored_count += 1
            
            if restored_count > 0:
                self.main_window.update_status(f"Restoration scan complete. Found duplicate sets ({restored_count} restored duplicates highlighted in green).")
            else:
                self.main_window.update_status("Restoration scan complete. No restored duplicates found in current duplicate sets.")
        else:
            # Regular scan feedback
            self.status_label.setText("Duplicate scan finished.")
        
        # Refresh highlighting after scan completes (for restoration cases)
        self.refresh_visual_highlighting()

    def populate_tree(self, duplicates):
        self.model.clear()
        if not duplicates:
            self.status_label.setText("No duplicate files found.")
            return

        for size, files in duplicates.items():
            parent_item = QStandardItem(f"Duplicate Set ({len(files)} files, {self.main_window.format_size(size)} each)")
            parent_item.setEditable(False)
            parent_item.setData(files, Qt.ItemDataRole.UserRole) # Store group paths
            
            for file_path in files:
                name_item = QStandardItem(os.path.basename(file_path))
                path_item = QStandardItem(file_path)
                size_item = QStandardItem(self.main_window.format_size(size))
                
                name_item.setCheckable(True)
                name_item.setEditable(False)
                path_item.setEditable(False)
                size_item.setEditable(False)
                
                # Apply visual highlighting for restored duplicates (green text)
                normalized_path = os.path.normpath(file_path)
                if hasattr(self.main_window, 'recently_restored_files') and normalized_path in self.main_window.recently_restored_files:
                    logging.info(f"Visual highlighting: Applying green text to restored duplicate {file_path}")
                    name_item.setForeground(QColor(0, 255, 0))  # Green text for restored duplicates
                    path_item.setForeground(QColor(0, 255, 0))
                    size_item.setForeground(QColor(0, 255, 0))
                else:
                    # Set default text color for normal duplicates (white for dark theme)
                    name_item.setForeground(QColor(255, 255, 255))
                    path_item.setForeground(QColor(255, 255, 255))
                    size_item.setForeground(QColor(255, 255, 255))
                
                name_item.setData(file_path, Qt.ItemDataRole.UserRole)
                parent_item.appendRow([name_item, path_item, size_item])

            self.model.appendRow(parent_item)
            
        self.main_window.resize_tree_columns(self.tree)
        self.status_label.setText(f"Found {len(duplicates)} sets of duplicate files.")

    def refresh_visual_highlighting(self):
        """Refresh visual highlighting for all displayed duplicates"""
        for i in range(self.model.rowCount()):
            parent_item = self.model.item(i)
            if parent_item:
                # Check each child file in the duplicate set
                for j in range(parent_item.rowCount()):
                    name_item = parent_item.child(j, 0)  # Name column
                    path_item = parent_item.child(j, 1)  # Path column
                    size_item = parent_item.child(j, 2)  # Size column
                    
                    if name_item and path_item:
                        file_path = name_item.data(Qt.ItemDataRole.UserRole)
                        if file_path:
                            normalized_path = os.path.normpath(file_path)
                            
                            # Check for restoration highlighting (green text)
                            if hasattr(self.main_window, 'recently_restored_files') and normalized_path in self.main_window.recently_restored_files:
                                logging.info(f"Visual highlighting: Applying green text to restored duplicate {file_path}")
                                name_item.setForeground(QColor(0, 255, 0))  # Green text for restored duplicates
                                path_item.setForeground(QColor(0, 255, 0))
                                if size_item:
                                    size_item.setForeground(QColor(0, 255, 0))
                            else:
                                # Normal white text for regular duplicates
                                name_item.setForeground(QColor(255, 255, 255))
                                path_item.setForeground(QColor(255, 255, 255))
                                if size_item:
                                    size_item.setForeground(QColor(255, 255, 255))

    def start_restoration_scan(self):
        """Start a duplicate scan specifically for restoration purposes"""
        logging.info("RESTORATION: Starting duplicate restoration scan")
        self._restoration_scan_active = True
        self.start_scan()
        logging.info("RESTORATION: start_scan() method called successfully for duplicates")

    def on_selection_changed(self, selected, deselected):
        indexes = selected.indexes()
        if not indexes:
            return
        
        # Get path from the second column (path)
        path_index = indexes[0].siblingAtColumn(1)
        path = self.model.data(path_index)
        if path and os.path.exists(path):
            self.preview_panel.set_preview(path)

    def get_selected_files_for_deletion(self):
        items_to_delete = []
        for i in range(self.model.rowCount()):
            parent = self.model.item(i)
            for row in range(parent.rowCount()):
                child = parent.child(row, 0)
                if child.checkState() == Qt.CheckState.Checked:
                    path = child.data(Qt.ItemDataRole.UserRole)
                    try:
                        size = os.path.getsize(path)
                    except OSError:
                        size = 0
                    items_to_delete.append({
                        'path': path, 
                        'size': size,
                        'category': 'Duplicates',  # Mark as duplicate for restoration tracking
                        'type': 'file',
                        'name': os.path.basename(path)
                    })
        return items_to_delete

    def request_deletion(self):
        items = self.get_selected_files_for_deletion()
        if not items:
            QMessageBox.warning(self, "No Files Selected", "Please select files to delete.")
            return
        self.delete_requested.emit(items)

    def select_all_but_newest(self):
        for i in range(self.model.rowCount()):
            parent = self.model.item(i)
            file_paths = parent.data(Qt.ItemDataRole.UserRole)
            
            if not file_paths:
                continue

            try:
                files_with_mtime = [(p, os.path.getmtime(p)) for p in file_paths if os.path.exists(p)]
                if not files_with_mtime:
                    continue
                
                files_with_mtime.sort(key=lambda x: x[1], reverse=True)
                newest_file_path = files_with_mtime[0][0]

                for row in range(parent.rowCount()):
                    child_item = parent.child(row, 0)
                    item_path = child_item.data(Qt.ItemDataRole.UserRole)
                    if item_path != newest_file_path:
                        child_item.setCheckState(Qt.CheckState.Checked)
                    else:
                        child_item.setCheckState(Qt.CheckState.Unchecked)
            except Exception as e:
                print(f"Error processing set: {e}")
                
    def stop_worker(self):
        if self.worker:
            self.worker.stop() 