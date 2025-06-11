import os
import os
import shutil
import time
import logging
import uuid
import json
from PyQt6.QtCore import QObject, pyqtSignal, QStandardPaths
from send2trash import send2trash
from .database_logger import log_event
from .deletion_logger import log_deletion, logger, format_size

APP_NAME = "MasterDeleter"
QUARANTINE_DIR = os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation), APP_NAME, "quarantine")
METADATA_FILE = os.path.join(QUARANTINE_DIR, "quarantine_metadata.json")

# Error code for "The cloud file provider is not running."
WIN_ERROR_CLOUD_PROVIDER_NOT_RUNNING = 362

class Deleter(QObject):
    finished = pyqtSignal(list, list) # succeeded_items, failed
    progress = pyqtSignal(int, str) # value, text
    error = pyqtSignal(str) # Emits the path of the problematic file
    
    def __init__(self, items_to_delete, use_recycle_bin=True):
        super().__init__()
        self.items_to_delete = items_to_delete
        self.use_recycle_bin = use_recycle_bin
        self._is_running = True

    def run(self):
        succeeded = []
        failed = []
        total_items = len(self.items_to_delete)
        for i, item in enumerate(self.items_to_delete):
            if not self._is_running:
                break
            
            path = os.path.normpath(item['path'])
            try:
                if self.use_recycle_bin:
                    self.send_to_recycle_bin(path, item.get('size'))
                    log_event("recycle", path, item.get('size'), "Recycle Bin")
                    log_deletion(item, "Recycle Bin", "Recycle Bin")
                    succeeded.append(item)
                else:
                    self.quarantine_file(path, item.get('size'), item.get('category', ''), item)
                    succeeded.append(item)
                
                progress_percent = int(((i + 1) / total_items) * 100)
                self.progress.emit(progress_percent, f"Processing: {os.path.basename(path)}")

            except OSError as e:
                # Check if the error is the specific cloud provider error
                if hasattr(e, 'winerror') and e.winerror == WIN_ERROR_CLOUD_PROVIDER_NOT_RUNNING:
                    logging.warning(f"Cloud file error for {path}: {e}")
                    self.error.emit(path)
                    failed.append({'item': item, 'error': "File is online and cloud provider is not running."})
                else:
                    logging.error(f"Failed to delete {path}: {e}")
                    failed.append({'item': item, 'error': str(e)})
            except Exception as e:
                logging.error(f"An unexpected error occurred while deleting {path}: {e}")
                failed.append({'item': item, 'error': str(e)})
        
        logger.info(f"Deletion thread finished. Succeeded: {len(succeeded)}, Failed: {len(failed)}")
        self.finished.emit(succeeded, failed)

    def stop(self):
        self._is_running = False

    def send_to_recycle_bin(self, path, size):
        try:
            send2trash(path)
            log_deletion(path, size, "Recycled")
        except Exception as e:
            logger.error(f"Error sending to recycle bin {path}: {e}")
            raise

    def quarantine_file(self, path, size, category, full_item_data=None):
        if not os.path.exists(QUARANTINE_DIR):
            os.makedirs(QUARANTINE_DIR)

        try:
            # Generate a unique name to avoid conflicts
            base_name = os.path.basename(path)
            unique_id = uuid.uuid4().hex[:8]
            quarantined_name = f"{unique_id}_{base_name}"
            destination_path = os.path.join(QUARANTINE_DIR, quarantined_name)
            
            # Handle both files and directories safely
            if os.path.isdir(path):
                # For directories, use copytree then remove original
                shutil.copytree(path, destination_path)
                shutil.rmtree(path)
                logging.info(f"Quarantined directory '{path}' as '{quarantined_name}'")
            else:
                # For files, use move (which is faster)
                shutil.move(path, destination_path)
                logging.info(f"Quarantined file '{path}' as '{quarantined_name}'")

            self.update_quarantine_metadata(quarantined_name, path, category, full_item_data)

            log_deletion(path, size, "Quarantined", quarantined_path=destination_path)
        except Exception as e:
            logger.error(f"Error quarantining {path}: {e}")
            raise
    
    def update_quarantine_metadata(self, quarantined_name, original_path, category, full_item_data=None):
        metadata = {}
        if os.path.exists(METADATA_FILE):
            try:
                with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass # Ignore if file is empty, corrupt, or missing

        # Store basic required metadata
        item_metadata = {
            'original_path': os.path.normpath(original_path),
            'quarantine_date': time.time(),
            'category': category
        }
        
        # Store additional metadata if available (like suggestion confidence, etc.)
        if full_item_data and isinstance(full_item_data, dict):
            # Extract useful metadata from the full item data
            if 'data' in full_item_data and isinstance(full_item_data['data'], dict):
                item_data = full_item_data['data']
                # Preserve suggestion-related metadata
                if 'suggestion_confidence' in item_data:
                    item_metadata['suggestion_confidence'] = item_data['suggestion_confidence']
                if 'reason' in item_data:
                    item_metadata['reason'] = item_data['reason']
                if 'confidence' in item_data:
                    item_metadata['confidence'] = item_data['confidence']

        metadata[quarantined_name] = item_metadata

        try:
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4)
        except IOError as e:
            logger.error(f"Failed to write quarantine metadata: {e}")
