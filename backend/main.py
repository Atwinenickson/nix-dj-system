import os
import json
import asyncio
import mimetypes
import random
import re
from pathlib import Path
from typing import Optional, Any
from datetime import datetime
from collections import Counter
import re as _re

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Body
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from mutagen import File as MutagenFile

from dotenv import load_dotenv
load_dotenv()

# ------------------------------------------------------------------
# Database driver auto-detection
# ------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USE_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))

if USE_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row
else:
    import sqlite3

DB_PATH = os.getenv("DB_PATH", "dj.db")

# ------------------------------------------------------------------
# SQL adapter — makes '?' placeholders and syntax portable
# ------------------------------------------------------------------
def sql(query: str) -> str:
    """Convert SQLite-flavored SQL to the active dialect."""
    if not USE_POSTGRES:
        return query
    q = query.replace("?", "%s")
    # SQLite date math → Postgres interval
    q = q.replace("datetime('now', ?)", "(NOW() + (%s)::interval)")
    q = q.replace("datetime('now')", "NOW()")
    return q


class DBConnection:
    """
    Thin wrapper so .execute / .fetchone / .fetchall / .lastrowid work
    the same on SQLite and Postgres.
    """
    def __init__(self):
        self.is_pg = USE_POSTGRES
        if self.is_pg:
            self.conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        else:
            self.conn = sqlite3.connect(DB_PATH)
            self.conn.row_factory = sqlite3.Row

    def execute(self, query: str, params: tuple = ()):
        q = sql(query)
        if self.is_pg:
            cur = self.conn.cursor()
            cur.execute(q, params)
            # emulate .lastrowid via RETURNING
            if q.strip().upper().startswith("INSERT") and "RETURNING" not in q.upper():
                return _PGCursor(cur)
            return _PGCursor(cur)
        else:
            return self.conn.execute(q, params)

    def executescript(self, script: str):
        if self.is_pg:
            cur = self.conn.cursor()
            # Postgres doesn't have executescript; split on ';'
            for stmt in script.split(";"):
                s = stmt.strip()
                if s:
                    cur.execute(s)
            self.conn.commit()
        else:
            self.conn.executescript(script)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        self.close()


class _PGCursor:
    """Mimics sqlite3.Cursor API: fetchone, fetchall, lastrowid."""
    def __init__(self, cur):
        self._cur = cur
        self.lastrowid = None
        if self._cur.description and self._cur.rowcount == 1:
            # try to fetch a potential RETURNING id
            try:
                self._last = self._cur.fetchone()
            except Exception:
                self._last = None
        else:
            self._last = None

    def fetchone(self):
        if self._last is not None:
            row = self._last
            self._last = None
            return row
        try:
            return self._cur.fetchone()
        except Exception:
            return None

    def fetchall(self):
        try:
            return self._cur.fetchall()
        except Exception:
            return []


def db():
    return DBConnection()


# ------------------------------------------------------------------
# Music folders
# ------------------------------------------------------------------
def _parse_dirs():
    raw = os.getenv("MUSIC_DIRS") or os.getenv("MUSIC_DIR") or "./songs"
    return [Path(p).expanduser().resolve() for p in raw.split(":") if p.strip()]

MUSIC_DIRS = _parse_dirs()
MUSIC_DIR = MUSIC_DIRS[0] if MUSIC_DIRS else Path("./songs").resolve()

import tempfile

# Vercel serverless is read-only except /tmp.
# Detect via the VERCEL env var it sets automatically.
if os.getenv("VERCEL"):
    SOURCES_CACHE = Path("/tmp/source_cache")
else:
    SOURCES_CACHE = Path("source_cache")

try:
    SOURCES_CACHE.mkdir(parents=True, exist_ok=True)
except OSError:
    # Ultimate fallback — always writable
    SOURCES_CACHE = Path(tempfile.gettempdir()) / "source_cache"
    SOURCES_CACHE.mkdir(parents=True, exist_ok=True)

print(f"📁 SOURCES_CACHE = {SOURCES_CACHE}", flush=True)

# ------------------------------------------------------------------
# FastAPI + CORS
# ------------------------------------------------------------------
app = FastAPI(title="DJ System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production if you want
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
)

