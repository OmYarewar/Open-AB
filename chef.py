import os
import sys
import time
import uuid
import shutil
import subprocess
import json

from typing import Dict, Any

NUM_WORKERS = 3  # Start with 3 concurrent workers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACES_DIR = os.path.join(BASE_DIR, "workspaces")
SYSTEM_STATE_FILE = os.path.join(BASE_DIR, "system_state.json")
PENDING_KILLS_FILE = os.path.join(BASE_DIR, "pending_kills.json")

# Provide the 2 API keys for the workers to use
API_KEYS = [
    os.environ.get("NVIDIA_API_KEY_1"),
    os.environ.get("NVIDIA_API_KEY_2")
]

class Worker:
    def __init__(self, id: str, process: subprocess.Popen, workspace_dir: str, start_time: float):
        self.id = id
        self.process = process
        self.workspace_dir = workspace_dir
        self.start_time = start_time

def spawn_worker(worker_id: str, api_key: str) -> Worker:
    workspace_dir = os.path.join(WORKSPACES_DIR, worker_id)
    os.makedirs(workspace_dir, exist_ok=True)

    env = os.environ.copy()
    env["NVIDIA_API_KEY"] = api_key
    env["PYTHONPATH"] = BASE_DIR # Ensure shared_skills can be imported

    # Run the worker process
    process = subprocess.Popen(
        [sys.executable, os.path.join(BASE_DIR, "worker.py"), workspace_dir, worker_id],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True
    )

    print(f"[Chef] Spawned worker {worker_id} in {workspace_dir}")
    return Worker(id=worker_id, process=process, workspace_dir=workspace_dir, start_time=time.time())


def write_system_state(workers: Dict[str, Worker]):
    state = {
        "status": "RUNNING",
        "timestamp": time.time(),
        "workers": []
    }
    for w_id, w in workers.items():
        status_file = os.path.join(w.workspace_dir, "status.txt")
        last_log = ""
        if os.path.exists(status_file):
            try:
                with open(status_file, "r") as f:
                    lines = f.readlines()
                    if lines: last_log = lines[-1].strip()
            except: pass

        state["workers"].append({
            "id": w_id,
            "uptime": time.time() - w.start_time,
            "workspace": w.workspace_dir,
            "last_log": last_log
        })
    with open(SYSTEM_STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def read_pending_kills() -> Dict:
    if os.path.exists(PENDING_KILLS_FILE):
        try:
            with open(PENDING_KILLS_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {}

def write_pending_kills(pending: Dict):
    with open(PENDING_KILLS_FILE, "w") as f:
        json.dump(pending, f, indent=4)

def process_approved_kills(workers: Dict[str, Worker]) -> list:
    pending = read_pending_kills()
    to_remove = []
    for w_id, status in list(pending.items()):
        if status == "APPROVED":
            if w_id in workers:
                cleanup_worker(workers[w_id])
                to_remove.append(w_id)
            del pending[w_id]
        elif status == "REJECTED":
            del pending[w_id]
    write_pending_kills(pending)
    return to_remove

def evaluate_worker(worker: Worker) -> bool:
    """Evaluate if a worker should be killed. Returns True if worker is underperforming."""
    status_file = os.path.join(worker.workspace_dir, "status.txt")

    if not os.path.exists(status_file):
        # Initial reply rule: if no reply under 5 min, kill
        if time.time() - worker.start_time > 300: # 5 mins
            print(f"[Chef] Worker {worker.id} hasn't replied in 5 mins. Killing.")
            return True
        return False

    try:
        with open(status_file, "r") as f:
            lines = f.readlines()

        if not lines:
            if time.time() - worker.start_time > 300:
                print(f"[Chef] Worker {worker.id} status file is empty after 5 mins. Killing.")
                return True
            return False

        # Basic heuristic: if it says "failed", "stuck", or hasn't updated recently
        last_line = lines[-1].lower()
        if "stuck" in last_line or "error" in last_line:
            print(f"[Chef] Worker {worker.id} seems stuck based on status: {last_line.strip()}. Killing.")
            return True

        # Check last modification time
        mtime = os.path.getmtime(status_file)
        if time.time() - mtime > 900: # 15 minutes without update
            print(f"[Chef] Worker {worker.id} idle for 15 mins. Killing.")
            return True

        return False
    except Exception as e:
        print(f"[Chef] Error evaluating worker {worker.id}: {e}")
        return False

def cleanup_worker(worker: Worker):
    try:
        worker.process.terminate()
        worker.process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        worker.process.kill()

    print(f"[Chef] Cleaned up worker process {worker.id}")

    # Optionally remove workspace to start fresh
    try:
        shutil.rmtree(worker.workspace_dir)
    except Exception as e:
        print(f"[Chef] Error removing workspace for {worker.id}: {e}")

def main():
    print("[Chef] Starting Autonomous Worker Management System...")

    if not API_KEYS[0] and not API_KEYS[1]:
        print("[Chef] Warning: No NVIDIA_API_KEY_1 or NVIDIA_API_KEY_2 found in environment.")
        # Proceed anyway for testing, but API calls will fail.

    workers: Dict[str, Worker] = {}

    # Initial spawn
    for i in range(NUM_WORKERS):
        worker_id = str(uuid.uuid4())[:8]
        # Distribute keys
        api_key = API_KEYS[i % 2] if API_KEYS[i % 2] else "dummy_key"
        workers[worker_id] = spawn_worker(worker_id, api_key)

    try:
        while True:
            manual_kill = os.environ.get("MANUAL_KILL_CONFIRM", "False").lower() == "true"
            write_system_state(workers)

            # Check on workers
            to_remove = []
            pending = read_pending_kills()

            for w_id, worker in workers.items():
                # Check if process died on its own
                if worker.process.poll() is not None:
                    print(f"[Chef] Worker {w_id} died unexpectedly with code {worker.process.returncode}.")
                    to_remove.append(w_id)
                    if w_id in pending: del pending[w_id]
                    continue

                # Evaluate performance
                if evaluate_worker(worker):
                    if manual_kill:
                        if w_id not in pending:
                            print(f"[Chef] Flagged worker {w_id} for manual kill confirmation.")
                            pending[w_id] = "PENDING"
                    else:
                        cleanup_worker(worker)
                        to_remove.append(w_id)

            write_pending_kills(pending)

            if manual_kill:
                to_remove.extend(process_approved_kills(workers))
            # Remove and respawn
            for w_id in to_remove:
                del workers[w_id]
                new_id = str(uuid.uuid4())[:8]
                api_key = API_KEYS[len(workers) % 2] if API_KEYS[len(workers) % 2] else "dummy_key"
                workers[new_id] = spawn_worker(new_id, api_key)

            time.sleep(30) # Wait before next evaluation loop

    except KeyboardInterrupt:
        print("[Chef] Shutting down. Cleaning up workers...")
        for worker in workers.values():
            cleanup_worker(worker)

if __name__ == "__main__":
    main()
