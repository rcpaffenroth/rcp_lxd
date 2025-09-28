#!/bin/bash

set -euo pipefail # Exit on error, undefined vars, pipe failures

# Default values
VM_NAME="vm1"
UBUNTU_VERSION="noble" # 24.04 LTS
CPU_COUNT=2
MEMORY="4GiB"
CLOUD_INIT_FILE="./cloud-init"
RUN_ANSIBLE=false
PRIVILEGED=false
FORWARD_SSH=false
SSH_PORT=2022
PORT_FORWARDS=() # Array to store port forwarding rules

# Ansible playbook options
RUN_SYSTEM_SETUP=false
RUN_RCPAFFENROTH_SETUP=false
RUN_TAILSCALE_SETUP=false
RUN_XFCE_SETUP=false

# Usage function
usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Create and configure an LXD container/VM with Ubuntu.

OPTIONS:
    -n, --name NAME         Container name (default: vm1)
    -d, --distro VERSION    Ubuntu version: focal(20.04), jammy(22.04), noble(24.04) (default: noble)
    -c, --cpu COUNT         Number of CPUs (default: 2)
    -m, --memory SIZE       Memory size with unit (e.g., 4GiB, 2048MiB) (default: 4GiB)
    -i, --cloud-init FILE   Cloud-init file path (default: ./cloud-init)
    --ssh-port PORT         Enable SSH port forwarding to specified port (default: 2022)
    --port HOST:GUEST       Forward port from host to guest (e.g., 8080:80, 3000:3000)
    --ansible               Run all Ansible playbooks after creation
    --no-ansible            Skip Ansible playbook execution (default)
    --system-setup          Run only system_setup.yml playbook
    --rcpaffenroth-setup    Run only rcpaffenroth_setup.yml playbook
    --tailscale-setup       Run only tailscale_setup.yml playbook
    --xfce-setup            Run only xfce_setup.yml playbook
    --privileged            Enable privileged mode (for ACPI/windowing)
    --vm                    Create VM instead of container
    -h, --help              Show this help message

EXAMPLES:
    $0                                          # Create vm1 with defaults (no port forwarding)
    $0 -n myvm -d noble -c 4 -m 8GiB           # Ubuntu 24.04, 4 CPUs, 8GB RAM
    $0 -n testvm --ssh-port 2023 --ansible     # Enable SSH on port 2023, run all Ansible playbooks
    $0 --vm -n myvm --privileged               # Create VM with privileged mode
    $0 --port 8080:80 --port 3000:3000         # Forward ports 8080->80 and 3000->3000
    $0 --ssh-port 2022 --port 9000:9000        # SSH forwarding + custom port
    $0 --system-setup --rcpaffenroth-setup     # Run only specific playbooks
    $0 --xfce-setup --tailscale-setup          # Run XFCE and Tailscale setup only

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
  -n | --name)
    VM_NAME="$2"
    shift 2
    ;;
  -d | --distro)
    UBUNTU_VERSION="$2"
    shift 2
    ;;
  -c | --cpu)
    CPU_COUNT="$2"
    shift 2
    ;;
  -m | --memory)
    MEMORY="$2"
    shift 2
    ;;
  -i | --cloud-init)
    CLOUD_INIT_FILE="$2"
    shift 2
    ;;
  --ssh-port)
    FORWARD_SSH=true
    SSH_PORT="$2"
    shift 2
    ;;
  --port)
    PORT_FORWARDS+=("$2")
    shift 2
    ;;
  --ansible)
    RUN_ANSIBLE=true
    RUN_SYSTEM_SETUP=true
    RUN_RCPAFFENROTH_SETUP=true
    RUN_TAILSCALE_SETUP=true
    RUN_XFCE_SETUP=true
    shift
    ;;
  --no-ansible)
    RUN_ANSIBLE=false
    RUN_SYSTEM_SETUP=false
    RUN_RCPAFFENROTH_SETUP=false
    RUN_TAILSCALE_SETUP=false
    RUN_XFCE_SETUP=false
    shift
    ;;
  --system-setup)
    RUN_ANSIBLE=true
    RUN_SYSTEM_SETUP=true
    shift
    ;;
  --rcpaffenroth-setup)
    RUN_ANSIBLE=true
    RUN_RCPAFFENROTH_SETUP=true
    shift
    ;;
  --tailscale-setup)
    RUN_ANSIBLE=true
    RUN_TAILSCALE_SETUP=true
    shift
    ;;
  --xfce-setup)
    RUN_ANSIBLE=true
    RUN_XFCE_SETUP=true
    shift
    ;;
  --privileged)
    PRIVILEGED=true
    shift
    ;;
  --vm)
    VM_TYPE="--vm"
    shift
    ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown option: $1"
    usage
    exit 1
    ;;
  esac
