#!/usr/bin/env python3
"""
Bridge Subscription Generator for Marzneshin
Generates Xray and Sing-box configs with chain proxy (bridge) support
"""

import argparse
import json
import os
import re
import base64
import urllib.parse
from pathlib import Path


def parse_vless_link(link: str) -> dict:
    """Parse vless:// link and extract all parameters"""
    if not link.startswith("vless://"):
        raise ValueError("Link must start with vless://")
    
    # Remove vless:// prefix
    link = link[8:]
    
    # Split by @ to get uuid and the rest
    if "@" not in link:
        raise ValueError("Invalid vless link format: missing @")
    
    uuid, rest = link.split("@", 1)
    
    # Split address and query
    if "?" in rest:
        address_port, query = rest.split("?", 1)
    else:
        address_port = rest
        query = ""
    
    # Remove fragment if present
    if "#" in query:
        query, _ = query.split("#", 1)
    
    # Parse address and port
    if ":" in address_port:
        address, port_str = address_port.rsplit(":", 1)
        port = int(port_str)
    else:
        address = address_port
        port = 443
    
    # Parse query parameters
    params = urllib.parse.parse_qs(query)
    
    # Extract parameters with defaults
    result = {
        "uuid": uuid,
        "address": address,
        "port": port,
        "security": params.get("security", ["reality"])[0],
        "type": params.get("type", ["tcp"])[0],
        "flow": params.get("flow", [""])[0],
        "sni": params.get("sni", [""])[0],
        "fp": params.get("fp", ["chrome"])[0],
        "pbk": params.get("pbk", [""])[0],
        "sid": params.get("sid", [""])[0],
        "spx": params.get("spx", ["/"])[0],
        "path": params.get("path", [""])[0],
        "mode": params.get("mode", ["auto"])[0],
        "encryption": params.get("encryption", ["none"])[0],
    }
    
    return result


def create_xray_bridge_outbound(bridge: dict) -> dict:
    """Create Xray outbound for bridge (purchased VLESS)"""
    outbound = {
        "tag": "bridge",
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": bridge["address"],
                "port": bridge["port"],
                "users": [{
                    "id": bridge["uuid"],
                    "encryption": bridge["encryption"],
                    "flow": bridge["flow"] if bridge["flow"] else None,
                }]
            }]
        },
        "streamSettings": {
            "network": bridge["type"],
            "security": bridge["security"],
        }
    }
    
    # Remove None values
    if not outbound["settings"]["vnext"][0]["users"][0]["flow"]:
        del outbound["settings"]["vnext"][0]["users"][0]["flow"]
    
    # Configure security settings
    if bridge["security"] == "reality":
        outbound["streamSettings"]["realitySettings"] = {
            "show": False,
            "fingerprint": bridge["fp"],
            "serverName": bridge["sni"] if bridge["sni"] else bridge["address"],
            "publicKey": bridge["pbk"],
            "shortId": bridge["sid"],
            "spiderX": bridge["spx"],
        }
    elif bridge["security"] == "tls":
        outbound["streamSettings"]["tlsSettings"] = {
            "serverName": bridge["sni"] if bridge["sni"] else bridge["address"],
            "fingerprint": bridge["fp"],
        }
    
    # Configure transport
    if bridge["type"] == "tcp":
        pass  # TCP is default
    elif bridge["type"] == "xhttp":
        outbound["streamSettings"]["xhttpSettings"] = {
            "path": bridge["path"],
            "mode": bridge["mode"],
        }
    elif bridge["type"] == "ws":
        outbound["streamSettings"]["wsSettings"] = {
            "path": bridge["path"],
        }
    elif bridge["type"] == "grpc":
        outbound["streamSettings"]["grpcSettings"] = {
            "serviceName": bridge["path"].lstrip("/"),
        }
    
    return outbound


