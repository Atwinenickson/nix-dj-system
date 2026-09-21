import os
import json
import sqlite3
import asyncio
import mimetypes
from pathlib import Path
from typing import Optional
from datetime import datetime
import random

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from mutagen import File as MutagenFile

# ------------------------------------------------------------------
# Music folders: colon-separated list in MUSIC_DIRS
# ------------------------------------------------------------------
def _parse_dirs():
    raw = os.getenv("MUSIC_DIRS") or os.getenv("MUSIC_DIR") or "./songs"
    return [Path(p).expanduser().resolve() for p in raw.split(":") if p.strip()]

MUSIC_DIRS = _parse_dirs()
MUSIC_DIR = MUSIC_DIRS[0] if MUSIC_DIRS else Path("./songs").resolve()

DB_PATH = os.getenv("DB_PATH", "dj.db")

# ------------------------------------------------------------------
# FastAPI + CORS
# ------------------------------------------------------------------
app = FastAPI(title="DJ System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
)

# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            title TEXT, artist TEXT, album TEXT,
            duration REAL, genre TEXT, added_at TEXT
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER,
            played_at TEXT
        );
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS playlist_tracks (
            playlist_id INTEGER, track_id INTEGER, position INTEGER
        );
        """)

init_db()

# ------------------------------------------------------------------
# Library scan
# ------------------------------------------------------------------
AUDIO_EXT = {
    # audio-only
    ".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg", ".oga",
    ".opus", ".wma", ".aiff", ".aif", ".alac",
    # video containers (browser <audio> plays the audio track)
    ".mp4", ".m4v", ".mov", ".webm", ".mkv",
}

def _is_audio_file(name: str) -> bool:
    # Skip macOS resource forks and hidden files
    if name.startswith("._") or name.startswith("."):
        return False
    return Path(name).suffix.lower() in AUDIO_EXT

def scan_library():
    """Walk all MUSIC_DIRS. Insert new files, prune missing ones."""
    added = 0
    removed = 0
    with db() as conn:
        seen = set()

        # ---- 1. Add new files ----
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

                    cur = conn.execute("SELECT id FROM tracks WHERE path=?", (full,))
                    if cur.fetchone():
                        continue

                    try:
                        audio = MutagenFile(full, easy=True)
                        title = (audio.get("title") or [Path(f).stem])[0]
                        artist = (audio.get("artist") or ["Unknown"])[0]
                        album = (audio.get("album") or [""])[0]
                        genre = (audio.get("genre") or [""])[0]
                        dur = audio.info.length if audio and audio.info else 0
                    except Exception as e:
                        print(f"⚠️  metadata error for {full}: {e}", flush=True)
                        title, artist, album, genre, dur = Path(f).stem, "Unknown", "", "", 0

                    conn.execute(
                        "INSERT INTO tracks(path,title,artist,album,duration,genre,added_at) "
                        "VALUES(?,?,?,?,?,?,?)",
                        (full, title, artist, album, dur, genre, datetime.utcnow().isoformat()),
                    )
                    added += 1

        # ---- 2. Prune stale rows ----
        # Any DB row whose file is gone OR is outside our MUSIC_DIRS scope gets removed
        existing = conn.execute("SELECT id, path FROM tracks").fetchall()
        for row in existing:
            p = row["path"]
            if p in seen:
                continue
            path_obj = Path(p)
            in_scope = any(str(path_obj).startswith(str(base) + os.sep) for base in MUSIC_DIRS)
            if not in_scope or not path_obj.exists():
                conn.execute("DELETE FROM tracks WHERE id=?", (row["id"],))
                removed += 1

    print(f"📚 scan: +{added} new, -{removed} removed", flush=True)
    return {"added": added, "removed": removed}


@app.on_event("startup")
async def startup():
    print(f"🎵 MUSIC_DIRS = {[str(d) for d in MUSIC_DIRS]}", flush=True)
    scan_library()

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
# Streaming (Range support for seeking)
# ------------------------------------------------------------------
@app.get("/api/stream/{track_id}")
def stream(track_id: int, request: Request):
    with db() as conn:
        row = conn.execute("SELECT path FROM tracks WHERE id=?", (track_id,)).fetchone()
    if not row:
        raise HTTPException(404, "track not found")
    path = Path(row["path"])
    if not path.exists():
        raise HTTPException(404, "file not found")

    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    start, end = 0, file_size - 1
    if range_header:
        bytes_range = range_header.replace("bytes=", "").split("-")
        start = int(bytes_range[0]) if bytes_range[0] else 0
        end = int(bytes_range[1]) if len(bytes_range) > 1 and bytes_range[1] else file_size - 1

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

    # MIME auto-detect (.mp3 → audio/mpeg, .m4a → audio/mp4, .mp4 → video/mp4, ...)
    mime, _ = mimetypes.guess_type(str(path))
    if not mime or not (mime.startswith("audio/") or mime.startswith("video/")):
        mime = "audio/mpeg"

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk),
        "Content-Type": mime,
    }
    return StreamingResponse(
        iterfile(),
        status_code=206 if range_header else 200,
        headers=headers,
    )

# ------------------------------------------------------------------
# History (for Capsule)
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
def capsule(days_ago_start: int = 30, days_ago_end: int = 365):
    """Nostalgic playlist: tracks you loved before but haven't played recently."""
    with db() as conn:
        rows = conn.execute("""
            SELECT t.*, MAX(h.played_at) as last_played, COUNT(h.id) as plays
            FROM tracks t JOIN history h ON h.track_id = t.id
            GROUP BY t.id
            HAVING last_played < datetime('now', ?)
            ORDER BY plays DESC LIMIT 30
        """, (f"-{days_ago_start} days",)).fetchall()
        return [dict(r) for r in rows]

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
        cur = conn.execute("SELECT id FROM playlists WHERE name=?", (name,))
        row = cur.fetchone()
        if row:
            pid = row["id"]
        else:
            pid = conn.execute("INSERT INTO playlists(name) VALUES(?)", (name,)).lastrowid
        pos = conn.execute(
            "SELECT COALESCE(MAX(position),-1)+1 FROM playlist_tracks WHERE playlist_id=?",
            (pid,),
        ).fetchone()[0]
        conn.execute("INSERT INTO playlist_tracks VALUES(?,?,?)", (pid, track_id, pos))
    return {"ok": True}

