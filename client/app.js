const API_BASE = "/api";
let isMonitoring = false;
let pollInterval = null;

const metricHistory = { cpu: [], ram: [], disk: [] };
const MAX_HISTORY = 30;

// Theme Persistence & Logic
function initializeTheme() {
    const theme = localStorage.getItem('theme');
    const checkbox = document.getElementById('checkbox');
    if (theme === 'light') {
        document.body.classList.add('light-theme');
        if (checkbox) checkbox.checked = false;
    } else {
        document.body.classList.remove('light-theme');
        if (checkbox) checkbox.checked = true; // Default to dark (checked)
    }
}

function toggleTheme() {
    const checkbox = document.getElementById('checkbox');
    const isDark = checkbox.checked;
    if (isDark) {
        document.body.classList.remove('light-theme');
        localStorage.setItem('theme', 'dark');
    } else {
        document.body.classList.add('light-theme');
        localStorage.setItem('theme', 'light');
    }
}

// Global initialization
window.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    loadConfig();
    startPolling();
    loadSessionProfile();
});

// Tab Switching
function switchTab(tab) {
    document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
    document.querySelectorAll('.module-section').forEach(sec => sec.classList.add('hidden'));
    
    document.getElementById(`nav-${tab}`).classList.add('active');
    document.getElementById(`${tab}-module`).classList.remove('hidden');
    
    // Auto-refresh when entering tabs
    if (tab === 'system') updateExtendedSysInfo();
    if (tab === 'network') updateNetworkDetails();
    if (tab === 'security') runSecurityAudit();

    // Re-initialize Lucide icons for dynamic content
    if (window.lucide) lucide.createIcons();
}

// Configuration Persistence
async function loadConfig() {
    try {
        const res = await fetch(`${API_BASE}/config`);
        const config = await res.json();
        
        document.getElementById('email-input').value = config.receiver_email || "";
        document.getElementById('sender-input').value = config.sender_email || "";
        document.getElementById('password-input').value = config.app_password || "";
        
        const alerts = config.alerts;
        document.getElementById('battery-toggle').checked = alerts.battery.enabled;
        document.getElementById('battery-threshold').value = alerts.battery.threshold;
        document.getElementById('disk-toggle').checked = alerts.disk.enabled;
        document.getElementById('disk-threshold').value = alerts.disk.threshold;
        document.getElementById('cpu-toggle').checked = alerts.cpu.enabled;
        document.getElementById('cpu-threshold').value = alerts.cpu.threshold;
        document.getElementById('ram-toggle').checked = alerts.ram.enabled;
        document.getElementById('ram-threshold').value = alerts.ram.threshold;
        document.getElementById('ip-toggle').checked = alerts.ip_change.enabled;
        document.getElementById('internet-toggle').checked = alerts.internet.enabled;
        
    } catch (err) {
        console.error("Failed to load config:", err);
    }
}

