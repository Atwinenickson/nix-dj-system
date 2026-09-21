<template>
  <section class="mx-4 my-6">
    <h2 class="text-xl font-bold mb-3">🎧 Browse</h2>
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      <button
        v-for="g in genres" :key="g.name"
        @click="$emit('select', g.name)"
        class="relative overflow-hidden rounded-xl p-5 text-left h-28
               hover:scale-[1.03] transition-transform shadow-lg"
        :style="{ background: g.gradient }"
      >
        <div class="absolute -right-4 -bottom-4 text-7xl opacity-25 select-none">{{ g.emoji }}</div>
        <div class="relative">
          <div class="text-2xl font-black text-white drop-shadow">{{ g.name }}</div>
          <div class="text-xs text-white/80 mt-1">{{ g.count }} tracks</div>
        </div>
      </button>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'

defineEmits(['select'])

const genres = ref([
  { name: 'All',       emoji: '🎵', gradient: 'linear-gradient(135deg,#6366f1,#8b5cf6)', count: 0 },
  { name: 'Chill',     emoji: '🌙', gradient: 'linear-gradient(135deg,#0ea5e9,#22d3ee)', count: 0 },
  { name: 'Party',     emoji: '🔥', gradient: 'linear-gradient(135deg,#f97316,#ef4444)', count: 0 },
  { name: 'Afro',      emoji: '🥁', gradient: 'linear-gradient(135deg,#eab308,#d97706)', count: 0 },
  { name: 'Gospel',    emoji: '✨', gradient: 'linear-gradient(135deg,#10b981,#047857)', count: 0 },
  { name: 'Hip Hop',   emoji: '🎤', gradient: 'linear-gradient(135deg,#ec4899,#be185d)', count: 0 },
  { name: 'Reggae',    emoji: '🌴', gradient: 'linear-gradient(135deg,#22c55e,#15803d)', count: 0 },
  { name: 'Oldies',    emoji: '📻', gradient: 'linear-gradient(135deg,#a78bfa,#7c3aed)', count: 0 },
])

onMounted(async () => {
  try {
    const r = await fetch('/api/tracks')
    if (!r.ok) return
    const all = await r.json()
    genres.value[0].count = all.length
  } catch {}
})
</script>