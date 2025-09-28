#! /bin/bash

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