async function saveConfig() {
    const config = {
        receiver_email: document.getElementById('email-input').value,
        sender_email: document.getElementById('sender-input').value,
        app_password: document.getElementById('password-input').value,
        alerts: {
            battery: { enabled: document.getElementById('battery-toggle').checked, threshold: parseInt(document.getElementById('battery-threshold').value) },
            disk: { enabled: document.getElementById('disk-toggle').checked, threshold: parseInt(document.getElementById('disk-threshold').value) },
            cpu: { enabled: document.getElementById('cpu-toggle').checked, threshold: parseInt(document.getElementById('cpu-threshold').value) },
            ram: { enabled: document.getElementById('ram-toggle').checked, threshold: parseInt(document.getElementById('ram-threshold').value) },
            ip_change: { enabled: document.getElementById('ip-toggle').checked },
            internet: { enabled: document.getElementById('internet-toggle').checked }
        }
    };

    try {
        await fetch(`${API_BASE}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        alert("Configuration saved!");
    } catch (err) {
        alert("Failed to save configuration");
    }
}

// Monitoring Toggle
async function toggleMonitoring() {
    const btn = document.getElementById('start-btn');
    const action = isMonitoring ? 'stop' : 'start';
    
    try {
        await fetch(`${API_BASE}/${action}`, { method: 'POST' });
        isMonitoring = !isMonitoring;
        
        if (isMonitoring) {
            btn.innerText = "Stop Monitoring";
            btn.classList.replace('btn-primary', 'btn-secondary');
            startPolling();
        } else {
            btn.innerText = "Start Monitoring";
            btn.classList.replace('btn-secondary', 'btn-primary');
            stopPolling();
        }
    } catch (err) {
        console.error("Failed to toggle monitoring:", err);
    }
}

// Live Status Polling
function startPolling() {
    updateStatus();
    updateLogs();
    pollInterval = setInterval(() => {
        updateStatus();
        updateLogs();
    }, 5000);
}

function stopPolling() {
    clearInterval(pollInterval);
}

async function updateStatus() {
    try {
        const res = await fetch(`${API_BASE}/status`);
        const data = await res.json();
        const stat = data.status;
        isMonitoring = data.is_running;

        if (stat.battery) {
            document.getElementById('stat-battery').innerText = `${stat.battery.percent}% (${stat.battery.plugged ? 'Charging' : 'On Battery'})`;
            document.getElementById('stat-battery').className = 'value ' + (stat.battery.percent < 20 ? 'status-danger' : 'status-good');
        }
        if (stat.cpu !== undefined) {
            document.getElementById('stat-cpu').innerText = `${stat.cpu}%`;
            document.getElementById('stat-cpu').className = 'value ' + (stat.cpu > 80 ? 'status-danger' : 'status-good');
            updateSparkline('cpu-sparkline', stat.cpu);
        }
        if (stat.ram !== undefined) {
            document.getElementById('stat-ram').innerText = `${stat.ram}%`;
            document.getElementById('stat-ram').className = 'value ' + (stat.ram > 80 ? 'status-danger' : 'status-good');
            updateSparkline('ram-sparkline', stat.ram);
        }
        if (stat.disk) {
            document.getElementById('stat-disk').innerText = `${stat.disk.percent}%`;
            document.getElementById('stat-disk').className = 'value ' + (stat.disk.percent > 85 ? 'status-danger' : 'status-good');
            updateSparkline('disk-sparkline', stat.disk.percent);
        }
        if (stat.ips) {
            document.getElementById('stat-local-ip').innerText = stat.ips.local;
            const publicIpEl = document.getElementById('net-public-ip');
            if (publicIpEl) publicIpEl.innerText = stat.ips.public;
        }
        if (stat.internet) {
            document.getElementById('stat-internet').innerText = stat.internet;
            document.getElementById('stat-internet').className = 'value ' + (stat.internet === 'Connected' ? 'status-good' : 'status-danger');
        }

        // Global Uptime badge and color
        if (stat.uptime) {
            const uptimeBadge = document.getElementById('uptime-display');
            if (uptimeBadge) {
                uptimeBadge.innerText = `Uptime: ${stat.uptime.formatted}`;
                uptimeBadge.classList.remove('uptime-orange', 'uptime-red');
                if (stat.uptime.seconds > 86400) uptimeBadge.classList.add('uptime-red');
                else if (stat.uptime.seconds > 43200) uptimeBadge.classList.add('uptime-orange');
            }
        }

        // Sync button state if changed on backend
        const btn = document.getElementById('start-btn');
        if (isMonitoring) {
            btn.innerText = "Stop Monitoring";
            btn.classList.replace('btn-primary', 'btn-secondary');
        } else {
            btn.innerText = "Start Monitoring";
            btn.classList.replace('btn-secondary', 'btn-primary');
        }

        // Update Radial Bars
        if (stat.battery) updateRadial('battery', stat.battery.percent);
        if (stat.cpu !== undefined) updateRadial('cpu', stat.cpu);
        if (stat.ram !== undefined) updateRadial('ram', stat.ram);
        if (stat.disk) updateRadial('disk', stat.disk.percent);

    } catch (err) {
        console.error("Status update failed:", err);
    }
}

async function updateLogs() {
    try {
        const res = await fetch(`${API_BASE}/logs`);
        const logs = await res.json();
        const container = document.getElementById('logs-container');
        
        if (logs.length === 0) {
            container.innerHTML = '<div class="empty-msg">No alerts triggered yet.</div>';
            return;
        }

        container.innerHTML = logs.map(log => `
            <div class="log-entry ${log.type.toLowerCase().replace(' ', '-')}">
                <span class="log-time">${log.time}</span>
                <span class="log-type">${log.type}</span>
                <span class="log-msg">${log.message}</span>
            </div>
        `).join('');
    } catch (err) {
        console.error("Logs update failed:", err);
    }
}

let currentProcessSort = 'cpu';

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    updateStatus(); 
    updateExtendedSysInfo();
    loadSessionProfile(); // Load session on startup
    
    if (window.lucide) lucide.createIcons();
    
    // Auto refresh status
    setInterval(updateStatus, 10000);
});

/* --- SYSTEM COMMAND CENTER LOGIC --- */

const TOOL_METADATA = {
    'mem': { title: 'Memory Analysis', desc: 'Deep-dive into current RAM utilization, swap buffers, and memory-heavy processes.', btn: 'Initialize Analysis', func: () => runTool('health') },
    'cpu-proc': { title: 'CPU Processes', desc: 'Real-time telemetry of high-execution priority processes currently utilizing CPU cycles.', btn: 'List Active PIDs', func: () => runTool('cpu-proc') },
    'disk-usage': { title: 'Storage Audit', desc: 'Comprehensive volume interrogation for partition health and available storage capacity.', btn: 'Perform Audit', func: () => runTool('health') },
    'largest-file': { title: 'Volume Scan', desc: 'Recursive scanner targeting high-capacity local files impacting disk overhead.', btn: 'Execute Scan', inputs: [{id: 'largest-path', label: 'Scan Path', val: '/home'}], func: () => getLargestFiles() },
    'find-word': { title: 'Pattern Search', desc: 'String interrogation within local file content using high-speed filtering techniques.', btn: 'Begin Search', inputs: [{id: 'search-word-path', label: 'Path', val: '/home'}, {id: 'search-keyword', label: 'Keyword', val: ''}], func: () => runWordSearch() },
    'find-file': { title: 'File Locator', desc: 'Metadata-based search for locating specific binary or text assets within the filesystem.', btn: 'Locate Asset', inputs: [{id: 'search-f-path', label: 'Path', val: '/home'}, {id: 'search-f-name', label: 'Filename', val: ''}], func: () => runFileSearch() },
    'sys-details': { title: 'System Specs', desc: 'Hardware-level identification, kernel versioning, and environment metadata.', btn: 'Get Metadata', func: () => updateExtendedSysInfo(true) },
    'health': { title: 'Health Check', desc: 'Diagnostic suite for core system stability and metric validation.', btn: 'Check Vitals', func: () => runTool('health') },
    'net-restart': { title: 'Network Reset', desc: 'Administrative protocol to re-initialize networking stack interfaces.', btn: 'Execute Protocol', func: () => runNetworkRestart() },
    'speedtest': { title: 'Performance Test', desc: 'Live bandwidth throughput assessment on the primary network interface.', btn: 'Run Test', func: () => runSpeedTest() },
    'services': { title: 'Service Manager', desc: 'Listing of active system daemons and listening daemon processes.', btn: 'Analyze Services', func: () => runTool('services') },
    'ports': { title: 'Port Scanner', desc: 'Network interrogation for discovering open listening ports and socket states.', btn: 'Scan Sockets', func: () => runTool('ports') },
    'logs': { title: 'Log Analyzer', desc: 'Heuristic analysis of the latest kernel and system binary logs.', btn: 'Parse Logs', func: () => runTool('logs') },
    'firewall': { title: 'Firewall Policy', desc: 'Audit of the current Uncomplicated Firewall (UFW) rules and active policies.', btn: 'Inspect Policy', func: () => runTool('firewall') }
};

let currentActiveTool = null;

function toggleToolInfo(toolId) {
    const container = document.getElementById('tool-info-container');
    const content = document.getElementById('tool-info-content');
    const actionArea = document.getElementById('tool-action-area');
    
    if (currentActiveTool === toolId && !container.classList.contains('hidden')) {
        container.classList.add('hidden');
        return;
    }

    currentActiveTool = toolId;
    const meta = TOOL_METADATA[toolId];
    
    // Lucide Icon mapping for the preview pane
    const iconName = document.querySelector(`[onclick="toggleToolInfo('${toolId}')"] [data-lucide]`)?.getAttribute('data-lucide') || 'settings';

    content.innerHTML = `
        <h2 style="margin-bottom:0.5rem; text-transform:none; color:var(--text-primary); font-size:1.1rem; letter-spacing:0">
            <i data-lucide="${iconName}" style="width:20px; height:20px; vertical-align:text-bottom; margin-right:8px; color:var(--accent-color)"></i>
            ${meta.title}
        </h2>
        <p style="font-size:0.9rem; color:var(--text-secondary); line-height:1.5">${meta.desc}</p>
        ${meta.inputs ? `
            <div class="input-group" style="margin-top:1.2rem">
                ${meta.inputs.map(i => `<input type="text" id="${i.id}" placeholder="${i.label}" value="${i.val}">`).join('')}
            </div>
        ` : ''}
    `;

    actionArea.innerHTML = `
        <button class="btn-primary" style="padding:0.6rem 1.2rem; font-size:0.85rem" onclick="TOOL_METADATA['${toolId}'].func()">
            ${meta.btn}
        </button>
        <button class="btn-secondary" style="padding:0.6rem 1.2rem; font-size:0.85rem" onclick="document.getElementById('tool-info-container').classList.add('hidden')">
            Deactivate
        </button>
    `;

    container.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function runTool(type) {
    const resultArea = document.getElementById('system-result-area');
    resultArea.innerHTML = `
        <div class="panel" id="tool-running-state">
            <h3 style="display:flex; align-items:center; gap:0.8rem">
                <i data-lucide="refresh-cw" class="icon spin"></i>
                Executing ${type.charAt(0).toUpperCase() + type.slice(1)} Audit...
            </h3>
            <p style="font-size:0.8rem; opacity:0.7; margin-top:0.5rem">Polling system data interfaces, please wait.</p>
        </div>
    `;
    if (window.lucide) lucide.createIcons();
    resultArea.scrollIntoView({ behavior: 'smooth', block: 'center' });

    try {
        let res, data, html = '';
        switch(type) {
            case 'health':
                res = await fetch(`${API_BASE}/sys_health`);
                data = await res.json();
                html = `
                    <div class="panel">
                        <h2><i class="icon">📊</i> Health Result</h2>
                        <div class="status-grid">
                            <div class="status-card"><span class="label">CPU</span><span class="value">${data.cpu}%</span></div>
                            <div class="status-card"><span class="label">RAM</span><span class="value">${data.ram.percent}%</span></div>
                            <div class="status-card"><span class="label">Disk</span><span class="value">${data.disk.percent}%</span></div>
                            <div class="status-card"><span class="label">Uptime</span><span class="value">${data.uptime.formatted}</span></div>
                        </div>
                    </div>
                `;
                break;
            case 'cpu-proc':
                res = await fetch(`${API_BASE}/top_processes?sort=cpu`);
                data = await res.json();
                html = `
                    <div class="panel">
                        <h2><i class="icon">🚀</i> Top Processes</h2>
                        <div class="list-container">
                            ${data.map(p => `<div><strong>${p.name}</strong> (PID ${p.pid}) - ${p.cpu_percent}% CPU</div>`).join('')}
                        </div>
                    </div>
                `;
                break;
            case 'firewall':
                res = await fetch(`${API_BASE}/tools/firewall`);
                data = await res.json();
                html = `<div class="panel"><h2>Firewall Status</h2><pre class="tool-output">${data.output}</pre></div>`;
                break;
            case 'services':
                res = await fetch(`${API_BASE}/tools/services`);
                data = await res.json();
                html = `<div class="panel"><h2>Active System Services</h2><pre class="tool-output">${data.output || "No service data found."}</pre></div>`;
                break;
            case 'ports':
                res = await fetch(`${API_BASE}/tools/services`); // Same endpoint, different context
                data = await res.json();
                html = `<div class="panel"><h2>Network Socket Audit (Listening Ports)</h2><pre class="tool-output">${data.output || "No port data found."}</pre></div>`;
                break;
            case 'logs':
                res = await fetch(`${API_BASE}/tools/logs`);
                data = await res.json();
                html = `<div class="panel"><h2>Syslog / Journal Analysis</h2><pre class="tool-output">${data.output || "Log access denied."}</pre></div>`;
                break;
        }
        resultArea.innerHTML = html;
        setTimeout(() => {
            resultArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
            if (window.lucide) lucide.createIcons();
        }, 100);
    } catch (err) { 
        resultArea.innerHTML = `
            <div class="panel">
                <h2 style="color:var(--danger-color)">Runtime Exception</h2>
                <div class="tool-output" style="border-color:var(--danger-color); color:var(--danger-color)">
                    Error: ${err.message}\n
                    Context: Failed to fetch data from ${type} endpoint.\n
                    Solution: Ensure backend server is active and accessible.
                </div>
            </div>
        `; 
    }
}

async function runNetworkRestart() {
    if (!confirm("This will temporarily drop your networking service. Any active SSH or file transfers will be interrupted. Proceed?")) return;
    try {
        const res = await fetch(`${API_BASE}/tools/network_restart`, { method: 'POST' });
        const data = await res.json();
        alert(data.message);
    } catch (err) { alert("Command issued. Check connectivity."); }
}

async function runHardNetworkRestart() {
    if (!confirm("CRITICAL: This forcefully restarts the NetworkManager service. You will lose connection for several seconds. Proceed?")) return;
    showNetworkToolStatus("Executing Hard Restart...");
    try {
        const res = await fetch(`${API_BASE}/network/hard_restart`, { method: 'POST' });
        const data = await res.json();
        showNetworkToolStatus(data.message, !data.success);
    } catch (err) { showNetworkToolStatus("Request failed. Network may be re-initializing.", true); }
}

async function runSafeNetworkFix() {
    if (!confirm("This will cycle your networking stack off and on. It is safer than a service restart but will still drop your connection temporarily. Proceed?")) return;
    showNetworkToolStatus("Re-initializing networking stack...");
    try {
        const res = await fetch(`${API_BASE}/network/safe_fix`, { method: 'POST' });
        const data = await res.json();
        showNetworkToolStatus(data.message, !data.success);
    } catch (err) { showNetworkToolStatus("Request failed. Check local networking.", true); }
}

async function runNetworkOptimize() {
    showNetworkToolStatus("Applying DNS/TCP optimizations...");
    try {
        const res = await fetch(`${API_BASE}/network/optimize`, { method: 'POST' });
        const data = await res.json();
        showNetworkToolStatus(data.message, !data.success);
    } catch (err) { showNetworkToolStatus("Optimization failed.", true); }
}

function showNetworkToolStatus(msg, isError = false) {
    const out = document.getElementById('network-tool-output');
    out.classList.remove('hidden');
    out.innerText = msg;
    out.style.color = isError ? 'var(--danger-color)' : 'var(--accent-color)';
}

async function runWordSearch() {
    const path = document.getElementById('search-word-path').value;
    const keyword = document.getElementById('search-keyword').value;
    const resultArea = document.getElementById('system-result-area');
    resultArea.innerHTML = '<div class="panel">Searching...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/content_search`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path, keyword})
        });
        const data = await res.json();
        
        let html = '<div class="panel"><h2>Search Results</h2>';
        if (data.warning) {
            html += `<p style="color:var(--warning-color); font-size:0.8rem; margin-bottom:1rem;">⚠️ ${data.warning}</p>`;
        }
        
        const matches = data.results || [];
        html += `<div class="list-container">${matches.map(r => `<div>${r}</div>`).join('') || 'No matches found.'}</div></div>`;
        
        resultArea.innerHTML = html;
    } catch (err) { resultArea.innerHTML = '<div class="panel">Search failed.</div>'; }
}

