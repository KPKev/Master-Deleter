import os
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTreeView, 
                              QSplitter, QLineEdit, QComboBox, QCheckBox, QMenu, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QStandardPaths, QModelIndex
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QDesktopServices

class NumericStandardItem(QStandardItem):
    """A QStandardItem that sorts based on a numeric value stored in UserRole."""
    def __lt__(self, other):
        return self.data(Qt.ItemDataRole.UserRole) < other.data(Qt.ItemDataRole.UserRole)

class CleanerTab(QWidget):
    # Signals to communicate with the main application logic
    scan_requested = pyqtSignal(str)
    cancel_requested = pyqtSignal()
    delete_requested = pyqtSignal(list)
    item_selected = pyqtSignal(str)
    add_to_exclusions_requested = pyqtSignal(str)
    explain_suggestion_requested = pyqtSignal(dict)
    refresh_requested = pyqtSignal()

    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.is_protected_category = False
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Top bar for controls
        top_bar_layout = QHBoxLayout()
        
        path_label = QLabel("Path:")
        self.path_input = QLineEdit('C:\\\\')
        browse_button = QPushButton("Browse")
        
        library_label = QLabel("Quick Select:")
        self.library_combo = QComboBox()
        self.populate_library_combo()
        
        self.scan_button = QPushButton('Scan')
        self.scan_button.setObjectName('scan_button')
        self.cancel_button = QPushButton('Cancel')
        self.refresh_button = QPushButton("Refresh")
        self.delete_button = QPushButton("Delete Selected")
        
        self.select_all_button = QPushButton("Select All")
        self.deselect_all_button = QPushButton("Deselect All")

        top_bar_layout.addWidget(path_label)
        top_bar_layout.addWidget(self.path_input, 1)
        top_bar_layout.addWidget(browse_button)
        top_bar_layout.addWidget(library_label)
        top_bar_layout.addWidget(self.library_combo)
        top_bar_layout.addWidget(self.scan_button)
        top_bar_layout.addWidget(self.cancel_button)
        top_bar_layout.addWidget(self.refresh_button)
        top_bar_layout.addWidget(self.delete_button)
        top_bar_layout.addWidget(self.select_all_button)
        top_bar_layout.addWidget(self.deselect_all_button)
        
        main_layout.addLayout(top_bar_layout)

        # Main content area
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - category view
        self.category_tree = QTreeView()
        self.category_model = QStandardItemModel()
        self.category_model.setHorizontalHeaderLabels(['Category', 'Size', 'Items'])
        self.category_tree.setModel(self.category_model)
        
        self.main_splitter.addWidget(self.category_tree)

        # Right side - file list view
        self.file_list_tree = QTreeView()
        self.file_list_tree.setSortingEnabled(True)
        self.file_list_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list_model = QStandardItemModel()
        self.file_list_model.setHorizontalHeaderLabels(['Name', 'Size', 'Path', 'Category'])
        self.file_list_tree.setModel(self.file_list_model)
        self.main_splitter.addWidget(self.file_list_tree)
        
        self.main_splitter.setSizes([300, 900])
        main_layout.addWidget(self.main_splitter)
        
        # Connect signals
        browse_button.clicked.connect(self._browse_folder)
        self.library_combo.activated.connect(self._select_library_path)
        self.scan_button.clicked.connect(lambda: self.scan_requested.emit(self.path_input.text()))
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.delete_button.clicked.connect(self._emit_delete_request)
        self.select_all_button.clicked.connect(lambda: self._set_check_state_recursive(self.file_list_model.invisibleRootItem(), Qt.CheckState.Checked))
        self.deselect_all_button.clicked.connect(lambda: self._set_check_state_recursive(self.file_list_model.invisibleRootItem(), Qt.CheckState.Unchecked))
        self.file_list_tree.customContextMenuRequested.connect(self.open_file_list_menu)
        self.file_list_model.itemChanged.connect(self._on_item_changed)
        self.file_list_tree.selectionModel().selectionChanged.connect(self._on_file_selected)

    def _browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if directory:
            self.path_input.setText(directory)

    def _select_library_path(self, index):
        path = self.library_combo.itemData(index)
        if path:
            self.path_input.setText(path)

    def populate_library_combo(self):
        self.library_combo.addItem("Select a library...", userData=None)
        locations = {
            "Desktop": QStandardPaths.StandardLocation.DesktopLocation,
            "Documents": QStandardPaths.StandardLocation.DocumentsLocation,
            "Downloads": QStandardPaths.StandardLocation.DownloadLocation,
            "Pictures": QStandardPaths.StandardLocation.PicturesLocation,
            "Music": QStandardPaths.StandardLocation.MusicLocation,
            "Videos": QStandardPaths.StandardLocation.MoviesLocation,
        }
        for name, location_enum in locations.items():
            path = QStandardPaths.writableLocation(location_enum)
            if path:
                self.library_combo.addItem(name, userData=path)

    def _emit_delete_request(self):
        checked_items = self._get_checked_items(self.file_list_model.invisibleRootItem())
        if checked_items:
            self.delete_requested.emit(checked_items)

    def _on_item_changed(self, item):
        if item.isCheckable():
            any_checked = self._is_any_item_checked(self.file_list_model.invisibleRootItem())
            self.delete_button.setEnabled(any_checked)

    def _on_file_selected(self, selected, deselected):
        indexes = selected.indexes()
        if indexes:
            path_col_index = self._find_column("Path")
            if path_col_index != -1:
                path_index = self.file_list_model.index(indexes[0].row(), 0, indexes[0].parent())
                item_data = self.file_list_model.itemFromIndex(path_index).data(Qt.ItemDataRole.UserRole + 1)
                if item_data and 'path' in item_data:
                    self.item_selected.emit(item_data['path'])

    def _get_checked_items(self, parent_item):
        checked_items = []
        for row in range(parent_item.rowCount()):
            name_item = parent_item.child(row, 0)
            if name_item and name_item.checkState() == Qt.CheckState.Checked:
                # The full item data is stored on the name item
                item_data = name_item.data(Qt.ItemDataRole.UserRole + 1)
                if item_data:
                    entry = {
                        'path': item_data.get('path'),
                        'size': item_data.get('size', 0),
                        'data': item_data # Pass the whole original dict
                    }
                    checked_items.append(entry)

            if name_item and name_item.hasChildren():
                checked_items.extend(self._get_checked_items(name_item))
        return checked_items

    def _is_any_item_checked(self, parent_item):
        for row in range(parent_item.rowCount()):
            item = parent_item.child(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                return True
            if item and item.hasChildren() and self._is_any_item_checked(item):
                return True
        return False

    def _set_check_state_recursive(self, parent_item, check_state):
        for row in range(parent_item.rowCount()):
            item = parent_item.child(row, 0)
            if item and item.isCheckable():
                item.setCheckState(check_state)
            if item and item.hasChildren():
                self._set_check_state_recursive(item, check_state)
    
    def open_file_list_menu(self, position):
        indexes = self.file_list_tree.selectedIndexes()
        if not indexes: return

        menu = QMenu()
        item_model_index = self.file_list_model.index(indexes[0].row(), 0, indexes[0].parent())
        item_data = self.file_list_model.itemFromIndex(item_model_index).data(Qt.ItemDataRole.UserRole + 1)
        if not item_data: return

        path = item_data.get('path')
        if not path: return
        
        open_loc_action = menu.addAction("Open File Location")
        add_exclusion_action = menu.addAction("Add Parent Folder to Exclusions")
        
        explain_action = None
        # Check if it's a suggestion by looking for the 'reason' key
        if 'reason' in item_data:
            menu.addSeparator()
            explain_action = menu.addAction("Why was this suggested?")

        action = menu.exec(self.file_list_tree.viewport().mapToGlobal(position))

        if action == open_loc_action:
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
        elif action == add_exclusion_action:
            self.add_to_exclusions_requested.emit(os.path.dirname(path))
        elif action and action == explain_action:
            self.explain_suggestion_requested.emit(item_data)
    
    def _find_column(self, header_text):
        for i in range(self.file_list_model.columnCount()):
            if self.file_list_model.headerData(i, Qt.Orientation.Horizontal) == header_text:
                return i
        return -1

    def get_path(self):
        return self.path_input.text()

    def get_scan_path(self):
        return self.path_input.text()

    def set_scan_mode(self, is_scanning):
        self.scan_button.setEnabled(not is_scanning)
        self.cancel_button.setEnabled(is_scanning)

    def update_category_tree(self, category_data):
        """
        Updates the category tree model in-place to preserve selections,
        instead of rebuilding it from scratch.
        """
        existing_items = {}
        for row in range(self.category_model.rowCount()):
            item = self.category_model.item(row, 0)
            if item:
                existing_items[item.text()] = row

        for cat_name, data in category_data.items():
            count_str = f"{data.get('count', 0):,}"
            size_str = data.get('size_str', '0 B')

            if cat_name in existing_items:
                # Update existing row
                row = existing_items[cat_name]
                self.category_model.item(row, 1).setText(count_str)
                self.category_model.item(row, 2).setText(size_str)
            else:
                # Add new row if it doesn't exist (e.g., on first load)
                name_item = QStandardItem(cat_name)
                name_item.setEditable(False)
                
                count_item = QStandardItem(count_str)
                count_item.setEditable(False)
                count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                
                size_item = QStandardItem(size_str)
                size_item.setEditable(False)
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                
                self.category_model.invisibleRootItem().appendRow([name_item, count_item, size_item])

    def update_file_list(self, headers, rows, is_protected_category=False):
        self.is_protected_category = is_protected_category
        self.file_list_model.clear()
        self.file_list_model.setHorizontalHeaderLabels(headers)
        
        root_item = self.file_list_model.invisibleRootItem()
        for item_data in rows:
            # Debug logging for highlighting
            file_path = item_data.get('path')
            if not file_path and item_data.get('_item_data'):
                file_path = item_data.get('_item_data', {}).get('path')
            
            if (self.main_window and hasattr(self.main_window, 'recently_restored_files') and 
                file_path and self.main_window.recently_restored_files):
                is_restored = os.path.normpath(file_path) in self.main_window.recently_restored_files
                if is_restored:
                    logging.info(f"Visual tracking: Processing RESTORED file for highlighting: {file_path}")
                    
            row_items = []
            for header in headers:
                key = header.lower().replace(' ', '_')
                
                # Special handling for Name and Size columns
                if header == "Name":
                    item = QStandardItem(str(item_data.get('name', os.path.basename(item_data.get('path', '')))))
                    item.setCheckable(not is_protected_category)
                    # Store the complete data dictionary on the name item for easy access
                    item.setData(item_data, Qt.ItemDataRole.UserRole + 1)
                    
                    # Apply color highlighting for recently restored files (green)
                    file_path = item_data.get('path')  # Direct path from row data
                    if not file_path and item_data.get('_item_data'):  # Fallback to nested data
                        file_path = item_data.get('_item_data', {}).get('path')
                    
                    if (self.main_window and hasattr(self.main_window, 'recently_restored_files') and 
                        file_path and 
                        os.path.normpath(file_path) in self.main_window.recently_restored_files):
                        item.setForeground(QColor(0, 200, 0))  # Green for restored files
                        logging.info(f"Visual tracking: Applied green highlighting to restored file: {file_path}")
                elif header == "Size":
                    raw_size = item_data.get('size', 0)
                    # Use NumericStandardItem for correct sorting
                    item = NumericStandardItem()
                    item.setData(raw_size, Qt.ItemDataRole.UserRole)
                    # Use the main window's formatter for the display text
                    if self.main_window and hasattr(self.main_window, 'format_size'):
                         item.setText(self.main_window.format_size(raw_size))
                    else: # Fallback
                        item.setText(f"{raw_size} B")
                    
                    # Apply color highlighting for recently restored files (green)
                    file_path = item_data.get('path')  # Direct path from row data
                    if not file_path and item_data.get('_item_data'):  # Fallback to nested data
                        file_path = item_data.get('_item_data', {}).get('path')
                    
                    if (self.main_window and hasattr(self.main_window, 'recently_restored_files') and 
                        file_path and 
                        os.path.normpath(file_path) in self.main_window.recently_restored_files):
                        item.setForeground(QColor(0, 200, 0))  # Green for restored files
                else:
                    value = item_data.get(key, '')
                    item = QStandardItem(str(value))
                    
                    # Apply color highlighting to all columns for recently restored files (green)
                    file_path = item_data.get('path')  # Direct path from row data
                    if not file_path and item_data.get('_item_data'):  # Fallback to nested data
                        file_path = item_data.get('_item_data', {}).get('path')
                    
                    if (self.main_window and hasattr(self.main_window, 'recently_restored_files') and 
                        file_path and 
                        os.path.normpath(file_path) in self.main_window.recently_restored_files):
                        item.setForeground(QColor(0, 200, 0))  # Green for restored files

                item.setEditable(False)
                row_items.append(item)
            root_item.appendRow(row_items)
            
    def set_ui_state(self, state):
        if not state: return
        self.main_splitter.restoreState(state.get('main_splitter_state'))
        self.category_tree.header().restoreState(state.get('category_tree_header'))
        self.file_list_tree.header().restoreState(state.get('file_list_header'))

    def get_ui_state(self):
        return {
            'main_splitter_state': self.main_splitter.saveState(),
            'category_tree_header': self.category_tree.header().saveState(),
            'file_list_header': self.file_list_tree.header().saveState(),
        }
