# Marzneshin Aggregator VPS Setup

VLESS Reality panel with integrated Proxy Aggregator (bridge + external VPN support).

## Features

- **Marzneshin Aggregator Panel** - Fork with built-in proxy aggregation
- **Marznode** - Upstream `dawsh/marznode:latest`
- **Xray Core** - VLESS Reality TCP/443 + optional XHTTP/8443
- **Bridge Support** - Chain proxy through purchased VLESS server (client-side)
- **External VPN** - Aggregate external subscriptions (base64, Clash YAML)
- **Multi-Format Subscriptions** - Xray JSON, Sing-box JSON, Clash YAML, Base64 links, HTML page
- **Speedtest** - Automatic latency testing with 15-min cache
- **Admin UI** - Manage bridge servers and external subscriptions via dashboard
- **Custom Templates** - Support for custom landing page (place in `templates_for_script/custom/`)

## What's New (vs old bridge setup)

- **No separate bridge server** - Everything is integrated into Marzneshin panel
- **Admin UI** - Add/manage bridge servers and external subscriptions via web dashboard
- **External VPN support** - Subscribe to external VPN providers and include in user subscriptions
- **Speedtest** - Automatic latency measurement for all proxy pool servers
- **Sing-box/Xray/Clash** - All formats supported natively
- **Routing modes** - direct / via_node / both for each subscription

## Installation

```bash
bash <(wget -qO- https://raw.githubusercontent.com/dimasavr2006/marzneshin-bridge-setup/master/vps-setup.sh)
```

## Installation Modes

1. **Full** - Marzneshin panel + Marznode + Caddy
2. **Node only** - Marznode for remote panel

## Bridge Configuration

After installation, bridge is configured through the Admin Dashboard:

1. Open Dashboard → Proxy Pool
2. Click "Add Subscription"
3. Enter name and vless:// link for your purchased server
4. Select category: "bridge"
5. Choose routing mode: direct / via_node / both

### External VPN Configuration

1. In Proxy Pool, click "Add Subscription"
2. Enter subscription URL (base64 or Clash YAML)
3. Select category: "external"
4. Choose routing mode
5. Click "Sync" to fetch servers

## How It Works

### User Subscription (`/sub/<user>/<token>`)
User gets ALL variants in one subscription:

```
[DIRECT] Your Servers
  - VLESS TCP/443
  - VLESS XHTTP/8443

[BRIDGE] Bridge Servers  
  - Bridge via Server A
  - Bridge via Server B

[EXTERNAL] External VPN
  - External VPN A (direct)
  - External VPN A (via node)
```

### Subscription Formats
- **Auto-detect** - By User-Agent header
- **HTML** - `/sub/<user>/<token>/html` - QR codes + grouped links
- **Xray JSON** - `/sub/<user>/<token>/xray`
- **Sing-box JSON** - `/sub/<user>/<token>/sing-box`
- **Clash YAML** - `/sub/<user>/<token>/clash`
- **Base64 Links** - `/sub/<user>/<token>/links`

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
[127.0.0.1:8000] --- Marzneshin Aggregator Panel
    |                -> Integrated proxy pool
    |                -> Multi-format subscriptions
    |                -> Speedtest engine
    |
[127.0.0.1:53042] --- Marznode gRPC (local)
```

## Chain Proxy (Bridge)

### Direct Connection (white lists OFF)
```
Client → Your Server (VLESS Reality) → Internet
```

### Bridge Connection (white lists ON)
```
Client → Purchased VLESS → Your Server → Internet
```

Purchased VLESS acts only as a bridge. Internet exit is from YOUR server.

**Implementation:** Client-side via `proxySettings` (Xray) or `detour` (Sing-box)

## Client Setup

### Standard Subscription
- Copy `https://domain.com/sub/<user>/<token>` to v2rayNG/v2rayN/Streisand
- Works when white lists are OFF

### Bridge Subscription (for white lists)
1. Use the same subscription link
2. In client, select configs tagged with "🌉 [Bridge]"
3. These configs route through your purchased VLESS first

### For Sing-box
- Use `/sub/<user>/<token>/sing-box`
- All variants available automatically with proper detour settings

## Management Commands

```bash
# View logs
docker compose -f /opt/marzneshin-vps-setup/docker-compose.yml logs -f

# Restart all services
docker compose -f /opt/marzneshin-vps-setup/docker-compose.yml restart

# Stop
docker compose -f /opt/marzneshin-vps-setup/docker-compose.yml down
```

## Uninstall

```bash
bash <(wget -qO- https://raw.githubusercontent.com/dimasavr2006/marzneshin-bridge-setup/main/uninstall.sh)
```

## File Structure

```
marzneshin-bridge-setup/
├── vps-setup.sh                    # Main installation script
├── uninstall.sh                    # Uninstall script
├── update_bridge.sh                # DEPRECATED - use Dashboard UI
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
    └── custom/                     # Custom landing page directory
```

## License

MIT
