import streamlit as st
from core.db import read_sheet
from core.styles import COLOR_ACCENT, COLOR_PRIMARY
from utils.helpers import LOGO_PATH


def init_session_state():
    if "authenticated_user" not in st.session_state:
        st.session_state.authenticated_user = None
    if "remembered_username" not in st.session_state:
        st.session_state.remembered_username = ""


def render_login_form():
    init_session_state()

    st.write("##")
    col_l, col_center, col_r = st.columns([1, 1.2, 1])
    with col_center:
        st.markdown(
            '<div style="max-width: 420px; margin: 0 auto;">', unsafe_allow_html=True
        )
        with st.form("login_form"):
            if LOGO_PATH.exists():
                st.image(str(LOGO_PATH), use_container_width=True)
            else:
                st.markdown(
                    f"""
                    <div style="text-align: center;">
                        <h1 style="color: {COLOR_PRIMARY}; margin: 0; font-size: 26px;">SIDHARTH</h1>
                        <p style="color: {COLOR_ACCENT}; font-weight: bold; margin: 0; font-size: 12px; letter-spacing: 2px;">SHUTTER & AUTOMATION</p>
                    </div>
                """,
                    unsafe_allow_html=True,
                )

            st.caption("Enterprise Operations & Field Portal")

            username_input = st.text_input(
                "Username / Name / Work ID",
                value=st.session_state.remembered_username,
                placeholder="e.g. Parvesh Kumar or W001",
            )
            password_input = st.text_input(
                "Password / PIN", type="password", placeholder="Enter password"
            )

            col_chk1, col_chk2 = st.columns(2)
            with col_chk1:
                show_pass = st.checkbox("Show Password")
            with col_chk2:
                remember_me = st.checkbox(
                    "Remember Me",
                    value=bool(st.session_state.remembered_username),
                )

            submit_button = st.form_submit_button(
                "🔑 LOGIN TO DASHBOARD", use_container_width=True
            )

            if submit_button:
                if not username_input or not password_input:
                    st.error("Please fill in both Username and Password.")
                else:
                    df_workers = read_sheet("Workers_Master")
                    if not df_workers.empty:
                        user_row = df_workers[
                            (
                                (
                                    df_workers["name"]
                                    .astype(str)
                                    .str.strip()
                                    .str.lower()
                                    == username_input.strip().lower()
                                )
                                | (
                                    df_workers["worker_id"]
                                    .astype(str)
                                    .str.strip()
                                    .str.lower()
                                    == username_input.strip().lower()
                                )
                            )
                            & (
                                df_workers["pin"].astype(str).str.strip()
                                == str(password_input).strip()
                            )
                        ]
                        if not user_row.empty:
                            st.session_state.authenticated_user = (
                                user_row.iloc[0].to_dict()
                            )
                            st.session_state.remembered_username = (
                                username_input.strip() if remember_me else ""
                            )
                            st.success("Authentication Successful!")
                            st.rerun()
                        else:
                            st.error("Invalid Username or Password.")
                    else:
                        st.error(
                            "⚠️ Database Unreachable — Verify Google Sheets setup."
                        )
        st.markdown("</div>", unsafe_allow_html=True)
