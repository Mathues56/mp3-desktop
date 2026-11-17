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
        self.geometry("850x580")
        self.minsize(650, 460)
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

    def _build(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.main = ttk.Frame(self, padding=22)
        self.main.pack(fill="both", expand=True)
        ttk.Label(self.main, text="MP3 Desktop", font=("Segoe UI Semibold", 22)).pack(
            anchor="w"
        )
        ttk.Label(
            self.main,
            text="Baixe arquivos MP3 disponibilizados diretamente para download.",
        ).pack(anchor="w", pady=(2, 18))
        self.tabs = ttk.Notebook(self.main)
        self.tabs.pack(fill="both", expand=True)
        overview = ttk.Frame(self.tabs, padding=20)
        download = ttk.Frame(self.tabs, padding=20)
        history = ttk.Frame(self.tabs, padding=20)
        projects = ttk.Frame(self.tabs, padding=20)
        settings = ttk.Frame(self.tabs, padding=20)
        self.tabs.add(overview, text="Visão geral")
        self.tabs.add(download, text="Downloads")
        self.tabs.add(history, text="Histórico")
        self.studio = Studio(self.tabs, self.db)
        self.tabs.add(self.studio, text="Estúdio de clipes")
        self.tabs.add(projects, text="Projetos")
        self.tabs.add(settings, text="Configurações")
        self.tabs.bind("<<NotebookTabChanged>>", self._refresh_overview)
        self.overview_text = tk.StringVar()
        ttk.Label(
            overview, text="Seus arquivos e clipes", font=("Segoe UI Semibold", 16)
        ).pack(anchor="w", pady=(0, 12))
        ttk.Label(overview, textvariable=self.overview_text, wraplength=550).pack(
            anchor="w", pady=(0, 18)
        )
        ttk.Button(
            overview,
            text="Novo download MP3",
            command=lambda: self.tabs.select(download),
        ).pack(anchor="w", pady=5)
        ttk.Button(
            overview,
            text="Abrir estúdio de clipes",
            command=lambda: self.tabs.select(self.studio),
        ).pack(anchor="w", pady=5)
        self.projects = ttk.Treeview(
            projects, columns=("path", "duration", "resolution"), show="headings"
        )
        for key, label in (
            ("path", "Arquivo"),
            ("duration", "Duração"),
            ("resolution", "Resolução"),
        ):
            self.projects.heading(key, text=label)
        self.projects.pack(fill="both", expand=True)
        ttk.Button(projects, text="Abrir no estúdio", command=self._open_project).pack(
            anchor="w", pady=10
        )
        self._refresh_overview()
        download.columnconfigure(0, weight=1)
        ttk.Label(download, text="URL HTTPS do arquivo MP3").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Entry(download, textvariable=self.url).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(5, 15)
        )
        ttk.Label(download, text="Pasta de destino").grid(row=2, column=0, sticky="w")
        ttk.Entry(download, textvariable=self.folder).grid(
            row=3, column=0, sticky="ew", pady=(5, 15)
        )
        ttk.Button(download, text="Escolher…", command=self._choose_folder).grid(
            row=3, column=1, padx=(8, 0), pady=(5, 15)
        )
        buttons = ttk.Frame(download)
        buttons.grid(row=4, column=0, columnspan=2, sticky="w")
        self.start_button = ttk.Button(buttons, text="Baixar MP3", command=self._start)
        self.start_button.pack(side="left")
        self.pause_button = ttk.Button(
            buttons, text="Pausar", command=self._pause, state="disabled"
        )
        self.pause_button.pack(side="left", padx=8)
        self.cancel_button = ttk.Button(
            buttons, text="Cancelar", command=self._cancel, state="disabled"
        )
        self.cancel_button.pack(side="left")
        self.open_button = ttk.Button(
            buttons, text="Abrir pasta", command=self._open_last, state="disabled"
        )
        self.open_button.pack(side="left", padx=8)
        self.progress = ttk.Progressbar(download, maximum=100)
        self.progress.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(25, 8))
        ttk.Label(download, textvariable=self.status, wraplength=600).grid(
            row=6, column=0, columnspan=2, sticky="w"
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
            ("path", "Arquivo", 450),
        ):
            self.history.heading(key, text=label)
            self.history.column(key, width=width)
        self.history.pack(fill="both", expand=True)
        ttk.Button(
            history, text="Abrir pasta do selecionado", command=self._open_selected
        ).pack(anchor="w", pady=12)
        ttk.Label(settings, text="Tema").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Combobox(
            settings,
            textvariable=self.theme,
            values=("Claro", "Escuro"),
            state="readonly",
            width=15,
        ).grid(row=0, column=1, sticky="w", padx=12)
        ttk.Label(settings, text="Limite por arquivo (MB)").grid(
            row=1, column=0, sticky="w", pady=8
        )
        ttk.Entry(settings, textvariable=self.limit, width=16).grid(
            row=1, column=1, sticky="w", padx=12
        )
        ttk.Button(settings, text="Salvar configurações", command=self._save).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=20
        )
        ttk.Label(
            settings, text="Idioma: português brasileiro  •  Downloads simultâneos: 1"
        ).grid(row=3, column=0, columnspan=2, sticky="w")

    def _apply_theme(self):
        dark = self.theme.get() == "Escuro"
        bg, fg, field = (
            ("#151b23", "#e6edf3", "#242d38")
            if dark
            else ("#f6f8fa", "#1f2937", "#ffffff")
        )
        self.configure(bg=bg)
        self.style.configure("TFrame", background=bg)
        self.style.configure(
            "TLabel", background=bg, foreground=fg, font=("Segoe UI", 10)
        )
        self.style.configure("TButton", padding=8, font=("Segoe UI", 10))
        self.style.configure("TNotebook", background=bg)
        self.style.configure(
            "TNotebook.Tab", background=field, foreground=fg, padding=(15, 8)
        )
        self.style.configure("TEntry", fieldbackground=field, foreground=fg)
        self.style.configure("TCombobox", fieldbackground=field, foreground=fg)
        self.style.configure(
            "Treeview", background=field, fieldbackground=field, foreground=fg
        )
        self.style.configure("Treeview.Heading", background=bg, foreground=fg)

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
