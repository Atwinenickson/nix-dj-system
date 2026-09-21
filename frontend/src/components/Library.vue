<template>
  <div class="p-4 pb-32">
    <div class="flex gap-2 mb-4">
      <input v-model="q" @input="search" placeholder="Search title, artist…"
             class="flex-1 bg-zinc-800 rounded px-3 py-2 outline-none" />
      <button @click="rescan" class="bg-green-500 text-black px-4 rounded">Rescan</button>
    </div>

    <ul class="space-y-1">
      <li v-for="t in tracks" :key="t.id"
          class="flex items-center justify-between px-3 py-2 rounded hover:bg-zinc-800 group">
        <div class="min-w-0">
          <div class="font-medium truncate">{{ t.title }}</div>
          <div class="text-xs text-zinc-400 truncate">{{ t.artist }} — {{ t.album }}</div>
        </div>
        <div class="flex gap-2 opacity-0 group-hover:opacity-100">
          <button @click="player.play(t)" class="text-green-400">▶ Play</button>
          <button @click="player.enqueue(t)" class="text-zinc-300">+ Queue</button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePlayer } from '../stores/player'
const API = 'http://127.0.0.1:8000'
const tracks = ref([])
const q = ref('')
const player = usePlayer()

async function load() {
  const url = q.value ? `${API}/api/tracks?q=${encodeURIComponent(q.value)}` : `${API}/api/tracks`
  tracks.value = await (await fetch(url)).json()
}
function search() { clearTimeout(window._t); window._t = setTimeout(load, 250) }
async function rescan() { await fetch(`${API}/api/rescan`, { method: 'POST' }); load() }
onMounted(load)
</script>