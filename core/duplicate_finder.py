import os
import hashlib
from PyQt6.QtCore import QObject, pyqtSignal

class DuplicateFinderWorker(QObject):
    """Scans for duplicate files in a separate thread."""
    progress_update = pyqtSignal(str)
    duplicates_found = pyqtSignal(list)
    scan_finished = pyqtSignal()

    def __init__(self, start_path, exclusions=None):
        super().__init__()
        self.start_path = start_path
        self._is_running = True
        self.exclusions = [path.lower() for path in exclusions] if exclusions else []

    def hash_file(self, path, quick_hash=False):
        """
        Calculates the SHA256 hash of a file.
        If quick_hash is True, only hashes the first 8KB.
        """
        hasher = hashlib.sha256()
        try:
            with open(path, 'rb') as f:
                if quick_hash:
                    chunk = f.read(8192)
                    if not self._is_running: return None
                    hasher.update(chunk)
                else:
                    while chunk := f.read(8192):
                        if not self._is_running:
                            return None
                        hasher.update(chunk)
            return hasher.hexdigest()
        except (PermissionError, FileNotFoundError) as e:
            self.progress_update.emit(f"Could not access {os.path.basename(path)}: {e}")
            return None

    def run(self):
        """Scans for duplicates and emits a list of them."""
        try:
            self.progress_update.emit("Grouping files by size...")
            files_by_size = {}
            file_count = 0
            
            for root, _, files in os.walk(self.start_path):
                if not self._is_running: break
                
                lower_root = root.lower()
                if any(lower_root.startswith(ex) for ex in self.exclusions):
                    continue

                for filename in files:
                    if not self._is_running: break
                    file_count += 1
                    
                    # Update progress every 100 files
                    if file_count % 100 == 0:
                        self.progress_update.emit(f"Scanned {file_count} files...")
                    
                    path = os.path.normpath(os.path.join(root, filename))
                    try:
                        size = os.path.getsize(path)
                        if size > 1024: # Ignore small files for efficiency
                            if size in files_by_size:
                                files_by_size[size].append(path)
                            else:
                                files_by_size[size] = [path]
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
                    except Exception as e:
                        self.progress_update.emit(f"Error scanning {filename}: {str(e)}")
                        continue
            
            self.progress_update.emit("Identifying duplicates by content...")
            duplicates = []
            potential_dupes = {size: paths for size, paths in files_by_size.items() if len(paths) > 1}

            for size, paths in potential_dupes.items():
                if not self._is_running: break
                
                # 1. Quick Hash (first 8KB)
                files_by_quick_hash = {}
                for path in paths:
                    if not self._is_running: break
                    self.progress_update.emit(f"Analyzing: {os.path.basename(path)}")
                    q_hash = self.hash_file(path, quick_hash=True)
                    if q_hash:
                        if q_hash in files_by_quick_hash:
                            files_by_quick_hash[q_hash].append(path)
                        else:
                            files_by_quick_hash[q_hash] = [path]
                
                # 2. Full Hash (only for matching quick hashes)
                for q_hash, q_paths in files_by_quick_hash.items():
                    if len(q_paths) < 2: continue
                    if not self._is_running: break
                    
                    files_by_full_hash = {}
                    for path in q_paths:
                        if not self._is_running: break
                        self.progress_update.emit(f"Verifying: {os.path.basename(path)}")
                        full_hash = self.hash_file(path, quick_hash=False)
                        if full_hash:
                            if full_hash in files_by_full_hash:
                                files_by_full_hash[full_hash].append(path)
                            else:
                                files_by_full_hash[full_hash] = [path]
                    
                    for f_hash_paths in files_by_full_hash.values():
                        if len(f_hash_paths) > 1:
                            duplicates.append(f_hash_paths)

            if not self._is_running:
                self.progress_update.emit("Scan cancelled by user")
            else:
                self.progress_update.emit(f"Scan complete. Found {len(duplicates)} duplicate sets.")
                
            self.duplicates_found.emit(duplicates)
            self.scan_finished.emit()
            
        except Exception as e:
            self.progress_update.emit(f"Scan failed: {str(e)}")
            import traceback
            print(f"Duplicate scan error: {traceback.format_exc()}")
            self.duplicates_found.emit([])  # Empty results on error
            self.scan_finished.emit()

    def stop(self):
        """Stops the scanning process."""
        self._is_running = False 