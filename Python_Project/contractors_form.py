"""
contractors_form.py
───────────────────
Full CRUD Tkinter form for the CONTRACTORS table in Refinery_Project.

Table schema
────────────
CREATE TABLE CONTRACTORS (
    Contractor_ID      VARCHAR(20)  PRIMARY KEY,
    Contractor_Name    VARCHAR(150) NOT NULL,
    Contract_Number    VARCHAR(50),
    Performance_Rating VARCHAR(20)
);

Notes
─────
• Contractor_ID is a user-supplied VARCHAR primary key (not auto-generated).
• Performance_Rating uses a fixed Combobox to prevent free-text inconsistency.
• No FK dependencies — this table can be populated independently.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from db_connection import get_connection

RATING_OPTIONS = ["Excellent", "Good", "Satisfactory", "Poor", "Under Review"]


class ContractorsForm(tk.Frame):

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
        self._selected_id = None        # Contractor_ID of currently selected row
        self._build_ui()
        self.load_contractors()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(
            self, text="Contractors Management", bg=self.BG, fg=self.ACCENT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 6))

        # Search bar
        search_frame = tk.Frame(self, bg=self.BG)
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 6))
        tk.Label(search_frame, text="Search:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_contractors())
        tk.Entry(
            search_frame, textvariable=self.search_var,
            bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
            relief=tk.FLAT, font=("Segoe UI", 10), width=30
        ).pack(side=tk.LEFT)

        # Entry panel
        panel = tk.LabelFrame(
            self, text=" Contractor Details ", bg=self.PANEL_BG, fg=self.ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, relief=tk.GROOVE
        )
        panel.pack(fill=tk.X, padx=20, pady=6)

        fields = [
            ("Contractor ID *",   "entry"),
            ("Contractor Name *", "entry"),
            ("Contract Number",   "entry"),
            ("Performance Rating","combo"),
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
            ("➕ Add",    self.add_contractor),
            ("✏️ Update",  self.update_contractor),
            ("🗑️ Delete",  self.delete_contractor),
            ("🔄 Refresh", self.load_contractors),
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

        cols = ("Contractor ID", "Contractor Name", "Contract Number", "Performance Rating")
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
            "Contractor ID": 120, "Contractor Name": 280,
            "Contract Number": 160, "Performance Rating": 150
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
        w = self._entries[label]
        return w.get().strip()

    def _none_if_empty(self, val: str):
        return val if val else None

    def _validate_inputs(self) -> bool:
        if not self._get("Contractor ID *"):
            messagebox.showwarning("Validation", "Contractor ID is required.")
            return False
        if not self._get("Contractor Name *"):
            messagebox.showwarning("Validation", "Contractor Name is required.")
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
        # v = (Contractor_ID, Contractor_Name, Contract_Number, Performance_Rating)
        self._selected_id = v[0]

        mapping = {
            "Contractor ID *":    v[0],
            "Contractor Name *":  v[1],
            "Contract Number":    v[2],
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
    def load_contractors(self, *_):
        for row in self.tree.get_children():
            self.tree.delete(row)

        keyword = self.search_var.get().strip()
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            if keyword:
                cursor.execute(
                    "SELECT Contractor_ID, Contractor_Name, Contract_Number, "
                    "Performance_Rating FROM CONTRACTORS "
                    "WHERE Contractor_ID LIKE ? OR Contractor_Name LIKE ? "
                    "   OR Contract_Number LIKE ? OR Performance_Rating LIKE ? "
                    "ORDER BY Contractor_ID",
                    (f"%{keyword}%",) * 4
                )
            else:
                cursor.execute(
                    "SELECT Contractor_ID, Contractor_Name, Contract_Number, "
                    "Performance_Rating FROM CONTRACTORS ORDER BY Contractor_ID"
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
                                 f"Failed to load contractors:\n{exc}")

    def add_contractor(self):
        if not self._validate_inputs():
            return

        con_id  = self._get("Contractor ID *")
        name    = self._get("Contractor Name *")
        con_num = self._none_if_empty(self._get("Contract Number"))
        rating  = self._get("Performance Rating")

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO CONTRACTORS "
                "(Contractor_ID, Contractor_Name, Contract_Number, Performance_Rating) "
                "VALUES (?, ?, ?, ?)",
                (con_id, name, con_num, rating)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success",
                                f"Contractor '{name}' added successfully.")
            self.clear_fields()
            self.load_contractors()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to add contractor:\n{exc}")

    def update_contractor(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection",
                                   "Please select a contractor from the list first.")
            return
        if not self._validate_inputs():
            return

        name    = self._get("Contractor Name *")
        con_num = self._none_if_empty(self._get("Contract Number"))
        rating  = self._get("Performance Rating")

        if not messagebox.askyesno("Confirm Update",
                                   f"Update Contractor ID '{self._selected_id}'?"):
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE CONTRACTORS "
                "SET Contractor_Name=?, Contract_Number=?, Performance_Rating=? "
                "WHERE Contractor_ID=?",
                (name, con_num, rating, self._selected_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Contractor updated successfully.")
            self.clear_fields()
            self.load_contractors()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to update contractor:\n{exc}")

    def delete_contractor(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection",
                                   "Please select a contractor from the list first.")
            return

        name = self._get("Contractor Name *")
        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete Contractor ID "
                                   f"'{self._selected_id}' – '{name}'?\n"
                                   f"This cannot be undone."):
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM CONTRACTORS WHERE Contractor_ID=?",
                           (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Contractor deleted successfully.")
            self.clear_fields()
            self.load_contractors()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to delete contractor:\n{exc}")


# ── Stand-alone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Refinery Project – Contractors Form")
    root.geometry("900x580")
    root.configure(bg="#1e2327")
    ContractorsForm(root)
    root.mainloop()
