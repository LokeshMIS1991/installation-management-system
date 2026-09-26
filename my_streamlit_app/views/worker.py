import pandas as pd
import plotly.express as px
import streamlit as st
from core.db import read_sheet, update_sheet_row
from utils.excel import generate_excel_download
from views.components import render_restricted_work_input


def render_dashboard(user):
    user_name = user.get("name", "User")
    user_designation = user.get("designation", "Worker")

    st.header(f"⚡ Daily Workspace & Task Pipeline — {user_name} ({user_designation})")
    st.caption("Track your assigned site duties, update live task progress, and view performance metrics.")

    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    st.markdown("### 🏆 Performance & Metrics Scorecard")

    my_logs = pd.DataFrame()
    if not df_logs.empty and "worker_name" in df_logs.columns:
        my_logs = df_logs[
            df_logs["worker_name"].astype(str).str.strip().str.lower()
            == user_name.strip().lower()
        ]

    days_worked = (
        my_logs["logged_date"].nunique()
        if not my_logs.empty and "logged_date" in my_logs.columns
        else 0
    )
    days_travelled = (
        len(my_logs[my_logs["is_travel_day"] == "Yes"])
        if not my_logs.empty and "is_travel_day" in my_logs.columns
        else 0
    )
    total_hours = (
        my_logs["hours_spent"].sum()
        if not my_logs.empty and "hours_spent" in my_logs.columns
        else 0
    )

    avg_handover_days = "N/A"
    if not df_sites.empty and "installation_id" in df_sites.columns:
        my_site_ids = my_logs["installation_id"].unique() if not my_logs.empty else []
        my_sites = df_sites[df_sites["installation_id"].isin(my_site_ids)].copy()

        if (
            not my_sites.empty
            and "order_date" in my_sites.columns
            and "handover_date" in my_sites.columns
        ):
            my_sites["order_dt"] = pd.to_datetime(
                my_sites["order_date"], errors="coerce"
            )
            my_sites["handover_dt"] = pd.to_datetime(
                my_sites["handover_date"], errors="coerce"
            )
            my_sites["duration"] = (
                my_sites["handover_dt"] - my_sites["order_dt"]
            ).dt.days
            valid_durations = my_sites["duration"].dropna()
            if not valid_durations.empty:
                avg_handover_days = f"{round(valid_durations.mean(), 1)} Days"

    perf_score = int((total_hours * 2) + (days_travelled * 15) + (days_worked * 10))

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">{days_worked}</div><div class="kpi-label">Days Worked</div></div>',
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">{days_travelled}</div><div class="kpi-label">Travel Days</div></div>',
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">{total_hours} hrs</div><div class="kpi-label">Total Hours</div></div>',
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">{avg_handover_days}</div><div class="kpi-label">Avg Handover Speed</div></div>',
            unsafe_allow_html=True,
        )
    with k5:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number" style="color:#00A859;">{perf_score} pts</div><div class="kpi-label">Performance Score</div></div>',
            unsafe_allow_html=True,
        )


def render_performance_history(user):
    user_name = user.get("name", "User")
    st.header(f"📊 Detailed Performance Report — {user_name}")

    df_logs = read_sheet("Worker_Daily_Logs")

    if df_logs.empty or "worker_name" not in df_logs.columns:
        st.info("⚠️ No Field Logs Recorded Yet")
    else:
        my_logs = df_logs[
            df_logs["worker_name"].astype(str).str.strip().str.lower()
            == user_name.strip().lower()
        ]

        if my_logs.empty:
            st.info("⚠️ You have not submitted any daily work logs yet.")
        else:
            excel_bytes = generate_excel_download(
                my_logs, f"{user_name}_Performance_Report.xlsx"
            )
            st.download_button(
                "📥 Download Performance Excel Report",
                data=excel_bytes,
                file_name=f"{user_name}_Performance_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.write("##")
            st.subheader("📈 Execution Breakdown")
            c_g1, c_g2 = st.columns(2)

            with c_g1:
                fig_hrs = px.bar(
                    my_logs,
                    x="logged_date",
                    y="hours_spent",
                    color="installation_id",
                    title="Daily Hours Logged per Site",
                )
                st.plotly_chart(fig_hrs, use_container_width=True)

            with c_g2:
                if "task_category" in my_logs.columns:
                    fig_pie = px.pie(
                        my_logs,
                        names="task_category",
                        values="hours_spent",
                        title="Time Distribution by Task Category",
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

            st.divider()
            st.subheader(f"📜 Submitted Work Logs ({len(my_logs)} Entries)")
            disp_cols = [
                c
                for c in [
                    "log_id",
                    "site_day",
                    "logged_date",
                    "installation_id",
                    "worker_role",
                    "team_lead_name",
                    "task_category",
                    "task_name",
                    "hours_spent",
                    "minutes_spent",
                    "is_travel_day",
                    "site_remarks",
                ]
                if c in my_logs.columns
            ]
            st.dataframe(
                my_logs[disp_cols].sort_values(by="logged_date", ascending=False),
                use_container_width=True,
            )


def render_profile(user):
    user_name = user.get("name", "User")
    user_role = user.get("role", "Worker")
    user_designation = user.get("designation", user_role)
    user_id = user.get("worker_id", "N/A")
    user_base_location = user.get("base_location", "Jaipur")

    st.header("👤 Profile & Security Settings")

    col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
    with col_center:
        st.markdown(
            f"""
            <div class="card-box">
                <h3 style="margin:0;">{user_name}</h3>
                <p style="margin:5px 0;"><b>Designation:</b> {user_designation}</p>
                <p style="margin:5px 0;"><b>Access Role:</b> {user_role}</p>
                <p style="margin:5px 0;"><b>Work ID:</b> {user_id}</p>
                <p style="margin:5px 0;"><b>Base Station:</b> {user_base_location}</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        st.subheader("🔑 Change Security PIN")
        with st.form("change_pin_form"):
            curr_pin = st.text_input("Current PIN", type="password")
            new_pin1 = st.text_input("New 4-Digit PIN", type="password", max_chars=4)
            new_pin2 = st.text_input("Confirm New PIN", type="password", max_chars=4)

            update_pin_btn = st.form_submit_button(
                "Update Security PIN", use_container_width=True
            )

            if update_pin_btn:
                if str(curr_pin).strip() != str(user.get("pin", "")).strip():
                    st.error("Incorrect current PIN!")
                elif not new_pin1 or len(new_pin1) < 4:
                    st.error("New PIN must be at least 4 digits.")
                elif new_pin1 != new_pin2:
                    st.error("New PINs do not match!")
                else:
                    success = update_sheet_row(
                        "Workers_Master", "name", user_name, {"pin": new_pin1.strip()}
                    )
                    if success:
                        st.session_state.authenticated_user["pin"] = new_pin1.strip()
                        st.success("PIN updated successfully!")
                        st.rerun()
