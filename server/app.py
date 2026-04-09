from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from monitor import MonitorEngine
import os
import psutil
import subprocess
import utils
import paramiko
import json
from security_utils import run_malware_scan, run_security_audit

app = Flask(__name__, static_folder='../client')
CORS(app)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOGS_PATH = os.path.join(BASE_DIR, "logs.json")
SESSION_PATH = os.path.join(BASE_DIR, "session_profile.json")

# Initialize Engine
engine = MonitorEngine(CONFIG_PATH, LOGS_PATH)

@app.route('/')
def serve_index():
    return send_from_directory('../client', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../client', path)

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "status": engine.current_status,
        "is_running": engine.running
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify(engine.logs)

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(engine.config)

@app.route('/api/config', methods=['POST'])
def update_config():
    new_config = request.json
    engine.save_config(new_config)
    return jsonify({"message": "Config updated successfully"})

@app.route('/api/start', methods=['POST'])
def start_monitor():
    engine.start()
    return jsonify({"message": "Monitoring started"})

@app.route('/api/stop', methods=['POST'])
def stop_monitor():
    engine.stop()
    return jsonify({"message": "Monitoring stopped"})

# --- New Tools Endpoints ---

@app.route('/api/sys_health', methods=['GET'])
def get_sys_health():
    health = {
        "cpu": psutil.cpu_percent(interval=None),
        "ram": {
            "percent": psutil.virtual_memory().percent,
            "used": f"{psutil.virtual_memory().used / (1024**3):.2f} GB",
            "total": f"{psutil.virtual_memory().total / (1024**3):.2f} GB"
        },
        "disk": {
            "percent": psutil.disk_usage('/').percent,
            "used": f"{psutil.disk_usage('/').used / (1024**3):.2f} GB",
            "total": f"{psutil.disk_usage('/').total / (1024**3):.2f} GB"
        },
        "uptime": utils.get_system_uptime()
    }
    return jsonify(health)

@app.route('/api/top_processes', methods=['GET'])
def get_processes():
    sort_by = request.args.get('sort', 'cpu')
    return jsonify(utils.get_top_processes(sort_by=sort_by))

@app.route('/api/hardware', methods=['GET'])
def get_hardware():
    return jsonify(utils.get_hardware_details())

@app.route('/api/extended_sys', methods=['GET'])
def get_extended_sys():
    return jsonify(utils.get_extended_sys_info())

@app.route('/api/largest_files', methods=['POST'])
def get_files():
    data = request.json
    path = data.get('path', '/')
    return jsonify(utils.get_largest_files(path))

@app.route('/api/file_search', methods=['POST'])
def search_files():
    data = request.json
    return jsonify(utils.file_search(data.get('path', '/'), data.get('filename', '')))

@app.route('/api/content_search', methods=['POST'])
def search_content():
    data = request.json
    return jsonify(utils.content_search(data.get('path', '/'), data.get('keyword', '')))

@app.route('/api/speedtest', methods=['GET'])
def run_speedtest():
    try:
        # Running speedtest-cli in simple mode
        output = subprocess.check_output(['speedtest-cli', '--simple'], stderr=subprocess.STDOUT, text=True)
        return jsonify({"output": output})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Speed Test Failed: {e.output.strip()}"}), 500
    except FileNotFoundError:
        return jsonify({"error": "Dependency Missing: 'speedtest-cli' is not installed on the Linux host. Please run 'sudo apt install speedtest-cli'."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ping', methods=['POST'])
def run_ping():
    data = request.json
    return jsonify({"output": utils.ping_test(data.get('host', 'google.com'))})

@app.route('/api/port_check', methods=['POST'])
def check_port():
    data = request.json
    status = utils.port_check(data.get('host', 'localhost'), int(data.get('port', 80)))
    return jsonify({"status": status})

@app.route('/api/network_details', methods=['GET'])
def get_net_details():
    return jsonify(utils.get_network_details())

@app.route('/api/network/hard_restart', methods=['POST'])
def net_hard_restart():
    success, msg = utils.hard_restart_network()
    return jsonify({"success": success, "message": msg}), 200 if success else 500

@app.route('/api/network/safe_fix', methods=['POST'])
def net_safe_fix():
    success, msg = utils.safe_network_fix()
    return jsonify({"success": success, "message": msg}), 200 if success else 500

@app.route('/api/network/optimize', methods=['POST'])
def net_optimize():
    success, msg = utils.optimize_network()
    return jsonify({"success": success, "message": msg}), 200 if success else 500

@app.route('/api/tools/firewall', methods=['GET'])
def get_firewall():
    return jsonify({"output": utils.get_firewall_status()})

@app.route('/api/tools/services', methods=['GET'])
def get_services():
    return jsonify({"output": utils.get_running_services()})

@app.route('/api/tools/logs', methods=['GET'])
def get_logs_summary():
    return jsonify({"output": utils.get_log_summary()})

@app.route('/api/tools/network_restart', methods=['POST'])
def net_restart():
    return jsonify({"message": utils.restart_network()})

@app.route('/api/ssh/exec', methods=['POST'])
def ssh_exec():
    data = request.json
    host = data.get('host')
    user = data.get('user')
    password = data.get('password')
    command = data.get('command')
    
    if not all([host, user, password, command]):
        return jsonify({"error": "Missing credentials or command"}), 400
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=password, timeout=5)
        
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        ssh.close()
        return jsonify({"output": output, "error": error})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/security/scan', methods=['POST'])
def security_scan():
    data = request.json
    path = data.get('path', '/home')
    return jsonify(run_malware_scan(path))

@app.route('/api/security/audit', methods=['GET'])
def security_audit():
    return jsonify(run_security_audit())

@app.route('/api/security/fix', methods=['POST'])
def security_fix():
    data = request.json
    command = data.get('command')
    if not command:
        return jsonify({"error": "No command provided"}), 400
    
    try:
        # Run the command using sudo -n to fail fast if password is required
        # and shell=True to support chained commands like '&&'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({"message": "Fix applied successfully", "output": result.stdout})
        else:
            error_msg = result.stderr or result.stdout or "Command failed"
            if "password is required" in error_msg.lower():
                return jsonify({
                    "error": "Sudo Permission Required",
                    "suggestion": "This fix requires sudo. Please configure NOPASSWD for this command in /etc/sudoers.",
                    "details": error_msg
                }), 403
            return jsonify({"error": error_msg, "details": result.stdout}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Session Restoration Endpoints ---

@app.route('/api/session/inventory', methods=['GET'])
def get_session_inventory():
    return jsonify({
        "apps": utils.get_installed_apps(),
        "services": utils.get_systemd_services()
    })

@app.route('/api/session/save', methods=['POST'])
def save_session():
    data = request.json
    with open(SESSION_PATH, 'w') as f:
        json.dump(data, f)
    return jsonify({"message": "Session profile saved"})

@app.route('/api/session/load', methods=['GET'])
def load_session():
    if os.path.exists(SESSION_PATH):
        try:
            with open(SESSION_PATH, 'r') as f:
                return jsonify(json.load(f))
        except:
            pass
    return jsonify({"apps": [], "services": [], "ports": []})

@app.route('/api/session/restore', methods=['POST'])
def restore_session():
    if not os.path.exists(SESSION_PATH):
        return jsonify({"message": "No session profile found"}), 404
    
    try:
        with open(SESSION_PATH, 'r') as f:
            config = json.load(f)
    except:
        return jsonify({"message": "Invalid session profile"}), 500
    
    results = []
    # Start apps
    for app in config.get('apps', []):
        success, msg = utils.run_session_resource(app)
        results.append({"name": app['name'], "success": success, "message": msg})
    
    # Start services
    for svc in config.get('services', []):
        success, msg = utils.run_session_resource(svc)
        results.append({"name": svc['name'], "success": success, "message": msg})
        
    return jsonify({"results": results})

from ai_utils import analyze_issue_with_ai, run_ai_fix, get_ollama_status, pull_ollama_model

# --- AI Troubleshooter Endpoints ---

@app.route('/api/ai/status', methods=['GET'])
def ai_status():
    return jsonify(get_ollama_status())

@app.route('/api/ai/setup', methods=['POST'])
def ai_setup():
    data = request.json
    model = data.get('model', 'mistral:latest')
    result = pull_ollama_model(model)
    return jsonify(result)

@app.route('/api/ai/analyze', methods=['POST'])
def ai_analyze():
    data = request.json
    user_input = data.get('issue')
    model = data.get('model', 'mistral:latest')
    
    if not user_input:
        return jsonify({"error": "No description provided"}), 400
    
    result = analyze_issue_with_ai(user_input, model)
    return jsonify(result)

if __name__ == '__main__':
    # Listen on 0.0.0.0 to enable access from Windows host
    app.run(host='0.0.0.0', debug=True, port=5000)