def create_xray_server_outbound(tag: str, server_domain: str, port: int, 
                                 protocol_type: str, pbk: str, sid: str,
                                 xhttp_path: str = "") -> dict:
    """Create Xray outbound for direct connection to user's server"""
    outbound = {
        "tag": tag,
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": server_domain,
                "port": port,
                "users": [{
                    "id": "{{USER_UUID}}",
                    "encryption": "none",
                    "flow": "xtls-rprx-vision"
                }]
            }]
        },
        "streamSettings": {
            "network": protocol_type,
            "security": "reality",
            "realitySettings": {
                "show": False,
                "fingerprint": "chrome",
                "serverName": server_domain,
                "publicKey": pbk,
                "shortId": sid,
                "spiderX": "/"
            }
        }
    }
    
    if protocol_type == "xhttp":
        outbound["streamSettings"]["xhttpSettings"] = {
            "path": xhttp_path,
            "mode": "auto"
        }
    
    return outbound


def create_sing_box_bridge_outbound(bridge: dict) -> dict:
    """Create Sing-box outbound for bridge (purchased VLESS)"""
    outbound = {
        "type": "vless",
        "tag": "bridge",
        "server": bridge["address"],
        "server_port": bridge["port"],
        "uuid": bridge["uuid"],
        "flow": bridge["flow"] if bridge["flow"] else "",
        "tls": {
            "enabled": bridge["security"] in ["tls", "reality"]
        }
    }
    
    if not outbound["flow"]:
        del outbound["flow"]
    
    # Configure TLS
    if bridge["security"] == "reality":
        outbound["tls"]["reality"] = {
            "enabled": True,
            "public_key": bridge["pbk"],
            "short_id": bridge["sid"]
        }
        outbound["tls"]["server_name"] = bridge["sni"] if bridge["sni"] else bridge["address"]
        outbound["tls"]["utls"] = {
            "enabled": True,
            "fingerprint": bridge["fp"]
        }
    elif bridge["security"] == "tls":
        outbound["tls"]["server_name"] = bridge["sni"] if bridge["sni"] else bridge["address"]
        outbound["tls"]["utls"] = {
            "enabled": True,
            "fingerprint": bridge["fp"]
        }
    
    # Configure transport
    if bridge["type"] == "xhttp":
        outbound["transport"] = {
            "type": "xhttp",
            "path": bridge["path"],
            "mode": bridge["mode"]
        }
    elif bridge["type"] == "ws":
        outbound["transport"] = {
            "type": "ws",
            "path": bridge["path"]
        }
    elif bridge["type"] == "grpc":
        outbound["transport"] = {
            "type": "grpc",
            "service_name": bridge["path"].lstrip("/")
        }
    
    return outbound


def create_sing_box_server_outbound(tag: str, server_domain: str, port: int,
                                    protocol_type: str, pbk: str, sid: str,
                                    xhttp_path: str = "") -> dict:
    """Create Sing-box outbound for direct connection to user's server"""
    outbound = {
        "type": "vless",
        "tag": tag,
        "server": server_domain,
        "server_port": port,
        "uuid": "{{USER_UUID}}",
        "flow": "xtls-rprx-vision",
        "tls": {
            "enabled": True,
            "reality": {
                "enabled": True,
                "public_key": pbk,
                "short_id": sid
            },
            "server_name": server_domain,
            "utls": {
                "enabled": True,
                "fingerprint": "chrome"
            }
        }
    }
    
    if protocol_type == "xhttp":
        outbound["transport"] = {
            "type": "xhttp",
            "path": xhttp_path,
            "mode": "auto"
        }
    
    return outbound


