#!/bin/bash
# =============================================
# INSTALLATION DIRECTE - Logistique Pro
# Ville de Marly
# =============================================

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

echo "🚛 Installation de Logistique Pro - Ville de Marly"
echo "=================================================="

cd "$APP_DIR"

echo "📁 Dossier application : $APP_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3 n'est pas installé."
    exit 1
fi

echo "🐍 Version Python détectée : $(python3 --version)"

echo "🧹 Préparation de l'environnement virtuel..."
if [ -d "$VENV_DIR" ]; then
    echo "ℹ️ Environnement existant détecté."
else
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "⬆️ Mise à jour de pip, setuptools et wheel..."
pip install --upgrade pip setuptools wheel

if [ ! -f "$APP_DIR/requirements.txt" ]; then
    echo "❌ Fichier requirements.txt introuvable."
    exit 1
fi

echo "📦 Installation des dépendances Python..."
pip install -r requirements.txt

echo "⚙️ Vérification du fichier .env..."
if [ ! -f "$APP_DIR/.env" ]; then
    if [ -f "$APP_DIR/.env.example" ]; then
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        echo "✅ Fichier .env créé à partir de .env.example"
    else
        echo "⚠️ Aucun .env.example trouvé. Le fichier .env n'a pas été créé."
    fi
else
    echo "✅ Fichier .env déjà présent"
fi

echo "🗄️ Initialisation de la base de données..."
python -c "from utils.database import init_database; init_database(); print('✅ Base de données initialisée')"

echo ""
echo "🎉 Installation terminée avec succès"
echo ""
echo "Pour lancer l'application :"
echo "cd \"$APP_DIR\""
echo "source .venv/bin/activate"
echo "streamlit run main.py --server.address 0.0.0.0 --server.port 8501 --server.headless true"
echo ""
