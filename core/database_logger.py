import sqlite3
import os
import time
import sqlite3
from PyQt6.QtCore import QStandardPaths

APP_NAME = "MasterDeleter"
DB_DIR = os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation), APP_NAME)
DB_PATH = os.path.join(DB_DIR, "history.db")

def get_db_connection():
    """Establishes a connection to the SQLite database, creating it if necessary."""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    conn = sqlite3.connect(DB_PATH)
    return conn

def setup_database():
    """Sets up the necessary tables in the database if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deletion_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            event_type TEXT NOT NULL,
            path TEXT NOT NULL,
            size_bytes INTEGER,
            destination TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_event(event_type, path, size_bytes=None, destination=None):
    """Logs an event to the deletion_history table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO deletion_history (timestamp, event_type, path, size_bytes, destination)
        VALUES (?, ?, ?, ?, ?)
    ''', (time.time(), event_type, path, size_bytes, destination))
    conn.commit()
    conn.close()

# Initialize the database on startup
setup_database() 