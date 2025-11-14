#!/bin/bash
# Install GamePulse systemd service for proper boot-time startup
# This ensures containers are created with production configuration on EC2 restart

set -e

echo "Installing GamePulse systemd service..."

# Copy service file to systemd directory
sudo cp /opt/gamepulse/infrastructure/gamepulse.service /etc/systemd/system/gamepulse.service

# Set proper permissions
sudo chmod 644 /etc/systemd/system/gamepulse.service

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable gamepulse.service

# Show status
sudo systemctl status gamepulse.service --no-pager || true

echo "✅ GamePulse systemd service installed successfully"
echo "   Service will start automatically on boot"
echo ""
echo "Manual commands:"
echo "  Start:   sudo systemctl start gamepulse"
echo "  Stop:    sudo systemctl stop gamepulse"
echo "  Restart: sudo systemctl restart gamepulse"
echo "  Status:  sudo systemctl status gamepulse"
echo "  Logs:    sudo journalctl -u gamepulse -f"
