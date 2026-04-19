cd /opt/logistique-pro/Logistique_Pro

cat > install.sh << 'EOF'
#!/bin/bash
# =============================================
# INSTALLATION COMPLETE - Logistique Pro Ville de Marly
# Version Clean & Robust - Avril 2026
# =============================================

set -e  # Arrête le script en cas d'erreur

APP_DIR="/opt/logistique-pro/Logistique_Pro"
VENV_DIR="$APP_DIR/.venv"

echo "🚛 Installation Logistique Pro - Ville de Marly"
echo "================================================"

cd "$APP_DIR"

# ====================== 1. ARRÊT DE TOUS LES SERVICES ======================
echo "🛑 Arrêt de tous les services en cours..."
pkill -f streamlit || true
pkill -f "python.*main.py" || true
pkill -f "python.*Logistique_Pro" || true
sleep 4

# ====================== 2. NETTOYAGE COMPLET (suppression des fichiers inutiles) ======================
echo "🧹 Nettoyage complet avant installation..."

# Suppression de l'ancien environnement
rm -rf "$VENV_DIR" __pycache__ *.pyc .streamlit/cache/

# Suppression des caches Python partout
find "$APP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$APP_DIR" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# Gestion du dossier pages / app_pages
if [ -d "app_pages" ] && [ ! -d "pages" ]; then
    echo "🔄 Renommage app_pages → pages"
    mv app_pages pages
fi

# ====================== 3. SAUVEGARDE DES BASES DE DONNÉES ======================
echo "💾 Sauvegarde des bases de données..."
TIMESTAMP=$(date +%Y%m%d_%H%M)
cp -n database.db "database_${TIMESTAMP}.bak" 2>/dev/null || true
cp -n logistique.db "logistique_${TIMESTAMP}.bak" 2>/dev/null || true

# ====================== 4. CRÉATION D'UN NOUVEL ENVIRONNEMENT VIRTUEL ======================
echo "🐍 Création d'un nouvel environnement virtuel propre..."
python3 -m venv "$VENV_DIR" --upgrade-deps

# ====================== 5. INSTALLATION DES DÉPENDANCES ======================
echo "🔌 Activation de l'environnement..."
source "$VENV_DIR/bin/activate"

echo "⬆️ Mise à jour de pip..."
pip install --upgrade pip wheel setuptools --quiet

echo "📦 Installation des packages (cela peut prendre 2-3 minutes)..."
pip install -r requirements.txt --no-cache-dir

# Installation forcée du package manquant (souvent oublié)
pip install streamlit-option-menu --quiet

echo "🗄️ Initialisation de la base de données..."
python -c '
from utils.database import init_database
init_database()
print("✅ Base de données initialisée avec toutes les tables")
' 2>&1 | cat

# ====================== FIN ======================
echo ""
echo "🎉 Installation terminée avec succès !"
echo ""
echo "Pour lancer l'application :"
echo "   cd $APP_DIR"
echo "   source .venv/bin/activate"
echo "   streamlit run main.py --server.address 0.0.0.0 --server.port 8501 --server.headless true"
echo ""
EOF

# Rend le script exécutable
chmod +x install.sh

echo "✅ Nouveau install.sh complet créé avec succès !"
echo "Tu peux maintenant lancer l'installation avec : ./install.sh"
