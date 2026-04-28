import os
import subprocess
import psutil
from flask import Flask, render_template_string, request, redirect, url_for
from dotenv import load_dotenv, set_key

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, '.env')

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Automaton System Configuration</title>
    <style>
        body { font-family: sans-serif; margin: 40px; background-color: #f4f4f9; color: #333; }
        .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1, h2 { color: #2c3e50; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], input[type="password"] { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        .btn { padding: 10px 15px; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-primary { background-color: #3498db; }
        .btn-success { background-color: #2ecc71; }
        .btn-danger { background-color: #e74c3c; }
        .status { margin-top: 20px; padding: 10px; background-color: #ecf0f1; border-radius: 4px; font-family: monospace; }
        .header-actions { display: flex; justify-content: space-between; align-items: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header-actions">
            <h1>Automaton Web GUI</h1>
            <div>
                <a href="{{ url_for('start') }}" class="btn btn-success">Start System</a>
                <a href="{{ url_for('stop') }}" class="btn btn-danger">Stop System</a>
            </div>
        </div>

        <div class="status">
            <strong>System Status:</strong> {{ status }}
        </div>

        <h2>Configuration</h2>
        <form method="POST" action="{{ url_for('save_config') }}">
            <div class="form-group">
                <label>NVIDIA API KEY 1</label>
                <input type="password" name="NVIDIA_API_KEY_1" value="{{ config.get('NVIDIA_API_KEY_1', '') }}">
            </div>
            <div class="form-group">
                <label>NVIDIA API KEY 2</label>
                <input type="password" name="NVIDIA_API_KEY_2" value="{{ config.get('NVIDIA_API_KEY_2', '') }}">
            </div>
            <div class="form-group">
                <label>Ethereum RPC URL</label>
                <input type="text" name="RPC_URL" value="{{ config.get('RPC_URL', '') }}" placeholder="https://mainnet.infura.io/v3/...">
            </div>
            <div class="form-group">
                <label>Wallet Private Key</label>
                <input type="password" name="PRIVATE_KEY" value="{{ config.get('PRIVATE_KEY', '') }}">
            </div>
            <button type="submit" class="btn btn-primary">Save Configuration</button>
        </form>
    </div>
</body>
</html>
"""

def get_chef_pid():
    """Find the PID of the running chef.py process."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and 'python' in cmdline[0] and 'chef.py' in ' '.join(cmdline):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def load_config():
    if not os.path.exists(ENV_FILE):
        return {}
    load_dotenv(ENV_FILE)
    return {
        'NVIDIA_API_KEY_1': os.environ.get('NVIDIA_API_KEY_1', ''),
        'NVIDIA_API_KEY_2': os.environ.get('NVIDIA_API_KEY_2', ''),
        'RPC_URL': os.environ.get('RPC_URL', ''),
        'PRIVATE_KEY': os.environ.get('PRIVATE_KEY', '')
    }

@app.route('/')
def index():
    pid = get_chef_pid()
    status = f"Running (PID: {pid})" if pid else "Stopped"
    config = load_config()
    return render_template_string(HTML_TEMPLATE, status=status, config=config)

@app.route('/save', methods=['POST'])
def save_config():
    if not os.path.exists(ENV_FILE):
        open(ENV_FILE, 'a').close()

    for key in ['NVIDIA_API_KEY_1', 'NVIDIA_API_KEY_2', 'RPC_URL', 'PRIVATE_KEY']:
        val = request.form.get(key, '')
        set_key(ENV_FILE, key, val)

    # Reload environment
    load_dotenv(ENV_FILE, override=True)
    return redirect(url_for('index'))

@app.route('/start')
def start():
    if not get_chef_pid():
        env = os.environ.copy()
        load_dotenv(ENV_FILE)
        # Add .env vars to env
        config = load_config()
        for k, v in config.items():
            env[k] = v

        chef_script = os.path.join(BASE_DIR, 'chef.py')
        log_file = open(os.path.join(BASE_DIR, 'chef.log'), 'w')
        subprocess.Popen(['python', chef_script], env=env, stdout=log_file, stderr=subprocess.STDOUT)
    return redirect(url_for('index'))

@app.route('/stop')
def stop():
    pid = get_chef_pid()
    if pid:
        try:
            psutil.Process(pid).terminate()
        except Exception:
            pass
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
