#!/usr/bin/env bash
set -euo pipefail

sudo apt update
sudo apt install -y apache2 curl git netcat-openbsd python3-venv ufw
sudo a2enmod proxy proxy_http headers
sudo systemctl enable --now apache2

if sudo ufw status | grep -q '^Status: active'; then
  sudo ufw allow 80/tcp
fi

sudo mkdir -p /data/music-app/audio
sudo chown -R ubuntu:ubuntu /data/music-app

echo "Clone the repository under /home/ubuntu/music_app, then follow docs/02_python_ec2_setup.md"
