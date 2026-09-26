from datetime import datetime, timedelta
import os
import pandas as pd
import streamlit as st
from core.db import append_to_sheet, read_sheet
from utils.helpers import validate_email


def render_dashboard(user):
    user_name = user.get("name", "User")
    user_role = user.get("role", "Worker")
    user_id = user.get("worker_id", "N/A")

    st.header(f"💼 Salesperson Project Portal — {user_name} ({user_id})")
    st.caption("Live monitoring of ongoing site installations, site statuses, and field team updates.")

    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_sites.empty:
        st.info("No sites found in database.")
        return

    if user_role == "Salesperson":
        sp_id_match = (
            df_sites.get("salesperson_id", pd.Series()).astype(str).str.strip().str.lower()
            == str(user_id).strip().lower()
            if "salesperson_id" in df_sites.columns
            else pd.Series(False, index=df_sites.index)
        )
        sp_name_match = (
            df_sites.get("salesperson_name", pd.Series()).astype(str).str.strip().str.lower()
            == str(user_name).strip().lower()
            if "salesperson_name" in df_sites.columns
            else pd.Series(False, index=df_sites.index)
        )
        my_sites = df_sites[sp_id_match | sp_name_match].copy()
    else:
        my_sites = df_sites.copy()

    if my_sites.empty:
        st.info("⚠️ You currently have no sites assigned to your Sales ID.")
        return

    total_my_sites = len(my_sites)
    in_prog_my_sites = len(
        my_sites[my_sites["status"].astype(str).str.strip().str.title() == "In Progress"]
    )
    hold_my_sites = len(
        my_sites[my_sites["status"].astype(str).str.strip().str.title() == "On Hold"]
    )
    completed_my_sites = len(
        my_sites[
            my_sites["status"]
            .astype(str)
            .str.strip()
            .str.title()
            .isin(["Handovered", "Completed"])
        ]
    )

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">{total_my_sites}</div><div class="kpi-label">Total Sites Acquired</div></div>',
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number" style="color:#00A859;">{in_prog_my_sites}</div><div class="kpi-label">In Progress</div></div>',
            unsafe_allow_html=True,
        )
    with s3:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number" style="color:#D32F2F;">{hold_my_sites}</div><div class="kpi-label">On Hold</div></div>',
            unsafe_allow_html=True,
        )
    with s4:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-number">{completed_my_sites}</div><div class="kpi-label">Completed Handovers</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    st.subheader("📋 My Acquired Sites & Progress Breakdown")
    for _, site in my_sites.iterrows():
        site_id = site.get("installation_id", "N/A")
        c_name = site.get("client_name", "N/A")
        st_val = str(site.get("status", "In Progress")).title()
        t_lead = site.get("team_lead", "Unassigned")
        deal_amt = site.get("deal_amount", "N/A")
        deal_amt_formatted = (
            f"₹{float(deal_amt):,.2f}"
            if str(deal_amt).replace(".", "", 1).isdigit()
            else deal_amt
        )

        site_logs = (
            df_logs[df_logs["installation_id"] == site_id]
            if not df_logs.empty and "installation_id" in df_logs.columns
            else pd.DataFrame()
        )
        workers_on_site = (
            site_logs["worker_name"].unique().tolist()
            if not site_logs.empty and "worker_name" in site_logs.columns
            else []
        )

        badge_color = (
            "#00A859" if st_val in ["In Progress", "Handovered"] else "#D32F2F"
        )

        with st.expander(f"📍 {site_id} — {c_name} [{st_val}]", expanded=True):
            col_info, col_team = st.columns(2)
            with col_info:
                st.write(f"**Client Phone:** {site.get('client_phone', 'N/A')}")
                st.write(f"**City:** {site.get('site_city', 'N/A')}")
                st.write(f"**Order Date:** {site.get('order_date', 'N/A')}")
                st.write(f"**Deal Amount:** {deal_amt_formatted}")
                st.write(f"**Target Handover:** {site.get('handover_date', 'N/A')}")
                st.write(
                    f"**Current Status:** <span style='color:{badge_color}; font-weight:bold;'>{st_val}</span>",
                    unsafe_allow_html=True,
                )
                if site.get("hold_reason"):
                    st.error(f"**Reason for Hold:** {site.get('hold_reason')}")
            with col_team:
                st.write(f"**Supervisor / Team Lead:** {t_lead}")
                st.write(f"**Team Helpers:** {site.get('team_members', 'None')}")
                st.write(
                    f"**Active Field Workers Logged:** {', '.join(workers_on_site) if workers_on_site else 'No field logs yet'}"
                )
                st.write(
                    f"**Total Days Worked On Site:** {site_logs['logged_date'].nunique() if not site_logs.empty else 0} Days"
                )


