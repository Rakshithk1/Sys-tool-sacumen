import os
import psutil
import socket
import subprocess
import time
import datetime

def get_system_uptime():
    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)
    
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    
    formatted = f"{hours} hrs, {minutes} min, {seconds} sec"
    return {"formatted": formatted, "seconds": uptime_seconds}

def get_top_processes(sort_by='cpu', n=5):
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
        try:
            info = proc.info
            # Suggestion logic
            suggestion = ""
            cmd = f"pkill -15 -p {info['pid']}"
            if sort_by == 'cpu' and info['cpu_percent'] > 50:
                suggestion = "High CPU! Consider termination if not critical."
                cmd = f"kill -9 {info['pid']}"
            elif sort_by == 'memory' and info['memory_percent'] > 20:
                suggestion = "High RAM usage! Check for memory leaks."
            
            info['suggestion'] = suggestion
            info['cmd'] = cmd
            processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    key = 'cpu_percent' if sort_by == 'cpu' else 'memory_percent'
    processes.sort(key=lambda x: x[key], reverse=True)
    return processes[:n]

def get_hardware_details():
    try:
        cpu_info = subprocess.check_output(['lscpu'], universal_newlines=True)
        # Extract specific lines for cleaner output
        cpu_summary = {}
        for line in cpu_info.split('\n'):
            if "Model name" in line: cpu_summary['model'] = line.split(':')[1].strip()
            if "CPU(s):" in line and "On-line" not in line: cpu_summary['cores'] = line.split(':')[1].strip()
            if "Architecture" in line: cpu_summary['arch'] = line.split(':')[1].strip()
        
        # Memory Info
        mem = psutil.virtual_memory()
        
        # Disk Info (Block devices)
        lsblk = subprocess.check_output(['lsblk', '-o', 'NAME,SIZE,TYPE,MODEL'], universal_newlines=True)
        
        return {
            "cpu": cpu_summary,
            "total_ram": f"{mem.total / (1024**3):.2f} GB",
            "lsblk": lsblk,
            "bios": subprocess.check_output(['cat', '/sys/class/dmi/id/bios_version'], stderr=subprocess.STDOUT, universal_newlines=True).strip() if os.path.exists('/sys/class/dmi/id/bios_version') else "N/A"
        }
    except Exception as e:
        return {"error": str(e)}

def get_extended_sys_info():
    import platform
    import getpass
    
    try:
        lsb = subprocess.check_output(['lsb_release', '-d'], text=True).split(':')[1].strip()
    except:
        lsb = platform.freedesktop_os_release().get('PRETTY_NAME', 'Linux')

    return {
        "os": platform.system(),
        "distro": lsb,
        "kernel": platform.release(),
        "arch": platform.machine(),
        "user": getpass.getuser(),
        "hostname": socket.gethostname(),
        "uptime": get_system_uptime()['formatted'],
        "python_v": platform.python_version()
    }

def get_firewall_status():
    try:
        # Attempt to get status - prioritizing non-interactive patterns
        output = subprocess.check_output(['sudo', '-n', 'ufw', 'status'], stderr=subprocess.STDOUT, text=True)
        return output.strip()
    except subprocess.CalledProcessError as e:
        if "password is required" in e.output.lower():
            return "CRITICAL: Sudo password required for Firewall audit.\n\nTo fix this:\n1. Run: 'sudo visudo'\n2. Add: '%sudo ALL=(ALL) NOPASSWD: /usr/sbin/ufw'\n3. Or run the dashboard with elevated privileges."
        return f"Firewall Audit Failed: {e.output.strip()}"
    except Exception as e:
        return f"Access Denied: Unable to fetch firewall status. ({str(e)})"

def get_running_services():
    try:
        # 'ss -tuln' works without root for basic port listing.
        # We omit '-p' (Process ID) by default to ensure it never hangs on sudo.
        output = subprocess.check_output(['ss', '-tuln'], stderr=subprocess.STDOUT, text=True)
        return output.strip()
    except Exception as e:
        return "Network audit utility (ss) is currently inaccessible on this host context."

def get_log_summary():
    try:
        # Get last 20 lines of syslog
        output = subprocess.check_output(['tail', '-n', '20', '/var/log/syslog'], text=True)
        return output.strip()
    except:
        try:
            # Fallback to journalctl
            output = subprocess.check_output(['journalctl', '-n', '20'], text=True)
            return output.strip()
        except:
            return "Unable to access system logs."

