# RCP LXD - LXD Container/VM Management Tool

A Python-based tool for managing LXD containers and VMs with integrated Ansible support.

## Installation

### Prerequisites

Install lxd:

```bash
sudo snap install lxd
```

Then set up LXD:

```bash
sudo lxd init --minimal
```

### Install rcp-lxd

This package uses `uv` for package management. To install:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the package in development mode
uv pip install -e .

# Or use the convenience script
./scripts/install.sh
```

## Usage

The tool provides a unified CLI with four commands: `create`, `run-ansible`,
`clean`, and `up` (an interactive `create` + `run-ansible` combo).

### Interactive (TUI) mode

Every command works exactly as before from the command line. Adding `-I` /
`--interactive` instead pops up a small [Textual](https://textual.textualize.io/)
form, pre-filled with the current defaults (and any flags you also passed), so
you can edit the options and submit. Submit with the **Submit** button or
`Ctrl+S`; cancel with **Cancel** or `Esc`.

```bash
# Configure the new container/VM in a TUI instead of passing every flag
rcp_lxd create --interactive

# Pre-seed some fields, tweak the rest interactively
rcp_lxd create --distro mint --cpu 4 -I

# Also available on clean and run-ansible
rcp_lxd clean -I
rcp_lxd run-ansible -I
```

#### `up`: create + run-ansible in one form

`rcp_lxd up` is always interactive: one combined form collects both the
create options and the Ansible playbook selection (the name is entered once),
then it creates the container/VM and immediately runs Ansible against it.

```bash
rcp_lxd up
```

### Classic flow

```bash fish
set -l NAME vm-gui-v2
# Clean up any existing instance
rcp_lxd clean --tailscale-logout -f --name $NAME    
# Create node
rcp_lxd create --name $NAME --cpu 4 --memory 16GiB --distro noble
# Run ansible playbooks
rcp_lxd run-ansible --name $NAME --all
# Run specific playbook for KDE
rcp_lxd run-ansible --name $NAME --playbook kde_setup.yml
# Clean up
rcp_lxd clean --tailscale-logout -f --name $NAME
```

### Tailscale testing flow

```bash fish
set -l NAME vm-gui-v2
# Clean up any existing instance
rcp_lxd clean --tailscale-logout -f --name $NAME
# Create node and run tailscale setup
rcp_lxd create --name $NAME --cpu 4 --memory 16GiB --distro noble && \
rcp_lxd run-ansible --name $NAME --tailscale-setup 
```

### Single command down and up

```bash fish
set -l NAME vm-gui-v2
# Clean up any existing instance
rcp_lxd clean --tailscale-logout -f --name $NAME
# Create node, run all ansible playbooks, and run kde setup
rcp_lxd create --name $NAME --cpu 4 --memory 16GiB --distro noble && \
rcp_lxd run-ansible --name $NAME --all && \
rcp_lxd run-ansible --name $NAME --playbook kde_setup.yml
```

### Linux Mint XFCE flow

`--distro mint` is a shortcut for the Linux Mint zena image (`images:mint/zena/cloud`).
Mint is **container-only** — there is no Mint VM image, so `--distro mint --vm`
errors out. The Mint LXC image is a minimal base with no desktop, so XFCE is
installed by the `mint_xfce_setup.yml` playbook (native `mint-meta-xfce`), which
exposes the desktop over VNC.

```bash fish
set -l NAME mint1
# Clean up any existing instance
rcp_lxd clean --tailscale-logout -f --name $NAME
# Create the Mint node, run the standard playbooks, then install Mint XFCE + VNC
rcp_lxd create --name $NAME --cpu 4 --memory 16GiB --distro mint && \
rcp_lxd run-ansible --name $NAME --all && \
rcp_lxd run-ansible --name $NAME --playbook mint_xfce_setup.yml
```

The playbook starts a systemd-managed VNC server on display `:1` (port 5901),
bound to localhost with no VNC password. Reach it through an SSH tunnel:

```bash
# Tunnel local port 5901 to the node's VNC server, then point a VNC client at localhost:5901
ssh -N -L 5901:localhost:5901 rcpaffenroth@<node-ip>
```

### Creating Containers/VMs

```bash
# Create a basic container
rcp_lxd create --name myvm

# Create a VM (instead of container) with custom resources
rcp_lxd create --name myvm --vm --cpu 4 --memory 8GiB --distro jammy

# Use a custom cloud-init file
rcp_lxd create --name myvm --cloud-init ./my-cloud-init
```

### Managing Containers

```bash
# Remove a container (with confirmation)
rcp_lxd clean --name myvm

# Force remove without confirmation
rcp_lxd clean --name myvm --force
```

### Running Ansible Playbooks

```bash
# Run all default playbooks
rcp_lxd run-ansible --name myvm

# Run specific playbooks
rcp_lxd run-ansible --name myvm --system-setup 

# Run all playbooks
rcp_lxd run-ansible --name myvm --all

