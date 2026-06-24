"""
vendors_form.py
───────────────
Full CRUD Tkinter form for the VENDORS table in Refinery_Project.

Table schema
────────────
CREATE TABLE VENDORS (
    Vendor_ID          VARCHAR(20)  PRIMARY KEY,
    Vendor_Name        VARCHAR(150) NOT NULL,
    Contact            VARCHAR(150),
    Performance_Rating VARCHAR(20)
);

Notes
─────
• Vendor_ID is a user-supplied VARCHAR primary key (not auto-generated).
• Performance_Rating uses a fixed Combobox to keep values consistent.
• No FK dependencies — this table can be populated independently.
  (MATERIALS references VENDORS, so populate VENDORS before MATERIALS.)
"""

import tkinter as tk
from tkinter import ttk, messagebox

from db_connection import get_connection

RATING_OPTIONS = ["Excellent", "Good", "Satisfactory", "Poor", "Under Review"]


class VendorsForm(tk.Frame):

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
        self._selected_id = None        # Vendor_ID of currently selected row
        self._build_ui()
        self.load_vendors()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(
            self, text="Vendors Management", bg=self.BG, fg=self.ACCENT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 6))

        # Search bar
        search_frame = tk.Frame(self, bg=self.BG)
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 6))
        tk.Label(search_frame, text="Search:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_vendors())
        tk.Entry(
            search_frame, textvariable=self.search_var,
            bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
            relief=tk.FLAT, font=("Segoe UI", 10), width=30
        ).pack(side=tk.LEFT)

        # Entry panel
        panel = tk.LabelFrame(
            self, text=" Vendor Details ", bg=self.PANEL_BG, fg=self.ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, relief=tk.GROOVE
        )
        panel.pack(fill=tk.X, padx=20, pady=6)

        fields = [
            ("Vendor ID *",        "entry"),
            ("Vendor Name *",      "entry"),
            ("Contact",            "entry"),
            ("Performance Rating", "combo"),
        ]

        self._entries = {}
        for i, (lbl, wtype) in enumerate(fields):
            tk.Label(panel, text=lbl, bg=self.PANEL_BG, fg=self.FG,
                     font=("Segoe UI", 10), anchor="w").grid(
                row=i, column=0, sticky="w", padx=14, pady=6
            )
            if wtype == "combo":
                widget = ttk.Combobox(
                    panel, values=RATING_OPTIONS, state="readonly",
                    font=("Segoe UI", 10), width=28
                )
                widget.set(RATING_OPTIONS[0])
            else:
                widget = tk.Entry(
                    panel, bg=self.ENTRY_BG, fg=self.FG,
                    insertbackground=self.FG, relief=tk.FLAT,
                    font=("Segoe UI", 10), width=30
                )
            widget.grid(row=i, column=1, padx=14, pady=6, sticky="w")
            self._entries[lbl] = widget

        # Button row
        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(pady=8)
        for text, cmd in [
            ("➕ Add",    self.add_vendor),
            ("✏️ Update",  self.update_vendor),
            ("🗑️ Delete",  self.delete_vendor),
            ("🔄 Refresh", self.load_vendors),
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

        cols = ("Vendor ID", "Vendor Name", "Contact", "Performance Rating")
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
            "Vendor ID": 110, "Vendor Name": 260,
            "Contact": 220, "Performance Rating": 150
        }
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_tree(c, False))
            self.tree.column(col, width=col_widths[col], anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get(self, label: str) -> str:
        return self._entries[label].get().strip()

    def _none_if_empty(self, val: str):
        return val if val else None

    def _validate_inputs(self) -> bool:
        if not self._get("Vendor ID *"):
            messagebox.showwarning("Validation", "Vendor ID is required.")
            return False
        if not self._get("Vendor Name *"):
            messagebox.showwarning("Validation", "Vendor Name is required.")
            return False
        return True

    def clear_fields(self):
        self._selected_id = None
        for lbl, widget in self._entries.items():
            if isinstance(widget, ttk.Combobox):
                widget.set(RATING_OPTIONS[0])
            else:
                widget.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _on_row_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        v = self.tree.item(selected[0], "values")
        # v = (Vendor_ID, Vendor_Name, Contact, Performance_Rating)
        self._selected_id = v[0]

        mapping = {
            "Vendor ID *":        v[0],
            "Vendor Name *":      v[1],
            "Contact":            v[2],
            "Performance Rating": v[3],
        }
        for lbl, val in mapping.items():
            w = self._entries[lbl]
            if isinstance(w, ttk.Combobox):
                w.set(val or RATING_OPTIONS[0])
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
    def load_vendors(self, *_):
        for row in self.tree.get_children():
            self.tree.delete(row)

        keyword = self.search_var.get().strip()
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            if keyword:
                cursor.execute(
                    "SELECT Vendor_ID, Vendor_Name, Contact, Performance_Rating "
                    "FROM VENDORS "
                    "WHERE Vendor_ID LIKE ? OR Vendor_Name LIKE ? "
                    "   OR Contact LIKE ? OR Performance_Rating LIKE ? "
                    "ORDER BY Vendor_ID",
                    (f"%{keyword}%",) * 4
                )
            else:
                cursor.execute(
                    "SELECT Vendor_ID, Vendor_Name, Contact, Performance_Rating "
                    "FROM VENDORS ORDER BY Vendor_ID"
                )
            for row in cursor.fetchall():
                self.tree.insert("", tk.END, values=(
                    row[0] or "",
                    row[1] or "",
                    row[2] or "",
                    row[3] or "",
                ))
            conn.close()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to load vendors:\n{exc}")

    def add_vendor(self):
        if not self._validate_inputs():
            return

        ven_id  = self._get("Vendor ID *")
        name    = self._get("Vendor Name *")
        contact = self._none_if_empty(self._get("Contact"))
        rating  = self._get("Performance Rating")

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO VENDORS "
                "(Vendor_ID, Vendor_Name, Contact, Performance_Rating) "
                "VALUES (?, ?, ?, ?)",
                (ven_id, name, contact, rating)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Vendor '{name}' added successfully.")
            self.clear_fields()
            self.load_vendors()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to add vendor:\n{exc}")

    def update_vendor(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection",
                                   "Please select a vendor from the list first.")
            return
        if not self._validate_inputs():
            return

        name    = self._get("Vendor Name *")
        contact = self._none_if_empty(self._get("Contact"))
        rating  = self._get("Performance Rating")

        if not messagebox.askyesno("Confirm Update",
                                   f"Update Vendor ID '{self._selected_id}'?"):
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE VENDORS "
                "SET Vendor_Name=?, Contact=?, Performance_Rating=? "
                "WHERE Vendor_ID=?",
                (name, contact, rating, self._selected_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Vendor updated successfully.")
            self.clear_fields()
            self.load_vendors()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to update vendor:\n{exc}")

    def delete_vendor(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection",
                                   "Please select a vendor from the list first.")
            return

        name = self._get("Vendor Name *")
        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete Vendor ID "
                                   f"'{self._selected_id}' – '{name}'?\n"
                                   f"This cannot be undone."):
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM VENDORS WHERE Vendor_ID=?",
                           (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Vendor deleted successfully.")
            self.clear_fields()
            self.load_vendors()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to delete vendor:\n{exc}")


# ── Stand-alone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Refinery Project – Vendors Form")
    root.geometry("900x580")
    root.configure(bg="#1e2327")
    VendorsForm(root)
    root.mainloop()
