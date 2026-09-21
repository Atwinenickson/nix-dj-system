<template>
  <div class="fixed bottom-0 left-0 right-0 bg-zinc-900 border-t border-zinc-800 p-3 z-40">
    <div class="flex items-center gap-3 max-w-7xl mx-auto">

      <!-- ===================== Track info (with cover art) ===================== -->
      <div class="flex items-center gap-3 w-64 min-w-0 shrink-0">
        <!-- Cover thumbnail -->
        <div class="w-12 h-12 rounded-lg overflow-hidden shrink-0 bg-zinc-800 shadow">
          <img
            v-if="player.current && !artFailed"
            :src="`/api/art/${player.current.id}`"
            :alt="player.current.title"
            class="w-full h-full object-cover"
            @error="artFailed = true"
          />
          <div
            v-else-if="player.current"
            class="w-full h-full flex items-center justify-center text-sm font-bold text-white"
            :style="{ background: gradientFor(player.current.artist) }"
          >{{ initials(player.current.artist) }}</div>
          <div
            v-else
            class="w-full h-full flex items-center justify-center text-zinc-600 text-lg"
          >♪</div>
        </div>

        <!-- Title + artist -->
        <div class="min-w-0 flex-1">
          <div class="font-semibold truncate text-sm">
            {{ player.current?.title || 'Nothing playing' }}
          </div>
          <div class="text-xs text-zinc-400 truncate">
            {{ player.current?.artist || '—' }}
          </div>
        </div>
      </div>

      <!-- ===================== Transport ===================== -->
      <div class="flex items-center gap-1 shrink-0">
        <button
          @click="player.toggleShuffle()"
          :class="player.shuffle ? 'text-green-400' : 'text-zinc-500'"
          class="text-lg hover:text-white transition px-1"
          title="Shuffle (S)"
        >🔀</button>

        <button
          @click="player.cycleRepeat()"
          :class="player.repeat !== 'off' ? 'text-green-400' : 'text-zinc-500'"
          class="text-lg hover:text-white transition px-1"
          :title="`Repeat: ${player.repeat} (R)`"
        >
          {{ player.repeat === 'one' ? '🔂' : '🔁' }}
        </button>

        <button
          @click="player.toggle()"
          class="bg-green-500 hover:bg-green-400 rounded-full w-10 h-10 text-black text-lg transition ml-1"
        >
          {{ player.isPlaying ? '❚❚' : '▶' }}
        </button>

        <button
          @click="player.playNext()"
          class="text-xl hover:text-green-400 transition px-1"
          title="Next (N)"
        >⏭</button>

        <button
          @click="player.autoDj = !player.autoDj"
          :class="player.autoDj ? 'text-green-400' : 'text-zinc-500'"
          class="text-lg hover:text-white transition px-1"
          title="Auto-DJ"
        >🤖</button>
      </div>

      <!-- ===================== Progress ===================== -->
      <div class="flex-1 min-w-0">
        <input
          type="range" min="0" :max="player.duration || 0" :value="player.progress"
          @input="e => player.seek(+e.target.value)"
          class="w-full accent-green-500"
        />
        <div class="flex justify-between text-xs text-zinc-500 -mt-1">
          <span>{{ fmt(player.progress) }}</span>
          <span v-if="player.sleepRemaining > 0" class="text-yellow-400">
            😴 {{ fmt(player.sleepRemaining) }}
          </span>
          <span>{{ fmt(player.duration) }}</span>
        </div>
      </div>

      <!-- ===================== Crossfade ===================== -->
      <div class="hidden md:flex items-center gap-2 shrink-0">
        <span class="text-xs text-zinc-400 whitespace-nowrap">
          ⤫ {{ player.crossfade }}s
        </span>
        <input
          type="range" min="0" max="12" step="0.5"
          v-model.number="player.crossfade"
          class="w-20 accent-green-500"
          title="Crossfade duration"
        />
      </div>

      <!-- ===================== Sleep timer menu ===================== -->
      <div class="hidden lg:block relative group shrink-0">
        <button class="text-lg text-zinc-400 hover:text-white px-1" title="Sleep timer">
          ⏱️
        </button>
        <div class="absolute bottom-full right-0 mb-2 hidden group-hover:flex
                    flex-col bg-zinc-800 rounded shadow-lg p-2 gap-1 w-28 z-50">
          <button
            v-for="m in [5, 15, 30, 45, 60]"
            :key="m"
            @click="player.startSleep(m)"
            class="text-xs hover:bg-zinc-700 rounded px-2 py-1 text-left"
          >{{ m }} min</button>
          <button
            @click="player.cancelSleep()"
            class="text-xs text-red-400 hover:bg-zinc-700 rounded px-2 py-1 text-left"
          >Cancel</button>
        </div>
      </div>

      <!-- ===================== Volume ===================== -->
      <div class="hidden sm:flex items-center gap-1 shrink-0">
        <span class="text-sm text-zinc-400">🔊</span>
        <input
          type="range" min="0" max="1" step="0.01"
          :value="player.volume"
          @input="e => player.setVolume(+e.target.value)"
          class="w-20 accent-green-500"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { usePlayer } from '../stores/player'

const player = usePlayer()

// Reset the "art failed" flag whenever the track changes,
// so a new track can try to load its own cover.
const artFailed = ref(false)
watch(() => player.current?.id, () => { artFailed.value = false })

const fmt = s => {
  if (!s || isNaN(s)) return '0:00'
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60).toString().padStart(2, '0')
  return `${m}:${sec}`
}

// Fallback when a track has no embedded cover art — deterministic gradient per artist
const initials = (name = '') =>
  name.split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase() || '?'

const gradientFor = (name = '') => {
  let h = 0
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360
  return `linear-gradient(135deg, hsl(${h},60%,45%), hsl(${(h + 60) % 360},70%,35%))`
}
</script>