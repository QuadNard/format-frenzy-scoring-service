#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
uvicorn main:app --app-dir ./src --host 0.0.0.0 --port 8080