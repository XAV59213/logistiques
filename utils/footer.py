import streamlit as st
from datetime import datetime
import socket

def show_footer():
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except:
        ip = "Serveur"

    heure = datetime.now().strftime("%d/%m/%Y %H:%M")

    st.markdown(
        f"""
        <style>
        .footer-pro {{
            position: fixed;
            bottom: 0;
            left: 272px;
            right: 0;
            background: #0b3b6e;
            color: white;
            padding: 8px 20px;
            font-size: 14px;
            z-index: 9999;
            border-top: 2px solid #1d5fa7;
        }}
        .footer-pro span {{
            margin-right: 25px;
        }}
        </style>

        <div class="footer-pro">
            <span>🏛️ Ville de Marly</span>
            <span>💻 Logistique Pro v2.0</span>
            <span>🕒 {heure}</span>
            <span>🌐 {ip}</span>
            <span>👨‍💻 <a href='mailto:descampsxavier@free.fr' style='color:white;text-decoration:none;'>Xavier59213</a></span>
        </div>
        """,
        unsafe_allow_html=True
    )
