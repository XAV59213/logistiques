cd /opt/logistique-pro/Logistique_Pro
cat > install.sh << 'EOF'
#!/bin/bash

# =============================================
# Installation Logistique Pro - Ville de Marly
# Version Clean & Robust (2026)
# =============================================

set -e  # Arrête le script en cas d'erreur

APP_DIR="/opt/logistique-pro/Logistique_Pro"
VENV_DIR="$APP_DIR/.venv"

echo "🚛 Installation Logistique Pro - Ville de Marly"
echo "================================================"

# Vérification du répertoire
if [ ! -d "$APP_DIR" ]; then
    echo "❌ Erreur : Le dossier $APP_DIR n'existe pas !"
    exit 1
fi

cd "$APP_DIR"

# === 1. ARRÊT DE TOUS LES SERVICES EN COURS ===
echo "🛑 Arrêt de tous les processus Streamlit et Python..."
pkill -f streamlit || true
pkill -f "python.*main.py" || true
pkill -f "streamlit run" || true
pkill -f "python.*Logistique_Pro" || true
sleep 4

# === 2. NETTOYAGE COMPLET DE LA VM ===
echo "🧹 Nettoyage complet de l'installation précédente..."
rm -rf "$VENV_DIR"
find "$APP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$APP_DIR" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
rm -rf *.pyc .streamlit/cache/ 2>/dev/null || true

# Gestion du dossier pages / app_pages (compatibilité)
if [ -d "app_pages" ] && [ ! -d "pages" ]; then
    echo "🔄 Renommage app_pages → pages..."
    mv app_pages pages
elif [ -d "pages" ]; then
    echo "✅ Dossier pages présent"
fi

# === 3. CRÉATION D'UN ENVIRONNEMENT VIRTUEL PROPRE ===
echo "🐍 Création d'un nouvel environnement virtuel..."
python3 -m venv "$VENV_DIR" --upgrade-deps

# === 4. INSTALLATION DES DÉPENDANCES ===
echo "🔌 Activation de l'environnement..."
source "$VENV_DIR/bin/activate"

echo "⬆️ Mise à jour de pip..."
pip install --upgrade pip wheel setuptools --quiet

echo "📦 Installation des packages (cela peut prendre 2-3 minutes)..."
pip install -r requirements.txt --no-cache-dir

echo ""
echo "✅ Installation terminée avec succès ! 🎉"
echo ""
echo "Pour lancer l'application maintenant :"
echo "   cd $APP_DIR"
echo "   source .venv/bin/activate"
echo "   streamlit run main.py --server.address 0.0.0.0 --server.port 8501 --server.headless true"
echo ""
EOF

# On rend le script exécutable
chmod +x install.sh

echo "✅ Nouveau install.sh installé et prêt à l'emploi !"