# Run arbitrary playbook from ansible/playdir directory
rcp_lxd run-ansible --name myvm --playbook xfce_setup.yml

# Run playbook with extra ansible arguments
rcp_lxd run-ansible --name myvm --playbook xfce_setup.yml -e "--skip-tags=slow" -e "--verbose"

# Run one built-in playbook restricted to a tag
rcp_lxd run-ansible --name myvm --rcpaffenroth-setup -e "--tags=dotfiles"

# Also run rcpaffenroth-setup's 'unsafe_ok'-tagged tasks
# (this adds --tags=unsafe_ok, which restricts that run to unsafe_ok-tagged tasks only)
rcp_lxd run-ansible --name myvm --rcpaffenroth-setup --unsafe-ok

# Skip SSH wait (if you know SSH is already available)
rcp_lxd run-ansible --name myvm --no-wait-ssh
```

## Cloud-Init Configuration

The tool uses a cloud-init file (default: `./cloud-init`) to bootstrap the container/VM. This typically includes:
- Creating user accounts
- Setting up SSH keys
- Installing basic packages
- Configuring network settings

## Ansible Integration

The tool integrates with a companion Ansible repo. By default it looks for that
repo at `~/projects/ansible`, running playbooks from its `playdir/` and using its
`ansible.cfg`:
- `system_setup.yml` - Basic system configuration
- `rcpaffenroth_setup.yml` - User-specific setup
- `tailscale_setup.yml` - Tailscale VPN setup

### Selecting the Ansible repo (`ANSIBLE_REPO`)

The location of the Ansible repo is controlled by the `ANSIBLE_REPO` environment
variable, which defaults to `~/projects/ansible`. It governs two things:

- **Playbooks** are resolved against `$ANSIBLE_REPO/playdir/`.
- **Config** is pinned by setting `ANSIBLE_CONFIG=$ANSIBLE_REPO/ansible.cfg`
  before invoking `ansible-playbook`, so the config no longer depends on the
  current working directory (there is no longer an `ansible.cfg` symlink in this
  repo) or on which checkout a symlink happened to point at.

Point it at a specific checkout or git worktree to test playbook changes from
there instead of the default checkout:

```bash
# Use the default ~/projects/ansible
rcp_lxd run-ansible --name myvm --all

# Use a specific worktree/checkout for this run
ANSIBLE_REPO=~/projects/worktrees/ansible rcp_lxd run-ansible --name myvm --all

# Export it for an entire session
export ANSIBLE_REPO=~/projects/worktrees/ansible
rcp_lxd run-ansible --name myvm --playbook kde_setup.yml
```

## Development

The package is structured as a modern Python project:

```
rcplxd/
├── __init__.py          # Package initialization
├── cli.py               # Main CLI interface
├── core.py              # Core LXD utilities
├── container.py         # Container management
└── ansible_utils.py     # Ansible integration
```

To contribute:
1. Make your changes
2. Test locally: `uv pip install -e .`
3. Run the commands to ensure they work as expected

## Notes

- The tool creates temporary inventory files in `./inventory/` 
- SSH helper scripts are created for convenience (e.g., `ssh_vm1.sh`)
- The tool waits for cloud-init completion before proceeding
- All Ansible playbooks include `--skip-tags=slow` by default for faster execution

## Python CLI (recommended for simplicity)

You can do the same with the Python wrapper that mirrors `create.sh` but uses Click and simpler defaults:

``` bash
./create.py --vm -n vm1 -d noble -c 2 -m 4GiB -i ./cloud-init
```

Flags supported (subset mirrors the shell script):
- `--name|-n`, `--distro|-d`, `--cpu|-c`, `--memory|-m`, `--cloud-init|-i`
- `--vm`
- (port forwarding options removed for the Python script to keep it minimal)
- (the Python script does not run Ansible; it writes an inventory in `lxd/inventory/<name>_temp.ini` and prints example commands)

To run Ansible playbooks, there's a separate helper:

```bash
./run_ansible.py -n vm1 --all          # run all playbooks (system, rcpaffenroth, tailscale)
./run_ansible.py -n vm1 --system-setup  # or choose specific ones
```

Clean up a VM/container:

```bash
./clean.py -n vm1          # prompts for confirmation
./clean.py -n vm1 -f       # force removal without prompt
```

The script will also create a temporary Ansible inventory in `lxd/inventory/<name>_temp.ini` and wait for SSH before running playbooks.

## Notes
I tried several different things here.  For example, you can create a lxc vm from inside ansible (i.e., there is a plugin called `lxd_container` that can be used to create a container).  However, I found that it was easier to create the container from the command line and then use ansible to configure it.  This is because the `lxd_container` plugin doesn't seem to have a way to pass in a cloud-init configuration.  Also, in general, it seems a little flaky and not well supported.

However, the ansible lxd inventory plugin seems better, though it has its own issues.  For example, it defaults to the ssh ansible connection method, where there is a quite nice lxd connection method that can be used.  The ssh connection method is set in the auto-generated inventory and while I could do some magic to change it, it was easier to just get ssh setup and then use that to run the ansible playbooks.

So, there is a clean separation of concerns here.  The `create.sh` script is used to create the VMs, the cloud-init creates rcpaffenroth and gets ssh setup, and then ansible is used to configure the VMs.

## General unsorted notes mainly on windowing
ssh -p 2022 -N -L 3389:localhost:3389 rcp2

ssh -p 2022 -N -L 3395:localhost:3389 rcp2
and enter 3395 into rdp client on windows

echo "xfce4-session" | tee .xsession

apt-get install -y acpid
systemctl disable --now acpid.service acpid.socket acpid.path
apt install ubuntu-desktop -y

apt install xrdp xubuntu-desktop
apt install xrdp ubuntu-mate-desktop #mate-session-manager

[Ubuntu Mate 20.04 XRDP setup (github.com)](https://gist.github.com/jelovac/6ed31e0901ccdcdeeb582277076bf966)

[20.04 - Start Xubuntu Session in xrdp - Ask Ubuntu](https://askubuntu.com/questions/1301024/start-xubuntu-session-in-xrdp)

The reason is because several environment variables are not set and passed to startxfce4. Create a /usr/local/bin/start-xubuntu file and put "start-xubuntu" in ~/.xsession:

```
#!/bin/bash

