import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

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

# Helper function to update a specific record in Google Sheets by key column
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
    "Edit / Update Daily Tasks",
    "View Logs & Update Status", 
    "Master Database"
])

if "task_count" not in st.session_state:
    st.session_state.task_count = 5

# 1. NEW INSTALLATION ORDER
if menu == "New Installation Order":
    st.header("Create New Installation Order")

    col1, col2 = st.columns(2)
    
    with col1:
        team_details = st.text_input("Team's Details", placeholder="e.g., Rajeer + 2 Helpers")
        city_name = st.text_input("City Name", "Mumbai").strip()
        site_address = st.text_area("Site Address", placeholder="Full installation site address...")
        city_prefix = city_name[:3].upper() if city_name else "GEN"

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
                timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
                inst_id = f"{city_prefix}-{timestamp_str}"
                
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
                
                st.success(f"Saved to Google Sheets! Generated ID: **{inst_id}**")

# 2. LOG DAILY TASKS
elif menu == "Log Daily Tasks":
    st.header("📋 Log Daily Tasks")
    
    log_date = st.date_input("Select Log Date", value=datetime.now(), min_value=datetime.now() - timedelta(days=7))
    auto_log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df_inst = read_sheet("Installations")
    
    if df_inst.empty:
        st.warning("No active Installation IDs found. Please create a new order first.")
    else:
        active_inst = df_inst[df_inst["status"].isin(["In Progress", "Pending"])]
        if active_inst.empty:
            st.info("No installations currently 'In Progress' or 'Pending'.")
        else:
            inst_ids = active_inst["installation_id"].tolist()
            selected_id = st.selectbox("Select Installation ID", inst_ids)

            df_items = read_sheet("Order_Items")
            site_items = df_items[df_items["installation_id"] == selected_id]
            
            product_options = [f"{row['sub_category']} ({row['dimensions']})" for _, row in site_items.iterrows()]
            product_options.append("General Site Work / Preparation")

            st.divider()
            st.subheader(f"Task Entry for Installation ID: `{selected_id}`")
            
            col1, col2 = st.columns(2)
            with col1:
                product_worked_on = st.selectbox("Choose the product", product_options)
            with col2:
                submitted_by = st.text_input("Technician Name", placeholder="e.g., Rajeer")

            st.markdown("#### Detailed Work Completed Today / Planned Tasks")

            tasks_list = []
            for i in range(st.session_state.task_count):
                task_val = st.text_input(f"Task / Sub-Task {i + 1}", key=f"task_field_{i}", placeholder=f"Enter task {i + 1} description...")
                if task_val.strip():
                    tasks_list.append(f"{i + 1}. {task_val.strip()}")

            if st.button("➕ Add Another Task Field"):
                st.session_state.task_count += 1
                st.rerun()

            st.divider()

            if st.button("Submit Daily Task Log", type="primary"):
                if not tasks_list:
                    st.error("Please enter at least one task description.")
                elif not submitted_by.strip():
                    st.error("Please enter Technician Name.")
                else:
                    combined_work_desc = "\n".join(tasks_list)
                    log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    log_row = [log_id, selected_id, auto_log_time, str(log_date), product_worked_on, combined_work_desc, submitted_by]
                    append_to_sheet("Daily_Logs", log_row)
                    
                    st.success(f"Tasks logged to Google Sheets for **{selected_id}** (Log ID: `{log_id}`)!")
                    st.session_state.task_count = 5

