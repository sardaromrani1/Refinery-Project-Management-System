"""
projects_form.py
────────────────
Full CRUD Tkinter form for the PROJECTT table in Refinery_Project.

Table schema
────────────
CREATE TABLE PROJECTT (
    Project_ID   INT IDENTITY(1,1) PRIMARY KEY,
    Project_Name VARCHAR(150) NOT NULL,
    Start_Date   DATE,
    End_Date     DATE,
    Status       VARCHAR(30)
);

Fixes applied vs. the original attempt
────────────────────────────────────────
1. Tuple bug  – row values accessed with row[index], not the whole tuple.
2. Input validation  – required field and date-format checks before any DB call.
3. Field clearing  – all entry widgets reset after every successful operation.
4. Confirmation dialogs  – Update / Delete now ask "Are you sure?" first.
5. Error handling  – every DB call is wrapped in try/except with user-visible messages.
6. Treeview selection  – clicking a row populates the form for easy edit/delete.
7. Status dropdown  – uses ttk.Combobox with fixed choices to prevent typos.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from db_connection import get_connection

# ── Allowed status values (must match your CHECK constraint if any) ──────────
STATUS_OPTIONS = ["Planning", "In Progress", "On Hold", "Completed", "Cancelled"]
DATE_FMT       = "%Y-%m-%d"   # format expected by SQL Server DATE columns


# ────────────────────────────────────────────────────────────────────────────
class ProjectsForm(tk.Frame):
    """
    A dark-themed frame with:
      • A data-entry panel (top/left)
      • CRUD buttons
      • A searchable, sortable Treeview listing all projects
    """

    # ── colours ──────────────────────────────────────────────────────────────
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
        self._selected_id = None          # Project_ID of the currently selected row
        self._build_ui()
        self.load_projects()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        # ── Title ─────────────────────────────────────────────────────────────
        tk.Label(
            self, text="Projects Management", bg=self.BG, fg=self.ACCENT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 6))

        # ── Search bar ────────────────────────────────────────────────────────
        search_frame = tk.Frame(self, bg=self.BG)
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 6))

        tk.Label(search_frame, text="Search:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_projects())
        tk.Entry(
            search_frame, textvariable=self.search_var,
            bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
            relief=tk.FLAT, font=("Segoe UI", 10), width=30
        ).pack(side=tk.LEFT)

        # ── Entry panel ───────────────────────────────────────────────────────
        panel = tk.LabelFrame(
            self, text=" Project Details ", bg=self.PANEL_BG, fg=self.ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, relief=tk.GROOVE
        )
        panel.pack(fill=tk.X, padx=20, pady=6)

        labels = ["Project Name *", "Start Date (YYYY-MM-DD)", "End Date (YYYY-MM-DD)", "Status"]
        self._entries = {}

        for i, lbl in enumerate(labels):
            tk.Label(panel, text=lbl, bg=self.PANEL_BG, fg=self.FG,
                     font=("Segoe UI", 10), anchor="w").grid(
                row=i, column=0, sticky="w", padx=14, pady=5
            )

            if lbl == "Status":
                widget = ttk.Combobox(
                    panel, values=STATUS_OPTIONS, state="readonly",
                    font=("Segoe UI", 10), width=28
                )
                widget.set(STATUS_OPTIONS[0])
            else:
                widget = tk.Entry(
                    panel, bg=self.ENTRY_BG, fg=self.FG,
                    insertbackground=self.FG, relief=tk.FLAT,
                    font=("Segoe UI", 10), width=30
                )
            widget.grid(row=i, column=1, padx=14, pady=5, sticky="w")
            self._entries[lbl] = widget

        # ── Button row ────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(pady=8)

        buttons = [
            ("➕ Add",    self.add_project),
            ("✏️ Update",  self.update_project),
            ("🗑️ Delete",  self.delete_project),
            ("🔄 Refresh", self.load_projects),
            ("✖ Clear",   self.clear_fields),
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

        cols = ("ID", "Project Name", "Start Date", "End Date", "Status")
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

        col_widths = {"ID": 55, "Project Name": 260, "Start Date": 110,
                      "End Date": 110, "Status": 120}
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
    def _get_field(self, label: str) -> str:
        widget = self._entries[label]
        if isinstance(widget, ttk.Combobox):
            return widget.get().strip()
        return widget.get().strip()

    def _validate_inputs(self) -> bool:
        name = self._get_field("Project Name *")
        if not name:
            messagebox.showwarning("Validation", "Project Name is required.")
            return False

        for lbl in ("Start Date (YYYY-MM-DD)", "End Date (YYYY-MM-DD)"):
            val = self._get_field(lbl)
            if val:
                try:
                    datetime.strptime(val, DATE_FMT)
                except ValueError:
                    messagebox.showwarning(
                        "Validation",
                        f"'{lbl}' must be in YYYY-MM-DD format (e.g. 2025-01-31)."
                    )
                    return False

        start = self._get_field("Start Date (YYYY-MM-DD)")
        end   = self._get_field("End Date (YYYY-MM-DD)")
        if start and end and start > end:
            messagebox.showwarning("Validation", "Start Date cannot be after End Date.")
            return False

        return True

    def _none_if_empty(self, val: str):
        return val if val else None

    def clear_fields(self):
        self._selected_id = None
        for lbl, widget in self._entries.items():
            if isinstance(widget, ttk.Combobox):
                widget.set(STATUS_OPTIONS[0])
            else:
                widget.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _on_row_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        # values = (ID, Project_Name, Start_Date, End_Date, Status)
        self._selected_id = int(values[0])

        self._entries["Project Name *"].delete(0, tk.END)
        self._entries["Project Name *"].insert(0, values[1])

        self._entries["Start Date (YYYY-MM-DD)"].delete(0, tk.END)
        self._entries["Start Date (YYYY-MM-DD)"].insert(0, values[2] if values[2] else "")

        self._entries["End Date (YYYY-MM-DD)"].delete(0, tk.END)
        self._entries["End Date (YYYY-MM-DD)"].insert(0, values[3] if values[3] else "")

        self._entries["Status"].set(values[4] if values[4] else STATUS_OPTIONS[0])

    def _sort_tree(self, col: str, reverse: bool):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def load_projects(self, *_):
        """Read all projects (filtered by search text) and populate the treeview."""
        for row in self.tree.get_children():
            self.tree.delete(row)

        keyword = self.search_var.get().strip()
        try:
            conn   = get_connection()
            cursor = conn.cursor()

            if keyword:
                cursor.execute(
                    "SELECT Project_ID, Project_Name, Start_Date, End_Date, Status "
                    "FROM PROJECTT "
                    "WHERE Project_Name LIKE ? OR Status LIKE ? "
                    "ORDER BY Project_ID DESC",
                    (f"%{keyword}%", f"%{keyword}%")
                )
            else:
                cursor.execute(
                    "SELECT Project_ID, Project_Name, Start_Date, End_Date, Status "
                    "FROM PROJECTT ORDER BY Project_ID DESC"
                )

            for row in cursor.fetchall():
                # row[0]=Project_ID  row[1]=Project_Name  row[2]=Start_Date
                # row[3]=End_Date    row[4]=Status
                start = str(row[2])[:10] if row[2] else ""
                end   = str(row[3])[:10] if row[3] else ""
                self.tree.insert("", tk.END, values=(row[0], row[1], start, end, row[4] or ""))

            conn.close()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load projects:\n{exc}")

    def add_project(self):
        if not self._validate_inputs():
            return

        name   = self._get_field("Project Name *")
        start  = self._none_if_empty(self._get_field("Start Date (YYYY-MM-DD)"))
        end    = self._none_if_empty(self._get_field("End Date (YYYY-MM-DD)"))
        status = self._get_field("Status")

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO PROJECTT (Project_Name, Start_Date, End_Date, Status) "
                "VALUES (?, ?, ?, ?)",
                (name, start, end, status)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Project '{name}' added successfully.")
            self.clear_fields()
            self.load_projects()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to add project:\n{exc}")

    def update_project(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select a project from the list first.")
            return
        if not self._validate_inputs():
            return

        name   = self._get_field("Project Name *")
        start  = self._none_if_empty(self._get_field("Start Date (YYYY-MM-DD)"))
        end    = self._none_if_empty(self._get_field("End Date (YYYY-MM-DD)"))
        status = self._get_field("Status")

        if not messagebox.askyesno("Confirm Update",
                                   f"Update Project ID {self._selected_id}?"):
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE PROJECTT "
                "SET Project_Name=?, Start_Date=?, End_Date=?, Status=? "
                "WHERE Project_ID=?",
                (name, start, end, status, self._selected_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Project updated successfully.")
            self.clear_fields()
            self.load_projects()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to update project:\n{exc}")

    def delete_project(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select a project from the list first.")
            return

        name = self._get_field("Project Name *")
        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete Project ID {self._selected_id}"
                                   f" – '{name}'?\nThis cannot be undone."):
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM PROJECTT WHERE Project_ID=?",
                           (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Project deleted successfully.")
            self.clear_fields()
            self.load_projects()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to delete project:\n{exc}")


# ── Stand-alone test runner ───────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Refinery Project – Projects Form")
    root.geometry("900x620")
    root.configure(bg="#1e2327")
    ProjectsForm(root)
    root.mainloop()