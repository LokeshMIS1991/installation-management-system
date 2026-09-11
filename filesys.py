import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Database setup with complete migration logic
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_NAME = "installations.db"

# Database setup with automatic schema migration checks
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Installations Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS installations (
            installation_id TEXT PRIMARY KEY,
            city_code TEXT,
            site_address TEXT,
            team_details TEXT,
            created_date TEXT,
            site_clearance_date TEXT,
            target_ho_date TEXT,
            status TEXT
        )
    ''')
    cursor.execute("PRAGMA table_info(installations)")
    inst_cols = [col[1] for col in cursor.fetchall()]
    if "city_code" not in inst_cols:
        cursor.execute("ALTER TABLE installations ADD COLUMN city_code TEXT DEFAULT 'GEN'")
    if "created_date" not in inst_cols:
        cursor.execute("ALTER TABLE installations ADD COLUMN created_date TEXT DEFAULT ''")

    # 2. Order Items Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            installation_id TEXT,
            category TEXT,
            sub_category TEXT,
            dimensions TEXT,
            quantity INTEGER,
            FOREIGN KEY (installation_id) REFERENCES installations (installation_id)
        )
    ''')
    cursor.execute("PRAGMA table_info(order_items)")
    item_cols = [col[1] for col in cursor.fetchall()]
    if "category" not in item_cols:
        cursor.execute("ALTER TABLE order_items ADD COLUMN category TEXT DEFAULT 'General'")
    if "sub_category" not in item_cols:
        cursor.execute("ALTER TABLE order_items ADD COLUMN sub_category TEXT DEFAULT 'General'")

    # 3. Daily Logs Table (Fixes missing logged_timestamp and logged_date)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_logs (
            log_id TEXT PRIMARY KEY,
            installation_id TEXT,
            logged_timestamp TEXT,
            logged_date TEXT,
            product_worked_on TEXT,
            work_description TEXT,
            submitted_by TEXT,
            FOREIGN KEY (installation_id) REFERENCES installations (installation_id)
        )
    ''')
    cursor.execute("PRAGMA table_info(daily_logs)")
    log_cols = [col[1] for col in cursor.fetchall()]
    
    if "logged_timestamp" not in log_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN logged_timestamp TEXT DEFAULT ''")
    if "logged_date" not in log_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN logged_date TEXT DEFAULT ''")
    if "product_worked_on" not in log_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN product_worked_on TEXT DEFAULT ''")
    if "work_description" not in log_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN work_description TEXT DEFAULT ''")
    if "submitted_by" not in log_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN submitted_by TEXT DEFAULT ''")

    conn.commit()
    conn.close()

init_db()
init_db()

PRODUCT_CATALOG = {
    "Rolling Shutters": [
        "Motorized Rolling Shutter",
        "Gear Rolling Shutter",
        "Manual Rolling Shutter"
    ],
    "Dock Leveler": [
        "Hydraulic Doclevller",
        "Hydraulic Dock Edge",
        "Manual Dock Edge"
    ],
    "Gates": [
        "Sliding Gate",
        "Telescopic Gate",
        "L-Folding Gate",
        "Swing Gate",
        "Retractable Gate"
    ],
    "Doors": [
        "High Speed Door",
        "Fire Door",
        "HMPS Door",
        "GPD Door",
        "Overhead Sectional Door"
    ],
    "Boom Barrier": [
        "Automatic Traffic Barrier",
        "Heavy-Duty Traffic Barrier"
    ],
    "Dock Shelter": [
        "Retractable Dock Shelter",
        "Inflatable Dock Shelter"
    ],
    "Dock Bumper": [
        "Heavy Rubber Bumper",
        "Moulded Bumper"
    ],
    "Other": ["Other"]
}

st.set_page_config(page_title="Installation Management System", layout="wide")
st.title("🛠️ Installation Management System")

# Clean Navigation Title
menu = st.sidebar.radio("Navigation", [
    "New Installation Order", 
    "Log Daily Tasks",
    "View Logs (By Installation ID)", 
    "Master Database"
])

def run_query(query, params=(), commit=False):
    conn = sqlite3.connect("installations.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    if commit:
        conn.commit()
        data = None
    else:
        data = cursor.fetchall()
    conn.close()
    return data

# Initialize session state for task count
if "task_count" not in st.session_state:
    st.session_state.task_count = 5

# 1. NEW INSTALLATION ORDER
if menu == "New Installation Order":
    st.header("Create New Installation Order")

    col1, col2 = st.columns(2)
    with col1:
        city_prefix = st.text_input("City/Location Code (e.g., MUM, DEL, BHW)", "MUM").upper()
        site_address = st.text_area("Site Address", placeholder="Full installation site address...")
        
        order_created_date = st.date_input(
            "Order Created Date", 
            min_value=datetime.now(),
            help="Past dates cannot be selected."
        )

    with col2:
        team_details = st.text_input("Team's Details", placeholder="e.g., Rajeer + 2 Helpers")
        site_clearance = st.date_input("Site Clearance Date", min_value=datetime.now())
        target_ho_date = st.date_input("Target Handover Date", min_value=datetime.now(), value=datetime.now() + timedelta(days=15))

    st.divider()
    st.subheader("Choose the product")

    col_cat, col_sub = st.columns(2)
    
    with col_cat:
        selected_category = st.selectbox("Select Main Category", list(PRODUCT_CATALOG.keys()))
        
    with col_sub:
        sub_category_options = PRODUCT_CATALOG[selected_category]
        selected_sub_category = st.selectbox("Select Sub-Category", sub_category_options)

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
            if not site_address.strip():
                st.error("Please enter a valid Site Address.")
            else:
                timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
                inst_id = f"{city_prefix}-{timestamp_str}"
                
                run_query('''
                    INSERT INTO installations 
                    (installation_id, city_code, site_address, team_details, created_date, site_clearance_date, target_ho_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (inst_id, city_prefix, site_address, team_details, str(order_created_date), str(site_clearance), str(target_ho_date), "In Progress"), commit=True)
                
                run_query('''
                    INSERT INTO order_items (installation_id, category, sub_category, dimensions, quantity)
                    VALUES (?, ?, ?, ?, ?)
                ''', (inst_id, selected_category, final_product_name, dimensions, int(quantity)), commit=True)
                
                st.success(f"Installation Order Created Successfully! Generated ID: **{inst_id}**")

