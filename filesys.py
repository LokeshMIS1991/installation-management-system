import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import random
import string

# Initialize Google Sheets Connection
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

def get_worksheet(sheet_name):
    client = get_gspread_client()
    return client.open("Installation_Schedules").worksheet(sheet_name)

# Helper function to append rows to a specific worksheet
def append_to_sheet(sheet_name, row_data):
    sheet = get_worksheet(sheet_name)
    sheet.append_row(row_data)

# Helper function to read worksheet data into DataFrame
def read_sheet(sheet_name):
    sheet = get_worksheet(sheet_name)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# Helper function to update a specific record in Google Sheets by Primary Key
def update_sheet_row(sheet_name, key_column_name, key_value, updated_row_dict):
    sheet = get_worksheet(sheet_name)
    records = sheet.get_all_records()
    headers = sheet.row_values(1)
    
    for idx, row in enumerate(records, start=2):  # Row 1 is header
        if str(row.get(key_column_name)) == str(key_value):
            for col_name, val in updated_row_dict.items():
                if col_name in headers:
                    col_idx = headers.index(col_name) + 1
                    sheet.update_cell(idx, col_idx, str(val))
            return True
    return False

# Helper functions to generate structured IDs (e.g., INST-2026-249E6 and LOG-2026-249E6)
def generate_project_id():
    year = datetime.now().strftime("%Y")
    chars = string.ascii_uppercase + string.digits
    unique_suffix = ''.join(random.choices(chars, k=5))
    return f"INST-{year}-{unique_suffix}"

def generate_log_id():
    year = datetime.now().strftime("%Y")
    chars = string.ascii_uppercase + string.digits
    unique_suffix = ''.join(random.choices(chars, k=5))
    return f"LOG-{year}-{unique_suffix}"

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

st.set_page_config(page_title="Installation Management System", layout="wide")
st.title("🛠️ Installation Management System")

menu = st.sidebar.radio("Navigation", [
    "New Installation Order", 
    "Log Daily Tasks",
    "Edit Task Log (By Primary Key)",
    "View Logs & Update Status", 
    "Master Database"
])

if "task_count" not in st.session_state:
    st.session_state.task_count = 5

if "next_task_count" not in st.session_state:
    st.session_state.next_task_count = 3

# 1. NEW INSTALLATION ORDER
if menu == "New Installation Order":
    st.header("Create New Installation Order")

    col1, col2 = st.columns(2)
    
    with col1:
        team_details = st.text_input("Team's Details", placeholder="e.g., Rajeer + 2 Helpers")
        city_name = st.text_input("City Name", "Mumbai").strip()
        site_address = st.text_area("Site Address", placeholder="Full installation site address...")

    with col2:
        min_past_date = datetime.now() - timedelta(days=7)
        
        order_created_date = st.date_input(
            "Installation Date (Order Created Date)", 
            value=datetime.now(), 
            min_value=min_past_date
        )
        site_clearance = st.date_input(
            "Site Clearance Date", 
            value=datetime.now(), 
            min_value=min_past_date
        )
        target_ho_date = st.date_input(
            "Target Handover Date", 
            value=datetime.now() + timedelta(days=15), 
            min_value=min_past_date
        )

    st.divider()

    col_cat, col_sub = st.columns(2)
    with col_cat:
        selected_category = st.selectbox("Select The product", list(PRODUCT_CATALOG.keys()))
    with col_sub:
        selected_sub_category = st.selectbox("Select Sub-Category", PRODUCT_CATALOG[selected_category])

    final_product_name = selected_sub_category
    if selected_category == "Other" or selected_sub_category == "Other":
        custom_name = st.text_input("Enter Custom Product Name", placeholder="Specify item name...")
        if custom_name.strip():
            final_product_name = custom_name.strip()

    with st.form("new_order_form"):
        col_dim, col_qty = st.columns(2)
        with col_dim:
            dimensions = st.text_input("Dimensions (WxH)", placeholder="e.g., 5330X6000")
        with col_qty:
            quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

        submitted = st.form_submit_button("Save Installation Order")

        if submitted:
            if not team_details.strip():
                st.error("Please enter Team's Details.")
            elif not site_address.strip():
                st.error("Please enter a valid Site Address.")
            else:
                df_inst = read_sheet("Installations")
                existing_ids = df_inst["installation_id"].tolist() if not df_inst.empty else []
                
                # Auto-generate unique installation project ID (e.g., INST-2026-249E6)
                inst_id = generate_project_id()
                while inst_id in existing_ids:
                    inst_id = generate_project_id()

                city_prefix = city_name[:3].upper() if city_name else "GEN"

                inst_row = [
                    inst_id, 
                    city_prefix, 
                    site_address, 
                    team_details, 
                    str(order_created_date), 
                    str(site_clearance), 
                    str(target_ho_date), 
                    "In Progress"
                ]
                append_to_sheet("Installations", inst_row)
                
                item_row = [inst_id, selected_category, final_product_name, dimensions, int(quantity)]
                append_to_sheet("Order_Items", item_row)
                
                st.success(f"Saved to Google Sheets! Generated Installation Project ID: **`{inst_id}`**")

