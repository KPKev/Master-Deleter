import logging
import os
import math
import logging
from logging.handlers import RotatingFileHandler
from PyQt6.QtCore import QStandardPaths

APP_NAME = "MasterDeleter"
LOG_DIR = os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation), APP_NAME, "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

DELETION_LOGGER_NAME = "DeletionLogger"
DELETION_LOG_FILE = os.path.join(LOG_DIR, 'deletion_history.log')

# Create and configure the logger at the module level
logger = logging.getLogger(DELETION_LOGGER_NAME)
# Prevent adding handlers multiple times in case of re-import
if not logger.handlers:
    logger.setLevel(logging.INFO)
    logger.propagate = False
    # Create file handler with rotation
    handler = RotatingFileHandler(DELETION_LOG_FILE, maxBytes=2*1024*1024, backupCount=5, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def setup_deletion_logger():
    """Returns the pre-configured logger instance."""
    return logger

def format_size(size_bytes):
    if size_bytes is None:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024))) if size_bytes > 0 else 0
    p = pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def log_deletion(path, size_bytes, status, quarantined_path=None):
    """Logs a file deletion event."""
    size_formatted = format_size(size_bytes)
    log_message = f"File: {path} | Size: {size_formatted} | Status: {status}"
    if status == "Quarantined" and quarantined_path:
        log_message += f" | Quarantined to: {quarantined_path}"
    logger.info(log_message)

# Initialize the logger when the module is imported
setup_deletion_logger() 