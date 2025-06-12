#!/usr/bin/env bash
set -e

python3 -m venv .venv

source .venv/bin/activate

pip install --upgrade pip
pip install -e .

echo "\n✅ Environment created. Activate it with 'source .venv/bin/activate'"
