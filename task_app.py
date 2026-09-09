import os
import sqlite3
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

APP_NAME = "Pine's Journal"


def data_dir():
    if os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA") or Path.home())
        path = root / APP_NAME
    else:
        path = Path.home() / ".pines_journal"
    path.mkdir(parents=True, exist_ok=True)
    return path


DB_PATH = data_dir() / "tarefas.db"


class Repository:
    def __init__(self):
        with sqlite3.connect(DB_PATH) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    completed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

    def all(self):
        with sqlite3.connect(DB_PATH) as con:
            con.row_factory = sqlite3.Row
            return con.execute(
                "SELECT * FROM tasks ORDER BY completed ASC, id DESC"
            ).fetchall()

    def create(self, title, description):
        with sqlite3.connect(DB_PATH) as con:
            con.execute(
                "INSERT INTO tasks(title, description, completed, created_at) VALUES(?,?,0,?)",
                (title, description, datetime.now().isoformat(timespec="seconds")),
            )

    def set_completed(self, task_id, completed):
        with sqlite3.connect(DB_PATH) as con:
            con.execute("UPDATE tasks SET completed=? WHERE id=?", (int(completed), task_id))

    def delete(self, task_id):
        with sqlite3.connect(DB_PATH) as con:
            con.execute("DELETE FROM tasks WHERE id=?", (task_id,))


class TaskDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Nova tarefa")
        self.geometry("380x280")
        self.resizable(False, False)
        self.transient(app)

        body = tk.Frame(self, padx=16, pady=16)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="Nome da tarefa", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.title_entry = tk.Entry(body, font=("Segoe UI", 10))
        self.title_entry.pack(fill="x", pady=(4, 12))
        tk.Label(body, text="Descrição", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.desc = tk.Text(body, height=6, font=("Segoe UI", 9))
        self.desc.pack(fill="both", expand=True, pady=(4, 12))
        tk.Button(body, text="Salvar", command=self.save).pack(anchor="e")
        self.title_entry.focus_set()

    def save(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Tarefa", "Informe o nome da tarefa.", parent=self)
            return
        self.app.repo.create(title, self.desc.get("1.0", "end").strip())
        self.destroy()
        self.app.refresh()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.repo = Repository()
        self.title(APP_NAME)
        self.geometry("500x600")
        self.minsize(420, 480)
        self.configure(bg="#eee9dd")
        self.build()
        self.refresh()

    def build(self):
        header = tk.Frame(self, bg="#6b1733", height=58)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=APP_NAME, bg="#6b1733", fg="white", font=("Georgia", 14, "bold")).pack(side="left", padx=18)
        tk.Button(header, text="+ Nova", command=lambda: TaskDialog(self), bg="#8d2141", fg="white", relief="flat").pack(side="right", padx=14, pady=13)

        self.list_frame = tk.Frame(self, bg="#eee9dd")
        self.list_frame.pack(fill="both", expand=True, padx=14, pady=14)

    def refresh(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        tasks = self.repo.all()
        if not tasks:
            card = tk.Frame(self.list_frame, bg="#fffdf3", bd=1, relief="solid")
            card.pack(fill="x")
            tk.Label(card, text="Nenhuma tarefa cadastrada", bg="#fffdf3", font=("Segoe UI", 10, "bold")).pack(pady=28)
            return

        for task in tasks:
            row = tk.Frame(self.list_frame, bg="#fffdf3", bd=1, relief="solid")
            row.pack(fill="x", pady=3)
            var = tk.BooleanVar(value=bool(task["completed"]))
            tk.Checkbutton(
                row, variable=var, bg="#fffdf3",
                command=lambda tid=task["id"], v=var: self.toggle(tid, v.get())
            ).pack(side="left", padx=8, pady=8)
            text = task["title"] + (" ✓" if task["completed"] else "")
            tk.Label(row, text=text, bg="#fffdf3", anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left", fill="x", expand=True)
            tk.Button(row, text="Excluir", relief="flat", command=lambda tid=task["id"]: self.delete(tid)).pack(side="right", padx=8)

    def toggle(self, task_id, completed):
        self.repo.set_completed(task_id, completed)
        self.refresh()

    def delete(self, task_id):
        if messagebox.askyesno("Excluir", "Excluir esta tarefa?", parent=self):
            self.repo.delete(task_id)
            self.refresh()


if __name__ == "__main__":
    App().mainloop()