export XDG_DATA_DIRS="/usr/share/xfce4:/usr/share/xubuntu:/usr/local/share:/usr/share:/var/lib/snapd/desktop:/usr/share"
export XDG_CONFIG_DIRS="/etc/xdg/xdg-xubuntu:/etc/xdg"

export LANG=en_US.UTF-8
export GDM_LANG=en_US.UTF-8
export DESKTOP_SESSION=xubuntu
export GDMSESSION=xubuntu
export XDG_SESSION_DESKTOP=xubuntu

# propagate to X sessions. It is important when user first
# login, they decide on the initial xfce/xubuntu template settings.
dbus-update-activation-environment --verbose XDG_DATA_DIRS XDG_CONFIG_DIRS DESKTOP_SESSION GDMSESSION XDG_SESSION_DESKTOP

exec startxfce4
```

# Old notes#! /bin/bash

# install lxd
#sudo snap install lxd

# initial setup
#lxd init --minimal
# One change I somtimes make:
# What IPv4 address should be used? (CIDR subnet notation, “auto” or “none”) [default=auto]: 192.168.0.1/24

# Note, it askes about NAT, which I think I need.

# The yaml file is saved as config.yaml

# creates the node using cloud-init
# NOTE: We may now want to do the --vm option, since that changes the way the network is setup.
lxc launch ubuntu:jammy vm1 --config=user.user-data="$(cat ./cloud-init)" -c limits.memory=4GiB -c limits.cpu=2
# Not for students, but for me since acpi support seems to need this
# and acpi is installed with windowing systems
lxc config set vm1 security.privileged true

# sleep a few seconds for the machine to come up
sleep 10

# anisble playbook using the lxd module
ansible-inventory -i inventory/lxd.yml -i inventory/lxd_groups.yml --graph all
ansible-playbook -i inventory/lxd.yml -i inventory/lxd_groups.yml -l vm1 ~/projects/ansible/playdir/system_setup.yml
ansible-playbook -i inventory/lxd.yml -i inventory/lxd_groups.yml -l vm1 ~/projects/ansible/playdir/ssh_setup.yml
ansible-playbook -i inventory/lxd.yml -i inventory/lxd_groups.yml -l vm1 ~/projects/ansible/playdir/rcpaffenroth_setup.yml

# login to the node
# This gets the IP address of the node vm1
# ssh `lxc list vm1 -f csv -c 4 | cut -f 1 -d ' '`

# forward a port
# lxc network list
# NOTE: This only works if the machine is *not* running in a VM.
lxc config device add vm1 myssh proxy listen=tcp:0.0.0.0:2022 connect=tcp:127.0.0.1:22

# list the networks so we can get the IP address
# lxc network list

# attach the network
# lxc network attach lxdbr0 my-test eth0

# set the IP address
# lxc config device set my-test eth0 ipv4.address 10.179.230.10

# lxc delete vm1 --force

# remove lxd
# sudo snap remove lxd


# Example of running tailscale setup
ansible-playbook -i inventory/vm1_temp.ini -l vm1 -e "TAILSCALE_HOSTNAME=tsvmtest" $HOME/projects/ansible/playdir/tailscale_setup.yml
ansible-playbook -i inventory/vmtest_temp.ini -l vmtest -e "TAILSCALE_HOSTNAME=tsvmtest" $HOME/projects/ansible/playdir/tailscale_setup.yml

ansible-playbook -i inventory/vmtest_temp.ini -l vmtest -e $HOME/projects/ansible/playdir/xfce_setup.yml 

./create.sh -n vmtest2 --ansible -c 4 -m 8GiB
