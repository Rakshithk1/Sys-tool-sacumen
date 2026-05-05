# Sys-tool

## 📌 Overview
Sys-tool is an adaptive system intelligence and monitoring platform that enhances traditional shell-based utilities with a unified dashboard, automation engine, diagnostics toolkit, and AI-assisted features.

It automatically detects the operating system and adapts functionality for Linux (including VM environments) and Windows systems.

---

## ⚙️ Core Modules

### 🖥 System Intelligence Dashboard
A real-time system overview without requiring terminal commands:
- System uptime tracking  
- CPU, RAM, and storage metrics  
- Live process telemetry  
- System specifications and environment metadata  

---

### 🔍 Diagnostic & Utility Engine
Advanced system inspection and troubleshooting toolkit:
- Storage audit and large file detection  
- Pattern-based file search (grep-like functionality)  
- System health validation checks  
- Network diagnostics and bandwidth testing  
- Service and port analysis  
- Log analysis and parsing engine  
- File transfer utilities (SCP / Rsync style support)  

---

### 📊 Live Monitoring Platform (Linux / VM)
Real-time system monitoring dashboard:
- CPU, RAM, Disk, and Battery monitoring  
- Active application tracking  
- Critical service monitoring  
- Session save and restore functionality  
- Real-time system analytics  

---

### 🚨 Smart Alert System (Linux / VM Only)
Automated alerting system for system threshold violations:
- Email notifications via Gmail SMTP  
- Configurable alert thresholds:
  - CPU usage  
  - Memory usage  
  - Disk usage  
  - Battery critical level  
- IP change detection alerts  
- Incident logging system  

---

### 🌐 Networking & Security Tools
System-level network and security utilities:
- SSH and service management tools  
- Network scanning and socket discovery  
- IP tracking and connectivity monitoring  
- Folder scanning for suspicious patterns  
- Basic malware detection heuristics  
- Security policy validation engine  

---

### 🤖 AI Assistant Module
Built-in AI-powered system assistant:
- Local AI integration (LLM-based tools like Ollama or external APIs)  
- System troubleshooting assistance  
- Command suggestions and automation support  
- Smart workflow guidance  

---

### 🪟 Cross-Platform Support
- **Linux / VM:** Full feature set including monitoring and alert system  
- **Windows:** Core system utilities without alerting module  

---

## 🛠 Tech Stack
- Node.js / Python  
- Shell scripting  
- Linux system APIs  
- Docker  
- SMTP (Gmail alerts)  
- Optional LLM integration (Ollama / AI tools)  

---

## 🚀 How to Run

### Server (Backend)

cd server
python app.py

## 📜 Notes
This project originated as a shell-based utility and was later evolved into a full system monitoring and automation platform using AI-assisted development tools.
