<template>
  <div class="p-4 space-y-4 bg-zinc-900 rounded-lg">
    <h2 class="font-bold text-lg">🎛️ DJ Controls</h2>

    <!-- Transport row -->
    <div class="flex flex-wrap gap-2">
      <button
        @click="player.toggleShuffle()"
        :class="player.shuffle ? 'bg-green-500 text-black' : 'bg-zinc-800'"
        class="px-3 py-1 rounded text-sm"
      >
        🔀 Shuffle {{ player.shuffle ? 'ON' : 'OFF' }}
      </button>

      <button
        @click="player.cycleRepeat()"
        class="px-3 py-1 rounded text-sm bg-zinc-800"
      >
        🔁 {{ repeatLabel }}
      </button>

      <button
        @click="player.autoDj = !player.autoDj"
        :class="player.autoDj ? 'bg-green-500 text-black' : 'bg-zinc-800'"
        class="px-3 py-1 rounded text-sm"
      >
        🤖 Auto-DJ {{ player.autoDj ? 'ON' : 'OFF' }}
      </button>

      <button
        @click="player.shuffleLibrary(20)"
        class="px-3 py-1 rounded text-sm bg-purple-600"
      >
        ✨ Surprise me (20 random)
      </button>
    </div>

    <!-- Crossfade -->
    <label class="block text-sm">
      Crossfade: <b>{{ player.crossfade }}s</b>
      <input
        type="range" min="0" max="12" step="0.5"
        v-model.number="player.crossfade"
        class="w-full accent-green-500"
      />
    </label>

    <!-- Fade in / out -->
    <div class="grid grid-cols-2 gap-4">
      <label class="text-sm">
        Fade in: <b>{{ player.fadeIn }}s</b>
        <input type="range" min="0" max="8" step="0.5"
               v-model.number="player.fadeIn" class="w-full accent-green-500" />
      </label>
      <label class="text-sm">
        Fade out (sleep): <b>{{ player.fadeOut }}s</b>
        <input type="range" min="0" max="8" step="0.5"
               v-model.number="player.fadeOut" class="w-full accent-green-500" />
      </label>
    </div>

    <!-- Playback rate -->
    <label class="block text-sm">
      Playback speed: <b>{{ player.playbackRate.toFixed(2) }}×</b>
      <input type="range" min="0.5" max="1.5" step="0.01"
             :value="player.playbackRate"
             @input="e => player.setPlaybackRate(+e.target.value)"
             class="w-full accent-green-500" />
    </label>

    <!-- EQ: Bass + Treble -->
    <div class="grid grid-cols-2 gap-4">
      <label class="text-sm">
        Bass: <b>{{ bass }}</b>
        <input type="range" min="-12" max="12" step="1" v-model.number="bass"
               @input="player.setBass(bass)" class="w-full accent-green-500" />
      </label>
      <label class="text-sm">
        Treble: <b>{{ treble }}</b>
        <input type="range" min="-12" max="12" step="1" v-model.number="treble"
               @input="player.setTreble(treble)" class="w-full accent-green-500" />
      </label>
    </div>

    <!-- Sleep timer -->
    <div class="border-t border-zinc-700 pt-3">
      <div class="font-semibold text-sm mb-2">😴 Sleep Timer</div>
      <div class="flex flex-wrap gap-2">
        <button v-for="m in [5, 15, 30, 45, 60]" :key="m"
                @click="player.startSleep(m)"
                class="px-3 py-1 bg-zinc-800 rounded text-sm">
          {{ m }}m
        </button>
        <button @click="player.cancelSleep()" class="px-3 py-1 bg-red-700 rounded text-sm">
          Cancel
        </button>
      </div>
      <div v-if="player.sleepRemaining > 0" class="text-xs text-green-400 mt-2">
        ⏳ Sleeping in {{ fmtTime(player.sleepRemaining) }}
      </div>
    </div>

    <!-- Normalize toggle -->
    <label class="flex items-center gap-2 text-sm">
      <input type="checkbox" v-model="player.normalize" class="accent-green-500" />
      Volume normalization (reduce peaks)
    </label>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { usePlayer } from '../stores/player'

const player = usePlayer()
const bass = ref(0)
const treble = ref(0)

const repeatLabel = computed(() =>
  player.repeat === 'off' ? 'Repeat Off'
  : player.repeat === 'all' ? 'Repeat All'
  : 'Repeat One'
)

function fmtTime(s) {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}
</script>