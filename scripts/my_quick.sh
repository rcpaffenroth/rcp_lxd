#! /bin/bash

NAME=${1:-test}

# Clean up any existing instance
uv run rcp_lxd clean --tailscale-logout -f --name $NAME
        
# Create node, run all ansible playbooks, and run desktop setup
uv run rcp_lxd create --name $NAME --cpu 4 --memory 16GiB --distro resolute
uv run rcp_lxd run-ansible --name $NAME --system-setup 
uv run rcp_lxd run-ansible --name $NAME --rcpaffenroth-setup
uv run rcp_lxd run-ansible --name $NAME --tailscale-setup 

