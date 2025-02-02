"""
Manage Redis server process.
"""
import sys
import os
import signal
import subprocess
import time
from pathlib import Path
import psutil

def get_pid():
    """Get Redis server PID if running."""
    pid_file = Path(__file__).parent.parent / "redis.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            if psutil.pid_exists(pid):
                return pid
        except:
            pass
    return None

def start_server():
    """Start Redis server."""
    pid = get_pid()
    if pid:
        print("Redis server is already running")
        return
    
    print("Starting Redis server...")
    subprocess.Popen(
        [sys.executable, "scripts/run_redis.py"],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    
    # Wait for server to start
    for _ in range(5):
        if get_pid():
            print("Redis server started")
            return
        time.sleep(1)
    
    print("Failed to start Redis server")

def stop_server():
    """Stop Redis server."""
    pid = get_pid()
    if not pid:
        print("Redis server is not running")
        return
    
    print("Stopping Redis server...")
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        if psutil.pid_exists(pid):
            os.kill(pid, signal.SIGKILL)
        print("Redis server stopped")
    except:
        print("Failed to stop Redis server")

def server_status():
    """Check Redis server status."""
    pid = get_pid()
    if pid:
        print(f"Redis server is running (PID: {pid})")
    else:
        print("Redis server is not running")

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python manage_redis.py [start|stop|status]")
        return
    
    command = sys.argv[1].lower()
    
    if command == "start":
        start_server()
    elif command == "stop":
        stop_server()
    elif command == "status":
        server_status()
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
