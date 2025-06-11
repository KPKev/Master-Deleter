import sys
import os
import math
import datetime
import time
import configparser
import logging
import json
import traceback

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTreeView, 
                              QSplitter, QHBoxLayout, QLineEdit, QFileDialog, QMessageBox, 
                              QCheckBox, QTabWidget, QComboBox, QDateTimeEdit, QListView,
                              QMenu, QProgressBar)
from PyQt6.QtCore import (Qt, QThread, QTimer, QDateTime, QUrl, QStringListModel, QByteArray, QStandardPaths, QModelIndex, QSettings, QItemSelectionModel)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QDesktopServices, QFontMetrics

from core.scanner import Scanner
from core.categorizer import (
    CAT_SYSTEM, CAT_APP, CAT_SAFE_DELETE, CAT_USER, CAT_UNKNOWN,
    CAT_DEV_PROJECT, CAT_USER_DOWNLOADS, CAT_USER_DOCUMENTS
)
from core.deleter import Deleter
from core.suggester import DeletionSuggester, SuggesterWorker
from core.persistence import save_suggester, load_suggester
from core.empty_folder_finder import EmptyFolderFinderWorker
from core.log_setup import setup_logging
from ui.preview_panel import PreviewPanel
from ui.duplicate_finder_tab import DuplicateFinderTab
from ui.empty_folder_finder_tab import EmptyFolderFinderTab
from ui.quarantine_tab import QuarantineTab
from ui.cleaner_tab import CleanerTab, NumericStandardItem
from ui.scheduler_tab import SchedulerTab
from ui.exclusions_tab import ExclusionsTab
from ui.settings_tab import SettingsTab
from ui.logging_tab import LoggingTab
from ui.deletion_history_tab import DeletionHistoryTab
from core.database_logger import log_event
from core.deletion_logger import setup_deletion_logger

CAT_SUGGESTED = "Smart Suggestions"
CAT_LARGEST_FILES = "Largest Files (Top 100)"
CAT_OLD_FILES = "Old & Unused Files (1 Year+)"

