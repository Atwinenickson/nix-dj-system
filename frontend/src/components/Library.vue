<template>
  <div class="pb-32">
    <Hero />
    <NowPlayingHero />
    <ArtistCarousel @filter-artist="searchArtist" />
    <GenreTiles @select="onGenre" />

    <section class="mx-4 my-6">
      <div class="flex items-center justify-between mb-3 gap-2 flex-wrap">
        <h2 class="text-xl font-bold">
          📚 Library
          <span class="text-sm text-zinc-500 font-normal ml-2">
            {{ tracks.length }} track{{ tracks.length === 1 ? '' : 's' }}
          </span>
        </h2>

        <div class="flex items-center gap-2">
          <input
            v-model="q"
            @input="search"
            placeholder="Search title, artist, album…"
            class="bg-zinc-800 rounded-full px-4 py-2 outline-none
                   focus:ring-2 ring-green-500 text-sm w-64"
          />
          <button
            @click="rescan"
            class="bg-green-500 hover:bg-green-400 text-black px-4 py-2 rounded-full text-sm font-semibold"
          >
            ↻ Rescan
          </button>
          <button
            @click="view = view === 'list' ? 'grid' : 'list'"
            class="bg-zinc-800 hover:bg-zinc-700 px-3 py-2 rounded-full text-sm"
            :title="view === 'grid' ? 'Switch to list' : 'Switch to grid'"
          >
            {{ view === 'grid' ? '☰' : '▦' }}
          </button>
        </div>
      </div>

      <!-- GRID view -->
      <div v-if="view === 'grid'" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <div
          v-for="t in tracks" :key="t.id"
          class="group bg-zinc-900 hover:bg-zinc-800 rounded-xl p-3 transition-colors cursor-pointer"
          @dblclick="player.play(t)"
        >
          <div class="relative aspect-square rounded-lg overflow-hidden mb-2 bg-zinc-800">
            <img
              v-if="!broken[t.id]"
              :src="`/api/art/${t.id}`"
              class="w-full h-full object-cover"
              @error="broken[t.id] = true"
            />
            <div
              v-else
              class="w-full h-full flex items-center justify-center text-4xl font-black text-white"
              :style="{ background: gradientFor(t.artist) }"
            >{{ initials(t.artist) }}</div>

            <button
              @click.stop="player.play(t)"
              class="absolute bottom-2 right-2 w-10 h-10 rounded-full
                     bg-green-500 text-black text-lg shadow-lg
                     opacity-0 group-hover:opacity-100 translate-y-1
                     group-hover:translate-y-0 transition-all"
            >▶</button>
          </div>
          <div class="text-sm font-medium truncate">{{ t.title }}</div>
          <div class="text-xs text-zinc-500 truncate">{{ t.artist }}</div>
        </div>
      </div>

      <!-- LIST view -->
      <ul v-else class="space-y-1">
        <li
          v-for="t in tracks" :key="t.id"
          class="flex items-center gap-3 px-3 py-2 rounded hover:bg-zinc-800 group"
        >
          <div class="w-10 h-10 rounded overflow-hidden shrink-0 bg-zinc-800">
            <img v-if="!broken[t.id]" :src="`/api/art/${t.id}`" class="w-full h-full object-cover" @error="broken[t.id] = true" />
            <div v-else class="w-full h-full flex items-center justify-center text-xs font-bold text-white"
                 :style="{ background: gradientFor(t.artist) }">{{ initials(t.artist) }}</div>
          </div>
          <div class="min-w-0 flex-1">
            <div class="font-medium truncate">{{ t.title }}</div>
            <div class="text-xs text-zinc-400 truncate">{{ t.artist }} — {{ t.album }}</div>
          </div>
          <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100">
            <button @click="player.play(t)" class="text-green-400">▶ Play</button>
            <button @click="player.enqueue(t)" class="text-zinc-300">+ Queue</button>
          </div>
        </li>
      </ul>

      <div v-if="!tracks.length" class="text-center text-zinc-500 py-16">
        No tracks found. Point <code>MUSIC_DIRS</code> at your folders and hit Rescan.
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { usePlayer } from '../stores/player'
import Hero from './Hero.vue'
import NowPlayingHero from './NowPlayingHero.vue'
import ArtistCarousel from './ArtistCarousel.vue'
import GenreTiles from './GenreTiles.vue'

const player = usePlayer()
const tracks = ref([])
const q = ref('')
const view = ref('grid')
const broken = reactive({})

async function load() {
  const url = q.value
    ? `/api/tracks?q=${encodeURIComponent(q.value)}`
    : '/api/tracks'
  const r = await fetch(url)
  tracks.value = r.ok ? await r.json() : []
}
function search() {
  clearTimeout(window._t)
  window._t = setTimeout(load, 250)
}
function searchArtist(name) {
  q.value = name
  load()
}
function onGenre(g) {
  if (g === 'All') { q.value = ''; load() }
  else { q.value = g; load() }
}
async function rescan() {
  await fetch('/api/rescan', { method: 'POST' })
  load()
}

function initials(name = '') {
  return name.split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase() || '?'
}
function gradientFor(name = '') {
  let h = 0
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360
  return `linear-gradient(135deg, hsl(${h},60%,45%), hsl(${(h+60)%360},70%,35%))`
}

onMounted(load)
</script>