import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        # Format the key properly to prevent base64 decoding errors
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        
    return gspread.authorize(creds)

# Helper function to append rows to a specific worksheet
def append_to_sheet(sheet_name, row_data):
    client = get_gspread_client()
    sheet = client.open_by_key("https://docs.google.com/spreadsheets/d/19rQC3aNtosjhSwyctKAk9ojUt0c8gyOPH-Q8trW5q5s/edit?gid=1303505636#gid=1303505636").worksheet(sheet_name)
    sheet.append_row(row_data)

# Helper function to read worksheet data into DataFrame
def read_sheet(sheet_name):
    client = get_gspread_client()
    sheet = client.open_by_key("https://docs.google.com/spreadsheets/d/19rQC3aNtosjhSwyctKAk9ojUt0c8gyOPH-Q8trW5q5s/edit?gid=1303505636#gid=1303505636").worksheet(sheet_name)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

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

st.set_page_config(page_title="Installation Management System", layout="wide")
st.title("🛠️ Installation Management System")

menu = st.sidebar.radio("Navigation", [
    "New Installation Order", 
    "Log Daily Tasks",
    "View Logs (By Installation ID)", 
    "Master Database"
])

if "task_count" not in st.session_state:
    st.session_state.task_count = 5

# 1. NEW INSTALLATION ORDER
if menu == "New Installation Order":
    st.header("Create New Installation Order")

    col1, col2 = st.columns(2)
    
    # Left Column: Details (Team -> City -> Address)
    with col1:
        team_details = st.text_input("Team's Details", placeholder="e.g., Rajeer + 2 Helpers")
        city_name = st.text_input("City Name", "Mumbai").strip()
        site_address = st.text_area("Site Address", placeholder="Full installation site address...")

        # Automatically extract first 3 letters of city as prefix code
        city_prefix = city_name[:3].upper() if city_name else "GEN"

    # Right Column: Dates sequentially one by one
    with col2:
        # Date limits: Allow picking up to 7 days in the past
        min_past_date = datetime.now() - timedelta(days=7)
        
        # 1. Order Created Date as Installation Date
        order_created_date = st.date_input(
            "Installation Date (Order Created Date)", 
            value=datetime.now(), 
            min_value=min_past_date
        )
        
        # 2. Site Clearance Date
        site_clearance = st.date_input(
            "Site Clearance Date", 
            value=datetime.now(), 
            min_value=min_past_date
        )
        
        # 3. Target Handover Date
        target_ho_date = st.date_input(
            "Target Handover Date", 
            value=datetime.now() + timedelta(days=15), 
            min_value=min_past_date
        )

    st.divider()

    # Changed label to "Select The product"
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
                
                # Append Header to 'Installations' Sheet
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
                
                # Append Item to 'Order_Items' Sheet
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
        inst_ids = df_inst[df_inst["status"] == "In Progress"]["installation_id"].tolist()
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

        st.markdown("#### Detailed Work Completed Today")

        tasks_list = []
        for i in range(st.session_state.task_count):
            task_val = st.text_input(f"Task / Sub-Task {i + 1}", key=f"task_field_{i}", placeholder=f"Enter task {i + 1} description...")
            if task_val.strip():
                tasks_list.append(f"{i + 1}. {task_val.strip()}")

        if st.button("➕ Add Another Task"):
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
                
                st.success(f"Tasks logged to Google Sheets for **{selected_id}**!")
                st.session_state.task_count = 5

# 3. VIEW LOGS BY INSTALLATION ID
elif menu == "View Logs (By Installation ID)":
    st.header("🔍 View Logs by Installation ID")

    df_inst = read_sheet("Installations")
    
    if df_inst.empty:
        st.warning("No Installation IDs recorded.")
    else:
        inst_ids = df_inst["installation_id"].tolist()
        selected_id = st.selectbox("Select Installation ID", inst_ids)

        site_info = df_inst[df_inst["installation_id"] == selected_id].iloc[0]
        
        st.markdown(f"### Details for Installation ID: `{site_info['installation_id']}`")
        st.write(f"**Site Address:** {site_info['site_address']} | **Team Details:** {site_info['team_details']}")
        
        st.divider()
        st.subheader("📦 Order Specifications")
        
        df_items = read_sheet("Order_Items")
        site_items = df_items[df_items["installation_id"] == selected_id]
        st.table(site_items[["category", "sub_category", "dimensions", "quantity"]])

        st.divider()
        st.subheader("📅 Day-Wise Activity Logs")
        
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
                        * **Time:** `{str(row['logged_timestamp']).split(' ')[-1]}`
                        * **Product/Area:** {row['product_worked_on']}
                        * **Technician:** {row['submitted_by']}
                        * **Tasks Completed:**
                        ```
                        {row['work_description']}
                        ```
                        """)
                        st.divider()

# 4. MASTER DATABASE
elif menu == "Master Database":
    st.header("Master Database View (Google Sheets)")
    
    st.subheader("1. All Installations")
    st.dataframe(read_sheet("Installations"), use_container_width=True)
    
    st.subheader("2. All Order Items")
    st.dataframe(read_sheet("Order_Items"), use_container_width=True)
    
    st.subheader("3. All Log Entries")
    st.dataframe(read_sheet("Daily_Logs"), use_container_width=True)
