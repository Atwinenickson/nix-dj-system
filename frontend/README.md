
---

## 📁 `frontend/README.md`

```markdown
# 🎨 DJ System — Frontend

Vue 3 + Vite + Pinia + Tailwind frontend for the ATWINE NICKSON DJ Music
System. Crossfade player, cover-art library, artist carousel, genre tiles,
Jam rooms, and a full DJ control panel.

---

## ✨ Features

- **Branded hero banner** — animated EQ bars, live library stats
- **Now Playing card** — big cover art, pulse ring, waveform bars
- **Artist carousel** — sliding circular avatars of top musicians
- **Genre tiles** — colored mood grid for quick filtering
- **Library view** — grid / list toggle, cover art, hover play, search
- **Player bar** — 48×48 cover thumbnail, transport, crossfade slider, volume
- **DJ Controls** — shuffle, repeat, auto-DJ, sleep timer, EQ, playback rate
- **Jam room** — real-time synced listening party over WebSocket
- **Queue** — reorder, remove, clear-all, jump-to
- **Capsule** — nostalgic old favorites
- **Keyboard shortcuts** — Space / N / S / R / ←→ / ↑↓

---

## 🧱 Tech Stack

| Layer | Tech |
|---|---|
| Framework | Vue 3 (`<script setup>`) |
| Build | Vite 5 |
| State | Pinia |
| Styling | Tailwind CSS 3 |
| Realtime | Native WebSocket |
| Audio | HTMLAudioElement + Web Audio API |

---

## 🚀 Quick Start

### 1. Install

```bash
cd frontend
npm install