async function runFileSearch() {
    const path = document.getElementById('search-f-path').value;
    const name = document.getElementById('search-f-name').value;
    const resultArea = document.getElementById('system-result-area');
    resultArea.innerHTML = '<div class="panel">Searching...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/file_search`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path, filename: name})
        });
        const data = await res.json();
        resultArea.innerHTML = `
            <div class="panel">
                <h2>File Search Results</h2>
                <div class="list-container">${data.map(r => `<div>${r}</div>`).join('') || 'No files found.'}</div>
            </div>
        `;
    } catch (err) { resultArea.innerHTML = '<div class="panel">Search failed.</div>'; }
}

async function updateExtendedSysInfo(showInResult = false) {
    try {
        const res = await fetch(`${API_BASE}/extended_sys`);
        const data = await res.json();
        
        document.getElementById('uptime-display').innerText = `Uptime: ${data.uptime}`;

        if (showInResult) {
            const resultArea = document.getElementById('system-result-area');
            resultArea.innerHTML = `
                <div class="panel">
                    <h2><i class="icon">ℹ️</i> Detailed Information</h2>
                    <div class="details-list" style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:1rem">
                        <div class="detail-item"><span class="label">OS</span><span class="value">${data.os}</span></div>
                        <div class="detail-item"><span class="label">Distro</span><span class="value">${data.distro}</span></div>
                        <div class="detail-item"><span class="label">Kernel</span><span class="value">${data.kernel}</span></div>
                        <div class="detail-item"><span class="label">User</span><span class="value">${data.user}</span></div>
                        <div class="detail-item"><span class="label">Hostname</span><span class="value">${data.hostname}</span></div>
                        <div class="detail-item"><span class="label">Arch</span><span class="value">${data.arch}</span></div>
                    </div>
                </div>
            `;
            resultArea.scrollIntoView({ behavior: 'smooth' });
        }
    } catch (err) { console.error("Extended sys info failed:", err); }
}

