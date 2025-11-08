#!/bin/bash
# Seed database with test data

set -e

echo "Seeding database with test data..."
source .venv/bin/activate
python scripts/seed_data.py