def restart_network():
    try:
        # Attempt to restart networking service
        subprocess.run(['sudo', '-n', 'systemctl', 'restart', 'networking'], check=True)
        return "Networking restart command issued successfully."
    except:
        try:
            subprocess.run(['sudo', '-n', 'systemctl', 'restart', 'NetworkManager'], check=True)
            return "NetworkManager restart command issued successfully."
        except Exception as e:
            return f"Failed to restart network: {str(e)}"

def hard_restart_network():
    """Forcefully restarts the NetworkManager service."""
    try:
        subprocess.run(['sudo', '-n', 'systemctl', 'restart', 'NetworkManager'], check=True, capture_output=True, text=True)
        return True, "NetworkManager successfully restarted."
    except subprocess.CalledProcessError as e:
        return False, f"Failed: {e.stderr or e.output or 'Permission Denied'}"

def safe_network_fix():
    """Soft-resets the networking stack using nmcli."""
    try:
        subprocess.run(['sudo', '-n', 'nmcli', 'networking', 'off'], check=True)
        time.sleep(1)
        subprocess.run(['sudo', '-n', 'nmcli', 'networking', 'on'], check=True)
        return True, "Networking stack successfully re-initialized."
    except Exception as e:
        return False, f"Fix failed: {str(e)}"

def optimize_network():
    """Flushes DNS and applies best-practice TCP optimizations."""
    actions = []
    
    # 1. Flush DNS Cache (often doesn't need root in modern systemd)
    try:
        subprocess.run(['resolvectl', 'flush-caches'], check=True, capture_output=True)
        actions.append("DNS cache cleared")
    except:
        try:
            subprocess.run(['systemd-resolve', '--flush-caches'], check=True, capture_output=True)
            actions.append("DNS cache cleared")
        except:
            pass

    # 2. Rescan WiFi
    try:
        subprocess.run(['nmcli', 'dev', 'wifi', 'rescan'], check=True, capture_output=True)
        actions.append("Wireless networks rescanned")
    except:
        pass
        
    if not actions:
        actions.append("No network optimizations could be applied automatically.")

    return {
        "type": "network",
        "actions": actions,
        "status": "success"
    }

def optimize_system():
    """Perform safe system cleaning commands to optimize performance."""
    actions = []
    
    # 1. User Application Cache
    try:
        cache_path = os.path.expanduser('~/.cache')
        if os.path.exists(cache_path):
            subprocess.run(['find', cache_path, '-type', 'f', '-atime', '+7', '-delete'], check=True, capture_output=True)
            actions.append("Stale application caches cleared")
    except:
        pass
        
    # 2. Sync Disks
    try:
        subprocess.run(['sync'], check=True, capture_output=True)
        actions.append("Filesystem buffers synchronized")
    except:
        pass
        
    # 3. Clean user-owned temporary files older than 1 day
    try:
        username = os.environ.get('USER', 'root')
        subprocess.run(['find', '/tmp', '-user', username, '-type', 'f', '-atime', '+1', '-delete'], check=True, capture_output=True)
        actions.append("Inactive temporary files removed")
    except:
        pass
        
    if not actions:
        actions.append("No system optimizations could be applied automatically.")

    return {
        "type": "system",
        "actions": actions,
        "status": "success"
    }

def get_largest_files(path, n=5):
    if not os.path.exists(path):
        return []
    
    files_list = []
    try:
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if not os.path.islink(file_path):
                        files_list.append((file_path, os.path.getsize(file_path)))
                except OSError:
                    continue
    except Exception:
        pass

    files_list.sort(key=lambda x: x[1], reverse=True)
    
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

    return [{"path": f, "size": format_size(s)} for f, s in files_list[:n]]

def file_search(path, filename):
    if not os.path.exists(path):
        return []
    
    results = []
    try:
        filename_lower = filename.lower()
        for root, dirs, files in os.walk(path):
            for file in files:
                if filename_lower in file.lower():
                    results.append(os.path.join(root, file))
                    if len(results) >= 20: # Limit result count
                        return results
    except Exception:
        pass
    return results

