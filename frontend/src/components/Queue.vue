<template>
  <div class="pb-32">
    <!-- Header banner -->
    <div class="mx-4 mt-4 mb-6 rounded-2xl overflow-hidden
                bg-gradient-to-br from-emerald-700 via-teal-600 to-cyan-500 p-6 shadow-2xl">
      <div class="flex items-center justify-between flex-wrap gap-4">
        <div>
          <div class="text-xs tracking-[0.3em] uppercase text-white/70 mb-1">Up Next</div>
          <h1 class="text-3xl md:text-4xl font-black text-white drop-shadow">
            🎧 Your Queue
          </h1>
          <p class="text-white/80 text-sm mt-1">
            {{ player.queue.length }} track{{ player.queue.length === 1 ? '' : 's' }}
            · {{ fmtTotal(queueDuration) }} total
          </p>
        </div>
        <div class="flex items-center gap-2">
          <span :class="jam.connected ? 'text-green-300' : 'text-white/60'" class="text-xs">
            {{ jam.connected ? '● Jam live' : '○ Jam offline' }}
          </span>
          <button
            v-if="player.queue.length"
            @click="clearQueue"
            class="bg-black/30 hover:bg-black/50 text-white px-4 py-2 rounded-full text-sm backdrop-blur"
          >
            Clear all
          </button>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!player.queue.length" class="mx-4 text-center py-16">
      <div class="text-6xl mb-4 opacity-40">🎵</div>
      <div class="text-zinc-400">Queue is empty</div>
      <div class="text-zinc-600 text-sm mt-1">Add tracks from the Library tab</div>
    </div>

    <!-- Queue list -->
    <ul v-else class="mx-4 space-y-2">
      <li
        v-for="(t, i) in player.queue" :key="t.id + '-' + i"
        class="flex items-center gap-3 px-3 py-2 rounded-xl bg-zinc-900/60 hover:bg-zinc-800
               group transition-colors border border-zinc-800/50"
      >
        <span class="w-6 text-center text-xs text-zinc-500 shrink-0">{{ i + 1 }}</span>

        <!-- Cover -->
        <div class="w-12 h-12 rounded-lg overflow-hidden shrink-0 bg-zinc-800">
          <img
            v-if="!broken[t.id]"
            :src="`/api/art/${t.id}`"
            class="w-full h-full object-cover"
            @error="broken[t.id] = true"
          />
          <div
            v-else
            class="w-full h-full flex items-center justify-center text-sm font-bold text-white"
            :style="{ background: gradientFor(t.artist) }"
          >{{ initials(t.artist) }}</div>
        </div>

        <!-- Meta -->
        <div class="min-w-0 flex-1">
          <div class="font-medium truncate text-sm">{{ t.title }}</div>
          <div class="text-xs text-zinc-400 truncate">
            {{ t.artist }}<span v-if="t.album"> — {{ t.album }}</span>
          </div>
        </div>

        <!-- Duration -->
        <span class="text-xs text-zinc-500 shrink-0 tabular-nums">{{ fmt(t.duration) }}</span>

        <!-- Actions -->
        <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
          <button
            @click="player.play(t)"
            class="text-green-400 hover:text-green-300 w-8 h-8 rounded-full hover:bg-zinc-700"
            title="Play now"
          >▶</button>
          <button
            @click="moveUp(i)" :disabled="i === 0"
            class="text-zinc-400 hover:text-white disabled:opacity-30 w-8 h-8 rounded hover:bg-zinc-700"
            title="Move up"
          >↑</button>
          <button
            @click="moveDown(i)" :disabled="i === player.queue.length - 1"
            class="text-zinc-400 hover:text-white disabled:opacity-30 w-8 h-8 rounded hover:bg-zinc-700"
            title="Move down"
          >↓</button>
          <button
            @click="player.dequeue(i)"
            class="text-red-400 hover:text-red-300 w-8 h-8 rounded hover:bg-zinc-700"
            title="Remove"
          >×</button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { usePlayer } from '../stores/player'
import { useJam } from '../stores/jam'

const player = usePlayer()
const jam = useJam()
const broken = reactive({})

const queueDuration = computed(() =>
  player.queue.reduce((sum, t) => sum + (t.duration || 0), 0)
)

function clearQueue() {
  for (let i = player.queue.length - 1; i >= 0; i--) player.dequeue(i)
}
function moveUp(i) {
  if (i <= 0) return
  const q = player.queue
  ;[q[i - 1], q[i]] = [q[i], q[i - 1]]
}
function moveDown(i) {
  const q = player.queue
  if (i >= q.length - 1) return
  ;[q[i], q[i + 1]] = [q[i + 1], q[i]]
}

const fmt = s => {
  if (!s || isNaN(s)) return '—'
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60).toString().padStart(2, '0')
  return `${m}:${sec}`
}
const fmtTotal = s => {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}
const initials = (name = '') =>
  name.split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase() || '?'
const gradientFor = (name = '') => {
  let h = 0
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360
  return `linear-gradient(135deg, hsl(${h},60%,45%), hsl(${(h + 60) % 360},70%,35%))`
}
</script>