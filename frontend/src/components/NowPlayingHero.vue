<template>
  <div
    v-if="player.current"
    class="mx-4 my-4 rounded-2xl overflow-hidden shadow-2xl
           bg-gradient-to-br from-zinc-900 to-zinc-800
           flex items-center gap-6 p-5"
  >
    <!-- Cover art -->
    <div class="relative shrink-0">
      <div
        class="absolute inset-0 rounded-xl blur-md opacity-70"
        :style="{ background: coverFailed ? gradientFor(player.current.artist) : 'transparent' }"
      ></div>
      <img
        v-if="!coverFailed"
        :src="`/api/art/${player.current.id}`"
        class="relative w-32 h-32 rounded-xl object-cover shadow-lg"
        @error="coverFailed = true"
      />
      <div
        v-else
        class="relative w-32 h-32 rounded-xl flex items-center justify-center
               text-5xl font-black text-white"
        :style="{ background: gradientFor(player.current.artist) }"
      >
        {{ initials(player.current.artist) }}
      </div>

      <!-- Playing pulse -->
      <div
        v-if="player.isPlaying"
        class="absolute -inset-1 rounded-xl border-2 border-green-500/70 animate-ping-slow pointer-events-none"
      ></div>
    </div>

    <!-- Meta -->
    <div class="min-w-0 flex-1">
      <div class="text-xs text-green-400 uppercase tracking-widest mb-1">
        {{ player.isPlaying ? '● Now Playing' : '❚❚ Paused' }}
      </div>
      <div class="text-2xl font-bold truncate">{{ player.current.title }}</div>
      <div class="text-zinc-400 truncate">{{ player.current.artist }}
        <span v-if="player.current.album"> · {{ player.current.album }}</span>
      </div>

      <!-- Waveform bars -->
      <div class="mt-4 flex items-end gap-0.5 h-10">
        <div
          v-for="i in 48" :key="i"
          class="w-1 bg-green-500/80 rounded-t"
          :style="{
            height: barHeight(i) + '%',
            opacity: player.isPlaying ? 1 : 0.3,
            transition: 'height 0.15s ease'
          }"
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { usePlayer } from '../stores/player'

const player = usePlayer()
const coverFailed = ref(false)

watch(() => player.current?.id, () => { coverFailed.value = false })

function initials(name = '') {
  return name.split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
}
function gradientFor(name = '') {
  let h = 0
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360
  return `linear-gradient(135deg, hsl(${h},60%,45%), hsl(${(h+60)%360},70%,35%))`
}
function barHeight(i) {
  const t = Date.now() / 300 + i
  return 30 + Math.abs(Math.sin(t + i * 0.7)) * 60
}
</script>

<style scoped>
@keyframes ping-slow {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50%      { opacity: 0;   transform: scale(1.04); }
}
.animate-ping-slow { animation: ping-slow 2.2s ease-in-out infinite; }
</style>