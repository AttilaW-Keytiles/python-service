#!/bin/bash

echo "Starting service now..."

# setup Virtual Env
if [ ! -d ".venv" ]; then
  # just needed once
  echo "It looks this is your first time... building Virtual Environment and dependencies..."
  python -m venv .venv
  source .venv/Scripts/activate
  pip install -e .
else
  # just activate
  source .venv/Scripts/activate
fi

# let's start the App
python main.py --cfg local_workfolder/conf/config.yaml --logCfg local_workfolder/conf/log-config.yaml