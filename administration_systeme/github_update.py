# -*- coding: utf-8 -*-
import streamlit as st

from administration_systeme.common import run_cmd


def render():
    st.subheader("Mise à jour GitHub sécurisée")

    st.warning(
        "Cette page ne redémarre pas Streamlit automatiquement. "
        "Après une mise à jour réussie, redémarre le service manuellement."
    )

    ok_branch, branch = run_cmd(["git", "branch", "--show-current"], timeout=10)
    branch = branch.strip() if ok_branch and branch.strip() else "main"

    ok_commit, commit = run_cmd(["git", "rev-parse", "--short", "HEAD"], timeout=10)
    ok_remote, remote = run_cmd(["git", "remote", "get-url", "origin"], timeout=10)

    c1, c2, c3 = st.columns(3)
    c1.metric("Branche", branch)
    c2.metric("Commit", commit.strip() if ok_commit else "N/A")
    c3.metric("Remote", "OK" if ok_remote else "N/A")

    if ok_remote:
        st.caption(remote)

    if st.button("Vérifier GitHub", width="stretch", key="git_fetch_mod"):
        ok, out = run_cmd(["git", "fetch", "--all", "--prune"], timeout=60)
        st.code(out, language="bash")

        ok2, out2 = run_cmd(["git", "status", "-sb"], timeout=20)
        st.code(out2, language="bash")

    confirm = st.checkbox("Je confirme vouloir mettre à jour depuis GitHub", key="git_confirm_pull_mod")

    if st.button("Mettre à jour maintenant", disabled=not confirm, type="primary", width="stretch", key="git_pull_mod"):
        ok, out = run_cmd(["git", "pull", "--ff-only", "origin", branch], timeout=120)

        if ok:
            st.success("Mise à jour GitHub terminée.")
            st.code("systemctl restart logistique.service", language="bash")
        else:
            st.error("Mise à jour GitHub échouée.")
            st.code(out, language="bash")
