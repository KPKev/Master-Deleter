import os
import shutil
import time
import json
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTreeView, QMessageBox, QLabel)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor
from PyQt6.QtCore import Qt, QStandardPaths, pyqtSignal
from send2trash import send2trash
from core.database_logger import log_event

APP_NAME = "MasterDeleter"
QUARANTINE_DIR = os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation), APP_NAME, "quarantine")
METADATA_FILE = os.path.join(QUARANTINE_DIR, "quarantine_metadata.json")

class QuarantineTab(QWidget):
    files_restored = pyqtSignal(list)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()
        self.populate_quarantined_files()

    def init_ui(self):
        layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        refresh_button = QPushButton("Refresh List")
        refresh_button.clicked.connect(self.populate_quarantined_files)
        restore_button = QPushButton("Restore Selected")
        restore_button.clicked.connect(self.restore_selected)
        delete_button = QPushButton("Delete Permanently")
        delete_button.clicked.connect(self.delete_selected_permanently)

        top_bar.addWidget(refresh_button)
        top_bar.addWidget(restore_button)
        top_bar.addWidget(delete_button)
        top_bar.addStretch()
        layout.addLayout(top_bar)
        
        info_label = QLabel("Files deleted without using the Recycle Bin are moved here. Restore them or delete them forever.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.tree = QTreeView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["File Name", "Original Location", "Date Quarantined"])
        self.tree.setModel(self.model)
        layout.addWidget(self.tree)

    def _load_metadata(self):
        if not os.path.exists(METADATA_FILE):
            return {}
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_metadata(self, data):
        try:
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except IOError:
            # Handle error
            pass

    def populate_quarantined_files(self):
        # Handle deletion highlighting counter
        if (self.main_window and hasattr(self.main_window, 'deletion_quarantine_refreshes_remaining') and 
            self.main_window.deletion_quarantine_refreshes_remaining > 0):
            self.main_window.deletion_quarantine_refreshes_remaining -= 1
            logging.info(f"Visual tracking: Preserving deletion highlighting for quarantine refresh (refreshes remaining: {self.main_window.deletion_quarantine_refreshes_remaining})")
        elif (self.main_window and hasattr(self.main_window, 'recently_deleted_files')):
            # Clear highlighting if no refreshes remaining
            if self.main_window.recently_deleted_files:
                logging.info("Visual tracking: Clearing deletion highlighting after refresh limit")
                self.main_window.recently_deleted_files.clear()
        
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["File Name", "Original Location", "Date Quarantined"])
        
        metadata = self._load_metadata()
        quarantined_files = os.listdir(QUARANTINE_DIR) if os.path.exists(QUARANTINE_DIR) else []

        for q_filename in quarantined_files:
            if q_filename == "quarantine_metadata.json":
                continue

            file_info = metadata.get(q_filename)
            if file_info:
                original_path = file_info.get('original_path', 'Unknown')
                date_quarantined_ts = file_info.get('quarantine_date', 0)
                date_quarantined = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(date_quarantined_ts))

                name_item = QStandardItem(os.path.basename(original_path))
                name_item.setCheckable(True)
                # Store the unique quarantined filename in the user role
                name_item.setData(q_filename, Qt.ItemDataRole.UserRole) 
                
                original_path_item = QStandardItem(original_path)
                date_item = QStandardItem(date_quarantined)
                
                # Apply color highlighting for recently deleted files (red)
                if (self.main_window and hasattr(self.main_window, 'recently_deleted_files') and 
                    os.path.normpath(original_path) in self.main_window.recently_deleted_files):
                    name_item.setForeground(QColor(255, 100, 100))  # Red for recently deleted files
                    original_path_item.setForeground(QColor(255, 100, 100))
                    date_item.setForeground(QColor(255, 100, 100))
                    logging.info(f"Visual tracking: Applied red highlighting to deleted file: {original_path}")

                self.model.appendRow([name_item, original_path_item, date_item])
            else:
                # Fallback for files not in metadata
                name_item = QStandardItem(q_filename)
                name_item.setCheckable(True)
                name_item.setData(q_filename, Qt.ItemDataRole.UserRole)
                
                unknown_path_item = QStandardItem("Unknown")
                unknown_date_item = QStandardItem("Unknown")
                
                # Note: For fallback files, we can't easily apply highlighting since we don't have original paths
                # but the highlighting is primarily for files deleted in this session anyway
                
                self.model.appendRow([name_item, unknown_path_item, unknown_date_item])
        
        self.main_window.resize_tree_columns(self.tree)

    def get_checked_files(self):
        checked_files = []
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked_files.append(item.data(Qt.ItemDataRole.UserRole))
        return checked_files

    def restore_selected(self):
        files_to_restore = self.get_checked_files()
        if not files_to_restore:
            QMessageBox.warning(self, "No Files", "Please select files to restore.")
            return

        metadata = self._load_metadata()
        restored_count = 0
        failed_count = 0
        restored_files_data = []

        for q_filename in files_to_restore:
            file_info = metadata.get(q_filename)
            if not file_info:
                logging.error(f"Restore failed: No metadata found for '{q_filename}'.")
                failed_count += 1
                continue
            
            source_path = os.path.join(QUARANTINE_DIR, q_filename)
            destination_path = file_info.get('original_path')

            if not destination_path:
                logging.error(f"Restore failed: No original_path in metadata for '{q_filename}'.")
                failed_count += 1
                continue
            
            # Normalize the destination path to handle mixed separators
            destination_path = os.path.normpath(destination_path)
            logging.info(f"Attempting to restore '{source_path}' to '{destination_path}'.")

            try:
                # Ensure destination directory exists
                destination_dir = os.path.dirname(destination_path)
                if not os.path.exists(destination_dir):
                    os.makedirs(destination_dir)
                    logging.info(f"Created destination directory: '{destination_dir}'.")
                
                # Avoid overwriting
                if os.path.exists(destination_path):
                    base, ext = os.path.splitext(destination_path)
                    new_destination_path = f"{base}_restored_{int(time.time())}{ext}"
                    logging.warning(f"Destination '{destination_path}' exists. Restoring to '{new_destination_path}'.")
                    destination_path = new_destination_path
                
                # Check if source actually exists
                if not os.path.exists(source_path):
                    logging.error(f"Restore failed: Quarantined file '{source_path}' not found.")
                    failed_count += 1
                    continue

                # Use a safer copy-then-delete strategy instead of a direct move.
                # Handle both files and directories
                if os.path.isdir(source_path):
                    # For directories, use copytree
                    shutil.copytree(source_path, destination_path)
                    shutil.rmtree(source_path)  # Remove the directory
                    logging.info(f"Restored directory '{source_path}' to '{destination_path}'")
                else:
                    # For files, use copy2
                    shutil.copy2(source_path, destination_path)
                    os.remove(source_path)
                    logging.info(f"Restored file '{source_path}' to '{destination_path}'")
                
                # Add the restored file's info to our list with all preserved metadata
                restored_file_data = {
                    'path': destination_path, # The restored path
                    'category': file_info.get('category', 'Unknown')
                }
                
                # Preserve any additional metadata that was stored during quarantine
                if 'suggestion_confidence' in file_info:
                    restored_file_data['suggestion_confidence'] = file_info['suggestion_confidence']
                if 'confidence' in file_info:
                    restored_file_data['confidence'] = file_info['confidence']
                if 'reason' in file_info:
                    restored_file_data['reason'] = file_info['reason']
                    
                restored_files_data.append(restored_file_data)

                # IMPORTANT: Only remove metadata after a successful operation
                del metadata[q_filename]
                
                log_event("restore", source_path, destination=destination_path)
                logging.info(f"Successfully restored '{q_filename}' to '{destination_path}'.")
                restored_count += 1
            except PermissionError as e:
                logging.error(f"Failed to restore '{q_filename}': Permission denied. File may be in use or require admin privileges: {e}")
                failed_count += 1
            except FileNotFoundError as e:
                logging.error(f"Failed to restore '{q_filename}': Quarantined file not found: {e}")
                failed_count += 1
            except Exception as e:
                logging.error(f"Failed to restore '{q_filename}': {e}", exc_info=True)
                failed_count += 1
        
        self._save_metadata(metadata)

        # Emit the signal with the list of successfully restored files
        if restored_files_data:
            self.files_restored.emit(restored_files_data)

        QMessageBox.information(self, "Restore Complete", f"Successfully restored {restored_count} of {len(files_to_restore)} items.")
        self.populate_quarantined_files()

    def delete_selected_permanently(self):
        files_to_delete = self.get_checked_files()
        if not files_to_delete:
            QMessageBox.warning(self, "No Files", "Please select files to delete permanently.")
            return

        reply = QMessageBox.question(self, "Confirm Permanent Deletion",
                                     f"Are you sure you want to permanently delete {len(files_to_delete)} files?\n"
                                     "This action CANNOT be undone.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.No:
            return

        deleted_count = 0
        metadata = self._load_metadata()
        for q_filename in files_to_delete:
            try:
                path = os.path.join(QUARANTINE_DIR, q_filename)
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                
                # Remove from metadata
                if q_filename in metadata:
                    del metadata[q_filename]

                log_event("delete_permanent", path)
                deleted_count +=1
            except Exception as e:
                print(f"Failed to permanently delete {q_filename}: {e}")

        self._save_metadata(metadata)
        QMessageBox.information(self, "Deletion Complete", f"{deleted_count} files permanently deleted.")
        self.populate_quarantined_files() 