# ------------------------------------------------------------------
# JAM (Real-time sync)
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
    
    

import io
from fastapi.responses import Response

@app.get("/api/art/{track_id}")
def get_art(track_id: int):
    """Return embedded cover art for a track, or 404."""
    with db() as conn:
        row = conn.execute("SELECT path FROM tracks WHERE id=?", (track_id,)).fetchone()
    if not row:
        raise HTTPException(404)
    path = Path(row["path"])
    if not path.exists():
        raise HTTPException(404)

    try:
        audio = MutagenFile(str(path))
        # Look for common tag keys that hold embedded art
        if audio is None:
            raise HTTPException(404)

        tags = getattr(audio, "tags", None)
        if not tags:
            raise HTTPException(404)

        pic = None
        # ID3 (mp3)
        for key in ("APIC:", "APIC:cover", "APIC:Cover"):
            if key in tags:
                pic = tags[key]
                break
        # MP4 / M4A
        if not pic and "covr" in tags:
            pic = tags["covr"][0]
        # FLAC
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


@app.get("/api/stats")
def stats():
    """Aggregate library stats for the UI header."""
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        artists = conn.execute("SELECT COUNT(DISTINCT artist) FROM tracks").fetchone()[0]
        albums = conn.execute("SELECT COUNT(DISTINCT album) FROM tracks").fetchone()[0]
        total_sec = conn.execute("SELECT COALESCE(SUM(duration), 0) FROM tracks").fetchone()[0]
        return {
            "tracks": total,
            "artists": artists,
            "albums": albums,
            "total_seconds": total_sec,
        }


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
            SELECT artist, COUNT(*) as track_count,
                   MIN(id) as sample_track_id
            FROM tracks
            WHERE artist != 'Unknown' AND artist != ''
            GROUP BY artist
            ORDER BY track_count DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

@app.get("/api/capsule")
def capsule(
    days_ago_start: int = 30,
    days_ago_end: int = 3650,
    min_plays: int = 1,
    limit: int = 50,
    target_minutes: int = 0,
):
    """
    Nostalgic playlist: tracks you loved before but haven't played recently.

    - days_ago_start: only include tracks NOT played in the last N days
    - days_ago_end: only include tracks played within the last M days (optional upper bound)
    - min_plays: ignore tracks played fewer than N times
    - limit: max number of tracks returned
    - target_minutes: if > 0, stop collecting once total duration reaches this many minutes
    """
    with db() as conn:
        rows = conn.execute("""
            SELECT t.*, MAX(h.played_at) as last_played, COUNT(h.id) as plays
            FROM tracks t JOIN history h ON h.track_id = t.id
            GROUP BY t.id
            HAVING plays >= ?
               AND last_played <  datetime('now', ?)
               AND last_played >= datetime('now', ?)
            ORDER BY plays DESC, last_played ASC
            LIMIT ?
        """, (
            min_plays,
            f"-{days_ago_start} days",
            f"-{days_ago_end} days",
            limit,
        )).fetchall()

    result = [dict(r) for r in rows]

    # If a target duration is set, trim the list to fit
    if target_minutes > 0:
        budget = target_minutes * 60
        trimmed = []
        total = 0
        for t in result:
            d = t.get("duration") or 0
            if total + d > budget and trimmed:
                break
            trimmed.append(t)
            total += d
        result = trimmed

    return result


from fastapi import Body

# ------------------------------------------------------------------
# DEV: seed fake history for testing
# ------------------------------------------------------------------
@app.post("/api/dev/seed-history")
def seed_history(count: int = 40, spread_days: int = 400):
    """
    DEV ONLY. Randomly assigns N tracks fake play history spread over the
    last `spread_days` days, so Capsule has something to show.
    """
    import random
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
    """DEV ONLY. Wipe all play history."""
    with db() as conn:
        conn.execute("DELETE FROM history")
    return {"ok": True}


