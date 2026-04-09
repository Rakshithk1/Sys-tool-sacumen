import requests
import json
import subprocess
import re
import shutil

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"

FIX_COMMAND_MAP = {
    "Restart network manager": "sudo systemctl restart NetworkManager",
    "Flush DNS cache": "resolvectl flush-caches",
    "Restart SSH service": "sudo systemctl restart ssh",
    "Clean /tmp directory": "sudo rm -rf /tmp/*",
    "Release/Renew DHCP": "sudo dhclient -r && sudo dhclient",
    "Restart UFW firewall": "sudo ufw reload",
    "Check high CPU processes": "ps aux --sort=-%cpu | head -n 6",
    "Verify Disk Health": "df -h",
    "Check System Logs": "journalctl -n 20",
    "Reload Systemd": "sudo systemctl daemon-reload",
    "Flush APT cache": "sudo apt-get clean"
}

def get_ollama_status():
    """Detects Ollama installation, running status, and models."""
    status = {
        "installed": False,
        "running": False,
        "models": [],
        "version": None,
        "error": None
    }
    
    # 1. Check if installed
    ollama_path = shutil.which("ollama")
    if ollama_path:
        status["installed"] = True
        try:
            ver_output = subprocess.check_output(["ollama", "--version"], text=True)
            status["version"] = ver_output.strip()
        except:
            pass
    
    # 2. Check if running and get models
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=3)
        if response.status_code == 200:
            status["running"] = True
            data = response.json()
            status["models"] = [m["name"] for m in data.get("models", [])]
    except requests.exceptions.ConnectionError:
        status["running"] = False
    except Exception as e:
        status["error"] = str(e)
        
    return status

def pull_ollama_model(model_name="mistral:latest"):
    """Starts a process to pull the requested model."""
    try:
        # Use -n to run non-interactively if possible, or just subprocess.run
        # Note: Pulling can take minutes.
        result = subprocess.run(["ollama", "pull", model_name], capture_output=True, text=True)
        return {
            "success": result.returncode == 0,
            "output": result.stdout if result.returncode == 0 else result.stderr
        }
    except Exception as e:
        return {"success": False, "output": str(e)}

def analyze_issue_with_ai(user_input, model="mistral:latest"):
    prompt = f"""You are a Linux system troubleshooting assistant.

Convert the user issue into STRICT JSON format with:
- issue (string)
- causes (array of strings)
- fixes (array of short fix titles)

Rules:
- Do NOT include explanations outside JSON
- Do NOT include shell commands
- Keep fixes short and actionable
- Be accurate for Linux/Ubuntu systems
- Map fixes to professional titles like:
  "Restart network manager", "Flush DNS cache", "Restart SSH service", "Clean /tmp directory", "Check high CPU processes"

User issue: {user_input}"""

    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(OLLAMA_GENERATE_URL, json=payload, timeout=45)
        response.raise_for_status()
        
        raw_text = response.json().get('response', '')
        
        # Extract JSON if LLM added markdown or fluff
        json_match = re.search(r'({.*})', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        else:
            return {
                "issue": "Structure Error",
                "causes": ["AI returned unstructured data"],
                "fixes": []
            }
            
    except Exception as e:
        return {"error": str(e)}

def run_ai_fix(fix_title):
    command = FIX_COMMAND_MAP.get(fix_title)
    if not command:
        return {"success": False, "output": f"No command mapping found for: {fix_title}"}
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return {
            "success": result.returncode == 0,
            "output": result.stdout if result.returncode == 0 else result.stderr
        }
    except Exception as e:
        return {"success": False, "output": str(e)}