function setProcessSort(sort) {
    currentProcessSort = sort;
    document.getElementById('proc-sort-cpu').classList.toggle('active', sort === 'cpu');
    document.getElementById('proc-sort-mem').classList.toggle('active', sort === 'memory');
    updateSysHealth();
}

function showProcessSuggestion(suggestion, cmd) {
    const box = document.getElementById('process-suggestion');
    const text = document.getElementById('suggestion-text');
    const code = document.getElementById('suggestion-cmd');
    
    if (!suggestion) {
        box.classList.add('hidden');
        return;
    }
    
    text.innerText = suggestion;
    code.innerText = cmd;
    box.classList.remove('hidden');
}

async function updateSysHealth() {
    try {
        const res = await fetch(`${API_BASE}/sys_health`);
        const data = await res.json();
        
        document.getElementById('sys-cpu').innerText = `${data.cpu}%`;
        document.getElementById('sys-ram').innerText = `${data.ram.used} / ${data.ram.total} (${data.ram.percent}%)`;
        document.getElementById('sys-disk').innerText = `${data.disk.used} / ${data.disk.total} (${data.disk.percent}%)`;
        document.getElementById('uptime-display').innerText = `Uptime: ${data.uptime}`;
        
        // Update processes
        const procRes = await fetch(`${API_BASE}/top_processes?sort=${currentProcessSort}`);
        const procs = await procRes.json();
        const procContainer = document.getElementById('processes-list');
        procContainer.innerHTML = procs.map(p => `
            <div onclick="showProcessSuggestion('${p.suggestion}', '${p.cmd}')" style="display:flex; justify-content:space-between; cursor:pointer">
                <span>PID: ${p.pid} - <strong>${p.name}</strong></span>
                <span style="color:var(--accent-color)">${currentProcessSort === 'cpu' ? p.cpu_percent + '% CPU' : p.memory_percent.toFixed(1) + '% RAM'}</span>
            </div>
        `).join('');
        
    } catch (err) { console.error("Sys health failed:", err); }
}

async function getLargestFiles() {
    const path = document.getElementById('largest-path').value;
    const resultArea = document.getElementById('system-result-area');
    resultArea.innerHTML = '<div class="panel">Scanning...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/largest_files`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path})
        });
        const files = await res.json();
        resultArea.innerHTML = `
            <div class="panel">
                <h2>Top Largest Files</h2>
                <div class="list-container">${files.map(f => `<div><strong>${f.size}</strong> - ${f.path}</div>`).join('') || "No files found."}</div>
            </div>
        `;
    } catch (err) { resultArea.innerHTML = '<div class="panel">Error scanning files.</div>'; }
}

async function searchFiles() {
    const path = document.getElementById('search-path').value;
    const filename = document.getElementById('search-filename').value;
    const container = document.getElementById('search-results');
    container.innerHTML = "Searching...";
    
    try {
        const res = await fetch(`${API_BASE}/file_search`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path, filename})
        });
        const results = await res.json();
        container.innerHTML = results.map(r => `<div>${r}</div>`).join('') || "No matches found.";
    } catch (err) { container.innerHTML = "Error during search."; }
}

function clearResults(id) {
    const container = document.getElementById(id);
    if (container) container.innerHTML = "";
}