# ------------------------------------------------------------------
# Schema — one definition, ported to both dialects
# ------------------------------------------------------------------
def _schema_sqlite() -> str:
    return """
    CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE,
        title TEXT, artist TEXT, album TEXT,
        duration REAL, genre TEXT, added_at TEXT
    );
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_id INTEGER, played_at TEXT
    );
    CREATE TABLE IF NOT EXISTS playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    );
    CREATE TABLE IF NOT EXISTS playlist_tracks (
        playlist_id INTEGER, track_id INTEGER, position INTEGER
    );
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        location TEXT UNIQUE NOT NULL,
        label TEXT,
        added_at TEXT,
        active INTEGER DEFAULT 1
    );
    """

def _schema_postgres() -> str:
    return """
    CREATE TABLE IF NOT EXISTS tracks (
        id SERIAL PRIMARY KEY,
        path TEXT UNIQUE,
        title TEXT, artist TEXT, album TEXT,
        duration DOUBLE PRECISION, genre TEXT, added_at TEXT
    );
    CREATE TABLE IF NOT EXISTS history (
        id SERIAL PRIMARY KEY,
        track_id INTEGER, played_at TEXT
    );
    CREATE TABLE IF NOT EXISTS playlists (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE
    );
    CREATE TABLE IF NOT EXISTS playlist_tracks (
        playlist_id INTEGER, track_id INTEGER, position INTEGER
    );
    CREATE TABLE IF NOT EXISTS sources (
        id SERIAL PRIMARY KEY,
        kind TEXT NOT NULL,
        location TEXT UNIQUE NOT NULL,
        label TEXT,
        added_at TEXT,
        active INTEGER DEFAULT 1
    );
    """

def init_db():
    with db() as conn:
        if USE_POSTGRES:
            cur = conn.conn.cursor()
            for stmt in _schema_postgres().split(";"):
                s = stmt.strip()
                if s:
                    cur.execute(s)
            conn.conn.commit()
        else:
            conn.executescript(_schema_sqlite())

init_db()
print(f"🗄️  Database: {'PostgreSQL (Neon)' if USE_POSTGRES else 'SQLite (local)'}", flush=True)

# ------------------------------------------------------------------
# Library scan
# ------------------------------------------------------------------
AUDIO_EXT = {
    ".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg", ".oga",
    ".opus", ".wma", ".aiff", ".aif", ".alac",
    ".mp4", ".m4v", ".mov", ".webm", ".mkv",
}

def _is_audio_file(name: str) -> bool:
    if name.startswith("._") or name.startswith("."):
        return False
    return Path(name).suffix.lower() in AUDIO_EXT


def scan_library():
    """Scan MUSIC_DIRS for audio files, update the database, and prune stale rows.""""
    added = 0
    removed = 0
    with db() as conn:
        seen = set()
        for base in MUSIC_DIRS:
            if not base.exists():
                print(f"⚠️  missing folder: {base}", flush=True)
                continue
            for root, _, files in os.walk(base):
                for f in files:
                    if not _is_audio_file(f):
                        continue
                    full = str(Path(root) / f)
                    seen.add(full)
                    if conn.execute("SELECT id FROM tracks WHERE path=?", (full,)).fetchone():
                        continue
                    meta = _extract_meta(full, Path(f).stem)
                    conn.execute(
                        "INSERT INTO tracks(path,title,artist,album,duration,genre,added_at) "
                        "VALUES(?,?,?,?,?,?,?)",
                        (full, meta["title"], meta["artist"], meta["album"],
                         meta["duration"], meta["genre"], datetime.utcnow().isoformat()),
                    )
                    added += 1

        # ---- 2. Prune stale rows ----
        # Only prune files that belong to the folders we actually scanned.
        # If we found nothing (e.g. on Vercel with no local dirs), skip pruning entirely.
        if seen:
            existing = conn.execute("SELECT id, path FROM tracks").fetchall()
            for row in existing:
                p = row["path"]
                if p in seen:
                    continue
                # Only consider rows that could have come from a scanned folder
                path_obj = Path(p)
                in_scope = any(
                    str(path_obj).startswith(str(base) + os.sep) for base in MUSIC_DIRS
                )
                # If it's not in scope, leave it alone (URL tracks, another machine's tracks, etc.)
                if not in_scope:
                    continue
                # In scope but file is gone → prune
                if not path_obj.exists():
                    conn.execute("DELETE FROM tracks WHERE id=?", (row["id"],))
                    removed += 1
        else:
            print("⏭️  skipped pruning (no folders scanned on this host)", flush=True)

    print(f"📚 scan: +{added} new, -{removed} removed", flush=True)
    return {"added": added, "removed": removed}