class FileDeleterApp(QWidget):
    def __init__(self):
        super().__init__()
        
        # Setup application-level settings
        QApplication.setOrganizationName("YourCompany")
        QApplication.setApplicationName("MasterDeleter")
        self.settings = QSettings()
        
        # Application state tracking for supervisor
        self.app_state_file = "app_state_recovery.json"
        self.last_state_save = time.time()
        self.state_save_interval = 30  # Save state every 30 seconds
        
        # Setup logging first
        logging.info("Application starting...")

        self.setWindowTitle('Master Deleter')
        self.setGeometry(100, 100, 1200, 800)
        self.scanner_thread = None
        self.scanner = None
        self.deleter_thread = None
        self.deleter = None
        self.suggester_thread = None
        self.suggester_worker = None
        self.suggester = DeletionSuggester()
        
        self.scheduler_timer = QTimer(self)
        self.scheduler_timer.timeout.connect(self.run_scheduled_scan)
        self.last_run_date = None
        self.exclusions = []
        self.schedule_settings = {}
        
        self.saved_theme = "Futuristic Dark"
        self.saved_header_states = {}
        
        self.pending_updates = {}
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.setInterval(200) 
        self.ui_update_timer.timeout.connect(self.update_category_tree_ui)

        self.categorized_data = {}
        self.dir_sizes = {}
        
        # Track recent restorations to trigger UI refreshes
        self.recent_restorations = False
        self.restoration_timer = QTimer(self)
        self.restoration_timer.setSingleShot(True)
        self.restoration_timer.timeout.connect(self.clear_restoration_flag)
        self.restoration_callback = None
        
        # Track recently restored and deleted files for visual highlighting
        self.recently_restored_files = set()  # Paths of files just restored (show green)
        self.recently_deleted_files = set()   # Paths of files just deleted (show red in quarantine)
        self.restoration_scans_remaining = 0  # How many scans restored files should survive
        self.deletion_quarantine_refreshes_remaining = 0  # How many quarantine refreshes deleted files should survive
        
        self.recycle_bin_checkbox = QCheckBox() 

        self.setup_logging()
        self.init_ui()
        self.load_settings()
        self.restore_ui_state()
        
        # Setup automatic state saving timer
        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self.save_recovery_state)
        self.state_timer.start(self.state_save_interval * 1000)  # Convert to milliseconds
        
        # Attempt to recover from previous crash
        self.attempt_crash_recovery()
        
        logging.info("Application initialized successfully.")

    def save_recovery_state(self):
        """Save current application state for crash recovery"""
        try:
            state = {
                "timestamp": datetime.datetime.now().isoformat(),
                "current_tab": self.tabs.currentIndex(),
                "scan_path": self.cleaner_tab.get_scan_path() if hasattr(self.cleaner_tab, 'get_scan_path') else "",
                "has_categorized_data": bool(self.categorized_data),
                "category_count": sum(len(data.get('items', [])) for data in self.categorized_data.values()),
                "exclusions": self.exclusions.copy(),
                "schedule_settings": self.schedule_settings.copy(),
                "ui_state": {
                    "window_geometry": [self.x(), self.y(), self.width(), self.height()],
                    "current_theme": getattr(self, 'saved_theme', 'Futuristic Dark')
                }
            }
            
            with open(self.app_state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
            self.last_state_save = time.time()
            logging.debug("Recovery state saved successfully")
            
        except Exception as e:
            logging.error(f"Failed to save recovery state: {e}")

    def attempt_crash_recovery(self):
        """Attempt to recover from a previous crash"""
        try:
            if not os.path.exists(self.app_state_file):
                logging.info("No previous state found - clean start")
                return
                
            with open(self.app_state_file, 'r') as f:
                state = json.load(f)
                
            # Check if state is recent (within last hour)
            state_time = datetime.datetime.fromisoformat(state["timestamp"])
            time_diff = datetime.datetime.now() - state_time
            
            if time_diff.total_seconds() > 3600:  # 1 hour
                logging.info("Previous state is too old, starting fresh")
                os.remove(self.app_state_file)
                return
                
            logging.info(f"Found recent state from {state_time}")
            logging.info("Attempting crash recovery...")
            
            # Restore basic settings
            if state.get("exclusions"):
                self.exclusions = state["exclusions"]
                self.exclusions_tab.set_exclusions(self.exclusions)
                
            if state.get("schedule_settings"):
                self.schedule_settings = state["schedule_settings"]
                
            # Restore UI state
            ui_state = state.get("ui_state", {})
            if ui_state.get("window_geometry"):
                x, y, w, h = ui_state["window_geometry"]
                self.setGeometry(x, y, w, h)
                
            if ui_state.get("current_theme"):
                self.apply_theme(ui_state["current_theme"])
                
            # Restore tab selection
            if "current_tab" in state:
                self.tabs.setCurrentIndex(state["current_tab"])
                
            # If there was scan data, suggest rescanning
            if state.get("has_categorized_data") and state.get("scan_path"):
                scan_path = state["scan_path"]
                category_count = state.get("category_count", 0)
                
                logging.info(f"Previous session had {category_count} items scanned in '{scan_path}'")
                self.status_label.setText(f"Recovered from crash - previous scan: {category_count} items in '{scan_path}'")
                
                # Auto-populate the scan path
                if hasattr(self.cleaner_tab, 'path_input'):
                    self.cleaner_tab.path_input.setText(scan_path)
                    
            logging.info("Crash recovery completed successfully")
            
            # Clean up the recovery file
            os.remove(self.app_state_file)
            
        except Exception as e:
            logging.error(f"Error during crash recovery: {e}")
            logging.error(traceback.format_exc())

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.preview_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.tabs = QTabWidget()
        self.cleaner_tab = CleanerTab(self)
        self.dupe_tab = DuplicateFinderTab(self)
        self.empty_tab = EmptyFolderFinderTab(self)
        self.quarantine_tab = QuarantineTab(self)
        self.scheduler_tab = SchedulerTab(self)
        self.exclusions_tab = ExclusionsTab(self)
        self.settings_tab = SettingsTab(self)
        self.logging_tab = LoggingTab(self)
        self.deletion_history_tab = DeletionHistoryTab(self)
        
        self.tabs.addTab(self.cleaner_tab, "Smart Cleaner")
        self.tabs.addTab(self.dupe_tab, "Duplicate Finder")
        self.tabs.addTab(self.empty_tab, "Empty Folder Finder")
        self.tabs.addTab(self.quarantine_tab, "Quarantine")
        self.tabs.addTab(self.scheduler_tab, "Scheduler")
        self.tabs.addTab(self.exclusions_tab, "Exclusions")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.logging_tab, "Logging")
        self.tabs.addTab(self.deletion_history_tab, "Deletion History")

        # --- Connect signals to slots ---
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Cleaner Tab
        self.cleaner_tab.scan_requested.connect(self.start_scan)
        self.cleaner_tab.cancel_requested.connect(self.cancel_scan)
        self.cleaner_tab.delete_requested.connect(self.delete_selected_files)
        self.cleaner_tab.item_selected.connect(self.on_file_selected)
        self.cleaner_tab.add_to_exclusions_requested.connect(self.add_exclusion_and_update)
        self.cleaner_tab.refresh_requested.connect(self.refresh_current_view)
        self.cleaner_tab.category_tree.selectionModel().selectionChanged.connect(self.on_category_selected)
        
        # Duplicate Tab
        self.dupe_tab.delete_requested.connect(self.delete_selected_files)
        
        # Quarantine Tab
        self.quarantine_tab.files_restored.connect(self.on_files_restored)
        
        # Other Tabs
        self.settings_tab.theme_changed.connect(self.change_theme)
        self.settings_tab.recycle_bin_changed.connect(self.set_recycle_bin)
        self.exclusions_tab.exclusions_changed.connect(self.update_exclusions)
        self.scheduler_tab.schedule_settings_changed.connect(self.update_schedule_settings)

        # Logging Tab
        self.log_handler.new_record.connect(self.logging_tab.append_log)
        self.logging_tab.log_level_changed.connect(self.set_log_level)
        
        self.preview_splitter.addWidget(self.tabs)
        self.preview_panel = PreviewPanel(self)
        self.preview_splitter.addWidget(self.preview_panel)
        self.preview_splitter.setSizes([700, 200])

        self.main_layout.addWidget(self.preview_splitter)
        
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(40)
        self.progress_bar.setTextVisible(True)
        
        progress_layout.addStretch(1)
        progress_layout.addWidget(self.progress_bar, 2)
        progress_layout.addStretch(1)
        self.main_layout.addLayout(progress_layout)

        status_bar_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status_label")
        status_bar_layout.addWidget(self.status_label, 1)
        self.main_layout.addLayout(status_bar_layout)

    def setup_logging(self):
        self.log_handler = setup_logging()
        setup_deletion_logger()

    def set_log_level(self, level):
        logging.getLogger().setLevel(level)
        logging.info(f"Log level changed to {logging.getLevelName(level)}")

    def resize_tree_columns(self, tree_view):
        model = tree_view.model()
        if not model: return
        for i in range(model.columnCount()):
            tree_view.resizeColumnToContents(i)

    def start_scan(self, path):
        if self.scanner_thread and self.scanner_thread.isRunning():
            logging.warning("Scan is already in progress.")
            return
        if self.suggester_thread and self.suggester_thread.isRunning():
            self.status_label.setText("Please wait for suggestion calculation to finish.")
            logging.warning("Suggestion calculation is in progress. Cannot start scan.")
            return

        # CLEAR OLD DATA: Clear the file list view from previous scan
        logging.info("Clearing previous scan data")
        self.cleaner_tab.update_file_list([], [], False)
        
        # Clear any selection to avoid confusion
        selection_model = self.cleaner_tab.category_tree.selectionModel()
        selection_model.clearSelection()
        
        # Clear visual highlighting from previous operations (unless restoration files have scans remaining)
        if self.restoration_scans_remaining > 0:
            # This is a restoration-related scan, preserve the highlighting and decrement counter
            self.restoration_scans_remaining -= 1
            logging.info(f"Visual tracking: Preserving restoration highlighting for scan (scans remaining: {self.restoration_scans_remaining})")
        else:
            # Normal scan, clear all highlighting
            self.recently_restored_files.clear()
            self.recently_deleted_files.clear()
            logging.info("Visual tracking: Cleared highlighting for new scan")

        self.setup_category_data()
        logging.info(f"Starting scan on path: {path}")
        self.status_label.setText('Scanning...')
        self.progress_bar.setVisible(True)
        self.scanner_thread = QThread()
        self.scanner = Scanner(start_path=path, exclusions=self.exclusions)
        self.scanner.moveToThread(self.scanner_thread)

        self.scanner_thread.started.connect(self.scanner.run)
        self.scanner.scan_finished.connect(self.scan_finished)
        self.scanner.scan_finished.connect(self.scanner_thread.quit)
        self.scanner.progress_update.connect(self.update_status)
        self.scanner.item_found.connect(self.handle_item_found)
        
        self.scanner_thread.finished.connect(self.scanner.deleteLater)
        self.scanner_thread.finished.connect(self.scanner_thread.deleteLater)
        self.scanner_thread.finished.connect(self.on_scanner_thread_finished)
        
        self.ui_update_timer.start()
        self.scanner_thread.start()
        self.cleaner_tab.set_scan_mode(is_scanning=True)

    def cancel_scan(self):
        if self.scanner and self.scanner_thread and self.scanner_thread.isRunning():
            logging.info("Cancelling scan...")
            self.status_label.setText("Cancelling scan...")
            self.scanner.stop()
        if self.suggester_thread and self.suggester_thread.isRunning():
            logging.info("Cancelling suggestions calculation...")
            self.status_label.setText("Cancelling suggestions...")
            self.suggester_thread.quit()
        self.cleaner_tab.set_scan_mode(is_scanning=False)

    def format_size(self, size):
        if size == 0: return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size, 1024)))
        p = math.pow(1024, i)
        s = round(size / p, 2)
        return f"{s} {size_name[i]}"

    def update_status(self, message):
        metrics = QFontMetrics(self.status_label.font())
        elided_text = metrics.elidedText(message, Qt.TextElideMode.ElideLeft, self.status_label.width())
        self.status_label.setText(elided_text)
        
    def handle_item_found(self, item):
        category = item['category']
        if category not in self.categorized_data: return
        self.categorized_data[category]['items'].append(item)
        if category not in self.pending_updates:
            self.pending_updates[category] = {'size': 0}
        self.pending_updates[category]['size'] += item.get('size', 0)

    def update_category_tree_ui(self):
        if self.pending_updates:
            for category, updates in self.pending_updates.items():
                self.categorized_data[category]['size'] += updates['size']
            self.pending_updates.clear()

        category_data_for_ui = {}
        for cat_name, data in self.categorized_data.items():
            category_data_for_ui[cat_name] = {
                "size_str": self.format_size(data['size']),
                "count": len(data['items'])
            }
        self.cleaner_tab.update_category_tree(category_data_for_ui)
        self.resize_tree_columns(self.cleaner_tab.category_tree)

    def scan_finished(self, dir_sizes):
        self.ui_update_timer.stop()
        self.update_category_tree_ui()
        self.status_label.setText('Scan finished. Analyzing files...')
        logging.info("Scan finished. Starting file analysis.")
        self.dir_sizes = dir_sizes
        
        self._rebuild_summary_categories()

        self.update_category_tree_ui()

        self.progress_bar.setVisible(False)
        self.cleaner_tab.set_scan_mode(is_scanning=False)
        logging.info("File analysis complete.")
        
        # AUTO-SELECT: Automatically select "Largest Files (Top 100)" after scan
        # (Skip auto-select if this is a restoration scan)
        if not (hasattr(self, 'restoration_callback') and self.restoration_callback):
            self.auto_select_largest_files()
        
        # Check if this scan was triggered by restoration
        if hasattr(self, 'restoration_callback') and self.restoration_callback:
            logging.info("RESTORATION: Scan complete, triggering restoration callback")
            callback = self.restoration_callback
            self.restoration_callback = None  # Clear it
            QTimer.singleShot(500, callback)  # Short delay to ensure scan is fully complete
            self.status_label.setText("Restoration scan complete.")
        else:
            self.status_label.setText("Scan complete. Showing largest files by default.")

    def auto_select_largest_files(self):
        """Automatically select and display the 'Largest Files (Top 100)' category after scan"""
        logging.info("AUTO-SELECT: Selecting 'Largest Files (Top 100)' by default")
        
        selection_model = self.cleaner_tab.category_tree.selectionModel()
        
        # Find the "Largest Files (Top 100)" category in the tree
        for row in range(self.cleaner_tab.category_model.rowCount()):
            item = self.cleaner_tab.category_model.item(row, 0)
            if item and item.text() == CAT_LARGEST_FILES:
                # Select this category
                index = self.cleaner_tab.category_model.indexFromItem(item)
                selection_model.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.SelectCurrent)
                
                # Force immediate display of the category contents
                selection = selection_model.selection()
                self.on_category_selected(selection, None)
                
                logging.info(f"AUTO-SELECT: Successfully selected '{CAT_LARGEST_FILES}'")
                return
        
        logging.warning("AUTO-SELECT: Could not find 'Largest Files (Top 100)' category")

    def _rebuild_summary_categories(self):
        """Re-calculates the summary categories like Largest and Old files from the primary data."""
        logging.debug("Rebuilding summary categories.")
        
        # Get all files from non-summary categories
        all_files = []
        for cat_name, data in self.categorized_data.items():
            # Exclude summary categories themselves from the source of files
            if cat_name not in [CAT_LARGEST_FILES, CAT_OLD_FILES, CAT_SUGGESTED]:
                for item in data['items']:
                    if item['type'] == 'file':
                        all_files.append(item)
        
        logging.debug(f"Found {len(all_files)} total files for summary category rebuild.")
        
        # --- Old Files ---
        now = time.time()
        one_year_ago = now - (365 * 24 * 60 * 60)
        old_files = [item for item in all_files if item.get('mtime', now) < one_year_ago]
        old_count_before = len(self.categorized_data[CAT_OLD_FILES]['items'])
        self.categorized_data[CAT_OLD_FILES]['items'] = old_files
        self.categorized_data[CAT_OLD_FILES]['size'] = sum(item['size'] for item in old_files)
        logging.debug(f"Old files: {old_count_before} -> {len(old_files)}")

        # --- Largest Files ---
        # Sort all files by size in descending order
        all_files_sorted = sorted(all_files, key=lambda x: x.get('size', 0), reverse=True)
        largest_files = all_files_sorted[:100]
        largest_count_before = len(self.categorized_data[CAT_LARGEST_FILES]['items'])
        self.categorized_data[CAT_LARGEST_FILES]['items'] = largest_files
        self.categorized_data[CAT_LARGEST_FILES]['size'] = sum(item['size'] for item in largest_files)
        logging.debug(f"Largest files: {largest_count_before} -> {len(largest_files)}")
        
        # Log the paths of largest files for debugging
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            largest_paths = [os.path.basename(item['path']) for item in largest_files[:5]]
            logging.debug(f"Top 5 largest files: {largest_paths}")

    def on_suggestion_finished(self, suggested_files):
        logging.info(f"Generated {len(suggested_files)} suggestions.")
        self.categorized_data[CAT_SUGGESTED]['items'] = suggested_files
        self.categorized_data[CAT_SUGGESTED]['size'] = sum(item['size'] for item in suggested_files)
        self.update_category_tree_ui()
        self.on_category_selected(self.cleaner_tab.category_tree.selectionModel().selection(), None)
        self.status_label.setText("Suggestions ready.")
        self.cleaner_tab.set_scan_mode(is_scanning=False)
        save_suggester(self.suggester)

    def on_category_selected(self, selected, deselected):
        indexes = selected.indexes()
        if not indexes: return

        category_name_item = self.cleaner_tab.category_model.itemFromIndex(indexes[0])
        if not category_name_item: return
        category_name = category_name_item.text()
        
        logging.debug(f"Category selected: {category_name}")
        
        is_protected = category_name in [CAT_SYSTEM, CAT_APP, CAT_DEV_PROJECT]
        items_data = self.categorized_data.get(category_name, {}).get('items', [])
        
        # Debug logging for summary categories
        if category_name in [CAT_LARGEST_FILES, CAT_OLD_FILES, CAT_SUGGESTED]:
            logging.debug(f"Summary category '{category_name}' has {len(items_data)} items")
            if category_name == CAT_LARGEST_FILES and items_data:
                top_file = items_data[0] if items_data else None
                if top_file:
                    logging.debug(f"Largest file: {os.path.basename(top_file['path'])} ({self.format_size(top_file['size'])})")
        
        headers, rows = [], []
        
        if category_name in [CAT_LARGEST_FILES, CAT_OLD_FILES]:
            headers = ['Name', 'Size', 'Path', 'Original Category']
            for item in items_data:
                rows.append({
                    'name': os.path.basename(item['path']), 'size': item['size'], 'path': item['path'], 
                    'original_category': item['category'], '_item_data': item})
        elif category_name == CAT_SUGGESTED:
            headers = ['Name', 'Confidence', 'Size', 'Path']
            for item in items_data:
                 rows.append({
                    'name': os.path.basename(item['path']), 'confidence': item.get('suggestion_confidence', 0),
                    'size': item['size'], 'path': item['path'], '_item_data': item})
        else:
            headers = ['Name', 'Size', 'Path']
            for item in items_data:
                 size = self.dir_sizes.get(item['path'], 0) if item['type'] == 'dir' else item['size']
                 rows.append({'name': os.path.basename(item['path']), 'size': size, 'path': item['path'], '_item_data': item})

        self.cleaner_tab.update_file_list(headers, rows, is_protected)
        self.resize_tree_columns(self.cleaner_tab.file_list_tree)

    def delete_selected_files(self, items_to_delete):
        if not items_to_delete:
            self.status_label.setText("No files selected for deletion.")
            logging.warning("Deletion requested, but no files were selected.")
            return

        total_size = sum(item['size'] for item in items_to_delete)
        reply = QMessageBox.question(self, 'Confirm Deletion',
                                     f"Are you sure you want to delete {len(items_to_delete)} items?\n"
                                     f"Total size: {self.format_size(total_size)}",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No: 
            logging.info("User cancelled deletion.")
            return

        logging.info(f"Starting deletion of {len(items_to_delete)} items.")
        self.status_label.setText(f"Deleting {len(items_to_delete)} items...")
        
        self.deleter_thread = QThread()
        use_recycle_bin = self.settings_tab.get_recycle_bin_enabled()
        self.deleter = Deleter(items_to_delete, use_recycle_bin=use_recycle_bin)
        self.deleter.moveToThread(self.deleter_thread)
        self.deleter_thread.started.connect(self.deleter.run)
        self.deleter.finished.connect(self.on_deletion_finished)
        self.deleter.progress.connect(self.update_deletion_progress)
        self.deleter.error.connect(self.on_cloud_file_error)
        
        # We need to quit the thread, but delay the object deletion
        self.deleter.finished.connect(self.deleter_thread.quit)
        self.deleter_thread.finished.connect(self.cleanup_deleter)

        self.deleter_thread.start()

    def update_deletion_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.status_label.setText(text)

    def on_cloud_file_error(self, file_path):
        QMessageBox.warning(self, "Cloud File Error", 
                            f"Could not delete '{file_path}'.\nThis may be a cloud-synced file. Please delete it manually from your cloud provider.")

    def cleanup_deleter(self):
        """
        Safely delete the deleter and its thread after all signals have been processed.
        """
        if self.deleter:
            self.deleter.deleteLater()
            self.deleter = None
        if self.deleter_thread:
            self.deleter_thread.deleteLater()
            self.deleter_thread = None
        logging.debug("Deleter and its thread have been marked for deletion.")

    def on_deletion_finished(self, succeeded_items, failed):
        logging.info(f"Deletion finished. Succeeded: {len(succeeded_items)}, Failed: {len(failed)}")
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Deletion complete. {len(succeeded_items)} files deleted.")
        
        # Get the current selection before the model is updated
        selection_model = self.cleaner_tab.category_tree.selectionModel()
        current_index = selection_model.currentIndex()
        selected_category_name = None
        if current_index.isValid():
            selected_category_name = self.cleaner_tab.category_model.itemFromIndex(current_index).text()

        if succeeded_items:
            # Track recently deleted files for visual highlighting (red in quarantine)
            self.recently_deleted_files.clear()  # Clear previous deletions
            self.recently_deleted_files.update(os.path.normpath(item['path']) for item in succeeded_items)
            self.deletion_quarantine_refreshes_remaining = 2  # Allow highlighting to survive through 2 quarantine refreshes
            logging.info(f"Visual tracking: {len(self.recently_deleted_files)} files marked as recently deleted, allowing 2 refresh survivals")
            
            # Train the suggester model with successful deletions
            suggested_items_deleted = [item['data'] for item in succeeded_items if item.get('data') and 'confidence' in item.get('data')]
            if suggested_items_deleted:
                self.suggester.train(suggested_items_deleted, 'deleted')
            
            # Remove deleted items from the data model using normalized paths for comparison
            succeeded_paths = {os.path.normpath(item['path']) for item in succeeded_items}
            for category in self.categorized_data:
                # The paths in categorized_data should already be normalized by the scanner
                self.categorized_data[category]['items'] = [
                    item for item in self.categorized_data[category]['items']
                    if item['path'] not in succeeded_paths
                ]
                # Recalculate category size
                self.categorized_data[category]['size'] = sum(item.get('size', 0) for item in self.categorized_data[category]['items'])

        # Refresh the UI
        self.update_category_tree_ui()

        # Restore the selection after the model has been updated
        if selected_category_name:
            for row in range(self.cleaner_tab.category_model.rowCount()):
                item = self.cleaner_tab.category_model.item(row)
                if item.text() == selected_category_name:
                    new_index = self.cleaner_tab.category_model.indexFromItem(item)
                    selection_model.setCurrentIndex(new_index, QItemSelectionModel.SelectionFlag.SelectCurrent)
                    break
        
        self.refresh_current_view()
        self.quarantine_tab.populate_quarantined_files()
        # After deletion, rescan for duplicates as the state has changed
        if self.tabs.currentWidget() == self.dupe_tab:
            self.dupe_tab.start_scan()

    def on_files_restored(self, restored_files):
        """
        Handles file restoration by triggering the exact same sequence that works:
        Scan + Refresh (programmatically)
        """
        logging.info(f"RESTORATION: Processing {len(restored_files)} restored files.")
        
        if not restored_files:
            return
            
        # Track recently restored files for visual highlighting (green in Smart Cleaner)
        self.recently_restored_files.clear()  # Clear previous restorations
        self.recently_restored_files.update(os.path.normpath(file_data.get('path', '')) for file_data in restored_files if file_data.get('path'))
        self.restoration_scans_remaining = 1  # Allow highlighting to survive through 1 scan+refresh cycle
        logging.info(f"Visual tracking: {len(self.recently_restored_files)} files marked as recently restored, allowing 1 scan survival")
            
        # Save current UI state
        selection_model = self.cleaner_tab.category_tree.selectionModel()
        current_index = selection_model.currentIndex()
        selected_category_name = None
        if current_index.isValid():
            selected_category_name = self.cleaner_tab.category_model.itemFromIndex(current_index).text()

        # Update quarantine tab first
        self.quarantine_tab.populate_quarantined_files()
        
        # Get the current scan path
        current_scan_path = self.get_scan_path()
        if not current_scan_path or not os.path.exists(current_scan_path):
            logging.error("Cannot rescan - no valid scan path available")
            self.status_label.setText(f"Restoration complete. {len(restored_files)} files restored.")
            return

        logging.info(f"RESTORATION: Auto-triggering scan + refresh sequence")
        
        # Step 1: Trigger scan (same as clicking Scan button)
        self.start_scan(current_scan_path)
        
        # Step 2: Schedule refresh after scan completes (same as clicking Refresh button)
        # We need to wait for scan to complete before refreshing
        self.restoration_callback = lambda: self.complete_restoration_refresh(selected_category_name)
        
        self.status_label.setText(f"Auto-scanning to detect {len(restored_files)} restored files...")

    def complete_restoration_refresh(self, selected_category_name):
        """Complete the restoration by refreshing and restoring selection"""
        logging.info("RESTORATION: Completing with refresh")
        
        # Step 2: Refresh (same as clicking Refresh button)
        self.refresh_current_view()
        
        # Step 3: Restore selection
        if selected_category_name:
            selection_model = self.cleaner_tab.category_tree.selectionModel()
            for row in range(self.cleaner_tab.category_model.rowCount()):
                item = self.cleaner_tab.category_model.item(row)
                if item and item.text() == selected_category_name:
                    new_index = self.cleaner_tab.category_model.indexFromItem(item)
                    selection_model.setCurrentIndex(new_index, QItemSelectionModel.SelectionFlag.SelectCurrent)
                    break
        
        self.status_label.setText("Restoration complete - files should now be visible")
        logging.info("RESTORATION: Complete")
        
        # Note: Restoration highlighting will now be cleared on the NEXT scan operation (not this restoration scan)
        logging.info(f"Visual tracking: Restoration complete. Highlighting will survive until next scan. Scans remaining: {self.restoration_scans_remaining}")



    def on_file_selected(self, path):
        self.preview_panel.set_preview(path)

    def on_tab_changed(self, index):
        current_widget = self.tabs.widget(index)
        if current_widget == self.quarantine_tab:
            logging.info("Switched to Quarantine tab, refreshing list.")
            self.quarantine_tab.populate_quarantined_files()
        elif current_widget == self.deletion_history_tab:
            logging.info("Switched to Deletion History tab, refreshing view.")
            self.deletion_history_tab.populate_history()
        elif current_widget == self.cleaner_tab:
            # If there were recent restorations, refresh the view
            if self.recent_restorations:
                logging.info("TAB SWITCH: Refreshing Smart Cleaner after recent restorations")
                self.refresh_current_view()

    def clear_restoration_flag(self):
        """Clear the recent restorations flag after a timeout"""
        self.recent_restorations = False
        logging.debug("Cleared recent restorations flag")



    def get_scan_path(self):
        return self.cleaner_tab.get_scan_path()

    def apply_theme(self, theme_name):
        css_file = "ui/style.qss" if theme_name == "Futuristic Dark" else "ui/style_light.qss"
        try:
            with open(css_file, 'r') as f: self.setStyleSheet(f.read())
            logging.info(f"Applied theme: {theme_name}")
        except FileNotFoundError: 
            logging.warning(f"Could not find stylesheet: {css_file}")
        self.preview_panel.set_theme(theme_name == "Futuristic Dark")

    def change_theme(self, theme_name): self.apply_theme(theme_name)

    def save_settings(self):
        logging.debug("Saving settings.")
        # UI state
        self.settings.setValue("main_splitter_state", self.preview_splitter.saveState())
        
        # Get state from cleaner tab
        cleaner_tab_state = self.cleaner_tab.get_ui_state()
        self.settings.setValue("cleaner_tab_state", cleaner_tab_state)

        # Other settings
        self.settings.setValue("theme", self.settings_tab.get_current_theme())
        self.settings.setValue("recycle_bin", self.settings_tab.get_recycle_bin_enabled())
        self.settings.setValue("exclusions", self.exclusions)
        self.settings.setValue("schedule_settings", self.scheduler_tab.get_schedule_settings())
        self.settings.sync()

    def load_settings(self):
        logging.debug("Loading settings.")
        # Load theme and apply it first
        theme = self.settings.value("theme", "Futuristic Dark")
        self.settings_tab.set_theme(theme)
        self.apply_theme(theme)
        
        # Load other settings
        recycle_enabled = self.settings.value("recycle_bin", "true") == "true"
        self.settings_tab.set_recycle_bin(recycle_enabled)
        self.set_recycle_bin(recycle_enabled)
        
        self.exclusions = self.settings.value("exclusions", [])
        self.exclusions_tab.set_exclusions(self.exclusions)
        
        schedule_settings = self.settings.value("schedule_settings", {})
        if schedule_settings:
            self.scheduler_tab.set_schedule_settings(schedule_settings)
            self.update_schedule_settings(schedule_settings)

    def restore_ui_state(self):
        logging.debug("Restoring UI state from settings.")
        try:
            # Restore main splitter
            main_splitter_state = self.settings.value("main_splitter_state")
            if main_splitter_state:
                self.preview_splitter.restoreState(main_splitter_state)

            # Restore cleaner tab state
            cleaner_tab_state = self.settings.value("cleaner_tab_state")
            if cleaner_tab_state:
                self.cleaner_tab.set_ui_state(cleaner_tab_state)
            
        except Exception as e:
            logging.error(f"Could not restore UI state: {e}")

    def set_recycle_bin(self, enabled):
        logging.info(f"Recycle bin feature set to {'enabled' if enabled else 'disabled'}.")
        self.recycle_bin_checkbox.setChecked(enabled)

    def update_exclusions(self, exclusions_list): self.exclusions = exclusions_list
    
    def update_schedule_settings(self, settings):
        self.schedule_settings = settings
        is_enabled = settings.get('enabled', False)
        if is_enabled:
            self.scheduler_timer.start(60 * 1000) # Check every minute
            self.status_label.setText("Scheduler enabled. The app must remain open for it to run.")
            logging.info("Scheduler enabled.")
        else:
            self.scheduler_timer.stop()
            self.status_label.setText("Scheduler disabled.")
            logging.info("Scheduler disabled.")

    def run_scheduled_scan(self):
        logging.info("Starting scheduled scan.")
        path = self.schedule_settings.get('path')
        if path and os.path.exists(path):
            self.last_run_date = QDateTime.currentDateTime()
            self.scheduler_tab.update_last_run(self.last_run_date)
            self.start_scan(path)
        else:
            logging.error(f"Scheduled scan path '{path}' is invalid or does not exist.")

    def refresh_current_view(self):
        logging.debug("Refreshing current category view")
        selection_model = self.cleaner_tab.category_tree.selectionModel()
        if selection_model and selection_model.hasSelection():
            current_selection = selection_model.selection()
            self.on_category_selected(current_selection, None)
        else:
            # If nothing is selected, clear the file list view
            self.cleaner_tab.update_file_list([], [], False)



    def add_exclusion_and_update(self, folder_path):
        if folder_path not in self.exclusions:
            self.exclusions.append(folder_path)
            self.exclusions_tab.set_exclusions(self.exclusions)
            QMessageBox.information(self, "Exclusion Added", f"'{folder_path}' has been added to the exclusion list.")
            logging.info(f"Added '{folder_path}' to exclusions.")

    def setup_category_data(self):
        self.categorized_data = {
            CAT_LARGEST_FILES: {'items': [], 'size': 0}, CAT_OLD_FILES: {'items': [], 'size': 0},
            CAT_SUGGESTED: {'items': [], 'size': 0}, CAT_SYSTEM: {'items': [], 'size': 0},
            CAT_APP: {'items': [], 'size': 0}, CAT_DEV_PROJECT: {'items': [], 'size': 0},
            CAT_USER_DOWNLOADS: {'items': [], 'size': 0}, CAT_USER_DOCUMENTS: {'items': [], 'size': 0},
            CAT_SAFE_DELETE: {'items': [], 'size': 0}, CAT_USER: {'items': [], 'size': 0},
            CAT_UNKNOWN: {'items': [], 'size': 0},
        }
        self.update_category_tree_ui()

    def closeEvent(self, event):
        self.save_settings()
        logging.info("Application closing...")
        
        # Clean up recovery state file on normal shutdown
        try:
            if os.path.exists(self.app_state_file):
                os.remove(self.app_state_file)
                logging.info("Recovery state cleaned up on normal shutdown")
        except Exception as e:
            logging.warning(f"Could not clean up recovery state: {e}")
        
        # Shutdown threads
        if self.scanner_thread and self.scanner_thread.isRunning(): self.scanner_thread.quit()
        if self.deleter_thread and self.deleter_thread.isRunning(): self.deleter_thread.quit()
        if hasattr(self.dupe_tab, 'dupe_worker') and self.dupe_tab.dupe_worker and self.dupe_tab.dupe_worker.thread().isRunning():
            self.dupe_tab.dupe_worker.stop()
        if hasattr(self, 'empty_tab'): self.empty_tab.stop_worker()
        if self.suggester_thread and self.suggester_thread.isRunning(): self.suggester_thread.quit()
        
        # Stop state saving timer
        if hasattr(self, 'state_timer'):
            self.state_timer.stop()
            
        event.accept()

    def on_scanner_thread_finished(self):
        logging.debug("Scanner thread finished, cleaning up references.")
        self.scanner = None
        self.scanner_thread = None

    def on_suggester_thread_finished(self):
        logging.debug("Suggester thread finished, cleaning up references.")
        self.suggester_worker = None
        self.suggester_thread = None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FileDeleterApp()
    ex.show()
    sys.exit(app.exec())
