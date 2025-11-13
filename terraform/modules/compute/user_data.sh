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
# Configure Swap Space (4GB for t2.micro memory support)
# ============================================================================

echo "=== Configuring swap space ==="

# Check if swap already exists and is enabled
if swapon --show | grep -q '/swapfile'; then
  echo "ℹ️ Swap file already exists and is enabled"
else
  if [ -f /swapfile ]; then
    echo "⚠️ /swapfile exists but not enabled - enabling..."
    swapon /swapfile
  else
    echo "Creating 4GB swap file..."

    # Use fallocate for fast allocation
    fallocate -l 4G /swapfile

    # Secure permissions (root only)
    chmod 600 /swapfile

    # Setup swap area
    mkswap /swapfile

    # Enable swap
    swapon /swapfile

    # Make persistent across reboots
    if ! grep -q '/swapfile' /etc/fstab; then
      echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi

    echo "✅ 4GB swap file created and enabled"
  fi
fi

# Optimize swappiness for server workloads (default is 60, lower = less swapping)
# Set to 10 for better performance (only swap when necessary)
if ! grep -q 'vm.swappiness' /etc/sysctl.conf; then
  echo 'vm.swappiness=10' >> /etc/sysctl.conf
  sysctl -w vm.swappiness=10
  echo "✅ Set vm.swappiness=10 for optimized server performance"
else
  echo "ℹ️ vm.swappiness already configured"
fi

# Display current swap status
echo "Current swap status:"
swapon --show
free -h

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
# Install AWS CLI v2
# ============================================================================

echo "=== Installing AWS CLI v2 ==="
apt-get install -y unzip
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"
unzip -q /tmp/awscliv2.zip -d /tmp
/tmp/aws/install
rm -rf /tmp/aws /tmp/awscliv2.zip

echo "=== Verifying AWS CLI installation ==="
aws --version

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
# Prepare Application Deployment Directory
# ============================================================================

echo "=== Creating application deployment directory ==="
mkdir -p /opt/gamepulse
chown ubuntu:ubuntu /opt/gamepulse
echo "✅ Created /opt/gamepulse with ubuntu:ubuntu ownership"

# ============================================================================
# Clone Application Repository
# ============================================================================

echo "=== Cloning application repository ==="
su - ubuntu -c 'git clone https://github.com/thephilipjones/GamePulse.git /opt/gamepulse 2>/dev/null || echo "Repository already cloned"'

if [ -d "/opt/gamepulse/.git" ]; then
  echo "✅ Repository cloned successfully"
  cd /opt/gamepulse
  echo "Current branch: $(git branch --show-current)"
  echo "Latest commit: $(git log -1 --oneline)"
else
  echo "⚠️ Repository clone skipped or failed"
fi

# ============================================================================
# Generate Environment File from Parameter Store
# ============================================================================

echo "=== Generating .env file from Parameter Store ==="
if [ -f "/opt/gamepulse/backend/scripts/load-secrets.sh" ]; then
  cd /opt/gamepulse
  su - ubuntu -c "cd /opt/gamepulse && bash backend/scripts/load-secrets.sh production .env 2>&1" > /var/log/load-secrets.log

  if [ -f "/opt/gamepulse/.env" ]; then
    echo "✅ Environment file generated successfully"
    chown ubuntu:ubuntu /opt/gamepulse/.env
    chmod 600 /opt/gamepulse/.env
  else
    echo "⚠️ Failed to generate .env file - check /var/log/load-secrets.log"
    echo "Secrets must be populated in Parameter Store before deployment"
  fi
else
  echo "⚠️ load-secrets.sh script not found - .env must be created manually"
fi

# ============================================================================
# Create Docker External Network
# ============================================================================

echo "=== Creating Traefik external network ==="
docker network create traefik-public 2>/dev/null && echo "✅ Network created" || echo "ℹ️ Network already exists"

# ============================================================================
# Completion
# ============================================================================

echo "=== Bootstrap complete! ==="
echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker compose version)"
echo "AWS CLI version: $(aws --version 2>&1 | head -1)"
echo "SSM Agent status: $(systemctl is-active snap.amazon-ssm-agent.amazon-ssm-agent.service)"
echo "Tailscale version: $(tailscale version)"
echo "Tailscale status: $(tailscale status 2>/dev/null | head -n 1 || echo 'Not connected')"
echo "Swap status: $(swapon --show | grep -c '/swapfile' || echo '0') swap file(s) active"
echo "Ubuntu user added to docker group (will take effect on next login)"
echo ""
echo "Application setup:"
if [ -d "/opt/gamepulse/.git" ]; then
  echo "✅ Repository cloned to /opt/gamepulse"
  echo "✅ Directory owned by ubuntu:ubuntu"
  if [ -f "/opt/gamepulse/.env" ]; then
    echo "✅ Environment file generated from Parameter Store"
    echo ""
    echo "Ready to deploy! Run:"
    echo "  cd /opt/gamepulse"
    echo "  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
  else
    echo "⚠️ Environment file not created - populate Parameter Store secrets"
    echo "  Then run: bash backend/scripts/load-secrets.sh production .env"
  fi
else
  echo "⚠️ Repository not cloned - manual setup required"
  echo ""
  echo "Manual setup steps:"
  echo "1. SSH: ssh -i ~/.ssh/gamepulse-key.pem ubuntu@<PUBLIC_IP>"
  echo "2. Clone: git clone https://github.com/thephilipjones/GamePulse.git /opt/gamepulse"
  echo "3. Secrets: cd /opt/gamepulse && bash backend/scripts/load-secrets.sh production .env"
  echo "4. Deploy: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
fi
