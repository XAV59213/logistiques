# pages/11_Messages.py
"""
Page Messages
Messagerie réelle basée sur la table SQLite messages.
"""

import pandas as pd
import streamlit as st

import utils.database as db


def _format_recipients(rows: list) -> list[dict]:
    recipients = []
    for row in rows:
        item = dict(row)
        recipients.append(
            {
                "label": f"{item['username']} ({item['role']}) - {item['email']}",
                "id": int(item["id"]),
                "username": item["username"],
                "email": item["email"],
                "role": item["role"],
            }
        )
    return recipients


def show() -> None:
    st.title("✉️ Messages")
    st.caption("Communication interne entre administrateurs et utilisateurs")

    user = st.session_state.get("user")
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    user_id = int(user["id"])
    user_role = user.get("role", "")

    tab_inbox, tab_new, tab_sent = st.tabs(
        ["📥 Boîte de réception", "✍️ Nouveau message", "📤 Messages envoyés"]
    )

    with tab_inbox:
        st.subheader("Messages reçus")
        messages = db.get_received_messages(user_id)

        if not messages:
            st.info("Aucun message reçu.")
        else:
            unread_count = sum(1 for m in messages if int(dict(m).get("is_read", 0)) == 0)
            st.metric("Messages non lus", unread_count)

            for msg in messages:
                msg = dict(msg)
                with st.container(border=True):
                    st.markdown(f"### {msg['subject']}")
                    st.caption(
                        f"De : {msg['sender_name']} ({msg['sender_email']}) • {msg['created_at']}"
                    )
                    st.write(msg["body"])
                    st.write(f"**Statut :** {'Lu' if int(msg['is_read']) == 1 else 'Non lu'}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if int(msg["is_read"]) == 0:
                            if st.button(
                                "Marquer comme lu",
                                key=f"read_{msg['id']}",
                                use_container_width=True,
                            ):
                                db.mark_message_read(int(msg["id"]), 1)
                                st.rerun()
                    with col2:
                        if int(msg["is_read"]) == 1:
                            if st.button(
                                "Remettre non lu",
                                key=f"unread_{msg['id']}",
                                use_container_width=True,
                            ):
                                db.mark_message_read(int(msg["id"]), 0)
                                st.rerun()

    with tab_new:
        st.subheader("Envoyer un nouveau message")

        recipient_rows = db.get_message_recipients_for_user(user_role)
        recipients = _format_recipients(recipient_rows)

        if not recipients:
            st.warning("Aucun destinataire disponible.")
        else:
            recipient_labels = [r["label"] for r in recipients]
            selected_label = st.selectbox("Destinataire", recipient_labels)
            selected_recipient = next(r for r in recipients if r["label"] == selected_label)

            subject = st.text_input("Sujet du message").strip()
            message_body = st.text_area("Message", height=220).strip()

            if st.button("📤 Envoyer le message", type="primary", use_container_width=True):
                if not subject or not message_body:
                    st.warning("Veuillez remplir le sujet et le message.")
                else:
                    try:
                        db.create_message(
                            sender_id=user_id,
                            recipient_id=int(selected_recipient["id"]),
                            subject=subject,
                            body=message_body,
                        )
                        st.success("✅ Message envoyé avec succès.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'envoi : {e}")

    with tab_sent:
        st.subheader("Messages envoyés")
        sent_messages = db.get_sent_messages(user_id)

        if not sent_messages:
            st.info("Aucun message envoyé.")
        else:
            rows = []
            for msg in sent_messages:
                msg = dict(msg)
                rows.append(
                    {
                        "Sujet": msg["subject"],
                        "Destinataire": msg["recipient_name"] or "Destinataire inconnu",
                        "Email": msg["recipient_email"] or "-",
                        "Date": msg["created_at"],
                        "Lu": "Oui" if int(msg["is_read"]) == 1 else "Non",
                    }
                )

            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            with st.expander("Voir le détail des messages envoyés", expanded=False):
                for msg in sent_messages:
                    msg = dict(msg)
                    with st.container(border=True):
                        st.markdown(f"### {msg['subject']}")
                        st.caption(
                            f"À : {msg['recipient_name'] or 'Destinataire inconnu'} "
                            f"({msg['recipient_email'] or '-'}) • {msg['created_at']}"
                        )
                        st.write(msg["body"])
                        st.write(f"**Lu :** {'Oui' if int(msg['is_read']) == 1 else 'Non'}")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
