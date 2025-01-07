#!/bin/bash

echo "Starting service now..."

# setup Virtual Env
if [ ! -d ".venv" ]; then
  # just needed once
  echo "It looks this is your first time... building Virtual Environment and dependencies..."

  # build local_workfolder dirs
  echo "Initializing local_workfolder ..."
  mkdir local_workfolder/data
  mkdir local_workfolder/logs
  mkdir local_workfolder/tmp
  echo "done"

  echo "Creating Virtual Environment ..."
  python -m venv .venv
  source .venv/Scripts/activate
  pip install -e .
else
  # just activate
  source .venv/Scripts/activate
fi

# let's start the App
python main.py --cfg local_workfolder/conf/config.yaml --logCfg local_workfolder/conf/log-config.yaml