# Master Deleter Hypervisor System 🛡️

A robust process supervision and crash recovery system for the Master Deleter application.

## Overview

The Hypervisor System provides:
- **Automatic crash detection and recovery**
- **Application state persistence**
- **Detailed crash logging and diagnostics**
- **Automatic restart with state restoration**
- **Health monitoring and supervision**

## Quick Start

### Launch with Supervisor (Recommended)
```bash
python launch_supervised.py
```

### Launch Directly (No Protection)
```bash
python launch_supervised.py --direct
```

### Check Status
```bash
python launch_supervised.py --status
```

### Stop Supervisor
```bash
python launch_supervised.py --stop
```

## How It Works

### 1. Supervisor Process (`supervisor.py`)
- **Monitors** the main application process continuously
- **Detects crashes** through process health checks
- **Restarts automatically** on failure (up to 5 attempts)
- **Logs everything** for debugging and analysis
- **Preserves stability** as a minimal, reliable watchdog

### 2. Application State Persistence (`main.py`)
- **Saves state** every 30 seconds automatically
- **Records** current tab, scan path, settings, window position
- **Recovers** previous session on restart after crash
- **Cleans up** state files on normal shutdown

### 3. Crash Recovery System
- **Detects** unexpected application termination
- **Collects** crash logs and error output
- **Attempts restart** with exponential backoff
- **Restores** previous application state
- **Limits** restart attempts to prevent infinite loops

## Files Created

| File | Purpose |
|------|---------|
| `supervisor.py` | Main supervisor/hypervisor process |
| `launch_supervised.py` | Easy launcher with options |
| `supervisor_state.json` | Supervisor statistics and state |
| `supervisor_crash.log` | Detailed crash information |
| `app_state_recovery.json` | Application state for recovery |
| `logs/supervisor.log` | Supervisor activity log |

## Configuration

### Supervisor Settings (in `supervisor.py`)
```python
MAX_RESTART_ATTEMPTS = 5        # Maximum restart attempts
RESTART_DELAY = 2.0            # Delay between restarts (seconds)
HEALTH_CHECK_INTERVAL = 1.0    # How often to check app health
```

### Application Settings (in `main.py`)
```python
state_save_interval = 30       # State save frequency (seconds)
```

## Monitoring and Logs

### Real-time Monitoring
The supervisor provides real-time console output showing:
- Application start/stop events
- Health check status
- Crash detection and restart attempts
- State save operations

### Log Files
- **`logs/supervisor.log`** - Complete supervisor activity
- **`supervisor_crash.log`** - Detailed crash reports with stack traces
- **Regular app logs** - Normal application logging continues

### Status Checking
```bash
# Quick status check
python launch_supervised.py --status

# View recent crashes
tail supervisor_crash.log

# Monitor supervisor live
tail -f logs/supervisor.log
```

## Crash Recovery Process

1. **Crash Detected** - Supervisor notices application stopped
2. **Logs Collected** - stdout/stderr and exit code captured
3. **Crash Logged** - Detailed crash report written
4. **Restart Initiated** - Application restarted after delay
5. **State Recovered** - Previous session state restored
6. **Normal Operation** - Application continues where it left off

## Benefits

### For Users
- ✅ **No data loss** - Scans and settings preserved across crashes
- ✅ **Automatic recovery** - No manual intervention needed
- ✅ **Session continuity** - Pick up where you left off
- ✅ **Stability** - Supervisor is much simpler and more stable than main app

### For Developers
- ✅ **Crash diagnostics** - Detailed error information collected
- ✅ **Stability metrics** - Track application reliability
- ✅ **Easy debugging** - All crashes logged with context
- ✅ **State analysis** - See what was happening when crashes occur

## Advanced Usage

### Custom Supervisor Configuration
Edit `supervisor.py` to adjust:
- Restart limits and delays
- Health check intervals
- Log file locations
- State preservation rules

### Integration with Task Scheduler
You can schedule the supervisor to start automatically:
```bash
# Windows Task Scheduler
schtasks /create /tn "MasterDeleterSupervisor" /tr "python C:\path\to\launch_supervised.py" /sc onstart
```

### Development Mode
For development, you might want to:
```bash
# Launch directly for debugging
python launch_supervised.py --direct

# Or with reduced restart attempts during testing
# (Edit MAX_RESTART_ATTEMPTS in supervisor.py)
```

## Troubleshooting

### Supervisor Won't Start
- Check if already running: `python launch_supervised.py --status`
- Check Python path and dependencies
- Look for permission issues in logs directory

### Application Keeps Crashing
- Check `supervisor_crash.log` for error details
- Review recent changes or system updates
- Consider temporarily running direct mode for debugging

### State Recovery Issues
- Check if `app_state_recovery.json` exists and is valid
- Review application logs for recovery errors
- State files are automatically cleaned after 1 hour

### Performance Impact
The supervisor has minimal overhead:
- ~1MB memory usage
- Health checks every 1 second
- State saves every 30 seconds
- No impact on application performance

## Security Considerations

- Supervisor runs with same permissions as user
- No network connections or external dependencies
- All files stored locally in application directory
- State files contain only application settings (no sensitive data)

---

**The Hypervisor System ensures your Master Deleter application stays running and recovers gracefully from any crashes!** 🚀