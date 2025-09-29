#!/usr/bin/env bash

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Install the package in development mode using uv
echo "Installing rcp-lxd package using uv..."
source .venv/bin/activate
uv pip install -e .

echo ""
echo "Installation complete! You can now use the 'rcp_lxd' command."
echo ""
echo "To activate the environment in your current shell:"
echo "  source .venv/bin/activate"
echo ""
echo "Available commands:"
echo "  rcp_lxd clean --name <container_name>    # Stop and remove a container"
echo "  rcp_lxd create --name <container_name>   # Create a new container"
echo "  rcp_lxd run-ansible --name <container>   # Run Ansible playbooks"
echo ""
echo "For help on any command, use:"
echo "  rcp_lxd <command> --help"