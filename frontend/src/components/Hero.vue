<template>
  <div class="relative overflow-hidden rounded-2xl mx-4 mt-4 mb-2
              bg-gradient-to-br from-purple-700 via-pink-600 to-orange-500
              p-8 shadow-2xl">
    <!-- Decorative blurred blobs -->
    <div class="absolute -top-16 -right-10 w-72 h-72 rounded-full bg-white/10 blur-3xl"></div>
    <div class="absolute -bottom-20 -left-10 w-64 h-64 rounded-full bg-black/20 blur-3xl"></div>

    <div class="relative flex items-center justify-between gap-6 flex-wrap">
      <div class="min-w-0">
        <div class="text-xs tracking-[0.3em] text-white/80 uppercase mb-2">
          Est. 2026 · Local-First
        </div>
        <h1 class="text-4xl md:text-6xl font-black text-white leading-tight drop-shadow-lg">
          ATWINE NICKSON
        </h1>
        <div class="text-2xl md:text-3xl font-bold text-white/90 tracking-wider">
          DJ MUSIC SYSTEM
        </div>
        <p class="mt-3 text-white/80 max-w-lg text-sm">
          Crossfade · Shuffle · Jam rooms · Sleep timer · Auto-DJ — all your music, no cloud.
        </p>
      </div>

      <!-- Live equalizer visual -->
      <div class="flex items-end gap-1 h-20 shrink-0">
        <div
          v-for="i in 14" :key="i"
          class="w-2 rounded-t bg-white/90"
          :style="{
            height: barHeight(i) + '%',
            animation: player.isPlaying ? `eq-${i % 4} 0.9s ease-in-out infinite` : 'none',
            opacity: player.isPlaying ? 1 : 0.4
          }"
        ></div>
      </div>
    </div>

    <!-- Stats row -->
    <div class="relative mt-6 flex flex-wrap gap-6 text-white/90 text-sm">
      <div>
        <div class="text-2xl font-bold">{{ fmt(stats.tracks) }}</div>
        <div class="text-xs uppercase tracking-wider opacity-80">Tracks</div>
      </div>
      <div>
        <div class="text-2xl font-bold">{{ fmt(stats.artists) }}</div>
        <div class="text-xs uppercase tracking-wider opacity-80">Artists</div>
      </div>
      <div>
        <div class="text-2xl font-bold">{{ fmt(stats.albums) }}</div>
        <div class="text-xs uppercase tracking-wider opacity-80">Albums</div>
      </div>
      <div>
        <div class="text-2xl font-bold">{{ fmtDuration(stats.total_seconds) }}</div>
        <div class="text-xs uppercase tracking-wider opacity-80">Playtime</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePlayer } from '../stores/player'

const player = usePlayer()
const stats = ref({ tracks: 0, artists: 0, albums: 0, total_seconds: 0 })

onMounted(async () => {
  try {
    const r = await fetch('/api/stats')
    if (r.ok) stats.value = await r.json()
  } catch {}
})

const fmt = n => (n ?? 0).toLocaleString()
const fmtDuration = s => {
  const h = Math.floor((s || 0) / 3600)
  return h > 0 ? `${h.toLocaleString()}h` : `${Math.floor((s||0)/60)}m`
}
const barHeight = i => 30 + ((i * 17) % 60)
</script>

<style scoped>
@keyframes eq-0 { 0%,100% { height: 25% } 50% { height: 90% } }
@keyframes eq-1 { 0%,100% { height: 45% } 50% { height: 70% } }
@keyframes eq-2 { 0%,100% { height: 20% } 50% { height: 95% } }
@keyframes eq-3 { 0%,100% { height: 55% } 50% { height: 80% } }
</style>