# 2. LOG DAILY TASKS (UPDATED WITH MULTI-TASK OPTIONS)
elif menu == "Log Daily Tasks":
    st.header("📋 Log Daily Tasks")
    
    log_date = st.date_input("Select Log Date", min_value=datetime.now())
    auto_log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    records = run_query("SELECT installation_id, site_address FROM installations WHERE status = 'In Progress'")
    
    if not records:
        st.warning("No active Installation IDs found. Please create a new order first.")
    else:
        inst_ids = [r[0] for r in records]
        selected_id = st.selectbox("Select Installation ID", inst_ids)

        items = run_query("SELECT sub_category, dimensions FROM order_items WHERE installation_id = ?", (selected_id,))
        product_options = [f"{item[0]} ({item[1]})" for item in items]
        product_options.append("General Site Work / Preparation")

        st.divider()

        st.subheader(f"Task Entry for Installation ID: `{selected_id}`")
        
        col1, col2 = st.columns(2)
        with col1:
            product_worked_on = st.selectbox("Choose the product", product_options)
        with col2:
            submitted_by = st.text_input("Technician Name", placeholder="e.g., Rajeer")

        st.markdown("#### Detailed Work Completed Today")
        st.write("Enter sub-tasks or activities completed:")

        # Dynamic task input list
        tasks_list = []
        for i in range(st.session_state.task_count):
            task_val = st.text_input(f"Task / Sub-Task {i + 1}", key=f"task_field_{i}", placeholder=f"Enter task {i + 1} description...")
            if task_val.strip():
                tasks_list.append(f"{i + 1}. {task_val.strip()}")

        # Button to increase task inputs
        if st.button("➕ Add Another Task"):
            st.session_state.task_count += 1
            st.rerun()

        st.divider()

        if st.button("Submit Daily Task Log", type="primary"):
            if not tasks_list:
                st.error("Please enter at least one task or sub-task description.")
            elif not submitted_by.strip():
                st.error("Please enter the Technician Name.")
            else:
                combined_work_desc = "\n".join(tasks_list)
                log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                run_query('''
                    INSERT INTO daily_logs 
                    (log_id, installation_id, logged_timestamp, logged_date, product_worked_on, work_description, submitted_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (log_id, selected_id, auto_log_time, str(log_date), product_worked_on, combined_work_desc, submitted_by), commit=True)
                
                st.success(f"Tasks logged successfully for **{selected_id}** on **{log_date}**!")
                # Reset task input count after submission
                st.session_state.task_count = 5

# 3. VIEW LOGS BY INSTALLATION ID
elif menu == "View Logs (By Installation ID)":
    st.header("🔍 View Logs by Installation ID")

    records = run_query("SELECT installation_id FROM installations")
    
    if not records:
        st.warning("No Installation IDs recorded in database.")
    else:
        inst_ids = [r[0] for r in records]
        selected_id = st.selectbox("Select Installation ID to View Progress", inst_ids)

        site_info = run_query("SELECT * FROM installations WHERE installation_id = ?", (selected_id,))[0]
        
        st.markdown(f"### Details for Installation ID: `{site_info[0]}`")
        st.write(f"**Site Address:** {site_info[1]} | **Team Details:** {site_info[2]}")
        
        st.divider()
        
        st.subheader("📦 Order Specifications")
        items = run_query("SELECT category, sub_category, dimensions, quantity FROM order_items WHERE installation_id = ?", (selected_id,))
        df_items = pd.DataFrame(items, columns=["Category", "Sub-Category", "Dimensions", "Quantity"])
        st.table(df_items)

        st.divider()

        st.subheader("📅 Day-Wise Activity Logs")
        logs = run_query('''
            SELECT logged_date, logged_timestamp, product_worked_on, work_description, submitted_by 
            FROM daily_logs 
            WHERE installation_id = ? 
            ORDER BY logged_timestamp DESC
        ''', (selected_id,))

        if not logs:
            st.info("No logs recorded for this Installation ID yet.")
        else:
            df_logs = pd.DataFrame(logs, columns=["Date", "Timestamp", "Product Worked On", "Tasks Completed", "Submitted By"])
            
            for day in df_logs["Date"].unique():
                with st.expander(f"📅 **Date: {day}**", expanded=True):
                    day_data = df_logs[df_logs["Date"] == day]
                    for _, row in day_data.iterrows():
                        st.markdown(f"""
                        * **Time:** `{row['Timestamp'].split(' ')[1]}`
                        * **Product/Area:** {row['Product Worked On']}
                        * **Technician:** {row['Submitted By']}
                        * **Tasks Completed:**
                        ```
                        {row['Tasks Completed']}
                        ```
                        """)
                        st.divider()

# 4. MASTER DATABASE
elif menu == "Master Database":
    st.header("Master Database View")
    conn = sqlite3.connect("installations.db")
    
    st.subheader("1. All Installation Header Records")
    st.dataframe(pd.read_sql_query("SELECT * FROM installations", conn), use_container_width=True)
    
    st.subheader("2. All Order Product Items")
    st.dataframe(pd.read_sql_query("SELECT * FROM order_items", conn), use_container_width=True)
    
    st.subheader("3. All Log Entries")
    st.dataframe(pd.read_sql_query("SELECT * FROM daily_logs", conn), use_container_width=True)
    
    conn.close()