import psutil
import requests
import time
import threading
import json
import os
from mailer import send_alert_email
import utils

class MonitorEngine:
    def __init__(self, config_path, logs_path):
        self.config_path = config_path
        self.logs_path = logs_path
        self.config = self.load_config()
        self.logs = []
        self.running = False
        self.current_status = {}
        self.last_values = {
            "public_ip": None,
            "private_ip": None,
            "battery_percent": None
        }

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {
            "receiver_email": "",
            "sender_email": "",
            "app_password": "",
            "alerts": {
                "battery": {"enabled": True, "threshold": 20},
                "disk": {"enabled": True, "threshold": 85},
                "cpu": {"enabled": True, "threshold": 80},
                "ram": {"enabled": True, "threshold": 80},
                "ip_change": {"enabled": True},
                "internet": {"enabled": True}
            }
        }

    def save_config(self, new_config):
        self.config = new_config
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def add_log(self, alert_type, message, value):
        log_entry = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": alert_type,
            "message": message,
            "value": value
        }
        self.logs.insert(0, log_entry)
        if len(self.logs) > 50:
            self.logs.pop()
        
        # Trigger email
        if self.config.get("receiver_email"):
            send_alert_email(self.config, alert_type, value)

    def check_battery(self):
        battery = psutil.sensors_battery()
        if not battery: return
        
        percent = battery.percent
        plugged = battery.power_plugged
        self.current_status["battery"] = {"percent": percent, "plugged": plugged}
        
        cfg = self.config["alerts"]["battery"]
        if cfg["enabled"]:
            was_below = self.last_values.get("battery_below_thresh", False)
            if percent < cfg["threshold"] and not plugged:
                if not was_below:
                    self.add_log("Battery Alert", f"Battery low: {percent}%", f"{percent}%")
                self.last_values["battery_below_thresh"] = True
            else:
                self.last_values["battery_below_thresh"] = False
            
            last_plugged = self.last_values.get("battery_plugged")
            if last_plugged is True and not plugged:
                 self.add_log("Battery Alert", "Charger disconnected", "Disconnected")
            elif last_plugged is False and plugged:
                 self.add_log("Battery Alert", "Charger connected", "Charging")

        self.last_values["battery_percent"] = percent
        self.last_values["battery_plugged"] = plugged

    def check_ips(self):
        # Private IP
        private_ip = "Unknown"
        try:
            import socket
            private_ip = socket.gethostbyname(socket.gethostname())
        except: pass
        
        # Public IP
        public_ip = "Unknown"
        if self.config["alerts"]["internet"]["enabled"] or self.config["alerts"]["ip_change"]["enabled"]:
            try:
                public_ip = requests.get('https://ifconfig.me/ip', timeout=5).text.strip()
            except:
                public_ip = "Request Failed"

        self.current_status["ips"] = {"private": private_ip, "public": public_ip}
        
        if self.config["alerts"]["ip_change"]["enabled"]:
            if self.last_values["private_ip"] and private_ip != self.last_values["private_ip"]:
                self.add_log("IP Change", "Private IP changed", private_ip)
        
        if public_ip != "Request Failed":
            self.last_values["public_ip"] = public_ip
        self.last_values["private_ip"] = private_ip

    def check_disk(self):
        disk = psutil.disk_usage('/')
        percent = disk.percent
        self.current_status["disk"] = {"percent": percent}
        
        cfg = self.config["alerts"]["disk"]
        if cfg["enabled"] and percent > cfg["threshold"]:
            self.add_log("Disk Alert", f"Disk usage high: {percent}%", f"{percent}%")

    def check_cpu_ram(self):
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        self.current_status["cpu"] = cpu
        self.current_status["ram"] = ram
        
        if self.config["alerts"]["cpu"]["enabled"] and cpu > self.config["alerts"]["cpu"]["threshold"]:
            self.add_log("CPU Alert", f"CPU usage high: {cpu}%", f"{cpu}%")
        
        if self.config["alerts"]["ram"]["enabled"] and ram > self.config["alerts"]["ram"]["threshold"]:
            self.add_log("RAM Alert", f"RAM usage high: {ram}%", f"{ram}%")

    def check_internet(self):
        connected = False
        try:
            requests.get('https://www.google.com', timeout=3)
            connected = True
        except:
            connected = False
            
        self.current_status["internet"] = "Connected" if connected else "Disconnected"
        
        if self.config["alerts"]["internet"]["enabled"] and not connected:
            self.add_log("Internet Alert", "Connection lost", "Offline")

    def run_loop(self):
        while self.running:
            try:
                self.check_battery()
                self.check_ips()
                self.check_disk()
                self.check_cpu_ram()
                self.check_internet()
                self.current_status["uptime"] = utils.get_system_uptime()
            except Exception as e:
                print(f"Monitor error: {e}")
            
            time.sleep(10) # 10 second interval

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
