from datetime import datetime
import pandas as pd
import streamlit as st
from config import DELAY_REASONS, TASK_CATEGORIES
from core.db import append_to_sheet, read_sheet, upload_file_to_drive
from core.styles import COLOR_ACCENT, COLOR_PRIMARY
from utils.helpers import format_worker_dropdown_options


@st.dialog("🎉 Daily Log Submitted Successfully!")
def show_upload_success_modal(site_id, day_label, records_count):
    st.write("### Great Job! 🚀")
    st.markdown(
        f"""
        Your **{records_count} task(s)** and photos for **{site_id} ({day_label})** have been uploaded and saved directly to the database.
        
        * All entries have been synchronized.
        * The entry form has been cleared for your next log.
        """
    )
    if st.button(
        "Close & Continue", use_container_width=True, key="btn_close_success_dialog"
    ):
        st.session_state["show_success_modal"] = False
        st.rerun()


def render_restricted_work_input(target_worker_name, is_crew_log=False):
    if st.session_state.get("show_success_modal"):
        m_info = st.session_state.get("modal_info", {})
        show_upload_success_modal(
            m_info.get("site_id", ""),
            m_info.get("day_label", ""),
            m_info.get("count", 1),
        )

    form_version_key = f"form_version_{target_worker_name}_{is_crew_log}"
    if form_version_key not in st.session_state:
        st.session_state[form_version_key] = 0
    v = st.session_state[form_version_key]

    df_sites = read_sheet("Sites_Master")
    df_workers = read_sheet("Workers_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    valid_site_map = {}
    site_info_dict = {}

    if not df_sites.empty and "installation_id" in df_sites.columns:
        today_date = datetime.now().date()

        for _, s in df_sites.iterrows():
            site_id = str(s.get("installation_id", "")).strip()
            status = str(s.get("status", "")).strip().lower()
            c_name = str(s.get("client_name", "N/A")).strip() or "N/A"
            c_phone = str(s.get("client_phone", "N/A")).strip() or "N/A"
            handover_str = str(s.get("handover_date", "")).strip()

            if status in ["handovered", "handover", "completed"]:
                continue

            if handover_str:
                try:
                    h_date = pd.to_datetime(handover_str).date()
                    if today_date > h_date:
                        continue
                except Exception:
                    pass

            display_label = f"{site_id} — {c_name}"
            valid_site_map[display_label] = site_id
            site_info_dict[site_id] = {
                "client_name": c_name,
                "client_phone": c_phone,
                "city": s.get("site_city", "Jaipur"),
                "address": s.get("site_address", "N/A"),
            }

    if not valid_site_map:
        st.warning("⚠️ No Active Installation Sites Available.")
        return

    header_placeholder = st.empty()

    c_site, c_date = st.columns(2)
    with c_site:
        selected_display_label = st.selectbox(
            "Current Logging for :",
            list(valid_site_map.keys()),
            key=f"site_{target_worker_name}_{is_crew_log}_v{v}",
        )
        selected_site_id = valid_site_map[selected_display_label]

    with c_date:
        log_date = st.date_input(
            "Date of Work",
            value=datetime.now(),
            key=f"date_{target_worker_name}_{is_crew_log}_v{v}",
        )

    site_days_count = 1
    if (
        not df_logs.empty
        and "installation_id" in df_logs.columns
        and "logged_date" in df_logs.columns
    ):
        site_logs = df_logs[df_logs["installation_id"] == selected_site_id]
        logged_dates = sorted(site_logs["logged_date"].astype(str).unique())

        cur_date_str = str(log_date)
        if cur_date_str in logged_dates:
            site_days_count = logged_dates.index(cur_date_str) + 1
        else:
            site_days_count = len(logged_dates) + 1

    site_day_label = f"Day {site_days_count}"

    header_placeholder.markdown(
        f"## 📝 Log Daily Tasks - {selected_site_id} ({site_day_label})"
    )

    site_meta = site_info_dict[selected_site_id]
    st.markdown(
        f"""
        <div class="client-card">
            <span style="font-size:15px; font-weight:700; color:{COLOR_PRIMARY};">🏢 Client Name: {site_meta['client_name']}</span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            <span style="font-size:15px; font-weight:700; color:{COLOR_ACCENT};">📞 Contact Mobile: <a href="tel:{site_meta['client_phone']}" style="color:{COLOR_ACCENT}; text-decoration:none;">{site_meta['client_phone']}</a></span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            <span style="font-size:15px; font-weight:700; color:{COLOR_PRIMARY};">📅 Current Timeline: <strong>{site_day_label}</strong></span>
        </div>
    """,
        unsafe_allow_html=True,
    )

    site_city = site_meta["city"]

    worker_options = format_worker_dropdown_options(df_workers)
    if not worker_options:
        worker_options = [target_worker_name]

    st.markdown("### 👥 Crew & Team Assignment")
    col_lead, col_helpers = st.columns(2)

    with col_lead:
        default_lead_idx = 0
        for idx, w_opt in enumerate(worker_options):
            if target_worker_name in w_opt:
                default_lead_idx = idx
                break

        team_lead_selected = st.selectbox(
            "Team Lead Name *",
            options=worker_options,
            index=default_lead_idx,
            key=f"team_lead_{target_worker_name}_{is_crew_log}_v{v}",
        )

    with col_helpers:
        available_helpers = [w for w in worker_options if w != team_lead_selected]
        team_helpers_selected = st.multiselect(
            "Team Members / Helpers",
            options=available_helpers,
            key=f"helpers_{target_worker_name}_{is_crew_log}_v{v}",
        )

    active_crew = [team_lead_selected] + team_helpers_selected

    st.write("##")
    st.markdown("### 🛠️ Tasks Completed Today")

    task_count_key = f"task_lines_count_{target_worker_name}_{is_crew_log}_v{v}"
    if task_count_key not in st.session_state:
        st.session_state[task_count_key] = 1

    task_entries = []

    for i in range(st.session_state[task_count_key]):
        st.caption(f"**Task Line #{i+1}**")
        col_cat, col_desc, col_assigned, col_hrs, col_min = st.columns(
            [2.5, 3, 2.5, 1.2, 1.2]
        )

        with col_cat:
            cat = st.selectbox(
                f"Category #{i+1}",
                TASK_CATEGORIES,
                key=f"cat_{target_worker_name}_{is_crew_log}_{i}_v{v}",
            )
        with col_desc:
            desc = st.text_input(
                f"Task #{i+1} Description",
                placeholder="e.g., Track Leveling",
                key=f"desc_{target_worker_name}_{is_crew_log}_{i}_v{v}",
            )
        with col_assigned:
            assigned_worker = st.selectbox(
                f"Assigned To #{i+1}",
                options=active_crew,
                key=f"assigned_{target_worker_name}_{is_crew_log}_{i}_v{v}",
            )
        with col_hrs:
            hrs = st.number_input(
                "Hours",
                min_value=0,
                max_value=24,
                value=2,
                step=1,
                key=f"hrs_{target_worker_name}_{is_crew_log}_{i}_v{v}",
            )
        with col_min:
            mins = st.selectbox(
                "Minutes",
                [0, 15, 30, 45],
                key=f"min_{target_worker_name}_{is_crew_log}_{i}_v{v}",
            )

        task_entries.append({
            "category": cat,
            "description": desc,
            "assigned_worker": assigned_worker,
            "hours": hrs,
            "minutes": mins,
        })

    if st.button(
        "➕ ADD MORE TASK LINES",
        key=f"add_task_btn_{target_worker_name}_{is_crew_log}_v{v}",
    ):
        st.session_state[task_count_key] += 1
        st.rerun()

    st.divider()

    st.markdown("### ⚠️ Site Remarks / Delays")
    col_delay_cat, col_delay_notes = st.columns([1, 2])

    with col_delay_cat:
        delay_reason = st.selectbox(
            "Primary Delay Category",
            options=DELAY_REASONS,
            key=f"delay_reason_{target_worker_name}_{is_crew_log}_v{v}",
        )

    with col_delay_notes:
        site_remarks = st.text_area(
            "Specific Site Notes / Remarks",
            placeholder="Provide details...",
            key=f"rem_{target_worker_name}_{is_crew_log}_v{v}",
        )

    st.markdown("### 📷 Site Photo Documentation")
    uploaded_photo = st.file_uploader(
        "Upload Photo of Site",
        type=["jpg", "jpeg", "png"],
        key=f"photo_{target_worker_name}_{is_crew_log}_v{v}",
    )

    if uploaded_photo is not None:
        st.image(uploaded_photo, caption="Uploaded Site Photo Preview", width=280)

    st.write("##")

    if st.button(
        "💾 Sync Daily Log to Database",
        key=f"btn_sync_{target_worker_name}_{is_crew_log}_v{v}",
        use_container_width=True,
    ):
        valid_tasks = [t for t in task_entries if t["description"].strip()]

        if not valid_tasks:
            st.error("Please enter at least one task description before syncing.")
            return

        photo_link = "No Photo"
        if uploaded_photo is not None:
            photo_name = f"{selected_site_id}_{target_worker_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            photo_link = upload_file_to_drive(uploaded_photo, photo_name)

        records_saved = 0

        for idx, t in enumerate(valid_tasks):
            raw_worker_string = t["assigned_worker"]
            clean_worker_name = raw_worker_string.split(" (")[0].strip()

            w_base = "Jaipur"
            w_desig = "Worker"

            if not df_workers.empty:
                m = df_workers[df_workers["name"] == clean_worker_name]
                if not m.empty:
                    w_base = m.iloc[0].get("base_location", "Jaipur")
                    w_desig = m.iloc[0].get("designation", "Worker")

            w_is_travel = str(w_base).strip().lower() != str(site_city).strip().lower()

            clean_lead_name = team_lead_selected.split(" (")[0].strip()

            log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{idx+1}"
            log_entry = {
                "log_id": log_id,
                "installation_id": selected_site_id,
                "site_day": site_day_label,
                "logged_date": str(log_date),
                "worker_name": clean_worker_name,
                "worker_role": w_desig,
                "team_lead_name": clean_lead_name,
                "task_category": t["category"],
                "task_name": t["description"],
                "hours_spent": t["hours"],
                "minutes_spent": t["minutes"],
                "base_location": w_base,
                "site_city": site_city,
                "is_travel_day": "Yes" if w_is_travel else "No",
                "delay_category": delay_reason,
                "site_remarks": site_remarks,
                "site_photo": photo_link,
                "logged_by": target_worker_name,
            }
            append_to_sheet("Worker_Daily_Logs", log_entry)
            records_saved += 1

        if records_saved > 0:
            st.session_state["show_success_modal"] = True
            st.session_state["modal_info"] = {
                "site_id": selected_site_id,
                "day_label": site_day_label,
                "count": records_saved,
            }
            st.session_state[form_version_key] += 1
            st.rerun()
