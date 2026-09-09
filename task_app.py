import calendar
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

APP_NAME = "Pine's Journal"
DATE_UI = "%d/%m/%Y"
DATE_DB = "%Y-%m-%d"


def data_dir():
    if os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA") or Path.home())
        path = root / APP_NAME
    else:
        path = Path.home() / ".pines_journal"
    path.mkdir(parents=True, exist_ok=True)
    return path


DB_PATH = data_dir() / "tarefas.db"


def parse_date(value):
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_UI).date()
    except ValueError:
        return None


class Repository:
    def __init__(self):
        with sqlite3.connect(DB_PATH) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    due_date TEXT,
                    completed INTEGER NOT NULL DEFAULT 0,
                    completed_at TEXT,
                    created_at TEXT NOT NULL
                )
            """)

    def connect(self):
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        return con

    def purge(self):
        cutoff = (datetime.now() - timedelta(days=7)).isoformat(timespec="seconds")
        with self.connect() as con:
            con.execute("DELETE FROM tasks WHERE completed=1 AND completed_at IS NOT NULL AND completed_at<=?", (cutoff,))

    def all(self):
        self.purge()
        with self.connect() as con:
            return con.execute("""
                SELECT * FROM tasks
                ORDER BY completed ASC,
                         CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
                         due_date ASC, id DESC
            """).fetchall()

    def for_day(self, day):
        with self.connect() as con:
            return con.execute(
                "SELECT * FROM tasks WHERE due_date=? ORDER BY completed ASC, id DESC",
                (day.strftime(DATE_DB),),
            ).fetchall()

    def create(self, title, description, due_date):
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as con:
            con.execute(
                "INSERT INTO tasks(title,description,due_date,completed,completed_at,created_at) VALUES(?,?,?,0,NULL,?)",
                (title, description, due_date, now),
            )

    def set_completed(self, task_id, completed):
        completed_at = datetime.now().isoformat(timespec="seconds") if completed else None
        with self.connect() as con:
            con.execute("UPDATE tasks SET completed=?, completed_at=? WHERE id=?", (int(completed), completed_at, task_id))

    def delete(self, task_id):
        with self.connect() as con:
            con.execute("DELETE FROM tasks WHERE id=?", (task_id,))


class TaskDialog(tk.Toplevel):
    def __init__(self, app, preset_date=None):
        super().__init__(app)
        self.app = app
        self.title("Nova tarefa")
        self.geometry("400x330")
        self.resizable(False, False)
        self.transient(app)
        body = tk.Frame(self, padx=16, pady=16)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="Nome", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.title_entry = tk.Entry(body, font=("Segoe UI", 10))
        self.title_entry.pack(fill="x", pady=(4, 10))
        tk.Label(body, text="Descrição", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.desc = tk.Text(body, height=6, font=("Segoe UI", 9))
        self.desc.pack(fill="x", pady=(4, 10))
        tk.Label(body, text="Data de conclusão (dd/mm/aaaa)", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.date_entry = tk.Entry(body, font=("Segoe UI", 10))
        self.date_entry.pack(fill="x", pady=(4, 14))
        if preset_date:
            self.date_entry.insert(0, preset_date.strftime(DATE_UI))
        tk.Button(body, text="Salvar tarefa", command=self.save).pack(anchor="e")
        self.title_entry.focus_set()

    def save(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Tarefa", "Informe o nome da tarefa.", parent=self)
            return
        raw = self.date_entry.get().strip()
        parsed = parse_date(raw) if raw else None
        if raw and not parsed:
            messagebox.showwarning("Data", "Use o formato dd/mm/aaaa.", parent=self)
            return
        due = parsed.strftime(DATE_DB) if parsed else None
        self.app.repo.create(title, self.desc.get("1.0", "end").strip(), due)
        self.destroy()
        self.app.refresh_current()


class App(tk.Tk):
    MONTHS = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

    def __init__(self):
        super().__init__()
        self.repo = Repository()
        self.title(APP_NAME)
        self.geometry("520x650")
        self.resizable(False, False)
        self.configure(bg="#eee9dd")
        today = date.today()
        self.year = today.year
        self.month = today.month
        self.current = "list"
        self.build_shell()
        self.show_list()

    def build_shell(self):
        header = tk.Frame(self, bg="#6b1733", height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=APP_NAME, bg="#6b1733", fg="white", font=("Georgia", 14, "bold")).pack(side="left", padx=18)
        tk.Button(header, text="+ Nova", command=lambda: TaskDialog(self), bg="#8d2141", fg="white", relief="flat").pack(side="right", padx=14, pady=13)

        nav = tk.Frame(self, bg="#fffdf3", height=50)
        nav.pack(fill="x")
        self.list_btn = tk.Button(nav, text="Lista", command=self.show_list, relief="flat")
        self.list_btn.pack(side="left", fill="both", expand=True)
        self.cal_btn = tk.Button(nav, text="Calendário", command=self.show_calendar, relief="flat")
        self.cal_btn.pack(side="left", fill="both", expand=True)

        self.content = tk.Frame(self, bg="#eee9dd")
        self.content.pack(fill="both", expand=True)

    def clear(self):
        for child in self.content.winfo_children():
            child.destroy()

    def refresh_current(self):
        self.show_calendar() if self.current == "calendar" else self.show_list()

    def show_list(self):
        self.current = "list"
        self.clear()
        tasks = self.repo.all()
        tk.Label(self.content, text="Minhas tarefas", bg="#eee9dd", font=("Georgia", 12, "bold")).pack(anchor="w", padx=14, pady=(14, 8))
        wrap = tk.Frame(self.content, bg="#eee9dd")
        wrap.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        if not tasks:
            tk.Label(wrap, text="Nenhuma tarefa cadastrada", bg="#fffdf3", pady=30).pack(fill="x")
            return
        today = date.today().strftime(DATE_DB)
        for task in tasks:
            completed = bool(task["completed"])
            overdue = bool(task["due_date"] and not completed and task["due_date"] < today)
            bg = "#eef4e7" if completed else "#fffdf3"
            row = tk.Frame(wrap, bg=bg, bd=1, relief="solid")
            row.pack(fill="x", pady=3)
            var = tk.BooleanVar(value=completed)
            tk.Checkbutton(row, variable=var, bg=bg, command=lambda tid=task["id"], v=var: self.toggle(tid, v.get())).pack(side="left", padx=8, pady=8)
            tk.Label(row, text=task["title"], bg=bg, font=("Segoe UI", 9, "bold"), anchor="w").pack(side="left", fill="x", expand=True)
            if task["due_date"]:
                label = datetime.strptime(task["due_date"], DATE_DB).strftime(DATE_UI)
                tk.Label(row, text=("! " if overdue else "") + label, bg=bg, fg="#b33b3b" if overdue else "#7d746d").pack(side="right", padx=8)

    def toggle(self, task_id, completed):
        self.repo.set_completed(task_id, completed)
        self.refresh_current()

    def show_calendar(self):
        self.current = "calendar"
        self.clear()
        top = tk.Frame(self.content, bg="#eee9dd")
        top.pack(fill="x", padx=14, pady=12)
        tk.Button(top, text="‹", command=lambda: self.change_month(-1)).pack(side="left")
        tk.Label(top, text=f"{self.MONTHS[self.month]} {self.year}", bg="#eee9dd", font=("Georgia", 11, "bold")).pack(side="left", expand=True)
        tk.Button(top, text="›", command=lambda: self.change_month(1)).pack(side="right")

        grid = tk.Frame(self.content, bg="#fffdf3", bd=1, relief="solid")
        grid.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        for c in range(7):
            grid.grid_columnconfigure(c, weight=1, uniform="day")
        for r in range(7):
            grid.grid_rowconfigure(r, weight=1, uniform="week")
        for c, label in enumerate(["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]):
            tk.Label(grid, text=label, bg="#fffdf3", font=("Segoe UI", 7, "bold")).grid(row=0, column=c, sticky="nsew")

        counts = {}
        for t in self.repo.all():
            if t["due_date"] and t["due_date"].startswith(f"{self.year:04d}-{self.month:02d}-"):
                counts[t["due_date"]] = counts.get(t["due_date"], 0) + 1

        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(self.year, self.month)
        for r, week in enumerate(weeks, start=1):
            for c, day_num in enumerate(week):
                cell = tk.Frame(grid, bg="#fffdf3", bd=1, relief="solid")
                cell.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                if day_num:
                    day_obj = date(self.year, self.month, day_num)
                    tk.Label(cell, text=str(day_num), bg="#fffdf3").pack(anchor="nw", padx=5, pady=4)
                    count = counts.get(day_obj.strftime(DATE_DB), 0)
                    if count:
                        tk.Label(cell, text=f"• {count}", bg="#fffdf3", fg="#8d2141").pack(anchor="nw", padx=5)
                    for widget in (cell, *cell.winfo_children()):
                        widget.bind("<Button-1>", lambda e, d=day_obj: self.open_day(d))

    def change_month(self, delta):
        m = self.month - 1 + delta
        self.year += m // 12
        self.month = m % 12 + 1
        self.show_calendar()

    def open_day(self, day_obj):
        win = tk.Toplevel(self)
        win.title(day_obj.strftime(DATE_UI))
        win.geometry("400x420")
        tk.Button(win, text="+ Nova", command=lambda: TaskDialog(self, preset_date=day_obj)).pack(anchor="e", padx=12, pady=12)
        body = tk.Frame(win)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        tasks = self.repo.for_day(day_obj)
        if not tasks:
            tk.Label(body, text="Nenhuma tarefa neste dia").pack(pady=30)
        else:
            for task in tasks:
                tk.Label(body, text=task["title"], anchor="w").pack(fill="x", pady=3)


if __name__ == "__main__":
    App().mainloop()
