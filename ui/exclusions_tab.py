from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListView, QPushButton, QFileDialog
from PyQt6.QtCore import QStringListModel, pyqtSignal

class ExclusionsTab(QWidget):
    exclusions_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.exclusions = []
        
        layout = QVBoxLayout(self)
        
        label = QLabel("Folders added here will be completely ignored by all scans and suggestions.")
        layout.addWidget(label)
        
        self.exclusions_list_view = QListView()
        self.exclusions_model = QStringListModel()
        self.exclusions_list_view.setModel(self.exclusions_model)
        layout.addWidget(self.exclusions_list_view)
        
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Folder to Exclusions")
        add_button.clicked.connect(self.add_exclusion)
        remove_button = QPushButton("Remove Selected Exclusion")
        remove_button.clicked.connect(self.remove_exclusion)
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        layout.addLayout(button_layout)

    def set_exclusions(self, exclusions_list):
        self.exclusions = exclusions_list
        self.exclusions_model.setStringList(self.exclusions)

    def add_exclusion(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder to Exclude")
        if directory and directory not in self.exclusions:
            self.exclusions.append(directory)
            self.exclusions_model.setStringList(self.exclusions)
            self.exclusions_changed.emit(self.exclusions)

    def remove_exclusion(self):
        selected_indexes = self.exclusions_list_view.selectedIndexes()
        if not selected_indexes: 
            return
            
        # Build a list of items to remove first
        to_remove = [self.exclusions_model.data(index, 0) for index in selected_indexes]

        # Filter the main list
        self.exclusions = [item for item in self.exclusions if item not in to_remove]
        
        # Update the model and emit the change
        self.exclusions_model.setStringList(self.exclusions)
        self.exclusions_changed.emit(self.exclusions)
