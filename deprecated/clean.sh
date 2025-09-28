#!/bin/bash

set -euo pipefail

# Default values
CONTAINER_NAME=""
FORCE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Stop and remove LXD container/VM created by create.sh

OPTIONS:
    -n, --name NAME     Container name to remove (required)
    -f, --force         Force removal without confirmation
    -h, --help          Show this help message

EXAMPLES:
    $0 -n myvm                  # Remove container 'myvm' with confirmation
    $0 -n testvm --force        # Force remove 'testvm' without asking
    $0 --name vm1 -f            # Force remove 'vm1'

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}" >&2
            usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$CONTAINER_NAME" ]]; then
    echo -e "${RED}Error: Container name is required${NC}" >&2
    usage
    exit 1
fi

# Check if LXC is available
if ! command -v lxc &> /dev/null; then
    echo -e "${RED}Error: LXC is not installed or not in PATH${NC}" >&2
    exit 1
fi

# Check if container exists
if ! lxc info "$CONTAINER_NAME" &> /dev/null; then
    echo -e "${YELLOW}Warning: Container '$CONTAINER_NAME' does not exist${NC}"
    exit 0
fi

# Get container status
STATUS=$(lxc list "$CONTAINER_NAME" -c s --format csv)

# Confirmation unless force flag is used
if [[ "$FORCE" != true ]]; then
    echo -e "${YELLOW}About to remove container: $CONTAINER_NAME (Status: $STATUS)${NC}"
    read -p "Are you sure? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

echo -e "${GREEN}Cleaning up container: $CONTAINER_NAME${NC}"

# Stop container if running
if [[ "$STATUS" == "RUNNING" ]]; then
    echo "Stopping container..."
    lxc stop "$CONTAINER_NAME"
fi

# Remove container
echo "Removing container..."
lxc delete "$CONTAINER_NAME"

echo -e "${GREEN}Container '$CONTAINER_NAME' successfully removed${NC}"
