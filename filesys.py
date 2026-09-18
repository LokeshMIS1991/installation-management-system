import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import random
import string
import os

# Page Configuration
st.set_page_config(
    page_title="Sidharth Shutter & Automation", 
    page_icon="🏢",
    layout="wide"
)

# Replace this with your Google Sheet ID (found in the URL: docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit)
SPREADSHEET_ID = "YOUR_GOOGLE_SHEET_ID_HERE"

# Render High-Quality Logo in Navigation Bar
LOGO_PATH = "Company Logo.jpeg"
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
else:
    st.sidebar.markdown("### 🏢 Sidharth Shutter")

st.sidebar.markdown("---")

# Custom CSS Theme
st.markdown("""
    <style>
    .stApp { background-color: #FAFCFE; }
    h1, h2, h3 { color: #0F4C81 !important; font-weight: 700 !important; }
    div.stButton > button:first-child {
        background-color: #00A651 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
    }
    div.stButton > button:first-child:hover { background-color: #008741 !important; }
    button[kind="primary"] {
        background: linear-gradient(135deg, #0F4C81 0%, #1A6BBA 100%) !important;
        color: white !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #F0F5FA !important;
        border-right: 2px solid #0F4C81 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Google Sheets Connection Management
def get_gspread_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    
    return gspread.authorize(creds)

def get_worksheet(worksheet_name):
    client = get_gspread_client()
    if SPREADSHEET_ID == "YOUR_GOOGLE_SHEET_ID_HERE":
        # Fallback to file title search if ID is not yet provided
        return client.open("Installation_Schedules").worksheet(worksheet_name)
    return client.open_by_key(SPREADSHEET_ID).worksheet(worksheet_name)

def read_sheet(sheet_name):
    try:
        sheet = get_worksheet(sheet_name)
        rows = sheet.get_all_values()
        
        if not rows or len(rows) < 2:
            return get_empty_default_df(sheet_name)
            
        headers = [str(h).strip().lower() for h in rows[0]]
        data = rows[1:]
        df = pd.DataFrame(data, columns=headers)
        
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
        return df
    except Exception as e:
        st.error(f"⚠️ Error loading tab '{sheet_name}': {e}")
        return get_empty_default_df(sheet_name)

def get_empty_default_df(sheet_name):
    if sheet_name == "Installations":
        return pd.DataFrame(columns=[
            "installation_id", "city_prefix", "site_address", "team_details", 
            "order_created_date", "site_clearance_date", "target_ho_date", "status"
        ])
    elif sheet_name == "Order_Items":
        return pd.DataFrame(columns=["installation_id", "category", "sub_category", "dimensions", "quantity"])
    elif sheet_name == "Daily_Logs":
        return pd.DataFrame(columns=[
            "log_id", "installation_id", "day_number", "logged_timestamp", 
            "logged_date", "product_worked_on", "tasks_completed", 
            "next_day_planned_tasks", "submitted_by"
        ])
    return pd.DataFrame()

def append_to_sheet(sheet_name, row_data):
    try:
        sheet = get_worksheet(sheet_name)
        sheet.append_row(row_data)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Failed to append row to {sheet_name}: {e}")

def update_sheet_row(sheet_name, key_column_name, key_value, updated_row_dict):
    try:
        sheet = get_worksheet(sheet_name)
        rows = sheet.get_all_values()
        if not rows:
            return False
            
        headers = [str(h).strip().lower() for h in rows[0]]
        key_column_name_lower = str(key_column_name).strip().lower()
        
        if key_column_name_lower not in headers:
            return False
            
        key_col_idx = headers.index(key_column_name_lower)
        
        for row_idx, row in enumerate(rows[1:], start=2):
            if len(row) > key_col_idx and str(row[key_col_idx]).strip() == str(key_value).strip():
                for col_name, val in updated_row_dict.items():
                    col_name_lower = str(col_name).strip().lower()
                    if col_name_lower in headers:
                        target_col_idx = headers.index(col_name_lower) + 1
                        sheet.update_cell(row_idx, target_col_idx, str(val))
                st.cache_data.clear()
                return True
    except Exception as e:
        st.error(f"Update failed: {e}")
    return False

def generate_project_id():
    year = datetime.now().strftime("%Y")
    chars = string.ascii_uppercase + string.digits
    return f"INST-{year}-{''.join(random.choices(chars, k=5))}"

def generate_log_id():
    year = datetime.now().strftime("%Y")
    chars = string.ascii_uppercase + string.digits
    return f"LOG-{year}-{''.join(random.choices(chars, k=5))}"

PRODUCT_CATALOG = {
    "Rolling Shutters": ["Motorized Rolling Shutter", "Gear Rolling Shutter", "Manual Rolling Shutter"],
    "Dock Leveler": ["Hydraulic Doclevller", "Hydraulic Dock Edge", "Manual Dock Edge"],
    "Gates": ["Sliding Gate", "Telescopic Gate", "L-Folding Gate", "Swing Gate", "Retractable Gate"],
    "Doors": ["High Speed Door", "Fire Door", "HMPS Door", "GPD Door", "Overhead Sectional Door"],
    "Boom Barrier": ["Automatic Traffic Barrier", "Heavy-Duty Traffic Barrier"],
    "Dock Shelter": ["Retractable Dock Shelter", "Inflatable Dock Shelter"],
    "Dock Bumper": ["Heavy Rubber Bumper", "Moulded Bumper"],
    "Other": ["Other"]
}

STATUS_OPTIONS = ["In Progress", "Pending", "Done", "Cancelled"]

st.markdown("""
    <div style="border-left: 6px solid #00A651; padding: 12px 18px; background-color: #F0F5FA; border-radius: 4px; margin-bottom: 25px;">
        <h1 style="margin:0; padding:0; font-size: 28px; color: #0F4C81;">🏢 Sidharth Shutter & Automation</h1>
        <p style="margin:2px 0 0 0; color: #1A6BBA; font-weight: 600; font-size: 14px;">Installation Management System</p>
    </div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("Navigation", [
    "New Installation Order", 
    "Log Daily Tasks",
    "Edit Task Log (By Primary Key)",
    "View Logs & Update Status", 
    "Master Database"
])

# 1. NEW INSTALLATION ORDER
if menu == "New Installation Order":
    st.header("Create New Installation Order")

    if "temp_inst_id" not in st.session_state:
        st.session_state.temp_inst_id = generate_project_id()

    st.markdown(f"**Automated Visit ID:** `{st.session_state.temp_inst_id}`")

    col1, col2 = st.columns(2)
    with col1:
        team_details = st.text_input("Team's Details *", placeholder="e.g., Rajeer + 2 Helpers")
        city_name = st.text_input("City Name *", "Mumbai").strip()
        site_address = st.text_area("Site Address *", placeholder="Full installation site address...")

    with col2:
        min_past_date = datetime.now() - timedelta(days=7)
        order_created_date = st.date_input("Installation Date (Order Created Date)", value=datetime.now(), min_value=min_past_date)
        site_clearance = st.date_input("Site Clearance Date", value=datetime.now(), min_value=min_past_date)
        target_ho_date = st.date_input("Target Handover Date", value=datetime.now() + timedelta(days=15), min_value=min_past_date)

    st.divider()

    col_cat, col_sub = st.columns(2)
    with col_cat:
        selected_category = st.selectbox("Select The Product", list(PRODUCT_CATALOG.keys()))
    with col_sub:
        selected_sub_category = st.selectbox("Select Sub-Category", PRODUCT_CATALOG[selected_category])

    final_product_name = selected_sub_category
    if selected_category == "Other" or selected_sub_category == "Other":
        custom_name = st.text_input("Enter Custom Product Name", placeholder="Specify item name...")
        if custom_name.strip():
            final_product_name = custom_name.strip()

    col_dim, col_qty = st.columns(2)
    with col_dim:
        dimensions = st.text_input("Dimensions (WxH)", placeholder="e.g., 5330X6000")
    with col_qty:
        quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

    st.divider()

    if st.button("Save Installation Order", use_container_width=True):
        if not team_details.strip():
            st.error("Please enter Team's Details.")
        elif not site_address.strip():
            st.error("Please enter a valid Site Address.")
        else:
            df_inst = read_sheet("Installations")
            existing_ids = df_inst["installation_id"].tolist() if not df_inst.empty else []
            
            inst_id = st.session_state.temp_inst_id
            while inst_id in existing_ids:
                inst_id = generate_project_id()

            city_prefix = city_name[:3].upper() if city_name else "GEN"

            inst_row = [
                inst_id, city_prefix, site_address, team_details, 
                str(order_created_date), str(site_clearance), str(target_ho_date), "In Progress"
            ]
            append_to_sheet("Installations", inst_row)
            
            item_row = [inst_id, selected_category, final_product_name, dimensions, int(quantity)]
            append_to_sheet("Order_Items", item_row)
            
            st.success(f"Saved to Google Sheets! Generated Installation ID: **`{inst_id}`**")
            st.session_state.temp_inst_id = generate_project_id()

# 2. LOG DAILY TASKS (WITH 5 MANUAL TASK SECTIONS)
elif menu == "Log Daily Tasks":
    st.header("📋 Log Daily Tasks")

    df_inst = read_sheet("Installations")
    df_logs = read_sheet("Daily_Logs")

    st.subheader("Select Installation Order")
    
    selected_id = None
    if df_inst.empty:
        st.warning("No installation records found in the Google Sheet database.")
    else:
        # Combined, single clean selection tool
        options_list = [f"{row['installation_id']} | {row['site_address'][:30]}..." for _, row in df_inst.iterrows()]
        selected_option = st.selectbox("Choose Installation Project ID:", options_list)
        if selected_option:
            selected_id = selected_option.split(" | ")[0]

    st.divider()

    if selected_id:
        inst_info = df_inst[df_inst["installation_id"] == selected_id].iloc[0]

        existing_logs = df_logs[df_logs["installation_id"] == selected_id] if not df_logs.empty else pd.DataFrame()
        day_number_int = len(existing_logs) + 1
        day_label = f"Day {day_number_int}"

        st.markdown(f"**Active Installation ID:** `{selected_id}` | **Day:** `{day_label}` | **Team:** `{inst_info['team_details']}`")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            log_date = st.date_input("Log Date", value=datetime.now())
        with col_p2:
            default_tech = inst_info['team_details'].split('+')[0].strip() if '+' in inst_info['team_details'] else inst_info['team_details']
            submitted_by = st.text_input("Technician Name *", value=default_tech)

        st.divider()
        st.subheader("🛠️ 5-Section Tasks & Remarks Form")

        task_sections_data = []

        # 5 Dynamic Manual Sections
        for sec in range(1, 6):
            with st.expander(f"📦 Task Section {sec}", expanded=(sec == 1)):
                sec_title = st.text_input(f"Section {sec} - Product / Task Name", key=f"sec_title_{sec}", placeholder=e.g., f"e.g., Gate {sec} or Rolling Shutter")
                
                st.markdown("**Sub-Tasks & Remarks (Type Manually):**")
                col_st1, col_st2 = st.columns(2)
                
                with col_st1:
                    sub1_name = st.text_input(f"Sub-Task 1 Name", key=f"sub1_name_{sec}", value="1. Reached")
                    sub1_rem = st.text_input(f"Sub-Task 1 Remark", key=f"sub1_rem_{sec}", placeholder="Enter remark...")
                    
                    sub2_name = st.text_input(f"Sub-Task 2 Name", key=f"sub2_name_{sec}", value="2. Open / Unpacked")
                    sub2_rem = st.text_input(f"Sub-Task 2 Remark", key=f"sub2_rem_{sec}", placeholder="Enter remark...")

                with col_st2:
                    sub3_name = st.text_input(f"Sub-Task 3 Name", key=f"sub3_name_{sec}", value="3. Count")
                    sub3_rem = st.text_input(f"Sub-Task 3 Remark", key=f"sub3_rem_{sec}", placeholder="Enter remark...")
                    
                    sub4_name = st.text_input(f"Sub-Task 4 Name", key=f"sub4_name_{sec}", value="4. Track / Progress")
                    sub4_rem = st.text_input(f"Sub-Task 4 Remark", key=f"sub4_rem_{sec}", placeholder="Enter remark...")

                if sec_title.strip():
                    task_sections_data.append({
                        "title": sec_title.strip(),
                        "sub1": f"{sub1_name}: {sub1_rem}" if sub1_rem.strip() else "",
                        "sub2": f"{sub2_name}: {sub2_rem}" if sub2_rem.strip() else "",
                        "sub3": f"{sub3_name}: {sub3_rem}" if sub3_rem.strip() else "",
                        "sub4": f"{sub4_name}: {sub4_rem}" if sub4_rem.strip() else ""
                    })

        st.divider()
        st.subheader("🔮 Next Day Planned Tasks")
        next_day_plan = st.text_area("Planned Tasks for Next Day", placeholder="Describe tomorrow's tasks...")

        if st.button("Submit Daily Task Log", use_container_width=True):
            if not task_sections_data:
                st.error("Please fill in at least Section 1 Product/Task Name and a remark.")
            elif not submitted_by.strip():
                st.error("Please specify the Technician Name.")
            else:
                # Format into structured pattern for Google Sheets
                formatted_entries = []
                summary_products = []
                for idx, sec_item in enumerate(task_sections_data, 1):
                    summary_products.append(sec_item["title"])
                    block = f"[{idx}. {sec_item['title']}]\n"
                    if sec_item["sub1"]: block += f"  • {sec_item['sub1']}\n"
                    if sec_item["sub2"]: block += f"  • {sec_item['sub2']}\n"
                    if sec_item["sub3"]: block += f"  • {sec_item['sub3']}\n"
                    if sec_item["sub4"]: block += f"  • {sec_item['sub4']}\n"
                    formatted_entries.append(block)

                combined_tasks_str = "\n".join(formatted_entries)
                products_str = ", ".join(summary_products)
                log_id = generate_log_id()
                auto_log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                log_row = [
                    log_id, selected_id, day_label, auto_log_time, str(log_date), 
                    products_str, combined_tasks_str, next_day_plan, submitted_by
                ]
                
                append_to_sheet("Daily_Logs", log_row)
                st.success(f"Log recorded successfully for Installation ID **`{selected_id}`** (Log ID: `{log_id}`)!")

# 3. EDIT TASK LOG (BY PRIMARY KEY)
elif menu == "Edit Task Log (By Primary Key)":
    st.header("✏️ Edit Task Log Entry by Log ID")

    df_logs = read_sheet("Daily_Logs")

    if df_logs.empty:
        st.warning("No task logs found in the database.")
    else:
        log_ids = df_logs["log_id"].tolist()
        selected_log_id = st.selectbox("Select Visit Log Key (LOG-YYYY-XXXXX):", log_ids)
        
        log_data = df_logs[df_logs["log_id"] == selected_log_id].iloc[0]

        with st.form("edit_log_form"):
            updated_product = st.text_input("Product Worked On", value=log_data['product_worked_on'])
            updated_tech = st.text_input("Technician Name", value=log_data['submitted_by'])
            updated_completed = st.text_area("Tasks & Remarks", value=log_data['tasks_completed'], height=200)
            updated_next = st.text_area("Planned Next Day Tasks", value=log_data.get('next_day_planned_tasks', ''), height=100)

            if st.form_submit_button("Update Log Entry in Google Sheets"):
                updates = {
                    "product_worked_on": updated_product,
                    "submitted_by": updated_tech,
                    "tasks_completed": updated_completed,
                    "next_day_planned_tasks": updated_next,
                    "logged_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " (Edited)"
                }
                
                if update_sheet_row("Daily_Logs", "log_id", selected_log_id, updates):
                    st.success(f"Log Key `{selected_log_id}` updated!")
                else:
                    st.error("Failed to update Google Sheet entry.")

# 4. VIEW LOGS & UPDATE STATUS
elif menu == "View Logs & Update Status":
    st.header("🔍 View Logs & Update Installation Status")

    df_inst = read_sheet("Installations")
    
    if df_inst.empty:
        st.warning("No Installation IDs recorded.")
    else:
        inst_map = {f"{row['installation_id']} | {row['site_address'][:30]}...": row['installation_id'] for _, row in df_inst.iterrows()}
        selected_label = st.selectbox("Select Installation Project ID:", list(inst_map.keys()))
        selected_id = inst_map[selected_label]

        site_info = df_inst[df_inst["installation_id"] == selected_id].iloc[0]
        st.success(f"Target Installation Project ID: `{site_info['installation_id']}`")
        
        current_status = site_info['status'] if site_info['status'] in STATUS_OPTIONS else "In Progress"
        new_status = st.selectbox("Change Overall Status:", STATUS_OPTIONS, index=STATUS_OPTIONS.index(current_status))
        
        if st.button("Update Status", type="primary"):
            if update_sheet_row("Installations", "installation_id", selected_id, {"status": new_status}):
                st.success(f"Status for Project `{selected_id}` updated to **{new_status}**!")
                st.rerun()

        st.divider()
        st.subheader("📅 Activity Timeline")
        
        df_logs = read_sheet("Daily_Logs")
        site_logs = df_logs[df_logs["installation_id"] == selected_id] if not df_logs.empty else pd.DataFrame()

        if site_logs.empty:
            st.info("No activity logs recorded for this Installation ID yet.")
        else:
            for _, row in site_logs.iterrows():
                with st.expander(f"📅 **{row.get('day_number', 'Day Log')} - Date: {row['logged_date']}**", expanded=True):
                    st.markdown(f"**Log ID:** `{row['log_id']}` | **Technician:** {row['submitted_by']}")
                    st.text(row['tasks_completed'])

# 5. MASTER DATABASE
elif menu == "Master Database":
    st.header("Master Database View (Google Sheets)")
    
    st.subheader("1. All Installations")
    st.dataframe(read_sheet("Installations"), use_container_width=True)
    
    st.subheader("2. All Order Items")
    st.dataframe(read_sheet("Order_Items"), use_container_width=True)
    
    st.subheader("3. All Log Entries")
    st.dataframe(read_sheet("Daily_Logs"), use_container_width=True)