# 2. LOG DAILY TASKS
elif menu == "Log Daily Tasks":
    st.header("📋 Log Daily Tasks")
    
    log_date = st.date_input("Select Log Date", value=datetime.now(), min_value=datetime.now() - timedelta(days=14))
    auto_log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df_inst = read_sheet("Installations")
    df_logs = read_sheet("Daily_Logs")
    
    if df_inst.empty:
        st.warning("No active Installation IDs found. Please create a new order first.")
    else:
        active_inst = df_inst[df_inst["status"].isin(["In Progress", "Pending"])]
        if active_inst.empty:
            st.info("No installations currently 'In Progress' or 'Pending'.")
        else:
            id_map = {f"{row['installation_id']} | {row['site_address'][:25]}...": row['installation_id'] for _, row in active_inst.iterrows()}
            selected_label = st.selectbox("Select Installation Project ID:", list(id_map.keys()))
            selected_id = id_map[selected_label]

            existing_logs = df_logs[df_logs["installation_id"] == selected_id] if not df_logs.empty else pd.DataFrame()
            day_number_int = len(existing_logs) + 1
            day_label = f"Day {day_number_int}"

            inst_info = active_inst[active_inst["installation_id"] == selected_id].iloc[0]

            df_items = read_sheet("Order_Items")
            site_items = df_items[df_items["installation_id"] == selected_id]
            
            product_options = [f"{row['sub_category']} ({row['dimensions']})" for _, row in site_items.iterrows()] if not site_items.empty else []
            product_options.append("General Site Work / Preparation")

            # Active Insertion Banner showing target ID explicitly
            st.success(f"📍 **INSERTING DATA FOR INSTALLATION ID:** `{selected_id}` | 👥 **Team:** {inst_info['team_details']} | 📌 **Progress:** {day_label}")

            if not existing_logs.empty:
                last_log = existing_logs.iloc[-1]
                prev_planned = last_log.get('next_day_planned_tasks', '')
                if prev_planned and str(prev_planned).strip():
                    with st.expander(f"📌 Tasks Planned Yesterday ({last_log.get('day_number', 'Previous Day')})", expanded=True):
                        st.info(prev_planned)

            st.divider()
            st.subheader(f"Task Entry Form for ID: `{selected_id}` ({day_label})")
            
            col1, col2 = st.columns(2)
            with col1:
                product_worked_on = st.selectbox("Choose the product worked on", product_options)
            with col2:
                submitted_by = st.text_input("Technician Name", value=inst_info['team_details'].split('+')[0].strip())

            st.markdown("#### Today's Completed Tasks")

            tasks_list = []
            for i in range(st.session_state.task_count):
                task_val = st.text_input(f"Task {i + 1}", key=f"today_task_{i}", placeholder="Write tasks only...")
                if task_val.strip():
                    tasks_list.append(f"{i + 1}. {task_val.strip()}")

            if st.button("➕ Add Another Completed Task Field"):
                st.session_state.task_count += 1
                st.rerun()

            st.divider()
            st.markdown("#### Planned Tasks for Next Day")

            next_tasks_list = []
            for j in range(st.session_state.next_task_count):
                next_val = st.text_input(f"Next Day Task {j + 1}", key=f"next_task_{j}", placeholder="Write planned tasks only...")
                if next_val.strip():
                    next_tasks_list.append(f"{j + 1}. {next_val.strip()}")

            if st.button("➕ Add Another Next Day Task Field"):
                st.session_state.next_task_count += 1
                st.rerun()

            st.divider()

            if st.button("Submit Daily Task Log", type="primary"):
                if not tasks_list:
                    st.error("Please enter at least one completed task description.")
                elif not submitted_by.strip():
                    st.error("Please enter Technician Name.")
                else:
                    combined_completed_tasks = "\n".join(tasks_list)
                    combined_next_tasks = "\n".join(next_tasks_list) if next_tasks_list else "None planned"
                    log_id = generate_log_id()
                    
                    log_row = [
                        log_id, 
                        selected_id, 
                        day_label,
                        auto_log_time, 
                        str(log_date), 
                        product_worked_on, 
                        combined_completed_tasks, 
                        combined_next_tasks, 
                        submitted_by
                    ]
                    append_to_sheet("Daily_Logs", log_row)
                    
                    st.success(f"Data successfully inserted for **Installation ID: `{selected_id}`** (Visit Log Key: `{log_id}`)!")
                    st.session_state.task_count = 5
                    st.session_state.next_task_count = 3

