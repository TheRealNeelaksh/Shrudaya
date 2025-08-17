#!/bin/bash

# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Run the Uvicorn server
# The $PORT variable is automatically provided by Render.
uvicorn server:app --host 0.0.0.0 --port $PORT