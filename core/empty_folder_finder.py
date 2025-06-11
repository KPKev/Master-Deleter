import os
from PyQt6.QtCore import QObject, pyqtSignal

class EmptyFolderFinderWorker(QObject):
    """Scans for empty folders in a separate thread."""
    progress_update = pyqtSignal(str)
    empty_folder_found = pyqtSignal(str)
    scan_finished = pyqtSignal(int) # Returns count of folders found

    def __init__(self, start_path, exclusions=None):
        super().__init__()
        self.start_path = start_path
        self._is_running = True
        self.folder_count = 0
        self.exclusions = [path.lower() for path in exclusions] if exclusions else []

    def run(self):
        """Scans for empty folders and emits them."""
        for root, dirs, files in os.walk(self.start_path, topdown=False):
            if not self._is_running:
                break
            
            lower_root = root.lower()
            if any(lower_root.startswith(ex) for ex in self.exclusions):
                continue

            if not dirs and not files:
                self.progress_update.emit(f"Found empty folder: {root}")
                self.empty_folder_found.emit(root)
                self.folder_count += 1
        
        self.scan_finished.emit(self.folder_count)

    def stop(self):
        self._is_running = False 