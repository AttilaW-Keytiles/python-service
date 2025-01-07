#!/bin/bash

# just run once
if [ -d ".venv" ]; then
  echo "Oops it looks we are already initialized! Exiting..."
  exit 0
fi

# create virtual env
echo "Creating virtual environment..."
python -m venv .venv
echo "done"
# now activate
source .venv/Scripts/activate
echo "environment is activated"

# time to install dependencies
echo "installing dependencies..."
pip install -e .
echo "done"

echo "init script is finished!"
