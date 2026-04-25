# Marzneshin Bridge VPS Setup

VLESS Reality panel with chain proxy (bridge) support for bypassing white lists.

## Features

- **Marzneshin Panel** - Upstream `dawsh/marzneshin:latest`
- **Marznode** - Upstream `dawsh/marznode:latest`
- **Xray Core** - VLESS Reality TCP/443 + optional XHTTP/8443
- **Bridge Support** - Chain proxy through purchased VLESS server
- **Dynamic Configs** - Personalized configs generated on-the-fly with user's UUID
- **Integrated UI** - Bridge page accessible from standard subscription page
- **Dual Subscriptions**:
  - Standard `/sub/<user>/<token>` via Marzneshin
  - Bridge `/sub/bridge/` with Xray + Sing-box configs
- **Custom Templates** - Support for custom landing page (place in `templates_for_script/custom/`)
- **No Hysteria2** - Clean setup without UDP protocols

## Installation

```bash
bash <(wget -qO- https://raw.githubusercontent.com/dimasavr2006/marzneshin-bridge-setup/main/vps-setup.sh)
```

## Installation Modes

1. **Full** - Marzneshin panel + Marznode + Caddy + Bridge Server
2. **Node only** - Marznode for remote panel + Bridge Server

## Bridge Configuration

During installation you can enable VLESS bridge:

1. Answer `y` to "Enable VLESS bridge?"
2. Paste your purchased VLESS link (`vless://...`)
3. Script will generate subscription configs automatically

### Updating Bridge Link (after installation)

```bash
cd /opt/marzneshin-vps-setup  # or /opt/marznode for node-only
./update_bridge.sh
```

## How It Works in Panel

### Standard Subscription Page
When users open their subscription link (`/sub/<user>/<token>`) in browser, they see:

1. **Standard Subscription** - Regular VLESS configs for direct connection
2. **Bridge Subscription** - Link to `/sub/bridge/` for chain proxy configs
3. **Instructions** - How to use both types of configs

### Bridge Subscription Page
At `https://your-domain.com/sub/bridge/`:

1. User pastes their UUID (from Marzneshin panel)
2. Clicks "Generate Configs"
3. Downloads personalized configs with their real UUID already inserted
4. Gets Sing-box subscription URL with UUID parameter

### Available Configs
- **Direct TCP** - Direct VLESS Reality TCP/443 (when lists are OFF)
- **Direct XHTTP** - Direct VLESS Reality XHTTP/8443 (when lists are OFF)
- **Proxy TCP** - Connection through bridge via TCP/443 (when lists are ON)
- **Proxy XHTTP** - Connection through bridge via XHTTP/8443 (when lists are ON)

## Architecture

```
Internet
    |
    v
[0.0.0.0:443] --- Xray VLESS Reality (TCP)
    |                -> dest: 127.0.0.1:4123 (Caddy selfsteal)
    |
[0.0.0.0:8443] --- Xray VLESS XHTTP (TCP, optional)
    |                -> dest: 127.0.0.1:4123
    |
[0.0.0.0:80] --- Caddy (HTTP/ACME)
    |
[127.0.0.1:4123] --- Caddy (internal TLS, selfsteal)
    |
[127.0.0.1:8000] --- Marzneshin Panel (full install)
    |
[127.0.0.1:53042] --- Marznode gRPC (local)
    |
[127.0.0.1:8080] --- Bridge Server (Flask)
    |                -> Dynamic config generation
    |                -> /sub/bridge/ HTML page
```

## Subscription Files

Generated automatically during installation:

```
subscriptions/
├── xray.json           # Xray config template (with {{USER_UUID}} placeholder)
├── singbox.json        # Sing-box config template
├── direct-tcp.json     # Direct TCP template
├── direct-xhttp.json   # Direct XHTTP template
├── proxy-tcp.json      # Proxy TCP template
├── proxy-xhttp.json    # Proxy XHTTP template
├── index.html          # Static bridge page (fallback)
└── bridge_config.json  # Parsed bridge parameters
```

**Note:** Users never see these template files directly. Bridge Server generates personalized configs on-the-fly.

## Client Setup

### Standard Subscription (always available)
- Copy `https://domain.com/sub/<user>/<token>` to v2rayNG/v2rayN/Streisand
- Works when white lists are OFF

### Bridge Subscription (for white lists)
1. Open `https://domain.com/sub/bridge/` (do this when lists are OFF!)
2. Copy your UUID from Marzneshin panel (Users → Your User → UUID)
3. Paste UUID and generate configs
4. Download Xray or Sing-box configs
5. Use "Proxy" configs when lists are ON
6. Use "Direct" configs when lists are OFF

### For Sing-box (automatic import)
- After generating configs on bridge page, copy the Sing-box URL
- Paste it into Sing-box app
- All 4 options will be available automatically

## Custom Landing Page

Place your custom HTML/CSS files in:
```
templates_for_script/custom/
├── index.html
├── style.css
└── ... (other assets)
```

If this directory exists and is not empty, it will be used instead of the default Confluence template.

## How Bridge Works

### Direct Connection (white lists OFF)
```
Client → Your Server (VLESS Reality) → Internet
```

### Bridge Connection (white lists ON)
```
Client → Purchased VLESS → Your Server → Internet
```

Your purchased VLESS acts only as a bridge. Internet exit is from YOUR server.

## Management Commands

```bash
# View logs
docker compose -f /opt/marzneshin-vps-setup/docker-compose.yml logs -f

# Restart all services
docker compose -f /opt/marzneshin-vps-setup/docker-compose.yml restart

# Stop
docker compose -f /opt/marzneshin-vps-setup/docker-compose.yml down

# Update bridge link
/opt/marzneshin-vps-setup/update_bridge.sh

# View bridge server logs
docker logs bridge-server
```

## Update Bridge Link

If you need to change the purchased VLESS server:

```bash
# Full installation
/opt/marzneshin-vps-setup/update_bridge.sh

# Node-only installation
/opt/marznode/update_bridge.sh
```

The script will:
1. Detect your installation
2. Ask for the new vless:// link
3. Regenerate all config templates
4. Restart bridge-server container

## Uninstall

```bash
bash <(wget -qO- https://raw.githubusercontent.com/dimasavr2006/marzneshin-bridge-setup/main/uninstall.sh)
```

## File Structure

```
marzneshin-bridge-setup/
├── vps-setup.sh                    # Main installation script
├── uninstall.sh                    # Uninstall script
├── update_bridge.sh                # Update bridge link
├── generate_subscription.py        # Config template generator
├── bridge_server.py                # Dynamic config server (Flask)
├── README.md
├── .gitignore
└── templates_for_script/
    ├── compose                     # Docker Compose (full)
    ├── compose_node                # Docker Compose (node)
    ├── marzneshin                  # Panel .env
    ├── xray                        # Xray config (full)
    ├── xray_node                   # Xray config (node)
    ├── xray_xhttp_inbound          # XHTTP inbound (full)
    ├── xray_node_xhttp_inbound     # XHTTP inbound (node)
    ├── caddy                       # Caddyfile (full)
    ├── caddy_node                  # Caddyfile (node)
    ├── confluence_page             # Default landing page
    ├── subscription/
    │   └── index.html              # Custom subscription page template
    └── custom/                     # Custom landing page directory
        └── README.md
```

## License

MIT