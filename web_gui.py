import os
import json
import subprocess
import psutil
import requests
from flask import Flask, render_template_string, request, redirect, url_for, jsonify
from dotenv import load_dotenv, set_key

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, '.env')
SYSTEM_STATE_FILE = os.path.join(BASE_DIR, 'system_state.json')
PENDING_KILLS_FILE = os.path.join(BASE_DIR, 'pending_kills.json')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Automaton Command Center</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background-color: #f0f2f5; color: #333; }
        .navbar { background-color: #2c3e50; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .navbar h1 { margin: 0; font-size: 24px; }
        .nav-links a { color: white; text-decoration: none; margin-left: 20px; padding: 5px 10px; border-radius: 4px; }
        .nav-links a.active, .nav-links a:hover { background-color: #34495e; }

        .container { max-width: 1000px; margin: 20px auto; padding: 0 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }

        .btn { padding: 10px 15px; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; font-size: 14px; }
        .btn-primary { background-color: #3498db; }
        .btn-success { background-color: #2ecc71; }
        .btn-danger { background-color: #e74c3c; }
        .btn-warning { background-color: #f1c40f; color: #333; }
        .btn-sm { padding: 5px 10px; font-size: 12px; }

        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        .log-snippet { font-family: monospace; background: #eee; padding: 2px 5px; border-radius: 3px; font-size: 12px; }

        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        input[type="checkbox"] { transform: scale(1.2); margin-right: 10px; }

        .chat-box { height: 300px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; background: #f9f9f9; border-radius: 4px; margin-bottom: 10px; }
        .chat-msg { margin-bottom: 10px; }
        .chat-user { color: #2980b9; font-weight: bold; }
        .chat-monitor { color: #27ae60; font-weight: bold; }
    </style>
    <script>
        // Auto-refresh Dashboard every 5 seconds
        if(window.location.pathname === '/') {
            setTimeout(() => window.location.reload(), 5000);
        }
    </script>
</head>
<body>
    <div class="navbar">
        <h1>Automaton Command Center</h1>
        <div class="nav-links">
            <a href="/" class="{{ 'active' if tab == 'dashboard' else '' }}">Dashboard</a>
            <a href="/config" class="{{ 'active' if tab == 'config' else '' }}">Configuration</a>
            <a href="/chat" class="{{ 'active' if tab == 'chat' else '' }}">Monitor Chat</a>
        </div>
    </div>

    <div class="container">
        {% if tab == 'dashboard' %}
            <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2>System Status: <span style="color: {{ 'green' if is_running else 'red' }}">{{ 'RUNNING' if is_running else 'STOPPED' }}</span></h2>
                </div>
                <div>
                    {% if not is_running %}
                        <a href="/start" class="btn btn-success">Start System</a>
                    {% else %}
                        <a href="/stop" class="btn btn-danger">Stop System</a>
                    {% endif %}
                </div>
            </div>

            <div class="card">
                <h2>Active Workers</h2>
                {% if state and state.workers %}
                    <table>
                        <tr>
                            <th>Worker ID</th>
                            <th>Uptime (s)</th>
                            <th>Latest Status Log</th>
                            <th>Actions</th>
                        </tr>
                        {% for w in state.workers %}
                        <tr>
                            <td>{{ w.id }}</td>
                            <td>{{ "%.1f"|format(w.uptime) }}</td>
                            <td><span class="log-snippet">{{ w.last_log[:60] }}...</span></td>
                            <td>
                                {% if w.id in pending_kills and pending_kills[w.id] == 'PENDING' %}
                                    <span style="color: red; font-weight: bold;">Kill Requested</span>
                                    <a href="/resolve_kill/{{ w.id }}/APPROVED" class="btn btn-danger btn-sm">Approve</a>
                                    <a href="/resolve_kill/{{ w.id }}/REJECTED" class="btn btn-warning btn-sm">Reject</a>
                                {% else %}
                                    <span style="color: green;">Healthy</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                {% else %}
                    <p>No workers running currently.</p>
                {% endif %}
            </div>

        {% elif tab == 'config' %}
            <div class="card">
                <h2>System Configuration</h2>
                <form method="POST" action="/save">
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
                        <input type="text" name="RPC_URL" value="{{ config.get('RPC_URL', '') }}">
                    </div>
                    <div class="form-group">
                        <label>Wallet Private Key</label>
                        <input type="password" name="PRIVATE_KEY" value="{{ config.get('PRIVATE_KEY', '') }}">
                    </div>
                    <div class="form-group" style="display: flex; align-items: center; margin-top: 20px;">
                        <input type="checkbox" name="MANUAL_KILL_CONFIRM" value="True" {{ 'checked' if config.get('MANUAL_KILL_CONFIRM') == 'True' else '' }}>
                        <label style="margin: 0;">Require manual confirmation before Monitor kills a worker</label>
                    </div>
                    <button type="submit" class="btn btn-primary" style="margin-top: 15px;">Save Configuration</button>
                </form>
            </div>

        {% elif tab == 'chat' %}
            <div class="card">
                <h2>Chat with Chef AI</h2>
                <p>Discuss system strategy, view agent logic, or manually command the orchestrator.</p>
                <div class="chat-box" id="chatbox">
                    <div class="chat-msg"><span class="chat-monitor">Monitor AI:</span> Hello! I am managing your workers. How can I assist you today?</div>
                </div>
                <div style="display: flex;">
                    <input type="text" id="chat-input" placeholder="Ask the Monitor..." style="flex-grow: 1; margin-right: 10px;" onkeypress="if(event.key === 'Enter') sendChat()">
                    <button class="btn btn-primary" onclick="sendChat()">Send</button>
                </div>
                <script>
                    function escapeHtml(unsafe) {
                        return unsafe
                             .replace(/&/g, "&amp;")
                             .replace(/</g, "&lt;")
                             .replace(/>/g, "&gt;")
                             .replace(/"/g, "&quot;")
                             .replace(/'/g, "&#039;");
                    }

                    function sendChat() {
                        const input = document.getElementById('chat-input');
                        const msg = input.value;
                        if(!msg) return;

                        const chatbox = document.getElementById('chatbox');
                        chatbox.innerHTML += `<div class="chat-msg"><span class="chat-user">You:</span> ${escapeHtml(msg)}</div>`;
                        input.value = '';
                        chatbox.scrollTop = chatbox.scrollHeight;

                        fetch('/api/chat', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({message: msg})
                        }).then(res => res.json()).then(data => {
                            chatbox.innerHTML += `<div class="chat-msg"><span class="chat-monitor">Monitor AI:</span> ${escapeHtml(data.reply)}</div>`;
                            chatbox.scrollTop = chatbox.scrollHeight;
                        });
                    }
                </script>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

def get_monitor_pid():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and 'python' in cmdline[0] and 'monitor.py' in ' '.join(cmdline):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def load_config():
    if not os.path.exists(ENV_FILE): return {}
    load_dotenv(ENV_FILE)
    return {
        'NVIDIA_API_KEY_1': os.environ.get('NVIDIA_API_KEY_1', ''),
        'NVIDIA_API_KEY_2': os.environ.get('NVIDIA_API_KEY_2', ''),
        'RPC_URL': os.environ.get('RPC_URL', ''),
        'PRIVATE_KEY': os.environ.get('PRIVATE_KEY', ''),
        'MANUAL_KILL_CONFIRM': os.environ.get('MANUAL_KILL_CONFIRM', 'False')
    }

@app.route('/')
def dashboard():
    state = {}
    pending_kills = {}
    if os.path.exists(SYSTEM_STATE_FILE):
        try:
            with open(SYSTEM_STATE_FILE, 'r') as f: state = json.load(f)
        except: pass
    if os.path.exists(PENDING_KILLS_FILE):
        try:
            with open(PENDING_KILLS_FILE, 'r') as f: pending_kills = json.load(f)
        except: pass

    return render_template_string(HTML_TEMPLATE, tab='dashboard', is_running=bool(get_monitor_pid()), state=state, pending_kills=pending_kills)

@app.route('/config')
def config_page():
    return render_template_string(HTML_TEMPLATE, tab='config', config=load_config(), is_running=bool(get_monitor_pid()))

@app.route('/chat')
def chat_page():
    return render_template_string(HTML_TEMPLATE, tab='chat', is_running=bool(get_monitor_pid()))

@app.route('/save', methods=['POST'])
def save_config():
    if not os.path.exists(ENV_FILE): open(ENV_FILE, 'a').close()
    for key in ['NVIDIA_API_KEY_1', 'NVIDIA_API_KEY_2', 'RPC_URL', 'PRIVATE_KEY']:
        set_key(ENV_FILE, key, request.form.get(key, ''))
    set_key(ENV_FILE, 'MANUAL_KILL_CONFIRM', 'True' if request.form.get('MANUAL_KILL_CONFIRM') else 'False')
    load_dotenv(ENV_FILE, override=True)
    return redirect(url_for('config_page'))

@app.route('/start')
def start():
    if not get_monitor_pid():
        env = os.environ.copy()
        load_dotenv(ENV_FILE)
        config = load_config()
        for k, v in config.items(): env[k] = v
        chef_script = os.path.join(BASE_DIR, 'monitor.py')
        log_file = open(os.path.join(BASE_DIR, 'monitor.log'), 'w')
        subprocess.Popen(['python', chef_script], env=env, stdout=log_file, stderr=subprocess.STDOUT)
    return redirect(url_for('dashboard'))

@app.route('/stop')
def stop():
    pid = get_monitor_pid()
    if pid:
        try: psutil.Process(pid).terminate()
        except: pass
    return redirect(url_for('dashboard'))

@app.route('/resolve_kill/<worker_id>/<action>')
def resolve_kill(worker_id, action):
    if os.path.exists(PENDING_KILLS_FILE):
        try:
            with open(PENDING_KILLS_FILE, 'r') as f: pending = json.load(f)
            if worker_id in pending:
                pending[worker_id] = action
                with open(PENDING_KILLS_FILE, 'w') as f: json.dump(pending, f)
        except: pass
    return redirect(url_for('dashboard'))

@app.route('/api/chat', methods=['POST'])
def api_chat():
    user_msg = request.json.get('message', '')
    conf = load_config()
    api_key = conf.get('NVIDIA_API_KEY_1') or conf.get('NVIDIA_API_KEY_2')

    if not api_key:
        return jsonify({'reply': 'Error: No NVIDIA API Key configured. Please set one in the Configuration tab.'})

    state_str = "{}"
    if os.path.exists(SYSTEM_STATE_FILE):
        with open(SYSTEM_STATE_FILE, 'r') as f: state_str = f.read()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"You are the Monitor AI overseeing an autonomous workforce dedicated entirely to earning ETH. Here is the current system state:\n{state_str}\n\nUser says: {user_msg}"

    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        reply = response.json()['choices'][0]['message']['content']
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'reply': f'API Error: {str(e)}'})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
