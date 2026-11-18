"""Tkinter interface. Network work stays off the UI thread."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import Cancelled, Download, DownloadError, Paused, Progress
from . import storage
from .design import (
    colors,
    FONT,
    FONT_SEMIBOLD,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_5,
    SPACE_6,
    TEXT_SIZE_BASE as TEXT_SIZE,
    TEXT_SIZE_SECTION,
    TEXT_SIZE_SMALL,
    TEXT_SIZE_TITLE,
)
from .studio import Studio


def size_text(value: float) -> str:
    return (
        f"{value / 1024 / 1024:.1f} MB"
        if value >= 1024 * 1024
        else f"{value / 1024:.0f} KB"
    )


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MP3 Desktop")
        self.geometry("920x640")
        self.minsize(700, 520)
        self.db = storage.connect()
        settings = storage.load_settings()
        self.folder = tk.StringVar(
            value=settings.get("folder", str(Path.home() / "Music"))
        )
        self.url = tk.StringVar()
        self.theme = tk.StringVar(value=settings.get("theme", "Claro"))
        self.limit = tk.StringVar(value=str(settings.get("limit_mb", 500)))
        self.status = tk.StringVar(value="Pronto para baixar um MP3 por URL direta.")
        self.events: queue.Queue = queue.Queue()
        self.job: Download | None = None
        self.worker: threading.Thread | None = None
        self.active = False
        self.paused = False
        self.last_path: Path | None = None
        self._build()
        self._apply_theme()
        self._refresh_history()
        self.after(100, self._poll)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _card(self, parent, **kw) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Card.TFrame", **kw)
        return frame

    def _section(self, parent, text: str, *, icon: str = "") -> ttk.Label:
        label = ttk.Label(
            parent,
            text=(f"{icon}  {text}" if icon else text),
            style="Section.TLabel",
        )
        label.pack(anchor="w", pady=(0, 10))
        return label

    def _primary_button(self, parent, text: str, command, **kw) -> ttk.Button:
        return ttk.Button(
            parent, text=text, command=command, style="Primary.TButton", **kw
        )

    def _secondary_button(self, parent, text: str, command, **kw) -> ttk.Button:
        return ttk.Button(
            parent, text=text, command=command, style="Secondary.TButton", **kw
        )

    def _build(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.main = tk.Frame(self, bg=self._colors_bg())
        self.main.pack(fill="both", expand=True)

        inner = ttk.Frame(self.main, padding=SPACE_6)
        inner.pack(fill="both", expand=True)

        header = ttk.Frame(inner)
        header.pack(fill="x", pady=(0, SPACE_5))
        ttk.Label(header, text="MP3 Desktop", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Baixe arquivos MP3 disponibilizados diretamente para download.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))
        self.tabs = ttk.Notebook(inner)
        self.tabs.pack(fill="both", expand=True)

        overview = ttk.Frame(self.tabs, padding=SPACE_6)
        download = ttk.Frame(self.tabs, padding=SPACE_6)
        history = ttk.Frame(self.tabs, padding=SPACE_6)
        projects = ttk.Frame(self.tabs, padding=SPACE_6)
        settings = ttk.Frame(self.tabs, padding=SPACE_6)

        self.tabs.add(overview, text="Visão geral")
        self.tabs.add(download, text="Downloads")
        self.tabs.add(history, text="Histórico")
        self.studio = Studio(self.tabs, self.db)
        self.tabs.add(self.studio, text="Estúdio de clipes")
        self.tabs.add(projects, text="Projetos")
        self.tabs.add(settings, text="Configurações")
        self.tabs.bind("<<NotebookTabChanged>>", self._refresh_overview)

        self.overview_text = tk.StringVar()
        ttk.Label(overview, text="Seus arquivos e clipes", style="Section.TLabel").pack(
            anchor="w", pady=(0, 12)
        )
        ttk.Label(
            overview,
            textvariable=self.overview_text,
            style="Muted.TLabel",
            wraplength=600,
        ).pack(anchor="w", pady=(0, 18))
        actions = ttk.Frame(overview)
        actions.pack(anchor="w", fill="x")
        self._primary_button(
            actions, "Novo download MP3", lambda: self.tabs.select(download)
        ).pack(side="left", padx=(0, SPACE_3))
        self._secondary_button(
            actions, "Abrir estúdio de clipes", lambda: self.tabs.select(self.studio)
        ).pack(side="left")

        self.projects = ttk.Treeview(
            projects, columns=("path", "duration", "resolution"), show="headings"
        )
        for key, label, width in (
            ("path", "Arquivo", 300),
            ("duration", "Duração", 100),
            ("resolution", "Resolução", 100),
        ):
            self.projects.heading(key, text=label)
            self.projects.column(key, width=width, anchor="w")
        self.projects.pack(fill="both", expand=True, pady=(0, 12))
        self._secondary_button(
            projects, "Abrir no estúdio", command=self._open_project
        ).pack(anchor="w")
        download.columnconfigure(0, weight=1)

        input_card = self._card(download)
        input_card.pack(fill="x", pady=(0, SPACE_5))
        input_inner = ttk.Frame(input_card, padding=SPACE_5)
        input_inner.pack(fill="both")
        input_inner.columnconfigure(0, weight=1)

        ttk.Label(
            input_inner, text="URL HTTPS do arquivo MP3", style="Section.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, SPACE_2))
        ttk.Entry(input_inner, textvariable=self.url).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, SPACE_4)
        )

        ttk.Label(input_inner, text="Pasta de destino", style="Section.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, SPACE_2)
        )
        folder_row = ttk.Frame(input_inner)
        folder_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, SPACE_4))
        folder_row.columnconfigure(0, weight=1)
        ttk.Entry(folder_row, textvariable=self.folder).grid(
            row=0, column=0, sticky="ew"
        )
        self._secondary_button(
            folder_row, "Escolher…", command=self._choose_folder
        ).grid(row=0, column=1, padx=(8, 0))

        action_card = self._card(download)
        action_card.pack(fill="x", pady=(0, SPACE_5))
        action_inner = ttk.Frame(action_card, padding=SPACE_5)
        action_inner.pack(fill="both")

        buttons = ttk.Frame(action_inner)
        buttons.pack(anchor="w", pady=(0, 14))
        self.start_button = self._primary_button(
            buttons, "Baixar MP3", command=self._start
        )
        self.start_button.pack(side="left")
        self.pause_button = self._secondary_button(
            buttons, text="Pausar", command=self._pause, state="disabled"
        )
        self.pause_button.pack(side="left", padx=SPACE_2)
        self.cancel_button = self._secondary_button(
            buttons, text="Cancelar", command=self._cancel, state="disabled"
        )
        self.cancel_button.pack(side="left")
        self.open_button = self._secondary_button(
            buttons, text="Abrir pasta", command=self._open_last, state="disabled"
        )
        self.open_button.pack(side="left", padx=SPACE_2)

        self.progress = ttk.Progressbar(action_inner, maximum=100)
        self.progress.pack(fill="x", pady=(0, SPACE_3))
        ttk.Label(
            action_inner, textvariable=self.status, style="Muted.TLabel", wraplength=700
        ).pack(anchor="w")
        ttk.Label(history, text="Histórico de downloads", style="Section.TLabel").pack(
            anchor="w", pady=(0, SPACE_3)
        )
        self.history = ttk.Treeview(
            history,
            columns=("size", "date", "path"),
            show="headings",
            selectmode="browse",
        )
        for key, label, width in (
            ("size", "Tamanho", 90),
            ("date", "Data", 150),
            ("path", "Arquivo", 420),
        ):
            self.history.heading(key, text=label)
            self.history.column(key, width=width, anchor="w")
        self.history.pack(fill="both", expand=True, pady=(0, SPACE_4))
        self._secondary_button(
            history, "Abrir pasta do selecionado", command=self._open_selected
        ).pack(anchor="w")

        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Tema", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=SPACE_2
        )
        ttk.Combobox(
            settings,
            textvariable=self.theme,
            values=("Claro", "Escuro"),
            state="readonly",
            width=15,
        ).grid(row=0, column=1, sticky="w", padx=SPACE_3)

        ttk.Label(
            settings, text="Limite por arquivo (MB)", style="Section.TLabel"
        ).grid(row=1, column=0, sticky="w", pady=SPACE_2)
        ttk.Entry(settings, textvariable=self.limit, width=16).grid(
            row=1, column=1, sticky="w", padx=SPACE_3
        )

        self._primary_button(settings, "Salvar configurações", command=self._save).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=SPACE_5
        )

        ttk.Label(
            settings,
            text="Idioma: português brasileiro  •  Downloads simultâneos: 1",
            style="Muted.TLabel",
        ).grid(row=3, column=0, columnspan=2, sticky="w")

    def _apply_theme(self):
        dark = self.theme.get() == "Escuro"
        c = colors(dark)

        self.configure(bg=c["bg"])
        self.style.theme_use("clam")

        self.style.configure("TFrame", background=c["bg"])
        self.style.configure(
            "Card.TFrame",
            background=c["surface"],
            relief="solid",
            borderwidth=1,
        )
        self.style.map(
            "Card.TFrame",
            background=[("active", c["border"])],
        )
        self.style.configure(
            "TLabel",
            background=c["bg"],
            foreground=c["text_primary"],
            font=(FONT, TEXT_SIZE),
        )
        self.style.configure(
            "Section.TLabel",
            background=c["bg"],
            foreground=c["text_primary"],
            font=(FONT_SEMIBOLD, TEXT_SIZE_SECTION),
        )
        self.style.configure(
            "Muted.TLabel",
            background=c["bg"],
            foreground=c["text_muted"],
            font=(FONT, TEXT_SIZE_SMALL),
        )
        self.style.configure(
            "Title.TLabel",
            background=c["bg"],
            foreground=c["text_primary"],
            font=(FONT_SEMIBOLD, TEXT_SIZE_TITLE),
        )
        self.style.configure(
            "Subtitle.TLabel",
            background=c["bg"],
            foreground=c["text_secondary"],
            font=(FONT, TEXT_SIZE),
        )

        self.style.configure(
            "TButton",
            background=c["surface"],
            foreground=c["text_primary"],
            font=(FONT, TEXT_SIZE),
            padding=(16, 10),
            borderwidth=1,
        )
        self.style.map(
            "TButton",
            background=[("active", c["border"]), ("disabled", c["surface"])],
            foreground=[("disabled", c["text_muted"])],
        )
        self.style.configure(
            "Primary.TButton",
            background=c["primary"],
            foreground=c["ink"],
            font=(FONT_SEMIBOLD, TEXT_SIZE),
            padding=(20, 12),
            borderwidth=0,
        )
        self.style.map(
            "Primary.TButton",
            background=[("active", c["primary_hover"]), ("disabled", c["text_muted"])],
        )
        self.style.configure(
            "Secondary.TButton",
            background=c["surface"],
            foreground=c["text_primary"],
            font=(FONT, TEXT_SIZE),
            padding=(16, 10),
            borderwidth=1,
        )
        self.style.map(
            "Secondary.TButton",
            background=[("active", c["border"])],
        )

        self.style.configure("TNotebook", background=c["bg"], borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background=c["surface"],
            foreground=c["text_secondary"],
            font=(FONT, TEXT_SIZE),
            padding=(20, 12),
            borderwidth=0,
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", c["primary"]), ("active", c["border"])],
            foreground=[("selected", c["ink"]), ("active", c["text_primary"])],
        )

        self.style.configure(
            "TEntry",
            fieldbackground=c["surface"],
            foreground=c["text_primary"],
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
            insertcolor=c["text_primary"],
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=c["surface"],
            foreground=c["text_primary"],
            background=c["surface"],
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", c["surface"])],
            background=[("readonly", c["surface"])],
            foreground=[("readonly", c["text_primary"])],
        )

        self.style.configure(
            "TProgressbar",
            background=c["primary"],
            troughcolor=c["surface"],
            bordercolor=c["border"],
            lightcolor=c["primary"],
            darkcolor=c["primary"],
        )

        self.style.configure(
            "Treeview",
            background=c["surface"],
            fieldbackground=c["surface"],
            foreground=c["text_primary"],
            rowheight=34,
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
        )
        self.style.map(
            "Treeview",
            background=[("selected", c["primary_light"])],
            foreground=[("selected", c["text_primary"])],
        )
        self.style.configure(
            "Treeview.Heading",
            background=c["surface"],
            foreground=c["text_secondary"],
            font=("Segoe UI Semibold", 9),
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", c["surface_hover"])],
        )

    def _colors_bg(self) -> str:
        return colors(self.theme.get() == "Escuro")["bg"]

    def _choose_folder(self):
        chosen = filedialog.askdirectory(
            initialdir=self.folder.get() or str(Path.home())
        )
        if chosen:
            self.folder.set(chosen)

    def _save(self):
        try:
            limit = int(self.limit.get())
            if not 1 <= limit <= 10240:
                raise ValueError
            storage.save_settings(
                {
                    "folder": self.folder.get(),
                    "theme": self.theme.get(),
                    "limit_mb": limit,
                }
            )
        except (ValueError, OSError):
            messagebox.showerror(
                "Configurações",
                "Informe um limite entre 1 e 10240 MB e uma pasta válida.",
            )
            return
        self._apply_theme()
        self.status.set("Configurações salvas.")

    def _start(self):
        try:
            limit = int(self.limit.get())
            if not 1 <= limit <= 10240:
                raise ValueError
            self.job = Download(
                self.url.get(),
                Path(self.folder.get()).expanduser(),
                max_bytes=limit * 1024 * 1024,
            )
            if not self.folder.get().strip():
                raise DownloadError("Escolha uma pasta de destino.")
        except ValueError:
            messagebox.showerror("Download", "Limite de tamanho inválido.")
            return
        except DownloadError as exc:
            messagebox.showerror("Download", str(exc))
            return
        self.progress["value"] = 0
        self.active = True
        self.paused = False
        self.start_button["state"] = "disabled"
        self.cancel_button["state"] = "normal"
        self.pause_button["state"] = "disabled"
        self.status.set("Conectando…")
        self._launch()

    def _launch(self):
        job = self.job

        def work():
            try:
                path = job.run(lambda progress: self.events.put(("progress", progress)))
                self.events.put(("done", path))
            except Paused as exc:
                self.events.put(("paused", str(exc)))
            except (Cancelled, DownloadError) as exc:
                self.events.put(("error", str(exc)))
            except Exception:
                self.events.put(("error", "Falha inesperada no download."))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _pause(self):
        if self.paused:
            self.job.pause.clear()
            self.paused = False
            self.pause_button["text"] = "Pausar"
            self.pause_button["state"] = "disabled"
            self.status.set("Retomando…")
            self._launch()
        elif self.job and self.job.resumable:
            self.job.pause.set()
            self.pause_button["state"] = "disabled"
            self.status.set("Pausando…")

    def _cancel(self):
        if self.job:
            self.job.cancel.set()
            if self.paused:
                self.job.partial.unlink(missing_ok=True)
                self._finish("Download cancelado.")
            else:
                self.status.set("Cancelando…")

    def _poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    p: Progress = value
                    self.progress["value"] = (
                        p.received / p.total * 100 if p.total else 0
                    )
                    self.pause_button["state"] = "normal" if p.resumable else "disabled"
                    seconds = (
                        f" • {int((p.total - p.received) / p.speed)} s restantes"
                        if p.total and p.speed
                        else ""
                    )
                    self.status.set(
                        f"{p.name} • {size_text(p.received)}"
                        + (f" / {size_text(p.total)}" if p.total else "")
                        + f" • {size_text(p.speed)}/s"
                        + seconds
                    )
                elif kind == "paused":
                    self.paused = True
                    self.pause_button["text"] = "Retomar"
                    self.pause_button["state"] = "normal"
                    self.status.set(value)
                elif kind == "done":
                    self.last_path = value
                    storage.add(value, self.db)
                    self._refresh_history()
                    self.open_button["state"] = "normal"
                    self.progress["value"] = 100
                    self._finish(f"Concluído: {value.name}")
                elif kind == "error":
                    self._finish(value)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _finish(self, message):
        self.active = False
        self.paused = False
        self.status.set(message)
        self.start_button["state"] = "normal"
        self.pause_button["state"] = "disabled"
        self.pause_button["text"] = "Pausar"
        self.cancel_button["state"] = "disabled"

    def _refresh_history(self):
        for item in self.history.get_children():
            self.history.delete(item)
        for name, path, size, date in storage.list_downloads(self.db):
            self.history.insert("", "end", values=(size_text(size), date, path))

    def _refresh_overview(self, _event=None):
        videos = storage.list_videos(self.db)
        downloads = storage.list_downloads(self.db)
        exports = storage.list_exports(self.db)
        if hasattr(self, "overview_text"):
            self.overview_text.set(
                f"{len(downloads)} MP3 no histórico  •  {len(videos)} vídeo(s) importado(s)  •  {len(exports)} tarefa(s) de exportação"
            )
        if hasattr(self, "projects"):
            for item in self.projects.get_children():
                self.projects.delete(item)
            for video_id, path, duration, width, height, _size in videos:
                self.projects.insert(
                    "",
                    "end",
                    iid=str(video_id),
                    values=(path, f"{duration:.1f} s", f"{width}×{height}"),
                )

    def _open_project(self):
        selected = self.projects.selection()
        if not selected:
            return
        self.studio._refresh_videos()
        for index, row in enumerate(self.studio.video_rows):
            if row[0] == int(selected[0]):
                self.studio.videos.current(index)
                self.studio._select_video()
                self.tabs.select(self.studio)
                break

    def _open_folder(self, path: Path):
        if not path.exists():
            messagebox.showerror("Pasta", "A pasta não existe mais.")
            return
        if os.name == "nt":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _open_last(self):
        if self.last_path:
            self._open_folder(self.last_path.parent)

    def _open_selected(self):
        selection = self.history.selection()
        if selection:
            self._open_folder(Path(self.history.item(selection[0], "values")[2]).parent)

    def _close(self):
        if self.active and not messagebox.askyesno(
            "Sair", "Cancelar o download e sair?"
        ):
            return
        if self.job and self.active:
            self.job.cancel.set()
        self.db.close()
        self.destroy()


def main():
    App().mainloop()
