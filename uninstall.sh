#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Remove container only if it is clearly related to Marzneshin paths/labels.
remove_if_marz_related() {
  local container_name="$1"
  local mounts
  local labels

  if ! docker ps -a --format '{{.Names}}' | grep -qx "$container_name"; then
    return 0
  fi

  mounts="$(docker inspect -f '{{range .Mounts}}{{println .Source}}{{end}}' "$container_name" 2>/dev/null || true)"
  labels="$(docker inspect -f '{{json .Config.Labels}}' "$container_name" 2>/dev/null || true)"

  if echo "$mounts" | grep -Eq '^/opt/marzneshin-vps-setup/|^/opt/marznode/|^/etc/opt/marzneshin/|^/var/lib/marzneshin|^/var/lib/marznode'; then
    echo_info "Removing leftover container: $container_name"
    docker rm -f "$container_name" 2>/dev/null || true
    return 0
  fi

  if echo "$labels" | grep -q '"com.docker.compose.project":"marzneshin"'; then
    echo_info "Removing leftover container: $container_name"
    docker rm -f "$container_name" 2>/dev/null || true
    return 0
  fi

  echo_warn "Skipping container '$container_name' (not clearly related to Marzneshin)."
}

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then
  echo_error "Please run as root"
  exit 1
fi

echo ""
echo "=============================================="
echo "       Marzneshin Bridge VPS Uninstall Script"
echo "=============================================="
echo ""

# Defaults for summary
remove_docker="n"
reset_ufw="n"
remove_images="n"
remove_legacy_data="n"

# Detect installation type
FULL_INSTALL=false
NODE_INSTALL=false
LEGACY_STACK=false

if [ -d "/opt/marzneshin-vps-setup" ]; then
  FULL_INSTALL=true
  echo_info "Detected: Full installation (Panel + Node)"
fi

if [ -d "/opt/marznode" ]; then
  NODE_INSTALL=true
  echo_info "Detected: Node-only installation"
fi

if [ -f "/etc/opt/marzneshin/docker-compose.yml" ]; then
  LEGACY_STACK=true
  echo_info "Detected: Legacy Marzneshin compose stack (/etc/opt/marzneshin)"
fi

if [ "$FULL_INSTALL" = false ] && [ "$NODE_INSTALL" = false ] && [ "$LEGACY_STACK" = false ]; then
  echo_warn "No Marzneshin installation detected."
  echo "Expected directories:"
  echo "  - /opt/marzneshin-vps-setup (full installation)"
  echo "  - /opt/marznode (node-only installation)"
  echo "  - /etc/opt/marzneshin (legacy compose stack)"
  read -ep "Continue anyway to clean up other components? [y/N]: " continue_anyway
  if [[ ! "${continue_anyway,,}" == "y" ]]; then
    exit 0
  fi
fi

echo ""
echo "This script will remove:"
echo "  - Docker compose stacks from this setup only (/opt/marzneshin-vps-setup, /opt/marznode)"
echo "  - Installation directories and all panel data"
echo "  - Optional cleanup (images/UFW/Docker) only if you confirm it"
echo ""
echo -e "${RED}WARNING: This will delete all VPN user data and configurations!${NC}"
echo ""
read -ep "Are you sure you want to continue? [y/N]: " confirm
if [[ ! "${confirm,,}" == "y" ]]; then
  echo "Aborted."
  exit 0
fi

#####################################
# Stop and remove Docker containers
#####################################
echo ""
if command -v docker &> /dev/null; then
  echo_info "Stopping Docker containers..."

  if [ "$FULL_INSTALL" = true ]; then
    if [ -f "/opt/marzneshin-vps-setup/docker-compose.yml" ]; then
      docker compose -f /opt/marzneshin-vps-setup/docker-compose.yml down --volumes --remove-orphans 2>/dev/null || true
    fi
  fi

  if [ "$NODE_INSTALL" = true ]; then
    if [ -f "/opt/marznode/docker-compose.yml" ]; then
      docker compose -f /opt/marznode/docker-compose.yml down --volumes --remove-orphans 2>/dev/null || true
    fi
  fi

  if [ "$LEGACY_STACK" = true ]; then
    docker compose -f /etc/opt/marzneshin/docker-compose.yml down --volumes --remove-orphans 2>/dev/null || true
  fi

  # Safety fallback: remove leftovers from marzneshin compose project
  while IFS= read -r leftover; do
    [ -n "$leftover" ] && docker rm -f "$leftover" 2>/dev/null || true
  done < <(docker ps -a --filter label=com.docker.compose.project=marzneshin --format '{{.Names}}')

  # Explicitly handle standalone caddy/bridge-server leftovers if mounted from marz paths
  remove_if_marz_related "caddy"
  remove_if_marz_related "bridge-server"

  read -ep "Also remove Marzneshin-related Docker images? [y/N]: " remove_images
  if [[ "${remove_images,,}" == "y" ]]; then
    echo_info "Removing known Marzneshin images..."
    docker rmi dimasavr/marzneshin-aggregator:main 2>/dev/null || true
    docker rmi dimasavr/marzneshin-aggregator:latest 2>/dev/null || true
    docker rmi dawsh/marzneshin:latest 2>/dev/null || true
    docker rmi dawsh/marznode:latest 2>/dev/null || true
    docker rmi caddy:2.9 2>/dev/null || true
    docker rmi caddy:latest 2>/dev/null || true
    docker rmi python:3.11-slim 2>/dev/null || true
    docker rmi marzneshin-marzneshin 2>/dev/null || true
  else
    echo_info "Docker images kept."
  fi