done

# Validation
if [[ ! -f "$CLOUD_INIT_FILE" ]]; then
  echo "Error: Cloud-init file '$CLOUD_INIT_FILE' not found"
  exit 1
fi

if ! command -v lxc &>/dev/null; then
  echo "Error: LXC command not found. Install with: sudo snap install lxd"
  exit 1
fi

# Check if container/VM already exists
if lxc info "$VM_NAME" &>/dev/null; then
  read -p "Container '$VM_NAME' already exists. Delete it? (y/N): " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Deleting existing container '$VM_NAME'..."
    lxc delete "$VM_NAME" --force
  else
    echo "Aborting."
    exit 1
  fi
fi

# Create the container/VM
echo "Creating container '$VM_NAME' with Ubuntu $UBUNTU_VERSION..."
echo "Resources: ${CPU_COUNT} CPUs, ${MEMORY} memory"

lxc launch "ubuntu:${UBUNTU_VERSION}" "$VM_NAME" ${VM_TYPE:-} \
  --config=user.user-data="$(cat "$CLOUD_INIT_FILE")" \
  -c limits.memory="$MEMORY" \
  -c limits.cpu="$CPU_COUNT"

# Set privileged mode if requested
if [[ "$PRIVILEGED" == "true" ]]; then
  echo "Enabling privileged mode..."
  lxc config set "$VM_NAME" security.privileged true
fi

# Wait for container to be ready
echo "Waiting for container to start and cloud-init to complete..."
sleep 15

# Wait for cloud-init to finish
echo "Waiting for cloud-init to complete..."
while ! lxc exec "$VM_NAME" -- cloud-init status --wait; do
  echo "Cloud-init still running, waiting..."
  sleep 10
done

# Set up port forwarding
# SSH port forwarding (if requested)
if [[ "$FORWARD_SSH" == "true" ]]; then
  echo "Setting up SSH port forwarding (host:$SSH_PORT -> container:22)..."
  lxc config device add "$VM_NAME" ssh-proxy proxy \
    listen="tcp:0.0.0.0:$SSH_PORT" \
    connect="tcp:127.0.0.1:22" || true
fi

