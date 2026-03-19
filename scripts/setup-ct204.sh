#!/bin/bash
# Setup script for CT 204 (dev-worker)
# Install ESP-IDF and Node.js for C and TypeScript TDD support

set -e

echo "=== CT 204 Setup for LangGraph TDD ==="

# Check OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "Detected OS: $NAME $VERSION"
fi

# Update package list
echo "Updating package lists..."
sudo apt update

# Install ESP-IDF prerequisites
echo "Installing ESP-IDF prerequisites..."
sudo apt install -y git wget curl flex bison python3 python3-pip python3-venv libffi-dev libssl-dev

# Install ESP-IDF
echo "Installing ESP-IDF v5.1..."
mkdir -p /opt
cd /opt
if [ ! -d "esp-idf" ]; then
    git clone --recursive https://github.com/espressif/esp-idf.git
    cd esp-idf
    git checkout v5.1
    ./install.sh
    echo "export IDF_PATH=/opt/esp-idf" >> ~/.bashrc
    echo "export PATH=\$IDF_PATH/tools:\$PATH" >> ~/.bashrc
else
    echo "ESP-IDF already installed at /opt/esp-idf"
fi

# Install Node.js 20.x for TypeScript/Next.js support
echo "Installing Node.js 20.x..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installations
echo ""
echo "=== Verification ==="
echo "ESP-IDF version:"
if [ -d "/opt/esp-idf" ]; then
    /opt/esp-idf/idf.py --version
fi

echo ""
echo "Node.js version:"
node --version

echo ""
echo "npm version:"
npm --version

echo ""
echo "=== Setup Complete ==="
echo "You may need to restart your shell or run:"
echo "  source ~/.bashrc"
echo ""
echo "Then test with:"
echo "  cd /mnt/workspace/tasks/esp32-test && idf.py build-test"
echo "  cd /mnt/workspace/tasks/nextjs-test && npm test"
