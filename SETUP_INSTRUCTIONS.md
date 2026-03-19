# CT 204 Setup Instructions

## Current Status

SSH access to CT 204 (dev-worker@192.168.8.202) is not configured from this environment.

## Manual Setup Required

Please run the following commands **on CT 204** directly (via SSH from your machine or direct console access):

### Option 1: Run the Setup Script

```bash
# Copy the script to CT 204
scp /mnt/workspace/langgraph_tdd/scripts/setup-ct204.sh dev-worker@192.168.8.202:/tmp/

# Run on CT 204
ssh dev-worker@192.168.8.202 "chmod +x /tmp/setup-ct204.sh && sudo bash /tmp/setup-ct204.sh"
```

### Option 2: Run Commands Manually

```bash
# SSH to CT 204
ssh dev-worker@192.168.8.202

# Run these commands on CT 204:

# 1. Update packages
sudo apt update

# 2. Install ESP-IDF prerequisites
sudo apt install -y git wget curl flex bison python3 python3-pip python3-venv libffi-dev libssl-dev

# 3. Install ESP-IDF
mkdir -p /opt
cd /opt
git clone --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
git checkout v5.1
./install.sh

# Add to shell profile
echo "export IDF_PATH=/opt/esp-idf" >> ~/.bashrc
echo "export PATH=\$IDF_PATH/tools:\$PATH" >> ~/.bashrc

# 4. Install Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 5. Verify
source ~/.bashrc
idf.py --version
node --version
npm --version
```

## After Setup

Once installed, the TDD agent will automatically:
- Use ESP-IDF host tests for C code (when IDF_PATH is set)
- Use npm/vitest for TypeScript code (when node/npm are available)

## Troubleshooting

### ESP-IDF already installed
If you see "ESP-IDF already installed", skip to Node.js installation.

### Node.js already installed
Check version: `node --version` - should be v20 or higher.

### Permission denied
Make sure you're running with `sudo` where required.

## Need Help?

If SSH from your local machine fails, you may need to:
1. Check SSH key configuration
2. Verify CT 204 firewall rules
3. Confirm dev-worker user exists on CT 204
