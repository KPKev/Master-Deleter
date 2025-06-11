#!/usr/bin/env python3
"""
Master Deleter - Supervised Launch
==================================

Launch script that starts the application under supervisor monitoring.
This provides automatic crash recovery and restart capabilities.

Usage: python launch_supervised.py [options]

Options:
  --direct    Launch the application directly without supervisor
  --status    Show supervisor status and exit
  --stop      Stop any running supervisor
"""

import sys
import os
import argparse
import subprocess
import time
import json
from pathlib import Path

def check_supervisor_running():
    """Check if supervisor is already running"""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'supervisor.py' in ' '.join(cmdline):
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        # psutil not available, can't check
        pass
    return None

def show_status():
    """Show supervisor status"""
    supervisor_pid = check_supervisor_running()
    
    print("Master Deleter Supervisor Status")
    print("=" * 40)
    
    if supervisor_pid:
        print(f"✅ Supervisor RUNNING (PID: {supervisor_pid})")
    else:
        print("❌ Supervisor NOT RUNNING")
    
    # Check for state files
    state_file = "supervisor_state.json"
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            print(f"📊 Total Starts: {state.get('total_starts', 0)}")
            print(f"💥 Total Crashes: {state.get('total_crashes', 0)}")
            if state.get('last_successful_start'):
                print(f"🕐 Last Start: {state['last_successful_start']}")
        except Exception as e:
            print(f"⚠️  Error reading state: {e}")
    
    # Check for crash logs
    crash_log = "supervisor_crash.log"
    if os.path.exists(crash_log):
        size = os.path.getsize(crash_log)
        print(f"📝 Crash Log: {size} bytes")
    else:
        print("📝 Crash Log: None")
    
    print("=" * 40)

def stop_supervisor():
    """Stop running supervisor"""
    supervisor_pid = check_supervisor_running()
    
    if not supervisor_pid:
        print("No supervisor running.")
        return
    
    print(f"Stopping supervisor (PID: {supervisor_pid})...")
    
    try:
        import psutil
        proc = psutil.Process(supervisor_pid)
        proc.terminate()
        
        # Wait for graceful shutdown
        try:
            proc.wait(timeout=10)
            print("✅ Supervisor stopped gracefully")
        except psutil.TimeoutExpired:
            print("⚠️  Supervisor didn't stop gracefully, forcing...")
            proc.kill()
            print("✅ Supervisor force-stopped")
            
    except ImportError:
        print("❌ psutil not available, cannot stop supervisor programmatically")
        print(f"Please manually terminate process {supervisor_pid}")
    except Exception as e:
        print(f"❌ Error stopping supervisor: {e}")

def launch_direct():
    """Launch application directly without supervisor"""
    print("Launching Master Deleter directly...")
    try:
        subprocess.run([sys.executable, "main.py"])
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Error launching application: {e}")

def launch_supervised():
    """Launch application under supervisor"""
    # Check if supervisor is already running
    if check_supervisor_running():
        print("⚠️  Supervisor is already running!")
        print("Use --status to check status or --stop to stop it first.")
        return
    
    print("🚀 Starting Master Deleter with Supervisor...")
    print("This provides automatic crash recovery and restart capabilities.")
    print("Press Ctrl+C to stop both supervisor and application.")
    print("=" * 60)
    
    try:
        # Start supervisor
        subprocess.run([sys.executable, "supervisor.py"])
    except KeyboardInterrupt:
        print("\n⚠️  Supervisor interrupted by user")
    except Exception as e:
        print(f"❌ Error starting supervisor: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Master Deleter Supervised Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--direct', action='store_true',
                        help='Launch application directly without supervisor')
    parser.add_argument('--status', action='store_true',
                        help='Show supervisor status and exit')
    parser.add_argument('--stop', action='store_true',
                        help='Stop any running supervisor')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
        return
    
    if args.stop:
        stop_supervisor()
        return
    
    if args.direct:
        launch_direct()
        return
    
    # Default: launch supervised
    launch_supervised()

if __name__ == "__main__":
    main()