async function updateNetworkDetails() {
    try {
        const res = await fetch(`${API_BASE}/network_details`);
        const data = await res.json();
        
        document.getElementById('net-hostname').innerText = data.hostname;
        document.getElementById('net-local-ip').innerText = data.local_ip;
        
        const statusRes = await fetch(`${API_BASE}/status`);
        const statusData = await statusRes.json();
        document.getElementById('net-public-ip-networks').innerText = statusData.status.ips.public || '--';

        const list = document.getElementById('interfaces-list');
        list.innerHTML = data.interfaces.map(i => `
            <div class="interface-card">
                <h3>${i.name}</h3>
                <p>${i.ip}</p>
                <small>${i.netmask}</small>
            </div>
        `).join('');
    } catch (err) { console.error("Net details failed:", err); }
}

async function runSpeedTest() {
    const resultArea = document.getElementById('system-result-area');
    resultArea.innerHTML = '<div class="panel"><h3>Running Performance Test...</h3><p style="font-size:0.8rem; opacity:0.7">This may take up to 45 seconds. Please wait.</p></div>';
    
    try {
        const res = await fetch(`${API_BASE}/speedtest`);
        const data = await res.json();
        
        if (data.error) {
            resultArea.innerHTML = `
                <div class="panel">
                    <h2>Performance Test Failed</h2>
                    <pre class="tool-output" style="color:var(--danger-color)">${data.error}</pre>
                    <p style="font-size:0.8rem; margin-top:1rem">Note: Ensure 'speedtest-cli' is installed on the host system.</p>
                </div>
            `;
            return;
        }

        resultArea.innerHTML = `
            <div class="panel">
                <h2>Network Diagnostics Result</h2>
                <pre class="tool-output">${data.output || "Diagnostics completed with no output."}</pre>
            </div>
        `;
    } catch (err) { 
        resultArea.innerHTML = `<div class="panel"><h2>Connection Error</h2><p style="color:var(--danger-color)">${err.message}</p></div>`; 
    }
}

async function runPing() {
    const host = document.getElementById('ping-host').value;
    const out = document.getElementById('ping-output');
    out.innerText = "Pinging...";
    
    try {
        const res = await fetch(`${API_BASE}/ping`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({host})
        });
        const data = await res.json();
        out.innerText = data.output;
    } catch (err) { out.innerText = "Ping failed."; }
}

async function checkPort() {
    const host = document.getElementById('port-host').value;
    const port = document.getElementById('port-number').value;
    const resDiv = document.getElementById('port-result');
    resDiv.innerText = "Checking...";
    resDiv.className = "port-status";
    
    try {
        const res = await fetch(`${API_BASE}/port_check`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({host, port})
        });
        const data = await res.json();
        resDiv.innerText = data.status;
        resDiv.classList.add(data.status === 'OPEN' ? 'status-open' : 'status-closed');
    } catch (err) { resDiv.innerText = "Error"; }
}

/* SSH Terminal Functions */
function openSSHModal() {
    document.getElementById('ssh-modal').classList.remove('hidden');
}

function closeSSHModal() {
    document.getElementById('ssh-modal').classList.add('hidden');
}

function connectSSH() {
    const host = document.getElementById('ssh-host').value;
    const user = document.getElementById('ssh-user').value;
    const pass = document.getElementById('ssh-pass').value;

    if (!host || !user || !pass) {
        alert("Please enter all credentials.");
        return;
    }

    // Hide setup, show terminal (simulated session)
    document.getElementById('ssh-setup').classList.add('hidden');
    document.getElementById('ssh-terminal-container').classList.remove('hidden');
    addTermLine(`Connected to ${user}@${host}...`);
}

function addTermLine(text, isError = false) {
    const output = document.getElementById('ssh-output');
    const line = document.createElement('div');
    line.className = 'term-line';
    if (isError) line.style.color = '#ff4444';
    line.innerText = text;
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
}

async function sendSSHCommand() {
    const input = document.getElementById('ssh-cmd-input');
    const command = input.value;
    if (!command) return;

    const host = document.getElementById('ssh-host').value;
    const user = document.getElementById('ssh-user').value;
    const pass = document.getElementById('ssh-pass').value;

    addTermLine(`$ ${command}`);
    input.value = '';

    try {
        const res = await fetch(`${API_BASE}/ssh/exec`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({host, user, password: pass, command})
        });
        const data = await res.json();
        if (data.output) addTermLine(data.output);
        if (data.error) addTermLine(data.error, true);
        if (data.error && !data.output) addTermLine("Execution failed: " + data.error, true);
    } catch (err) {
        addTermLine("Transmission Error: " + err, true);
    }
}

async function runSecurityAudit() {
    const resultsDiv = document.getElementById('audit-results');
    resultsDiv.innerHTML = '<div class="empty-msg">Auditing...</div>';
    
    const priority = { 'FAIL': 0, 'WARNING': 1, 'INFO': 2, 'PASS': 3 };

    try {
        const res = await fetch(`${API_BASE}/security/audit`);
        let data = await res.json();
        
        data.sort((a, b) => (priority[a.status] ?? 99) - (priority[b.status] ?? 99));

        resultsDiv.innerHTML = '';
        data.forEach(item => {
            const entry = document.createElement('div');
            entry.className = 'audit-entry';
            
            let statusClass = 'status-info-bg';
            if (item.status === 'PASS') statusClass = 'status-pass-bg';
            else if (item.status === 'FAIL') statusClass = 'status-fail-bg';
            else if (item.status === 'WARNING') statusClass = 'status-warning-bg';
            
            entry.style.borderLeftColor = item.status === 'FAIL' ? 'var(--danger-color)' : (item.status === 'WARNING' ? '#fbbf24' : (item.status === 'PASS' ? 'var(--success-color)' : 'var(--accent-color)'));
            
            const canFix = item.fix_command && (item.status === 'FAIL' || item.status === 'WARNING');
            
            entry.innerHTML = `
                <div class="audit-header">
                    <div>
                        <span class="audit-check">${item.check}</span>
                        ${canFix ? '<span class="fix-hint">Click here to fix</span>' : ''}
                    </div>
                    <span class="audit-status ${statusClass}">${item.status}</span>
                </div>
                <div class="audit-msg">
                    <strong>${item.target}</strong>: ${item.suggestion}
                </div>
                ${item.fix_command ? `
                    <div class="security-suggestion hidden">
                        <p style="font-size:0.8rem; margin-bottom:0.5rem; opacity:0.8">Action Plan:</p>
                        <code style="display:block; background:rgba(255,255,255,0.05); padding:0.5rem; border-radius:4px; font-size:0.75rem">${item.fix_command}</code>
                        ${canFix ? `<button class="btn-fix" onclick="fixSecurityIssue('${item.fix_command.replace(/'/g, "\\'")}', this)">Fix It Automatically</button>` : ''}
                    </div>
                ` : ''}
            `;
            
            if (item.fix_command) {
                entry.onclick = (e) => {
                    if (e.target.tagName === 'BUTTON' || e.target.tagName === 'CODE') return;
                    entry.classList.toggle('active');
                    entry.querySelector('.security-suggestion').classList.toggle('hidden');
                };
            }
            resultsDiv.appendChild(entry);
        });
    } catch (err) { resultsDiv.innerHTML = '<div class="empty-msg">Audit failed.</div>'; }
}

