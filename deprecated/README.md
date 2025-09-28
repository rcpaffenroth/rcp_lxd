# Notes 4-20-2024

## Hemmingway bridge
This was a nice exercise, but is likely better done using a shell script.
The lxc command line tool is much more powerful than the lxd plugin for ansible.
For example, you can use cloudinit to create a user and set the password, do a bunch of other things, etc.

However, once the machine is up and running then ansible will certainly have a role to play.

```bash

## What I learned

This does everything.  Makes a machine, adds a user, forwards a port, etc.  It is a good example of how to use the lxd plugin for ansible.

```bash
ansible-playbook test_vm1.yml
```


## ideas while I was learning
This is close to working.  I just doesn't seem to be able to be root for the last command
```bash
ansible-playbook from_gemini.yml
```

Can only create VM on hardware, not WSL2.  I get the following error (which makes sense):

Error: Failed instance creation: Failed creating instance record: Instance type "virtual-machine" is not supported on this server: vhost_vsock kernel module not loaded

```bash
sudo snap install lxd
sudo usermod -a -G lxd $USER

lxd init --minimal

lxc launch ubuntu:22.04 --vm my-vm
lxc list

ansible-inventory -i my-vm_inventory.ini --list
# This works!
ansible my-vm -a "ls /tmp" -i my-vm_inventory.ini

ansible-inventory -i lxd.yml --list
ansible-inventory -i lxd.yml --extra-vars "ansible_connection=lxd" --extra-vars "ansible_host=" --list
# This has issues with /tmp"
ansible typeVM -a "ls /tmp" -i lxd.yml --extra-vars "ansible_connection=lxd" --extra-vars "ansible_host=my-vm"

sudo snap remove lxd
```

```bash

# BEWARE!  

This seems to not be working now. It seems to want to use ssh instead of lxd for the connections.   I am not sure what I broke but

**All this should be taken with a grain of salt.**

I found this:

https://cloud-images.ubuntu.com/jammy/current/
KVM
When launching the download image from KVM, you will need to specify the virtio network driver.

LXD
First add the new Ubuntu images simplestreams endpoint:

  
    lxc remote add --protocol simplestreams ubuntu-daily https://cloud-images.ubuntu.com/
  
Launch the jammy image:

  
    lxc launch ubuntu-daily:jammy

# LXD notes
```lxd``` is a container hypervisor that is a part of the LXC project. It is a daemon that provides a REST API to manage LXC containers. It is a more user-friendly way to manage LXC containers than the LXC command line tools.

```lxc``` is a command line tool that is used to manage LXC containers. It is a part of the LXC project.

# Installation
```bash
sudo nap install lxd
```

# Configuration
```bash
lxd init --minimal
```

# Create a lxd vm 

## by hand
```bash
lxc launch ubuntu:22.04 --vm my-vm
```

## using an ansible playbook (NOT WORKING)
```bash
ansible-playbook -i inventory.yml create-lxd-vm.yml
```

inventory.yml for a local lxd server using the lxd connection plugin
```yaml
all:
  hosts:
    localhost:
      ansible_connection: lxd
```

create-lxd-vm.yml
```yaml
---
- hosts: localhost
  tasks:
    - name: Create a lxd vm
      lxd_container:
        name: my-vm
        state: started
        source:
          type: image
          mode: pull
          server: https://cloud-images.ubuntu.com/daily
          protocol: simplestreams
          alias: focal/amd64
        profiles:
          - default
```

# Add the user rcpaffenroth to the above vm using an ansible playbook and the lxd connection plugin

lxd.yml
```yaml
# simple lxd.yml including virtual machines and containers
plugin: community.general.lxd
url: unix:/var/snap/lxd/common/lxd/unix.socket
type_filter: both

groupby:
  typeVM:
    type: type
    attribute: virtual-machine
```

Check the inventory file
```bash
ansible-inventory -i lxd.yml --list
ansible-inventory -i lxd.yml --graph all
```

FIXME:  THIS IS NOT WORKING.  It breaks on a mkdir command.  I think that the lxd plugin is not working correctly.  I am not sure what is going on.  I will have to investigate further.

```bash
ansible-playbook -i inventory.yml add-user-to-lxd-vm.yml
```

add-user-to-lxd-vm.yml
```yaml
---
- hosts: my-vm
  tasks:
    - name: Add user rcpaffenroth to the vm
      user:
        name: rcpaffenroth
        state: present
        groups: sudo
        append: yes
``` 

# add a user to the lxd group
```bash
sudo usermod -a -G lxd $USER
```

# Create a lxd vm using the lxc command line tool ```bash
lxc launch ubuntu:20.04 my-vm
```

# List all lxd vms
```bash
lxc list
```

# Notes

Ok, I have things working, but it will take a bit more experimentation to see what is going on

```bash
ansible-playbook -i lxd.yml -i lxd_groups.yml  add-user-to-lxd-vm.yml
```

seems to work, but it needs both inventory files. The first one is for the lxd connection plugin, and the second sets the groups that I need.  It doesn't seem to be able to do both at once.  I.e., the ansible inventory file is parsed using the appropriate plugin, and the lxd plugin only does a subset of the things that the yml plugin done.

