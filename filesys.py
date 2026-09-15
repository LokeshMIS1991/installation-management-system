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

# Helper function to append rows
def append_to_sheet(sheet_name, row_data):
    sheet = get_worksheet(sheet_name)
    sheet.append_row(row_data)

# Helper function to read worksheet data safely
def read_sheet(sheet_name):
    try:
        sheet = get_worksheet(sheet_name)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
    except Exception:
        df = pd.DataFrame()
    
    # Safe Fallbacks if Google Sheet tab is empty or missing headers
    if df.empty or "installation_id" not in df.columns:
        if sheet_name == "Installations":
            return pd.DataFrame(columns=[
                "installation_id", "city_prefix", "site_address", "team_details", 
                "order_created_date", "site_clearance_date", "target_ho_date", "status"
            ])
        elif sheet_name == "Order_Items":
            return pd.DataFrame(columns=[
                "installation_id", "category", "sub_category", "dimensions", "quantity"
            ])
        elif sheet_name == "Daily_Logs":
            return pd.DataFrame(columns=[
                "log_id", "installation_id", "day_number", "logged_timestamp", 
                "logged_date", "product_worked_on", "tasks_completed", 
                "next_day_planned_tasks", "submitted_by"
            ])
    return df

# Helper function to update record by Primary Key
def update_sheet_row(sheet_name, key_column_name, key_value, updated_row_dict):
    sheet = get_worksheet(sheet_name)
    records = sheet.get_all_records()
    headers = sheet.row_values(1)
    
    for idx, row in enumerate(records, start=2):
        if str(row.get(key_column_name)) == str(key_value):
            for col_name, val in updated_row_dict.items():
                if col_name in headers:
                    col_idx = headers.index(col_name) + 1
                    sheet.update_cell(idx, col_idx, str(val))
            return True
    return False

# Helper functions for structured IDs
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
    st.session_state.next_task_count = 5

# 1. NEW INSTALLATION ORDER
if menu == "New Installation Order":
    st.header("Create New Installation Order")

    if "temp_inst_id" not in st.session_state:
        st.session_state.temp_inst_id = generate_project_id()

    # Light Blue Banner
    st.markdown(f"""
        <div style="background-color: #EBF3FE; padding: 16px 20px; border-radius: 8px; margin-bottom: 20px;">
            <span style="color: #0F4C81; font-weight: 700; font-size: 16px;">Automated Visit ID:</span>
            <span style="color: #336699; font-weight: 600; font-size: 16px; margin-left: 8px; font-family: monospace;">{st.session_state.temp_inst_id}</span>
        </div>
    """, unsafe_allow_html=True)

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