else
  echo_warn "Docker is not installed, skipping container/image cleanup."
fi

#####################################
# Remove installation directories
#####################################
echo ""
echo_info "Removing installation directories..."

if [ -d "/opt/marzneshin-vps-setup" ]; then
  rm -rf /opt/marzneshin-vps-setup
  echo_info "Removed /opt/marzneshin-vps-setup"
fi

if [ -d "/opt/marznode" ]; then
  rm -rf /opt/marznode
  echo_info "Removed /opt/marznode"
fi

if [ -d "/etc/opt/marzneshin" ]; then
  rm -rf /etc/opt/marzneshin
  echo_info "Removed /etc/opt/marzneshin"
fi

if [ "$LEGACY_STACK" = true ]; then
  read -ep "Remove legacy runtime data dirs (/var/lib/marzneshin, /var/lib/marznode)? [y/N]: " remove_legacy_data
  if [[ "${remove_legacy_data,,}" == "y" ]]; then
    rm -rf /var/lib/marzneshin
    rm -rf /var/lib/marznode
    echo_info "Removed /var/lib/marzneshin and /var/lib/marznode"
  fi
fi

#####################################
# Reset UFW
#####################################
echo ""
if command -v ufw &> /dev/null; then
  read -ep "Reset UFW firewall rules? [y/N]: " reset_ufw
  if [[ "${reset_ufw,,}" == "y" ]]; then
    echo_info "Resetting UFW..."
    ufw --force reset
    ufw disable
    echo_info "UFW reset and disabled"
  fi
fi

#####################################
# Ask about Docker
#####################################
echo ""
read -ep "Remove Docker completely? [y/N]: " remove_docker
if [[ "${remove_docker,,}" == "y" ]]; then
  echo_info "Removing Docker..."

  # Stop Docker service
  systemctl stop docker 2>/dev/null || true
  systemctl stop docker.socket 2>/dev/null || true

  # Remove Docker packages
  apt remove --purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-ce-rootless-extras docker-compose 2>/dev/null || true
  apt autoremove -y 2>/dev/null || true

  # Remove Docker data
  rm -rf /var/lib/docker
  rm -rf /var/lib/containerd
  rm -rf /etc/docker
  rm -f /etc/apt/sources.list.d/docker.list
  rm -f /etc/apt/keyrings/docker.gpg
  rm -f /etc/apt/keyrings/docker.asc

  echo_info "Docker removed"
else
  echo_info "Docker kept. You can prune unused data with: docker system prune -a"
fi

#####################################
# Cleanup
#####################################
echo ""
echo_info "System package cleanup skipped."

echo ""
echo "=============================================="
echo "       Uninstallation Complete"
echo "=============================================="
echo ""
echo "Removed components:"
[ "$FULL_INSTALL" = true ] && echo "  - Marzneshin panel installation"
[ "$NODE_INSTALL" = true ] && echo "  - Marznode installation"
[ "$LEGACY_STACK" = true ] && echo "  - Legacy compose stack (/etc/opt/marzneshin)"
echo "  - Docker containers from detected Marzneshin compose stacks"
[[ "${remove_images,,}" == "y" ]] && echo "  - Marzneshin Docker images"
[[ "${remove_legacy_data,,}" == "y" ]] && echo "  - Legacy runtime data dirs in /var/lib"
[[ "${remove_docker,,}" == "y" ]] && echo "  - Docker"
[[ "${reset_ufw,,}" == "y" ]] && echo "  - UFW rules (reset)"
echo ""
echo "=============================================="
