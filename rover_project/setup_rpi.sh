#!/bin/bash
# Raspberry Pi Setup Script for Space Rover
# Run with: bash setup_rpi.sh

echo "=========================================="
echo "  Space Rover - Raspberry Pi Setup"
echo "=========================================="
echo ""

# Update system
echo "→ Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo ""
echo "→ Installing system dependencies..."
sudo apt-get install -y python3-pip python3-dev
sudo apt-get install -y python3-opencv
sudo apt-get install -y libgpiod2
sudo apt-get install -y python3-pil
sudo apt-get install -y i2c-tools
sudo apt-get install -y python3-smbus
sudo apt-get install -y libatlas-base-dev
sudo apt-get install -y git

# Install Python packages
echo ""
echo "→ Installing Python packages..."
pip3 install -r requirements_rpi.txt

# Enable I2C
echo ""
echo "→ Enabling I2C interface..."
sudo raspi-config nonint do_i2c 0

# Add user to groups
echo ""
echo "→ Adding user to necessary groups..."
sudo usermod -a -G gpio,i2c,spi,video $USER

# Create data directory
echo ""
echo "→ Creating data directory..."
mkdir -p ~/rover_project/data
mkdir -p ~/rover_project/data/logs
mkdir -p ~/rover_project/data/images

# Create config file
echo ""
echo "→ Creating default configuration..."
cat > ~/rover_project/rover_config.json << EOF
{
  "auto_study_enabled": true,
  "study_interval": 30,
  "default_speed": 50,
  "ir_priority": true,
  "log_to_file": true,
  "camera_resolution": [320, 240],
  "min_obstacle_area": 1500
}
EOF

# Test I2C
echo ""
echo "→ Testing I2C devices..."
sudo i2cdetect -y 1

echo ""
echo "=========================================="
echo "  ✓ Setup Complete!"
echo "=========================================="
echo ""
echo "IMPORTANT: Please reboot your Raspberry Pi"
echo "Run: sudo reboot"
echo ""
echo "After reboot, verify I2C is working:"
echo "  sudo i2cdetect -y 1"
echo ""
echo "To test components individually:"
echo "  python3 sensor_manager.py"
echo "  python3 motor_controller.py"
echo "  python3 obstacle_detector.py"
echo ""
echo "To run the complete rover system:"
echo "  python3 rover_main.py"
echo ""