# 3. EDIT / UPDATE DAILY TASKS (PRIMARY KEY BASED)
elif menu == "Edit / Update Daily Tasks":
    st.header("✏️ Edit / Update Daily Task Log by Primary Key")

    df_logs = read_sheet("Daily_Logs")

    if df_logs.empty:
        st.warning("No task logs found in the database.")
    else:
        st.subheader("Select Primary Key (Log ID)")
        
        log_ids = df_logs["log_id"].tolist()
        selected_log_id = st.selectbox("Select Log ID to Edit:", log_ids)

        log_data = df_logs[df_logs["log_id"] == selected_log_id].iloc[0]

        st.info(f"**Installation ID:** `{log_data['installation_id']}` | **Date Logged:** {log_data['logged_date']} | **Technician:** {log_data['submitted_by']}")

        with st.form("edit_log_form"):
            updated_product = st.text_input("Product Worked On", value=log_data['product_worked_on'])
            updated_tech = st.text_input("Technician Name", value=log_data['submitted_by'])
            updated_desc = st.text_area("Work Description / Next Day Tasks", value=log_data['work_description'], height=200)
            
            save_edit = st.form_submit_button("Update Log Entry")

            if save_edit:
                updates = {
                    "product_worked_on": updated_product,
                    "submitted_by": updated_tech,
                    "work_description": updated_desc,
                    "logged_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " (Edited)"
                }
                
                success = update_sheet_row("Daily_Logs", "log_id", selected_log_id, updates)
                if success:
                    st.success(f"Log ID `{selected_log_id}` updated successfully!")
                else:
                    st.error("Failed to update Google Sheet entry.")

# 4. VIEW LOGS & UPDATE STATUS
elif menu == "View Logs & Update Status":
    st.header("🔍 View Logs & Update Installation Status")

    df_inst = read_sheet("Installations")
    
    if df_inst.empty:
        st.warning("No Installation IDs recorded.")
    else:
        inst_ids = df_inst["installation_id"].tolist()
        selected_id = st.selectbox("Select Installation ID", inst_ids)

        site_info = df_inst[df_inst["installation_id"] == selected_id].iloc[0]
        
        st.markdown(f"### Installation ID: `{site_info['installation_id']}`")
        st.write(f"**Site Address:** {site_info['site_address']} | **Team Details:** {site_info['team_details']}")
        
        st.divider()

        # STATUS UPDATION SECTION
        st.subheader("📌 Update Installation Status")
        col_status, col_btn = st.columns([2, 1])
        
        current_status = site_info['status'] if site_info['status'] in STATUS_OPTIONS else "In Progress"
        
        with col_status:
            new_status = st.selectbox("Change Overall Status:", STATUS_OPTIONS, index=STATUS_OPTIONS.index(current_status))
            
        with col_btn:
            st.write(" ")
            st.write(" ")
            if st.button("Update Status", type="primary"):
                updated = update_sheet_row("Installations", "installation_id", selected_id, {"status": new_status})
                if updated:
                    st.success(f"Status updated to **{new_status}**!")
                    st.rerun()
                else:
                    st.error("Could not update status in Google Sheets.")

        st.divider()
        st.subheader("📦 Order Specifications")
        
        df_items = read_sheet("Order_Items")
        site_items = df_items[df_items["installation_id"] == selected_id]
        st.table(site_items[["category", "sub_category", "dimensions", "quantity"]])

        st.divider()
        st.subheader("📅 Activity Logs for this Installation")
        
        df_logs = read_sheet("Daily_Logs")
        site_logs = df_logs[df_logs["installation_id"] == selected_id]

        if site_logs.empty:
            st.info("No logs recorded for this Installation ID yet.")
        else:
            for day in site_logs["logged_date"].unique():
                with st.expander(f"📅 **Date: {day}**", expanded=True):
                    day_data = site_logs[site_logs["logged_date"] == day]
                    for _, row in day_data.iterrows():
                        st.markdown(f"""
                        * **Log Key ID:** `{row['log_id']}`
                        * **Time:** `{str(row['logged_timestamp']).split(' ')[-1]}`
                        * **Product/Area:** {row['product_worked_on']}
                        * **Technician:** {row['submitted_by']}
                        * **Tasks Completed / Notes:**
                        ```
                        {row['work_description']}
                        ```
                        """)
                        st.divider()

# 5. MASTER DATABASE
elif menu == "Master Database":
    st.header("Master Database View (Google Sheets)")
    
    st.subheader("1. All Installations")
    st.dataframe(read_sheet("Installations"), use_container_width=True)
    
    st.subheader("2. All Order Items")
    st.dataframe(read_sheet("Order_Items"), use_container_width=True)
    
    st.subheader("3. All Log Entries")
    st.dataframe(read_sheet("Daily_Logs"), use_container_width=True)
