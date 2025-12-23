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
./install.sh
```

## Usage

The tool provides a unified CLI with three main commands:

### Classic flow

```bash
rcp_lxd create --name vm-gui-v2 --cpu 4 --memory 16GiB --distro noble
rcp_lxd run-ansible --name vm-gui-v2 --all
rcp_lxd run-ansible --name vm-gui-v2 --playbook xfce_setup.yml
rcp_lxd clean --name vm-gui-v2
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

The tool integrates with Ansible playbooks located in `~/projects/ansible/playdir/`:
- `system_setup.yml` - Basic system configuration
- `rcpaffenroth_setup.yml` - User-specific setup
- `tailscale_setup.yml` - Tailscale VPN setup

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