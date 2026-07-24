#! /bin/bash

#for VERSION in kde cinnamon mate; do
for VERSION in kde; do
    for NUMBER in 1 2; do
        export NAME=vm-gui-$VERSION-$NUMBER-v2
        echo "=== Processing $NAME ==="
        
        # Clean up any existing instance
        rcp_lxd clean --tailscale-logout -f --name $NAME
        
        # Create node, run all ansible playbooks, and run desktop setup
        rcp_lxd create --name $NAME --cpu 4 --memory 16GiB --distro noble && \
        rcp_lxd run-ansible --name $NAME --all && \
        rcp_lxd run-ansible --name $NAME --playbook ${VERSION}_setup.yml
        
        echo "=== Completed $NAME ==="
        echo ""
    done
done
