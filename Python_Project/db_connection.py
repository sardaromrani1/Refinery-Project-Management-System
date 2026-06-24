import pyodbc

# ── Change these to match your SQL Server instance ──────────────────────────
SERVER   = "DESKTOP-M079PML\SQLEXPRESS01,14330"          # e.g. "DESKTOP-ABC\\SQLEXPRESS"
DATABASE = "Refinery_Project"
# Uses Windows Authentication; swap to SQL auth if needed (see comment below)
# ─────────────────────────────────────────────────────────────────────────────

def get_connection():
    """Return a live pyodbc Connection, or raise on failure."""
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"          # Windows Auth
        # Uncomment below for SQL Server Auth and remove Trusted_Connection line:
        # f"UID=your_username;PWD=your_password;"
    )
    return pyodbc.connect(conn_str)
