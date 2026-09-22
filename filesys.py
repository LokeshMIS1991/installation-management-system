import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. PAGE CONFIG & BRANDING THEME
# ==========================================
st.set_page_config(page_title="Installation & Field Operations Portal", layout="wide", page_icon="🏗️")

# Custom CSS Theme
st.markdown("""
    <style>
    .main-header { color: #0F4C81; font-weight: 700; }
    .stButton>button { background-color: #0F4C81; color: white; border-radius: 5px; }
    .stButton>button:hover { background-color: #00A651; color: white; }
    .card-box { background-color: #F0F5FA; border-left: 5px solid #0F4C81; padding: 15px; border-radius: 6px; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE INITIALIZATION (4-SHEETS + EXPANDED)
# ==========================================
def init_mock_db():
    if "db" not in st.session_state:
        st.session_state.db = {
            # Sheet 1: Workers Master
            "Workers_Master": pd.DataFrame([
                {"worker_id": "W001", "name": "Admin User", "pin": "9999", "role": "Admin", "base_location": "Jaipur"},
                {"worker_id": "W002", "name": "Vishak", "pin": "1234", "role": "Supervisor", "base_location": "Jaipur"},
                {"worker_id": "W003", "name": "Ramesh", "pin": "5678", "role": "Worker", "base_location": "Jaipur"},
                {"worker_id": "W004", "name": "Kabir", "pin": "1122", "role": "Supervisor", "base_location": "Jaipur"},
                {"worker_id": "W005", "name": "Suresh", "pin": "3344", "role": "Worker", "base_location": "Jaipur"}
            ]),
            # Sheet 2: Sites Master
            "Sites_Master": pd.DataFrame([
                {"installation_id": "INST-2026-G4HVI", "site_name": "Jaipur Metro Station", "site_city": "Jaipur", "team_lead": "Vishak", "status": "In Progress", "order_date": "2026-09-01", "handover_date": "2026-10-15"},
                {"installation_id": "INST-2026-B9K12", "site_name": "Udaipur Hotel Complex", "site_city": "Udaipur", "team_lead": "Kabir", "status": "In Progress", "order_date": "2026-09-10", "handover_date": "2026-11-01"}
            ]),
            # Sheet 3: Task Assignments
            "Task_Assignments": pd.DataFrame([
                {"task_id": "TSK-001", "installation_id": "INST-2026-G4HVI", "task_name": "Motorized Rolling Shutter Assembly", "assigned_to": "Ramesh", "status": "In Progress"},
                {"task_id": "TSK-002", "installation_id": "INST-2026-G4HVI", "task_name": "Electrical Wiring & Control Panel", "assigned_to": "Vishak", "status": "Pending"},
                {"task_id": "TSK-003", "installation_id": "INST-2026-B9K12", "task_name": "Sliding Gate Track Fitting", "assigned_to": "Suresh", "status": "In Progress"},
                {"task_id": "TSK-004", "installation_id": "INST-2026-B9K12", "task_name": "Structural Welding", "assigned_to": "Kabir", "status": "Pending"}
            ]),
            # Sheet 4: Worker Daily Logs
            "Worker_Daily_Logs": pd.DataFrame(columns=[
                "log_id", "installation_id", "logged_date", "worker_name", "role",
                "task_name", "progress_percentage", "hours_spent", "minutes_spent",
                "base_location", "site_city", "is_travel_day", "site_remarks", "logged_by"
            ])
        }

def read_sheet(sheet_name):
    init_mock_db()
    return st.session_state.db.get(sheet_name, pd.DataFrame())

def append_to_sheet(sheet_name, row_data_dict):
    init_mock_db()
    df = st.session_state.db[sheet_name]
    new_df = pd.DataFrame([row_data_dict])
    st.session_state.db[sheet_name] = pd.concat([df, new_df], ignore_index=True)

def update_sheet_row(sheet_name, key_col, key_val, update_dict):
    init_mock_db()
    df = st.session_state.db[sheet_name]
    if not df.empty and key_col in df.columns:
        idx = df[df[key_col] == key_val].index
        for i in idx:
            for k, v in update_dict.items():
                df.at[i, k] = v
        st.session_state.db[sheet_name] = df
        return True
    return False

# ==========================================
# 3. AUTHENTICATION & SIDEBAR BRANDING
# ==========================================
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

def render_sidebar_header():
    st.sidebar.markdown("""
        <div style="text-align: center; padding: 10px; background-color: #0F4C81; color: white; border-radius: 8px; margin-bottom: 15px;">
            <h2 style="margin:0; font-size: 20px;">🏗️ INDUSTRIAL CORP</h2>
            <p style="margin:0; font-size: 11px; color: #A3D1FF;">Installation Management System</p>
        </div>
    """, unsafe_allow_html=True)

render_sidebar_header()

if not st.session_state.authenticated_user:
    st.title("🔐 Worker & Supervisor Authentication")
    df_workers = read_sheet("Workers_Master")
    worker_names = df_workers["name"].tolist() if not df_workers.empty else []

    col1, col2 = st.columns(2)
    with col1:
        selected_name = st.selectbox("Select Your Name", worker_names)
    with col2:
        entered_pin = st.text_input("Enter 4-Digit PIN", type="password", max_chars=4)

    if st.button("Authenticate", type="primary", use_container_width=True):
        user_row = df_workers[(df_workers["name"] == selected_name) & (df_workers["pin"].astype(str) == str(entered_pin))]
        if not user_row.empty:
            st.session_state.authenticated_user = user_row.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("Invalid PIN. Please try again.")
    st.stop()

# Active Session
user = st.session_state.authenticated_user
user_name = user["name"]
user_role = user["role"]
user_base_location = user["base_location"]

st.sidebar.markdown(f"**User:** {user_name} (`{user_role}`)  \n**Base:** {user_base_location}")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.authenticated_user = None
    st.rerun()

st.sidebar.divider()

# Navigation Routing based on Role
STATUS_OPTIONS = ["In Progress", "Completed", "On Hold", "Pending Inspection"]

if user_role == "Admin":
    menu_options = [
        "Active Tasks Dashboard", 
        "Handover Date Dashboard", 
        "New Installation Order", 
        "Log Daily Tasks", 
        "Team Head Dashboard", 
        "View Logs & Update Status", 
        "Master Database"
    ]
elif user_role == "Supervisor":
    menu_options = [
        "Active Tasks Dashboard", 
        "Handover Date Dashboard", 
        "New Installation Order", 
        "Log Daily Tasks", 
        "Team Head Dashboard", 
        "View Logs & Update Status", 
        "Master Database"
    ]
else:
    menu_options = ["Log Daily Tasks"]

menu = st.sidebar.radio("Navigation Menu", menu_options)

# ==========================================
# 4. HELPER: RESTRICTED WORK LOG FORM
# ==========================================
def render_restricted_work_input(target_worker_name, is_crew_log=False):
    df_sites = read_sheet("Sites_Master")
    df_tasks = read_sheet("Task_Assignments")

    site_options = df_sites["installation_id"].tolist() if not df_sites.empty else []
    if not site_options:
        st.warning("No installation sites found.")
        return

    c_site, c_date = st.columns(2)
    with c_site:
        selected_site_id = st.selectbox(f"Select Site for {target_worker_name}", site_options, key=f"site_{target_worker_name}_{is_crew_log}")
    with c_date:
        log_date = st.date_input("Date of Work", value=datetime.now(), key=f"date_{target_worker_name}_{is_crew_log}")

    site_info = df_sites[df_sites["installation_id"] == selected_site_id].iloc[0]
    site_city = site_info["site_city"]

    # Travel / TA-DA Detection
    target_base = user_base_location
    if is_crew_log:
        df_w = read_sheet("Workers_Master")
        match = df_w[df_w["name"] == target_worker_name]
        if not match.empty:
            target_base = match.iloc[0]["base_location"]

    is_travel = str(target_base).strip().lower() != str(site_city).strip().lower()

    if is_travel:
        st.warning(f"✈️ **Travel Day Detected (TA/DA Triggered)**: Base (`{target_base}`) ≠ Site Location (`{site_city}`)")
    else:
        st.info(f"🏠 **Local Site**: Base (`{target_base}`) matches Site Location (`{site_city}`)")

    assigned_tasks = df_tasks[df_tasks["installation_id"] == selected_site_id]["task_name"].tolist() if not df_tasks.empty else []
    if not assigned_tasks:
        assigned_tasks = ["General Site Preparation & Assembly"]

    c_tsk, c_pct, c_hrs, c_min = st.columns([3, 2, 1, 1])
    with c_tsk:
        selected_task = st.selectbox("Task Worked On", assigned_tasks, key=f"tsk_{target_worker_name}_{is_crew_log}")
    with c_pct:
        progress_pct = st.selectbox("Progress (%)", [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100], index=5, key=f"pct_{target_worker_name}_{is_crew_log}")
    with c_hrs:
        hours_spent = st.number_input("Hours", min_value=0, max_value=24, value=8, key=f"hrs_{target_worker_name}_{is_crew_log}")
    with c_min:
        minutes_spent = st.selectbox("Minutes", [0, 15, 30, 45], key=f"min_{target_worker_name}_{is_crew_log}")

    site_remarks = st.text_area("Site Remarks / Delays", placeholder="Note any site obstacles, material shortages...", key=f"rem_{target_worker_name}_{is_crew_log}")

    if st.button(f"💾 Submit Daily Log for {target_worker_name}", type="primary", key=f"btn_{target_worker_name}_{is_crew_log}"):
        log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        log_entry = {
            "log_id": log_id,
            "installation_id": selected_site_id,
            "logged_date": str(log_date),
            "worker_name": target_worker_name,
            "role": user_role if target_worker_name == user_name else "Worker",
            "task_name": selected_task,
            "progress_percentage": progress_pct,
            "hours_spent": hours_spent,
            "minutes_spent": minutes_spent,
            "base_location": target_base,
            "site_city": site_city,
            "is_travel_day": is_travel,
            "site_remarks": site_remarks,
            "logged_by": user_name
        }
        append_to_sheet("Worker_Daily_Logs", log_entry)
        st.success(f"Log submitted successfully for **{target_worker_name}**!")
        st.rerun()

# ==========================================
# 5. PAGE IMPLEMENTATIONS
# ==========================================

# --- PAGE: ACTIVE TASKS DASHBOARD ---
if menu == "Active Tasks Dashboard":
    st.header("📋 Active Tasks Dashboard")
    df_tasks = read_sheet("Task_Assignments")
    df_sites = read_sheet("Sites_Master")

    if df_tasks.empty:
        st.info("No active tasks found.")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            site_filter = st.selectbox("Filter by Site", ["All Sites"] + df_sites["installation_id"].tolist())
        with col_f2:
            status_filter = st.selectbox("Filter by Task Status", ["All Statuses", "In Progress", "Pending", "Completed"])

        filtered_tasks = df_tasks.copy()
        if site_filter != "All Sites":
            filtered_tasks = filtered_tasks[filtered_tasks["installation_id"] == site_filter]
        if status_filter != "All Statuses":
            filtered_tasks = filtered_tasks[filtered_tasks["status"] == status_filter]

        st.dataframe(filtered_tasks, use_container_width=True)

# --- PAGE: HANDOVER DATE DASHBOARD ---
elif menu == "Handover Date Dashboard":
    st.header("📅 Site Handover Date Dashboard")
    df_sites = read_sheet("Sites_Master")

    if df_sites.empty:
        st.info("No installation sites found.")
    else:
        df_sites["handover_date"] = pd.to_datetime(df_sites["handover_date"])
        df_sites["days_remaining"] = (df_sites["handover_date"] - datetime.now()).dt.days

        st.subheader("Upcoming Project Handovers")
        for _, site in df_sites.iterrows():
            days = site["days_remaining"]
            badge_color = "#00A651" if days > 15 else ("#E6A100" if days >= 0 else "#D32F2F")
            
            st.markdown(f"""
                <div class="card-box">
                    <h3 style="margin:0; color:#0F4C81;">{site['site_name']} ({site['installation_id']})</h3>
                    <p style="margin:5px 0;"><b>Location:</b> {site['site_city']} | <b>Team Lead:</b> {site['team_lead']}</p>
                    <p style="margin:5px 0;"><b>Target Handover Date:</b> {site['handover_date'].strftime('%Y-%m-%d')}</p>
                    <p style="margin:5px 0;"><b>Status:</b> <span style="color:{badge_color}; font-weight:bold;">{site['status']} ({days} Days Remaining)</span></p>
                </div>
            """, unsafe_allow_html=True)

# --- PAGE: NEW INSTALLATION ORDER ---
elif menu == "New Installation Order":
    st.header("🆕 Create New Installation Order")
    with st.form("new_order_form"):
        c1, c2 = st.columns(2)
        with c1:
            inst_id = st.text_input("Installation ID", value=f"INST-2026-{datetime.now().strftime('%M%S')}")
            site_name = st.text_input("Site / Project Name")
            site_city = st.text_input("Site City")
        with c2:
            team_lead = st.text_input("Assigned Team Lead", value=user_name)
            order_date = st.date_input("Order Date", value=datetime.now())
            handover_date = st.date_input("Target Handover Date", value=datetime.now() + timedelta(days=30))

        submit = st.form_submit_button("Create Installation Order", type="primary")
        if submit:
            if not site_name or not site_city:
                st.error("Please fill in all site details.")
            else:
                new_site = {
                    "installation_id": inst_id,
                    "site_name": site_name,
                    "site_city": site_city,
                    "team_lead": team_lead,
                    "status": "In Progress",
                    "order_date": str(order_date),
                    "handover_date": str(handover_date)
                }
                append_to_sheet("Sites_Master", new_site)
                st.success(f"Installation Order **{inst_id}** created successfully!")

# --- PAGE: LOG DAILY TASKS ---
elif menu == "Log Daily Tasks":
    st.header(f"📝 Log Daily Tasks - {user_name}")
    render_restricted_work_input(target_worker_name=user_name, is_crew_log=False)

# --- PAGE: TEAM HEAD DASHBOARD ---
elif menu == "Team Head Dashboard":
    st.header("👥 Dual-Tab Team Head Dashboard")
    tab_personal, tab_crew = st.tabs(["👤 Personal Daily Work Log", "👨‍🔧 Crew Daily Hours & Task Logging"])

    with tab_personal:
        st.subheader(f"Personal Execution Log ({user_name})")
        render_restricted_work_input(target_worker_name=user_name, is_crew_log=False)

    with tab_crew:
        st.subheader("Manage Crew Daily Logs")
        df_workers = read_sheet("Workers_Master")
        crew_members = df_workers[df_workers["role"] == "Worker"]["name"].tolist() if not df_workers.empty else []

        if not crew_members:
            st.info("No workers registered in Workers_Master.")
        else:
            selected_crew = st.selectbox("Select Worker to Log For", crew_members)
            st.divider()
            render_restricted_work_input(target_worker_name=selected_crew, is_crew_log=True)

# --- PAGE: VIEW LOGS & UPDATE STATUS ---
elif menu == "View Logs & Update Status":
    st.header("🔍 View Daily Logs & Update Site Status")
    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_sites.empty:
        st.info("No installation projects available.")
    else:
        site_list = df_sites["installation_id"].tolist()
        selected_inst = st.selectbox("Select Installation ID", site_list)

        site_row = df_sites[df_sites["installation_id"] == selected_inst].iloc[0]
        
        st.markdown(f"""
            <div class="card-box">
                <h3 style="margin:0; color:#0F4C81;">{site_row['site_name']} ({site_row['installation_id']})</h3>
                <p style="margin:5px 0;"><b>City:</b> {site_row['site_city']} | <b>Team Lead:</b> {site_row['team_lead']}</p>
                <p style="margin:5px 0;"><b>Current Status:</b> <b>{site_row['status']}</b></p>
            </div>
        """, unsafe_allow_html=True)

        st.subheader("⚙️ Update Project Status")
        col_st, col_btn = st.columns([2, 1])
        with col_st:
            curr_st = site_row['status']
            st_idx = STATUS_OPTIONS.index(curr_st) if curr_st in STATUS_OPTIONS else 0
            new_st = st.selectbox("New Status", STATUS_OPTIONS, index=st_idx)
        with col_btn:
            st.write(" ")
            st.write(" ")
            if st.button("Update Status", type="primary"):
                update_sheet_row("Sites_Master", "installation_id", selected_inst, {"status": new_st})
                st.success(f"Status updated to **{new_st}**!")
                st.rerun()

        st.divider()
        st.subheader("📜 Submitted Work Logs")
        p_logs = df_logs[df_logs["installation_id"] == selected_inst] if not df_logs.empty else pd.DataFrame()

        if p_logs.empty:
            st.info("No work logs recorded for this site yet.")
        else:
            for _, l in p_logs.iterrows():
                with st.expander(f"📅 Date: {l.get('logged_date')} | Worker: {l.get('worker_name')} | Log ID: {l.get('log_id')}"):
                    st.write(f"**Task:** {l.get('task_name')} ({l.get('progress_percentage')}% Completed)")
                    st.write(f"**Time Spent:** {l.get('hours_spent')} hrs {l.get('minutes_spent')} mins")
                    st.write(f"**Travel Day:** {'Yes (TA/DA Triggered)' if l.get('is_travel_day') else 'No (Local)'}")
                    st.write(f"**Remarks:** {l.get('site_remarks', 'None')}")

# --- PAGE: MASTER DATABASE ---
elif menu == "Master Database":
    st.header("🗄️ Master Database Views")
    m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["Workers Master", "Sites Master", "Task Assignments", "Worker Daily Logs"])

    with m_tab1:
        st.dataframe(read_sheet("Workers_Master"), use_container_width=True)
    with m_tab2:
        st.dataframe(read_sheet("Sites_Master"), use_container_width=True)
    with m_tab3:
        st.dataframe(read_sheet("Task_Assignments"), use_container_width=True)
    with m_tab4:
        st.dataframe(read_sheet("Worker_Daily_Logs"), use_container_width=True)
