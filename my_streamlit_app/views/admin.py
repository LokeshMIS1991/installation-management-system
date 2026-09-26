from datetime import datetime, timedelta
import re
import pandas as pd
import plotly.express as px
import streamlit as st
from core.db import append_to_sheet, read_sheet, update_sheet_row
from utils.helpers import WORKER_DESIGNATIONS, generate_work_id, validate_email


def render_analytics():
    st.header("📊 Admin Operations & Expense Analytics")

    df_logs = read_sheet("Worker_Daily_Logs")
    df_expenses = read_sheet("Expense_Logs")
    df_sites = read_sheet("Sites_Master")

    active_site_ids = []
    if not df_sites.empty and "installation_id" in df_sites.columns:
        df_sites_copy = df_sites.copy()
        df_sites_copy.columns = [
            str(col).strip().lower().replace(" ", "_") for col in df_sites_copy.columns
        ]

        running_sites = df_sites_copy[
            ~df_sites_copy["status"]
            .astype(str)
            .str.strip()
            .str.title()
            .isin(["Handovered", "Handover", "Completed"])
        ]
        active_site_ids = running_sites["installation_id"].unique().tolist()

    if not df_logs.empty and active_site_ids:
        df_logs = df_logs[df_logs["installation_id"].isin(active_site_ids)]

    if df_logs.empty:
        st.info("No active log data available for running sites.")
        return

    sites_visited = (
        df_logs["installation_id"].nunique()
        if "installation_id" in df_logs.columns
        else 0
    )
    days_worked = (
        df_logs["logged_date"].nunique() if "logged_date" in df_logs.columns else 0
    )
    days_travelled = (
        len(df_logs[df_logs["is_travel_day"] == "Yes"])
        if "is_travel_day" in df_logs.columns
        else 0
    )

    travel_exp = (
        pd.to_numeric(df_expenses["travel_expense"], errors="coerce").sum()
        if not df_expenses.empty and "travel_expense" in df_expenses.columns
        else 0
    )
    stay_exp = (
        pd.to_numeric(df_expenses["stay_expense"], errors="coerce").sum()
        if not df_expenses.empty and "stay_expense" in df_expenses.columns
        else 0
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">{sites_visited}</div><div class="kpi-label">Active Sites Visited</div></div>',
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">{days_worked}</div><div class="kpi-label">Days Worked</div></div>',
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">{days_travelled}</div><div class="kpi-label">Days Travelled</div></div>',
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">₹{travel_exp:,.0f}</div><div class="kpi-label">Travel Expense</div></div>',
            unsafe_allow_html=True,
        )
    with k5:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">₹{stay_exp:,.0f}</div><div class="kpi-label">Stay Expense</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    g1, g2 = st.columns(2)
    with g1:
        st.subheader("⚠️ Problems & Delays Encountered")
        if "delay_category" in df_logs.columns:
            delay_df = df_logs[df_logs["delay_category"] != "No Delay"]
            if not delay_df.empty:
                fig_delay = px.bar(
                    delay_df,
                    x="delay_category",
                    color="installation_id",
                    title="Site Problems by Category (Running Sites)",
                )
                st.plotly_chart(fig_delay, use_container_width=True)
            else:
                st.success("No delays or problems reported across running sites!")

    with g2:
        st.subheader("💰 Worker Expenses Breakdown")
        if not df_expenses.empty and "worker_name" in df_expenses.columns:
            fig_exp = px.bar(
                df_expenses,
                x="worker_name",
                y=["travel_expense", "stay_expense"],
                title="Travel vs. Stay Expense per Worker",
                barmode="stack",
            )
            st.plotly_chart(fig_exp, use_container_width=True)


