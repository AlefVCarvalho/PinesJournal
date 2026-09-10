import calendar
import os
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageFont, ImageTk

APP_NAME = "Pine's Journal"
REGISTRY_VALUE = "PinesJournal"
DATE_FMT_DB = "%Y-%m-%d"
DATE_FMT_UI = "%d/%m/%Y"

TITLE_FONT = ("Georgia", 13, "bold")
SECTION_FONT = ("Georgia", 11, "bold")
SUBSECTION_FONT = ("Segoe UI", 9, "bold")
BODY_FONT = ("Segoe UI", 8)
BODY_FONT_LARGE = ("Segoe UI", 9)
SMALL_FONT = ("Segoe UI", 7)
BUTTON_FONT = ("Segoe UI", 7, "bold")

THEMES = {
    "Vinho": {
        "bg": "#eee9dd",
        "panel": "#fffdf3",
        "header": "#6b1733",
        "header_hover": "#7e2040",
        "text": "#322b2b",
        "muted": "#7d746d",
        "border": "#ddd4c3",
        "accent": "#8d2141",
        "accent_dark": "#65152e",
        "danger": "#b33b3b",
        "danger_bg": "#fff0eb",
        "success": "#5f7958",
        "success_bg": "#eef4e7",
        "today": "#fff1bd",
        "selected": "#f4e3ad",
        "neutral": "#eef0f3",
    },
    "Azul": {
        "bg": "#e9eef4",
        "panel": "#fbfdff",
        "header": "#24496d",
        "header_hover": "#2c5a86",
        "text": "#26313b",
        "muted": "#6f7983",
        "border": "#d6dde5",
        "accent": "#3f6f9f",
        "accent_dark": "#2d5277",
        "danger": "#b33b3b",
        "danger_bg": "#fff0eb",
        "success": "#4e7b69",
        "success_bg": "#edf7f2",
        "today": "#dcecff",
        "selected": "#cfe1f4",
        "neutral": "#edf1f5",
    },
    "Verde": {
        "bg": "#e9eee9",
        "panel": "#fbfdf9",
        "header": "#315b45",
        "header_hover": "#3b6b52",
        "text": "#29342d",
        "muted": "#718078",
        "border": "#d7dfd7",
        "accent": "#4f7b62",
        "accent_dark": "#385b47",
        "danger": "#b33b3b",
        "danger_bg": "#fff0eb",
        "success": "#4f7b62",
        "success_bg": "#edf7ef",
        "today": "#e4efc8",
        "selected": "#d8e7c4",
        "neutral": "#edf1ed",
    },
    "Grafite": {
        "bg": "#e8e8e8",
        "panel": "#fafafa",
        "header": "#303238",
        "header_hover": "#41444b",
        "text": "#26282d",
        "muted": "#757980",
        "border": "#d7d8db",
        "accent": "#555962",
        "accent_dark": "#393c43",
        "danger": "#b33b3b",
        "danger_bg": "#fff0eb",
        "success": "#57705f",
        "success_bg": "#eef4ef",
        "today": "#e7e0bb",
        "selected": "#ddd6b0",
        "neutral": "#eceef0",
    },
}

COLORS = THEMES["Vinho"].copy()


def apply_theme(theme_name: str):
    palette = THEMES.get(theme_name, THEMES["Vinho"])
    COLORS.clear()
    COLORS.update(palette)


def base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


def icon_path() -> Path:
    return base_dir() / "app_icon.ico"


def asset_path(name: str) -> Path:
    return base_dir() / "assets" / name


def load_tinted_icon(filename: str, size: int, color: str):
    path = asset_path(filename)
    if not path.exists():
        return None
    try:
        source = Image.open(path).convert("RGBA")
        source = source.resize((size, size), Image.Resampling.LANCZOS)
        alpha = source.getchannel("A")
        colored = Image.new("RGBA", source.size, color)
        colored.putalpha(alpha)
        return ImageTk.PhotoImage(colored)
    except Exception:
        return None


def app_data_dir() -> Path:
    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
        folder = Path(base) / APP_NAME
    else:
        folder = Path.home() / ".pines_journal"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def default_png_dir() -> Path:
    if os.name == "nt":
        base = Path.home() / "Pictures"
    else:
        base = Path.home() / "Pictures"
    folder = base / "Pine's Journal"
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return folder


DB_PATH = app_data_dir() / "tarefas.db"


def iso_now() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def parse_ui_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FMT_UI).date()
    except ValueError:
        return None


def format_due_date(value):
    if not value:
        return ""
    try:
        return datetime.strptime(value, DATE_FMT_DB).strftime(DATE_FMT_UI)
    except (TypeError, ValueError):
        return value


def load_icon_photo(size=24):
    path = icon_path()
    if not path.exists():
        return None
    try:
        image = Image.open(path).convert("RGBA")
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except Exception:
        return None


def load_header_mark(size=30):
    path = asset_path("header_mark.png")
    if not path.exists():
        return load_icon_photo(size)
    try:
        image = Image.open(path).convert("RGBA")
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except Exception:
        return load_icon_photo(size)


def _hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in rgb)


def lighten(color, amount=0.15):
    r, g, b = _hex_to_rgb(color)
    return _rgb_to_hex((r + (255 - r) * amount, g + (255 - g) * amount, b + (255 - b) * amount))


def darken(color, amount=0.15):
    r, g, b = _hex_to_rgb(color)
    return _rgb_to_hex((r * (1 - amount), g * (1 - amount), b * (1 - amount)))


