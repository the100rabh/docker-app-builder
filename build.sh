#!/bin/bash

# This script builds a standalone executable for the Docker App Builder using PyInstaller.
# The final executable will be located in the 'dist' directory.

set -e

echo "--- Installing/Updating PyInstaller ---"
./venv/bin/pip install -U pyinstaller

echo "--- Cleaning up previous builds ---"
rm -rf build/
rm -rf dist/
rm -f DockerAppBuilder.spec

echo "--- Building executable ---"
# --windowed: Prevents a console from opening for the GUI
# --onefile: Bundles everything into a single executable
# --name: Specifies the name of the final executable
./venv/bin/pyinstaller --name DockerAppBuilder \
                      --onefile \
                      --windowed \
                      --clean \
                      docker_app_builder/main.py

echo ""
echo "--- Build complete! ---"
echo "To run the application, execute the following command:"
echo "./dist/DockerAppBuilder"
