#!/bin/bash
# =============================================
# INSTALLATION COMPLETE - Logistique Pro Ville de Marly
# Version Clean & Robust - Avril 2026
# =============================================

set -e

APP_DIR="/opt/logistique-pro"
VENV_DIR="$APP_DIR/.venv"

echo "🚛 Installation Logistique Pro - Ville de Marly"
echo "================================================"

cd "$APP_DIR"

# 1. ARRÊT DE TOUS LES SERVICES
echo "🛑 Arrêt de tous les services en cours..."
pkill -f streamlit || true
pkill -f "python.*main.py" || true
sleep 4

# 2. NETTOYAGE TOTAL
echo "🧹 Nettoyage complet avant installation..."
rm -rf "$VENV_DIR" __pycache__ *.pyc .streamlit/cache/ 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 3. SAUVEGARDE DES BASES DE DONNÉES
echo "💾 Sauvegarde des bases de données..."
TIMESTAMP=$(date +%Y%m%d_%H%M)
cp -n database.db "database_${TIMESTAMP}.bak" 2>/dev/null || true
cp -n logistique.db "logistique_${TIMESTAMP}.bak" 2>/dev/null || true

# 4. CRÉATION D'UN NOUVEL ENVIRONNEMENT VIRTUEL
echo "🐍 Création d'un nouvel environnement virtuel..."
python3 -m venv "$VENV_DIR" --upgrade-deps

# 5. INSTALLATION DES DÉPENDANCES
echo "🔌 Activation de l'environnement..."
source "$VENV_DIR/bin/activate"

echo "⬆️ Mise à jour de pip..."
pip install --upgrade pip wheel setuptools --quiet

echo "📦 Installation des packages..."
pip install -r requirements.txt --no-cache-dir
pip install streamlit-option-menu --quiet

# 6. INITIALISATION DE LA BASE DE DONNÉES
echo "🗄️ Initialisation de la base de données..."
python -c '
from utils.database import init_database
init_database()
print("✅ Base de données initialisée avec succès")
' 2>&1 | cat

echo ""
echo "🎉 Installation terminée avec succès !"
echo ""
echo "Pour lancer l'application :"
echo "   source .venv/bin/activate"
echo "   streamlit run main.py --server.address 0.0.0.0 --server.port 8501 --server.headless true"