# ------------------------------------------------------------------
# Save a mix as a named playlist (idempotent)
# ------------------------------------------------------------------
@app.post("/api/playlists/{name}/bulk")
def save_playlist_bulk(name: str, track_ids: list[int] = Body(..., embed=True)):
    """
    Create a playlist (if missing) and add all track_ids in order.
    Replaces any existing tracks in the same-named playlist.
    """
    if not track_ids:
        return {"ok": True, "count": 0}

    with db() as conn:
        # Get or create playlist
        row = conn.execute("SELECT id FROM playlists WHERE name=?", (name,)).fetchone()
        if row:
            pid = row["id"]
            # Wipe existing order so this call is idempotent
            conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=?", (pid,))
        else:
            pid = conn.execute("INSERT INTO playlists(name) VALUES(?)", (name,)).lastrowid

        # Insert in order
        for pos, tid in enumerate(track_ids):
            conn.execute(
                "INSERT INTO playlist_tracks(playlist_id, track_id, position) VALUES(?,?,?)",
                (pid, tid, pos),
            )

    return {"ok": True, "count": len(track_ids), "name": name}


# ------------------------------------------------------------------
# Load a playlist's tracks (needed to resume / preview)
# ------------------------------------------------------------------
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


from collections import Counter
import re

# ------------------------------------------------------------------
# Side-by-side capsule comparison
# ------------------------------------------------------------------
@app.get("/api/capsule/compare")
def capsule_compare(
    a_start: int = 365,  # "not played in last A_START days"
    a_end:   int = 730,  # "but played within last A_END days"
    b_start: int = 180,
    b_end:   int = 365,
    limit:   int = 25,
):
    """
    Returns two lists side-by-side.
    Column A: tracks not played in last `a_start` days but played within `a_end` days.
    Column B: same for `b_start`/`b_end`.
    """
    def window(start, end):
        with db() as conn:
            rows = conn.execute("""
                SELECT t.*, MAX(h.played_at) AS last_played, COUNT(h.id) AS plays
                FROM tracks t JOIN history h ON h.track_id = t.id
                GROUP BY t.id
                HAVING last_played <  datetime('now', ?)
                   AND last_played >= datetime('now', ?)
                ORDER BY plays DESC, last_played ASC
                LIMIT ?
            """, (f"-{start} days", f"-{end} days", limit)).fetchall()
            return [dict(r) for r in rows]

    return {
        "a": {"start": a_start, "end": a_end, "label": f"{a_start}d–{a_end}d ago", "tracks": window(a_start, a_end)},
        "b": {"start": b_start, "end": b_end, "label": f"{b_start}d–{b_end}d ago", "tracks": window(b_start, b_end)},
    }


# ------------------------------------------------------------------
# Auto-generate a name for a mix
# ------------------------------------------------------------------
@app.post("/api/capsule/auto-name")
def capsule_auto_name(track_ids: list[int] = Body(..., embed=True)):
    """
    Given a list of track IDs, produce a catchy mix name based on
    dominant artist and/or genre.
    """
    if not track_ids:
        return {"name": f"Capsule Mix · {datetime.utcnow().strftime('%b %Y')}"}

    placeholders = ",".join("?" for _ in track_ids)
    with db() as conn:
        rows = conn.execute(
            f"SELECT artist, genre, album, title FROM tracks WHERE id IN ({placeholders})",
            track_ids,
        ).fetchall()

    artists = Counter((r["artist"] or "").strip() for r in rows if r["artist"])
    genres  = Counter((r["genre"]  or "").strip() for r in rows if r["genre"])
    albums  = Counter((r["album"]  or "").strip() for r in rows if r["album"])

    top_artist, artist_count = artists.most_common(1)[0] if artists else ("", 0)
    top_genre,  genre_count  = genres.most_common(1)[0]  if genres  else ("", 0)
    top_album,  album_count  = albums.most_common(1)[0]  if albums  else ("", 0)

    total = len(rows)
    date_tag = datetime.utcnow().strftime("%b %Y")

    # Decide on a naming strategy
    if artist_count / max(total, 1) >= 0.4:
        # Dominant artist
        name = f"{top_artist} Heavy · {date_tag}"
    elif genre_count / max(total, 1) >= 0.4:
        # Dominant genre
        name = f"{top_genre.title()} Vibes · {date_tag}"
    elif album_count / max(total, 1) >= 0.5:
        # Mostly one album
        name = f"{top_album} Session · {date_tag}"
    elif len(artists) <= 3 and total >= 5:
        # Few artists
        top2 = " & ".join(a for a, _ in artists.most_common(2))
        name = f"{top2} Mix · {date_tag}"
    else:
        # Mixed bag — describe by vibe
        adjectives = ["Late Night", "Sunset", "Midnight", "Sunday", "Golden Hour", "Autumn", "Velvet", "Analog"]
        import random as _r
        name = f"{_r.choice(adjectives)} Capsule · {total} tracks"

    return {
        "name": name,
        "dominant_artist": top_artist,
        "dominant_genre": top_genre,
        "artist_share": round(artist_count / max(total, 1), 2),
        "genre_share": round(genre_count / max(total, 1), 2),
    }