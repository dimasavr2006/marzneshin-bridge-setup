#!/usr/bin/env python3
"""
Bridge Subscription Server
Dynamic config generation with UUID substitution
"""

from flask import Flask, request, jsonify, render_template_string
import json
import os
import re
from pathlib import Path

app = Flask(__name__)

# Determine base directory based on installation mode
if os.path.exists("/opt/marzneshin-vps-setup/subscriptions"):
    BASE_DIR = Path("/opt/marzneshin-vps-setup/subscriptions")
else:
    BASE_DIR = Path("/opt/marznode/subscriptions")


def load_bridge_config():
    config_path = BASE_DIR / "bridge_config.json"
    if not config_path.exists():
        return None
    with open(config_path) as f:
        return json.load(f)


def generate_config(template_name, uuid):
    template_path = BASE_DIR / template_name
    if not template_path.exists():
        return None
    
    with open(template_path) as f:
        content = f.read()
    
    content = content.replace("{{USER_UUID}}", uuid)
    return json.loads(content)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bridge Subscription</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 { color: #333; margin-bottom: 10px; text-align: center; }
        .subtitle { color: #666; text-align: center; margin-bottom: 30px; }
        .warning {
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 30px;
            color: #856404;
        }
        .info-box {
            background: #e7f3ff;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
        }
        button {
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover { background: #5568d3; }
        .configs {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .config-card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }
        .config-card h3 { color: #667eea; margin-bottom: 10px; }
        .config-card p { color: #666; font-size: 14px; margin-bottom: 10px; }
        .config-card a {
            display: inline-block;
            margin-top: 10px;
            padding: 8px 16px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 14px;
        }
        .config-card a:hover { background: #5568d3; }
        .hidden { display: none; }
        .instructions {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .instructions h3 { color: #333; margin-bottom: 15px; }
        .instructions ol { margin-left: 20px; color: #555; }
        .instructions li { margin-bottom: 8px; }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Bridge Subscription</h1>
        <p class="subtitle">Chain Proxy Configs for White Lists</p>
        
        <div class="warning">
            <strong>Important:</strong> Access this page when white lists are OFF to save configs. 
            When lists are ON, use the saved configs.
        </div>
        
        <div class="info-box">
            <strong>How it works:</strong> Your purchased VLESS server acts as a bridge to reach your own server. 
            Internet exit is still from YOUR server.
        </div>
        
        <form id="uuidForm">
            <div class="input-group">
                <input type="text" id="uuidInput" placeholder="Enter your UUID from the panel" required
                       pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}">
                <button type="submit">Generate Configs</button>
            </div>
        </form>
        
        <div id="configs" class="configs hidden">
            <div class="config-card">
                <h3>Xray Full</h3>
                <p>All 4 options in one config</p>
                <a id="xrayLink" href="#" download="xray.json">Download</a>
            </div>
            <div class="config-card">
                <h3>Sing-box Full</h3>
                <p>All 4 options in one config</p>
                <a id="singboxLink" href="#" download="singbox.json">Download</a>
            </div>
            <div class="config-card">
                <h3>Direct TCP</h3>
                <p>For when lists are OFF</p>
                <a id="directTcpLink" href="#" download="direct-tcp.json">Download</a>
            </div>
            <div class="config-card">
                <h3>Direct XHTTP</h3>
                <p>For when lists are OFF</p>
                <a id="directXhttpLink" href="#" download="direct-xhttp.json">Download</a>
            </div>
            <div class="config-card">
                <h3>Proxy TCP</h3>
                <p>For when lists are ON</p>
                <a id="proxyTcpLink" href="#" download="proxy-tcp.json">Download</a>
            </div>
            <div class="config-card">
                <h3>Proxy XHTTP</h3>
                <p>For when lists are ON</p>
                <a id="proxyXhttpLink" href="#" download="proxy-xhttp.json">Download</a>
            </div>
        </div>
        
        <div class="instructions">
            <h3>Instructions</h3>
            <ol>
                <li>Copy your UUID from the Marzneshin panel (Users -> Your User -> UUID)</li>
                <li>Paste it above and click "Generate Configs"</li>
                <li>Download configs for your client (Xray or Sing-box)</li>
                <li><strong>When lists are OFF:</strong> Use "Direct" configs</li>
                <li><strong>When lists are ON:</strong> Use "Proxy" configs (routes through bridge)</li>
            </ol>
        </div>
        
        <div class="instructions">
            <h3>For Sing-box Automatic Import</h3>
            <p>Use this URL in Sing-box:</p>
            <code id="singboxUrl"></code>
        </div>
    </div>
    
    <script>
        document.getElementById('uuidForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const uuid = document.getElementById('uuidInput').value.trim();
            if (!uuid) return;
            
            const baseUrl = window.location.pathname;
            if (!baseUrl.endsWith('/')) baseUrl += '/';
            
            const params = 'uuid=' + encodeURIComponent(uuid);
            
            document.getElementById('xrayLink').href = baseUrl + 'xray.json?' + params;
            document.getElementById('singboxLink').href = baseUrl + 'singbox.json?' + params;
            document.getElementById('directTcpLink').href = baseUrl + 'direct-tcp.json?' + params;
            document.getElementById('directXhttpLink').href = baseUrl + 'direct-xhttp.json?' + params;
            document.getElementById('proxyTcpLink').href = baseUrl + 'proxy-tcp.json?' + params;
            document.getElementById('proxyXhttpLink').href = baseUrl + 'proxy-xhttp.json?' + params;
            
            document.getElementById('singboxUrl').textContent = 
                window.location.origin + baseUrl + 'singbox.json?uuid=' + encodeURIComponent(uuid);
            
            document.getElementById('configs').classList.remove('hidden');
        });
    </script>
</body>
</html>
"""


@app.route("/sub/bridge/")
def bridge_page():
    return render_template_string(HTML_TEMPLATE)


@app.route("/sub/bridge/<path:filename>")
def serve_config(filename):
    if not filename.endswith(".json"):
        return "Not found", 404
    
    uuid = request.args.get("uuid", "").strip()
    if not uuid:
        return jsonify({"error": "UUID parameter is required"}), 400
    
    if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', uuid, re.IGNORECASE):
        return jsonify({"error": "Invalid UUID format. Expected: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"}), 400
    
    config = generate_config(filename, uuid)
    if config is None:
        return jsonify({"error": "Config template not found"}), 404
    
    return jsonify(config)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
