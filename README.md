# Master Deleter 🗂️🧹

A powerful, intelligent file management and cleanup application with built-in crash recovery and supervised execution.

## 🌟 Features

### 🔍 **Smart File Analysis**
- **Category-based file organization** (System, Apps, User files, etc.)
- **AI-powered deletion suggestions** using machine learning
- **Largest files detection** - Find space hogs instantly
- **Old & unused file identification** (1+ years old)
- **Empty folder finder** with bulk deletion
- **Duplicate file detection** with smart grouping

### 🛡️ **Safety & Recovery**
- **Quarantine system** - Safe deletion with restore capability
- **Recycle bin integration** - Use Windows recycle bin or quarantine
- **Exclusion management** - Protect important directories
- **Undo functionality** - Restore deleted files easily
- **Visual highlighting** - Green for restored, red for recently deleted

### 🤖 **Hypervisor System**
- **Automatic crash recovery** - Supervisor monitors and restarts
- **State persistence** - Never lose your scan progress
- **Comprehensive logging** - Track all operations and crashes
- **Process supervision** - Rock-solid stability layer

### 📋 **Management Tools**
- **Deletion history** - Track all cleanup operations
- **Scheduled scanning** - Automated cleanup routines
- **Real-time preview** - See file contents before deletion
- **Batch operations** - Process multiple files efficiently

## 🚀 Quick Start

### Prerequisites
```bash
pip install -r requirements.txt
```

### Launch Options

#### Supervised Mode (Recommended)
```bash
# Launch with automatic crash recovery
python launch_supervised.py

# Or double-click
start_master_deleter.bat
```

#### Direct Mode
```bash
# Launch without supervisor
python launch_supervised.py --direct

# Or traditional launch
python main.py
```

### Supervisor Management
```bash
# Check supervisor status
python launch_supervised.py --status

# Stop supervisor
python launch_supervised.py --stop
```

## 🏗️ Architecture

### Core Components
- **`main.py`** - Main application with PyQt6 interface
- **`supervisor.py`** - Process hypervisor for crash recovery
- **`launch_supervised.py`** - Smart launcher with supervision
- **`core/`** - Backend logic (scanning, deletion, AI suggestions)
- **`ui/`** - User interface components and styling

### Key Technologies
- **PyQt6** - Modern cross-platform GUI framework
- **scikit-learn** - Machine learning for deletion suggestions
- **psutil** - Process monitoring and management
- **send2trash** - Safe file deletion via recycle bin

## 🎨 User Interface

### Tabs Overview
1. **Smart Cleaner** - Main scanning and deletion interface
2. **Duplicates** - Find and remove duplicate files
3. **Empty Folders** - Locate and clean empty directories
4. **Quarantine** - Manage safely deleted files
5. **Schedule** - Set up automated cleanup routines
6. **Exclusions** - Configure protected directories
7. **Settings** - Application preferences and themes
8. **Logging** - View application activity logs
9. **History** - Track all deletion operations

### Visual Features
- **Dual themes** - Dark and light mode support
- **Active tab highlighting** - Blue tabs match button colors
- **Real-time feedback** - Progress bars and status updates
- **File highlighting** - Visual cues for recent operations

## 🛡️ Safety Features

### Quarantine System
- All non-recycle-bin deletions go to quarantine
- Metadata preservation for perfect restoration
- Bulk restore capabilities
- Automatic cleanup of old quarantine items

### Exclusion Management
- Protect system directories automatically
- User-configurable exclusion lists
- Path-based protection rules
- Visual indicators for protected areas

### Crash Recovery
- Automatic state saving every 30 seconds
- Complete session recovery after crashes
- Scan progress preservation
- Settings and preferences restoration

## 📊 Intelligent Features

### AI-Powered Suggestions
- Machine learning model trains on user deletion patterns
- Confidence scores for deletion recommendations
- Adaptive learning from user feedback
- Smart categorization of file types

### Smart Categorization
- **System Files** - OS and system components
- **Application Files** - Installed software files
- **User Files** - Documents, downloads, personal data
- **Development Projects** - Source code and dev files
- **Safe to Delete** - Temporary and cache files

## 🔧 Configuration

### Application Settings
- **Theme selection** - Dark/light mode toggle
- **Deletion method** - Recycle bin vs quarantine
- **Scan exclusions** - Directories to skip
- **Auto-suggestions** - AI recommendation settings

### Supervisor Configuration
```python
# In supervisor.py
MAX_RESTART_ATTEMPTS = 5        # Restart limit
RESTART_DELAY = 2.0            # Delay between restarts
HEALTH_CHECK_INTERVAL = 1.0    # Monitoring frequency
```

## 📝 Logging & Monitoring

### Log Files
- **Application logs** - Standard operation logging
- **Supervisor logs** - Process monitoring activity
- **Crash logs** - Detailed crash analysis
- **Deletion history** - Complete operation tracking

### Monitoring Features
- Real-time process health checks
- Crash detection and reporting
- Performance metrics tracking
- State persistence monitoring

## 🔄 Development

### Project Structure
```
Master-Deleter/
├── main.py                    # Main application
├── supervisor.py              # Process supervisor
├── launch_supervised.py       # Smart launcher
├── requirements.txt           # Dependencies
├── core/                      # Backend logic
│   ├── scanner.py            # File system scanning
│   ├── categorizer.py        # File categorization
│   ├── deleter.py            # Deletion operations
│   ├── suggester.py          # AI suggestions
│   └── ...
├── ui/                       # User interface
│   ├── cleaner_tab.py        # Main cleanup interface
│   ├── quarantine_tab.py     # Quarantine management
│   ├── style.qss            # Dark theme styling
│   └── ...
└── logs/                     # Application logs
```

### Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **PyQt6** - Excellent GUI framework
- **scikit-learn** - Powerful ML capabilities
- **psutil** - System monitoring tools
- **send2trash** - Safe deletion utilities

---

**Master Deleter - Clean your system with confidence and intelligence!** 🚀✨