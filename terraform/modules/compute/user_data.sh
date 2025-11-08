#!/bin/bash
# GamePulse EC2 User Data Bootstrap Script
# Installs Docker CE, Docker Compose, and Tailscale on Ubuntu 24.04 LTS
# Executed once on instance launch

set -e  # Exit on any error
set -x  # Print commands for debugging (visible in /var/log/cloud-init-output.log)

# ============================================================================
# Update System Packages
# ============================================================================

echo "=== Updating apt package index ==="
apt-get update -y

# ============================================================================
# Install Prerequisites
# ============================================================================

echo "=== Installing prerequisites ==="
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# ============================================================================
# Add Docker GPG Key and Repository
# ============================================================================

echo "=== Adding Docker GPG key ==="
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "=== Adding Docker repository ==="
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# ============================================================================
# Install Docker
# ============================================================================

echo "=== Updating apt after adding Docker repository ==="
apt-get update -y

echo "=== Installing Docker CE and Docker Compose ==="
apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

# ============================================================================
# Configure Docker Permissions
# ============================================================================

echo "=== Adding ubuntu user to docker group ==="
usermod -aG docker ubuntu

# ============================================================================
# Enable and Start Docker Service
# ============================================================================

echo "=== Enabling Docker service ==="
systemctl enable docker

echo "=== Starting Docker service ==="
systemctl start docker

# ============================================================================
# Verify Installation
# ============================================================================

echo "=== Verifying Docker installation ==="
docker --version
docker compose version

# ============================================================================
# Configure Docker Daemon for Production
# ============================================================================

echo "=== Configuring Docker daemon for production ==="
cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true
}
EOF

systemctl restart docker

# ============================================================================
# Install Tailscale (Optional - requires auth key to connect)
# ============================================================================

echo "=== Installing Tailscale ==="
curl -fsSL https://tailscale.com/install.sh | sh

# Note: To connect to Tailscale network, run after SSH login:
# sudo tailscale up --authkey=<your-auth-key>
# Or set TAILSCALE_AUTHKEY environment variable before terraform apply

echo "=== Tailscale installed but not connected ==="
echo "To connect: sudo tailscale up --authkey=YOUR_KEY"
echo "Get auth key: https://login.tailscale.com/admin/settings/keys"

# ============================================================================
# Completion
# ============================================================================

echo "=== Bootstrap complete! ==="
echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker compose version)"
echo "Tailscale version: $(tailscale version)"
echo "Ubuntu user added to docker group (will take effect on next login)"
echo ""
echo "Next steps:"
echo "1. SSH to instance: ssh -i ~/.ssh/gamepulse-key.pem ubuntu@<PUBLIC_IP>"
echo "2. Connect to Tailscale: sudo tailscale up --authkey=YOUR_KEY"
echo "3. Verify: tailscale status"
