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

def run_network_security_scan():
    """Detects active external connections and flags potentially suspicious public IP connections."""
    results = []
    suspicious_count = 0
    external_count = 0
    
    try:
        # Use ss to get established TCP connections
        out = subprocess.run(['ss', '-tnp', 'state', 'established'], capture_output=True, text=True)
        lines = out.stdout.split('\n')[1:] # Skip header
        
        for line in lines:
            if not line.strip(): continue
            parts = line.split()
            if len(parts) >= 5:
                peer_addr = parts[4]
                
                # Extract IP from peer (strip port)
                ip = peer_addr.rsplit(':', 1)[0].replace('[', '').replace(']', '')
                
                # Check if it's local
                if any(ip.startswith(prefix) for prefix in ['127.', '192.168.', '10.', '0.', '::1']):
                    continue
                if ip.startswith('172.'):
                    try:
                        if 16 <= int(ip.split('.')[1]) <= 31: continue
                    except: pass
                
                # External connection found
                external_count += 1
                status = "INFO"
                suggestion = f"Active connection to {ip}"
                
                # Basic heuristic for suspicious port
                port = peer_addr.rsplit(':', 1)[1] if ':' in peer_addr else ''
                if port not in ['443', '80', '22', '53', '123']:
                    status = "WARNING"
                    suggestion = f"Non-standard active connection port ({port}) to {ip}. Verify process."
                    suspicious_count += 1
                
                proc = parts[5] if len(parts) > 5 else "Unknown"
                
                results.append({
                    "check": "External Connection",
                    "target": peer_addr,
                    "status": status,
                    "suggestion": suggestion + f" [{proc}]",
                    "fix_command": f"echo 'Review connection. Kill if bad.'"
                })
    except Exception as e:
        results.append({
            "check": "Network Scan Tool",
            "target": "ss command",
            "status": "FAIL",
            "suggestion": "Could not execute network scan tools. (" + str(e) + ")",
            "fix_command": ""
        })

    if external_count == 0:
        results.append({
            "check": "External Connections",
            "target": "Network",
            "status": "PASS",
            "suggestion": "No active external connections found.",
            "fix_command": ""
        })

    return results