async function fixSecurityIssue(command, btn) {
    const parent = btn.parentElement.parentElement;
    btn.disabled = true;
    btn.innerText = "Applying Fix...";
    
    try {
        const res = await fetch(`${API_BASE}/security/fix`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({command})
        });
        const data = await res.json();
        
        if (data.message) {
            btn.parentElement.innerHTML = '<div class="status-fixed">✅ Issue Resolved Successfully</div>';
            parent.querySelector('.audit-status').className = 'audit-status status-pass-bg';
            parent.querySelector('.audit-status').innerText = 'FIXED';
            parent.querySelector('.fix-hint')?.remove();
        } else {
            console.error("Fix Failed Details:", data);
            btn.innerText = "Fix Failed";
            const errorMsg = data.error || "Unknown error";
            const suggest = data.suggestion || "Check terminal logs.";
            
            // Show detailed error in-place
            const errBox = document.createElement('div');
            errBox.style = "margin-top:10px; padding:10px; background:rgba(248,113,113,0.1); border:1px solid var(--danger-color); border-radius:4px; font-size:0.8rem; color:var(--danger-color)";
            errBox.innerHTML = `
                <strong>${errorMsg}</strong><br>
                ${suggest}<br>
                <code style="display:block; margin-top:5px; font-size:0.7rem; opacity:0.8">${data.details || ""}</code>
            `;
            btn.parentElement.appendChild(errBox);
            btn.style.display = 'none';
        }
    } catch (err) {
        btn.innerText = "Error";
        console.error(err);
    }
}

async function runMalwareScan() {
    const path = document.getElementById('scan-path').value;
    const statusDiv = document.getElementById('scan-status');
    const resultsDiv = document.getElementById('scan-results');
    const btn = document.getElementById('scan-btn');
    const missingDiv = document.getElementById('clamav-missing');
    
    btn.disabled = true;
    statusDiv.style.color = "var(--text-primary)";
    statusDiv.innerText = "Scanning... (This may take a while)";
    resultsDiv.innerHTML = '';
    missingDiv.classList.add('hidden');
    
    try {
        const res = await fetch(`${API_BASE}/security/scan`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path})
        });
        const data = await res.json();
        
        btn.disabled = false;
        if (data.error) {
            statusDiv.innerText = data.error;
            statusDiv.style.color = "var(--danger-color)";
            if (data.error.toLowerCase().includes("not installed")) {
                missingDiv.classList.remove('hidden');
            }
            return;
        }
        
        statusDiv.innerHTML = `Scan Complete: <strong style="color:${data.count > 0 ? 'var(--danger-color)' : 'var(--success-color)'}">${data.count}</strong> threats found.`;
        
        if (data.infected.length === 0) {
            resultsDiv.innerHTML = '<div class="empty-msg">No threats detected in this directory.</div>';
        } else {
            data.infected.forEach(item => {
                const entry = document.createElement('div');
                entry.className = 'audit-entry';
                entry.style.borderLeftColor = 'var(--danger-color)';
                entry.innerHTML = `
                    <div class="audit-header">
                        <span class="audit-check">THREAT DETECTED</span>
                        <span class="audit-status status-fail-bg">${item.virus}</span>
                    </div>
                    <div class="audit-msg">
                        <strong>File:</strong> ${item.file}<br>
                        <strong>Recommended:</strong> ${item.suggestion}
                    </div>
                `;
                resultsDiv.appendChild(entry);
            });
        }
    } catch (err) {
        statusDiv.innerText = "Scan failed due to connection error.";
        btn.disabled = false;
    }
}

function updateSparkline(id, value) {
    const metric = id.split('-')[0];
    metricHistory[metric].push(value);
    if (metricHistory[metric].length > MAX_HISTORY) metricHistory[metric].shift();
    
    const container = document.getElementById(id);
    if (!container) return;
    
    const width = container.clientWidth || 300;
    const height = 40;
    
    if (metricHistory[metric].length < 2) return;

    const points = metricHistory[metric].map((v, i) => {
        const x = (i / (MAX_HISTORY - 1)) * width;
        const y = height - (v / 100) * height;
        return `${x},${y}`;
    });

    const pathData = `M ${points.join(' L ')}`;
    const fillData = `${pathData} L ${width},${height} L 0,${height} Z`;
    
    container.innerHTML = `
        <svg class="sparkline-svg" width="100%" height="${height}" viewbox="0 0 ${width} ${height}" preserveAspectRatio="none">
            <path class="sparkline-fill" d="${fillData}"></path>
            <path class="sparkline-path" d="${pathData}"></path>
        </svg>
    `;
}

/* --- NEW: RADIAL PROGRESS LOGIC --- */

function updateRadial(id, percent) {
    const container = document.getElementById(`radial-${id}`);
    if (!container) return;

    const progressBar = container.querySelector('.progress-bar');
    const text = container.querySelector('.percentage-text');
    
    const circumference = 2 * Math.PI * 20; // r=20
    const offset = circumference - (percent / 100 * circumference);
    
    progressBar.style.strokeDasharray = circumference;
    progressBar.style.strokeDashoffset = offset;
    text.innerText = `${Math.round(percent)}%`;

    // Color feedback
    if (percent > 85) progressBar.style.stroke = 'var(--danger-color)';
    else if (percent > 70) progressBar.style.stroke = 'var(--warning-color)';
    else progressBar.style.stroke = 'var(--accent-color)';
}

/* --- NEW: SESSION RESTORATION LOGIC --- */

let currentSessionProfile = { apps: [], services: [], ports: [] };
let fullInventory = { apps: [], services: [] };
let pickerType = 'app';

async function loadSessionProfile() {
    try {
        const res = await fetch(`${API_BASE}/session/load`);
        currentSessionProfile = await res.json();
        renderSessionChips();
    } catch (err) { console.error("Failed to load session:", err); }
}

