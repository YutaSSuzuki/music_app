#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 /tmp/oracle-ai-database-preinstall-26ai-*.el9.x86_64.rpm /tmp/oracle-ai-database-free-26ai-*.el9.x86_64.rpm" >&2
  exit 1
fi

preinstall_rpm=$1
database_rpm=$2

sudo dnf update -y
sudo dnf install -y "$preinstall_rpm"
sudo dnf install -y "$database_rpm"

echo "Run the following command to create FREE/FREEPDB1:"
echo "  sudo /etc/init.d/oracle-free-26ai configure"
