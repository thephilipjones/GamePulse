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
# Install AWS SSM Agent (for Session Manager access)
# ============================================================================

echo "=== Installing AWS SSM Agent via snap ==="
snap install amazon-ssm-agent --classic

echo "=== Enabling SSM Agent service ==="
systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service

echo "=== Starting SSM Agent service ==="
systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service

echo "=== Verifying SSM Agent status ==="
systemctl status snap.amazon-ssm-agent.amazon-ssm-agent.service --no-pager

# ============================================================================
# Install and Configure Tailscale (Automatic auth via Parameter Store)
# ============================================================================

echo "=== Installing Tailscale ==="
curl -fsSL https://tailscale.com/install.sh | sh

echo "=== Connecting to Tailscale network ==="

# Fetch Tailscale auth key from Parameter Store
TAILSCALE_AUTHKEY=$(aws ssm get-parameter \
  --name "/gamepulse/shared/infrastructure/tailscale_authkey" \
  --with-decryption \
  --region us-east-1 \
  --query 'Parameter.Value' \
  --output text 2>/dev/null)

if [ -n "$TAILSCALE_AUTHKEY" ] && [ "$TAILSCALE_AUTHKEY" != "PLACEHOLDER-UPDATE-VIA-AWS-CLI" ]; then
  echo "✅ Fetched Tailscale auth key from Parameter Store"

  # Connect to Tailscale with hostname
  if tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname=gamepulse-prod --ssh; then
    echo "✅ Connected to Tailscale network"
    tailscale status
  else
    echo "⚠️ Failed to connect to Tailscale"
  fi
else
  echo "⚠️ Tailscale auth key not found or is placeholder in Parameter Store"
  echo "To connect manually: sudo tailscale up --authkey=YOUR_KEY"
  echo ""
  echo "To enable automatic connection:"
  echo "1. Generate auth key: https://login.tailscale.com/admin/settings/keys"
  echo "2. Store in Parameter Store:"
  echo "   aws ssm put-parameter --name '/gamepulse/shared/infrastructure/tailscale_authkey' \\"
  echo "     --value 'YOUR_KEY' --type SecureString --overwrite"
fi

# ============================================================================
# Completion
# ============================================================================

echo "=== Bootstrap complete! ==="
echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker compose version)"
echo "SSM Agent status: $(systemctl is-active snap.amazon-ssm-agent.amazon-ssm-agent.service)"
echo "Tailscale version: $(tailscale version)"
echo "Tailscale status: $(tailscale status 2>/dev/null | head -n 1 || echo 'Not connected')"
echo "Ubuntu user added to docker group (will take effect on next login)"
echo ""
echo "Next steps:"
echo "1. SSH to instance: ssh -i ~/.ssh/gamepulse-key.pem ubuntu@<PUBLIC_IP>"
echo "   OR use SSM Session Manager: aws ssm start-session --target <INSTANCE_ID>"
echo "2. Clone repository: git clone https://github.com/PhilipTrauner/gamepulse.git /opt/gamepulse"
echo "3. Deploy application: cd /opt/gamepulse && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
