#!/usr/bin/env python3
"""
Master Deleter Application Supervisor/Hypervisor
================================================

A stable monitoring environment that:
- Watches the main application for crashes
- Automatically restarts on failure
- Preserves application state
- Logs all crash information
- Provides crash recovery and diagnostics

Usage: python supervisor.py
"""

import os
import sys
import time
import json
import logging
import subprocess
import signal
import traceback
import psutil
from datetime import datetime
from pathlib import Path

# Supervisor Configuration
APP_SCRIPT = "main.py"
MAX_RESTART_ATTEMPTS = 5
RESTART_DELAY = 2.0  # seconds
CRASH_LOG_FILE = "supervisor_crash.log"
STATE_FILE = "supervisor_state.json"
HEALTH_CHECK_INTERVAL = 1.0  # seconds

class ApplicationSupervisor:
    def __init__(self):
        self.setup_logging()
        self.app_process = None
        self.restart_count = 0
        self.start_time = datetime.now()
        self.last_crash_time = None
        self.is_running = True
        self.state = self.load_state()
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.logger.info("=== Master Deleter Supervisor Started ===")
        self.logger.info(f"Monitoring: {APP_SCRIPT}")
        self.logger.info(f"PID: {os.getpid()}")

    def setup_logging(self):
        """Setup comprehensive logging for the supervisor"""
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configure supervisor logger
        self.logger = logging.getLogger("supervisor")
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # File handler for supervisor logs
        file_handler = logging.FileHandler(log_dir / "supervisor.log")
        file_handler.setLevel(logging.INFO)
        
        # Console handler for real-time monitoring
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Detailed formatter
        formatter = logging.Formatter(
            '%(asctime)s - SUPERVISOR - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def load_state(self):
        """Load supervisor state from file"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                    self.logger.info(f"Loaded supervisor state: {state}")
                    return state
        except Exception as e:
            self.logger.warning(f"Could not load supervisor state: {e}")
        
        # Default state
        return {
            "total_starts": 0,
            "total_crashes": 0,
            "last_successful_start": None,
            "crash_history": []
        }

    def save_state(self):
        """Save supervisor state to file"""
        try:
            self.state["last_update"] = datetime.now().isoformat()
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save supervisor state: {e}")

    def start_application(self):
        """Start the main application process"""
        try:
            self.logger.info(f"Starting application: {APP_SCRIPT}")
            
            # Start the application with Python
            self.app_process = subprocess.Popen(
                [sys.executable, APP_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd(),
                bufsize=1,
                universal_newlines=True
            )
            
            self.state["total_starts"] += 1
            self.state["last_successful_start"] = datetime.now().isoformat()
            self.save_state()
            
            self.logger.info(f"Application started with PID: {self.app_process.pid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start application: {e}")
            self.log_crash("Failed to start", str(e))
            return False

    def is_application_healthy(self):
        """Check if the application is still running and healthy"""
        if not self.app_process:
            return False
            
        # Check if process is still running
        poll_result = self.app_process.poll()
        if poll_result is not None:
            return False
            
        # Additional health checks can be added here
        # For example, checking if the application responds to signals
        try:
            # Check if the process exists and is responsive
            process = psutil.Process(self.app_process.pid)
            if process.status() == psutil.STATUS_ZOMBIE:
                return False
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
            
        return True

    def log_crash(self, crash_type, error_details):
        """Log detailed crash information"""
        crash_info = {
            "timestamp": datetime.now().isoformat(),
            "crash_type": crash_type,
            "error_details": error_details,
            "restart_count": self.restart_count,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        }
        
        # Add to crash history
        self.state["total_crashes"] += 1
        self.state["crash_history"].append(crash_info)
        
        # Keep only last 10 crashes in history
        if len(self.state["crash_history"]) > 10:
            self.state["crash_history"] = self.state["crash_history"][-10:]
        
        self.save_state()
        
        # Log to supervisor crash log
        try:
            with open(CRASH_LOG_FILE, 'a') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"CRASH REPORT - {crash_info['timestamp']}\n")
                f.write(f"{'='*80}\n")
                f.write(f"Type: {crash_type}\n")
                f.write(f"Details: {error_details}\n")
                f.write(f"Restart Count: {self.restart_count}\n")
                f.write(f"Uptime: {crash_info['uptime_seconds']:.2f} seconds\n")
                f.write(f"{'='*80}\n")
        except Exception as e:
            self.logger.error(f"Could not write to crash log: {e}")

    def collect_application_logs(self):
        """Collect stdout/stderr from the application process"""
        if not self.app_process:
            return "", ""
            
        try:
            # Read available output (non-blocking)
            stdout_data = ""
            stderr_data = ""
            
            if self.app_process.stdout:
                self.app_process.stdout.settimeout(0.1)
                try:
                    stdout_data = self.app_process.stdout.read()
                except:
                    pass
                    
            if self.app_process.stderr:
                self.app_process.stderr.settimeout(0.1)
                try:
                    stderr_data = self.app_process.stderr.read()
                except:
                    pass
                    
            return stdout_data, stderr_data
            
        except Exception as e:
            self.logger.error(f"Error collecting application logs: {e}")
            return "", ""

    def restart_application(self):
        """Restart the application after a crash"""
        self.restart_count += 1
        self.last_crash_time = datetime.now()
        
        self.logger.warning(f"Application restart #{self.restart_count}")
        
        # Check restart limits
        if self.restart_count > MAX_RESTART_ATTEMPTS:
            self.logger.critical(f"Maximum restart attempts ({MAX_RESTART_ATTEMPTS}) exceeded!")
            self.logger.critical("Supervisor shutting down to prevent infinite restart loop")
            return False
        
        # Cleanup previous process
        if self.app_process:
            try:
                self.app_process.terminate()
                self.app_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.app_process.kill()
            except Exception as e:
                self.logger.error(f"Error terminating process: {e}")
        
        # Wait before restart
        self.logger.info(f"Waiting {RESTART_DELAY} seconds before restart...")
        time.sleep(RESTART_DELAY)
        
        # Attempt restart
        if self.start_application():
            self.logger.info("Application restarted successfully")
            return True
        else:
            self.logger.error("Failed to restart application")
            return False

    def signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.is_running = False

    def run(self):
        """Main supervisor loop"""
        self.logger.info("Supervisor entering main monitoring loop")
        
        # Start the application initially
        if not self.start_application():
            self.logger.critical("Failed to start application initially. Exiting.")
            return 1
        
        try:
            while self.is_running:
                # Health check
                if not self.is_application_healthy():
                    self.logger.warning("Application health check failed!")
                    
                    # Collect any final output
                    stdout, stderr = self.collect_application_logs()
                    if stdout:
                        self.logger.info(f"Application stdout: {stdout}")
                    if stderr:
                        self.logger.error(f"Application stderr: {stderr}")
                    
                    # Get exit code
                    exit_code = self.app_process.poll() if self.app_process else -1
                    
                    # Log the crash
                    error_details = f"Exit code: {exit_code}"
                    if stderr:
                        error_details += f", Stderr: {stderr}"
                    
                    self.log_crash("Application crash", error_details)
                    
                    # Attempt restart
                    if not self.restart_application():
                        break
                
                # Sleep between health checks
                time.sleep(HEALTH_CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            self.logger.info("Supervisor interrupted by user")
        except Exception as e:
            self.logger.critical(f"Supervisor error: {e}")
            self.logger.critical(traceback.format_exc())
        
        finally:
            self.cleanup()
        
        return 0

    def cleanup(self):
        """Clean shutdown of supervisor and application"""
        self.logger.info("Performing supervisor cleanup...")
        
        if self.app_process and self.app_process.poll() is None:
            self.logger.info("Terminating application process...")
            try:
                self.app_process.terminate()
                self.app_process.wait(timeout=5)
                self.logger.info("Application terminated gracefully")
            except subprocess.TimeoutExpired:
                self.logger.warning("Application didn't terminate, killing...")
                self.app_process.kill()
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")
        
        # Save final state
        self.save_state()
        self.logger.info("=== Master Deleter Supervisor Shutdown ===")

    def print_status(self):
        """Print current supervisor status"""
        print(f"\n{'='*60}")
        print(f"MASTER DELETER SUPERVISOR STATUS")
        print(f"{'='*60}")
        print(f"Application: {APP_SCRIPT}")
        print(f"Supervisor PID: {os.getpid()}")
        print(f"Application PID: {self.app_process.pid if self.app_process else 'Not running'}")
        print(f"Restart Count: {self.restart_count}")
        print(f"Total Starts: {self.state['total_starts']}")
        print(f"Total Crashes: {self.state['total_crashes']}")
        print(f"Uptime: {datetime.now() - self.start_time}")
        print(f"Last Crash: {self.last_crash_time or 'None'}")
        print(f"{'='*60}\n")


def main():
    """Main entry point"""
    print("Master Deleter Application Supervisor")
    print("====================================")
    print("Starting hypervisor environment...")
    
    supervisor = ApplicationSupervisor()
    
    try:
        return supervisor.run()
    except Exception as e:
        print(f"Fatal supervisor error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())