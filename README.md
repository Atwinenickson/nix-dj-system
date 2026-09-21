
---

## 📁 Bonus — Root `README.md`

If you want a top-level README for the whole project:

```markdown
# 🎚️ ATWINE NICKSON — DJ Music System

A local-first DJ player inspired by Spotify's **Crossfade**, **Capsule**,
and **Jam** features. Plays your music straight from disk — no cloud, no
upload, no subscription.

![status](https://img.shields.io/badge/status-active-success)
![backend](https://img.shields.io/badge/backend-FastAPI-009688)
![frontend](https://img.shields.io/badge/frontend-Vue%203-42b883)

## ✨ Features

- **Crossfade** — dual-audio blend, 0–12s per transition
- **Shuffle & Repeat** — off / all / one, plus library shuffle
- **Sleep Timer** — auto-stop with fade-out (5/15/30/45/60 min)
- **Auto-DJ** — never stops; refills from random tracks
- **Web Audio EQ** — bass & treble (±12 dB), playback speed 0.5×–1.5×
- **Jam Rooms** — synced playback + shared queue over WebSocket
- **Capsule** — rediscover old favorites
- **Multi-folder scan** — point at several directories via `MUSIC_DIRS`
- **Cover art extraction** — ID3, MP4, FLAC embedded artwork
- **Video support** — `.mp4`/`.mov`/`.webm` audio plays via `<audio>`

## 🏗️ Architecture
