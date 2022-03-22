#!/bin/bash

# Start up script for the API service (referenced by Dockerfile).

set -eu

# Update the database schema
alembic upgrade head

# Run the application
uvicorn narrativelog.main:app --host 0.0.0.0 --port 8080
