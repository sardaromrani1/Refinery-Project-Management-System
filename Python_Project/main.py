"""
main.py
───────
Entry point for the Refinery Project desktop app.
Sidebar navigation switches between module forms.
"""

import tkinter as tk
from tkinter import messagebox

from projects_form    import ProjectsForm
from materials_form   import MaterialsForm
from contractors_form import ContractorsForm
from vendors_form     import VendorsForm
from costs_form       import CostsForm


class RefineryApp(tk.Tk):

    BG      = "#1e2327"
    SIDE_BG = "#161b1f"
    FG      = "#e0e0e0"
    ACCENT  = "#00b4d8"
    SEL_BG  = "#00b4d8"
    BTN_FG  = "#ffffff"

    MODULES = [
        ("Projects",    ProjectsForm),
        ("Materials",   MaterialsForm),
        ("Contractors", ContractorsForm),
        ("Vendors",     VendorsForm),
        ("Costs",       CostsForm),
        # Add more here as you build them:
        # ("WBS Activities", WbsForm),
        # ("Equipment",      EquipmentForm),
        # ("Inspections",    InspectionsForm),
        # ("Resources",      ResourcesForm),
        # ("Permits",        PermitsForm),
        # ("Documents",      DocumentsForm),
    ]

    def __init__(self):
        super().__init__()
        self.title("Refinery Project Management System")
        self.geometry("1150x700")
        self.minsize(950, 600)
        self.configure(bg=self.BG)
        self._current_frame = None
        self._nav_buttons   = {}
        self._build_layout()
        self._load_module(self.MODULES[0])

    def _build_layout(self):
        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = tk.Frame(self, bg=self.SIDE_BG, width=180)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar, text="⚙ Refinery\nProject", bg=self.SIDE_BG, fg=self.ACCENT,
            font=("Segoe UI", 13, "bold"), pady=22
        ).pack(fill=tk.X)

        tk.Frame(sidebar, bg=self.ACCENT, height=1).pack(fill=tk.X, padx=12)

        for name, form_cls in self.MODULES:
            btn = tk.Button(
                sidebar, text=name,
                bg=self.SIDE_BG, fg=self.FG,
                activebackground=self.SEL_BG, activeforeground=self.BTN_FG,
                relief=tk.FLAT, font=("Segoe UI", 10), anchor="w",
                padx=18, cursor="hand2",
                command=lambda n=name, c=form_cls: self._load_module((n, c))
            )
            btn.pack(fill=tk.X, pady=1)
            self._nav_buttons[name] = btn

        tk.Frame(sidebar, bg=self.ACCENT, height=1).pack(
            fill=tk.X, padx=12, side=tk.BOTTOM, pady=4)
        tk.Label(
            sidebar, text="v1.0", bg=self.SIDE_BG,
            fg="#555e66", font=("Segoe UI", 8)
        ).pack(side=tk.BOTTOM)

        # ── Main content area ─────────────────────────────────────────────────
        self.content = tk.Frame(self, bg=self.BG)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _load_module(self, module_tuple):
        name, form_cls = module_tuple

        for n, btn in self._nav_buttons.items():
            btn.configure(
                bg=self.SEL_BG if n == name else self.SIDE_BG,
                fg=self.BTN_FG if n == name else self.FG,
                font=("Segoe UI", 10, "bold") if n == name else ("Segoe UI", 10)
            )

        if self._current_frame:
            self._current_frame.destroy()

        try:
            self._current_frame = form_cls(self.content)
        except Exception as exc:
            messagebox.showerror("Load Error",
                                 f"Could not load '{name}':\n{exc}")


if __name__ == "__main__":
    app = RefineryApp()
    app.mainloop()