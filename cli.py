import os
import sys
import argparse
import subprocess
import psutil
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, '.env')

def get_monitor_pid():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and 'python' in cmdline[0] and 'monitor.py' in ' '.join(cmdline):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def start_system():
    pid = get_monitor_pid()
    if pid:
        print(f"System is already running (PID: {pid}).")
        return

    env = os.environ.copy()
    if os.path.exists(ENV_FILE):
        load_dotenv(ENV_FILE)
        for k in ['NVIDIA_API_KEY_1', 'NVIDIA_API_KEY_2', 'RPC_URL', 'PRIVATE_KEY']:
            val = os.environ.get(k)
            if val:
                env[k] = val

    chef_script = os.path.join(BASE_DIR, 'monitor.py')
    log_file = open(os.path.join(BASE_DIR, 'monitor.log'), 'w')

    process = subprocess.Popen(['python', chef_script], env=env, stdout=log_file, stderr=subprocess.STDOUT)
    print(f"System started (PID: {process.pid}). Logs are being written to monitor.log")

def stop_system():
    pid = get_monitor_pid()
    if not pid:
        print("System is not running.")
        return

    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=5)
        print(f"System stopped (PID: {pid}).")
    except psutil.TimeoutExpired:
        proc.kill()
        print(f"System forcefully stopped (PID: {pid}).")
    except Exception as e:
        print(f"Error stopping system: {e}")

def status_system():
    pid = get_monitor_pid()
    if pid:
        print(f"Status: RUNNING (PID: {pid})")
    else:
        print("Status: STOPPED")

def main():
    parser = argparse.ArgumentParser(description="Automaton CLI Manager")
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    subparsers.add_parser('start', help='Start the autonomous system')
    subparsers.add_parser('stop', help='Stop the autonomous system')
    subparsers.add_parser('status', help='Check the status of the autonomous system')

    args = parser.parse_args()

    if args.command == 'start':
        start_system()
    elif args.command == 'stop':
        stop_system()
    elif args.command == 'status':
        status_system()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
