# utils/style.py
import streamlit as st
from config import DEFAULT_CONFIG
from typing import Dict

def apply_global_style() -> None:
    """Applique le style CSS global professionnel avec support des 3 thèmes."""
    
    # Récupération du thème choisi par l'utilisateur (stocké dans session_state)
    current_theme = st.session_state.get("theme", DEFAULT_CONFIG["default_theme"])
    
    # Définition des palettes de couleurs
    themes: Dict[str, Dict[str, str]] = {
        "Municipal Bleu": {
            "primary": "#003366",
            "secondary": "#f8f9fa",
            "accent": "#ffc107",
            "text": "#ffffff",
            "background": "#f8f9fa",
            "card_bg": "#ffffff",
        },
        "Mode Clair": {
            "primary": "#1a73e8",
            "secondary": "#f8f9fa",
            "accent": "#34a853",
            "text": "#202124",
            "background": "#ffffff",
            "card_bg": "#f8f9fa",
        },
        "Mode Sombre": {
            "primary": "#8ab4f8",
            "secondary": "#2d2d2d",
            "accent": "#fbbc05",
            "text": "#e8eaed",
            "background": "#1f1f1f",
            "card_bg": "#2d2d2d",
        }
    }
    
    theme = themes.get(current_theme, themes["Municipal Bleu"])
    
    css = f"""
    <style>
        /* ====================== STYLE GLOBAL ====================== */
        .main {{
            background-color: {theme['background']};
            color: {theme['text']};
        }}
        
        /* Titres */
        h1, h2, h3, h4, h5, h6 {{
            color: {theme['primary']};
            font-weight: 600;
        }}
        
        /* Sidebar */
        .css-1d391kg, .stSidebar {{
            background-color: {theme['card_bg']};
        }}
        
        /* Boutons principaux */
        .stButton>button {{
            background-color: {theme['primary']};
            color: white;
            border-radius: 8px;
            font-weight: 500;
            border: none;
            transition: all 0.3s ease;
        }}
        
        .stButton>button:hover {{
            background-color: #002244;
            box-shadow: 0 4px 12px rgba(0, 51, 102, 0.3);
        }}
        
        /* Cards */
        .stCard, div[data-testid="stExpander"] > div {{
            background-color: {theme['card_bg']};
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
            border: 1px solid #e9ecef;
        }}
        
        /* Notifications */
        .notification-card {{
            background-color: #fff8e1;
            border-left: 5px solid {theme['accent']};
            padding: 16px;
            border-radius: 10px;
            margin-bottom: 12px;
        }}
        
        /* Stock colors */
        .stock-ok {{ color: #34a853; font-weight: 600; }}
        .stock-low {{ color: #f57c00; font-weight: 600; }}
        .stock-critical {{ color: #d32f2f; font-weight: 700; }}
        
        /* Footer */
        .custom-footer {{
            text-align: center;
            color: #6c757d;
            font-size: 0.85rem;
            padding: 20px 0;
            border-top: 1px solid #e9ecef;
            margin-top: 40px;
        }}
        
        /* Amélioration générale */
        .stAlert {{ border-radius: 10px; }}
    </style>
    """
    
    st.markdown(css, unsafe_allow_html=True)


def set_theme(theme_name: str) -> None:
    """Change le thème de l'utilisateur et le sauvegarde dans session_state."""
    if theme_name in ["Municipal Bleu", "Mode Clair", "Mode Sombre"]:
        st.session_state.theme = theme_name
        st.rerun()