def render_log_deal(user):
    user_name = user.get("name", "User")
    user_id = user.get("worker_id", "N/A")
    user_base_location = user.get("base_location", "Jaipur")

    st.header(f"📝 Log Sales Field Visit & Order Deal — {user_name}")
    st.caption("Record site visits, update deal confirmation statuses, set agreed pricing, and create new order deals.")

    new_visit_id = f"INST-2026-{os.urandom(2).hex().upper()}"
    st.info(f"🆔 **Automated Site / Order ID:** `{new_visit_id}`")

    with st.form("form_sales_visit_deal"):
        st.subheader("🏢 Client & Site Details")
        c1, c2 = st.columns(2)
        with c1:
            client_name = st.text_input("Client / Business Name *", placeholder="e.g. Apex Warehousing")
            client_phone = st.text_input("Client Mobile Number *", max_chars=10, placeholder="e.g. 9876543210")
            client_email = st.text_input("Client Email Address", placeholder="e.g. client@company.com")
            visit_date = st.date_input("Visit Date", value=datetime.now())
        with c2:
            site_city = st.text_input("Site City *", value=user_base_location)
            site_address = st.text_area("Site Address *", placeholder="Complete site address details...")

        st.divider()
        st.subheader("🤝 Deal & Order Status Details")

        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            order_confirmed = st.selectbox(
                "Order Status *",
                ["Confirmed Order", "Under Negotiation / Lead", "Lost / Cancelled"],
            )
        with col_d2:
            deal_amount = st.number_input(
                "Agreed Deal Amount (₹) *", min_value=0.0, step=1000.0, format="%.2f"
            )
        with col_d3:
            expected_handover = st.date_input(
                "Expected Handover Date", value=datetime.now() + timedelta(days=20)
            )

        st.markdown("### 📦 Product Requirements & Visit Notes")
        product_notes = st.text_area(
            "Product Specifications / Deal Terms",
            placeholder="Mention shutter sizes, quantity, automation type, motor specs, etc.",
        )
        visit_remarks = st.text_area(
            "Sales Visit Remarks / Meeting Notes",
            placeholder="Detail discussion takeaways, pending approvals, or payment schedules...",
        )

        submit_deal = st.form_submit_button("💾 Save Sales Visit & Sync Order Deal", use_container_width=True)

        if submit_deal:
            clean_phone = str(client_phone).strip()
            clean_email = str(client_email).strip()

            if not client_name.strip() or not clean_phone or not site_city.strip():
                st.error("Please fill in Client Name, Mobile Number, and Site City.")
            elif len(clean_phone) != 10 or not clean_phone.isdigit():
                st.error("Please enter a valid 10-digit mobile number.")
            elif clean_email and not validate_email(clean_email):
                st.error("Please enter a valid email address (e.g. name@domain.com).")
            else:
                order_status_mapped = (
                    "In Progress"
                    if order_confirmed == "Confirmed Order"
                    else (
                        "On Hold"
                        if order_confirmed == "Under Negotiation / Lead"
                        else "Cancelled"
                    )
                )

                order_payload = {
                    "installation_id": new_visit_id,
                    "client_name": client_name.strip(),
                    "client_phone": clean_phone,
                    "client_email": clean_email,
                    "salesperson_id": user_id,
                    "salesperson_name": user_name,
                    "team_lead": "",
                    "team_members": "",
                    "site_city": site_city.strip(),
                    "site_address": site_address.strip(),
                    "order_date": str(visit_date),
                    "handover_date": str(expected_handover),
                    "deal_status": order_confirmed,
                    "deal_amount": str(deal_amount),
                    "products_summary": product_notes.strip(),
                    "status": order_status_mapped,
                    "hold_reason": f"Sales Remarks: {visit_remarks.strip()}"
                    if visit_remarks.strip()
                    else "",
                }

                append_to_sheet("Sites_Master", order_payload)
                st.success(
                    f"🎉 Deal for **{client_name}** recorded successfully under **{new_visit_id}**! Total Value: **₹{deal_amount:,.2f}**"
                )
                st.rerun()


