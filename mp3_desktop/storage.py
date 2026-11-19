"""Local completed-download history and preferences."""

import json
import os
import sqlite3
import sys
from pathlib import Path


def _default_data_dir() -> Path:
    if sys.platform == "win32":
        return Path.home() / "AppData" / "Local" / "MP3Desktop"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "MediaStudio"
    return Path.home() / ".local" / "share" / "mp3-desktop"


DATA_DIR = (
    Path(os.environ["MP3_DESKTOP_DATA_DIR"])
    if "MP3_DESKTOP_DATA_DIR" in os.environ
    else _default_data_dir()
)


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or DATA_DIR / "history.db"
    target.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(target)
    db.execute(
        "CREATE TABLE IF NOT EXISTS downloads (id INTEGER PRIMARY KEY, name TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL, completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, duration REAL NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL, size INTEGER NOT NULL, added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS project_videos (project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE, PRIMARY KEY(project_id, video_id))"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS clips (id INTEGER PRIMARY KEY, video_id INTEGER NOT NULL REFERENCES videos(id), start REAL NOT NULL, end REAL NOT NULL, title TEXT NOT NULL)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS exports (id INTEGER PRIMARY KEY, clip_id INTEGER NOT NULL REFERENCES clips(id), folder TEXT NOT NULL, preset TEXT NOT NULL, quality INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending', result TEXT)"
    )
    db.execute("UPDATE exports SET status='interrupted' WHERE status='running'")
    db.commit()
    return db


def add(path: Path, db: sqlite3.Connection) -> None:
    db.execute(
        "INSERT INTO downloads (name, path, size) VALUES (?, ?, ?)",
        (path.name, str(path), path.stat().st_size),
    )
    db.commit()


def list_downloads(db: sqlite3.Connection) -> list[tuple]:
    return db.execute(
        "SELECT name, path, size, completed_at FROM downloads ORDER BY id DESC LIMIT 500"
    ).fetchall()


def add_video(video, db: sqlite3.Connection) -> int:
    db.execute(
        "INSERT OR IGNORE INTO videos (path,duration,width,height,size) VALUES (?,?,?,?,?)",
        (str(video.path), video.duration, video.width, video.height, video.size),
    )
    db.commit()
    return db.execute(
        "SELECT id FROM videos WHERE path=?", (str(video.path),)
    ).fetchone()[0]


def list_videos(db: sqlite3.Connection) -> list[tuple]:
    return db.execute(
        "SELECT id,path,duration,width,height,size FROM videos ORDER BY id DESC"
    ).fetchall()


def add_project(name: str, description: str, db: sqlite3.Connection) -> int:
    cursor = db.execute(
        "INSERT INTO projects (name, description) VALUES (?, ?)", (name, description)
    )
    db.commit()
    return cursor.lastrowid


def list_projects(db: sqlite3.Connection) -> list[tuple]:
    return db.execute(
        "SELECT p.id,p.name,p.description,p.created_at,COUNT(pv.video_id) "
        "FROM projects p LEFT JOIN project_videos pv ON pv.project_id=p.id "
        "GROUP BY p.id ORDER BY p.id DESC"
    ).fetchall()


def update_project(
    project_id: int, name: str, description: str, db: sqlite3.Connection
) -> None:
    cursor = db.execute(
        "UPDATE projects SET name=?,description=? WHERE id=?",
        (name, description, project_id),
    )
    if cursor.rowcount == 0:
        raise ValueError("Projeto não encontrado.")
    db.commit()


def delete_project(project_id: int, db: sqlite3.Connection) -> None:
    db.execute("DELETE FROM project_videos WHERE project_id=?", (project_id,))
    cursor = db.execute("DELETE FROM projects WHERE id=?", (project_id,))
    if cursor.rowcount == 0:
        raise ValueError("Projeto não encontrado.")
    db.commit()


def add_video_to_project(
    project_id: int, video_id: int, db: sqlite3.Connection
) -> None:
    if not db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
        raise ValueError("Projeto não encontrado.")
    db.execute(
        "INSERT OR IGNORE INTO project_videos (project_id,video_id) VALUES (?,?)",
        (project_id, video_id),
    )
    db.commit()


def list_project_videos(project_id: int, db: sqlite3.Connection) -> list[tuple]:
    return db.execute(
        "SELECT v.id,v.path,v.duration,v.width,v.height,v.size "
        "FROM videos v JOIN project_videos pv ON pv.video_id=v.id "
        "WHERE pv.project_id=? ORDER BY v.id DESC",
        (project_id,),
    ).fetchall()


def add_clip(clip, db: sqlite3.Connection) -> int:
    cursor = db.execute(
        "INSERT INTO clips (video_id,start,end,title) VALUES (?,?,?,?)",
        (clip.video_id, clip.start, clip.end, clip.title),
    )
    db.commit()
    return cursor.lastrowid


def list_clips(video_id: int, db: sqlite3.Connection) -> list[tuple]:
    return db.execute(
        "SELECT id,start,end,title FROM clips WHERE video_id=? ORDER BY start",
        (video_id,),
    ).fetchall()


def delete_clip(clip_id: int, db: sqlite3.Connection) -> None:
    db.execute("DELETE FROM exports WHERE clip_id=?", (clip_id,))
    db.execute("DELETE FROM clips WHERE id=?", (clip_id,))
    db.commit()


def enqueue(
    clip_id: int, folder: Path, preset: str, quality: int, db: sqlite3.Connection
) -> int:
    cursor = db.execute(
        "INSERT INTO exports (clip_id,folder,preset,quality) VALUES (?,?,?,?)",
        (clip_id, str(folder), preset, quality),
    )
    db.commit()
    return cursor.lastrowid


def next_export(db: sqlite3.Connection):
    return db.execute(
        "SELECT e.id,e.clip_id,e.folder,e.preset,e.quality,c.video_id,c.start,c.end,c.title,v.path,v.duration,v.width,v.height,v.size FROM exports e JOIN clips c ON c.id=e.clip_id JOIN videos v ON v.id=c.video_id WHERE e.status='pending' ORDER BY e.id LIMIT 1"
    ).fetchone()


def update_export(
    export_id: int, status: str, result: str | None, db: sqlite3.Connection
) -> None:
    db.execute(
        "UPDATE exports SET status=?,result=? WHERE id=?", (status, result, export_id)
    )
    db.commit()


def list_exports(db: sqlite3.Connection) -> list[tuple]:
    return db.execute(
        "SELECT e.id,c.title,e.status,e.result FROM exports e JOIN clips c ON c.id=e.clip_id ORDER BY e.id DESC LIMIT 200"
    ).fetchall()


def load_settings() -> dict:
    try:
        return json.loads((DATA_DIR / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(settings: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target = DATA_DIR / "settings.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(settings, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)