# Custom port forwarding
if [[ ${#PORT_FORWARDS[@]} -gt 0 ]]; then
  echo "Setting up custom port forwarding..."
  for i in "${!PORT_FORWARDS[@]}"; do
    port_rule="${PORT_FORWARDS[$i]}"
    if [[ ! "$port_rule" =~ ^[0-9]+:[0-9]+$ ]]; then
      echo "Warning: Invalid port format '$port_rule', expected HOST:GUEST (e.g., 8080:80)"
      continue
    fi

    host_port=$(echo "$port_rule" | cut -d':' -f1)
    guest_port=$(echo "$port_rule" | cut -d':' -f2)
    device_name="port-proxy-${i}"

    echo "  Forwarding host:$host_port -> container:$guest_port"
    lxc config device add "$VM_NAME" "$device_name" proxy \
      listen="tcp:0.0.0.0:$host_port" \
      connect="tcp:127.0.0.1:$guest_port" || echo "    Warning: Failed to add port forwarding for $port_rule"
  done
fi

# Run Ansible to update the newly created machine
if [[ "$RUN_ANSIBLE" == "true" ]]; then
  echo "Running Ansible to update the newly created machine..."

  # Get the container's IP address
  CONTAINER_IP=$(lxc list "$VM_NAME" -f csv -c 4 | cut -f 1 -d ' ' | head -1)

  if [[ -n "$CONTAINER_IP" ]]; then
    echo "Container IP: $CONTAINER_IP"

    # Create a temporary inventory in the inventory directory for debugging
    TEMP_INVENTORY="inventory/${VM_NAME}_temp.ini"
    cat >"$TEMP_INVENTORY" <<EOF
$VM_NAME ansible_host=$CONTAINER_IP ansible_user=rcpaffenroth ansible_ssh_common_args='-o StrictHostKeyChecking=no'

[have_root]
$VM_NAME

[have_rcpaffenroth]
$VM_NAME
EOF

    echo "Created temporary inventory at: $TEMP_INVENTORY"

    # Wait for SSH to be available
    echo "Waiting for SSH to be available..."
    timeout=60
    while ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no rcpaffenroth@"$CONTAINER_IP" exit 2>/dev/null; do
      sleep 5
    done

    echo "Created temporary inventory at: $TEMP_INVENTORY"

    if [[ $timeout -gt 0 ]]; then
      # Run system setup playbook
      if [[ "$RUN_SYSTEM_SETUP" == "true" && -f "$HOME/projects/ansible/playdir/system_setup.yml" ]]; then
        echo "Running system setup playbook..."
        ansible-playbook -i "$TEMP_INVENTORY" -l "$VM_NAME" --skip-tags=slow \
          "$HOME/projects/ansible/playdir/system_setup.yml" ||
          echo "Warning: System setup playbook failed"
      fi

      # Run rcpaffenroth setup playbook
      if [[ "$RUN_RCPAFFENROTH_SETUP" == "true" && -f "$HOME/projects/ansible/playdir/rcpaffenroth_setup.yml" ]]; then
        echo "Running rcpaffenroth setup playbook..."
        ansible-playbook -i "$TEMP_INVENTORY" -l "$VM_NAME" --skip-tags="slow,nonlocal" \
          "$HOME/projects/ansible/playdir/rcpaffenroth_setup.yml" ||
          echo "Warning: rcpaffenroth setup playbook failed"
      fi

      # Run tailscale setup playbook
      if [[ "$RUN_TAILSCALE_SETUP" == "true" && -f "$HOME/projects/ansible/playdir/tailscale_setup.yml" ]]; then
        echo "Running tailscale setup playbook..."
        ansible-playbook -i "$TEMP_INVENTORY" -l "$VM_NAME" -e "TAILSCALE_HOSTNAME=ts${VM_NAME}" --skip-tags="slow,nonlocal" \
          "$HOME/projects/ansible/playdir/tailscale_setup.yml" ||
          echo "Warning: tailscale setup playbook failed"
      fi

      # Run xfce setup playbook
      if [[ "$RUN_XFCE_SETUP" == "true" && -f "$HOME/projects/ansible/playdir/xfce_setup.yml" ]]; then
        echo "Running xfce setup playbook..."
        ansible-playbook -i "$TEMP_INVENTORY" -l "$VM_NAME" --skip-tags="slow,nonlocal" \
          "$HOME/projects/ansible/playdir/xfce_setup.yml" ||
          echo "Warning: xfce setup playbook failed"
      fi
    fi

    # Keep temporary inventory for debugging (don't clean up)
    echo "Temporary inventory file kept for debugging: $TEMP_INVENTORY"
  else
    echo "Warning: Could not determine container IP, skipping Ansible"
  fi
fi

# Get container IP for reference
CONTAINER_IP=$(lxc list "$VM_NAME" -f csv -c 4 | cut -f 1 -d ' ' | head -1)

echo
echo "=== Container '$VM_NAME' created successfully ==="
echo "Ubuntu version: $UBUNTU_VERSION"
echo "Resources: ${CPU_COUNT} CPUs, ${MEMORY} memory"
echo "Container IP: ${CONTAINER_IP:-"(not available yet)"}"

# Show port forwarding info
if [[ "$FORWARD_SSH" == "true" ]]; then
  echo "SSH access: ssh -p $SSH_PORT localhost"
fi

if [[ ${#PORT_FORWARDS[@]} -gt 0 ]]; then
  echo "Port forwarding:"
  for port_rule in "${PORT_FORWARDS[@]}"; do
    if [[ "$port_rule" =~ ^[0-9]+:[0-9]+$ ]]; then
      host_port=$(echo "$port_rule" | cut -d':' -f1)
      guest_port=$(echo "$port_rule" | cut -d':' -f2)
      echo "  host:$host_port -> container:$guest_port"
    fi
  done
fi

if [[ "$FORWARD_SSH" != "true" && ${#PORT_FORWARDS[@]} -eq 0 ]]; then
  echo "No port forwarding configured"
fi

echo "Direct exec: lxc exec $VM_NAME -- bash"
echo
echo "To delete: lxc delete $VM_NAME --force"
# sudo snap remove lxd