def render_track_progress(user):
    user_name = user.get("name", "User")
    user_role = user.get("role", "Worker")
    user_id = user.get("worker_id", "N/A")

    st.header(f"🔍 Site Progress & Order Tracker — {user_name}")
    st.caption("Search site records by Site ID or Client Name to view live progress, worker logs, and timeline updates.")

    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_sites.empty:
        st.warning("No installation records found in the database.")
        return

    col_search1, col_search2 = st.columns([2, 1])
    with col_search1:
        search_query = st.text_input(
            "🔍 Search by Site ID or Client Name:", placeholder="e.g. INST-2026 or Reliance"
        ).strip()
    with col_search2:
        status_filter = st.selectbox(
            "Filter Status",
            ["All Statuses", "In Progress", "On Hold", "Handovered", "Completed"],
        )

    filtered_df = df_sites.copy()

    if user_role == "Salesperson":
        sp_id_match = (
            filtered_df.get("salesperson_id", pd.Series())
            .astype(str)
            .str.strip()
            .str.lower()
            == str(user_id).strip().lower()
            if "salesperson_id" in filtered_df.columns
            else pd.Series(False, index=filtered_df.index)
        )

        sp_name_match = (
            filtered_df.get("salesperson_name", pd.Series())
            .astype(str)
            .str.strip()
            .str.lower()
            == str(user_name).strip().lower()
            if "salesperson_name" in filtered_df.columns
            else pd.Series(False, index=filtered_df.index)
        )

        filtered_df = filtered_df[sp_id_match | sp_name_match]

    if search_query:
        q = search_query.lower()
        filtered_df = filtered_df[
            filtered_df["installation_id"].astype(str).str.lower().str.contains(q)
            | filtered_df["client_name"].astype(str).str.lower().str.contains(q)
        ]

    if status_filter != "All Statuses":
        filtered_df = filtered_df[
            filtered_df["status"].astype(str).str.strip().str.title() == status_filter
        ]

    st.write("##")

    if filtered_df.empty:
        st.info("No matching sites found for your search criteria or assigned user profile.")
    else:
        st.subheader(f"Found {len(filtered_df)} Matching Site(s)")
        for _, site in filtered_df.iterrows():
            site_id = site.get("installation_id", "N/A")
            c_name = site.get("client_name", "N/A")
            c_phone = site.get("client_phone", "N/A")
            status = str(site.get("status", "In Progress")).title()
            deal_amt = site.get("deal_amount", "N/A")
            deal_amt_formatted = (
                f"₹{float(deal_amt):,.2f}"
                if str(deal_amt).replace(".", "", 1).isdigit()
                else deal_amt
            )

            status_color = (
                "#00A859" if status in ["In Progress", "Handovered"] else "#D32F2F"
            )

            with st.expander(
                f"🏗️ {site_id} | {c_name} | Status: {status}", expanded=True
            ):
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.markdown(f"**📞 Client Contact:** {c_phone}")
                    st.markdown(f"**📍 City:** {site.get('site_city', 'N/A')}")
                    st.markdown(f"**🏠 Address:** {site.get('site_address', 'N/A')}")
                with col_m2:
                    st.markdown(f"**💰 Deal Value:** {deal_amt_formatted}")
                    st.markdown(f"**🤝 Deal Status:** {site.get('deal_status', 'N/A')}")
                    st.markdown(f"**📅 Order Date:** {site.get('order_date', 'N/A')}")
                with col_m3:
                    st.markdown(
                        f"**👨‍🔧 Supervisor / Team Lead:** {site.get('team_lead', 'Unassigned')}"
                    )
                    st.markdown(
                        f"**🎯 Target Handover:** {site.get('handover_date', 'N/A')}"
                    )
                    st.markdown(
                        f"**⚡ Current Status:** <span style='color:{status_color}; font-weight:bold;'>{status}</span>",
                        unsafe_allow_html=True,
                    )

                if site.get("hold_reason"):
                    st.warning(f"**Hold Remarks / Notes:** {site.get('hold_reason')}")

                st.divider()
                st.markdown("#### 📜 Live Field Logs for this Site")
                site_logs = (
                    df_logs[df_logs["installation_id"] == site_id]
                    if not df_logs.empty and "installation_id" in df_logs.columns
                    else pd.DataFrame()
                )

                if site_logs.empty:
                    st.caption("No daily field logs submitted by workers yet.")
                else:
                    disp_cols = [
                        c
                        for c in [
                            "logged_date",
                            "site_day",
                            "worker_name",
                            "worker_role",
                            "task_category",
                            "task_name",
                            "hours_spent",
                            "site_remarks",
                        ]
                        if c in site_logs.columns
                    ]
                    st.dataframe(
                        site_logs[disp_cols].sort_values(
                            by="logged_date", ascending=False
                        ),
                        use_container_width=True,
                    )