function renderSessionChips() {
    const appsList = document.getElementById('session-apps');
    const servicesList = document.getElementById('session-services');
    
    if (appsList) {
        appsList.innerHTML = currentSessionProfile.apps.map(app => `
            <div class="resource-chip">
                <span>${app.name}</span>
                <button onclick="removeResource('${app.id}', 'app')">&times;</button>
            </div>
        `).join('') || '<div class="empty-msg" style="padding:0.5rem; font-size:10px">No apps selected.</div>';
    }
    
    if (servicesList) {
        servicesList.innerHTML = currentSessionProfile.services.map(svc => `
            <div class="resource-chip">
                <span>${svc.name}</span>
                <button onclick="removeResource('${svc.name}', 'service')">&times;</button>
            </div>
        `).join('') || '<div class="empty-msg" style="padding:0.5rem; font-size:10px">No services selected.</div>';
    }
}

async function openResourcePicker(type) {
    pickerType = type;
    document.getElementById('resource-picker-modal').classList.remove('hidden');
    document.getElementById('picker-title').innerText = `Select ${type === 'app' ? 'Application' : 'System Service'}`;
    
    const container = document.getElementById('inventory-list');
    container.innerHTML = '<div class="empty-msg">Scanning system...</div>';

    if (fullInventory.apps.length === 0) {
        try {
            const res = await fetch(`${API_BASE}/session/inventory`);
            fullInventory = await res.json();
        } catch (err) {
            container.innerHTML = '<div class="empty-msg">Failed to load inventory.</div>';
            return;
        }
    }
    renderInventory();
}

function closeResourcePicker() {
    document.getElementById('resource-picker-modal').classList.add('hidden');
}

let tempSelection = [];

function renderInventory(filter = "") {
    const container = document.getElementById('inventory-list');
    const items = pickerType === 'app' ? fullInventory.apps : fullInventory.services;
    const filtered = items.filter(i => (i.name || i).toLowerCase().includes(filter.toLowerCase()));
    
    container.innerHTML = filtered.map(item => {
        const name = item.name || item;
        const id = item.id || name;
        const isSelected = tempSelection.includes(id);
        return `
            <div class="inventory-item ${isSelected ? 'selected' : ''}" onclick="toggleResourceSelection('${id}')">
                <i data-lucide="${pickerType === 'app' ? 'layers' : 'settings'}" class="icon"></i>
                <div class="info">
                    <div class="name">${name}</div>
                    <div class="type">${item.state || pickerType}</div>
                </div>
            </div>
        `;
    }).join('');
    if (window.lucide) lucide.createIcons();
}

function filterInventory() {
    const q = document.getElementById('picker-search').value;
    renderInventory(q);
}

function toggleResourceSelection(id) {
    const idx = tempSelection.indexOf(id);
    if (idx > -1) {
        tempSelection.splice(idx, 1);
    } else {
        tempSelection.push(id);
    }
    renderInventory(document.getElementById('picker-search').value);
}

function confirmResourceSelection() {
    const items = pickerType === 'app' ? fullInventory.apps : fullInventory.services;
    const list = pickerType === 'app' ? currentSessionProfile.apps : currentSessionProfile.services;
    
    tempSelection.forEach(id => {
        const item = items.find(i => (i.id || i.name) === id);
        if (item && !list.find(li => (li.id || li.name) === id)) {
            list.push(item);
        }
    });
    
    renderSessionChips();
    closeResourcePicker();
    tempSelection = [];
}

function removeResource(id, type) {
    const list = type === 'app' ? currentSessionProfile.apps : currentSessionProfile.services;
    const idx = list.findIndex(i => (i.id || i.name) === id);
    if (idx > -1) {
        list.splice(idx, 1);
        renderSessionChips();
    }
}

async function saveSessionProfile() {
    try {
        const res = await fetch(`${API_BASE}/session/save`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(currentSessionProfile)
        });
        alert("Session Profile Saved!");
    } catch (err) { alert("Failed to save profile."); }
}

