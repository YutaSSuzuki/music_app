#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /tmp/oracle-ai-database-free-26ai-*.el9.x86_64.rpm" >&2
  exit 1
fi

database_rpm=$1

sudo dnf update -y
sudo dnf install -y oracle-ai-database-preinstall-26ai
sudo dnf install -y "$database_rpm"

echo "Run the following command to create FREE/FREEPDB1:"
echo "  sudo /etc/init.d/oracle-free-26ai configure"
