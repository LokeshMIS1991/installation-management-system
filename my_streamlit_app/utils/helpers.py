import re
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = BASE_DIR / "Company Logo.jpeg"

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"
WORKER_DESIGNATIONS = ["Installer", "Helper", "Manager"]


def validate_email(email_str: str) -> bool:
    """Validates structure of email address."""
    if not email_str:
        return False
    return bool(re.match(EMAIL_REGEX, email_str.strip()))


def generate_work_id(role: str, df_workers: pd.DataFrame) -> str:
    """Auto-generates dynamic Work IDs like ADM01, SPV001, W001, SP001."""
    role_prefix_map = {
        "Admin": "ADM",
        "Supervisor": "SPV",
        "Worker": "W",
        "Salesperson": "SP",
    }

    prefix = role_prefix_map.get(role, "EMP")

    if df_workers.empty or "worker_id" not in df_workers.columns:
        return f"{prefix}01" if prefix == "ADM" else f"{prefix}001"

    existing_ids = df_workers["worker_id"].dropna().astype(str).str.strip()
    role_ids = [uid for uid in existing_ids if uid.startswith(prefix)]

    if not role_ids:
        return f"{prefix}01" if prefix == "ADM" else f"{prefix}001"

    numbers = []
    for uid in role_ids:
        num_part = uid[len(prefix) :]
        if num_part.isdigit():
            numbers.append(int(num_part))

    next_num = max(numbers) + 1 if numbers else 1
    padding = 2 if prefix == "ADM" else 3
    return f"{prefix}{next_num:0{padding}d}"


def format_worker_dropdown_options(df_workers: pd.DataFrame) -> list:
    """Formats worker options with designations for UI drop-downs."""
    if df_workers.empty or "name" not in df_workers.columns:
        return []

    options = []
    for _, row in df_workers.iterrows():
        name = str(row.get("name", "")).strip()
        role = str(row.get("role", "")).strip()
        desig = str(row.get("designation", "")).strip()

        if not name or role in ["Admin", "Salesperson"]:
            continue

        if role == "Worker" and desig:
            options.append(f"{name} ({desig})")
        else:
            options.append(name)

    return sorted(list(set(options)))
