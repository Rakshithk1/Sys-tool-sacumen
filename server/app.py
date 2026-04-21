from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from monitor import MonitorEngine
import os
import psutil
import subprocess
import utils
import paramiko
import json
from security_utils import run_malware_scan, run_security_audit, run_network_security_scan
import windows_utils

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

# --- OS Info & Cross-Platform Endpoints ---

@app.route('/api/os_info', methods=['GET'])
def os_info():
    return jsonify(windows_utils.get_os_info())

@app.route('/api/windows/metrics', methods=['GET'])
def win_metrics():
    return jsonify(windows_utils.get_windows_metrics())

@app.route('/api/windows/processes', methods=['GET'])
def win_processes():
    return jsonify(windows_utils.get_windows_processes())

@app.route('/api/windows/services', methods=['GET'])
def win_services():
    return jsonify(windows_utils.get_windows_services())

@app.route('/api/windows/network', methods=['GET'])
def win_network():
    return jsonify(windows_utils.get_windows_network())

@app.route('/api/windows/cleanup_temp', methods=['POST'])
def win_cleanup():
    return jsonify(windows_utils.cleanup_windows_temp())

@app.route('/api/windows/unified_sysinfo', methods=['GET'])
def win_unified_sysinfo():
    return jsonify(windows_utils.get_unified_sysinfo())

# --- Linux SSH & File Transfer Endpoints ---

@app.route('/api/linux/ssh_status', methods=['GET'])
def linux_ssh_status():
    try:
        # Check if anything is listening on port 22
        output = subprocess.check_output("ss -tulnp | grep :22", shell=True, text=True)
        return jsonify({"active": True, "output": output.strip()})
    except subprocess.CalledProcessError:
        return jsonify({"active": False, "message": "SSH port 22 is not active."})

@app.route('/api/linux/ssh_enable', methods=['POST'])
def linux_ssh_enable():
    try:
        subprocess.run("sudo systemctl start ssh", shell=True, check=True)
        subprocess.run("sudo systemctl enable ssh", shell=True, check=True)
        return jsonify({"success": True, "message": "SSH service started and enabled."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/linux/transfer', methods=['POST'])
def linux_transfer():
    data = request.json
    mode = data.get('mode') # 'send' or 'receive'
    use_rsync = data.get('rsync', False)
    
    file_path = data.get('filePath')
    remote_user = data.get('user')
    remote_ip = data.get('ip')
    dest_path = data.get('destPath')
    
    if not all([file_path, remote_user, remote_ip, dest_path]):
        return jsonify({"error": "Missing transfer parameters"}), 400

    # Build command
    # Note: For production, we'd use Paramiko or handle password prompts via PTY.
    # For now, we assume public key auth or simple background execution for the exercise.
    base_cmd = "rsync -avz" if use_rsync else "scp -r"
    
    if mode == 'send':
        cmd = f"{base_cmd} {file_path} {remote_user}@{remote_ip}:{dest_path}"
    else: # receive
        cmd = f"{base_cmd} {remote_user}@{remote_ip}:{file_path} {dest_path}"

    try:
        # In a real app, this should be async or stream output. 
        # Here we run it and return the result.
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return jsonify({
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cmd": cmd
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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
    return jsonify(utils.optimize_network())

@app.route('/api/system/optimize', methods=['POST'])
def sys_optimize():
    return jsonify(utils.optimize_system())

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
@app.route('/api/ssh/test', methods=['POST'])
def ssh_test():
    data = request.json
    host = data.get('host')
    user = data.get('user')
    password = data.get('password')
    
    if not all([host, user, password]):
        return jsonify({"success": False, "error": "Missing credentials", "message": "Incomplete configuration"}), 400
        
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=password, timeout=5)
        ssh.close()
        return jsonify({"success": True, "message": "Connection established successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "message": "Authentication failed"}), 500


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

@app.route('/api/security/network_scan', methods=['GET'])
def network_security_scan():
    return jsonify(run_network_security_scan())


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
