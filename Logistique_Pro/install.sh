#!/usr/bin/env bash
set -e

echo "== Installation Logistique Pro - Ville de Marly =="

command -v python3 >/dev/null 2>&1 || { echo "Python3 requis"; exit 1; }

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

mkdir -p data/backups data/reservations data/stock data/inventaires
mkdir -p assets/icons assets/photos utils pages

[ -f .env ] || cp .env.example .env

echo "Installation terminée."
echo "Lancer avec : streamlit run main.py"