def generate_xray_full_config(bridge: dict, server_domain: str, 
                              pbk: str, sid: str, xhttp_path: str = "") -> dict:
    """Generate full Xray config with all 4 outbounds"""
    config = {
        "log": {"loglevel": "warning"},
        "outbounds": []
    }
    
    # Bridge outbound (first)
    config["outbounds"].append(create_xray_bridge_outbound(bridge))
    
    # Direct TCP outbound
    config["outbounds"].append(
        create_xray_server_outbound("direct-tcp", server_domain, 443, "tcp", pbk, sid)
    )
    
    # Direct XHTTP outbound (if path provided)
    if xhttp_path:
        config["outbounds"].append(
            create_xray_server_outbound("direct-xhttp", server_domain, 8443, "xhttp", pbk, sid, xhttp_path)
        )
    
    # Proxy TCP outbound (through bridge)
    proxy_tcp = create_xray_server_outbound("proxy-tcp", server_domain, 443, "tcp", pbk, sid)
    proxy_tcp["proxySettings"] = {
        "tag": "bridge",
        "transportLayer": True
    }
    config["outbounds"].append(proxy_tcp)
    
    # Proxy XHTTP outbound (through bridge, if path provided)
    if xhttp_path:
        proxy_xhttp = create_xray_server_outbound("proxy-xhttp", server_domain, 8443, "xhttp", pbk, sid, xhttp_path)
        proxy_xhttp["proxySettings"] = {
            "tag": "bridge",
            "transportLayer": True
        }
        config["outbounds"].append(proxy_xhttp)
    
    return config


def generate_sing_box_full_config(bridge: dict, server_domain: str,
                                  pbk: str, sid: str, xhttp_path: str = "") -> dict:
    """Generate full Sing-box config with all 4 outbounds"""
    config = {
        "log": {"level": "warn"},
        "outbounds": []
    }
    
    # Bridge outbound (first)
    config["outbounds"].append(create_sing_box_bridge_outbound(bridge))
    
    # Direct TCP outbound
    config["outbounds"].append(
        create_sing_box_server_outbound("direct-tcp", server_domain, 443, "tcp", pbk, sid)
    )
    
    # Direct XHTTP outbound (if path provided)
    if xhttp_path:
        config["outbounds"].append(
            create_sing_box_server_outbound("direct-xhttp", server_domain, 8443, "xhttp", pbk, sid, xhttp_path)
        )
    
    # Proxy TCP outbound (through bridge)
    proxy_tcp = create_sing_box_server_outbound("proxy-tcp", server_domain, 443, "tcp", pbk, sid)
    proxy_tcp["detour"] = "bridge"
    config["outbounds"].append(proxy_tcp)
    
    # Proxy XHTTP outbound (through bridge, if path provided)
    if xhttp_path:
        proxy_xhttp = create_sing_box_server_outbound("proxy-xhttp", server_domain, 8443, "xhttp", pbk, sid, xhttp_path)
        proxy_xhttp["detour"] = "bridge"
        config["outbounds"].append(proxy_xhttp)
    
    return config


def generate_individual_configs(bridge: dict, server_domain: str,
                                pbk: str, sid: str, xhttp_path: str = "") -> dict:
    """Generate individual JSON configs for each connection type"""
    configs = {}
    
    # Direct TCP
    configs["direct-tcp"] = {
        "outbounds": [create_xray_server_outbound("direct-tcp", server_domain, 443, "tcp", pbk, sid)]
    }
    
    # Proxy TCP
    proxy_tcp = create_xray_server_outbound("proxy-tcp", server_domain, 443, "tcp", pbk, sid)
    proxy_tcp["proxySettings"] = {"tag": "bridge", "transportLayer": True}
    configs["proxy-tcp"] = {
        "outbounds": [
            create_xray_bridge_outbound(bridge),
            proxy_tcp
        ]
    }
    
    if xhttp_path:
        # Direct XHTTP
        configs["direct-xhttp"] = {
            "outbounds": [create_xray_server_outbound("direct-xhttp", server_domain, 8443, "xhttp", pbk, sid, xhttp_path)]
        }
        
        # Proxy XHTTP
        proxy_xhttp = create_xray_server_outbound("proxy-xhttp", server_domain, 8443, "xhttp", pbk, sid, xhttp_path)
        proxy_xhttp["proxySettings"] = {"tag": "bridge", "transportLayer": True}
        configs["proxy-xhttp"] = {
            "outbounds": [
                create_xray_bridge_outbound(bridge),
                proxy_xhttp
            ]
        }
    
    return configs


