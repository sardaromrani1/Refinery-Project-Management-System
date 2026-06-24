"""
materials_form.py
─────────────────
Full CRUD Tkinter form for the MATERIALS table in Refinery_Project.

Table schema
────────────
CREATE TABLE MATERIALS (
    Material_ID       VARCHAR(20)  PRIMARY KEY,
    Activity_ID       VARCHAR(20),
    Vendor_ID         VARCHAR(20),
    Description       VARCHAR(150),
    Quantity          INT,
    PO_Number         VARCHAR(50),
    Order_Date        DATE,
    Expected_Delivery DATE,
    Actual_Delivery   DATE,
    Status            VARCHAR(30),
    CONSTRAINT fk_materials_activity FOREIGN KEY (Activity_ID) REFERENCES WBS_ACTIVITIES(Activity_ID),
    CONSTRAINT fk_materials_vendor   FOREIGN KEY (Vendor_ID)   REFERENCES VENDORS(Vendor_ID)
);

Notes
─────
• Material_ID is a user-supplied VARCHAR primary key (not auto-generated).
• Activity_ID and Vendor_ID are FK dropdowns loaded from their parent tables.
• Quantity must be a positive integer.
• All three date fields are validated as YYYY-MM-DD.
• Order_Date ≤ Expected_Delivery constraint enforced in Python.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from db_connection import get_connection

STATUS_OPTIONS = ["Ordered", "In Transit", "Delivered", "Cancelled", "On Hold"]
DATE_FMT       = "%Y-%m-%d"


class MaterialsForm(tk.Frame):

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
        self._selected_id = None        # Material_ID of currently selected row
        self._build_ui()
        self.load_materials()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(
            self, text="Materials Management", bg=self.BG, fg=self.ACCENT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 6))

        # Search bar
        search_frame = tk.Frame(self, bg=self.BG)
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 6))
        tk.Label(search_frame, text="Search:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_materials())
        tk.Entry(
            search_frame, textvariable=self.search_var,
            bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
            relief=tk.FLAT, font=("Segoe UI", 10), width=30
        ).pack(side=tk.LEFT)

        # Entry panel – two columns of fields
        panel = tk.LabelFrame(
            self, text=" Material Details ", bg=self.PANEL_BG, fg=self.ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, relief=tk.GROOVE
        )
        panel.pack(fill=tk.X, padx=20, pady=6)

        # Field definitions: (label, widget_type, options/None)
        fields = [
            ("Material ID *",          "entry",    None),
            ("Description",            "entry",    None),
            ("Activity ID",            "combo",    []),   # populated from DB
            ("Vendor ID",              "combo",    []),   # populated from DB
            ("Quantity",               "entry",    None),
            ("PO Number",              "entry",    None),
            ("Order Date (YYYY-MM-DD)",           "entry", None),
            ("Expected Delivery (YYYY-MM-DD)",    "entry", None),
            ("Actual Delivery (YYYY-MM-DD)",      "entry", None),
            ("Status",                 "combo",    STATUS_OPTIONS),
        ]

        self._entries = {}
        # Lay out in two columns (5 rows each)
        left_fields  = fields[:5]
        right_fields = fields[5:]

        for col_offset, field_group in enumerate([left_fields, right_fields]):
            for row_idx, (lbl, wtype, opts) in enumerate(field_group):
                tk.Label(panel, text=lbl, bg=self.PANEL_BG, fg=self.FG,
                         font=("Segoe UI", 10), anchor="w").grid(
                    row=row_idx, column=col_offset * 2, sticky="w", padx=14, pady=5
                )
                if wtype == "combo":
                    widget = ttk.Combobox(
                        panel, values=opts or [], state="readonly",
                        font=("Segoe UI", 10), width=22
                    )
                    if opts:
                        widget.set(opts[0])
                else:
                    widget = tk.Entry(
                        panel, bg=self.ENTRY_BG, fg=self.FG,
                        insertbackground=self.FG, relief=tk.FLAT,
                        font=("Segoe UI", 10), width=24
                    )
                widget.grid(row=row_idx, column=col_offset * 2 + 1,
                            padx=14, pady=5, sticky="w")
                self._entries[lbl] = widget

        # Populate FK dropdowns
        self._load_activity_ids()
        self._load_vendor_ids()

        # Button row
        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(pady=8)
        for text, cmd in [
            ("➕ Add",    self.add_material),
            ("✏️ Update",  self.update_material),
            ("🗑️ Delete",  self.delete_material),
            ("🔄 Refresh", self.load_materials),
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

        cols = ("Material ID", "Description", "Activity ID", "Vendor ID",
                "Qty", "PO Number", "Order Date", "Exp. Delivery",
                "Act. Delivery", "Status")
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
            "Material ID": 90, "Description": 180, "Activity ID": 90,
            "Vendor ID": 80, "Qty": 55, "PO Number": 90,
            "Order Date": 95, "Exp. Delivery": 100,
            "Act. Delivery": 100, "Status": 90,
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

    # ── FK dropdown loaders ───────────────────────────────────────────────────
    def _load_activity_ids(self):
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT Activity_ID FROM WBS_ACTIVITIES ORDER BY Activity_ID")
            ids = [r[0] for r in cursor.fetchall()]
            conn.close()
            self._entries["Activity ID"]["values"] = ids
            if ids:
                self._entries["Activity ID"].set(ids[0])
        except Exception:
            pass   # table may not exist yet; leave dropdown empty

    def _load_vendor_ids(self):
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT Vendor_ID FROM VENDORS ORDER BY Vendor_ID")
            ids = [r[0] for r in cursor.fetchall()]
            conn.close()
            self._entries["Vendor ID"]["values"] = ids
            if ids:
                self._entries["Vendor ID"].set(ids[0])
        except Exception:
            pass

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get(self, label: str) -> str:
        w = self._entries[label]
        return w.get().strip()

    def _none_if_empty(self, val: str):
        return val if val else None

    def _validate_date(self, val: str, label: str) -> bool:
        if val:
            try:
                datetime.strptime(val, DATE_FMT)
            except ValueError:
                messagebox.showwarning(
                    "Validation",
                    f"'{label}' must be YYYY-MM-DD (e.g. 2025-06-30)."
                )
                return False
        return True

    def _validate_inputs(self) -> bool:
        if not self._get("Material ID *"):
            messagebox.showwarning("Validation", "Material ID is required.")
            return False

        qty = self._get("Quantity")
        if qty:
            try:
                if int(qty) < 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Validation",
                                       "Quantity must be a non-negative integer.")
                return False

        for lbl in ("Order Date (YYYY-MM-DD)",
                    "Expected Delivery (YYYY-MM-DD)",
                    "Actual Delivery (YYYY-MM-DD)"):
            if not self._validate_date(self._get(lbl), lbl):
                return False

        order = self._get("Order Date (YYYY-MM-DD)")
        exp   = self._get("Expected Delivery (YYYY-MM-DD)")
        if order and exp and order > exp:
            messagebox.showwarning("Validation",
                                   "Order Date cannot be after Expected Delivery.")
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
        # v = (Material_ID, Description, Activity_ID, Vendor_ID, Qty, PO_Number,
        #       Order_Date, Exp_Delivery, Act_Delivery, Status)
        self._selected_id = v[0]

        mapping = {
            "Material ID *":                    v[0],
            "Description":                      v[1],
            "Activity ID":                      v[2],
            "Vendor ID":                        v[3],
            "Quantity":                         v[4],
            "PO Number":                        v[5],
            "Order Date (YYYY-MM-DD)":          v[6],
            "Expected Delivery (YYYY-MM-DD)":   v[7],
            "Actual Delivery (YYYY-MM-DD)":     v[8],
            "Status":                           v[9],
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
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def load_materials(self, *_):
        for row in self.tree.get_children():
            self.tree.delete(row)

        keyword = self.search_var.get().strip()
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            if keyword:
                cursor.execute(
                    "SELECT Material_ID, Description, Activity_ID, Vendor_ID, "
                    "Quantity, PO_Number, Order_Date, Expected_Delivery, "
                    "Actual_Delivery, Status "
                    "FROM MATERIALS "
                    "WHERE Material_ID LIKE ? OR Description LIKE ? "
                    "   OR PO_Number LIKE ? OR Status LIKE ? "
                    "ORDER BY Material_ID",
                    (f"%{keyword}%",) * 4
                )
            else:
                cursor.execute(
                    "SELECT Material_ID, Description, Activity_ID, Vendor_ID, "
                    "Quantity, PO_Number, Order_Date, Expected_Delivery, "
                    "Actual_Delivery, Status "
                    "FROM MATERIALS ORDER BY Material_ID"
                )

            def fmt_date(val):
                return str(val)[:10] if val else ""

            for row in cursor.fetchall():
                self.tree.insert("", tk.END, values=(
                    row[0] or "",           # Material_ID
                    row[1] or "",           # Description
                    row[2] or "",           # Activity_ID
                    row[3] or "",           # Vendor_ID
                    row[4] if row[4] is not None else "",  # Quantity
                    row[5] or "",           # PO_Number
                    fmt_date(row[6]),       # Order_Date
                    fmt_date(row[7]),       # Expected_Delivery
                    fmt_date(row[8]),       # Actual_Delivery
                    row[9] or "",           # Status
                ))
            conn.close()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to load materials:\n{exc}")

    def add_material(self):
        if not self._validate_inputs():
            return

        mat_id  = self._get("Material ID *")
        desc    = self._none_if_empty(self._get("Description"))
        act_id  = self._none_if_empty(self._get("Activity ID"))
        ven_id  = self._none_if_empty(self._get("Vendor ID"))
        qty_str = self._get("Quantity")
        qty     = int(qty_str) if qty_str else None
        po      = self._none_if_empty(self._get("PO Number"))
        ord_dt  = self._none_if_empty(self._get("Order Date (YYYY-MM-DD)"))
        exp_dt  = self._none_if_empty(self._get("Expected Delivery (YYYY-MM-DD)"))
        act_dt  = self._none_if_empty(self._get("Actual Delivery (YYYY-MM-DD)"))
        status  = self._get("Status")

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO MATERIALS "
                "(Material_ID, Description, Activity_ID, Vendor_ID, Quantity, "
                " PO_Number, Order_Date, Expected_Delivery, Actual_Delivery, Status) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (mat_id, desc, act_id, ven_id, qty, po,
                 ord_dt, exp_dt, act_dt, status)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success",
                                f"Material '{mat_id}' added successfully.")
            self.clear_fields()
            self.load_materials()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to add material:\n{exc}")

    def update_material(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection",
                                   "Please select a material from the list first.")
            return
        if not self._validate_inputs():
            return

        desc    = self._none_if_empty(self._get("Description"))
        act_id  = self._none_if_empty(self._get("Activity ID"))
        ven_id  = self._none_if_empty(self._get("Vendor ID"))
        qty_str = self._get("Quantity")
        qty     = int(qty_str) if qty_str else None
        po      = self._none_if_empty(self._get("PO Number"))
        ord_dt  = self._none_if_empty(self._get("Order Date (YYYY-MM-DD)"))
        exp_dt  = self._none_if_empty(self._get("Expected Delivery (YYYY-MM-DD)"))
        act_dt  = self._none_if_empty(self._get("Actual Delivery (YYYY-MM-DD)"))
        status  = self._get("Status")

        if not messagebox.askyesno("Confirm Update",
                                   f"Update Material ID '{self._selected_id}'?"):
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE MATERIALS SET "
                "Description=?, Activity_ID=?, Vendor_ID=?, Quantity=?, "
                "PO_Number=?, Order_Date=?, Expected_Delivery=?, "
                "Actual_Delivery=?, Status=? "
                "WHERE Material_ID=?",
                (desc, act_id, ven_id, qty, po,
                 ord_dt, exp_dt, act_dt, status, self._selected_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Material updated successfully.")
            self.clear_fields()
            self.load_materials()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to update material:\n{exc}")

    def delete_material(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection",
                                   "Please select a material from the list first.")
            return

        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete Material ID "
                                   f"'{self._selected_id}'?\nThis cannot be undone."):
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM MATERIALS WHERE Material_ID=?",
                           (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Material deleted successfully.")
            self.clear_fields()
            self.load_materials()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to delete material:\n{exc}")


# ── Stand-alone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Refinery Project – Materials Form")
    root.geometry("1100x680")
    root.configure(bg="#1e2327")
    MaterialsForm(root)
    root.mainloop()