# 2. LOG DAILY TASKS
elif menu == "Log Daily Tasks":
    st.header("📋 Log Daily Tasks")

    df_inst = read_sheet("Installations")
    df_logs = read_sheet("Daily_Logs")

    st.subheader("1. Search Options")
    search_tab1, search_tab2 = st.tabs(["🔎 Search by Primary Key", "📅 Search by Date"])

    selected_id = None

    with search_tab1:
        col_pk_input, col_pk_select = st.columns(2)
        with col_pk_input:
            pk_query = st.text_input("Enter Primary Key directly:", placeholder="e.g., INST-2026-XXXXX").strip()
        
        with col_pk_select:
            all_ids = df_inst["installation_id"].tolist() if not df_inst.empty else []
            id_options = [f"{row['installation_id']} | {row['site_address'][:25]}..." for _, row in df_inst.iterrows()] if not df_inst.empty else ["No existing IDs found"]
            selected_dropdown = st.selectbox("Or choose existing Installation Key:", id_options)

        if pk_query:
            if pk_query in all_ids:
                selected_id = pk_query
            else:
                matched = [i for i in all_ids if pk_query.lower() in i.lower()]
                if matched:
                    selected_id = matched[0]
                else:
                    st.warning(f"No match found for primary key: '{pk_query}'. Using dropdown selection.")
        
        if not selected_id and not df_inst.empty:
            selected_id = selected_dropdown.split(" | ")[0]

    with search_tab2:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            filter_date = st.date_input("Filter Orders by Created Date:", value=datetime.now())
        
        with col_d2:
            if not df_inst.empty and "order_created_date" in df_inst.columns:
                filtered_df = df_inst[df_inst["order_created_date"].astype(str) == str(filter_date)]
                if not filtered_df.empty:
                    date_options = [f"{row['installation_id']} | {row['site_address'][:25]}..." for _, row in filtered_df.iterrows()]
                    date_selected_dropdown = st.selectbox("Select Project matching date:", date_options)
                    selected_id = date_selected_dropdown.split(" | ")[0]
                else:
                    st.info(f"No installation orders found created on {filter_date}.")
            else:
                st.info("No installation records available to filter by date.")

    st.divider()

    if not selected_id or df_inst.empty or selected_id not in df_inst["installation_id"].values:
        st.info("Please enter or select a valid Primary Key above to load and record task logs.")
    else:
        inst_info = df_inst[df_inst["installation_id"] == selected_id].iloc[0]

        existing_logs = df_logs[df_logs["installation_id"] == selected_id] if not df_logs.empty else pd.DataFrame()
        day_number_int = len(existing_logs) + 1
        day_label = f"Day {day_number_int}"

        df_items = read_sheet("Order_Items")
        site_items = df_items[df_items["installation_id"] == selected_id] if not df_items.empty else pd.DataFrame()
        product_options = [f"{row['sub_category']} ({row['dimensions']})" for _, row in site_items.iterrows()] if not site_items.empty else []
        product_options.append("General Site Work / Preparation")

        # Light Blue Banner displaying active target key
        st.markdown(f"""
            <div style="background-color: #EBF3FE; padding: 16px 20px; border-radius: 8px; margin-bottom: 20px;">
                <span style="color: #0F4C81; font-weight: 700; font-size: 16px;">Automated Visit ID:</span>
                <span style="color: #336699; font-weight: 600; font-size: 16px; margin-left: 8px; font-family: monospace;">{selected_id}</span>
                <span style="color: #555; font-size: 14px; margin-left: 15px;">({day_label} | Team: {inst_info['team_details']})</span>
            </div>
        """, unsafe_allow_html=True)

        if not existing_logs.empty:
            last_log = existing_logs.iloc[-1]
            prev_planned = last_log.get('next_day_planned_tasks', '')
            if prev_planned and str(prev_planned).strip():
                with st.expander(f"📌 Tasks Planned Yesterday ({last_log.get('day_number', 'Previous Day')})", expanded=True):
                    st.info(prev_planned)

        log_date = st.date_input("Select Log Date", value=datetime.now(), min_value=datetime.now() - timedelta(days=14))
        auto_log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            product_worked_on = st.selectbox("Choose the product worked on", product_options)
        with col_p2:
            submitted_by = st.text_input("Technician Name *", value=inst_info['team_details'].split('+')[0].strip())

        st.divider()
        st.markdown("### Today's Completed Tasks (5 Default Tasks)")
        
        completed_tasks = []
        for i in range(st.session_state.task_count):
            task_input = st.text_input(f"Task {i + 1}", key=f"today_task_{i}", placeholder="Describe task performed...")
            if task_input.strip():
                completed_tasks.append(f"{i + 1}. {task_input.strip()}")

        if st.button("➕ Add Another Task Field"):
            st.session_state.task_count += 1
            st.rerun()

        st.divider()
        st.markdown("### Planned Tasks for Next Day")

        next_tasks = []
        for j in range(st.session_state.next_task_count):
            next_input = st.text_input(f"Next Day Task {j + 1}", key=f"next_task_{j}", placeholder="Describe planned task...")
            if next_input.strip():
                next_tasks.append(f"{j + 1}. {next_input.strip()}")

        if st.button("➕ Add Another Next Day Task Field"):
            st.session_state.next_task_count += 1
            st.rerun()

        st.divider()

        if st.button("Submit Daily Task Log", type="primary"):
            if not completed_tasks:
                st.error("Please enter at least one completed task description.")
            elif not submitted_by.strip():
                st.error("Please enter Technician Name.")
            else:
                combined_completed_tasks = "\n".join(completed_tasks)
                combined_next_tasks = "\n".join(next_tasks) if next_tasks else "None planned"
                log_id = generate_log_id()
                
                log_row = [
                    log_id, selected_id, day_label, auto_log_time, str(log_date), 
                    product_worked_on, combined_completed_tasks, combined_next_tasks, submitted_by
                ]
                append_to_sheet("Daily_Logs", log_row)
                
                st.success(f"Tasks logged successfully for Installation Primary Key **`{selected_id}`** (Visit Log Key: `{log_id}`)!")
                st.session_state.task_count = 5
                st.session_state.next_task_count = 5

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
        site_items = df_items[df_items["installation_id"] == selected_id] if not df_items.empty else pd.DataFrame()
        if not site_items.empty:
            st.table(site_items[["category", "sub_category", "dimensions", "quantity"]])
        else:
            st.info("No order items recorded for this installation ID.")

        st.divider()
        st.subheader("📅 Activity Timeline")
        
        df_logs = read_sheet("Daily_Logs")
        site_logs = df_logs[df_logs["installation_id"] == selected_id] if not df_logs.empty else pd.DataFrame()

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