def generate_qr_code(data: str) -> str:
    """Generate base64 encoded QR code SVG"""
    import subprocess
    try:
        result = subprocess.run(
            ["qrencode", "-t", "SVG", "-o", "-", data],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return base64.b64encode(result.stdout.encode()).decode()
    except:
        pass
    return ""


def generate_html_page(domain: str, has_xhttp: bool) -> str:
    """Generate HTML page with all subscription options"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bridge Subscription - {domain}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{ color: #333; margin-bottom: 10px; text-align: center; }}
        .subtitle {{ color: #666; text-align: center; margin-bottom: 30px; }}
        .warning {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 30px;
            color: #856404;
        }}
        .section {{ margin-bottom: 40px; }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 2px solid #e9ecef;
            transition: transform 0.2s, border-color 0.2s;
        }}
        .card:hover {{
            transform: translateY(-5px);
            border-color: #667eea;
        }}
        .card h3 {{ color: #667eea; margin-bottom: 10px; }}
        .card p {{ color: #666; font-size: 14px; margin-bottom: 15px; }}
        .btn {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 14px;
            transition: background 0.2s;
        }}
        .btn:hover {{ background: #5568d3; }}
        .qr-code {{
            width: 200px;
            height: 200px;
            margin: 15px auto;
            background: white;
            padding: 10px;
            border-radius: 8px;
        }}
        .info-box {{
            background: #e7f3ff;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}
        .info-box h4 {{ color: #667eea; margin-bottom: 8px; }}
        .info-box ul {{ margin-left: 20px; color: #555; }}
        .info-box li {{ margin-bottom: 5px; }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        .full-config {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            overflow-x: auto;
        }}
        .full-config a {{
            color: #66d9ef;
            text-decoration: none;
        }}
        .full-config a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Bridge Subscription</h1>
        <p class="subtitle">{domain}</p>
        
        <div class="warning">
            <strong>Attention:</strong> Access this page when white lists are OFF to save configs. 
            When lists are ON, use the saved configs.
        </div>
        
        <div class="section">
            <h2>Quick Links</h2>
            <div class="full-config">
                <p><strong>Standard Subscription:</strong> <code>https://{domain}/sub/&lt;user&gt;/&lt;token&gt;</code></p>
                <p style="margin-top: 10px;"><strong>Full Xray Config:</strong> <a href="xray.json" download>Download xray.json</a></p>
                <p><strong>Full Sing-box Config:</strong> <a href="singbox.json" download>Download singbox.json</a></p>
            </div>
        </div>
        
        <div class="section">
            <h2>Connection Options</h2>
            <div class="cards">
                <div class="card">
                    <h3>Direct TCP</h3>
                    <p>Direct connection to your server via VLESS Reality TCP/443</p>
                    <a href="direct-tcp.json" download class="btn">Download JSON</a>
                </div>
                {'<div class="card">\n                    <h3>Direct XHTTP</h3>\n                    <p>Direct connection to your server via VLESS Reality XHTTP/8443</p>\n                    <a href="direct-xhttp.json" download class="btn">Download JSON</a>\n                </div>' if has_xhttp else ''}
                <div class="card">
                    <h3>Proxy TCP</h3>
                    <p>Connection through purchased VLESS bridge via TCP/443</p>
                    <a href="proxy-tcp.json" download class="btn">Download JSON</a>
                </div>
                {'<div class="card">\n                    <h3>Proxy XHTTP</h3>\n                    <p>Connection through purchased VLESS bridge via XHTTP/8443</p>\n                    <a href="proxy-xhttp.json" download class="btn">Download JSON</a>\n                </div>' if has_xhttp else ''}
            </div>
        </div>
        
        <div class="section">
            <h2>Instructions</h2>
            <div class="info-box">
                <h4>For Xray Clients (v2rayNG, v2rayN, Streisand):</h4>
                <ul>
                    <li>Download <code>xray.json</code> or individual config</li>
                    <li>Replace <code>{{USER_UUID}}</code> with your UUID from the panel</li>
                    <li>Import into your Xray client</li>
                    <li>Select <strong>Proxy TCP</strong> or <strong>Proxy XHTTP</strong> when lists are on</li>
                    <li>Select <strong>Direct TCP</strong> or <strong>Direct XHTTP</strong> when lists are off</li>
                </ul>
            </div>
            <div class="info-box">
                <h4>For Sing-box:</h4>
                <ul>
                    <li>Use subscription URL: <code>https://{domain}/sub/bridge/singbox.json</code></li>
                    <li>Or download <code>singbox.json</code> and replace <code>{{USER_UUID}}</code></li>
                    <li>All 4 options will be available automatically</li>
                </ul>
            </div>
        </div>
        
        <div class="section">
            <h2>Traffic Flow</h2>
            <div class="info-box">
                <h4>When white lists are OFF:</h4>
                <ul>
                    <li><strong>Direct:</strong> Client → Your Server → Internet</li>
                </ul>
            </div>
            <div class="info-box">
                <h4>When white lists are ON:</h4>
                <ul>
                    <li><strong>Proxy:</strong> Client → Purchased VLESS → Your Server → Internet</li>
                    <li>Your purchased VLESS acts only as a bridge</li>
                    <li>Internet exit is from YOUR server, not the purchased one</li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Generate bridge subscription configs")
    parser.add_argument("--bridge-link", required=True, help="vless:// link for purchased VLESS")
    parser.add_argument("--server-config", required=True, help="Path to server xray_config.json")
    parser.add_argument("--domain", required=True, help="Server domain")
    parser.add_argument("--output-dir", required=True, help="Output directory for configs")
    parser.add_argument("--pbk", required=True, help="Reality public key")
    parser.add_argument("--sid", required=True, help="Reality short ID")
    
    args = parser.parse_args()
    
    # Parse bridge link
    try:
        bridge = parse_vless_link(args.bridge_link)
    except Exception as e:
        print(f"ERROR: Failed to parse bridge link: {e}")
        exit(1)
    
    # Save bridge config for reference
    bridge_config = {
        "enabled": True,
        "link": args.bridge_link,
        "parsed": bridge
    }
    
    # Read server config to check for XHTTP
    xhttp_path = ""
    try:
        with open(args.server_config, 'r') as f:
            server_config = json.load(f)
        
        for inbound in server_config.get("inbounds", []):
            if inbound.get("tag") == "VLESS-XHTTP-Reality":
                xhttp_path = inbound.get("streamSettings", {}).get("xhttpSettings", {}).get("path", "")
                break
    except Exception as e:
        print(f"Warning: Could not read server config: {e}")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Save bridge config
    with open(os.path.join(args.output_dir, "bridge_config.json"), 'w') as f:
        json.dump(bridge_config, f, indent=2)
    
    # Generate full Xray config
    xray_config = generate_xray_full_config(bridge, args.domain, args.pbk, args.sid, xhttp_path)
    with open(os.path.join(args.output_dir, "xray.json"), 'w') as f:
        json.dump(xray_config, f, indent=2)
    
    # Generate full Sing-box config
    singbox_config = generate_sing_box_full_config(bridge, args.domain, args.pbk, args.sid, xhttp_path)
    with open(os.path.join(args.output_dir, "singbox.json"), 'w') as f:
        json.dump(singbox_config, f, indent=2)
    
    # Generate individual configs
    individual_configs = generate_individual_configs(bridge, args.domain, args.pbk, args.sid, xhttp_path)
    for name, config in individual_configs.items():
        with open(os.path.join(args.output_dir, f"{name}.json"), 'w') as f:
            json.dump(config, f, indent=2)
    
    # Generate HTML page
    html = generate_html_page(args.domain, bool(xhttp_path))
    with open(os.path.join(args.output_dir, "index.html"), 'w') as f:
        f.write(html)
    
    print(f"Bridge subscription files generated in {args.output_dir}")
    print("Files:")
    for f in os.listdir(args.output_dir):
        print(f"  - {f}")


if __name__ == "__main__":
    main()
