#! /bin/bash
# Usage: scripts/ip.sh <container-name>
# Prints the container's IPv4 address, e.g.: ssh $(scripts/ip.sh test)

set -euo pipefail

NAME=${1:?Usage: $0 <container-name>}

IP=$(lxc list --format json "$NAME" | jq -r '.[0].state.network.eth0.addresses[] | select(.family == "inet") | .address')

if [ -z "$IP" ]; then
    echo "Could not find IPv4 address for container '$NAME'" >&2
    exit 1
fi

echo "$IP"
