import os
from PyQt6.QtCore import QObject, pyqtSignal
from .categorizer import categorize_path

class Scanner(QObject):
    item_found = pyqtSignal(dict)
    dir_size_updated = pyqtSignal(str, int)
    progress_update = pyqtSignal(str)
    scan_finished = pyqtSignal(dict)

    def __init__(self, start_path='C:\\', exclusions=None):
        super().__init__()
        self.start_path = os.path.normpath(start_path)
        self._is_running = True
        self.dir_sizes = {}
        self.exclusions = [os.path.normpath(path.lower()) for path in exclusions] if exclusions else []

    def run(self):
        """Starts the file system scan."""
        print(f"Starting scan of {self.start_path}")
        
        for root, dirs, files in os.walk(self.start_path, topdown=True):
            if not self._is_running:
                break
            
            root = os.path.normpath(root)
            lower_root = root.lower()

            # More robust exclusion check at the top
            if lower_root.startswith(tuple(self.exclusions)):
                dirs[:] = [] # Don't traverse any further down this path
                continue # Skip processing this directory
            
            # Prune the directories to avoid traversing into excluded folders
            dirs[:] = [d for d in dirs if not os.path.normpath(os.path.join(lower_root, d)).startswith(tuple(self.exclusions))]
            
            self.progress_update.emit(f"Scanning: {root}")

            # Emit directories first
            for name in dirs:
                if not self._is_running:
                    break
                path = os.path.normpath(os.path.join(root, name))
                category = categorize_path(path)
                self.item_found.emit({'type': 'dir', 'path': path, 'size': 0, 'category': category})

            # Process files and update directory sizes
            current_dir_size = 0
            for name in files:
                if not self._is_running:
                    break
                try:
                    path = os.path.normpath(os.path.join(root, name))
                    
                    # Double-check exclusion for the file itself
                    if os.path.normpath(path.lower()).startswith(tuple(self.exclusions)):
                        continue

                    # Normalize the path for consistency
                    path = os.path.normpath(path)

                    stat_result = os.stat(path)
                    size = stat_result.st_size
                    mtime = stat_result.st_mtime
                    current_dir_size += size
                    category = categorize_path(path)
                    self.item_found.emit({'type': 'file', 'path': path, 'size': size, 'category': category, 'mtime': mtime})
                except (FileNotFoundError, PermissionError, OSError) as e:
                    print(f"Could not access file {path}: {e}")

            # Update size of current directory and all its parents
            if current_dir_size > 0:
                path = root
                while path.startswith(self.start_path):
                    path = os.path.normpath(path)
                    self.dir_sizes[path] = self.dir_sizes.get(path, 0) + current_dir_size
                    self.dir_size_updated.emit(path, self.dir_sizes[path])
                    parent = os.path.dirname(path)
                    if parent == path:
                        break
                    path = parent
        
        if self._is_running:
            self.scan_finished.emit(self.dir_sizes)

    def stop(self):
        self._is_running = False 