def content_search(path, keyword):
    """
    Searches for a keyword inside files at the given path using grep with a Python fallback.
    """
    if not os.path.exists(path):
        return {"results": [], "warning": "Path does not exist."}
    
    results = []
    has_permission_errors = False
    
    # 1. Primary approach: grep (fast)
    try:
        # -r: recursive, -l: filenames only, -I: ignore binary, -s: silent (no permission errors)
        cmd = [
            'grep', '-r', '-l', '-I', '-s',
            '--exclude-dir=.git', 
            '--exclude-dir=node_modules', 
            '--exclude-dir=__pycache__', 
            '--exclude-dir=venv',
            '--', keyword, path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        # We accept results even if returncode is 2 (partial failure/permission denied)
        stdout_results = result.stdout.strip().split('\n')
        results = [line for line in stdout_results if line]
        
        if result.returncode == 2 or "Permission denied" in result.stderr:
            has_permission_errors = True
            
    except Exception as e:
        # 2. Fallback: Simple Python search (slower but robust)
        try:
            for root, dirs, files in os.walk(path):
                # Skip hidden/blacklisted dirs manually
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', 'venv']]
                for file in files:
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, 'r', errors='ignore') as f:
                            if keyword in f.read():
                                results.append(full_path)
                                if len(results) >= 20: break
                    except:
                        has_permission_errors = True
                    if len(results) >= 20: break
                if len(results) >= 20: break
        except:
            pass

    return {
        "results": results[:20],
        "warning": "Some directories were inaccessible due to permissions." if has_permission_errors else None
    }

def ping_test(host):
    try:
        # Use -c 4 for 4 pings on Linux
        output = subprocess.check_output(['ping', '-c', '4', host], stderr=subprocess.STDOUT, universal_newlines=True)
        return output
    except subprocess.CalledProcessError as e:
        return e.output

def port_check(host, port):
    try:
        with socket.create_connection((host, port), timeout=2):
            return "OPEN"
    except (socket.timeout, ConnectionRefusedError, socket.error):
        return "CLOSED"

def get_network_details():
    # ... previous logic ...
    interfaces = []
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET: # IPv4
                interfaces.append({
                    "name": interface,
                    "ip": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast
                })
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    return {
        "hostname": hostname,
        "local_ip": local_ip,
        "interfaces": interfaces
    }

def get_installed_apps():
    apps = []
    base_dirs = ["/usr/share/applications", os.path.expanduser("~/.local/share/applications")]
    
    visited_ids = set()
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            continue
        
        for entry in os.listdir(base_dir):
            if entry.endswith(".desktop") and entry not in visited_ids:
                path = os.path.join(base_dir, entry)
                try:
                    name, exec_cmd = "", ""
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if line.startswith("Name="):
                                name = line.split("=")[1].strip()
                            if line.startswith("Exec="):
                                # Extract path, ignoring arguments like %U, %f
                                exec_parts = line.split("=")[1].strip().split(" ")
                                exec_cmd = exec_parts[0].strip('"').strip("'")
                            if name and exec_cmd:
                                break
                    if name:
                        apps.append({"name": name, "exec": exec_cmd, "id": entry, "type": "app"})
                        visited_ids.add(entry)
                except:
                    continue
    return sorted(apps, key=lambda x: x["name"])

def get_systemd_services():
    try:
        output = subprocess.check_output(['systemctl', 'list-unit-files', '--type=service', '--no-legend'], text=True)
        services = []
        for line in output.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    state = parts[1]
                    services.append({"name": name, "state": state, "type": "service"})
        return sorted(services, key=lambda x: x["name"])
    except:
        return []

def run_session_resource(resource):
    """Attempt to start/open a session resource."""
    res_type = resource.get("type")
    target = resource.get("exec") or resource.get("name")
    
    try:
        if res_type == "app":
            # Start app in background, detached
            subprocess.Popen([target], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, f"Started application: {resource['name']}"
        elif res_type == "service":
            subprocess.run(['sudo', 'systemctl', 'start', target], check=True)
            return True, f"Started service: {target}"
        elif res_type == "port":
            # For ports, we just confirm if they are open/active? 
            # Usually 'Restore' for ports doesn't make sense unless it's a specific binary.
            return True, f"Port {target} monitored."
    except Exception as e:
        return False, str(e)
    return False, "Unknown resource type"
