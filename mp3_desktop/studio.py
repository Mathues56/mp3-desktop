"""Manual clip studio and persistent sequential export queue."""

from __future__ import annotations

import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import storage
from .media import (
    Clip,
    MediaError,
    Video,
    binary,
    export,
    probe,
    validate_clip,
    PRESETS,
)


class Studio(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, padding=16)
        self.db = db
        self.events: queue.Queue = queue.Queue()
        self.video_id: int | None = None
        self.video: Video | None = None
        self.cancel = threading.Event()
        self.running = False
        self.status = tk.StringVar(value="Importe um vídeo local para começar.")
        self.preset = tk.StringVar(value="Original")
        self.quality = tk.StringVar(value="23")
        self.start = tk.StringVar(value="0")
        self.end = tk.StringVar(value="10")
        self.title_var = tk.StringVar(value="Clipe 1")
        self.folder = tk.StringVar(value=str(Path.home() / "Videos"))
        self._build()
        self._refresh_videos()
        self._refresh_exports()
        self._start_next()
        self.after(100, self._poll)

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Button(top, text="Importar vídeos…", command=self._import).pack(side="left")
        ttk.Button(top, text="Pré-visualizar no FFplay", command=self._preview).pack(
            side="left", padx=8
        )
        ttk.Label(top, textvariable=self.status, wraplength=480).pack(
            side="left", padx=12
        )
        self.videos = ttk.Combobox(self, state="readonly")
        self.videos.grid(row=1, column=0, sticky="ew", pady=(12, 4))
        self.videos.bind("<<ComboboxSelected>>", self._select_video)
        body = ttk.Panedwindow(self, orient="horizontal")
        body.grid(row=2, column=0, sticky="nsew")
        left = ttk.Frame(body, padding=10)
        right = ttk.Frame(body, padding=10)
        body.add(left, weight=3)
        body.add(right, weight=2)
        ttk.Label(left, text="Timeline (segundos)").pack(anchor="w")
        self.timeline = ttk.Scale(left, from_=0, to=1, command=self._seek)
        self.timeline.pack(fill="x", pady=8)
        self.position = ttk.Label(left, text="0 s")
        self.position.pack(anchor="w")
        form = ttk.Frame(left)
        form.pack(fill="x", pady=12)
        for col, (label, var) in enumerate(
            (
                ("Início (s)", self.start),
                ("Fim (s)", self.end),
                ("Título", self.title_var),
            )
        ):
            ttk.Label(form, text=label).grid(row=0, column=col, sticky="w")
            ttk.Entry(form, textvariable=var, width=14 if col < 2 else 23).grid(
                row=1, column=col, sticky="ew", padx=(0, 8)
            )
        ttk.Button(left, text="Adicionar intervalo", command=self._add_clip).pack(
            anchor="w"
        )
        ttk.Label(left, text="Clipe selecionado").pack(anchor="w", pady=(15, 3))
        self.clips = ttk.Treeview(
            left,
            columns=("start", "end", "title"),
            show="headings",
            height=5,
            selectmode="extended",
        )
        for key, label in (("start", "Início"), ("end", "Fim"), ("title", "Título")):
            self.clips.heading(key, text=label)
            self.clips.column(key, width=80 if key != "title" else 180)
        self.clips.pack(fill="both", expand=True)
        self.clips.bind("<<TreeviewSelect>>", self._select_clip)
        actions = ttk.Frame(left)
        actions.pack(anchor="w", pady=6)
        ttk.Button(actions, text="Atualizar", command=self._update_clip).pack(
            side="left"
        )
        ttk.Button(actions, text="Excluir", command=self._delete_clip).pack(
            side="left", padx=8
        )
        ttk.Label(right, text="Exportação MP4").pack(anchor="w")
        ttk.Combobox(
            right, textvariable=self.preset, values=list(PRESETS), state="readonly"
        ).pack(fill="x", pady=5)
        ttk.Label(right, text="Qualidade CRF (18 melhor, 32 menor)").pack(anchor="w")
        ttk.Entry(right, textvariable=self.quality).pack(fill="x", pady=5)
        ttk.Entry(right, textvariable=self.folder).pack(fill="x", pady=5)
        ttk.Button(right, text="Escolher pasta…", command=self._choose_folder).pack(
            anchor="w"
        )
        ttk.Button(right, text="Adicionar à fila", command=self._enqueue).pack(
            anchor="w", pady=(12, 4)
        )
        ttk.Button(
            right, text="Cancelar exportação atual", command=self.cancel.set
        ).pack(anchor="w")
        self.progress = ttk.Progressbar(right, maximum=100)
        self.progress.pack(fill="x", pady=12)
        self.exports = ttk.Treeview(
            right, columns=("title", "status"), show="headings", height=5
        )
        self.exports.heading("title", text="Clipe")
        self.exports.heading("status", text="Estado")
        self.exports.pack(fill="both", expand=True)

    def _import(self):
        paths = filedialog.askopenfilenames(
            title="Importar vídeos",
            filetypes=[("Vídeos", "*.mp4 *.mkv *.mov *.webm *.avi")],
        )
        if not paths:
            return
        self.status.set(f"Lendo {len(paths)} vídeo(s)…")

        def work():
            for path in paths:
                try:
                    self.events.put(("video", probe(Path(path))))
                except MediaError as exc:
                    self.events.put(("error", f"{Path(path).name}: {exc}"))
            self.events.put(("import_done", None))

        threading.Thread(target=work, daemon=True).start()

    def _refresh_videos(self):
        self.video_rows = storage.list_videos(self.db)
        self.videos["values"] = [
            f"{Path(row[1]).name} • {row[2]:.1f} s • {row[3]}×{row[4]}"
            for row in self.video_rows
        ]
        if self.video_id is None and self.video_rows:
            self.videos.current(0)
            self._select_video()

    def _select_video(self, _event=None):
        index = self.videos.current()
        if index < 0:
            return
        row = self.video_rows[index]
        self.video_id = row[0]
        self.video = Video(Path(row[1]), row[2], row[3], row[4], row[5])
        self.timeline.configure(to=row[2])
        self.end.set(str(min(10.0, row[2])))
        self.status.set(
            f"{self.video.path.name} • {row[2]:.1f} s • {row[3]}×{row[4]} • {row[5] / 1048576:.1f} MB"
        )
        self._refresh_clips()

    def _seek(self, value):
        self.position.configure(text=f"{float(value):.1f} s")

    def _preview(self):
        if not self.video:
            return
        try:
            subprocess.Popen(
                [
                    binary("ffplay"),
                    "-autoexit",
                    "-ss",
                    str(self.timeline.get()),
                    str(self.video.path),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (MediaError, OSError) as exc:
            messagebox.showerror("Pré-visualização", str(exc))

    def _clip_from_form(self) -> Clip:
        if self.video_id is None or self.video is None:
            raise MediaError("Importe e selecione um vídeo.")
        try:
            clip = Clip(
                self.video_id,
                float(self.start.get()),
                float(self.end.get()),
                self.title_var.get().strip(),
            )
        except ValueError as exc:
            raise MediaError("Informe tempos numéricos em segundos.") from exc
        validate_clip(clip, self.video.duration)
        return clip

    def _add_clip(self):
        try:
            storage.add_clip(self._clip_from_form(), self.db)
            self._refresh_clips()
        except MediaError as exc:
            messagebox.showerror("Intervalo", str(exc))

    def _refresh_clips(self):
        for item in self.clips.get_children():
            self.clips.delete(item)
        if self.video_id:
            for clip_id, start, end, title in storage.list_clips(
                self.video_id, self.db
            ):
                self.clips.insert(
                    "", "end", iid=str(clip_id), values=(start, end, title)
                )

    def _select_clip(self, _event=None):
        selected = self.clips.selection()
        if selected:
            start, end, title = self.clips.item(selected[0], "values")
            self.start.set(start)
            self.end.set(end)
            self.title_var.set(title)
            self.timeline.set(float(start))

    def _update_clip(self):
        selected = self.clips.selection()
        if not selected:
            return
        try:
            clip = self._clip_from_form()
        except MediaError as exc:
            messagebox.showerror("Intervalo", str(exc))
            return
        self.db.execute(
            "UPDATE clips SET start=?,end=?,title=? WHERE id=?",
            (clip.start, clip.end, clip.title, int(selected[0])),
        )
        self.db.commit()
        self._refresh_clips()

    def _delete_clip(self):
        selected = self.clips.selection()
        if selected:
            storage.delete_clip(int(selected[0]), self.db)
            self._refresh_clips()
            self._refresh_exports()

    def _choose_folder(self):
        folder = filedialog.askdirectory(
            initialdir=self.folder.get() or str(Path.home())
        )
        if folder:
            self.folder.set(folder)

    def _enqueue(self):
        selected = self.clips.selection()
        if not selected:
            messagebox.showerror("Exportação", "Selecione um clipe.")
            return
        try:
            quality = int(self.quality.get())
            if (
                not 18 <= quality <= 32
                or self.preset.get() not in PRESETS
                or not self.folder.get().strip()
            ):
                raise ValueError
            for item in selected:
                storage.enqueue(
                    int(item),
                    Path(self.folder.get()),
                    self.preset.get(),
                    quality,
                    self.db,
                )
        except ValueError:
            messagebox.showerror(
                "Exportação", "Revise pasta, preset e qualidade (18 a 32)."
            )
            return
        self._refresh_exports()
        self._start_next()

    def _start_next(self):
        if self.running:
            return
        row = storage.next_export(self.db)
        if not row:
            return
        (
            export_id,
            clip_id,
            folder,
            preset,
            quality,
            video_id,
            start,
            end,
            title,
            path,
            duration,
            width,
            height,
            size,
        ) = row
        self.running = True
        self.cancel.clear()
        storage.update_export(export_id, "running", None, self.db)
        self._refresh_exports()
        clip = Clip(video_id, start, end, title)
        video = Video(Path(path), duration, width, height, size)

        def work():
            try:
                result = export(
                    clip,
                    video,
                    Path(folder),
                    preset,
                    quality,
                    lambda value: self.events.put(("progress", value)),
                    self.cancel,
                )
                self.events.put(("export_done", (export_id, str(result))))
            except MediaError as exc:
                self.events.put(("export_error", (export_id, str(exc))))

        threading.Thread(target=work, daemon=True).start()

    def _refresh_exports(self):
        for item in self.exports.get_children():
            self.exports.delete(item)
        for export_id, title, status, _ in storage.list_exports(self.db):
            self.exports.insert("", "end", iid=str(export_id), values=(title, status))

    def _poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "video":
                    self.video_id = storage.add_video(value, self.db)
                    self._refresh_videos()
                    for index, row in enumerate(self.video_rows):
                        if row[0] == self.video_id:
                            self.videos.current(index)
                            self._select_video()
                            break
                elif kind == "import_done":
                    self.status.set("Importação concluída.")
                elif kind == "error":
                    self.status.set(value)
                elif kind == "progress":
                    self.progress["value"] = value
                elif kind in {"export_done", "export_error"}:
                    export_id, result = value
                    storage.update_export(
                        export_id,
                        "done" if kind == "export_done" else "failed",
                        result,
                        self.db,
                    )
                    self.status.set(
                        f"Exportado: {result}" if kind == "export_done" else result
                    )
                    self.progress["value"] = 100 if kind == "export_done" else 0
                    self.running = False
                    self._refresh_exports()
                    self._start_next()
        except queue.Empty:
            pass
        self.after(100, self._poll)
