"""
inspections_form.py
─────────────────────
Full CRUD Tkinter form for the INSPECTIONS table in Refinery_Project.

Table schema
────────────
CREATE TABLE INSPECTIONS (
    Inspection_ID VARCHAR(20) PRIMARY KEY,
    Equipment_Tag VARCHAR(20),
    Inspection_Date DATE,
    Inspection_Type VARCHAR(50),
    Result VARCHAR(50),
    Inspector VARCHAR(100),

    CONSTRAINT fk_inspections_equipment FOREIGN KEY (Equipment_Tag)
        REFERENCES EQUIPMENT (Equipment_Tag)
);

Notes
─────
• Inspection_ID is a user-entered VARCHAR PK, editable on Add, locked once a
  row is selected for Update/Delete.
• Equipment_Tag is a foreign key, presented as a read-only Combobox populated
  live from EQUIPMENT ("Equipment_Tag - Description"), optional.

Search behaviour (added to match projects_form.py / equipment_form.py)
────────────────────────────────────────────────────────────────────────
• Column-scoped search: user picks which column to search (Inspection ID,
  Equipment Tag, Inspection Date, Inspection Type, Result, Inspector) via a
  dropdown next to the search box.
• Text columns use a keyword LIKE search.
• "Inspection Date" uses a date-range search (From / To tkcalendar.DateEntry
  pickers) instead of a keyword box, same as projects_form.py / equipment_form.py.
• The Inspection_Date entry field in the details panel is now a DateEntry
  calendar picker (was a free-typed "YYYY-MM-DD" Entry) for consistency.

Requires the 'tkcalendar' package:
    pip install tkcalendar
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from tkcalendar import DateEntry

from db_connection import get_connection

DATE_FMT = "%Y-%m-%d"

INSPECTION_TYPE_OPTIONS = ["Visual", "Ultrasonic Thickness", "Pressure Test",
                           "Functional Test", "Safety", "Regulatory", "Other"]
RESULT_OPTIONS = ["Pass", "Fail", "Conditional Pass", "Pending"]

# ── Search column options: display label -> actual SQL column name ──────────
SEARCH_COLUMNS = {
    "Inspection ID": "Inspection_ID",
    "Equipment Tag": "Equipment_Tag",
    "Inspection Date": "Inspection_Date",
    "Inspection Type": "Inspection_Type",
    "Result": "Result",
    "Inspector": "Inspector",
}

# Columns that use a date-range search (From / To calendars) instead of a keyword box
DATE_RANGE_COLUMNS = {"Inspection Date": "Inspection_Date"}


# ────────────────────────────────────────────────────────────────────────────
class InspectionsForm(tk.Frame):
    """
    Dark-themed frame with:
      • A data-entry panel (top)
      • CRUD buttons
      • A searchable, sortable Treeview listing all inspections
      • Column-scoped search: keyword search for text columns, date-range
        search (From/To calendars) for Inspection Date
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
        self._selected_id = None # Inspection_ID of the currently selected row
        self._equipment_display_to_id = {}
        self._equipment_id_to_display = {}
        self._build_ui()
        self._refresh_equipment_options()
        self.load_inspections()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            self, text="Inspections Management", bg=self.BG, fg=self.ACCENT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 6))

        # ── Search bar (column selector + dynamic keyword/date-range area) ───
        search_frame = tk.Frame(self, bg=self.BG)
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 6))

        tk.Label(search_frame, text="Search by:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))

        self.search_column_var = tk.StringVar(value="Inspector")
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
        self.search_var.trace_add("write", lambda *_: self.load_inspections())

        # Date-range widgets are created on demand in _build_keyword_search() /
        # _build_date_range_search(); references stored here once created.
        self._search_keyword_entry = None
        self._search_date_from = None
        self._search_date_to = None

        # Build the initial search input (default column is "Inspector" -> keyword box)
        self._build_keyword_search()

        # ── Entry panel ───────────────────────────────────────────────────────
        panel = tk.LabelFrame(
            self, text=" Inspection Details ", bg=self.PANEL_BG, fg=self.ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, relief=tk.GROOVE
        )
        panel.pack(fill=tk.X, padx=20, pady=6)

        self._entries = {}

        col0_fields = [
            ("Inspection_ID *", "entry"),
            ("Equipment_Tag", "fk_equipment"),
            ("Inspection_Date", "date"),
        ]
        col1_fields = [
            ("Inspection_Type", "combo_type"),
            ("Result", "combo_result"),
            ("Inspector", "entry"),
        ]

        for i, (lbl, kind) in enumerate(col0_fields):
            self._make_field(panel, lbl, kind, row=i, col=0)
        for i, (lbl, kind) in enumerate(col1_fields):
            self._make_field(panel, lbl, kind, row=i, col=2)

        # ── Button row ────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(pady=8)

        buttons = [
            ("➕ Add", self.add_inspection),
            ("✏️ Update", self.update_inspection),
            ("🗑️ Delete", self.delete_inspection),
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

        cols = ("Inspection_ID", "Equipment_Tag", "Inspection_Date",
                "Inspection_Type", "Result", "Inspector")
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

        col_widths = {"Inspection_ID": 110, "Equipment_Tag": 110,
                      "Inspection_Date": 110, "Inspection_Type": 140,
                      "Result": 120, "Inspector": 140}
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
        elif kind == "fk_equipment":
            widget = ttk.Combobox(panel, values=[""], state="readonly",
                                  font=("Segoe UI", 10), width=26)
            widget.set("")
        elif kind == "combo_type":
            widget = ttk.Combobox(panel, values=INSPECTION_TYPE_OPTIONS, state="normal",
                                  font=("Segoe UI", 10), width=26)
        elif kind == "combo_result":
            widget = ttk.Combobox(panel, values=RESULT_OPTIONS, state="normal",
                                  font=("Segoe UI", 10), width=26)
        elif kind == "date":
            # Calendar date picker, same style as projects_form.py / equipment_form.py.
            widget = DateEntry(
                panel, date_pattern="yyyy-mm-dd",
                font=("Segoe UI", 10), width=25,
                background=self.ACCENT, foreground="#ffffff",
                borderwidth=0, state="readonly"
            )
            # Blank by default — DateEntry defaults to "today"; Inspection_Date
            # should start empty rather than assume today's date.
            widget.delete(0, tk.END)
        else:
            raise ValueError(f"Unknown field kind: {kind}")

        widget.grid(row=row, column=col + 1, padx=14, pady=5, sticky="w")
        self._entries[label] = widget

    # ── FK loading ───────────────────────────────────────────────────────────
    def _refresh_equipment_options(self):
        self._equipment_display_to_id = {}
        self._equipment_id_to_display = {}
        rows = []
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT Equipment_Tag, Description FROM EQUIPMENT ORDER BY Equipment_Tag"
            )
            rows = cursor.fetchall()
            conn.close()
        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load Equipment:\n{exc}")

        values = [""]
        for r in rows:
            label = r[1] if r[1] else ""
            display = f"{r[0]} - {label}" if label else r[0]
            self._equipment_display_to_id[display] = r[0]
            self._equipment_id_to_display[r[0]] = display
            values.append(display)

        widget = self._entries["Equipment_Tag"]
        widget["values"] = values
        if widget.get() not in values:
            widget.set("")

    def _refresh_all(self):
        self._refresh_equipment_options()
        self.load_inspections()

    # ── Search-input builders ──────────────────────────────────────────────
    def _clear_search_input_frame(self):
        for child in self.search_input_frame.winfo_children():
            child.destroy()
        self._search_keyword_entry = None
        self._search_date_from = None
        self._search_date_to = None

    def _build_keyword_search(self):
        """Show a single keyword Entry (used for ID / Tag / Type / Result /
        Inspector search)."""
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
        """Show two calendar pickers: 'From' and 'To' (used for Inspection Date search)."""
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
        self._search_date_from.bind("<<DateEntrySelected>>", lambda _e: self.load_inspections())

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
        self._search_date_to.bind("<<DateEntrySelected>>", lambda _e: self.load_inspections())

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
        self.load_inspections()

    def _on_search_column_change(self, _event=None):
        column_label = self.search_column_var.get()
        if column_label in DATE_RANGE_COLUMNS:
            self._build_date_range_search()
        else:
            self._build_keyword_search()
        self.load_inspections()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_field(self, label: str) -> str:
        return self._entries[label].get().strip()

    def _equipment_id_from_field(self):
        display = self._get_field("Equipment_Tag")
        if not display:
            return None
        return self._equipment_display_to_id.get(display, display)

    def _validate_inputs(self, is_add: bool) -> bool:
        if is_add and not self._get_field("Inspection_ID *"):
            messagebox.showwarning("Validation", "Inspection_ID is required.")
            return False

        # DateEntry already enforces yyyy-mm-dd formatting via the calendar,
        # but we still guard against a manually-cleared/blank field here.
        val = self._get_field("Inspection_Date")
        if val:
            try:
                datetime.strptime(val, DATE_FMT)
            except ValueError:
                messagebox.showwarning(
                    "Validation",
                    "'Inspection_Date' must be in YYYY-MM-DD format (e.g. 2025-01-31)."
                )
                return False

        return True

    def _none_if_empty(self, val: str):
        return val if val else None

    def _set_date_field(self, label: str, value):
        """Set a DateEntry field's text directly (value may be a date string or empty)."""
        widget = self._entries[label]
        widget.delete(0, tk.END)
        if value:
            widget.insert(0, value)

    def clear_fields(self):
        self._selected_id = None
        self._entries["Inspection_ID *"].configure(state="normal")
        for lbl, widget in self._entries.items():
            if isinstance(widget, ttk.Combobox):
                widget.set("")
            elif isinstance(widget, DateEntry):
                widget.delete(0, tk.END)
            else:
                widget.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _on_row_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        # values = (Inspection_ID, Equipment_Tag, Inspection_Date,
        # Inspection_Type, Result, Inspector)
        self._selected_id = values[0]

        self._entries["Inspection_ID *"].configure(state="normal")
        self._entries["Inspection_ID *"].delete(0, tk.END)
        self._entries["Inspection_ID *"].insert(0, values[0])
        self._entries["Inspection_ID *"].configure(state="disabled")

        equip_tag = values[1]
        self._entries["Equipment_Tag"].set(
            self._equipment_id_to_display.get(equip_tag, "") if equip_tag else ""
        )

        self._set_date_field("Inspection_Date", values[2] if values[2] else "")

        self._entries["Inspection_Type"].set(values[3] if values[3] else "")
        self._entries["Result"].set(values[4] if values[4] else "")

        self._entries["Inspector"].delete(0, tk.END)
        self._entries["Inspector"].insert(0, values[5] if values[5] else "")

    def _sort_tree(self, col: str, reverse: bool):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def load_inspections(self, *_):
        """Read inspections, filtered by the selected column, into the treeview.

        Text columns (ID / Tag / Type / Result / Inspector) use a keyword LIKE
        search. Inspection Date uses a From/To range search.
        """
        for row in self.tree.get_children():
            self.tree.delete(row)

        column_label = self.search_column_var.get()
        sql_column = SEARCH_COLUMNS.get(column_label, "Inspector")
        keyword_active = False
        rows = []

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
                    "SELECT Inspection_ID, Equipment_Tag, Inspection_Date, "
                    "Inspection_Type, Result, Inspector FROM INSPECTIONS" + where_clause +
                    " ORDER BY Inspection_ID",
                    params
                )
                keyword_active = bool(conditions)

            else:
                keyword = self.search_var.get().strip()
                keyword_active = bool(keyword)

                if keyword:
                    cursor.execute(
                        f"SELECT Inspection_ID, Equipment_Tag, Inspection_Date, "
                        f"Inspection_Type, Result, Inspector FROM INSPECTIONS "
                        f"WHERE {sql_column} LIKE ? ORDER BY Inspection_ID",
                        (f"%{keyword}%",)
                    )
                else:
                    cursor.execute(
                        "SELECT Inspection_ID, Equipment_Tag, Inspection_Date, "
                        "Inspection_Type, Result, Inspector FROM INSPECTIONS "
                        "ORDER BY Inspection_ID"
                    )

            rows = cursor.fetchall()
            for row in rows:
                insp_date = str(row[2])[:10] if row[2] else ""
                self.tree.insert("", tk.END, values=(
                    row[0], row[1] or "", insp_date, row[3] or "",
                    row[4] or "", row[5] or ""
                ))

            conn.close()

            if keyword_active and not rows:
                messagebox.showinfo("Search", "No inspections matched your search criteria.")

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load inspections:\n{exc}")

    def add_inspection(self):
        if not self._validate_inputs(is_add=True):
            return

        insp_id = self._get_field("Inspection_ID *")
        equip_tag = self._equipment_id_from_field()
        insp_date = self._none_if_empty(self._get_field("Inspection_Date"))
        insp_type = self._none_if_empty(self._get_field("Inspection_Type"))
        result = self._none_if_empty(self._get_field("Result"))
        inspector = self._none_if_empty(self._get_field("Inspector"))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO INSPECTIONS (Inspection_ID, Equipment_Tag, Inspection_Date, "
                "Inspection_Type, Result, Inspector) VALUES (?, ?, ?, ?, ?, ?)",
                (insp_id, equip_tag, insp_date, insp_type, result, inspector)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Inspection '{insp_id}' added successfully.")
            self.clear_fields()
            self.load_inspections()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to add inspection:\n{exc}")

    def update_inspection(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select an inspection from the list first.")
            return
        if not self._validate_inputs(is_add=False):
            return

        equip_tag = self._equipment_id_from_field()
        insp_date = self._none_if_empty(self._get_field("Inspection_Date"))
        insp_type = self._none_if_empty(self._get_field("Inspection_Type"))
        result = self._none_if_empty(self._get_field("Result"))
        inspector = self._none_if_empty(self._get_field("Inspector"))

        if not messagebox.askyesno("Confirm Update",
                                   f"Update Inspection '{self._selected_id}'?"):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE INSPECTIONS SET Equipment_Tag=?, Inspection_Date=?, "
                "Inspection_Type=?, Result=?, Inspector=? WHERE Inspection_ID=?",
                (equip_tag, insp_date, insp_type, result, inspector, self._selected_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Inspection updated successfully.")
            self.clear_fields()
            self.load_inspections()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to update inspection:\n{exc}")

    def delete_inspection(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select an inspection from the list first.")
            return

        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete Inspection '{self._selected_id}'?"
                                   f"\nThis cannot be undone."):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM INSPECTIONS WHERE Inspection_ID=?",
                           (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Inspection deleted successfully.")
            self.clear_fields()
            self.load_inspections()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to delete inspection:\n{exc}")


# ── Stand-alone test runner ───────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Refinery Project – Inspections Form")
    root.geometry("1000x650")
    root.configure(bg="#1e2327")
    InspectionsForm(root)
    root.mainloop()
