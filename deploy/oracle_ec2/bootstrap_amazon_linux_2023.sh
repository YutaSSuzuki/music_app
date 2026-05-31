#!/usr/bin/env bash
set -euo pipefail

echo "Legacy container setup only. Use bootstrap_oracle_linux_9.sh for the target Oracle EC2." >&2

sudo dnf update -y
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

echo "Log out/in once so docker group is applied, then run docker compose."
