#!/usr/bin/env bash
set -e

echo "== Installation Logistique Pro - Ville de Marly =="

command -v python3 >/dev/null 2>&1 || { echo "Python3 requis"; exit 1; }

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

mkdir -p data
mkdir -p data/backups
mkdir -p data/reservations
mkdir -p data/stock
mkdir -p data/inventaires

mkdir -p assets/css
mkdir -p assets/icons
mkdir -p assets/photos

mkdir -p static/photos
mkdir -p docs
mkdir -p utils
mkdir -p pages

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
  else
    echo "Fichier .env.example manquant"
    exit 1
  fi
fi

echo "Installation terminée."
echo "Active l'environnement : source .venv/bin/activate"
echo "Puis lance : streamlit run main.py"
