"""
costs_form.py
─────────────
Full CRUD Tkinter form for the COSTS table in Refinery_Project.

Table schema
────────────
CREATE TABLE COSTS (
    Cost_ID         VARCHAR(20)    PRIMARY KEY,
    Activity_ID     VARCHAR(20),
    Cost_Type       VARCHAR(50),
    Budgeted_Amount DECIMAL(15,2),
    Actual_Amount   DECIMAL(15,2),
    Date_Recorded   DATE,
    CONSTRAINT fk_costs_activity FOREIGN KEY (Activity_ID)
        REFERENCES WBS_ACTIVITIES(Activity_ID)
);

Notes
─────
• Cost_ID is a user-supplied VARCHAR primary key (not auto-generated).
• Activity_ID is a FK dropdown loaded from WBS_ACTIVITIES at startup.
• Budgeted_Amount and Actual_Amount validated as non-negative decimals.
• Date_Recorded validated as YYYY-MM-DD.
• Variance (Actual - Budgeted) is calculated and shown read-only in the treeview.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from decimal import Decimal, InvalidOperation

from db_connection import get_connection

COST_TYPE_OPTIONS = [
    "Labour", "Equipment", "Material", "Subcontract",
    "Engineering", "Procurement", "Construction", "Other"
]
DATE_FMT = "%Y-%m-%d"


class CostsForm(tk.Frame):

    BG       = "#1e2327"
    PANEL_BG = "#252b30"
    FG       = "#e0e0e0"
    ACCENT   = "#00b4d8"
    BTN_BG   = "#00b4d8"
    BTN_FG   = "#ffffff"
    ENTRY_BG = "#2e3540"
    SEL_BG   = "#00b4d8"

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, bg=self.BG, *args, **kwargs)
        self._selected_id = None        # Cost_ID of currently selected row
        self._build_ui()
        self.load_costs()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(
            self, text="Costs Management", bg=self.BG, fg=self.ACCENT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 6))

        # Search bar
        search_frame = tk.Frame(self, bg=self.BG)
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 6))
        tk.Label(search_frame, text="Search:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_costs())
        tk.Entry(
            search_frame, textvariable=self.search_var,
            bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
            relief=tk.FLAT, font=("Segoe UI", 10), width=30
        ).pack(side=tk.LEFT)

        # Entry panel – two columns
        panel = tk.LabelFrame(
            self, text=" Cost Details ", bg=self.PANEL_BG, fg=self.ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, relief=tk.GROOVE
        )
        panel.pack(fill=tk.X, padx=20, pady=6)

        # Left column fields
        left_fields = [
            ("Cost ID *",                  "entry"),
            ("Activity ID",                "combo_db"),   # FK from WBS_ACTIVITIES
            ("Cost Type",                  "combo"),
        ]
        # Right column fields
        right_fields = [
            ("Budgeted Amount",            "entry"),
            ("Actual Amount",              "entry"),
            ("Date Recorded (YYYY-MM-DD)", "entry"),
        ]

        self._entries = {}

        for col_offset, field_group in enumerate([left_fields, right_fields]):
            for row_idx, (lbl, wtype) in enumerate(field_group):
                tk.Label(panel, text=lbl, bg=self.PANEL_BG, fg=self.FG,
                         font=("Segoe UI", 10), anchor="w").grid(
                    row=row_idx, column=col_offset * 2,
                    sticky="w", padx=14, pady=6
                )
                if wtype == "combo":
                    widget = ttk.Combobox(
                        panel, values=COST_TYPE_OPTIONS, state="readonly",
                        font=("Segoe UI", 10), width=22
                    )
                    widget.set(COST_TYPE_OPTIONS[0])
                elif wtype == "combo_db":
                    widget = ttk.Combobox(
                        panel, values=[], state="readonly",
                        font=("Segoe UI", 10), width=22
                    )
                else:
                    widget = tk.Entry(
                        panel, bg=self.ENTRY_BG, fg=self.FG,
                        insertbackground=self.FG, relief=tk.FLAT,
                        font=("Segoe UI", 10), width=24
                    )
                widget.grid(row=row_idx, column=col_offset * 2 + 1,
                            padx=14, pady=6, sticky="w")
                self._entries[lbl] = widget

        # Load FK dropdown
        self._load_activity_ids()

        # Button row
        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(pady=8)
        for text, cmd in [
            ("➕ Add",    self.add_cost),
            ("✏️ Update",  self.update_cost),
            ("🗑️ Delete",  self.delete_cost),
            ("🔄 Refresh", self.load_costs),
            ("✖ Clear",   self.clear_fields),
        ]:
            tk.Button(
                btn_frame, text=text, command=cmd,
                bg=self.BTN_BG, fg=self.BTN_FG, activebackground="#0096c7",
                relief=tk.FLAT, font=("Segoe UI", 10, "bold"),
                width=11, cursor="hand2"
            ).pack(side=tk.LEFT, padx=5)

        # Treeview
        tree_frame = tk.Frame(self, bg=self.BG)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 16))

        cols = ("Cost ID", "Activity ID", "Cost Type",
                "Budgeted", "Actual", "Variance", "Date Recorded")
        self.tree = ttk.Treeview(tree_frame, columns=cols,
                                 show="headings", selectmode="browse")

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

        col_widths = {
            "Cost ID": 100, "Activity ID": 100, "Cost Type": 120,
            "Budgeted": 110, "Actual": 110, "Variance": 110,
            "Date Recorded": 110
        }
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_tree(c, False))
            self.tree.column(col, width=col_widths[col], anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",
                             command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

    # ── FK dropdown loader ────────────────────────────────────────────────────
    def _load_activity_ids(self):
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT Activity_ID FROM WBS_ACTIVITIES ORDER BY Activity_ID"
            )
            ids = [r[0] for r in cursor.fetchall()]
            conn.close()
            self._entries["Activity ID"]["values"] = ids
            if ids:
                self._entries["Activity ID"].set(ids[0])
        except Exception:
            pass    # table may not exist yet; leave dropdown empty

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get(self, label: str) -> str:
        return self._entries[label].get().strip()

    def _none_if_empty(self, val: str):
        return val if val else None

    def _parse_decimal(self, val: str, label: str):
        """Return Decimal or None; show warning and return False on bad input."""
        if not val:
            return None
        try:
            d = Decimal(val)
            if d < 0:
                raise InvalidOperation
            return d
        except InvalidOperation:
            messagebox.showwarning(
                "Validation",
                f"'{label}' must be a non-negative number (e.g. 12500.00)."
            )
            return False    # sentinel – distinct from None

    def _validate_inputs(self) -> bool:
        if not self._get("Cost ID *"):
            messagebox.showwarning("Validation", "Cost ID is required.")
            return False

        for lbl in ("Budgeted Amount", "Actual Amount"):
            result = self._parse_decimal(self._get(lbl), lbl)
            if result is False:
                return False

        date_val = self._get("Date Recorded (YYYY-MM-DD)")
        if date_val:
            try:
                datetime.strptime(date_val, DATE_FMT)
            except ValueError:
                messagebox.showwarning(
                    "Validation",
                    "Date Recorded must be in YYYY-MM-DD format (e.g. 2025-06-30)."
                )
                return False

        return True

    def clear_fields(self):
        self._selected_id = None
        for lbl, widget in self._entries.items():
            if isinstance(widget, ttk.Combobox):
                vals = widget["values"]
                widget.set(vals[0] if vals else "")
            else:
                widget.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _on_row_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        v = self.tree.item(selected[0], "values")
        # v = (Cost_ID, Activity_ID, Cost_Type, Budgeted, Actual, Variance, Date_Recorded)
        self._selected_id = v[0]

        mapping = {
            "Cost ID *":                   v[0],
            "Activity ID":                 v[1],
            "Cost Type":                   v[2],
            "Budgeted Amount":             v[3],
            "Actual Amount":               v[4],
            # Variance is computed – not editable
            "Date Recorded (YYYY-MM-DD)":  v[6],
        }
        for lbl, val in mapping.items():
            w = self._entries[lbl]
            if isinstance(w, ttk.Combobox):
                w.set(val or "")
            else:
                w.delete(0, tk.END)
                w.insert(0, val or "")

    def _sort_tree(self, col: str, reverse: bool):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            data.sort(key=lambda t: float(t[0].replace(",", ""))
                      if t[0] else 0, reverse=reverse)
        except ValueError:
            data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    @staticmethod
    def _fmt_decimal(val) -> str:
        """Format a DB decimal value as a 2-dp string, or empty string."""
        if val is None:
            return ""
        try:
            return f"{Decimal(str(val)):.2f}"
        except Exception:
            return str(val)

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def load_costs(self, *_):
        for row in self.tree.get_children():
            self.tree.delete(row)

        keyword = self.search_var.get().strip()
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            if keyword:
                cursor.execute(
                    "SELECT Cost_ID, Activity_ID, Cost_Type, "
                    "Budgeted_Amount, Actual_Amount, Date_Recorded "
                    "FROM COSTS "
                    "WHERE Cost_ID LIKE ? OR Activity_ID LIKE ? "
                    "   OR Cost_Type LIKE ? "
                    "ORDER BY Cost_ID",
                    (f"%{keyword}%",) * 3
                )
            else:
                cursor.execute(
                    "SELECT Cost_ID, Activity_ID, Cost_Type, "
                    "Budgeted_Amount, Actual_Amount, Date_Recorded "
                    "FROM COSTS ORDER BY Cost_ID"
                )

            for row in cursor.fetchall():
                budgeted = self._fmt_decimal(row[3])
                actual   = self._fmt_decimal(row[4])
                # Variance = Actual - Budgeted
                try:
                    variance = f"{Decimal(str(row[4] or 0)) - Decimal(str(row[3] or 0)):.2f}"
                except Exception:
                    variance = ""
                date_val = str(row[5])[:10] if row[5] else ""

                self.tree.insert("", tk.END, values=(
                    row[0] or "",   # Cost_ID
                    row[1] or "",   # Activity_ID
                    row[2] or "",   # Cost_Type
                    budgeted,
                    actual,
                    variance,
                    date_val,
                ))
            conn.close()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to load costs:\n{exc}")

    def add_cost(self):
        if not self._validate_inputs():
            return

        cost_id  = self._get("Cost ID *")
        act_id   = self._none_if_empty(self._get("Activity ID"))
        cost_type= self._none_if_empty(self._get("Cost Type"))
        budgeted = self._parse_decimal(self._get("Budgeted Amount"), "Budgeted Amount")
        actual   = self._parse_decimal(self._get("Actual Amount"),   "Actual Amount")
        date_rec = self._none_if_empty(self._get("Date Recorded (YYYY-MM-DD)"))

        if budgeted is False or actual is False:
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO COSTS "
                "(Cost_ID, Activity_ID, Cost_Type, Budgeted_Amount, "
                " Actual_Amount, Date_Recorded) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (cost_id, act_id, cost_type,
                 float(budgeted) if budgeted is not None else None,
                 float(actual)   if actual   is not None else None,
                 date_rec)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success",
                                f"Cost record '{cost_id}' added successfully.")
            self.clear_fields()
            self.load_costs()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to add cost:\n{exc}")

    def update_cost(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection",
                                   "Please select a cost record from the list first.")
            return
        if not self._validate_inputs():
            return

        act_id   = self._none_if_empty(self._get("Activity ID"))
        cost_type= self._none_if_empty(self._get("Cost Type"))
        budgeted = self._parse_decimal(self._get("Budgeted Amount"), "Budgeted Amount")
        actual   = self._parse_decimal(self._get("Actual Amount"),   "Actual Amount")
        date_rec = self._none_if_empty(self._get("Date Recorded (YYYY-MM-DD)"))

        if budgeted is False or actual is False:
            return

        if not messagebox.askyesno("Confirm Update",
                                   f"Update Cost ID '{self._selected_id}'?"):
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE COSTS SET "
                "Activity_ID=?, Cost_Type=?, Budgeted_Amount=?, "
                "Actual_Amount=?, Date_Recorded=? "
                "WHERE Cost_ID=?",
                (act_id, cost_type,
                 float(budgeted) if budgeted is not None else None,
                 float(actual)   if actual   is not None else None,
                 date_rec, self._selected_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Cost record updated successfully.")
            self.clear_fields()
            self.load_costs()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to update cost:\n{exc}")

    def delete_cost(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection",
                                   "Please select a cost record from the list first.")
            return

        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete Cost ID "
                                   f"'{self._selected_id}'?\n"
                                   f"This cannot be undone."):
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM COSTS WHERE Cost_ID=?",
                           (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Cost record deleted successfully.")
            self.clear_fields()
            self.load_costs()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to delete cost:\n{exc}")


# ── Stand-alone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Refinery Project – Costs Form")
    root.geometry("980x620")
    root.configure(bg="#1e2327")
    CostsForm(root)
    root.mainloop()