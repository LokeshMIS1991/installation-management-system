import streamlit as st
from core.auth import render_login_form
from core.styles import COLOR_ACCENT, COLOR_PRIMARY, apply_custom_styles
from utils.helpers import LOGO_PATH
from views import admin, salesperson, supervisor, worker
from views.components import render_restricted_work_input

# 1. Page Config & CSS Theme Setup
st.set_page_config(
    page_title="Sidharth Shutter & Automation - Portal",
    layout="wide",
    page_icon="⚙️",
    initial_sidebar_state="auto",
)
apply_custom_styles()

# 2. Authentication Route
if (
    "authenticated_user" not in st.session_state
    or not st.session_state.authenticated_user
):
    render_login_form()
    st.stop()

# 3. Active Session Context
user = st.session_state.authenticated_user
user_name = user.get("name", "User")
user_role = user.get("role", "Worker")
user_designation = user.get("designation", user_role)
user_id = user.get("worker_id", "N/A")
user_base_location = user.get("base_location", "Jaipur")

# 4. Sidebar Branding & Context
if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), use_container_width=True)
else:
    st.sidebar.markdown(
        f"""
        <div style="text-align: center; padding: 12px; background-color: {COLOR_PRIMARY}; color: white; border-radius: 8px; margin-bottom: 10px;">
            <h2 style="margin:0; font-size: 21px; color: white !important;">SIDHARTH</h2>
            <p style="margin:0; font-size: 11px; letter-spacing: 1.5px; color: {COLOR_ACCENT}; font-weight: bold;">SHUTTER & AUTOMATION</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

st.sidebar.markdown(
    f"**Active User:** {user_name} (`{user_id}`)  \n**Designation:** {user_designation}  \n**Role:** {user_role}  \n**Base Station:** {user_base_location}"
)
st.sidebar.divider()

# 5. Dynamic Navigation Options
if user_role == "Admin":
    menu_options = [
        "Admin Analytics Dashboard",
        "Sales Analytics Report",
        "User Management",
        "Master Database",
    ]
elif user_role == "Salesperson":
    menu_options = [
        "My Sales Dashboard",
        "📝 Log Visit & Order Deal",
        "🔍 Track Site Progress",
        "My Profile & Settings",
    ]
elif user_role == "Supervisor":
    menu_options = [
        "🔔 New Installation Requests",
        "New Installation Order",
        "Log Daily Tasks",
        "View Logs & Update Status",
        "Active Tasks Dashboard",
        "Team Head Dashboard",
        "Master Database",
    ]
else:  # Worker (Helper, Installer, Manager)
    menu_options = [
        "My Work Dashboard",
        "Log Daily Tasks",
        "My Work History & Performance",
        "My Profile & Settings",
    ]

menu = st.sidebar.radio("Navigation Menu", menu_options)
st.sidebar.divider()

if st.sidebar.button("🚪 LOG OUT", use_container_width=True):
    st.session_state.authenticated_user = None
    st.rerun()

# 6. Page Routing
if menu == "Admin Analytics Dashboard":
    admin.render_analytics()
elif menu == "Sales Analytics Report":
    admin.render_sales_report()
elif menu == "User Management":
    admin.render_user_management()
elif menu == "Master Database":
    admin.render_master_db()
elif menu == "My Sales Dashboard":
    salesperson.render_dashboard(user)
elif menu == "📝 Log Visit & Order Deal":
    salesperson.render_log_deal(user)
elif menu == "🔍 Track Site Progress":
    salesperson.render_track_progress(user)
elif menu == "🔔 New Installation Requests":
    supervisor.render_new_requests()
elif menu == "New Installation Order":
    supervisor.render_new_order()
elif menu == "View Logs & Update Status":
    supervisor.render_view_logs_and_update_status()
elif menu == "Team Head Dashboard":
    supervisor.render_team_head_dashboard(user)
elif menu == "Active Tasks Dashboard":
    supervisor.render_active_tasks()
elif menu == "My Work Dashboard":
    worker.render_dashboard(user)
elif menu == "Log Daily Tasks":
    render_restricted_work_input(target_worker_name=user_name, is_crew_log=False)
elif menu == "My Work History & Performance":
    worker.render_performance_history(user)
elif menu == "My Profile & Settings":
    worker.render_profile(user)
