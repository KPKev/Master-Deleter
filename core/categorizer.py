import os

# Define categories
CAT_SYSTEM = "Essential System Files"
CAT_APP = "Application Files"
CAT_DEV_PROJECT = "Development Projects"
CAT_USER_DOWNLOADS = "User Downloads"
CAT_USER_DOCUMENTS = "User Documents"
CAT_SAFE_DELETE = "Safe to Delete"
CAT_USER = "Other User Files"
CAT_UNKNOWN = "Unknown"

# Known paths and extensions
SYSTEM_PATHS = [
    os.environ.get('SystemRoot', 'C:\\Windows').lower()
]
PROGRAM_FILES_PATHS = [
    os.environ.get('ProgramFiles', 'C:\\Program Files').lower(),
    os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)').lower()
]
# More specific user paths
DOWNLOADS_PATH = os.path.expanduser('~/Downloads').lower()
DOCUMENTS_PATH = os.path.expanduser('~/Documents').lower()

USER_PATHS = {
    'pictures': os.path.expanduser('~/Pictures').lower(),
    'videos': os.path.expanduser('~/Videos').lower(),
    'music': os.path.expanduser('~/Music').lower(),
    'desktop': os.path.expanduser('~/Desktop').lower(),
}
SAFE_DELETE_EXT = ['.log', '.tmp', '.bak', '.dmp', '.temp', '.thumbcache']
SAFE_DELETE_FOLDERS = ['temp', 'tmp', 'cache', 'prefetch', '__pycache__']

DEV_PROJECT_INDICATORS = ['.git', 'node_modules', 'package.json', 'requirements.txt', '.sln', 'venv', '.idea', '.vscode']

def is_dev_project(path):
    """Checks if a path seems to be part of a development project."""
    path_parts = path.lower().split(os.sep)
    if any(indicator in path_parts for indicator in DEV_PROJECT_INDICATORS):
        return True
    try:
        for entry in os.scandir(path):
            if entry.name.lower() in DEV_PROJECT_INDICATORS:
                return True
    except (PermissionError, FileNotFoundError):
        pass
    return False

def categorize_path(path):
    """
    Categorizes a given path based on a set of rules.
    Order is important here.
    """
    lower_path = path.lower()
    
    # Check for safe to delete folders and extensions
    if any(folder in lower_path.split(os.sep) for folder in SAFE_DELETE_FOLDERS):
        return CAT_SAFE_DELETE
    if any(lower_path.endswith(ext) for ext in SAFE_DELETE_EXT):
        return CAT_SAFE_DELETE

    # Check for system paths
    if any(lower_path.startswith(p) for p in SYSTEM_PATHS):
        return CAT_SYSTEM

    # Check for program files
    if any(lower_path.startswith(p) for p in PROGRAM_FILES_PATHS):
        return CAT_APP

    # Check for development projects
    if is_dev_project(os.path.dirname(path)):
        return CAT_DEV_PROJECT

    # Check for specific user folders
    if lower_path.startswith(DOWNLOADS_PATH):
        return CAT_USER_DOWNLOADS
    if lower_path.startswith(DOCUMENTS_PATH):
        return CAT_USER_DOCUMENTS

    # Check for other user files
    if any(lower_path.startswith(p) for p in USER_PATHS.values()):
        return CAT_USER

    return CAT_UNKNOWN 