class SoftButton(tk.Canvas):
    def __init__(self, master, text="", image=None, command=None, width=90, height=32, radius=10,
                 fill="#ffffff", fg="#111111", hover_fill=None, outline=None, font=BUTTON_FONT,
                 compound="left", padx=10, cursor="hand2"):
        bg_parent = master.cget("bg") if "bg" in master.keys() else COLORS["bg"]
        super().__init__(master, width=width, height=height, highlightthickness=0, bd=0,
                         bg=bg_parent, cursor=cursor)
        self.command = command
        self.text = text
        self.image_ref = image
        self.width_value = width
        self.height_value = height
        self.radius = radius
        self.fill = fill
        self.fg = fg
        self.hover_fill = hover_fill or lighten(fill, 0.08)
        self.outline = outline or darken(fill, 0.12)
        self.font = font
        self.compound = compound
        self.padx = padx
        self.selected = False
        self.current_fill = fill
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Configure>", lambda e: self._redraw())
        self._redraw()

    def set_text(self, text):
        self.text = text
        self._redraw()

    def set_style(self, fill=None, fg=None, hover_fill=None, outline=None, image=None):
        if fill is not None:
            self.fill = fill
        if fg is not None:
            self.fg = fg
        if hover_fill is not None:
            self.hover_fill = hover_fill
        if outline is not None:
            self.outline = outline
        if image is not None:
            self.image_ref = image
        self.current_fill = self.fill
        self._redraw()

    def set_selected(self, selected: bool):
        self.selected = selected
        self.current_fill = self.fill
        self._redraw()

    def _draw_round_rect(self, x1, y1, x2, y2, radius, fill, outline):
        r = max(4, min(radius, (x2 - x1) // 3, (y2 - y1) // 3))
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        self.create_polygon(
            points, smooth=True, splinesteps=24, fill=fill,
            outline=outline, width=1
        )


    def _redraw(self):
        self.delete("all")
        # Antes do primeiro layout, winfo_width/height normalmente retornam 1.
        # Use o tamanho solicitado do botao como minimo para evitar geometria invalida.
        try:
            actual_w = int(self.winfo_width())
            actual_h = int(self.winfo_height())
        except (tk.TclError, TypeError, ValueError):
            actual_w = 1
            actual_h = 1

        w = max(12, self.width_value, actual_w)
        h = max(12, self.height_value, actual_h)
        r = min(self.radius, max(3, min(w, h) // 3))
        x1, y1, x2, y2 = 1, 1, w - 2, h - 2
        self._draw_round_rect(x1, y1, x2, y2, r, self.current_fill, self.outline)
        if self.image_ref and self.text:
            if self.compound == "top":
                self.create_image(w // 2, h // 2 - 7, image=self.image_ref)
                self.create_text(w // 2, h - 11, text=self.text, fill=self.fg, font=self.font)
            else:
                img_x = 16 + self.padx // 2
                self.create_image(img_x, h // 2, image=self.image_ref)
                self.create_text(img_x + 12 + self.padx // 2, h // 2, text=self.text, fill=self.fg, font=self.font, anchor="w")
        elif self.image_ref:
            self.create_image(w // 2, h // 2, image=self.image_ref)
        else:
            self.create_text(w // 2, h // 2, text=self.text, fill=self.fg, font=self.font)

    def _on_enter(self, _event):
        self.current_fill = self.hover_fill
        self._redraw()

    def _on_leave(self, _event):
        self.current_fill = self.fill
        self._redraw()

    def _on_click(self, _event):
        if callable(self.command):
            self.command()


class TaskRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.initialize()

    def connect(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def initialize(self):
        with self.connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    due_date TEXT,
                    completed INTEGER NOT NULL DEFAULT 0,
                    completed_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed, completed_at)")
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

    def purge_old_completed(self):
        cutoff = datetime.now() - timedelta(days=7)
        with self.connect() as con:
            cur = con.execute(
                "DELETE FROM tasks WHERE completed = 1 AND completed_at IS NOT NULL AND completed_at <= ?",
                (cutoff.replace(microsecond=0).isoformat(sep=" "),),
            )
            return cur.rowcount

    def list_tasks(self):
        self.purge_old_completed()
        with self.connect() as con:
            return con.execute(
                """
                SELECT * FROM tasks
                ORDER BY completed ASC,
                         CASE WHEN due_date IS NULL THEN 1 ELSE 0 END ASC,
                         due_date ASC,
                         created_at DESC
                """
            ).fetchall()

    def list_tasks_for_date(self, day: date):
        self.purge_old_completed()
        with self.connect() as con:
            return con.execute(
                """
                SELECT * FROM tasks
                WHERE due_date = ?
                ORDER BY completed ASC, created_at DESC
                """,
                (day.strftime(DATE_FMT_DB),),
            ).fetchall()

    def get_task(self, task_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()

    def create_task(self, title, description="", due_date=None):
        now = iso_now()
        with self.connect() as con:
            cur = con.execute(
                """
                INSERT INTO tasks(title, description, due_date, completed, completed_at, created_at, updated_at)
                VALUES (?, ?, ?, 0, NULL, ?, ?)
                """,
                (title.strip(), description.strip(), due_date, now, now),
            )
            return cur.lastrowid

    def update_task(self, task_id, title, description, due_date):
        with self.connect() as con:
            con.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, due_date = ?, updated_at = ?
                WHERE id = ?
                """,
                (title.strip(), description.strip(), due_date, iso_now(), task_id),
            )

    def set_completed(self, task_id, completed: bool):
        completed_at = iso_now() if completed else None
        with self.connect() as con:
            con.execute(
                """
                UPDATE tasks
                SET completed = ?, completed_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (1 if completed else 0, completed_at, iso_now(), task_id),
            )

    def delete_task(self, task_id):
        with self.connect() as con:
            con.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def overdue_count(self):
        today = date.today().strftime(DATE_FMT_DB)
        with self.connect() as con:
            return con.execute(
                "SELECT COUNT(*) FROM tasks WHERE completed = 0 AND due_date IS NOT NULL AND due_date < ?",
                (today,),
            ).fetchone()[0]

    def calendar_counts(self, year, month):
        first = date(year, month, 1)
        last = date(year, month, calendar.monthrange(year, month)[1])
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT due_date,
                       COUNT(*) AS total,
                       SUM(CASE WHEN completed = 0 THEN 1 ELSE 0 END) AS pending
                FROM tasks
                WHERE due_date BETWEEN ? AND ?
                GROUP BY due_date
                """,
                (first.strftime(DATE_FMT_DB), last.strftime(DATE_FMT_DB)),
            ).fetchall()
        return {row["due_date"]: (row["total"], row["pending"]) for row in rows}

    def get_setting(self, key, default=None):
        with self.connect() as con:
            row = con.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO settings(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value)),
            )

    def get_bool_setting(self, key, default=False):
        value = self.get_setting(key, "1" if default else "0")
        return str(value).lower() in {"1", "true", "yes", "on"}


def startup_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    python_exe = Path(sys.executable)
    pythonw = python_exe.with_name("pythonw.exe") if os.name == "nt" else python_exe
    return f'"{pythonw}" "{Path(__file__).resolve()}"'


def startup_enabled():
    if os.name != "nt":
        return False
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, REGISTRY_VALUE)
        return bool(value)
    except (OSError, FileNotFoundError):
        return False


def set_startup_enabled(enabled: bool):
    if os.name != "nt":
        raise RuntimeError("A inicialização automática está disponível apenas no Windows.")
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, REGISTRY_VALUE, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, REGISTRY_VALUE)
            except FileNotFoundError:
                pass


class ScrollableFrame(tk.Frame):
    def __init__(self, master, bg=None, **kwargs):
        bg = bg or COLORS["bg"]
        super().__init__(master, bg=bg, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.inner.bind("<MouseWheel>", self._on_mousewheel)

    def _on_inner_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except tk.TclError:
            pass


class BorderlessMixin:
    def make_borderless(self):
        try:
            self.overrideredirect(True)
        except tk.TclError:
            pass
        self._drag_origin = None

    def bind_drag(self, widget):
        widget.bind("<ButtonPress-1>", self._drag_start)
        widget.bind("<B1-Motion>", self._drag_move)

    def _drag_start(self, event):
        self._drag_origin = (event.x_root - self.winfo_x(), event.y_root - self.winfo_y())

    def _drag_move(self, event):
        if not self._drag_origin:
            return
        x = event.x_root - self._drag_origin[0]
        y = event.y_root - self._drag_origin[1]
        self.geometry(f"+{x}+{y}")


class DatePicker(BorderlessMixin, tk.Toplevel):
    MONTHS = [
        "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    WEEKDAYS = ["S", "T", "Q", "Q", "S", "S", "D"]

    def __init__(self, owner, initial_date=None, on_select=None):
        super().__init__(owner)
        self.owner = owner
        self.on_select = on_select
        selected = initial_date or date.today()
        self.year = selected.year
        self.month = selected.month
        self.withdraw()
        self.geometry("320x340")
        self.resizable(False, False)
        self.configure(bg=COLORS["panel"])
        self.make_borderless()
        self._build()
        self._center_over_owner()
        self.deiconify()
        self.lift()
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.update_idletasks()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.after(120, self._normalize_topmost)

    def _normalize_topmost(self):
        try:
            keep_top = bool(getattr(self.owner, "attributes", lambda *_: False)("-topmost"))
            self.attributes("-topmost", keep_top)
            self.lift()
        except Exception:
            pass

    def _build(self):
        head = tk.Frame(self, bg=COLORS["header"], height=38)
        head.pack(fill="x")
        head.pack_propagate(False)
        title = tk.Label(head, text="Selecionar data", bg=COLORS["header"], fg="white", font=("Segoe UI", 9, "bold"))
        title.pack(side="left", padx=12)
        close = tk.Button(head, text="×", command=self.destroy, bg=COLORS["header"], fg="white", activebackground=COLORS["header_hover"], activeforeground="white", relief="flat", bd=0, width=3, cursor="hand2", font=SUBSECTION_FONT)
        close.pack(side="right", fill="y")
        self.bind_drag(head)
        self.bind_drag(title)

        self.body = tk.Frame(self, bg=COLORS["panel"])
        self.body.pack(fill="both", expand=True)
        self._render_body()

    def _center_over_owner(self):
        self.update_idletasks()
        try:
            x = self.owner.winfo_rootx() + max(0, (self.owner.winfo_width() - 320) // 2)
            y = self.owner.winfo_rooty() + max(0, (self.owner.winfo_height() - 340) // 2)
            self.geometry(f"320x340+{x}+{y}")
        except tk.TclError:
            pass

    def _render_body(self):
        for widget in self.body.winfo_children():
            widget.destroy()

        top = tk.Frame(self.body, bg=COLORS["panel"])
        top.pack(fill="x", padx=12, pady=(12, 7))
        tk.Button(top, text="‹", command=lambda: self._change_month(-1), relief="flat", bg=COLORS["neutral"], width=3, font=SUBSECTION_FONT, cursor="hand2").pack(side="left")
        tk.Label(top, text=f"{self.MONTHS[self.month]} {self.year}", bg=COLORS["panel"], fg=COLORS["text"], font=SUBSECTION_FONT).pack(side="left", expand=True)
        tk.Button(top, text="›", command=lambda: self._change_month(1), relief="flat", bg=COLORS["neutral"], width=3, font=SUBSECTION_FONT, cursor="hand2").pack(side="right")

        grid = tk.Frame(self.body, bg=COLORS["panel"])
        grid.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        for c in range(7):
            grid.grid_columnconfigure(c, weight=1, uniform="dp")
            tk.Label(grid, text=self.WEEKDAYS[c], bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 7, "bold")).grid(row=0, column=c, sticky="nsew", pady=(0, 3))
        for r in range(1, 7):
            grid.grid_rowconfigure(r, weight=1)

        today = date.today()
        rows = calendar.monthcalendar(self.year, self.month)
        while len(rows) < 6:
            rows.append([0] * 7)
        for r, week in enumerate(rows, start=1):
            for c, day_num in enumerate(week):
                if not day_num:
                    continue
                day_obj = date(self.year, self.month, day_num)
                is_today = day_obj == today
                bg = COLORS["today"] if is_today else COLORS["panel"]
                fg = COLORS["accent"] if is_today else COLORS["text"]
                btn = tk.Button(
                    grid, text=str(day_num), command=lambda d=day_obj: self._select(d),
                    relief="flat", bd=0, bg=bg, fg=fg,
                    activebackground=COLORS["selected"], activeforeground=COLORS["text"],
                    font=("Segoe UI", 8, "bold" if is_today else "normal"), cursor="hand2"
                )
                btn.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)

        bottom = tk.Frame(self.body, bg=COLORS["panel"])
        bottom.pack(fill="x", padx=12, pady=(0, 10))
        tk.Button(bottom, text="Hoje", command=lambda: self._select(date.today()), relief="flat", bg=COLORS["neutral"], fg=COLORS["text"], padx=10, pady=4, cursor="hand2").pack(side="left")
        tk.Button(bottom, text="Cancelar", command=self.destroy, relief="flat", bg=COLORS["panel"], fg=COLORS["muted"], padx=8, pady=4, cursor="hand2").pack(side="right")

    def _change_month(self, delta):
        month = self.month - 1 + delta
        self.year += month // 12
        self.month = month % 12 + 1
        self._render_body()

    def _select(self, selected):
        if self.on_select:
            self.on_select(selected)
        self.destroy()


class TaskEditor(BorderlessMixin, tk.Toplevel):
    def __init__(self, app, task_id=None, preset_date=None, on_close=None):
        super().__init__(app)
        self.app = app
        self.repo = app.repo
        self.task_id = task_id
        self.preset_date = preset_date
        self.on_close = on_close
        self.withdraw()
        self.geometry("420x470")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.make_borderless()
        self._build()
        self._load()
        self._center_over_app()
        self.deiconify()
        self.lift()
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.update_idletasks()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.after(100, self._finish_show)
        self.bind("<Control-Return>", lambda _e: self._save())
        self.bind("<Escape>", lambda _e: self._close())

    def _finish_show(self):
        if not self.winfo_exists():
            return
        try:
            self.attributes("-topmost", bool(self.app.always_on_top))
            self.lift()
            self.focus_force()
            self.title_entry.focus_set()
        except tk.TclError:
            pass

    def _center_over_app(self):
        self.update_idletasks()
        try:
            x = self.app.winfo_rootx() + max(0, (self.app.winfo_width() - 420) // 2)
            y = self.app.winfo_rooty() + max(0, (self.app.winfo_height() - 470) // 2)
            self.geometry(f"420x470+{x}+{y}")
        except tk.TclError:
            pass

    def _build(self):
        head = tk.Frame(self, bg=COLORS["header"], height=42)
        head.pack(fill="x")
        head.pack_propagate(False)
        title_text = "Nova tarefa" if self.task_id is None else "Detalhes da tarefa"
        title = tk.Label(head, text=title_text, bg=COLORS["header"], fg="white", font=SUBSECTION_FONT)
        title.pack(side="left", padx=14)
        close = tk.Button(head, text="×", command=self._close, bg=COLORS["header"], fg="white", activebackground=COLORS["header_hover"], activeforeground="white", relief="flat", bd=0, width=4, cursor="hand2", font=SUBSECTION_FONT)
        close.pack(side="right", fill="y")
        self.bind_drag(head)
        self.bind_drag(title)

        body = tk.Frame(self, bg=COLORS["panel"], padx=18, pady=12)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Nome da tarefa *", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.title_entry = tk.Entry(body, font=("Segoe UI", 10), relief="solid", bd=1)
        self.title_entry.pack(fill="x", ipady=5, pady=(4, 10))

        tk.Label(body, text="Descrição", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.desc_text = tk.Text(body, height=7, wrap="word", font=BODY_FONT_LARGE, relief="solid", bd=1)
        self.desc_text.pack(fill="both", expand=True, pady=(4, 10))

        tk.Label(body, text="Data de conclusão", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        date_row = tk.Frame(body, bg=COLORS["panel"])
        date_row.pack(fill="x", pady=(4, 0))
        self.date_entry = tk.Entry(date_row, font=("Segoe UI", 10), relief="solid", bd=1)
        self.date_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.date_entry.bind("<Double-Button-1>", lambda _e: self._open_date_picker())
        tk.Button(date_row, text="Calendário", command=self._open_date_picker, bg=COLORS["neutral"], fg=COLORS["text"], relief="flat", padx=8, cursor="hand2", font=("Segoe UI", 7, "bold")).pack(side="left", padx=(5, 0), ipady=5)
        tk.Button(date_row, text="×", command=lambda: self.date_entry.delete(0, "end"), bg=COLORS["neutral"], fg=COLORS["muted"], relief="flat", width=3, cursor="hand2", font=SUBSECTION_FONT).pack(side="left", padx=(4, 0), ipady=3)
        tk.Label(body, text="dd/mm/aaaa", bg=COLORS["panel"], fg=COLORS["muted"], font=SMALL_FONT).pack(anchor="w", pady=(2, 0))

        footer = tk.Frame(self, bg=COLORS["bg"], padx=14, pady=10)
        footer.pack(fill="x", side="bottom")
        if self.task_id is not None:
            tk.Button(footer, text="Excluir", command=self._delete, bg=COLORS["danger_bg"], fg=COLORS["danger"], relief="flat", padx=10, pady=6, cursor="hand2").pack(side="left")
        tk.Button(footer, text="Cancelar", command=self._close, bg=COLORS["neutral"], fg=COLORS["text"], relief="flat", padx=10, pady=6, cursor="hand2").pack(side="right")
        tk.Button(footer, text="Salvar tarefa", command=self._save, bg=COLORS["accent"], fg="white", activebackground=COLORS["accent_dark"], activeforeground="white", relief="flat", padx=14, pady=6, font=BUTTON_FONT, cursor="hand2").pack(side="right", padx=(0, 6))

    def _load(self):
        if self.task_id is not None:
            task = self.repo.get_task(self.task_id)
            if not task:
                self._close()
                return
            self.title_entry.insert(0, task["title"])
            self.desc_text.insert("1.0", task["description"] or "")
            if task["due_date"]:
                self.date_entry.insert(0, format_due_date(task["due_date"]))
        elif self.preset_date:
            self.date_entry.insert(0, self.preset_date.strftime(DATE_FMT_UI))

    def _open_date_picker(self):
        initial = parse_ui_date(self.date_entry.get()) or self.preset_date or date.today()
        DatePicker(self, initial_date=initial, on_select=self._set_date)

    def _set_date(self, selected):
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, selected.strftime(DATE_FMT_UI))

    def _save(self):
        title = self.title_entry.get().strip()
        description = self.desc_text.get("1.0", "end").strip()
        date_text = self.date_entry.get().strip()
        if not title:
            messagebox.showwarning("Campo obrigatório", "Informe o nome da tarefa.", parent=self)
            return

        due = None
        if date_text:
            parsed = parse_ui_date(date_text)
            if not parsed:
                messagebox.showwarning("Data inválida", "Use dd/mm/aaaa ou escolha a data pelo calendário.", parent=self)
                return
            due = parsed.strftime(DATE_FMT_DB)

        if self.task_id is None:
            self.repo.create_task(title, description, due)
        else:
            self.repo.update_task(self.task_id, title, description, due)
        self.app.refresh_current_view()
        self._close(refresh=False)

    def _delete(self):
        should_delete = True
        if self.app.confirm_delete:
            should_delete = messagebox.askyesno("Excluir tarefa", "Deseja excluir esta tarefa definitivamente?", parent=self)
        if should_delete:
            self.repo.delete_task(self.task_id)
            self.app.refresh_current_view()
            self._close(refresh=False)

    def _close(self, refresh=False):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        try:
            self.destroy()
        except tk.TclError:
            pass
        if refresh:
            self.app.refresh_current_view()
        if self.on_close:
            try:
                self.on_close()
            except tk.TclError:
                pass


class TaskApp(BorderlessMixin, tk.Tk):
    APP_W = 540
    APP_H = 650

    def __init__(self):
        super().__init__()
        self.repo = TaskRepository(DB_PATH)
        self.repo.purge_old_completed()

        self.theme_name = self.repo.get_setting("theme", "Vinho")
        if self.theme_name not in THEMES:
            self.theme_name = "Vinho"
        apply_theme(self.theme_name)

        self.always_on_top = self.repo.get_bool_setting("always_on_top", False)
        self.confirm_delete = self.repo.get_bool_setting("confirm_delete", True)

        self.current_view = "list"
        today = date.today()
        self.calendar_year = today.year
        self.calendar_month = today.month

        self.scratch_tool = "brush"
        self.scratch_strokes = []
        self.scratch_texts = []
        self.scratch_next_id = 1
        self.scratch_next_text_id = 1
        self.scratch_active_id = None
        self.scratch_canvas = None
        self.scratch_text_entry = None
        self.scratch_text_window = None
        self.scratch_tool_buttons = {}
        self.active_editor = None
        self.active_day_window = None
        self.ui_images = {}

        self.task_search_var = tk.StringVar(self, value="")
        self.task_filter_var = tk.StringVar(self, value="Todas")
        configured_png = self.repo.get_setting("png_folder", str(default_png_dir()))
        self.png_folder = Path(configured_png).expanduser() if configured_png else default_png_dir()

        self.title(APP_NAME)
        self._apply_native_icon()
        self.geometry(f"{self.APP_W}x{self.APP_H}")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.make_borderless()
        try:
            self.attributes("-topmost", self.always_on_top)
        except tk.TclError:
            pass
        self._configure_styles()
        self._build_shell()
        self.show_list()
        self.after(20, self._ensure_taskbar_presence)

    def _apply_native_icon(self):
        icon = icon_path()
        if icon.exists():
            try:
                self.iconbitmap(default=str(icon))
            except Exception:
                pass

    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Vertical.TScrollbar",
            gripcount=0,
            background="#c8ccd2",
            troughcolor=COLORS["bg"],
            bordercolor=COLORS["bg"],
            arrowcolor="#6b7078",
        )

    def _ensure_taskbar_presence(self):
        if os.name != "nt":
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception:
            pass


    def _build_shell(self):
        self.topbar = tk.Frame(self, bg=COLORS["header"], height=58)
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)

        drag_area = tk.Frame(self.topbar, bg=COLORS["header"])
        drag_area.pack(side="left", fill="both", expand=True, padx=(8, 6))

        self.header_icon_photo = load_header_mark(30)
        if self.header_icon_photo:
            icon_label = tk.Label(drag_area, image=self.header_icon_photo, bg=COLORS["header"])
            icon_label.pack(side="left", padx=(6, 8), pady=8)
            self.bind_drag(icon_label)

        title = tk.Label(drag_area, text=APP_NAME, bg=COLORS["header"], fg="white", font=TITLE_FONT)
        title.pack(side="left")
        self.bind_drag(drag_area)
        self.bind_drag(title)

        controls = tk.Frame(self.topbar, bg=COLORS["header"])
        controls.pack(side="right", padx=(4, 8), pady=9)

        # Fechar fica na extremidade direita; minimizar fica imediatamente à esquerda.
        self.close_btn = SoftButton(
            controls, text="×", command=self.destroy, width=30, height=30, radius=9,
            fill=COLORS["header"], hover_fill="#a8324b", fg="white",
            outline=lighten(COLORS["header"], 0.10), font=("Segoe UI", 11, "bold"), compound="center"
        )
        self.close_btn.pack(side="right")

        self.min_btn = SoftButton(
            controls, text="—", command=self._minimize, width=30, height=30, radius=9,
            fill=COLORS["header"], hover_fill=COLORS["header_hover"], fg="white",
            outline=lighten(COLORS["header"], 0.10), font=("Segoe UI", 10, "bold"), compound="center"
        )
        self.min_btn.pack(side="right", padx=(0, 6))

        self.navbar = tk.Frame(self, bg=COLORS["panel"], height=58, highlightbackground=COLORS["border"], highlightthickness=1)
        self.navbar.pack(fill="x")
        self.navbar.pack_propagate(False)

        self.list_btn = self._nav_button(self.navbar, "Lista de Tarefas", "lista.png", self.show_list)
        self.calendar_btn = self._nav_button(self.navbar, "Calendário", "calendario.png", self.show_calendar)
        self.scratch_btn = self._nav_button(self.navbar, "Bloco de Notas", "bloco.png", self.show_scratch)
        self.settings_btn = self._nav_button(self.navbar, "Configurações", "configuracoes.png", self.show_settings)

        self.content = tk.Frame(self, bg=COLORS["bg"])
        self.content.pack(fill="both", expand=True)


    def open_new_task(self, preset_date=None, on_close=None):
        return self.open_task_editor(task_id=None, preset_date=preset_date, on_close=on_close)

    def open_task_editor(self, task_id=None, preset_date=None, on_close=None):
        try:
            if self.active_editor is not None and self.active_editor.winfo_exists():
                self.active_editor.lift()
                self.active_editor.focus_force()
                return self.active_editor
        except tk.TclError:
            self.active_editor = None

        def editor_closed():
            self.active_editor = None
            if on_close:
                on_close()

        try:
            editor = TaskEditor(
                self, task_id=task_id, preset_date=preset_date, on_close=editor_closed
            )
            self.active_editor = editor
            return editor
        except Exception as exc:
            self.active_editor = None
            messagebox.showerror(
                "Nova tarefa",
                f"Não foi possível abrir o editor de tarefas.\n\n{exc}",
                parent=self,
            )
            return None

    def _minimize(self):
        try:
            self.overrideredirect(False)
            self.iconify()
            self.after(150, self._restore_borderless_after_minimize)
        except tk.TclError:
            pass

    def _restore_borderless_after_minimize(self):
        if self.state() == "normal":
            try:
                self.overrideredirect(True)
                self._ensure_taskbar_presence()
            except tk.TclError:
                pass
        else:
            self.after(150, self._restore_borderless_after_minimize)

    def _nav_button(self, parent, text, icon_file, command):
        icon = load_tinted_icon(icon_file, 18, COLORS["muted"])
        key = f"nav_{text}"
        self.ui_images[key] = icon
        btn = SoftButton(
            parent, text=text, image=icon, command=command, width=125, height=44, radius=10,
            fill=COLORS["panel"], fg=COLORS["muted"], hover_fill=COLORS["neutral"],
            outline=COLORS["border"], font=("Segoe UI", 7, "bold"), compound="top", padx=0
        )
        btn.icon_file = icon_file
        btn.icon_key = key
        btn.pack(side="left", fill="both", expand=True, padx=4, pady=6)
        return btn

    def _set_active_nav(self, view):
        pairs = {
            "list": self.list_btn,
            "calendar": self.calendar_btn,
            "scratch": self.scratch_btn,
            "settings": self.settings_btn,
        }
        for key, button in pairs.items():
            active = key == view
            icon = load_tinted_icon(button.icon_file, 18, COLORS["accent"] if active else COLORS["muted"])
            self.ui_images[button.icon_key] = icon
            button.set_style(
                fill=COLORS["selected"] if active else COLORS["panel"],
                fg=COLORS["text"] if active else COLORS["muted"],
                hover_fill=lighten(COLORS["selected"] if active else COLORS["neutral"], 0.05),
                outline=COLORS["border"],
                image=icon,
            )
            button.set_selected(active)

    def clear_content(self):
        if getattr(self, "scratch_text_entry", None) is not None:
            self._commit_scratch_text_entry()
        for child in self.content.winfo_children():
            child.destroy()
        self.scratch_canvas = None
        self.scratch_text_entry = None
        self.scratch_text_window = None

    def refresh_current_view(self):
        if self.current_view == "calendar":
            self.show_calendar()
        elif self.current_view == "scratch":
            self.show_scratch()
        elif self.current_view == "settings":
            self.show_settings()
        else:
            self.show_list()

    def _rebuild_shell(self, view=None):
        target = view or self.current_view
        for child in self.winfo_children():
            child.destroy()
        self.configure(bg=COLORS["bg"])
        self._configure_styles()
        self._build_shell()
        if target == "calendar":
            self.show_calendar()
        elif target == "scratch":
            self.show_scratch()
        elif target == "settings":
            self.show_settings()
        else:
            self.show_list()

    def show_list(self):
        self.current_view = "list"
        self._set_active_nav("list")
        self.clear_content()

        header = tk.Frame(self.content, bg=COLORS["bg"])
        header.pack(fill="x", padx=14, pady=(11, 6))
        tk.Label(header, text="Minhas tarefas", bg=COLORS["bg"], fg=COLORS["text"], font=SECTION_FONT).pack(side="left", pady=(5, 0))
        SoftButton(
            header, text="+ Nova", command=self.open_new_task,
            width=78, height=30, radius=9,
            fill=COLORS["accent"], hover_fill=COLORS["accent_dark"], fg="white",
            outline=darken(COLORS["accent"], 0.18),
            font=BUTTON_FONT, compound="center"
        ).pack(side="right")

        filter_row = tk.Frame(self.content, bg=COLORS["bg"])
        filter_row.pack(fill="x", padx=14, pady=(0, 7))

        search_box = tk.Frame(filter_row, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        search_box.pack(side="left", fill="x", expand=True)
        tk.Label(search_box, text="⌕", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI Symbol", 10, "bold")).pack(side="left", padx=(8, 3))
        self.task_search_entry = tk.Entry(
            search_box, textvariable=self.task_search_var, relief="flat", bd=0,
            bg=COLORS["panel"], fg=COLORS["text"], insertbackground=COLORS["text"],
            font=BODY_FONT
        )
        self.task_search_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        self.task_search_entry.bind("<KeyRelease>", lambda _e: self._render_filtered_tasks())

        self.task_filter_button = SoftButton(
            filter_row,
            text=f"{self.task_filter_var.get()}  ▾",
            command=self._open_task_filter_menu,
            width=118, height=31, radius=9,
            fill=COLORS["panel"], hover_fill=COLORS["selected"], fg=COLORS["text"],
            outline=COLORS["border"], font=BUTTON_FONT, compound="center"
        )
        self.task_filter_button.pack(side="right", padx=(7, 0))

        overdue = self.repo.overdue_count()
        if overdue:
            banner = tk.Frame(self.content, bg=COLORS["danger_bg"], highlightbackground="#f0caca", highlightthickness=1)
            banner.pack(fill="x", padx=14, pady=(0, 7))
            tk.Label(banner, text=f"⚠ {overdue} atrasada{'s' if overdue != 1 else ''}", bg=COLORS["danger_bg"], fg=COLORS["danger"], font=("Segoe UI", 8, "bold")).pack(side="left", padx=10, pady=6)
            tk.Label(banner, text="Prazo vencido", bg=COLORS["danger_bg"], fg="#986060", font=SMALL_FONT).pack(side="right", padx=10)

        self.task_scroll = ScrollableFrame(self.content, bg=COLORS["bg"])
        self.task_scroll.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._render_filtered_tasks()

    def _open_task_filter_menu(self):
        options = ["Todas", "Pendentes", "Concluídas", "Atrasadas", "Sem data"]
        menu = tk.Menu(
            self, tearoff=False,
            bg=COLORS["panel"], fg=COLORS["text"],
            activebackground=COLORS["selected"], activeforeground=COLORS["text"],
            font=BODY_FONT, bd=1, relief="solid"
        )
        current = self.task_filter_var.get() or "Todas"
        for option in options:
            label = f"✓  {option}" if option == current else f"    {option}"
            menu.add_command(label=label, command=lambda value=option: self._set_task_filter(value))
        try:
            x = self.task_filter_button.winfo_rootx()
            y = self.task_filter_button.winfo_rooty() + self.task_filter_button.winfo_height() + 2
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except tk.TclError:
                pass

    def _set_task_filter(self, value):
        self.task_filter_var.set(value)
        if hasattr(self, "task_filter_button") and self.task_filter_button.winfo_exists():
            self.task_filter_button.set_text(f"{value}  ▾")
        self._render_filtered_tasks()

    def _render_filtered_tasks(self):
        scroll = getattr(self, "task_scroll", None)
        if scroll is None or not scroll.winfo_exists():
            return
        for child in scroll.inner.winfo_children():
            child.destroy()

        tasks = list(self.repo.list_tasks())
        query = self.task_search_var.get().strip().lower()
        filter_name = self.task_filter_var.get() or "Todas"
        today_db = date.today().strftime(DATE_FMT_DB)

        if query:
            filtered = []
            for task in tasks:
                haystack = " ".join([
                    task["title"] or "",
                    task["description"] or "",
                    format_due_date(task["due_date"]) if task["due_date"] else "",
                ]).lower()
                if query in haystack:
                    filtered.append(task)
            tasks = filtered

        if filter_name == "Pendentes":
            tasks = [t for t in tasks if not t["completed"]]
        elif filter_name == "Concluídas":
            tasks = [t for t in tasks if t["completed"]]
        elif filter_name == "Atrasadas":
            tasks = [t for t in tasks if not t["completed"] and t["due_date"] and t["due_date"] < today_db]
        elif filter_name == "Sem data":
            tasks = [t for t in tasks if not t["due_date"]]

        if not tasks:
            empty = tk.Frame(scroll.inner, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
            empty.pack(fill="x", pady=4)
            message = "Seu bloco está vazio" if not query and filter_name == "Todas" else "Nenhuma tarefa encontrada"
            detail = "Use + Nova para criar a primeira tarefa." if message == "Seu bloco está vazio" else "Tente alterar a pesquisa ou o filtro."
            tk.Label(empty, text=message, bg=COLORS["panel"], fg=COLORS["text"], font=SUBSECTION_FONT).pack(pady=(28, 4))
            tk.Label(empty, text=detail, bg=COLORS["panel"], fg=COLORS["muted"], font=BODY_FONT).pack(pady=(0, 28))
            return

        pending = [t for t in tasks if not t["completed"]]
        completed = [t for t in tasks if t["completed"]]
        if pending:
            self._section_label(scroll.inner, "Pendentes", len(pending))
            for task in pending:
                self._task_row(scroll.inner, task)
        if completed:
            self._section_label(scroll.inner, "Concluídas", len(completed), top_pad=12)
            for task in completed:
                self._task_row(scroll.inner, task)

    def _section_label(self, parent, text, count, top_pad=0):
        frame = tk.Frame(parent, bg=COLORS["bg"])
        frame.pack(fill="x", pady=(top_pad, 4))
        tk.Label(frame, text=text, bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Label(frame, text=str(count), bg=COLORS["neutral"], fg=COLORS["muted"], font=("Segoe UI", 7, "bold"), padx=6, pady=1).pack(side="left", padx=6)

    def _task_row(self, parent, task, refresh_callback=None, editor_callback=None):
        completed = bool(task["completed"])
        overdue = bool(task["due_date"] and not completed and task["due_date"] < date.today().strftime(DATE_FMT_DB))
        bg = COLORS["success_bg"] if completed else COLORS["panel"]
        row = tk.Frame(parent, bg=bg, highlightbackground=COLORS["border"], highlightthickness=1, cursor="hand2")
        row.pack(fill="x", pady=3)

        var = tk.BooleanVar(value=completed)
        check = tk.Checkbutton(
            row, variable=var,
            command=lambda tid=task["id"], v=var: self._toggle_task(tid, v.get(), refresh_callback),
            bg=bg, activebackground=bg, selectcolor=bg, cursor="hand2", bd=0
        )
        check.pack(side="left", padx=(8, 5), pady=9)

        text_frame = tk.Frame(row, bg=bg, cursor="hand2")
        text_frame.pack(side="left", fill="x", expand=True, pady=7)
        title_fg = COLORS["muted"] if completed else COLORS["text"]
        title = tk.Label(text_frame, text=task["title"], bg=bg, fg=title_fg, font=("Segoe UI", 9, "bold"), anchor="w", cursor="hand2")
        title.pack(anchor="w")
        desc = None
        if task["description"]:
            preview = task["description"].replace("\n", " ").strip()
            if len(preview) > 58:
                preview = preview[:55] + "..."
            desc = tk.Label(text_frame, text=preview, bg=bg, fg=COLORS["muted"], font=SMALL_FONT, anchor="w", cursor="hand2")
            desc.pack(anchor="w", pady=(1, 0))

        due = None
        if task["due_date"]:
            label_bg = COLORS["danger_bg"] if overdue else COLORS["neutral"]
            label_fg = COLORS["danger"] if overdue else COLORS["muted"]
            due_text = ("! " if overdue else "") + format_due_date(task["due_date"])
            due = tk.Label(row, text=due_text, bg=label_bg, fg=label_fg, font=("Segoe UI", 7, "bold"), padx=7, pady=4, cursor="hand2")
            due.pack(side="right", padx=8)

        open_fn = lambda _e, tid=task["id"]: self.open_task_editor(task_id=tid, on_close=editor_callback)
        for widget in (row, text_frame, title, desc, due):
            if widget is not None:
                widget.bind("<Button-1>", open_fn)

    def _toggle_task(self, task_id, completed, refresh_callback=None):
        self.repo.set_completed(task_id, completed)
        if refresh_callback:
            refresh_callback()
        else:
            self.refresh_current_view()

    def show_calendar(self):
        self.current_view = "calendar"
        self._set_active_nav("calendar")
        self.clear_content()

        top = tk.Frame(self.content, bg=COLORS["bg"])
        top.pack(fill="x", padx=14, pady=(12, 6))
        SoftButton(top, text="‹", command=lambda: self._change_month(-1), width=30, height=28, radius=9,
                   fill=COLORS["neutral"], hover_fill=COLORS["selected"], fg=COLORS["text"],
                   outline=COLORS["border"], font=SUBSECTION_FONT, compound="center").pack(side="left")
        self.month_label = tk.Label(top, text="", bg=COLORS["bg"], fg=COLORS["text"], font=SECTION_FONT)
        self.month_label.pack(side="left", expand=True)
        SoftButton(top, text="›", command=lambda: self._change_month(1), width=30, height=28, radius=9,
                   fill=COLORS["neutral"], hover_fill=COLORS["selected"], fg=COLORS["text"],
                   outline=COLORS["border"], font=SUBSECTION_FONT, compound="center").pack(side="right")

        card = tk.Frame(self.content, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        grid = tk.Frame(card, bg=COLORS["panel"])
        grid.pack(fill="both", expand=True, padx=8, pady=8)
        grid.grid_anchor("center")
        for col in range(7):
            grid.grid_columnconfigure(col, weight=0, uniform="day", minsize=68)
        grid.grid_rowconfigure(0, weight=0, minsize=28)
        for row in range(1, 7):
            grid.grid_rowconfigure(row, weight=0, uniform="week", minsize=66)

        weekdays = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        for col, name in enumerate(weekdays):
            tk.Label(grid, text=name, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 7, "bold")).grid(row=0, column=col, sticky="nsew", padx=1, pady=2)

        month_names = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        self.month_label.configure(text=f"{month_names[self.calendar_month]} {self.calendar_year}")
        counts = self.repo.calendar_counts(self.calendar_year, self.calendar_month)
        rows = calendar.monthcalendar(self.calendar_year, self.calendar_month)
        while len(rows) < 6:
            rows.append([0] * 7)
        today = date.today()

        for r, week in enumerate(rows, start=1):
            for c, day_num in enumerate(week):
                if day_num == 0:
                    blank = tk.Frame(grid, bg=COLORS["panel"], width=68, height=66)
                    blank.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                    blank.grid_propagate(False)
                    continue
                day_obj = date(self.calendar_year, self.calendar_month, day_num)
                key = day_obj.strftime(DATE_FMT_DB)
                total, pending = counts.get(key, (0, 0))
                is_today = day_obj == today
                is_overdue = day_obj < today and pending > 0
                day_bg = COLORS["today"] if is_today else (COLORS["danger_bg"] if is_overdue else COLORS["panel"])
                cell = tk.Frame(
                    grid, bg=day_bg, width=68, height=66,
                    highlightbackground=COLORS["border"], highlightthickness=1, cursor="hand2"
                )
                cell.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                cell.grid_propagate(False)
                cell.pack_propagate(False)
                day_label = tk.Label(cell, text=str(day_num), bg=day_bg, fg=COLORS["danger"] if is_overdue else COLORS["text"], font=BUTTON_FONT, cursor="hand2")
                day_label.place(x=6, y=5)
                count_label = None
                if total:
                    count_label = tk.Label(cell, text=f"• {total}", bg=day_bg, fg=COLORS["danger"] if is_overdue else COLORS["accent"], font=("Segoe UI", 7, "bold"), cursor="hand2")
                    count_label.place(x=6, y=25)
                open_day = lambda _e, d=day_obj: self.open_day(d)
                for widget in (cell, day_label, count_label):
                    if widget is not None:
                        widget.bind("<Button-1>", open_day)

    def _change_month(self, delta):
        month = self.calendar_month - 1 + delta
        self.calendar_year += month // 12
        self.calendar_month = month % 12 + 1
        self.show_calendar()

    def open_day(self, day_obj):
        # The day window is deliberately non-modal. A modal grab on a borderless
        # Toplevel can make Windows appear frozen if the window is not yet visible.
        try:
            if self.active_day_window is not None and self.active_day_window.winfo_exists():
                self.active_day_window.destroy()
        except tk.TclError:
            pass
        self.active_day_window = None

        win = tk.Toplevel(self)
        self.active_day_window = win
        win.withdraw()
        win.geometry("420x430")
        win.resizable(False, False)
        win.configure(bg=COLORS["bg"])
        try:
            win.overrideredirect(True)
        except tk.TclError:
            pass

        drag = {"x": 0, "y": 0}

        def close_day():
            if self.active_day_window is win:
                self.active_day_window = None
            try:
                win.destroy()
            except tk.TclError:
                pass

        def start_drag(event):
            drag["x"] = event.x_root - win.winfo_x()
            drag["y"] = event.y_root - win.winfo_y()

        def move_drag(event):
            try:
                win.geometry(f"+{event.x_root - drag['x']}+{event.y_root - drag['y']}")
            except tk.TclError:
                pass

        head = tk.Frame(win, bg=COLORS["header"], height=42)
        head.pack(fill="x")
        head.pack_propagate(False)
        title = tk.Label(
            head, text=day_obj.strftime("%d/%m/%Y"),
            bg=COLORS["header"], fg="white", font=SUBSECTION_FONT
        )
        title.pack(side="left", padx=14)
        tk.Button(
            head, text="×", command=close_day,
            bg=COLORS["header"], fg="white",
            activebackground=COLORS["header_hover"], activeforeground="white",
            relief="flat", bd=0, width=4, font=SUBSECTION_FONT, cursor="hand2"
        ).pack(side="right", fill="y")
        head.bind("<ButtonPress-1>", start_drag)
        head.bind("<B1-Motion>", move_drag)
        title.bind("<ButtonPress-1>", start_drag)
        title.bind("<B1-Motion>", move_drag)

        toolbar = tk.Frame(win, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=12, pady=(10, 5))
        tk.Label(
            toolbar, text="Tarefas do dia",
            bg=COLORS["bg"], fg=COLORS["text"], font=SUBSECTION_FONT
        ).pack(side="left")

        body = tk.Frame(win, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        def refresh_calendar_behind():
            if self.current_view == "calendar":
                self.show_calendar()

        def render(refresh_calendar=False):
            if not win.winfo_exists():
                return
            for child in body.winfo_children():
                child.destroy()
            tasks = self.repo.list_tasks_for_date(day_obj)
            if not tasks:
                empty = tk.Frame(
                    body, bg=COLORS["panel"],
                    highlightbackground=COLORS["border"], highlightthickness=1
                )
                empty.pack(fill="x", pady=3)
                tk.Label(
                    empty, text="Nenhuma tarefa neste dia",
                    bg=COLORS["panel"], fg=COLORS["muted"], font=BODY_FONT_LARGE
                ).pack(pady=26)
            else:
                callback = lambda: render(refresh_calendar=True)
                for task in tasks:
                    self._task_row(
                        body, task,
                        refresh_callback=callback,
                        editor_callback=callback
                    )
            if refresh_calendar:
                refresh_calendar_behind()

        # Build and position first; only then show/focus the borderless window.
        win.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - 420) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - 430) // 2)
        win.geometry(f"420x430+{x}+{y}")
        render(refresh_calendar=False)
        win.deiconify()
        win.lift()
        try:
            win.attributes("-topmost", True)
        except tk.TclError:
            pass
        win.update_idletasks()
        try:
            win.focus_force()
        except tk.TclError:
            pass

        def normalize_day_window():
            try:
                if win.winfo_exists():
                    win.attributes("-topmost", bool(self.always_on_top))
                    win.lift()
            except tk.TclError:
                pass

        win.after(120, normalize_day_window)
        win.bind("<Escape>", lambda _e: close_day())

    def show_scratch(self):
        self.current_view = "scratch"
        self._set_active_nav("scratch")
        self.clear_content()

        toolbar = tk.Frame(self.content, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=14, pady=(11, 7))

        self.ui_images["tool_brush"] = load_tinted_icon("lapis.png", 15, COLORS["text"])
        self.ui_images["tool_eraser"] = load_tinted_icon("borracha.png", 15, COLORS["text"])
        self.ui_images["tool_text"] = load_tinted_icon("text.png", 15, COLORS["text"])
        self.ui_images["tool_download"] = load_tinted_icon("download.png", 15, "white")

        brush = SoftButton(
            toolbar, text="Lápis", image=self.ui_images["tool_brush"],
            command=lambda: self._set_scratch_tool("brush"), width=76, height=32, radius=9,
            fill=COLORS["neutral"], hover_fill=COLORS["selected"], fg=COLORS["text"],
            outline=COLORS["border"], font=("Segoe UI", 7, "bold")
        )
        brush.pack(side="left")
        eraser = SoftButton(
            toolbar, text="Borracha", image=self.ui_images["tool_eraser"],
            command=lambda: self._set_scratch_tool("eraser"), width=92, height=32, radius=9,
            fill=COLORS["neutral"], hover_fill=COLORS["selected"], fg=COLORS["text"],
            outline=COLORS["border"], font=("Segoe UI", 7, "bold")
        )
        eraser.pack(side="left", padx=(5, 0))
        text_btn = SoftButton(
            toolbar, text="Texto", image=self.ui_images["tool_text"],
            command=lambda: self._set_scratch_tool("text"), width=78, height=32, radius=9,
            fill=COLORS["neutral"], hover_fill=COLORS["selected"], fg=COLORS["text"],
            outline=COLORS["border"], font=("Segoe UI", 7, "bold")
        )
        text_btn.pack(side="left", padx=(5, 0))
        self.scratch_tool_buttons = {"brush": brush, "eraser": eraser, "text": text_btn}
        self._update_scratch_tool_buttons()

        save_btn = SoftButton(
            toolbar, text="Salvar PNG", image=self.ui_images["tool_download"],
            command=self._save_scratch_png, width=106, height=32, radius=9, fill=COLORS["accent"],
            hover_fill=COLORS["accent_dark"], fg="white", outline=darken(COLORS["accent"], 0.18),
            font=("Segoe UI", 7, "bold")
        )
        save_btn.pack(side="right")

        paper = tk.Frame(self.content, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        paper.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.scratch_canvas = tk.Canvas(paper, bg="#fffef8", highlightthickness=0, cursor="pencil")
        self.scratch_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.scratch_canvas.bind("<ButtonPress-1>", self._scratch_press)
        self.scratch_canvas.bind("<B1-Motion>", self._scratch_move)
        self.scratch_canvas.bind("<ButtonRelease-1>", self._scratch_release)
        self.after_idle(self._redraw_scratch)

    def _set_scratch_tool(self, tool):
        self._commit_scratch_text_entry()
        self.scratch_tool = tool
        self.scratch_active_id = None
        if self.scratch_canvas:
            cursors = {"brush": "pencil", "eraser": "dotbox", "text": "xterm"}
            self.scratch_canvas.configure(cursor=cursors.get(tool, "arrow"))
        self._update_scratch_tool_buttons()

    def _update_scratch_tool_buttons(self):
        for name, button in self.scratch_tool_buttons.items():
            active = name == self.scratch_tool
            button.set_style(
                fill=COLORS["selected"] if active else COLORS["neutral"],
                fg=COLORS["text"],
                hover_fill=lighten(COLORS["selected"] if active else COLORS["neutral"], 0.05),
                outline=COLORS["border"],
            )
            button.set_selected(active)

    def _scratch_press(self, event):
        if not self.scratch_canvas:
            return
        if self.scratch_tool == "eraser":
            self._erase_stroke_at(event.x, event.y)
            return
        if self.scratch_tool == "text":
            self._begin_scratch_text_entry(event.x, event.y)
            return
        stroke_id = self.scratch_next_id
        self.scratch_next_id += 1
        stroke = {
            "id": stroke_id,
            "points": [(event.x, event.y)],
            "color": "#2d2926",
            "width": 3,
            "item": None,
        }
        item = self.scratch_canvas.create_line(
            event.x, event.y, event.x + 1, event.y + 1,
            fill=stroke["color"], width=stroke["width"],
            smooth=True, splinesteps=12, capstyle="round",
            tags=(f"stroke_{stroke_id}",)
        )
        stroke["item"] = item
        self.scratch_strokes.append(stroke)
        self.scratch_active_id = stroke_id

    def _begin_scratch_text_entry(self, x, y):
        self._commit_scratch_text_entry()
        if not self.scratch_canvas:
            return
        entry = tk.Entry(
            self.scratch_canvas, font=("Segoe UI", 10),
            bg="#fffef8", fg="#2d2926", insertbackground="#2d2926",
            relief="solid", bd=1
        )
        window_id = self.scratch_canvas.create_window(
            x, y, anchor="nw", window=entry, width=190, height=28, tags=("text_editor",)
        )
        self.scratch_text_entry = entry
        self.scratch_text_window = window_id
        self.scratch_text_position = (x, y)
        entry.focus_set()
        entry.bind("<Return>", lambda _e: self._commit_scratch_text_entry())
        entry.bind("<Escape>", lambda _e: self._cancel_scratch_text_entry())

    def _commit_scratch_text_entry(self):
        entry = getattr(self, "scratch_text_entry", None)
        if entry is None:
            return
        try:
            value = entry.get().strip()
        except tk.TclError:
            value = ""
        pos = getattr(self, "scratch_text_position", (12, 12))
        if self.scratch_canvas and self.scratch_text_window is not None:
            try:
                self.scratch_canvas.delete(self.scratch_text_window)
            except tk.TclError:
                pass
        try:
            entry.destroy()
        except tk.TclError:
            pass
        self.scratch_text_entry = None
        self.scratch_text_window = None
        if not value or not self.scratch_canvas:
            return
        text_id = self.scratch_next_text_id
        self.scratch_next_text_id += 1
        x, y = pos
        item = self.scratch_canvas.create_text(
            x, y, text=value, anchor="nw", fill="#2d2926",
            font=("Segoe UI", 11), tags=(f"text_{text_id}",)
        )
        self.scratch_texts.append({
            "id": text_id, "x": x, "y": y, "text": value,
            "color": "#2d2926", "size": 11, "item": item
        })

    def _cancel_scratch_text_entry(self):
        entry = getattr(self, "scratch_text_entry", None)
        if self.scratch_canvas and self.scratch_text_window is not None:
            try:
                self.scratch_canvas.delete(self.scratch_text_window)
            except tk.TclError:
                pass
        if entry is not None:
            try:
                entry.destroy()
            except tk.TclError:
                pass
        self.scratch_text_entry = None
        self.scratch_text_window = None

    def _scratch_move(self, event):
        if not self.scratch_canvas:
            return
        if self.scratch_tool == "eraser":
            self._erase_stroke_at(event.x, event.y)
            return
        if self.scratch_active_id is None:
            return
        stroke = next((s for s in self.scratch_strokes if s["id"] == self.scratch_active_id), None)
        if not stroke:
            return
        stroke["points"].append((event.x, event.y))
        coords = []
        for x, y in stroke["points"]:
            coords.extend([x, y])
        if len(coords) == 2:
            coords.extend([coords[0] + 1, coords[1] + 1])
        self.scratch_canvas.coords(stroke["item"], *coords)

    def _scratch_release(self, _event):
        self.scratch_active_id = None

    def _erase_stroke_at(self, x, y):
        if not self.scratch_canvas:
            return
        items = self.scratch_canvas.find_overlapping(x - 9, y - 9, x + 9, y + 9)
        for item in reversed(items):
            tags = self.scratch_canvas.gettags(item)
            stroke_tag = next((tag for tag in tags if tag.startswith("stroke_")), None)
            text_tag = next((tag for tag in tags if tag.startswith("text_")), None)
            if stroke_tag:
                try:
                    stroke_id = int(stroke_tag.split("_", 1)[1])
                except ValueError:
                    continue
                self.scratch_canvas.delete(item)
                self.scratch_strokes = [s for s in self.scratch_strokes if s["id"] != stroke_id]
                if self.scratch_active_id == stroke_id:
                    self.scratch_active_id = None
                break
            if text_tag:
                try:
                    text_id = int(text_tag.split("_", 1)[1])
                except ValueError:
                    continue
                self.scratch_canvas.delete(item)
                self.scratch_texts = [t for t in self.scratch_texts if t["id"] != text_id]
                break

    def _redraw_scratch(self):
        if not self.scratch_canvas or not self.scratch_canvas.winfo_exists():
            return
        self.scratch_canvas.delete("all")
        for stroke in self.scratch_strokes:
            coords = []
            for x, y in stroke["points"]:
                coords.extend([x, y])
            if len(coords) == 2:
                coords.extend([coords[0] + 1, coords[1] + 1])
            item = self.scratch_canvas.create_line(
                *coords, fill=stroke["color"], width=stroke["width"],
                smooth=True, splinesteps=12, capstyle="round",
                tags=(f"stroke_{stroke['id']}",)
            )
            stroke["item"] = item
        for text_item in self.scratch_texts:
            item = self.scratch_canvas.create_text(
                text_item["x"], text_item["y"], text=text_item["text"],
                anchor="nw", fill=text_item["color"],
                font=("Segoe UI", text_item.get("size", 11)),
                tags=(f"text_{text_item['id']}",)
            )
            text_item["item"] = item

    def _save_scratch_png(self):
        if not self.scratch_canvas:
            return
        self._commit_scratch_text_entry()
        self.scratch_canvas.update_idletasks()
        width = max(1, self.scratch_canvas.winfo_width())
        height = max(1, self.scratch_canvas.winfo_height())
        folder = Path(self.png_folder).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Salvar PNG", f"Não foi possível acessar a pasta configurada.\n\n{exc}", parent=self)
            return
        default_name = f"PinesJournal_Bloco_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = folder / default_name

        image = Image.new("RGB", (width, height), "#fffef8")
        draw = ImageDraw.Draw(image)
        for stroke in self.scratch_strokes:
            points = stroke["points"]
            if not points:
                continue
            if len(points) == 1:
                x, y = points[0]
                r = max(1, stroke["width"] // 2)
                draw.ellipse((x - r, y - r, x + r, y + r), fill=stroke["color"])
            else:
                draw.line(points, fill=stroke["color"], width=stroke["width"], joint="curve")

        try:
            if os.name == "nt":
                font_path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "cour.ttf"
                pil_font = ImageFont.truetype(str(font_path), 15) if font_path.exists() else ImageFont.load_default()
            else:
                candidate = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
                pil_font = ImageFont.truetype(str(candidate), 15) if candidate.exists() else ImageFont.load_default()
        except Exception:
            pil_font = ImageFont.load_default()

        for text_item in self.scratch_texts:
            draw.text((text_item["x"], text_item["y"]), text_item["text"], fill=text_item["color"], font=pil_font)

        try:
            image.save(path, "PNG")
        except OSError as exc:
            messagebox.showerror("Salvar PNG", f"Não foi possível salvar a imagem.\n\n{exc}", parent=self)
            return
        messagebox.showinfo("Bloco salvo", f"Imagem salva em:\n{path}", parent=self)

    def show_settings(self):
        self.current_view = "settings"
        self._set_active_nav("settings")
        self.clear_content()

        scroll = ScrollableFrame(self.content, bg=COLORS["bg"])
        scroll.pack(fill="both", expand=True, padx=14, pady=12)

        title = tk.Label(scroll.inner, text="Configurações", bg=COLORS["bg"], fg=COLORS["text"], font=SECTION_FONT)
        title.pack(anchor="w", pady=(0, 8))

        theme_card = self._settings_card(scroll.inner, "Cor do tema")
        theme_row = tk.Frame(theme_card, bg=COLORS["panel"])
        theme_row.pack(fill="x", pady=(4, 2))
        for name, palette in THEMES.items():
            selected = name == self.theme_name
            btn = SoftButton(
                theme_row, text=name, command=lambda n=name: self._change_theme(n),
                width=104, height=30, radius=9, fill=palette["accent"],
                hover_fill=palette["accent_dark"], fg="white",
                outline=(darken(palette["accent"], 0.28) if selected else darken(palette["accent"], 0.12)),
                font=BUTTON_FONT, compound="center"
            )
            btn.pack(side="left", expand=True, fill="x", padx=3)

        behavior = self._settings_card(scroll.inner, "Comportamento", top=9)
        self.startup_var = tk.BooleanVar(value=startup_enabled())
        startup_check = self._settings_check(behavior, "Iniciar com o Windows", self.startup_var, self._toggle_startup)
        if os.name != "nt":
            startup_check.configure(state="disabled")

        self.topmost_var = tk.BooleanVar(value=self.always_on_top)
        self._settings_check(behavior, "Manter janela sempre no topo", self.topmost_var, self._toggle_topmost)

        self.confirm_delete_var = tk.BooleanVar(value=self.confirm_delete)
        self._settings_check(behavior, "Confirmar antes de excluir tarefas", self.confirm_delete_var, self._toggle_confirm_delete)

        png_card = self._settings_card(scroll.inner, "Pasta dos PNGs do Bloco de Notas", top=9)
        tk.Label(
            png_card, text="As imagens salvas pelo Bloco de Notas serão gravadas nesta pasta.",
            bg=COLORS["panel"], fg=COLORS["muted"], font=SMALL_FONT
        ).pack(anchor="w", pady=(1, 5))
        png_row = tk.Frame(png_card, bg=COLORS["panel"])
        png_row.pack(fill="x")
        self.png_folder_var = tk.StringVar(value=str(self.png_folder))
        png_entry = tk.Entry(png_row, textvariable=self.png_folder_var, font=BODY_FONT, relief="solid", bd=1)
        png_entry.pack(side="left", fill="x", expand=True, ipady=4)
        png_entry.bind("<Return>", lambda _e: self._save_png_folder_from_entry())
        png_entry.bind("<FocusOut>", lambda _e: self._save_png_folder_from_entry(silent=True))
        SoftButton(
            png_row, text="Escolher", command=self._choose_png_folder, width=76, height=28, radius=8,
            fill=COLORS["neutral"], hover_fill=COLORS["selected"], fg=COLORS["text"],
            outline=COLORS["border"], font=BUTTON_FONT, compound="center"
        ).pack(side="left", padx=(6, 0))

        data_card = self._settings_card(scroll.inner, "Dados locais", top=9)
        tk.Label(
            data_card, text="As tarefas ficam salvas neste computador.",
            bg=COLORS["panel"], fg=COLORS["muted"], font=SMALL_FONT
        ).pack(anchor="w", pady=(2, 5))
        data_row = tk.Frame(data_card, bg=COLORS["panel"])
        data_row.pack(fill="x")
        self.data_folder_var = tk.StringVar(value=str(DB_PATH.parent))
        data_entry = tk.Entry(
            data_row, textvariable=self.data_folder_var, font=BODY_FONT,
            relief="solid", bd=1, state="readonly",
            readonlybackground=COLORS["panel"], fg=COLORS["text"]
        )
        data_entry.pack(side="left", fill="x", expand=True, ipady=4)
        SoftButton(
            data_row, text="Abrir", command=self._open_data_folder,
            width=76, height=28, radius=8,
            fill=COLORS["neutral"], hover_fill=COLORS["selected"], fg=COLORS["text"],
            outline=COLORS["border"], font=BUTTON_FONT, compound="center"
        ).pack(side="left", padx=(6, 0))

    def _choose_png_folder(self):
        current = str(self.png_folder)
        selected = filedialog.askdirectory(parent=self, title="Escolher pasta para os PNGs", initialdir=current if Path(current).exists() else str(Path.home()))
        if not selected:
            return
        self.png_folder = Path(selected)
        self.repo.set_setting("png_folder", str(self.png_folder))
        if hasattr(self, "png_folder_var"):
            self.png_folder_var.set(str(self.png_folder))

    def _save_png_folder_from_entry(self, silent=False):
        if not hasattr(self, "png_folder_var"):
            return
        raw = self.png_folder_var.get().strip()
        if not raw:
            return
        folder = Path(raw).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            if not silent:
                messagebox.showerror("Pasta inválida", f"Não foi possível usar esta pasta.\n\n{exc}", parent=self)
            return
        self.png_folder = folder
        self.repo.set_setting("png_folder", str(folder))
        self.png_folder_var.set(str(folder))

    def _settings_card(self, parent, title, top=0):
        card = tk.Frame(parent, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1, padx=12, pady=10)
        card.pack(fill="x", pady=(top, 0))
        tk.Label(card, text=title, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        return card

    def _settings_check(self, parent, text, variable, command):
        check = tk.Checkbutton(
            parent, text=text, variable=variable, command=command,
            bg=COLORS["panel"], fg=COLORS["text"], activebackground=COLORS["panel"], activeforeground=COLORS["text"],
            selectcolor=COLORS["panel"], font=BODY_FONT, cursor="hand2", bd=0, anchor="w"
        )
        check.pack(fill="x", anchor="w", pady=3)
        return check

    def _change_theme(self, theme_name):
        if theme_name not in THEMES:
            return
        self.theme_name = theme_name
        self.repo.set_setting("theme", theme_name)
        apply_theme(theme_name)
        self._rebuild_shell("settings")

    def _toggle_startup(self):
        requested = self.startup_var.get()
        try:
            set_startup_enabled(requested)
        except Exception as exc:
            self.startup_var.set(startup_enabled())
            messagebox.showerror("Inicialização automática", f"Não foi possível alterar a inicialização automática.\n\n{exc}", parent=self)

    def _toggle_topmost(self):
        self.always_on_top = self.topmost_var.get()
        self.repo.set_setting("always_on_top", "1" if self.always_on_top else "0")
        try:
            self.attributes("-topmost", self.always_on_top)
        except tk.TclError:
            pass

    def _toggle_confirm_delete(self):
        self.confirm_delete = self.confirm_delete_var.get()
        self.repo.set_setting("confirm_delete", "1" if self.confirm_delete else "0")

    def _open_data_folder(self):
        folder = app_data_dir()
        try:
            if os.name == "nt":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            messagebox.showerror("Pasta de dados", f"Não foi possível abrir a pasta.\n\n{exc}", parent=self)


def main():
    app = TaskApp()
    app.mainloop()


if __name__ == "__main__":
    main()
