#!/bin/bash

set -e

# Script to update bridge configuration after installation
# Usage: ./update_bridge.sh

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Detect installation type
FULL_INSTALL=false
NODE_INSTALL=false

if [ -d "/opt/marzneshin-vps-setup" ] && [ -f "/opt/marzneshin-vps-setup/docker-compose.yml" ]; then
  FULL_INSTALL=true
  INSTALL_DIR="/opt/marzneshin-vps-setup"
  echo_info "Detected: Full installation"
fi

if [ -d "/opt/marznode" ] && [ -f "/opt/marznode/docker-compose.yml" ]; then
  NODE_INSTALL=true
  INSTALL_DIR="/opt/marznode"
  echo_info "Detected: Node-only installation"
fi

if [ "$FULL_INSTALL" = false ] && [ "$NODE_INSTALL" = false ]; then
  echo_error "No installation detected."
  echo "Expected directories:"
  echo "  - /opt/marzneshin-vps-setup (full installation)"
  echo "  - /opt/marznode (node-only installation)"
  exit 1
fi

# Check if bridge was previously enabled
if [ ! -f "$INSTALL_DIR/subscriptions/bridge_config.json" ]; then
  echo_warn "Bridge was not previously enabled for this installation."
  read -ep "Do you want to enable bridge now? [y/N]: " enable_bridge
  if [[ ! "${enable_bridge,,}" == "y" ]]; then
    echo "Aborted."
    exit 0
  fi
fi

echo ""
echo "=============================================="
echo "       Update Bridge Configuration"
echo "=============================================="
echo ""

# Get new bridge link
echo "Enter the new vless:// link for your purchased VLESS server:"
read -ep "> " bridge_link

# Validate vless link
if [[ ! "$bridge_link" =~ ^vless:// ]]; then
  echo_error "Invalid vless link format. Must start with vless://"
  exit 1
fi

# Get domain from installation
if [ "$FULL_INSTALL" = true ]; then
  DOMAIN=$(grep "SUBSCRIPTION_URL_PREFIX" "$INSTALL_DIR/marzneshin/.env" | cut -d'=' -f2 | sed 's|https://||')
  SERVER_CONFIG="$INSTALL_DIR/marznode_data/xray_config.json"
else
  # For node installation, we need to get domain from Caddyfile or user input
  if [ -f "$INSTALL_DIR/caddy/Caddyfile" ]; then
    DOMAIN=$(grep "https://" "$INSTALL_DIR/caddy/Caddyfile" | head -1 | sed 's|https://||' | sed 's| {||')
  fi
  
  if [ -z "$DOMAIN" ]; then
    read -ep "Enter your domain: " DOMAIN
  fi
  SERVER_CONFIG="$INSTALL_DIR/marznode_data/xray_config.json"
fi

# Get Xray parameters
if [ -f "$SERVER_CONFIG" ]; then
  PBK=$(jq -r '.inbounds[0].streamSettings.realitySettings.publicKey' "$SERVER_CONFIG" 2>/dev/null || echo "")
  SID=$(jq -r '.inbounds[0].streamSettings.realitySettings.shortIds[0]' "$SERVER_CONFIG" 2>/dev/null || echo "")
fi

if [ -z "$PBK" ] || [ "$PBK" == "null" ]; then
  echo_warn "Could not detect Reality Public Key from config."
  read -ep "Enter Reality Public Key: " PBK
fi

if [ -z "$SID" ] || [ "$SID" == "null" ]; then
  echo_warn "Could not detect Reality Short ID from config."
  read -ep "Enter Reality Short ID: " SID
fi

echo ""
echo_info "Updating bridge configuration..."

# Download latest generate_subscription.py
DOWNLOAD_URL="https://raw.githubusercontent.com/dimasavr2006/bridge-subscription-server/main/generate_subscription.py"
echo_info "Downloading latest subscription generator..."
wget -qO generate_subscription.py "$DOWNLOAD_URL"
chmod +x generate_subscription.py

# Regenerate configs
python3 generate_subscription.py \
  --bridge-link "$bridge_link" \
  --server-config "$SERVER_CONFIG" \
  --domain "$DOMAIN" \
  --output-dir "$INSTALL_DIR/subscriptions" \
  --pbk "$PBK" \
  --sid "$SID"

# Cleanup
rm -f generate_subscription.py

echo_info "Bridge configuration updated!"

# Restart bridge-server if running
if docker ps --format '{{.Names}}' | grep -q "^bridge-server$"; then
  echo_info "Restarting bridge-server container..."
  docker restart bridge-server
fi

echo ""
echo "=============================================="
echo "       Bridge Update Complete"
echo "=============================================="
echo ""
echo "Bridge: Managed via Dashboard -> Proxy Pool"
echo ""
echo ""
echo "=============================================="