def render_sales_report():
    st.header("📊 Salesperson Performance & Orders Analytics")
    st.caption("Track order volume, project statuses, and revenue acquisition per Salesperson across custom time windows.")

    df_sites = read_sheet("Sites_Master")

    if df_sites.empty:
        st.warning("No site records found in Sites_Master.")
        return

    f1, f2 = st.columns([2, 2])
    with f1:
        time_filter = st.selectbox(
            "📅 Select Report Time Period:",
            [
                "All Time",
                "Last 15 Days",
                "Last 1 Month (30 Days)",
                "Last 3 Months (90 Days)",
                "Last 6 Months (180 Days)",
                "Last 9 Months (270 Days)",
                "Quarterly (90 Days)",
                "Last 1 Year (365 Days)",
            ],
        )

    filtered_sites = df_sites.copy()
    if "order_date" in filtered_sites.columns:
        filtered_sites["order_dt"] = pd.to_datetime(
            filtered_sites["order_date"], errors="coerce"
        )
        today = datetime.now()

        days_map = {
            "Last 15 Days": 15,
            "Last 1 Month (30 Days)": 30,
            "Last 3 Months (90 Days)": 90,
            "Last 6 Months (180 Days)": 180,
            "Last 9 Months (270 Days)": 270,
            "Quarterly (90 Days)": 90,
            "Last 1 Year (365 Days)": 365,
        }

        if time_filter in days_map:
            cutoff_date = today - timedelta(days=days_map[time_filter])
            filtered_sites = filtered_sites[
                filtered_sites["order_dt"] >= cutoff_date
            ]

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">{len(filtered_sites)}</div><div class="kpi-label">Orders Acquired</div></div>',
            unsafe_allow_html=True,
        )
    with k2:
        in_prog = (
            len(
                filtered_sites[
                    filtered_sites["status"]
                    .astype(str)
                    .str.strip()
                    .str.title()
                    == "In Progress"
                ]
            )
            if "status" in filtered_sites.columns
            else 0
        )
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number" style="color:#00A859;">{in_prog}</div><div class="kpi-label">Sites In Progress</div></div>',
            unsafe_allow_html=True,
        )
    with k3:
        on_hold = (
            len(
                filtered_sites[
                    filtered_sites["status"]
                    .astype(str)
                    .str.strip()
                    .str.title()
                    == "On Hold"
                ]
            )
            if "status" in filtered_sites.columns
            else 0
        )
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number" style="color:#D32F2F;">{on_hold}</div><div class="kpi-label">Sites On Hold</div></div>',
            unsafe_allow_html=True,
        )
    with k4:
        handovered = (
            len(
                filtered_sites[
                    filtered_sites["status"]
                    .astype(str)
                    .str.strip()
                    .str.title()
                    .isin(["Handovered", "Completed"])
                ]
            )
            if "status" in filtered_sites.columns
            else 0
        )
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">{handovered}</div><div class="kpi-label">Completed Handovers</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    if (
        "salesperson_name" in filtered_sites.columns
        or "salesperson_id" in filtered_sites.columns
    ):
        sp_col = (
            "salesperson_name"
            if "salesperson_name" in filtered_sites.columns
            else "salesperson_id"
        )

        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            st.subheader("📦 Total Orders Brought per Salesperson")
            fig_orders = px.bar(
                filtered_sites,
                x=sp_col,
                color="status",
                title=f"Orders & Status Breakdown ({time_filter})",
                barmode="stack",
            )
            st.plotly_chart(fig_orders, use_container_width=True)

        with c_chart2:
            st.subheader("🎯 Site Status Share")
            fig_pie = px.pie(
                filtered_sites,
                names="status",
                title=f"Site Execution Distribution ({time_filter})",
                hole=0.4,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("📜 Detailed Salesperson Order Records")
        disp_cols = [
            c
            for c in [
                "installation_id",
                "client_name",
                sp_col,
                "order_date",
                "deal_amount",
                "site_city",
                "status",
                "hold_reason",
            ]
            if c in filtered_sites.columns
        ]
        st.dataframe(filtered_sites[disp_cols], use_container_width=True)
    else:
        st.info("No salesperson assignment columns found in Sites_Master yet.")


def render_user_management():
    st.header("👥 Dynamic User & Access Management")
    df_workers = read_sheet("Workers_Master")

    if st.session_state.get("user_created_success"):
        new_user = st.session_state.get("created_user_name", "User")
        st.toast(f"👤 Account for {new_user} created successfully!", icon="✅")
        del st.session_state["user_created_success"]

    tab_add, tab_batch, tab_edit = st.tabs([
        "➕ Add Single User",
        "⚡ Batch Process Raw String",
        "✏️ Edit Existing User & Role",
    ])

    with tab_add:
        st.subheader("Add Employee / Salesperson / Supervisor")
        col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
        with col_center:
            selected_role = st.selectbox(
                "System Access Role *",
                ["Worker", "Supervisor", "Salesperson", "Admin"],
                key="add_user_role_select",
            )

            worker_designation = ""
            if selected_role == "Worker":
                worker_designation = st.selectbox(
                    "Field Designation *",
                    WORKER_DESIGNATIONS,
                    key="add_user_designation_select",
                )

            auto_generated_id = generate_work_id(selected_role, df_workers)

            with st.form("add_user_form"):
                st.info(f"**Auto-Generated Work ID:** `{auto_generated_id}`")

                c1, c2 = st.columns(2)
                with c1:
                    new_name = st.text_input("Full Name *")
                    new_email = st.text_input(
                        "Email Address *", placeholder="e.g. user@company.com"
                    )
                    new_aadhaar = st.text_input(
                        "Aadhaar Number *", max_chars=12, placeholder="12-digit number"
                    )
                with c2:
                    new_pin = st.text_input(
                        "4-Digit PIN / Password *", type="password"
                    )
                    new_base = st.text_input("Base Station / City", value="Jaipur")

                submit_new_user = st.form_submit_button(
                    "Create User & Sync to Database", use_container_width=True
                )
                if submit_new_user:
                    clean_aadhaar = str(new_aadhaar).strip()
                    if not new_name or not new_pin or not new_email:
                        st.error("Please fill in Full Name, Email, and PIN.")
                    elif not validate_email(new_email):
                        st.error("Please enter a valid email address.")
                    elif clean_aadhaar and (
                        len(clean_aadhaar) > 12 or not clean_aadhaar.isdigit()
                    ):
                        st.error(
                            "Aadhaar number must contain only numeric digits and cannot exceed 12 digits."
                        )
                    else:
                        user_dict = {
                            "worker_id": auto_generated_id,
                            "name": new_name.strip(),
                            "email": new_email.strip(),
                            "aadhaar_no": "[Identity Omitted]",
                            "pin": str(new_pin).strip(),
                            "role": selected_role,
                            "designation": worker_designation
                            if selected_role == "Worker"
                            else selected_role,
                            "base_location": new_base.strip(),
                        }
                        append_to_sheet("Workers_Master", user_dict)
                        st.session_state["user_created_success"] = True
                        st.session_state["created_user_name"] = new_name
                        st.rerun()

    with tab_batch:
        st.subheader("⚡ Batch Import Employees")
        raw_text_input = st.text_area("Paste Continuous Data String Here:")
        if st.button("🔍 Parse and Import Data"):
            if raw_text_input:
                pattern = re.compile(
                    r"([A-Z]{1,3}\d{2,3})([A-Za-z\s]+?)(\d{12})(\d{4})(Supervisor|Worker|Admin|Salesperson)([A-Za-z]+)"
                )
                matches = pattern.findall(raw_text_input)
                for m in matches:
                    append_to_sheet(
                        "Workers_Master",
                        {
                            "worker_id": m[0],
                            "name": m[1].strip(),
                            "aadhaar_no": "[Redacted Identity]",
                            "pin": m[3],
                            "role": m[4],
                            "designation": "Installer"
                            if m[4] == "Worker"
                            else m[4],
                            "base_location": m[5],
                        },
                    )
                st.success("All extracted users synced!")
                st.rerun()

    with tab_edit:
        st.subheader("Update Profile")
        if not df_workers.empty and "name" in df_workers.columns:
            selected_edit_user = st.selectbox(
                "Select User to Edit", sorted(df_workers["name"].tolist())
            )
            user_data = df_workers[df_workers["name"] == selected_edit_user].iloc[0]

            col_l, col_center, col_r = st.columns([0.1, 0.8, 0.1])
            with col_center:
                with st.form("edit_user_form"):
                    e_role = st.selectbox(
                        "Update System Access Role",
                        ["Worker", "Supervisor", "Salesperson", "Admin"],
                        index=["Worker", "Supervisor", "Salesperson", "Admin"].index(
                            user_data.get("role", "Worker")
                        ),
                    )

                    e_desig = user_data.get("designation", "")
                    desig_idx = (
                        WORKER_DESIGNATIONS.index(e_desig)
                        if e_desig in WORKER_DESIGNATIONS
                        else 0
                    )

                    e_designation = (
                        st.selectbox(
                            "Update Field Designation",
                            WORKER_DESIGNATIONS,
                            index=desig_idx,
                        )
                        if e_role == "Worker"
                        else e_role
                    )

                    e_email = st.text_input(
                        "Update Email", value=str(user_data.get("email", ""))
                    )
                    e_pin = st.text_input(
                        "Update PIN", value=str(user_data.get("pin", ""))
                    )
                    e_base = st.text_input(
                        "Update Base Location",
                        value=str(user_data.get("base_location", "Jaipur")),
                    )

                    submit_edit = st.form_submit_button(
                        "Update Profile in Database", use_container_width=True
                    )
                    if submit_edit:
                        if e_email and not validate_email(e_email):
                            st.error("Please enter a valid email address.")
                        else:
                            updates = {
                                "role": e_role,
                                "designation": e_designation,
                                "email": e_email.strip(),
                                "pin": e_pin,
                                "base_location": e_base,
                            }
                            update_sheet_row(
                                "Workers_Master", selected_edit_user, updates
                            )
                            st.success(f"Updated **{selected_edit_user}** successfully!")
                            st.rerun()


def render_master_db():
    st.header("🗄️ Live Google Sheets Database")
    m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs([
        "Workers Master",
        "Sites Master",
        "Task Assignments",
        "Worker Daily Logs",
    ])

    with m_tab1:
        st.dataframe(read_sheet("Workers_Master"), use_container_width=True)
    with m_tab2:
        st.dataframe(read_sheet("Sites_Master"), use_container_width=True)
    with m_tab3:
        st.dataframe(read_sheet("Task_Assignments"), use_container_width=True)
    with m_tab4:
        st.dataframe(read_sheet("Worker_Daily_Logs"), use_container_width=True)
