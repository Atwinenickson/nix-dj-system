<template>
  <div class="min-h-screen bg-zinc-950 text-white flex">
    <div class="flex-1 overflow-y-auto pb-24">
      <header class="p-4 border-b border-zinc-800 flex items-center gap-4 sticky top-0 bg-zinc-950 z-30">
        <h1 class="text-xl font-bold">🎚️ DJ System</h1>

        <nav class="flex gap-3 text-sm text-zinc-400">
          <button
            v-for="t in tabs" :key="t.id"
            @click="tab = t.id"
            :class="tab === t.id ? 'text-white' : 'hover:text-zinc-200'"
          >{{ t.label }}</button>
        </nav>

        <!-- Live status (right side) -->
        <div class="ml-auto flex items-center gap-3 text-xs">
          <!-- Jam connection dot -->
          <span
            :class="jam.connected ? 'text-green-400' : 'text-zinc-600'"
            :title="jam.connected ? `Jam: ${jam.roomId}` : 'Jam offline'"
          >{{ jam.connected ? '●' : '○' }}</span>

          <span v-if="player.shuffle" class="text-green-400" title="Shuffle on">🔀</span>

          <span v-if="player.repeat !== 'off'" class="text-green-400" title="Repeat">
            {{ player.repeat === 'one' ? '🔂' : '🔁' }}
          </span>

          <span v-if="player.autoDj" class="text-green-400" title="Auto-DJ on">🤖</span>

          <span v-if="player.sleepRemaining > 0" class="text-yellow-400">
            😴 {{ fmtTime(player.sleepRemaining) }}
          </span>

          <button
            v-if="player.queueCount"
            @click="tab = 'queue'"
            class="text-zinc-500 hover:text-white transition"
            :title="'View queue (' + player.queueCount + ')'"
          >
            Queue: {{ player.queueCount }}
          </button>
        </div>
      </header>

      <Library    v-if="tab==='library'" />
      <Capsule    v-else-if="tab==='capsule'" />
      <Queue      v-else-if="tab==='queue'" />
      <DjControls v-else-if="tab==='dj'" />
    </div>

    <Jam class="w-80 hidden md:block border-l border-zinc-800" />
    <Player />

    <!-- Keyboard shortcut cheat sheet -->
    <div class="fixed bottom-20 left-2 text-[10px] text-zinc-600 hidden lg:block">
      Space: play/pause · N: next · S: shuffle · R: repeat · ←/→: seek · ↑/↓: vol
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import Library from './components/Library.vue'
import Player from './components/Player.vue'
import Jam from './components/Jam.vue'
import Capsule from './components/Capsule.vue'
import Queue from './components/Queue.vue'
import DjControls from './components/DjControls.vue'
import { usePlayer } from './stores/player'
import { useJam } from './stores/jam'

const tab = ref('library')
const player = usePlayer()
const jam = useJam()

const tabs = [
  { id: 'library', label: 'Library' },
  { id: 'capsule', label: 'Capsule' },
  { id: 'queue',   label: 'Queue' },
  { id: 'dj',      label: '🎛️ DJ' },
]

function fmtTime(s) {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}

// ---- Keyboard shortcuts ----
function onKey(e) {
  const tag = e.target?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target?.isContentEditable) return

  switch (e.key) {
    case ' ':
      e.preventDefault()
      player.toggle()
      break
    case 'n':
    case 'N':
      player.playNext()
      break
    case 's':
    case 'S':
      player.toggleShuffle()
      break
    case 'r':
    case 'R':
      player.cycleRepeat()
      break
    case 'ArrowRight':
      e.preventDefault()
      if (e.shiftKey) player.seek(Math.min(player.duration, player.progress + 15))
      else            player.seek(player.progress + 5)
      break
    case 'ArrowLeft':
      e.preventDefault()
      if (e.shiftKey) player.seek(Math.max(0, player.progress - 15))
      else            player.seek(Math.max(0, player.progress - 5))
      break
    case 'ArrowUp':
      e.preventDefault()
      player.setVolume(Math.min(1, player.volume + 0.05))
      break
    case 'ArrowDown':
      e.preventDefault()
      player.setVolume(Math.max(0, player.volume - 0.05))
      break
  }
}

onMounted(() => {
  // Connect to Jam room 'main' so queue mirrors work globally
  jam.connect('main')
  window.addEventListener('keydown', onKey)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  // Note: we do NOT call jam.disconnect() here — the app is being torn down anyway
})
</script>