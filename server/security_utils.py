import subprocess
import os
import re

def run_malware_scan(path):
    """
    Runs clamscan on the specified path and returns a list of infected files.
    """
    if not os.path.exists(path):
        return {"error": f"Path '{path}' does not exist.", "infected": []}

    try:
        # -r: recursive, -i: only infected, --no-summary: cleaner output
        # Using sudo -n to avoid hanging if password is required
        result = subprocess.run(
            ['sudo', '-n', 'clamscan', '-r', '-i', '--no-summary', path],
            capture_output=True,
            text=True
        )
        
        # If exit code 0 (no viruses) or 1 (viruses found)
        if result.returncode in [0, 1]:
            lines = result.stdout.strip().split('\n')
            infected = []
            for line in lines:
                if line and ': ' in line:
                    file_parts = line.split(': ')
                    if len(file_parts) >= 2:
                        file_path = file_parts[0]
                        virus = file_parts[1]
                        infected.append({
                            "file": file_path,
                            "virus": virus,
                            "suggestion": f"Recommended action: rm {file_path}"
                        })
            
            return {
                "path": path,
                "infected": infected,
                "count": len(infected),
                "status": "Clean" if len(infected) == 0 else "Infected"
            }
        else:
            error_msg = result.stderr or "Scan failed"
            if "password is required" in error_msg.lower():
                return {"error": "Permission Denied: ClamAV requires sudo. Please configure NOPASSWD for clamscan.", "infected": []}
            return {"error": error_msg, "infected": []}

    except FileNotFoundError:
        return {"error": "ClamAV not installed. Run 'sudo apt install clamav' to enable malware scanning.", "infected": []}
    except Exception as e:
        return {"error": str(e), "infected": []}

def run_security_audit():
    """
    Performs basic security audits on the Linux host.
    """
    results = []
    
    # 1. Check for world-writable sensitive files
    sensitive_files = ['/etc/passwd', '/etc/shadow', '/etc/group', '/etc/sudoers']
    for f in sensitive_files:
        if os.path.exists(f):
            mode = os.stat(f).st_mode
            if mode & 0o002: # check world-writable bit
                results.append({
                    "check": "World-Writable Secret",
                    "target": f,
                    "status": "FAIL",
                    "suggestion": "This sensitive system file is world-writable, which is unsafe.",
                    "fix_command": f"sudo -n chmod o-w {f}"
                })
            else:
                results.append({
                    "check": "File Permissions",
                    "target": f,
                    "status": "PASS",
                    "suggestion": "File permissions are correctly restricted.",
                    "fix_command": ""
                })

    # 2. Check for root login patterns in 'last' command (basic check)
    try:
        last_out = subprocess.check_output(['last', '-n', '5', 'root'], text=True)
        results.append({
            "check": "Recent Root Logins",
            "target": "Auth Logs",
            "status": "INFO",
            "suggestion": "Review recent root log-ins for unauthorized access.",
            "details": last_out.strip(),
            "fix_command": "last root"
        })
    except: pass

    # 3. Check for open SSH port if not intended (simplistic)
    try:
        netstat = subprocess.check_output(['ss', '-tuln'], text=True)
        if ':22 ' in netstat:
             results.append({
                "check": "SSH Service",
                "target": "Port 22",
                "status": "WARNING",
                "suggestion": "SSH is active; consider stopping and disabling it if not in use.",
                "fix_command": "sudo -n systemctl stop ssh && sudo -n systemctl disable ssh"
            })
    except: pass

    return results