async function restoreSession() {
    const btn = document.querySelector('button[onclick="restoreSession()"]');
    const oldText = btn.innerText;
    btn.innerText = "Restoring Session...";
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/session/restore`, { method: 'POST' });
        const data = await res.json();
        const successCount = data.results.filter(r => r.success).length;
        alert(`Session Restoration Complete: ${successCount} of ${data.results.length} resources started.`);
    } catch (err) { alert("Restoration failed. Check server logs."); }
    
    btn.innerText = oldText;
    btn.disabled = false;
}

/* --- NEW: AI TROUBLESHOOTER LOGIC --- */

/* --- NEW: GUIDED AI TROUBLESHOOTER FLOW --- */

let currentAiState = {
    model: 'mistral:latest',
    issue: ''
};

async function analyzeIssue() {
    const input = document.getElementById('ai-input').value.trim();
    if (!input) {
        alert("Please describe your issue first.");
        return;
    }
    currentAiState.issue = input;

    const resultArea = document.getElementById('ai-result-area');
    resultArea.innerHTML = `
        <div class="wizard-screen">
            <i data-lucide="search" class="icon spin wizard-icon" style="color:var(--accent-color)"></i>
            <h3 class="wizard-title">Checking AI Environment</h3>
            <p class="wizard-desc">Detecting local AI engines and verifying model integrity...</p>
        </div>
    `;
    if (window.lucide) lucide.createIcons();

    try {
        const res = await fetch(`${API_BASE}/ai/status`);
        const status = await res.json();
        
        handleAiStatus(status);
    } catch (err) {
        showErrorScreen("Connectivity Issue", "Unable to communicate with the local backend server.");
    }
}

function handleAiStatus(status) {
    const resultArea = document.getElementById('ai-result-area');
    
    // Case 1: Ollama not installed
    if (!status.installed) {
        resultArea.innerHTML = `
            <div class="wizard-screen">
                <span class="wizard-icon">❌</span>
                <h3 class="wizard-title">Ollama Not Found</h3>
                <p class="wizard-desc">No local AI engine detected. This feature requires Ollama to be installed on your system.</p>
                <div class="cmd-block">curl -fsSL https://ollama.com/install.sh | sh</div>
                <button class="btn-primary" onclick="window.open('https://ollama.com', '_blank')">Install Ollama Guide</button>
                <button class="btn-secondary" onclick="analyzeIssue()" style="margin-left:1rem;">Retry Detection</button>
            </div>
        `;
    } 
    // Case 2: Ollama exists but service not running
    else if (!status.running) {
        resultArea.innerHTML = `
            <div class="wizard-screen">
                <span class="wizard-icon">🟡</span>
                <h3 class="wizard-title">Ollama Not Running</h3>
                <p class="wizard-desc">The Ollama engine is installed but the background service is not active.</p>
                <div class="cmd-block">ollama serve</div>
                <button class="btn-primary" onclick="analyzeIssue()">Wake Up AI</button>
            </div>
        `;
    }
    // Case 3: No models found
    else if (status.models.length === 0) {
        showModelSetupScreen();
    }
    // Case 4: Ready but maybe needs specific model
    else {
        // Preferred model check
        if (status.models.includes('mistral:latest') || status.models.includes('mistral')) {
            currentAiState.model = 'mistral:latest';
            showPermissionPrompt();
        } else if (status.models.includes('llama3:latest') || status.models.includes('llama3')) {
            currentAiState.model = 'llama3:latest';
            showPermissionPrompt();
        } else {
            showModelSetupScreen();
        }
    }
    if (window.lucide) lucide.createIcons();
}

function showModelSetupScreen() {
    const resultArea = document.getElementById('ai-result-area');
    resultArea.innerHTML = `
        <div class="wizard-screen">
            <span class="wizard-icon">📦</span>
            <h3 class="wizard-title">Model Setup Required</h3>
            <p class="wizard-desc">Ollama is ready, but you need a lightweight model (Mistral) to process your request.</p>
            <button class="btn-primary" id="model-install-btn" onclick="installAiModel('mistral:latest')">
                Install Mistral (4.1GB)
            </button>
        </div>
    `;
}

async function installAiModel(modelName) {
    const btn = document.getElementById('model-install-btn');
    btn.disabled = true;
    btn.innerText = "Downloading Model (may take minutes)...";

    try {
        const res = await fetch(`${API_BASE}/ai/setup`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ model: modelName })
        });
        const data = await res.json();
        if (data.success) {
            analyzeIssue(); // Restart flow
        } else {
            alert("Model installation failed: " + data.output);
            btn.disabled = false;
            btn.innerText = "Retry Install";
        }
    } catch (err) {
        alert("Network error during installation.");
        btn.disabled = false;
    }
}

function showPermissionPrompt() {
    const resultArea = document.getElementById('ai-result-area');
    resultArea.innerHTML = `
        <div class="wizard-screen">
            <span class="wizard-icon">🔒</span>
            <h3 class="wizard-title">AI Analysis Permission</h3>
            <p class="wizard-desc">The local engine (${currentAiState.model}) is ready. Would you like it to analyze your system issue?</p>
            <div style="display:flex; justify-content:center; gap:1rem;">
                <button class="btn-primary" onclick="proceedWithAiAnalysis()">Proceed with Analysis</button>
                <button class="btn-secondary" onclick="resetAiArea()">Cancel</button>
            </div>
        </div>
    `;
}

async function proceedWithAiAnalysis() {
    const resultArea = document.getElementById('ai-result-area');
    resultArea.innerHTML = `
        <div class="ai-result-panel" style="text-align:center; padding-top:4rem;">
            <i data-lucide="refresh-cw" class="icon spin" style="width:48px; height:48px; color:var(--accent-color); margin-bottom:1rem;"></i>
            <p style="color:var(--text-secondary)">Engaging Local LLM (${currentAiState.model})...</p>
        </div>
    `;
    if (window.lucide) lucide.createIcons();

    try {
        const res = await fetch(`${API_BASE}/ai/analyze`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                issue: currentAiState.issue,
                model: currentAiState.model
            })
        });
        const data = await res.json();

        if (data.error) throw new Error(data.error);

        renderAiResults(data);
    } catch (err) {
        showErrorScreen("Analysis Failed", err.message);
    }
}

function renderAiResults(data) {
    const resultArea = document.getElementById('ai-result-area');
    resultArea.innerHTML = `
        <div class="ai-result-panel">
            <div class="ai-card issue">
                <h3 style="color:var(--text-primary); margin-bottom:0.5rem;">
                    <i data-lucide="search" class="icon" style="color:var(--accent-color)"></i>
                    Detected: ${data.issue}
                </h3>
                <ul class="cause-list">
                    ${data.causes.map(c => `<li>${c}</li>`).join('')}
                </ul>
            </div>

            <div class="ai-card fixes">
                <h3 style="color:var(--text-primary); margin-bottom:1rem;">
                    <i data-lucide="check-circle" class="icon" style="color:#10b981"></i>
                    Recommended Remediation
                </h3>
                <div id="ai-fixes-list">
                    ${data.fixes.map(f => `
                        <div class="fix-item">
                            <span class="fix-title">${f}</span>
                            <button class="btn-primary" style="padding:0.4rem 0.8rem; font-size:0.75rem; background:#10b981;" 
                                onclick="executeAiFix('${f}', this)">
                                Fix Now
                            </button>
                        </div>
                    `).join('') || '<p class="empty-msg">No automated fixes available for this issue.</p>'}
                </div>
            </div>
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

function showErrorScreen(title, msg) {
    const resultArea = document.getElementById('ai-result-area');
    resultArea.innerHTML = `
        <div class="wizard-screen">
            <span class="wizard-icon">⚠️</span>
            <h3 class="wizard-title" style="color:var(--danger-color)">${title}</h3>
            <p class="wizard-desc">${msg}</p>
            <button class="btn-primary" onclick="analyzeIssue()">Retry Process</button>
        </div>
    `;
}

function resetAiArea() {
    const resultArea = document.getElementById('ai-result-area');
    resultArea.innerHTML = `
        <div class="empty-msg" style="margin-top:4rem;">
            <i data-lucide="bot" style="width:48px; height:48px; opacity:0.2; margin-bottom:1rem;"></i>
            <p>Analysis cancelled. Enter a new issue to start over.</p>
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

async function executeAiFix(fixTitle, btn) {
    const originalText = btn.innerText;
    btn.innerText = "Fixing...";
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/ai/fix`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ fix_title: fixTitle })
        });
        const data = await res.json();

        if (data.success) {
            btn.innerText = "Applied!";
            btn.style.background = "#059669";
            setTimeout(() => {
                alert(`Fix Applied Successfully!\n\nOutput:\n${data.output}`);
            }, 100);
        } else {
            btn.innerText = "Failed";
            btn.style.background = "var(--danger-color)";
            alert(`Execution Failed:\n${data.output}`);
        }
    } catch (err) {
        alert("Network error occurred during fix execution.");
        btn.innerText = originalText;
        btn.disabled = false;
    }
}
