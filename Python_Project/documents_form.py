"""
documents_form.py
──────────────────
Full CRUD Tkinter form for the DOCUMENTS table in Refinery_Project.

Table schema
────────────
CREATE TABLE DOCUMENTS(
    Document_ID VARCHAR(20) PRIMARY KEY,
    Activity_ID VARCHAR(20),
    Doc_Type VARCHAR(50),
    Title VARCHAR(150),
    Revision VARCHAR(10),
    Issue_Date DATE,
    Status VARCHAR(30),

    CONSTRAINT fk_documents_activity FOREIGN KEY (Activity_ID)
        REFERENCES WBS_ACTIVITIES (Activity_ID)
);

Notes
─────
• Document_ID is a user-entered VARCHAR PK (not IDENTITY), so the ID field
  is editable on Add but locked once a row is selected for Update/Delete.
• Activity_ID is a foreign key, presented as a read-only Combobox populated
  live from WBS_ACTIVITIES ("Activity_ID - Activity_Name"), optional (NULLable).
• Doc_Type and Status are presented as editable Comboboxes (you can pick a
  common value or type your own — there's no CHECK constraint on these
  columns in the schema).

Upgrades applied (matching projects_form.py pattern)
─────────────────────────────────────────────────────
8. Column-scoped search – user picks which column to search (Document ID,
   Activity ID, Doc Type, Title, Revision, Issue Date, Status) via a
   dropdown next to the search box.
9. Calendar date picker – Issue_Date field in the details panel uses a
   clickable calendar (tkcalendar.DateEntry) instead of free-typed text.
10. Date-range search – selecting "Issue Date" in the search dropdown swaps
    the keyword box for two calendar pickers ("From" / "To") so you can
    search a date range instead of a single keyword.

Requires the 'tkcalendar' package:
    pip install tkcalendar
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from tkcalendar import DateEntry

from db_connection import get_connection

DATE_FMT = "%Y-%m-%d"

DOC_TYPE_OPTIONS = ["Drawing", "Specification", "Datasheet", "Report",
                    "Procedure", "Certificate", "Permit Drawing", "Other"]
STATUS_OPTIONS = ["Draft", "Issued", "Under Review", "Approved",
                    "Superseded", "Void"]

# ── Search column options: display label -> actual SQL column name ──────────
SEARCH_COLUMNS = {
    "Document ID": "Document_ID",
    "Activity ID": "Activity_ID",
    "Doc Type": "Doc_Type",
    "Title": "Title",
    "Revision": "Revision",
    "Issue Date": "Issue_Date",
    "Status": "Status",
}

# Columns that use a date-range search (From / To calendars) instead of a keyword box
DATE_RANGE_COLUMNS = {"Issue Date": "Issue_Date"}


# ────────────────────────────────────────────────────────────────────────────
class DocumentsForm(tk.Frame):
    """
    Dark-themed frame with:
      • A data-entry panel (top) with a calendar date picker for Issue_Date
      • CRUD buttons
      • A searchable, sortable Treeview listing all documents
      • Column-scoped search: keyword search for text columns, date-range
        search (From/To calendars) for Issue Date
    """

    BG = "#1e2327"
    PANEL_BG = "#252b30"
    FG = "#e0e0e0"
    ACCENT = "#00b4d8"
    BTN_BG = "#00b4d8"
    BTN_FG = "#ffffff"
    ENTRY_BG = "#2e3540"
    SEL_BG = "#00b4d8"

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, bg=self.BG, *args, **kwargs)
        self._selected_id = None # Document_ID of the currently selected row
        self._activity_display_to_id = {} # "Activity_ID - Name" -> Activity_ID
        self._activity_id_to_display = {} # Activity_ID -> "Activity_ID - Name"
        self._build_ui()
        self._refresh_activity_options()
        self.load_documents()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            self, text="Documents Management", bg=self.BG, fg=self.ACCENT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 6))

        # ── Search bar (column selector + dynamic keyword/date-range area) ───
        search_frame = tk.Frame(self, bg=self.BG)
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 6))

        tk.Label(search_frame, text="Search by:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))

        self.search_column_var = tk.StringVar(value="Title")
        search_column_combo = ttk.Combobox(
            search_frame, textvariable=self.search_column_var,
            values=list(SEARCH_COLUMNS.keys()), state="readonly",
            font=("Segoe UI", 10), width=14
        )
        search_column_combo.pack(side=tk.LEFT, padx=(0, 10))
        # Rebuild the search input area (keyword box vs. date-range pickers)
        # whenever the chosen column changes, then re-run the search.
        search_column_combo.bind("<<ComboboxSelected>>", self._on_search_column_change)

        # Container that holds either the keyword Entry OR the From/To DateEntry pair.
        # Its contents are swapped dynamically by _on_search_column_change().
        self.search_input_frame = tk.Frame(search_frame, bg=self.BG)
        self.search_input_frame.pack(side=tk.LEFT)

        # Keyword search variable (used for text columns)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_documents())

        # Date-range widgets are created on demand in _build_keyword_search() /
        # _build_date_range_search(); references stored here once created.
        self._search_keyword_entry = None
        self._search_date_from = None
        self._search_date_to = None

        # Build the initial search input (default column is "Title" -> keyword box)
        self._build_keyword_search()

        # ── Entry panel ───────────────────────────────────────────────────────
        panel = tk.LabelFrame(
            self, text=" Document Details ", bg=self.PANEL_BG, fg=self.ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, relief=tk.GROOVE
        )
        panel.pack(fill=tk.X, padx=20, pady=6)

        self._entries = {}

        # column 0
        col0_fields = [
            ("Document_ID *", "entry"),
            ("Activity_ID", "fk_activity"),
            ("Doc_Type", "combo_doctype"),
        ]
        # column 1
        col1_fields = [
            ("Title *", "entry"),
            ("Revision", "entry"),
            ("Issue Date", "date"),
            ("Status", "combo_status"),
        ]

        for i, (lbl, kind) in enumerate(col0_fields):
            self._make_field(panel, lbl, kind, row=i, col=0)
        for i, (lbl, kind) in enumerate(col1_fields):
            self._make_field(panel, lbl, kind, row=i, col=2)

        # ── Button row ────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(pady=8)

        buttons = [
            ("➕ Add", self.add_document),
            ("✏️ Update", self.update_document),
            ("🗑️ Delete", self.delete_document),
            ("🔄 Refresh", self._refresh_all),
            ("✖ Clear", self.clear_fields),
        ]
        for text, cmd in buttons:
            tk.Button(
                btn_frame, text=text, command=cmd,
                bg=self.BTN_BG, fg=self.BTN_FG, activebackground="#0096c7",
                relief=tk.FLAT, font=("Segoe UI", 10, "bold"),
                width=11, cursor="hand2"
            ).pack(side=tk.LEFT, padx=5)

        # ── Treeview ──────────────────────────────────────────────────────────
        tree_frame = tk.Frame(self, bg=self.BG)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 16))

        cols = ("Document_ID", "Activity_ID", "Doc_Type", "Title",
                "Revision", "Issue_Date", "Status")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 selectmode="browse")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=self.PANEL_BG, foreground=self.FG,
                        rowheight=26, fieldbackground=self.PANEL_BG,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                        background=self.ACCENT, foreground="#ffffff",
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", self.SEL_BG)])

        col_widths = {"Document_ID": 100, "Activity_ID": 100, "Doc_Type": 110,
                      "Title": 220, "Revision": 70, "Issue_Date": 100, "Status": 110}
        for col in cols:
            self.tree.heading(col, text=col.replace("_", " "),
                              command=lambda c=col: self._sort_tree(c, False))
            self.tree.column(col, width=col_widths[col], anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

    def _make_field(self, panel, label, kind, row, col):
        tk.Label(panel, text=label, bg=self.PANEL_BG, fg=self.FG,
                 font=("Segoe UI", 10), anchor="w").grid(
            row=row, column=col, sticky="w", padx=14, pady=5
        )

        if kind == "entry":
            widget = tk.Entry(
                panel, bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
                relief=tk.FLAT, font=("Segoe UI", 10), width=28
            )
        elif kind == "fk_activity":
            widget = ttk.Combobox(panel, values=[""], state="readonly",
                                  font=("Segoe UI", 10), width=26)
            widget.set("")
        elif kind == "combo_doctype":
            widget = ttk.Combobox(panel, values=DOC_TYPE_OPTIONS, state="normal",
                                  font=("Segoe UI", 10), width=26)
        elif kind == "combo_status":
            widget = ttk.Combobox(panel, values=STATUS_OPTIONS, state="normal",
                                  font=("Segoe UI", 10), width=26)
            widget.set(STATUS_OPTIONS[0])
        elif kind == "date":
            # Calendar date picker. date_pattern controls the .get() string format.
            widget = DateEntry(
                panel, date_pattern="yyyy-mm-dd",
                font=("Segoe UI", 10), width=25,
                background=self.ACCENT, foreground="#ffffff",
                borderwidth=0, state="readonly"
            )
            # Blank by default — DateEntry defaults to "today"; we want the
            # form to start empty since Issue_Date is optional.
            widget.delete(0, tk.END)
        else:
            raise ValueError(f"Unknown field kind: {kind}")

        widget.grid(row=row, column=col + 1, padx=14, pady=5, sticky="w")
        self._entries[label] = widget

    # ── Search-input builders ──────────────────────────────────────────────
    def _clear_search_input_frame(self):
        for child in self.search_input_frame.winfo_children():
            child.destroy()
        self._search_keyword_entry = None
        self._search_date_from = None
        self._search_date_to = None

    def _build_keyword_search(self):
        """Show a single keyword Entry (used for ID / Activity / Type / Title / Revision / Status search)."""
        self._clear_search_input_frame()

        tk.Label(self.search_input_frame, text="Keyword:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))

        self.search_var.set("") # reset previous keyword
        self._search_keyword_entry = tk.Entry(
            self.search_input_frame, textvariable=self.search_var,
            bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
            relief=tk.FLAT, font=("Segoe UI", 10), width=30
        )
        self._search_keyword_entry.pack(side=tk.LEFT)

    def _build_date_range_search(self):
        """Show two calendar pickers: 'From' and 'To' (used for Issue Date search)."""
        self._clear_search_input_frame()

        tk.Label(self.search_input_frame, text="From:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self._search_date_from = DateEntry(
            self.search_input_frame, date_pattern="yyyy-mm-dd",
            font=("Segoe UI", 10), width=12,
            background=self.ACCENT, foreground="#ffffff",
            borderwidth=0, state="readonly"
        )
        self._search_date_from.delete(0, tk.END) # start blank
        self._search_date_from.pack(side=tk.LEFT, padx=(0, 10))
        self._search_date_from.bind("<<DateEntrySelected>>", lambda _e: self.load_documents())

        tk.Label(self.search_input_frame, text="To:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self._search_date_to = DateEntry(
            self.search_input_frame, date_pattern="yyyy-mm-dd",
            font=("Segoe UI", 10), width=12,
            background=self.ACCENT, foreground="#ffffff",
            borderwidth=0, state="readonly"
        )
        self._search_date_to.delete(0, tk.END) # start blank
        self._search_date_to.pack(side=tk.LEFT)
        self._search_date_to.bind("<<DateEntrySelected>>", lambda _e: self.load_documents())

        # Small "Clear dates" button so the user can reset without retyping
        tk.Button(
            self.search_input_frame, text="✖", command=self._clear_date_range,
            bg=self.BTN_BG, fg=self.BTN_FG, activebackground="#0096c7",
            relief=tk.FLAT, font=("Segoe UI", 9, "bold"), width=2, cursor="hand2"
        ).pack(side=tk.LEFT, padx=(8, 0))

    def _clear_date_range(self):
        if self._search_date_from is not None:
            self._search_date_from.delete(0, tk.END)
        if self._search_date_to is not None:
            self._search_date_to.delete(0, tk.END)
        self.load_documents()

    def _on_search_column_change(self, _event=None):
        column_label = self.search_column_var.get()
        if column_label in DATE_RANGE_COLUMNS:
            self._build_date_range_search()
        else:
            self._build_keyword_search()
        self.load_documents()

    # ── FK loading ───────────────────────────────────────────────────────────
    def _refresh_activity_options(self):
        self._activity_display_to_id = {}
        self._activity_id_to_display = {}
        rows = []
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT Activity_ID, Activity_Name FROM WBS_ACTIVITIES ORDER BY Activity_ID"
            )
            rows = cursor.fetchall()
            conn.close()
        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load WBS Activities:\n{exc}")

        values = [""]
        for r in rows:
            display = f"{r[0]} - {r[1]}"
            self._activity_display_to_id[display] = r[0]
            self._activity_id_to_display[r[0]] = display
            values.append(display)

        widget = self._entries["Activity_ID"]
        widget["values"] = values
        if widget.get() not in values:
            widget.set("")

    def _refresh_all(self):
        self._refresh_activity_options()
        self.load_documents()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_field(self, label: str) -> str:
        return self._entries[label].get().strip()

    def _activity_id_from_field(self):
        display = self._get_field("Activity_ID")
        if not display:
            return None
        return self._activity_display_to_id.get(display, display)

    def _validate_inputs(self, is_add: bool) -> bool:
        if is_add and not self._get_field("Document_ID *"):
            messagebox.showwarning("Validation", "Document_ID is required.")
            return False
        if not self._get_field("Title *"):
            messagebox.showwarning("Validation", "Title is required.")
            return False

        # DateEntry already enforces yyyy-mm-dd formatting via the calendar,
        # but we still guard against a manually-cleared/blank field here.
        val = self._get_field("Issue Date")
        if val:
            try:
                datetime.strptime(val, DATE_FMT)
            except ValueError:
                messagebox.showwarning(
                    "Validation",
                    "'Issue Date' must be in YYYY-MM-DD format (e.g. 2025-01-31)."
                )
                return False

        return True

    def _none_if_empty(self, val: str):
        return val if val else None

    def clear_fields(self):
        self._selected_id = None
        self._entries["Document_ID *"].configure(state="normal")
        for lbl, widget in self._entries.items():
            if isinstance(widget, ttk.Combobox):
                if lbl == "Status":
                    widget.set(STATUS_OPTIONS[0])
                else:
                    widget.set("")
            elif isinstance(widget, DateEntry):
                widget.delete(0, tk.END)
            else:
                widget.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _set_date_field(self, label: str, value):
        """Set a DateEntry field's text directly (value may be a date string or empty)."""
        widget = self._entries[label]
        widget.delete(0, tk.END)
        if value:
            widget.insert(0, value)

    def _on_row_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        # values = (Document_ID, Activity_ID, Doc_Type, Title, Revision, Issue_Date, Status)
        self._selected_id = values[0]

        self._entries["Document_ID *"].configure(state="normal")
        self._entries["Document_ID *"].delete(0, tk.END)
        self._entries["Document_ID *"].insert(0, values[0])
        self._entries["Document_ID *"].configure(state="disabled")

        activity_id = values[1]
        self._entries["Activity_ID"].set(
            self._activity_id_to_display.get(activity_id, "") if activity_id else ""
        )

        self._entries["Doc_Type"].set(values[2] if values[2] else "")

        self._entries["Title *"].delete(0, tk.END)
        self._entries["Title *"].insert(0, values[3])

        self._entries["Revision"].delete(0, tk.END)
        self._entries["Revision"].insert(0, values[4] if values[4] else "")

        self._set_date_field("Issue Date", values[5] if values[5] else "")

        self._entries["Status"].set(values[6] if values[6] else STATUS_OPTIONS[0])

    def _sort_tree(self, col: str, reverse: bool):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def load_documents(self, *_):
        """Read documents, filtered by the selected column, into the treeview.

        Text columns (ID / Activity ID / Doc Type / Title / Revision / Status)
        use a keyword LIKE search. Issue Date uses a From/To range search.
        """
        for row in self.tree.get_children():
            self.tree.delete(row)

        column_label = self.search_column_var.get()
        sql_column = SEARCH_COLUMNS.get(column_label, "Title")
        keyword_active = False

        try:
            conn = get_connection()
            cursor = conn.cursor()

            if column_label in DATE_RANGE_COLUMNS:
                date_from = self._search_date_from.get().strip() if self._search_date_from else ""
                date_to = self._search_date_to.get().strip() if self._search_date_to else ""

                conditions, params = [], []
                if date_from:
                    conditions.append(f"{sql_column} >= ?")
                    params.append(date_from)
                if date_to:
                    conditions.append(f"{sql_column} <= ?")
                    params.append(date_to)

                where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
                cursor.execute(
                    "SELECT Document_ID, Activity_ID, Doc_Type, Title, Revision, "
                    "Issue_Date, Status FROM DOCUMENTS" + where_clause +
                    " ORDER BY Document_ID",
                    params
                )
                keyword_active = bool(conditions)

            else:
                keyword = self.search_var.get().strip()
                keyword_active = bool(keyword)

                if keyword:
                    cursor.execute(
                        f"SELECT Document_ID, Activity_ID, Doc_Type, Title, Revision, "
                        f"Issue_Date, Status FROM DOCUMENTS WHERE {sql_column} LIKE ? "
                        f"ORDER BY Document_ID",
                        (f"%{keyword}%",)
                    )
                else:
                    cursor.execute(
                        "SELECT Document_ID, Activity_ID, Doc_Type, Title, Revision, "
                        "Issue_Date, Status FROM DOCUMENTS ORDER BY Document_ID"
                    )

            rows = cursor.fetchall()
            for row in rows:
                issue = str(row[5])[:10] if row[5] else ""
                self.tree.insert("", tk.END, values=(
                    row[0], row[1] or "", row[2] or "", row[3] or "",
                    row[4] or "", issue, row[6] or ""
                ))

            conn.close()

            if keyword_active and not rows:
                messagebox.showinfo("Search", "No documents matched your search criteria.")

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load documents:\n{exc}")

    def add_document(self):
        if not self._validate_inputs(is_add=True):
            return

        doc_id = self._get_field("Document_ID *")
        activity_id = self._activity_id_from_field()
        doc_type = self._none_if_empty(self._get_field("Doc_Type"))
        title = self._get_field("Title *")
        revision = self._none_if_empty(self._get_field("Revision"))
        issue_date = self._none_if_empty(self._get_field("Issue Date"))
        status = self._none_if_empty(self._get_field("Status"))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO DOCUMENTS (Document_ID, Activity_ID, Doc_Type, Title, "
                "Revision, Issue_Date, Status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (doc_id, activity_id, doc_type, title, revision, issue_date, status)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Document '{doc_id}' added successfully.")
            self.clear_fields()
            self.load_documents()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to add document:\n{exc}")

    def update_document(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select a document from the list first.")
            return
        if not self._validate_inputs(is_add=False):
            return

        activity_id = self._activity_id_from_field()
        doc_type = self._none_if_empty(self._get_field("Doc_Type"))
        title = self._get_field("Title *")
        revision = self._none_if_empty(self._get_field("Revision"))
        issue_date = self._none_if_empty(self._get_field("Issue Date"))
        status = self._none_if_empty(self._get_field("Status"))

        if not messagebox.askyesno("Confirm Update",
                                   f"Update Document '{self._selected_id}'?"):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE DOCUMENTS SET Activity_ID=?, Doc_Type=?, Title=?, Revision=?, "
                "Issue_Date=?, Status=? WHERE Document_ID=?",
                (activity_id, doc_type, title, revision, issue_date, status,
                 self._selected_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Document updated successfully.")
            self.clear_fields()
            self.load_documents()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to update document:\n{exc}")

    def delete_document(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select a document from the list first.")
            return

        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete Document '{self._selected_id}'?"
                                   f"\nThis cannot be undone."):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM DOCUMENTS WHERE Document_ID=?",
                           (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Document deleted successfully.")
            self.clear_fields()
            self.load_documents()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to delete document:\n{exc}")


# ── Stand-alone test runner ───────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Refinery Project – Documents Form")
    root.geometry("1000x650")
    root.configure(bg="#1e2327")
    DocumentsForm(root)
    root.mainloop()