@app.on_event("startup")
async def startup():
    print(f"🎵 MUSIC_DIRS = {[str(d) for d in MUSIC_DIRS]}", flush=True)
    scan_library()
    with db() as conn:
        rows = conn.execute("SELECT * FROM sources WHERE active=1").fetchall()
    for r in rows:
        ingest_source(r["kind"], r["location"], r["label"] or "")

# ------------------------------------------------------------------
# Library API
# ------------------------------------------------------------------
@app.get("/api/tracks")
def list_tracks(q: Optional[str] = None):
    with db() as conn:
        if q:
            like = f"%{q}%"
            rows = conn.execute(
                "SELECT * FROM tracks WHERE title LIKE ? OR artist LIKE ? OR album LIKE ? "
                "ORDER BY artist, title",
                (like, like, like),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tracks ORDER BY artist, title").fetchall()
        return [dict(r) for r in rows]


@app.post("/api/rescan")
def rescan():
    return scan_library()

# ------------------------------------------------------------------
# Streaming
# ------------------------------------------------------------------
@app.get("/api/stream/{track_id}")
async def stream(track_id: int, request: Request):
    with db() as conn:
        row = conn.execute("SELECT path FROM tracks WHERE id=?", (track_id,)).fetchone()
    if not row:
        raise HTTPException(404)
    src = row["path"]

    if src.startswith(("http://", "https://")):
        cached = SOURCES_CACHE / Path(src.split("?")[0]).name
        if cached.exists():
            return _stream_file(cached, request)
        return await _stream_remote(src, request)

    return _stream_file(Path(src), request)


def _stream_file(path: Path, request: Request):
    if not path.exists():
        raise HTTPException(404)
    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    start, end = 0, file_size - 1
    if range_header:
        b = range_header.replace("bytes=", "").split("-")
        start = int(b[0]) if b[0] else 0
        end = int(b[1]) if len(b) > 1 and b[1] else file_size - 1
    chunk = end - start + 1

    def iterfile():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = chunk
            while remaining > 0:
                data = f.read(min(1024 * 256, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        mime = "audio/mpeg"

    return StreamingResponse(
        iterfile(),
        status_code=206 if range_header else 200,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk),
            "Content-Type": mime,
        },
    )


async def _stream_remote(url: str, request: Request):
    import httpx
    headers = {}
    if "range" in request.headers:
        headers["range"] = request.headers["range"]
    client = httpx.AsyncClient(timeout=None)
    req = client.build_request("GET", url, headers=headers)
    resp = await client.send(req, stream=True)

    async def iterator():
        async for chunk in resp.aiter_bytes(1024 * 256):
            yield chunk
        await resp.aclose()
        await client.aclose()

    passthrough = {
        k: v for k, v in resp.headers.items()
        if k.lower() in {"content-type", "content-length", "content-range", "accept-ranges"}
    }
    return StreamingResponse(iterator(), status_code=resp.status_code, headers=passthrough)

# ------------------------------------------------------------------
# History / Capsule
# ------------------------------------------------------------------
@app.post("/api/history/{track_id}")
def log_play(track_id: int):
    with db() as conn:
        conn.execute(
            "INSERT INTO history(track_id,played_at) VALUES(?,?)",
            (track_id, datetime.utcnow().isoformat()),
        )
    return {"ok": True}


@app.get("/api/capsule")
def capsule(
    days_ago_start: int = 30,
    days_ago_end: int = 3650,
    min_plays: int = 1,
    limit: int = 50,
    target_minutes: int = 0,
):
    with db() as conn:
        rows = conn.execute("""
            SELECT t.*, MAX(h.played_at) as last_played, COUNT(h.id) as plays
            FROM tracks t JOIN history h ON h.track_id = t.id
            GROUP BY t.id
            HAVING COUNT(h.id) >= ?
               AND MAX(h.played_at) <  datetime('now', ?)
               AND MAX(h.played_at) >= datetime('now', ?)
            ORDER BY plays DESC, last_played ASC
            LIMIT ?
        """, (
            min_plays,
            f"-{days_ago_start} days",
            f"-{days_ago_end} days",
            limit,
        )).fetchall()

    result = [dict(r) for r in rows]
    if target_minutes > 0:
        budget = target_minutes * 60
        trimmed, total = [], 0
        for t in result:
            d = t.get("duration") or 0
            if total + d > budget and trimmed:
                break
            trimmed.append(t)
            total += d
        result = trimmed
    return result


# ------------------------------------------------------------------
# Playlists
# ------------------------------------------------------------------
@app.get("/api/playlists")
def playlists():
    with db() as conn:
        rows = conn.execute("SELECT * FROM playlists").fetchall()
        return [dict(r) for r in rows]


@app.post("/api/playlists/{name}/tracks/{track_id}")
def add_to_playlist(name: str, track_id: int):
    with db() as conn:
        row = conn.execute("SELECT id FROM playlists WHERE name=?", (name,)).fetchone()
        if row:
            pid = row["id"]
        else:
            cur = conn.execute("INSERT INTO playlists(name) VALUES(?)", (name,))
            pid = cur.lastrowid if cur.lastrowid else \
                  conn.execute("SELECT id FROM playlists WHERE name=?", (name,)).fetchone()["id"]
        pos_row = conn.execute(
            "SELECT COALESCE(MAX(position),-1)+1 FROM playlist_tracks WHERE playlist_id=?",
            (pid,)
        ).fetchone()
        pos = pos_row[0] if not isinstance(pos_row, dict) else list(pos_row.values())[0]
        conn.execute("INSERT INTO playlist_tracks VALUES(?,?,?)", (pid, track_id, pos))
    return {"ok": True}


@app.post("/api/playlists/{name}/bulk")
def save_playlist_bulk(name: str, track_ids: list[int] = Body(..., embed=True)):
    if not track_ids:
        return {"ok": True, "count": 0}
    with db() as conn:
        row = conn.execute("SELECT id FROM playlists WHERE name=?", (name,)).fetchone()
        if row:
            pid = row["id"]
            conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=?", (pid,))
        else:
            conn.execute("INSERT INTO playlists(name) VALUES(?)", (name,))
            pid = conn.execute("SELECT id FROM playlists WHERE name=?", (name,)).fetchone()["id"]
        for pos, tid in enumerate(track_ids):
            conn.execute(
                "INSERT INTO playlist_tracks(playlist_id, track_id, position) VALUES(?,?,?)",
                (pid, tid, pos),
            )
    return {"ok": True, "count": len(track_ids), "name": name}


@app.get("/api/playlists/{name}/tracks")
def playlist_tracks(name: str):
    with db() as conn:
        row = conn.execute("SELECT id FROM playlists WHERE name=?", (name,)).fetchone()
        if not row:
            return []
        pid = row["id"]
        rows = conn.execute("""
            SELECT t.* FROM playlist_tracks pt
            JOIN tracks t ON t.id = pt.track_id
            WHERE pt.playlist_id = ?
            ORDER BY pt.position
        """, (pid,)).fetchall()
        return [dict(r) for r in rows]

# ------------------------------------------------------------------
# Jam (WebSocket)
# ------------------------------------------------------------------
class Room:
    def __init__(self):
        self.clients: list[WebSocket] = []
        self.state = {"track_id": None, "position": 0.0, "playing": False, "queue": []}

rooms: dict[str, Room] = {}


@app.websocket("/ws/jam/{room_id}")
async def jam(ws: WebSocket, room_id: str):
    await ws.accept()
    room = rooms.setdefault(room_id, Room())
    room.clients.append(ws)
    await ws.send_json({"type": "state", **room.state})
    try:
        while True:
            msg = await ws.receive_json()
            t = msg.get("type")
            if t == "play":
                room.state["playing"] = True
            elif t == "pause":
                room.state["playing"] = False
            elif t == "seek":
                room.state["position"] = msg.get("position", 0)
            elif t == "load":
                room.state.update(track_id=msg["track_id"], position=0, playing=True)
            elif t == "queue_add":
                room.state["queue"].append(msg["track_id"])
            elif t == "queue_remove":
                idx = msg.get("index")
                if 0 <= idx < len(room.state["queue"]):
                    room.state["queue"].pop(idx)
            dead = []
            for c in room.clients:
                try:
                    await c.send_json({"type": "state", **room.state, "from": msg.get("user")})
                except Exception:
                    dead.append(c)
            for d in dead:
                room.clients.remove(d)
    except WebSocketDisconnect:
        if ws in room.clients:
            room.clients.remove(ws)


@app.get("/api/jam/{room_id}/state")
def get_room(room_id: str):
    return rooms.get(room_id, Room()).state

# ------------------------------------------------------------------
# Random / Shuffle
# ------------------------------------------------------------------
@app.get("/api/tracks/random")
def random_track(exclude_id: Optional[int] = None, limit: int = 1):
    with db() as conn:
        if exclude_id:
            rows = conn.execute(
                "SELECT * FROM tracks WHERE id != ? ORDER BY RANDOM() LIMIT ?",
                (exclude_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tracks ORDER BY RANDOM() LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows] if limit != 1 else (dict(rows[0]) if rows else None)


@app.post("/api/tracks/shuffle")
def shuffle_tracks(limit: int = 20, genre: Optional[str] = None):
    with db() as conn:
        if genre:
            rows = conn.execute(
                "SELECT * FROM tracks WHERE genre = ? ORDER BY RANDOM() LIMIT ?",
                (genre, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tracks ORDER BY RANDOM() LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

# ------------------------------------------------------------------
# Cover art
# ------------------------------------------------------------------
@app.get("/api/art/{track_id}")
def get_art(track_id: int):
    with db() as conn:
        row = conn.execute("SELECT path FROM tracks WHERE id=?", (track_id,)).fetchone()
    if not row:
        raise HTTPException(404)
    src = row["path"]

    # URL tracks: no local art extraction possible
    if src.startswith(("http://", "https://")):
        cached = SOURCES_CACHE / Path(src.split("?")[0]).name
        if not cached.exists():
            raise HTTPException(404)
        path = cached
    else:
        path = Path(src)
        if not path.exists():
            raise HTTPException(404)

    try:
        audio = MutagenFile(str(path))
        if audio is None:
            raise HTTPException(404)
        tags = getattr(audio, "tags", None)
        if not tags:
            raise HTTPException(404)

        pic = None
        for key in ("APIC:", "APIC:cover", "APIC:Cover"):
            if key in tags:
                pic = tags[key]; break
        if not pic and "covr" in tags:
            pic = tags["covr"][0]
        if not pic and hasattr(audio, "pictures") and audio.pictures:
            pic = audio.pictures[0]
        if not pic:
            raise HTTPException(404)

        data = getattr(pic, "data", None) or bytes(pic)
        mime = getattr(pic, "mime", None) or "image/jpeg"
        return Response(content=data, media_type=mime)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(404)

# ------------------------------------------------------------------
# Stats
# ------------------------------------------------------------------
@app.get("/api/stats")
def stats():
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        artists = conn.execute("SELECT COUNT(DISTINCT artist) FROM tracks").fetchone()[0]
        albums = conn.execute("SELECT COUNT(DISTINCT album) FROM tracks").fetchone()[0]
        total_sec = conn.execute("SELECT COALESCE(SUM(duration), 0) FROM tracks").fetchone()[0]
        return {"tracks": total, "artists": artists, "albums": albums, "total_seconds": total_sec}


@app.get("/api/tracks/recent")
def recent_tracks(limit: int = 12):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM tracks ORDER BY added_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/tracks/top-artists")
def top_artists(limit: int = 12):
    with db() as conn:
        rows = conn.execute("""
            SELECT artist, COUNT(*) as track_count, MIN(id) as sample_track_id
            FROM tracks
            WHERE artist != 'Unknown' AND artist != ''
            GROUP BY artist
            ORDER BY track_count DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

# ------------------------------------------------------------------
# DEV helpers
# ------------------------------------------------------------------
@app.post("/api/dev/seed-history")
def seed_history(count: int = 40, spread_days: int = 400):
    with db() as conn:
        tracks = conn.execute("SELECT id FROM tracks ORDER BY RANDOM() LIMIT ?", (count,)).fetchall()
        for row in tracks:
            tid = row["id"]
            plays = random.randint(1, 8)
            for _ in range(plays):
                days_ago = random.randint(1, spread_days)
                conn.execute(
                    "INSERT INTO history(track_id, played_at) VALUES(?, datetime('now', ?))",
                    (tid, f"-{days_ago} days"),
                )
    return {"seeded": len(tracks)}


@app.delete("/api/dev/clear-history")
def clear_history():
    with db() as conn:
        conn.execute("DELETE FROM history")
    return {"ok": True}

# ------------------------------------------------------------------
# Capsule compare + auto-name
# ------------------------------------------------------------------
@app.get("/api/capsule/compare")
def capsule_compare(
    a_start: int = 365, a_end: int = 730,
    b_start: int = 180, b_end: int = 365,
    limit: int = 25,
):
    def window(start, end):
        with db() as conn:
            rows = conn.execute("""
                SELECT t.*, MAX(h.played_at) AS last_played, COUNT(h.id) AS plays
                FROM tracks t JOIN history h ON h.track_id = t.id
                GROUP BY t.id
                HAVING MAX(h.played_at) <  datetime('now', ?)
                   AND MAX(h.played_at) >= datetime('now', ?)
                ORDER BY plays DESC, last_played ASC
                LIMIT ?
            """, (f"-{start} days", f"-{end} days", limit)).fetchall()
            return [dict(r) for r in rows]

    return {
        "a": {"start": a_start, "end": a_end, "label": f"{a_start}d–{a_end}d ago",
              "tracks": window(a_start, a_end)},
        "b": {"start": b_start, "end": b_end, "label": f"{b_start}d–{b_end}d ago",
              "tracks": window(b_start, b_end)},
    }


@app.post("/api/capsule/auto-name")
def capsule_auto_name(track_ids: list[int] = Body(..., embed=True)):
    if not track_ids:
        return {"name": f"Capsule Mix · {datetime.utcnow().strftime('%b %Y')}"}

    placeholders = ",".join("?" for _ in track_ids)
    with db() as conn:
        rows = conn.execute(
            f"SELECT artist, genre, album, title FROM tracks WHERE id IN ({placeholders})",
            tuple(track_ids),
        ).fetchall()

    artists = Counter((r["artist"] or "").strip() for r in rows if r["artist"])
    genres = Counter((r["genre"] or "").strip() for r in rows if r["genre"])
    albums = Counter((r["album"] or "").strip() for r in rows if r["album"])

    top_artist, artist_count = artists.most_common(1)[0] if artists else ("", 0)
    top_genre, genre_count = genres.most_common(1)[0] if genres else ("", 0)
    top_album, album_count = albums.most_common(1)[0] if albums else ("", 0)

    total = len(rows)
    date_tag = datetime.utcnow().strftime("%b %Y")

    if artist_count / max(total, 1) >= 0.4:
        name = f"{top_artist} Heavy · {date_tag}"
    elif genre_count / max(total, 1) >= 0.4:
        name = f"{top_genre.title()} Vibes · {date_tag}"
    elif album_count / max(total, 1) >= 0.5:
        name = f"{top_album} Session · {date_tag}"
    elif len(artists) <= 3 and total >= 5:
        top2 = " & ".join(a for a, _ in artists.most_common(2))
        name = f"{top2} Mix · {date_tag}"
    else:
        adjectives = ["Late Night", "Sunset", "Midnight", "Sunday", "Golden Hour", "Autumn", "Velvet", "Analog"]
        name = f"{random.choice(adjectives)} Capsule · {total} tracks"

    return {
        "name": name,
        "dominant_artist": top_artist,
        "dominant_genre": top_genre,
        "artist_share": round(artist_count / max(total, 1), 2),
        "genre_share": round(genre_count / max(total, 1), 2),
    }

# ------------------------------------------------------------------
# Sources (folders, files, URLs, streams)
# ------------------------------------------------------------------
@app.get("/api/sources")
def list_sources():
    with db() as conn:
        rows = conn.execute("SELECT * FROM sources ORDER BY added_at DESC").fetchall()
        return [dict(r) for r in rows]


@app.post("/api/sources")
def add_source(payload: dict = Body(...)):
    kind = (payload.get("kind") or "").strip()
    loc = (payload.get("location") or "").strip()
    label = (payload.get("label") or "").strip()

    if kind not in {"folder", "file", "url", "stream"}:
        raise HTTPException(400, "invalid kind")
    if not loc:
        raise HTTPException(400, "location required")

    if kind in {"folder", "file"}:
        p = Path(loc).expanduser().resolve()
        if not p.exists():
            raise HTTPException(400, f"path not found: {p}")
        if kind == "folder" and not p.is_dir():
            raise HTTPException(400, "not a directory")
        if kind == "file" and not p.is_file():
            raise HTTPException(400, "not a file")
        loc = str(p)

    if kind in {"url", "stream"} and not loc.startswith(("http://", "https://")):
        raise HTTPException(400, "URL must start with http(s)://")

    with db() as conn:
        existing = conn.execute("SELECT id FROM sources WHERE location=?", (loc,)).fetchone()
        if existing:
            raise HTTPException(400, "source already exists")
        conn.execute(
            "INSERT INTO sources(kind,location,label,added_at) VALUES(?,?,?,?)",
            (kind, loc, label, datetime.utcnow().isoformat()),
        )

    added = ingest_source(kind, loc, label)
    return {"ok": True, "added": added}


@app.delete("/api/sources/{source_id}")
def delete_source(source_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        if not row:
            raise HTTPException(404)
        loc = row["location"]
        conn.execute("DELETE FROM sources WHERE id=?", (source_id,))
        conn.execute("DELETE FROM tracks WHERE path LIKE ?", (f"%{loc}%",))
    return {"ok": True}


def ingest_source(kind: str, location: str, label: str = "") -> int:
    if kind == "folder":
        return _ingest_folder(Path(location))
    if kind == "file":
        return _ingest_file(Path(location))
    if kind == "url":
        return _ingest_url(location, label)
    if kind == "stream":
        return _ingest_stream(location, label)
    return 0


def _ingest_folder(base: Path) -> int:
    added = 0
    with db() as conn:
        for root, _, files in os.walk(base):
            for f in files:
                if not _is_audio_file(f):
                    continue
                full = str(Path(root) / f)
                if conn.execute("SELECT 1 FROM tracks WHERE path=?", (full,)).fetchone():
                    continue
                meta = _extract_meta(full, Path(f).stem)
                conn.execute(
                    "INSERT INTO tracks(path,title,artist,album,duration,genre,added_at) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (full, meta["title"], meta["artist"], meta["album"],
                     meta["duration"], meta["genre"], datetime.utcnow().isoformat()),
                )
                added += 1
    return added


def _ingest_file(path: Path) -> int:
    if not path.is_file() or not _is_audio_file(path.name):
        return 0
    full = str(path)
    with db() as conn:
        if conn.execute("SELECT 1 FROM tracks WHERE path=?", (full,)).fetchone():
            return 0
        meta = _extract_meta(full, path.stem)
        conn.execute(
            "INSERT INTO tracks(path,title,artist,album,duration,genre,added_at) VALUES(?,?,?,?,?,?,?)",
            (full, meta["title"], meta["artist"], meta["album"],
             meta["duration"], meta["genre"], datetime.utcnow().isoformat()),
        )
    return 1


def _ingest_url(url: str, label: str = "") -> int:
    import httpx
    with db() as conn:
        if conn.execute("SELECT 1 FROM tracks WHERE path=?", (url,)).fetchone():
            return 0

    name = label or Path(url.split("?")[0]).name or "download"
    if "." not in name:
        name += ".mp3"
    cached = SOURCES_CACHE / name

    if not cached.exists():
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=60) as r:
                r.raise_for_status()
                with open(cached, "wb") as f:
                    for chunk in r.iter_bytes(1024 * 256):
                        f.write(chunk)
        except Exception as e:
            print(f"⚠️  failed to download {url}: {e}", flush=True)
            return 0

    meta = _extract_meta(str(cached), cached.stem)
    with db() as conn:
        conn.execute(
            "INSERT INTO tracks(path,title,artist,album,duration,genre,added_at) VALUES(?,?,?,?,?,?,?)",
            (url, meta["title"], meta["artist"], meta["album"],
             meta["duration"], meta["genre"], datetime.utcnow().isoformat()),
        )
    return 1


def _ingest_stream(url: str, label: str = "") -> int:
    with db() as conn:
        if conn.execute("SELECT 1 FROM tracks WHERE path=?", (url,)).fetchone():
            return 0
        conn.execute(
            "INSERT INTO tracks(path,title,artist,album,duration,genre,added_at) VALUES(?,?,?,?,?,?,?)",
            (url, label or "Live Stream", "Radio", "", 0, "stream",
             datetime.utcnow().isoformat()),
        )
    return 1


def _extract_meta(full_path: str, fallback_title: str) -> dict:
    try:
        audio = MutagenFile(full_path, easy=True)
        return {
            "title":  (audio.get("title")  or [fallback_title])[0],
            "artist": (audio.get("artist") or ["Unknown"])[0],
            "album":  (audio.get("album")  or [""])[0],
            "genre":  (audio.get("genre")  or [""])[0],
            "duration": audio.info.length if audio and audio.info else 0,
        }
    except Exception:
        return {"title": fallback_title, "artist": "Unknown", "album": "", "genre": "", "duration": 0}