import os
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# ==========================================
# 1. PAGE CONFIG & GLOBAL THEME
# ==========================================
st.set_page_config(
    page_title="Sidharth Shutter & Automation - Portal", 
    layout="wide", 
    page_icon="⚙️"
)

COLOR_PRIMARY = "#10418A"    # Sidharth Deep Blue
COLOR_ACCENT = "#00A859"     # Vibrant Green Dot
COLOR_BG_LIGHT = "#EBF3FA"   # Soft Blue Background Tint
COLOR_LOGOUT = "#9E2A2B"     # Sidharth Crimson Red for Logout

# Apply CSS Inject strictly targeted at UI elements
st.markdown(f"""
    <style>
    /* App background */
    .stApp {{
        background-color: #F4F7FC;
    }}
    
    /* Headers */
    h1, h2, h3 {{ 
        color: {COLOR_PRIMARY} !important; 
        font-weight: 700 !important; 
    }}
    
    /* Standard Buttons */
    .stButton>button {{ 
        background-color: {COLOR_PRIMARY} !important; 
        color: #FFFFFF !important; 
        border-radius: 6px !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }}
    
    /* Card Boxes & Dashboard Containers */
    .card-box {{ 
        background-color: {COLOR_BG_LIGHT}; 
        border-left: 6px solid {COLOR_PRIMARY}; 
        padding: 18px; 
        border-radius: 8px; 
        margin-bottom: 15px; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}

    .kpi-card {{
        background-color: #FFFFFF;
        border: 2px solid {COLOR_PRIMARY};
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }}

    .kpi-number {{
        font-size: 28px;
        font-weight: bold;
        color: {COLOR_PRIMARY};
    }}

    .kpi-label {{
        font-size: 13px;
        color: #6C757D;
        font-weight: 600;
    }}
    
    /* ==========================================
       SIDEBAR COMPACTION & LOGOUT BUTTON FIX
       ========================================== */
    section[data-testid="stSidebar"] {{
        background-color: #EBF1F8;
    }}

    /* Compact Sidebar Elements & Reduce Gaps */
    section[data-testid="stSidebar"] .block-container {{
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
    }}

    section[data-testid="stSidebar"] hr {{
        margin-top: 0.8rem !important;
        margin-bottom: 0.8rem !important;
    }}

    section[data-testid="stSidebar"] div[role="radiogroup"] > label {{
        padding-top: 2px !important;
        padding-bottom: 2px !important;
        margin-bottom: 2px !important;
    }}

    section[data-testid="stSidebar"] div[role="radiogroup"] {{
        gap: 4px !important;
    }}

    /* Distinct Crimson Red Logout Button */
    .sidebar-logout-container button {{
        background-color: {COLOR_LOGOUT} !important;
        background: {COLOR_LOGOUT} !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 10px 0px !important;
        font-size: 15px !important;
        border: none !important;
        width: 100% !important;
        margin-top: 10px !important;
        box-shadow: 0 4px 10px rgba(158, 42, 43, 0.3) !important;
    }}
    .sidebar-logout-container button * {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}
    .sidebar-logout-container button:hover {{
        background-color: #7F1D1D !important;
        background: #7F1D1D !important;
        box-shadow: 0 6px 14px rgba(127, 29, 29, 0.45) !important;
    }}

    /* ==========================================
       LOGIN FORM & BLUE INPUT OUTLINES
       ========================================== */
    div[data-testid="stForm"] {{
        background-color: #FFFFFF;
        border: 2px solid {COLOR_PRIMARY};
        border-radius: 16px;
        padding: 30px 25px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
        max-width: 480px;
        margin: 0 auto;
    }}

    .login-caption {{
        color: #6C757D;
        text-align: center;
        font-size: 13px;
        margin-top: 10px;
        margin-bottom: 20px;
        font-weight: 500;
    }}

    div[data-testid="stForm"] .stTextInput label {{
        color: {COLOR_PRIMARY} !important;
        font-weight: 700 !important;
    }}

    div[data-testid="stForm"] div[data-baseweb="input"] {{
        border: 2px solid {COLOR_PRIMARY} !important;
        border-radius: 8px !important;
        background-color: #FFFFFF !important;
    }}
    
    div[data-testid="stForm"] div[data-baseweb="input"]:focus-within {{
        border-color: {COLOR_ACCENT} !important;
        box-shadow: 0 0 6px rgba(0, 168, 89, 0.4) !important;
    }}

    div[data-testid="stForm"] .stCheckbox label {{
        color: {COLOR_PRIMARY} !important;
        font-weight: 600 !important;
    }}

    div[data-testid="stFormSubmitButton"] > button {{
        background-color: {COLOR_ACCENT} !important;
        background: {COLOR_ACCENT} !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 12px 0px !important;
        font-size: 16px !important;
        border: none !important;
        width: 100% !important;
        margin-top: 15px !important;
        box-shadow: 0 4px 12px rgba(0, 168, 89, 0.35) !important;
    }}

    div[data-testid="stFormSubmitButton"] > button * {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}

    div[data-testid="stFormSubmitButton"] > button:hover {{
        background-color: #008747 !important;
        background: #008747 !important;
        color: #FFFFFF !important;
        box-shadow: 0 6px 15px rgba(0, 168, 89, 0.5) !important;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GOOGLE SHEETS LIVE CONNECTION ENGINE
# ==========================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_gspread_client():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(credentials)

def get_workbook():
    client = get_gspread_client()
    sheet_url = st.secrets.get("spreadsheet_url", "https://docs.google.com/spreadsheets/d/19rQC3aNtosjhSwyctKAk9ojUt0c8gyOPH-Q8trW5q5s/edit")
    return client.open_by_url(sheet_url)

def read_sheet(sheet_name: str) -> pd.DataFrame:
    try:
        wb = get_workbook()
        sheet = wb.worksheet(sheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error reading tab '{sheet_name}': {e}")
        return pd.DataFrame()

def append_to_sheet(sheet_name: str, row_data_dict: dict):
    try:
        wb = get_workbook()
        sheet = wb.worksheet(sheet_name)
        headers = sheet.row_values(1)
        if not headers:
            headers = list(row_data_dict.keys())
            sheet.append_row(headers)
        row_values = [str(row_data_dict.get(h, "")) for h in headers]
        sheet.append_row(row_values)
    except Exception as e:
        st.error(f"Error writing to tab '{sheet_name}': {e}")

def update_sheet_row(sheet_name: str, key_col: str, key_val: str, update_dict: dict) -> bool:
    try:
        wb = get_workbook()
        sheet = wb.worksheet(sheet_name)
        df = pd.DataFrame(sheet.get_all_records())
        if df.empty or key_col not in df.columns:
            return False
        match_idx = df[df[key_col].astype(str) == str(key_val)].index
        if match_idx.empty:
            return False
        row_num = match_idx[0] + 2
        headers = sheet.row_values(1)
        for col_name, new_val in update_dict.items():
            if col_name in headers:
                col_num = headers.index(col_name) + 1
                sheet.update_cell(row_num, col_num, str(new_val))
        return True
    except Exception as e:
        st.error(f"Error updating tab '{sheet_name}': {e}")
        return False

# ==========================================
# 3. AUTHENTICATION (FORM LAYOUT)
# ==========================================
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if "remembered_username" not in st.session_state:
    st.session_state.remembered_username = ""

if not st.session_state.authenticated_user:
    st.write("##")
    
    with st.form("login_form"):
        logo_path = "Company Logo.jpeg"
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
        else:
            st.markdown(f"""
                <div style="text-align: center;">
                    <h1 style="color: {COLOR_PRIMARY}; margin: 0; font-size: 32px;">SIDHARTH</h1>
                    <p style="color: {COLOR_ACCENT}; font-weight: bold; margin: 0; font-size: 14px; letter-spacing: 2px;">SHUTTER & AUTOMATION</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="login-caption">Enterprise Operations & Field Portal</div>', unsafe_allow_html=True)

        username_input = st.text_input("Username / Name", value=st.session_state.remembered_username, placeholder="e.g. Admin User or Vishak")
        password_input = st.text_input("Password / PIN", type="password", placeholder="Enter password")

        col_chk1, col_chk2 = st.columns(2)
        with col_chk1:
            show_pass = st.checkbox("Show Password")
        with col_chk2:
            remember_me = st.checkbox("Remember Me", value=bool(st.session_state.remembered_username))

        submit_button = st.form_submit_button("🔑 LOGIN TO DASHBOARD", use_container_width=True)

        if submit_button:
            if not username_input or not password_input:
                st.error("Please fill in both Username and Password.")
            else:
                df_workers = read_sheet("Workers_Master")
                if not df_workers.empty:
                    user_row = df_workers[
                        (df_workers["name"].astype(str).str.strip().str.lower() == username_input.strip().lower()) & 
                        (df_workers["pin"].astype(str) == str(password_input).strip())
                    ]
                    if not user_row.empty:
                        st.session_state.authenticated_user = user_row.iloc[0].to_dict()
                        if remember_me:
                            st.session_state.remembered_username = username_input.strip()
                        else:
                            st.session_state.remembered_username = ""
                        st.success("Authentication Successful!")
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password.")
                else:
                    st.error("Unable to load user database. Verify Google Sheets setup.")
    st.stop()

# ==========================================
# 4. ACTIVE SESSION & SIDEBAR NAVIGATION
# ==========================================
user = st.session_state.authenticated_user
user_name = user.get("name", "User")
user_role = user.get("role", "Worker")
user_base_location = user.get("base_location", "Jaipur")

logo_path = "Company Logo.jpeg"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    st.sidebar.markdown(f"""
        <div style="text-align: center; padding: 12px; background-color: {COLOR_PRIMARY}; color: white; border-radius: 8px; margin-bottom: 10px;">
            <h2 style="margin:0; font-size: 21px; color: white !important;">SIDHARTH</h2>
            <p style="margin:0; font-size: 11px; letter-spacing: 1.5px; color: {COLOR_ACCENT}; font-weight: bold;">SHUTTER & AUTOMATION</p>
        </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown(f"**Active User:** {user_name} (`{user_role}`)  \n**Base Station:** {user_base_location}")
st.sidebar.divider()

STATUS_OPTIONS = ["In Progress", "Completed", "On Hold", "Pending Inspection"]

if user_role == "Admin":
    menu_options = [
        "Admin Analytics Dashboard", 
        "User Management", 
        "TA/DA Payroll & Travel Summary", 
        "Advanced Field Logs Inspector", 
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

st.sidebar.divider()

# Crimson Red Logout Button BELOW Navigation
st.sidebar.markdown('<div class="sidebar-logout-container">', unsafe_allow_html=True)
if st.sidebar.button("🚪 LOG OUT", use_container_width=True):
    st.session_state.authenticated_user = None
    st.rerun()
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 5. RESTRICTED LOGGING FORM HELPER
# ==========================================
def render_restricted_work_input(target_worker_name, is_crew_log=False):
    df_sites = read_sheet("Sites_Master")
    df_tasks = read_sheet("Task_Assignments")

    site_options = df_sites["installation_id"].tolist() if not df_sites.empty and "installation_id" in df_sites.columns else []
    if not site_options:
        st.warning("No installation sites found in Google Sheets 'Sites_Master'.")
        return

    c_site, c_date = st.columns(2)
    with c_site:
        selected_site_id = st.selectbox(f"Select Site for {target_worker_name}", site_options, key=f"site_{target_worker_name}_{is_crew_log}")
    with c_date:
        log_date = st.date_input("Date of Work", value=datetime.now(), key=f"date_{target_worker_name}_{is_crew_log}")

    site_info = df_sites[df_sites["installation_id"] == selected_site_id].iloc[0]
    site_city = site_info.get("site_city", "Jaipur")

    target_base = user_base_location
    if is_crew_log:
        df_w = read_sheet("Workers_Master")
        match = df_w[df_w["name"] == target_worker_name]
        if not match.empty:
            target_base = match.iloc[0].get("base_location", "Jaipur")

    is_travel = str(target_base).strip().lower() != str(site_city).strip().lower()

    if is_travel:
        st.warning(f"✈️ **Travel Day Detected (TA/DA Triggered)**: Base (`{target_base}`) ≠ Site Location (`{site_city}`)")
    else:
        st.info(f"🏠 **Local Site**: Base (`{target_base}`) matches Site Location (`{site_city}`)")

    assigned_tasks = df_tasks[df_tasks["installation_id"] == selected_site_id]["task_name"].tolist() if not df_tasks.empty and "task_name" in df_tasks.columns else []
    if not assigned_tasks:
        assigned_tasks = ["Motorized Rolling Shutter Assembly", "Electrical Wiring & Automation", "Sliding Gate Fitting", "Structural Welding"]

    c_tsk, c_pct, c_hrs, c_min = st.columns([3, 2, 1, 1])
    with c_tsk:
        selected_task = st.selectbox("Task Worked On", assigned_tasks, key=f"tsk_{target_worker_name}_{is_crew_log}")
    with c_pct:
        progress_pct = st.selectbox("Progress (%)", [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100], index=5, key=f"pct_{target_worker_name}_{is_crew_log}")
    with c_hrs:
        hours_spent = st.number_input("Hours", min_value=0, max_value=24, value=8, key=f"hrs_{target_worker_name}_{is_crew_log}")
    with c_min:
        minutes_spent = st.selectbox("Minutes", [0, 15, 30, 45], key=f"min_{target_worker_name}_{is_crew_log}")

    site_remarks = st.text_area("Site Remarks / Delays", placeholder="Note any motor issues, power availability, or structural delays...", key=f"rem_{target_worker_name}_{is_crew_log}")

    if st.button(f"💾 Sync Daily Log to Google Sheets ({target_worker_name})", type="primary", key=f"btn_{target_worker_name}_{is_crew_log}"):
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
            "is_travel_day": "Yes" if is_travel else "No",
            "site_remarks": site_remarks,
            "logged_by": user_name
        }
        append_to_sheet("Worker_Daily_Logs", log_entry)
        st.success(f"Successfully recorded log for **{target_worker_name}**!")
        st.rerun()

# ==========================================
# 6. MODULE IMPLEMENTATIONS
# ==========================================

if menu == "Admin Analytics Dashboard":
    st.header("📊 Admin Operations Dashboard")
    df_logs = read_sheet("Worker_Daily_Logs")
    df_workers = read_sheet("Workers_Master")
    df_sites = read_sheet("Sites_Master")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{len(df_workers)}</div><div class="kpi-label">Active Team Members</div></div>', unsafe_allow_html=True)
    with kpi2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{len(df_sites)}</div><div class="kpi-label">Total Installation Sites</div></div>', unsafe_allow_html=True)
    with kpi3:
        tot_hrs = df_logs["hours_spent"].sum() if not df_logs.empty and "hours_spent" in df_logs.columns else 0
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{tot_hrs} hrs</div><div class="kpi-label">Total Field Hours Logged</div></div>', unsafe_allow_html=True)
    with kpi4:
        trv_days = len(df_logs[df_logs["is_travel_day"] == "Yes"]) if not df_logs.empty and "is_travel_day" in df_logs.columns else 0
        st.markdown(f'<div class="kpi-card"><div class="kpi-number">{trv_days} Days</div><div class="kpi-label">TA/DA Travel Days Claims</div></div>', unsafe_allow_html=True)

    st.write("##")
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("Field Hours per Worker")
        if not df_logs.empty and "worker_name" in df_logs.columns:
            hrs_df = df_logs.groupby("worker_name")["hours_spent"].sum().reset_index()
            st.bar_chart(hrs_df.set_index("worker_name"))
        else:
            st.info("No work logs available for charts.")

    with col_chart2:
        st.subheader("Site Status Distribution")
        if not df_sites.empty and "status" in df_sites.columns:
            st_counts = df_sites["status"].value_counts()
            st.bar_chart(st_counts)
        else:
            st.info("No site status data available.")

elif menu == "User Management":
    st.header("👥 User & Access Management")
    df_workers = read_sheet("Workers_Master")

    tab_add, tab_edit = st.tabs(["➕ Add New Team Member", "✏️ Edit Existing User & Role"])

    with tab_add:
        st.subheader("Add Worker / Supervisor to System")
        with st.form("add_user_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_w_id = st.text_input("Worker ID", value=f"W{len(df_workers)+1:03d}")
                new_name = st.text_input("Full Name")
                new_pin = st.text_input("4-Digit PIN / Password", type="password")
            with c2:
                new_role = st.selectbox("System Role", ["Worker", "Supervisor", "Admin"])
                new_base = st.text_input("Base Station / City", value="Jaipur")

            submit_new_user = st.form_submit_button("Create User & Sync to Google Sheets", type="primary")
            if submit_new_user:
                if not new_name or not new_pin:
                    st.error("Please enter Full Name and PIN.")
                else:
                    user_dict = {
                        "worker_id": new_w_id,
                        "name": new_name,
                        "pin": str(new_pin),
                        "role": new_role,
                        "base_location": new_base
                    }
                    append_to_sheet("Workers_Master", user_dict)
                    st.success(f"User **{new_name}** successfully added!")
                    st.rerun()

    with tab_edit:
        st.subheader("Update User Profile, Role & PIN")
        if df_workers.empty or "name" not in df_workers.columns:
            st.info("No users available in Workers_Master.")
        else:
            selected_edit_user = st.selectbox("Select User to Edit", df_workers["name"].tolist())
            user_data = df_workers[df_workers["name"] == selected_edit_user].iloc[0]

            with st.form("edit_user_form"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    e_role = st.selectbox("Update Role", ["Worker", "Supervisor", "Admin"], index=["Worker", "Supervisor", "Admin"].index(user_data.get("role", "Worker")))
                    e_pin = st.text_input("Update PIN", value=str(user_data.get("pin", "")))
                with e_col2:
                    e_base = st.text_input("Update Base Location", value=str(user_data.get("base_location", "Jaipur")))

                submit_edit = st.form_submit_button("Update Profile in Google Sheets", type="primary")
                if submit_edit:
                    updates = {
                        "role": e_role,
                        "pin": e_pin,
                        "base_location": e_base
                    }
                    update_sheet_row("Workers_Master", "name", selected_edit_user, updates)
                    st.success(f"Updated **{selected_edit_user}** successfully!")
                    st.rerun()

elif menu == "TA/DA Payroll & Travel Summary":
    st.header("✈️ TA/DA Travel Allowance & Payroll Report")
    st.caption("Automated calculation aggregating travel days (Base Location ≠ Site Location)")

    df_logs = read_sheet("Worker_Daily_Logs")

    if df_logs.empty or "is_travel_day" not in df_logs.columns:
        st.info("No travel log records found.")
    else:
        travel_logs = df_logs[df_logs["is_travel_day"] == "Yes"]

        if travel_logs.empty:
            st.warning("No travel days logged yet across any project site.")
        else:
            st.subheader("Travel Days Summary by Worker")
            summary_df = travel_logs.groupby(["worker_name", "base_location"]).agg(
                total_travel_days=("is_travel_day", "count"),
                total_hours_worked=("hours_spent", "sum")
            ).reset_index()

            col_rate, _ = st.columns([1, 2])
            with col_rate:
                ta_rate = st.number_input("Daily TA/DA Allowance Rate (₹)", value=500, step=50)

            summary_df["Estimated Allowance (₹)"] = summary_df["total_travel_days"] * ta_rate
            st.dataframe(summary_df, use_container_width=True)

            st.divider()
            st.subheader("Detailed Travel Log Records")
            st.dataframe(travel_logs[["log_id", "logged_date", "worker_name", "base_location", "site_city", "task_name", "hours_spent", "site_remarks"]], use_container_width=True)

            csv_payroll = summary_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export TA/DA Payroll Report (CSV)",
                data=csv_payroll,
                file_name=f"TADA_Payroll_Report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

elif menu == "Advanced Field Logs Inspector":
    st.header("🔍 Advanced Field Log Inspector & Exporter")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_logs.empty:
        st.info("No field logs recorded in Google Sheets.")
    else:
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            worker_list = ["All Workers"] + df_logs["worker_name"].unique().tolist()
            filter_worker = st.selectbox("Filter by Worker", worker_list)
        with f_col2:
            site_list = ["All Sites"] + df_logs["installation_id"].unique().tolist()
            filter_site = st.selectbox("Filter by Site ID", site_list)
        with f_col3:
            travel_filter = st.selectbox("Filter by Travel Day", ["All Logs", "Travel Days Only (Yes)", "Local Days Only (No)"])

        filtered_df = df_logs.copy()
        if filter_worker != "All Workers":
            filtered_df = filtered_df[filtered_df["worker_name"] == filter_worker]
        if filter_site != "All Sites":
            filtered_df = filtered_df[filtered_df["installation_id"] == filter_site]
        if travel_filter == "Travel Days Only (Yes)":
            filtered_df = filtered_df[filtered_df["is_travel_day"] == "Yes"]
        elif travel_filter == "Local Days Only (No)":
            filtered_df = filtered_df[filtered_df["is_travel_day"] == "No"]

        st.subheader(f"Matching Records ({len(filtered_df)} entries)")
        st.dataframe(filtered_df, use_container_width=True)

        csv_logs = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Filtered Logs to CSV",
            data=csv_logs,
            file_name=f"Filtered_Field_Logs_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

elif menu == "Active Tasks Dashboard":
    st.header("📋 Active Tasks Dashboard")
    df_tasks = read_sheet("Task_Assignments")
    df_sites = read_sheet("Sites_Master")

    if df_tasks.empty:
        st.info("No active tasks found in Google Sheets.")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            site_options = ["All Sites"] + (df_sites["installation_id"].tolist() if not df_sites.empty and "installation_id" in df_sites.columns else [])
            site_filter = st.selectbox("Filter by Site", site_options)
        with col_f2:
            status_filter = st.selectbox("Filter by Task Status", ["All Statuses", "In Progress", "Pending", "Completed"])

        filtered_tasks = df_tasks.copy()
        if site_filter != "All Sites" and "installation_id" in filtered_tasks.columns:
            filtered_tasks = filtered_tasks[filtered_tasks["installation_id"] == site_filter]
        if status_filter != "All Statuses" and "status" in filtered_tasks.columns:
            filtered_tasks = filtered_tasks[filtered_tasks["status"] == status_filter]

        st.dataframe(filtered_tasks, use_container_width=True)

elif menu == "Handover Date Dashboard":
    st.header("📅 Site Handover Date Dashboard")
    df_sites = read_sheet("Sites_Master")

    if df_sites.empty or "handover_date" not in df_sites.columns:
        st.info("No site handover records found in Google Sheets.")
    else:
        df_sites["handover_date_dt"] = pd.to_datetime(df_sites["handover_date"], errors="coerce")
        df_sites["days_remaining"] = (df_sites["handover_date_dt"] - datetime.now()).dt.days

        st.subheader("Upcoming Project Handovers")
        for _, site in df_sites.iterrows():
            days = site.get("days_remaining", 0)
            badge_color = COLOR_ACCENT if days > 15 else ("#E6A100" if days >= 0 else "#D32F2F")
            
            st.markdown(f"""
                <div class="card-box">
                    <h3 style="margin:0;">{site.get('site_name', 'N/A')} ({site.get('installation_id', 'N/A')})</h3>
                    <p style="margin:5px 0;"><b>City:</b> {site.get('site_city', 'N/A')} | <b>Team Lead:</b> {site.get('team_lead', 'N/A')}</p>
                    <p style="margin:5px 0;"><b>Target Handover:</b> {site.get('handover_date', 'N/A')}</p>
                    <p style="margin:5px 0;"><b>Status:</b> <span style="color:{badge_color}; font-weight:bold;">{site.get('status', 'In Progress')} ({days} Days Remaining)</span></p>
                </div>
            """, unsafe_allow_html=True)

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
                st.error("Please fill in site name and city.")
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
                st.success(f"Installation Order **{inst_id}** recorded in Google Sheets!")

elif menu == "Log Daily Tasks":
    st.header(f"📝 Log Daily Tasks - {user_name}")
    render_restricted_work_input(target_worker_name=user_name, is_crew_log=False)

elif menu == "Team Head Dashboard":
    st.header("👥 Dual-Tab Team Head Dashboard")
    tab_personal, tab_crew = st.tabs(["👤 Personal Work Log", "👨‍🔧 Crew Task Logging"])

    with tab_personal:
        st.subheader(f"Personal Execution Log ({user_name})")
        render_restricted_work_input(target_worker_name=user_name, is_crew_log=False)

    with tab_crew:
        st.subheader("Manage Active Crew Logs")
        df_workers = read_sheet("Workers_Master")
        crew_members = df_workers[df_workers["role"] == "Worker"]["name"].tolist() if not df_workers.empty and "role" in df_workers.columns else []

        if not crew_members:
            st.info("No workers registered in Google Sheets Workers_Master.")
        else:
            selected_crew = st.selectbox("Select Worker to Log For", crew_members)
            st.divider()
            render_restricted_work_input(target_worker_name=selected_crew, is_crew_log=True)

elif menu == "View Logs & Update Status":
    st.header("🔍 View Daily Logs & Update Status")
    df_sites = read_sheet("Sites_Master")
    df_logs = read_sheet("Worker_Daily_Logs")

    if df_sites.empty or "installation_id" not in df_sites.columns:
        st.info("No sites available in Google Sheets.")
    else:
        site_list = df_sites["installation_id"].tolist()
        selected_inst = st.selectbox("Select Installation ID", site_list)

        site_row = df_sites[df_sites["installation_id"] == selected_inst].iloc[0]
        
        st.markdown(f"""
            <div class="card-box">
                <h3 style="margin:0;">{site_row.get('site_name', 'N/A')} ({site_row.get('installation_id', 'N/A')})</h3>
                <p style="margin:5px 0;"><b>City:</b> {site_row.get('site_city', 'N/A')} | <b>Team Lead:</b> {site_row.get('team_lead', 'N/A')}</p>
                <p style="margin:5px 0;"><b>Current Status:</b> <b>{site_row.get('status', 'In Progress')}</b></p>
            </div>
        """, unsafe_allow_html=True)

        st.subheader("⚙️ Update Project Status")
        col_st, col_btn = st.columns([2, 1])
        with col_st:
            curr_st = site_row.get("status", "In Progress")
            st_idx = STATUS_OPTIONS.index(curr_st) if curr_st in STATUS_OPTIONS else 0
            new_st = st.selectbox("New Status", STATUS_OPTIONS, index=st_idx)
        with col_btn:
            st.write(" ")
            st.write(" ")
            if st.button("Update Status", type="primary"):
                update_sheet_row("Sites_Master", "installation_id", selected_inst, {"status": new_st})
                st.success(f"Status updated to **{new_st}** in Google Sheets!")
                st.rerun()

        st.divider()
        st.subheader("📜 Submitted Work Logs")
        p_logs = df_logs[df_logs["installation_id"] == selected_inst] if not df_logs.empty and "installation_id" in df_logs.columns else pd.DataFrame()

        if p_logs.empty:
            st.info("No logs recorded for this site yet.")
        else:
            for _, l in p_logs.iterrows():
                with st.expander(f"📅 Date: {l.get('logged_date')} | Worker: {l.get('worker_name')} | Log ID: {l.get('log_id')}"):
                    st.write(f"**Task:** {l.get('task_name')} ({l.get('progress_percentage')}% Progress)")
                    st.write(f"**Time Spent:** {l.get('hours_spent')} hrs {l.get('minutes_spent')} mins")
                    st.write(f"**Travel Day (TA/DA):** {l.get('is_travel_day')}")
                    st.write(f"**Remarks:** {l.get('site_remarks', 'None')}")

elif menu == "Master Database":
    st.header("🗄️ Live Google Sheets Database")
    m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["Workers Master", "Sites Master", "Task Assignments", "Worker Daily Logs"])

    with m_tab1:
        st.dataframe(read_sheet("Workers_Master"), use_container_width=True)
    with m_tab2:
        st.dataframe(read_sheet("Sites_Master"), use_container_width=True)
    with m_tab3:
        st.dataframe(read_sheet("Task_Assignments"), use_container_width=True)
    with m_tab4:
        st.dataframe(read_sheet("Worker_Daily_Logs"), use_container_width=True)
