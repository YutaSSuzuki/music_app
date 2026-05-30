#!/usr/bin/env bash
set -euo pipefail

sudo dnf update -y
sudo dnf install -y python3 python3-pip git httpd
sudo systemctl enable --now httpd

sudo mkdir -p /opt/music-app
sudo chown -R ec2-user:ec2-user /opt/music-app

echo "Install app files under /opt/music-app/oracle, then follow docs/02_python_ec2_setup.md"