# 3. EDIT TASK LOG (BY PRIMARY KEY)
elif menu == "Edit Task Log (By Primary Key)":
    st.header("✏️ Edit Task Log Entry by Log ID")

    df_logs = read_sheet("Daily_Logs")

    if df_logs.empty:
        st.warning("No task logs found in the database.")
    else:
        col_k1, col_k2 = st.columns(2)
        with col_k1:
            log_ids = df_logs["log_id"].tolist()
            selected_log_id = st.selectbox("Select Visit Log Key (LOG-YYYY-XXXXX):", log_ids)
            
        log_data = df_logs[df_logs["log_id"] == selected_log_id].iloc[0]

        with col_k2:
            st.info(f"📍 **Target Installation ID:** `{log_data['installation_id']}` | **Day:** {log_data.get('day_number', 'N/A')} | **Date:** {log_data['logged_date']}")

        st.divider()

        with st.form("edit_log_form"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                updated_product = st.text_input("Product Worked On", value=log_data['product_worked_on'])
            with col_e2:
                updated_tech = st.text_input("Technician Name", value=log_data['submitted_by'])

            st.markdown("#### 1. Edit Completed Tasks")
            updated_completed = st.text_area("Completed Tasks", value=log_data['tasks_completed'], height=150)
            
            st.markdown("#### 2. Edit Planned Next Day Tasks")
            updated_next = st.text_area("Planned Next Day Tasks", value=log_data.get('next_day_planned_tasks', ''), height=150)

            save_edit = st.form_submit_button("Update Log Entry in Google Sheets")

            if save_edit:
                updates = {
                    "product_worked_on": updated_product,
                    "submitted_by": updated_tech,
                    "tasks_completed": updated_completed,
                    "next_day_planned_tasks": updated_next,
                    "logged_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " (Edited)"
                }
                
                success = update_sheet_row("Daily_Logs", "log_id", selected_log_id, updates)
                if success:
                    st.success(f"Log Key `{selected_log_id}` updated for Installation ID **`{log_data['installation_id']}`**!")
                else:
                    st.error("Failed to update Google Sheet entry. Verify column headers.")

# 4. VIEW LOGS & UPDATE STATUS
elif menu == "View Logs & Update Status":
    st.header("🔍 View Logs & Update Installation Status")

    df_inst = read_sheet("Installations")
    
    if df_inst.empty:
        st.warning("No Installation IDs recorded.")
    else:
        inst_map = {f"{row['installation_id']} | {row['site_address'][:25]}...": row['installation_id'] for _, row in df_inst.iterrows()}
        selected_label = st.selectbox("Select Installation Project ID:", list(inst_map.keys()))
        selected_id = inst_map[selected_label]

        site_info = df_inst[df_inst["installation_id"] == selected_id].iloc[0]
        
        st.success(f"### Target Installation Project ID: `{site_info['installation_id']}`")
        st.write(f"**Site Address:** {site_info['site_address']} | **Team Details:** {site_info['team_details']}")
        
        st.divider()

        st.subheader("📌 Update Overall Status")
        col_status, col_btn = st.columns([2, 1])
        
        current_status = site_info['status'] if site_info['status'] in STATUS_OPTIONS else "In Progress"
        
        with col_status:
            new_status = st.selectbox("Change Overall Status:", STATUS_OPTIONS, index=STATUS_OPTIONS.index(current_status))
            
        with col_btn:
            st.write(" ")
            st.write(" ")
            if st.button("Update Status", type="primary"):
                updated_inst = update_sheet_row("Installations", "installation_id", selected_id, {"status": new_status})
                if updated_inst:
                    st.success(f"Status for Installation Project `{selected_id}` updated to **{new_status}**!")
                    st.rerun()
                else:
                    st.error("Could not update status in Google Sheets.")

        st.divider()
        st.subheader("📦 Order Specifications")
        
        df_items = read_sheet("Order_Items")
        site_items = df_items[df_items["installation_id"] == selected_id]
        if not site_items.empty:
            st.table(site_items[["category", "sub_category", "dimensions", "quantity"]])
        else:
            st.info("No order items recorded for this installation ID.")

        st.divider()
        st.subheader("📅 Activity Timeline")
        
        df_logs = read_sheet("Daily_Logs")
        site_logs = df_logs[df_logs["installation_id"] == selected_id]

        if site_logs.empty:
            st.info("No activity logs recorded for this Installation ID yet.")
        else:
            for _, row in site_logs.iterrows():
                with st.expander(f"📅 **{row.get('day_number', 'Day Log')} - Date: {row['logged_date']}**", expanded=True):
                    st.markdown(f"""
                    * **Visit Log ID:** `{row['log_id']}`
                    * **Timestamp:** `{str(row['logged_timestamp']).split(' ')[-1]}`
                    * **Product Worked On:** {row['product_worked_on']}
                    * **Technician:** {row['submitted_by']}
                    
                    **Completed Tasks:**
                    ```
                    {row['tasks_completed']}
                    ```
                    
                    **Planned Tasks for Next Day:**
                    ```
                    {row.get('next_day_planned_tasks', 'None recorded')}
                    ```
                    """)

# 5. MASTER DATABASE
elif menu == "Master Database":
    st.header("Master Database View (Google Sheets)")
    
    st.subheader("1. All Installations")
    st.dataframe(read_sheet("Installations"), use_container_width=True)
    
    st.subheader("2. All Order Items")
    st.dataframe(read_sheet("Order_Items"), use_container_width=True)
    
    st.subheader("3. All Log Entries")
    st.dataframe(read_sheet("Daily_Logs"), use_container_width=True)
