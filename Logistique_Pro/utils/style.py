# utils/style.py
from typing import Dict

import streamlit as st

import utils.database as db
from config import DEFAULT_CONFIG


def get_visual_settings() -> Dict[str, str]:
    def _safe_setting(key: str, default: str) -> str:
        try:
            value = db.get_setting(key, default)
            return value if value else default
        except Exception:
            return default

    return {
        "site_title": _safe_setting("site_title", DEFAULT_CONFIG["site_title"]),
        "site_subtitle": _safe_setting("site_subtitle", DEFAULT_CONFIG["site_subtitle"]),
        "primary_color": _safe_setting("primary_color", DEFAULT_CONFIG["primary_color"]),
        "secondary_color": _safe_setting("secondary_color", DEFAULT_CONFIG["secondary_color"]),
        "accent_color": _safe_setting("accent_color", DEFAULT_CONFIG["accent_color"]),
    }


def apply_global_style() -> None:
    current_theme = st.session_state.get("theme", DEFAULT_CONFIG["default_theme"])
    visual = get_visual_settings()

    theme_presets: Dict[str, Dict[str, str]] = {
        "Municipal Bleu": {
            "background": visual["secondary_color"],
            "card_bg": "#ffffff",
            "sidebar_bg": "#f8fbff",
            "text": "#1f2937",
            "muted_text": "#6b7280",
            "border": "#dbe3ec",
            "button_text": "#ffffff",
        },
        "Mode Clair": {
            "background": "#ffffff",
            "card_bg": "#f8f9fa",
            "sidebar_bg": "#f7f8fa",
            "text": "#202124",
            "muted_text": "#5f6368",
            "border": "#dadce0",
            "button_text": "#ffffff",
        },
        "Mode Sombre": {
            "background": "#1f1f1f",
            "card_bg": "#2d2d2d",
            "sidebar_bg": "#202124",
            "text": "#e8eaed",
            "muted_text": "#9aa0a6",
            "border": "#3c4043",
            "button_text": "#ffffff",
        },
    }

    theme = theme_presets.get(current_theme, theme_presets["Municipal Bleu"])

    css = f"""
    <style>
        :root {{
            --primary-color: {visual["primary_color"]};
            --secondary-color: {visual["secondary_color"]};
            --accent-color: {visual["accent_color"]};
            --bg-color: {theme["background"]};
            --card-bg: {theme["card_bg"]};
            --sidebar-bg: {theme["sidebar_bg"]};
            --text-color: {theme["text"]};
            --muted-text: {theme["muted_text"]};
            --border-color: {theme["border"]};
            --button-text: {theme["button_text"]};
        }}

        html, body, [data-testid="stAppViewContainer"], .main {{
            background-color: var(--bg-color);
            color: var(--text-color);
        }}

        .main .block-container {{
            padding-top: 1.2rem;
            padding-bottom: 1rem;
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: var(--primary-color);
            font-weight: 700;
        }}

        p, span, label, div {{
            color: inherit;
        }}

        section[data-testid="stSidebar"] {{
            background: var(--sidebar-bg);
            border-right: 1px solid var(--border-color);
        }}

        div[data-testid="metric-container"] {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 12px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
        }}

        .stButton > button,
        .stDownloadButton > button {{
            background: var(--primary-color);
            color: var(--button-text);
            border: none;
            border-radius: 10px;
            padding: 0.55rem 1rem;
            font-weight: 600;
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover {{
            filter: brightness(0.95);
        }}

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        textarea,
        input {{
            border-radius: 10px !important;
        }}

        .notification-card {{
            background-color: var(--card-bg);
            border-left: 5px solid var(--accent-color);
            padding: 16px;
            border-radius: 10px;
            margin-bottom: 12px;
        }}

        .stock-ok {{
            color: #34a853;
            font-weight: 600;
        }}

        .stock-low {{
            color: #f57c00;
            font-weight: 600;
        }}

        .stock-critical {{
            color: #d32f2f;
            font-weight: 700;
        }}

        .custom-footer {{
            text-align: center;
            color: var(--muted-text);
            font-size: 0.85rem;
            padding: 20px 0;
            border-top: 1px solid var(--border-color);
            margin-top: 40px;
        }}

        .stAlert {{
            border-radius: 10px;
        }}

        hr {{
            border: none;
            border-top: 1px solid var(--border-color);
            margin: 1rem 0;
        }}
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)


def set_theme(theme_name: str) -> None:
    if theme_name in ["Municipal Bleu", "Mode Clair", "Mode Sombre"]:
        st.session_state.theme = theme_name
        st.rerun()
