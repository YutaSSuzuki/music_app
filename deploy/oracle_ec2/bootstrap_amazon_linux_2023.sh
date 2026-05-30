#!/usr/bin/env bash
set -euo pipefail

sudo dnf update -y
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

echo "Log out/in once so docker group is applied, then run docker compose."
