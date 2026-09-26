from datetime import datetime, timedelta
import os
import pandas as pd
import streamlit as st
from config import HOLD_REASONS, PRODUCT_CATALOG, STATUS_OPTIONS
from core.db import append_to_sheet, read_sheet, update_sheet_row
from utils.helpers import format_worker_dropdown_options, validate_email
from views.components import render_restricted_work_input


def render_new_requests():
    st.header("🔔 Pending Installation Requests & Sales Orders")
    st.caption("Review new installation orders raised by salespersons and assign team execution leads.")

    df_sites = read_sheet("Sites_Master")
    df_workers = read_sheet("Workers_Master")

    if df_sites.empty:
        st.info("No installation requests found.")
        return

    unassigned_mask = (
        df_sites.get("team_lead", pd.Series())
        .astype(str)
        .str.strip()
        .replace(["", "nan", "None", "Unassigned"], "")
        == ""
    )
    pending_requests = df_sites[unassigned_mask].copy()

    if pending_requests.empty:
        st.success("✅ All installation orders have been processed and assigned to team leads!")
    else:
        st.warning(
            f"🚨 **{len(pending_requests)} New Installation Order(s) Awaiting Supervisor Action!**"
        )

        worker_options = format_worker_dropdown_options(df_workers)

        for _, req in pending_requests.iterrows():
            site_id = req.get("installation_id", "N/A")
            c_name = req.get("client_name", "N/A")
            c_phone = req.get("client_phone", "N/A")
            sp_name = req.get("salesperson_name", "Salesperson")
            deal_amt = req.get("deal_amount", "N/A")

            with st.expander(
                f"🆕 Order ID: {site_id} — Client: {c_name} (Salesperson: {sp_name})",
                expanded=True,
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Client Mobile:** {c_phone}")
                    st.write(f"**City:** {req.get('site_city', 'N/A')}")
                    st.write(f"**Address:** {req.get('site_address', 'N/A')}")
                    st.write(f"**Order Date:** {req.get('order_date', 'N/A')}")
                with col2:
                    st.write(f"**Deal Value:** ₹{deal_amt}")
                    st.write(f"**Target Handover:** {req.get('handover_date', 'N/A')}")
                    st.write(f"**Products Summary:** {req.get('products_summary', 'None')}")

                st.markdown("#### ⚡ Assign Execution Team & Activate Site")
                with st.form(f"assign_team_form_{site_id}"):
                    a_lead = st.selectbox(
                        "Assign Team Lead *", options=worker_options, key=f"lead_{site_id}"
                    )
                    a_helpers = st.multiselect(
                        "Assign Helpers / Crew",
                        options=[w for w in worker_options if w != a_lead],
                        key=f"helpers_{site_id}",
                    )

                    submit_assignment = st.form_submit_button(
                        "✅ Accept Order & Assign Team", use_container_width=True
                    )

                    if submit_assignment:
                        if not a_lead:
                            st.error("Please select a Team Lead.")
                        else:
                            clean_lead = a_lead.split(" (")[0].strip()
                            clean_helpers = [
                                h.split(" (")[0].strip() for h in a_helpers
                            ]
                            updates = {
                                "team_lead": clean_lead,
                                "team_members": ", ".join(clean_helpers),
                                "status": "In Progress",
                            }
                            update_sheet_row(
                                "Sites_Master", "installation_id", site_id, updates
                            )
                            st.success(
                                f"Installation **{site_id}** activated and assigned to **{clean_lead}**!"
                            )
                            st.rerun()


def render_new_order():
    st.header("Create New Installation Order")
    df_workers = read_sheet("Workers_Master")
    df_sites = read_sheet("Sites_Master")

    worker_options = format_worker_dropdown_options(df_workers)
    salesperson_options = []

    if not df_workers.empty and "name" in df_workers.columns:
        sp_df = df_workers[
            df_workers["role"].astype(str).str.strip().str.title() == "Salesperson"
        ]
        if not sp_df.empty:
            salesperson_options = (
                sp_df["worker_id"].astype(str) + " - " + sp_df["name"].astype(str)
            ).tolist()

    if "products_count" not in st.session_state:
        st.session_state.products_count = 1

    st.markdown("### 🔗 Order Creation & Linkage")
    existing_sp_orders = {}
    if not df_sites.empty and "installation_id" in df_sites.columns:
        unassigned_df = df_sites[
            df_sites.get("team_lead", pd.Series())
            .astype(str)
            .str.strip()
            .replace(["", "nan", "None"], "")
            == ""
        ]
        for _, r in unassigned_df.iterrows():
            s_id = str(r.get("installation_id")).strip()
            c_n = str(r.get("client_name")).strip()
            existing_sp_orders[f"{s_id} — {c_n}"] = s_id

    link_type = st.radio(
        "Order Source:",
        options=[
            "Create Custom Site ID (Direct Supervisor Order)",
            "Select Existing Salesperson Order ID",
        ],
        horizontal=True,
    )

    if link_type == "Select Existing Salesperson Order ID" and existing_sp_orders:
        selected_sp_label = st.selectbox(
            "Select Pending Sales Order *", options=list(existing_sp_orders.keys())
        )
        visit_id = existing_sp_orders[selected_sp_label]
        st.info(f"📌 **Linking to Existing Salesperson Order ID:** `{visit_id}`")
    else:
        visit_id = f"INST-2026-{os.urandom(2).hex().upper()}"
        st.info(f"🆔 **Automated Site / Order ID:** `{visit_id}`")

    col_client, col_team, col_dates = st.columns(3)

    with col_client:
        st.markdown("### 🏢 Client Info")
        client_name = st.text_input("Client / Company Name *", placeholder="e.g. Reliance Logistics")
        client_phone = st.text_input("Client Mobile No. *", placeholder="e.g. 9876543210", max_chars=10)
        client_email = st.text_input("Client Email Address", placeholder="e.g. client@company.com")

        selected_sp = st.selectbox("💼 Link Salesperson", options=["Unassigned"] + salesperson_options)
        sp_id = selected_sp.split(" - ")[0] if selected_sp != "Unassigned" else ""
        sp_name = selected_sp.split(" - ")[1] if selected_sp != "Unassigned" else "Unassigned"

    with col_team:
        st.markdown("### 👨‍💼 Team & Site Structure")
        team_lead_name = st.selectbox("Team Lead Name *", options=worker_options, key="inst_team_lead")
        team_helpers = st.multiselect("Team Members / Helpers", options=[w for w in worker_options if w != team_lead_name], key="inst_helpers")
        city_name = st.text_input("City Name *", value="Mumbai", key="inst_city_name")
        site_address = st.text_area("Site Address *", placeholder="Full installation site address...", key="inst_site_address")

    with col_dates:
        st.markdown("### 📅 Order Dates")
        inst_date = st.date_input("Installation Date", value=datetime.now(), key="inst_order_date")
        site_clearance_date = st.date_input("Site Clearance Date", value=datetime.now(), key="inst_clearance_date")
        target_handover_date = st.date_input("Target Handover Date", value=datetime.now() + timedelta(days=15), key="inst_handover_date")

    st.divider()

    st.markdown("### 📦 Order Products Details")
    products_data = []
    catalog_main_categories = list(PRODUCT_CATALOG.keys())

    for p_idx in range(st.session_state.products_count):
        st.markdown(f"#### Product #{p_idx + 1}")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            product_type = st.selectbox("Select Product", catalog_main_categories, key=f"prod_type_{p_idx}")
            dimensions = st.text_input("Dimensions (WxH)", placeholder="e.g., 5330X6000", key=f"prod_dim_{p_idx}")
        with col_p2:
            sub_cat_options = PRODUCT_CATALOG.get(product_type, ["Other"])
            sub_category = st.selectbox("Select Sub-Category", sub_cat_options, key=f"prod_sub_{p_idx}")
            quantity = st.number_input("Quantity", min_value=1, value=1, step=1, key=f"prod_qty_{p_idx}")

        products_data.append({
            "product_type": product_type,
            "sub_category": sub_category,
            "dimensions": dimensions,
            "quantity": quantity,
        })

    if st.button("➕ Add Another Product", key="btn_add_product"):
        st.session_state.products_count += 1
        st.rerun()

    st.write("##")
    if st.button("💾 Submit Installation Order", use_container_width=True, key="btn_submit_inst_order"):
        clean_phone = str(client_phone).strip()
        clean_email = str(client_email).strip()

        if not client_name or not clean_phone or not team_lead_name or not city_name or not site_address:
            st.error("Please fill in all mandatory fields.")
        elif len(clean_phone) != 10 or not clean_phone.isdigit():
            st.error("Please enter a valid 10-digit mobile number.")
        elif clean_email and not validate_email(clean_email):
            st.error("Please enter a valid email address.")
        else:
            clean_lead = team_lead_name.split(" (")[0].strip()
            clean_helpers = [h.split(" (")[0].strip() for h in team_helpers]

            order_data = {
                "installation_id": visit_id,
                "client_name": client_name.strip(),
                "client_phone": clean_phone,
                "client_email": clean_email,
                "salesperson_id": sp_id,
                "salesperson_name": sp_name,
                "team_lead": clean_lead,
                "team_members": ", ".join(clean_helpers),
                "site_city": city_name,
                "site_address": site_address,
                "order_date": str(inst_date),
                "site_clearance_date": str(site_clearance_date),
                "handover_date": str(target_handover_date),
                "products_summary": str(products_data),
                "status": "In Progress",
            }
            if link_type == "Select Existing Salesperson Order ID" and existing_sp_orders:
                update_sheet_row("Sites_Master", "installation_id", visit_id, order_data)
            else:
                append_to_sheet("Sites_Master", order_data)

            st.success(
                f"Installation Order **{visit_id}** for **{client_name}** linked to **{sp_name}** successfully!"
            )
            st.session_state.products_count = 1


def render_view_logs_and_update_status():
    st.markdown("## 🔍 View Daily Logs & Update Status")

    df_sites = read_sheet("Sites_Master")
    if df_sites.empty:
        st.warning("No installation records found.")
        return

    df_sites.columns = [
        str(col).strip().lower().replace(" ", "_") for col in df_sites.columns
    ]

    site_map = {}
    site_data = {}

    for _, s in df_sites.iterrows():
        site_id = str(s.get("installation_id", "")).strip()
        status = str(s.get("status") or "In Progress").strip().title()

        if not site_id or status in ["Handovered", "Handover", "Completed"]:
            continue

        c_name = str(
            s.get("client_name") or s.get("client") or s.get("company_name") or "N/A"
        ).strip()
        c_phone = str(
            s.get("client_phone") or s.get("mobile_no") or s.get("phone") or "N/A"
        ).strip()
        city = str(s.get("site_city") or s.get("city") or "N/A").strip()
        lead = str(s.get("team_lead") or s.get("lead") or "N/A").strip()

        display_label = f"{site_id} — {c_name}" if c_name != "N/A" else site_id

        site_map[display_label] = site_id
        site_data[site_id] = {
            "client_name": c_name,
            "client_phone": c_phone,
            "city": city,
            "team_lead": lead,
            "status": status,
        }

    if not site_map:
        st.info("No active installation sites found (all sites completed or handovered).")
        return

    selected_label = st.selectbox(
        "Select Installation ID",
        options=list(site_map.keys()),
        key="view_logs_site_select",
    )

    selected_id = site_map[selected_label]
    info = site_data[selected_id]

    st.markdown(
        f"""
        <div style="background-color: #f0f4f8; padding: 20px; border-radius: 10px; border-left: 5px solid #1E3A8A; margin-top: 15px; margin-bottom: 20px;">
            <h2 style="color: #1E3A8A; margin-top: 0; margin-bottom: 10px;">{selected_id}</h2>
            <p style="margin: 5px 0;"><strong>Client Name:</strong> {info['client_name']} | <strong>Client Mobile:</strong> {info['client_phone']}</p>
            <p style="margin: 5px 0;"><strong>City:</strong> {info['city']} | <strong>Team Lead:</strong> {info['team_lead']}</p>
            <p style="margin: 5px 0;"><strong>Current Status:</strong> {info['status']}</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    col_st, col_btn = st.columns([2, 1])
    with col_st:
        curr_st = info["status"]
        st_idx = STATUS_OPTIONS.index(curr_st) if curr_st in STATUS_OPTIONS else 0
        new_st = st.selectbox(
            "Update Status",
            STATUS_OPTIONS,
            index=st_idx,
            key="update_status_selectbox",
        )

    hold_reason_val = ""
    hold_remark_val = ""

    if new_st == "On Hold":
        st.warning("⚠️ Site is being placed On Hold. A reason is mandatory.")
        c_r1, c_r2 = st.columns(2)
        with c_r1:
            hold_reason_val = st.selectbox(
                "Mandatory Reason for Hold *",
                HOLD_REASONS,
                key="hold_reason_select",
            )
        with c_r2:
            if hold_reason_val == "Other":
                hold_remark_val = st.text_input(
                    "Specific Hold Remarks (Mandatory for 'Other') *",
                    key="hold_remark_input",
                )

    with col_btn:
        st.write(" ")
        st.write(" ")
        if st.button("Update Status", key="btn_update_site_status"):
            if new_st == "On Hold":
                if hold_reason_val == "Other" and not hold_remark_val.strip():
                    st.error("Please enter specific remarks when selecting 'Other'.")
                    st.stop()

                final_hold_note = (
                    f"On Hold Reason: {hold_reason_val} - {hold_remark_val}"
                    if hold_reason_val == "Other"
                    else f"On Hold Reason: {hold_reason_val}"
                )
                update_sheet_row(
                    "Sites_Master",
                    "installation_id",
                    selected_id,
                    {"status": new_st, "hold_reason": final_hold_note},
                )
            else:
                update_sheet_row(
                    "Sites_Master",
                    "installation_id",
                    selected_id,
                    {"status": new_st},
                )

            st.success(f"Status updated to **{new_st}**!")
            st.rerun()

    st.divider()
    st.subheader("📜 Submitted Work Logs")
    df_logs = read_sheet("Worker_Daily_Logs")
    p_logs = (
        df_logs[df_logs["installation_id"] == selected_id]
        if not df_logs.empty and "installation_id" in df_logs.columns
        else pd.DataFrame()
    )

    if not p_logs.empty:
        for _, l in p_logs.iterrows():
            day_lbl = l.get("site_day", "")
            header_prefix = f"[{day_lbl}] " if day_lbl else ""
            with st.expander(
                f"📅 {header_prefix}Date: {l.get('logged_date')} | Worker: {l.get('worker_name')} | Role/Designation: {l.get('worker_role', 'N/A')}"
            ):
                st.write(f"**Task Category:** {l.get('task_category')}")
                st.write(f"**Task Description:** {l.get('task_name')}")
                st.write(
                    f"**Time Spent:** {l.get('hours_spent')} hrs {l.get('minutes_spent')} mins"
                )
                st.write(f"**Travel Day (TA/DA):** {l.get('is_travel_day')}")
                st.write(f"**Photo Attached:** {l.get('site_photo', 'No Photo')}")
                st.write(
                    f"**Remarks / Cause of Delay:** {l.get('site_remarks', 'None')}"
                )
    else:
        st.info("No submitted field logs found for this installation ID.")


def render_team_head_dashboard(user):
    user_name = user.get("name", "User")
    st.header("👥 Dual-Tab Team Head Dashboard")
    tab_personal, tab_crew = st.tabs(["👤 Personal Work Log", "👨‍🔧 Crew Task Logging"])

    with tab_personal:
        st.subheader(f"Personal Execution Log ({user_name})")
        render_restricted_work_input(target_worker_name=user_name, is_crew_log=False)

    with tab_crew:
        st.subheader("Manage Active Crew Logs")
        df_workers = read_sheet("Workers_Master")

        worker_options = format_worker_dropdown_options(df_workers)

        if not worker_options:
            st.info("⚠️ No Active Crew Members Found")
        else:
            selected_crew_str = st.selectbox("Select Worker to Log For", worker_options)
            selected_crew = selected_crew_str.split(" (")[0].strip()
            st.divider()
            render_restricted_work_input(target_worker_name=selected_crew, is_crew_log=True)


def render_active_tasks():
    st.header("📋 Active Tasks Dashboard")
    st.caption("Track site installation progress, monitor individual task statuses, and export site reports.")

    df_tasks = read_sheet("Task_Assignments")
    df_sites = read_sheet("Sites_Master")

    if df_tasks.empty:
        st.info("⚠️ No Active Tasks Found")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            site_options = ["All Sites"] + (
                df_sites["installation_id"].tolist()
                if not df_sites.empty and "installation_id" in df_sites.columns
                else []
            )
            site_filter = st.selectbox("Filter by Site", site_options)
        with col_f2:
            status_filter = st.selectbox(
                "Filter by Task Status",
                ["All Statuses", "In Progress", "Pending", "Completed"],
            )

        filtered_tasks = df_tasks.copy()
        if site_filter != "All Sites" and "installation_id" in filtered_tasks.columns:
            filtered_tasks = filtered_tasks[
                filtered_tasks["installation_id"] == site_filter
            ]
        if status_filter != "All Statuses" and "status" in filtered_tasks.columns:
            filtered_tasks = filtered_tasks[filtered_tasks["status"] == status_filter]

        st.write("##")
        st.subheader(f"Task List ({len(filtered_tasks)} Records)")
        st.dataframe(filtered_tasks, use_container_width=True)
