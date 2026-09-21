# 🎚️ DJ System — Backend

FastAPI backend powering a local-first DJ player. Scans your music folders,
streams audio with HTTP Range support, tracks play history, and hosts
WebSocket-based Jam rooms for synchronized listening.

---

## ✨ Features

- **Multi-folder library scan** — point at several directories via `MUSIC_DIRS`
- **Auto-prune on rescan** — removes rows whose files no longer exist
- **Range-aware streaming** — seek, scrub, resume without re-downloading
- **MIME auto-detection** — `.mp3`, `.m4a`, `.mp4`, `.mov`, `.webm`, `.flac` all play
- **Embedded cover art extraction** — ID3, MP4 `covr`, FLAC `pictures`
- **Play history** — powers the Capsule (nostalgic old favorites) feature
- **Jam rooms** — WebSocket sync of playback state + shared queue
- **Metadata via Mutagen** — title, artist, album, genre, duration

---

## 🧱 Tech Stack

| Layer | Tech |
|---|---|
| Framework | FastAPI |
| Server | Uvicorn |
| Database | SQLite |
| Metadata | Mutagen |
| Realtime | WebSockets (FastAPI native) |
| Runtime | Python 3.12 |

---

## 🚀 Quick Start

### 1. Install

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

# Install dependencies
pip install fastapi "uvicorn[standard]" mutagen