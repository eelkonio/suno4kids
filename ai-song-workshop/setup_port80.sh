#!/bin/bash

# Setup script to allow Python to bind to port 80
# Run this on the EC2 instance after deployment

echo "Setting up Python to bind to port 80..."

# Get the Python executable path
PYTHON_PATH=$(readlink -f venv/bin/python)

echo "Python path: $PYTHON_PATH"

# Give Python permission to bind to privileged ports (< 1024)
sudo setcap 'cap_net_bind_service=+ep' "$PYTHON_PATH"

echo "✓ Python can now bind to port 80"

# Verify
getcap "$PYTHON_PATH"
