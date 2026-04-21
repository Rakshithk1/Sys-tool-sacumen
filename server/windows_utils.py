"""
windows_utils.py
Utilities for Windows-specific system information.
Executed via powershell.exe through WSL interop.
"""
import subprocess
import os
import platform
import psutil

def _run_ps(cmd):
    """Execute a PowerShell command through WSL interop and return output."""
    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', cmd],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip(), result.returncode == 0
    except FileNotFoundError:
        return None, False  # powershell.exe not accessible
    except Exception as e:
        return str(e), False


def get_os_info():
    """Returns OS info from the server perspective, and also detects if Windows is reachable via WSL interop."""
    server_os = platform.system().lower()  # 'linux' in WSL, 'windows' if native
    
    windows_available = False
    win_version = None
    
    # Try to reach powershell.exe (only works if running in WSL)
    out, ok = _run_ps("[System.Environment]::OSVersion.VersionString")
    if ok and out:
        windows_available = True
        win_version = out

    return {
        "server_os": server_os,
        "windows_available": windows_available,
        "windows_version": win_version,
        "platform": platform.platform(),
        "hostname": platform.node(),
        "arch": platform.machine()
    }


def get_windows_processes(top_n=15):
    """Get top running Windows processes via tasklist."""
    out, ok = _run_ps(
        "Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 | "
        "Select-Object Name, Id, CPU, WorkingSet | ConvertTo-Json"
    )
    if not ok or not out:
        return {"error": "Cannot retrieve Windows processes. PowerShell interop unavailable."}
    
    import json
    try:
        procs = json.loads(out)
        if isinstance(procs, dict):
            procs = [procs]
        return {
            "processes": [
                {
                    "name": p.get("Name", ""),
                    "pid": p.get("Id", 0),
                    "cpu": round(p.get("CPU", 0) or 0, 2),
                    "memory_mb": round((p.get("WorkingSet", 0) or 0) / 1024 / 1024, 1)
                }
                for p in procs
            ]
        }
    except Exception as e:
        return {"error": f"Parse error: {e}", "raw": out}


def get_windows_services(filter_running=True):
    """Get Windows services status."""
    status_filter = "Running" if filter_running else "*"
    out, ok = _run_ps(
        f"Get-Service | Where-Object {{$_.Status -eq '{status_filter}' -or '{status_filter}' -eq '*'}} | "
        "Select-Object Name, DisplayName, Status | ConvertTo-Json"
    )
    if not ok or not out:
        return {"error": "Cannot retrieve Windows services."}
    
    import json
    try:
        services = json.loads(out)
        if isinstance(services, dict):
            services = [services]
        return {
            "services": [
                {
                    "name": s.get("Name", ""),
                    "display": s.get("DisplayName", ""),
                    "status": str(s.get("Status", ""))
                }
                for s in services
            ]
        }
    except Exception as e:
        return {"error": f"Parse error: {e}", "raw": out}


def get_windows_network():
    """Get Windows network info via ipconfig."""
    out, ok = _run_ps("ipconfig /all")
    if not ok or not out:
        return {"error": "Cannot retrieve Windows network info."}
    return {"raw": out}


def cleanup_windows_temp():
    """Clean Windows temp files."""
    actions = []
    
    # Delete user temp files
    out, ok = _run_ps(
        "Remove-Item -Path $env:TEMP\\* -Force -Recurse -ErrorAction SilentlyContinue; "
        "Write-Output 'User temp files cleared.'"
    )
    if ok:
        actions.append("User %TEMP% folder cleared")
    
    # Clear recycle bin
    out2, ok2 = _run_ps(
        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue; "
        "Write-Output 'Recycle Bin emptied.'"
    )
    if ok2:
        actions.append("Recycle Bin emptied")
    
    if not actions:
        actions.append("No cleanup performed — PowerShell interop unavailable.")
    
    return {"actions": actions, "success": len(actions) > 0}


def get_unified_sysinfo():
    """Returns a comprehensive set of Windows system information."""
    data = {"hardware": {}, "os": {}, "network": {}, "status": {}}

    # 1. Hardware Info
    hw_cmd = (
        "Get-WmiObject Win32_Processor | Select-Object -First 1 | Select-Object Name, NumberOfCores, MaxClockSpeed; "
        "Get-WmiObject Win32_ComputerSystem | Select-Object TotalPhysicalMemory; "
        "Get-WmiObject Win32_VideoController | Select-Object Name | ConvertTo-Json"
    )
    hw_out, hw_ok = _run_ps(hw_cmd)
    if hw_ok:
        try:
            # Simple manual parsing since PowerShell combined output might be tricky for direct JSON
            # However, for robustness, we'll try to refine the PS command if needed.
            # Let's use individual calls instead for cleaner data.
            pass
        except: pass

    # Refined Hardware
    out, ok = _run_ps("Get-WmiObject Win32_Processor | Select-Object Name, NumberOfCores | ConvertTo-Json")
    if ok: data["hardware"]["cpu"] = out
    
    out, ok = _run_ps("Get-WmiObject Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum | Select-Object Sum | ConvertTo-Json")
    if ok: data["hardware"]["ram"] = out

    # 2. OS Info
    out, ok = _run_ps("Get-WmiObject Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture, BuildNumber | ConvertTo-Json")
    if ok: data["os"] = out

    # 3. Network
    out, ok = _run_ps("Get-NetIPAddress -AddressFamily IPv4 | Select-Object IPAddress, InterfaceAlias | ConvertTo-Json")
    if ok: data["network"]["ips"] = out

    # 4. Status
    out, ok = _run_ps("(Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime | Select-Object Days, Hours, Minutes | ConvertTo-Json")
    if ok: data["status"]["uptime"] = out

    return data


def get_windows_metrics():
    """Get basic Windows system metrics using psutil (cross-platform)."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    cpu = psutil.cpu_percent(interval=0.5)
    
    return {
        "cpu_percent": cpu,
        "ram_total_gb": round(mem.total / 1024**3, 1),
        "ram_used_gb": round(mem.used / 1024**3, 1),
        "ram_percent": mem.percent,
        "disk_total_gb": round(disk.total / 1024**3, 1),
        "disk_used_gb": round(disk.used / 1024**3, 1),
        "disk_percent": disk.percent
    }
