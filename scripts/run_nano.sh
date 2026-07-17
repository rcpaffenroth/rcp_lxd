#! /bin/bash

NAME=${1:-test}

# Clean up any existing instance
rcp_lxd clean --tailscale-logout -f --name $NAME
        
# Create node, run all ansible playbooks, and run desktop setup
rcp_lxd create --name $NAME --cpu 4 --memory 16GiB --distro resolute
rcp_lxd run-ansible --name $NAME --system-setup

