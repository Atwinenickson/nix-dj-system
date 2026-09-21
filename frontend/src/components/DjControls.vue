<template>
  <div class="pb-32">
    <!-- Hero banner (neon mixer vibe) -->
    <div class="mx-4 mt-4 mb-6 rounded-2xl overflow-hidden relative
                bg-gradient-to-br from-fuchsia-700 via-purple-700 to-indigo-800 p-6 shadow-2xl">
      <div class="absolute -top-10 -right-10 w-72 h-72 rounded-full bg-white/10 blur-3xl"></div>

      <div class="relative flex items-center justify-between flex-wrap gap-4">
        <div>
          <div class="text-xs tracking-[0.3em] uppercase text-white/70 mb-1">
            Studio
          </div>
          <h1 class="text-3xl md:text-4xl font-black text-white drop-shadow">
            🎛️ DJ Controls
          </h1>
          <p class="text-white/80 text-sm mt-1">
            Shape the sound — crossfade, EQ, tempo, sleep.
          </p>
        </div>

        <!-- Live LEDs -->
        <div class="flex gap-2">
          <div class="w-3 h-3 rounded-full"
               :class="player.isPlaying ? 'bg-green-400 animate-pulse' : 'bg-zinc-600'"></div>
          <div class="w-3 h-3 rounded-full"
               :class="player.crossfade > 0 ? 'bg-cyan-400' : 'bg-zinc-600'"></div>
          <div class="w-3 h-3 rounded-full"
               :class="player.autoDj ? 'bg-pink-400 animate-pulse' : 'bg-zinc-600'"></div>
        </div>
      </div>
    </div>

    <div class="mx-4 grid grid-cols-1 lg:grid-cols-2 gap-4">

      <!-- ============= Playback Modes ============= -->
      <section class="rounded-2xl bg-zinc-900 border border-zinc-800 p-5">
        <h2 class="text-sm uppercase tracking-widest text-zinc-400 mb-4">
          Playback Modes
        </h2>
        <div class="grid grid-cols-3 gap-3">
          <button
            @click="player.toggleShuffle()"
            :class="player.shuffle
              ? 'bg-green-500 text-black shadow-lg shadow-green-500/30'
              : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'"
            class="rounded-xl py-4 flex flex-col items-center gap-1 transition"
          >
            <span class="text-2xl">🔀</span>
            <span class="text-xs font-semibold">Shuffle</span>
            <span class="text-[10px] opacity-70">{{ player.shuffle ? 'ON' : 'OFF' }}</span>
          </button>

          <button
            @click="player.cycleRepeat()"
            :class="player.repeat !== 'off'
              ? 'bg-green-500 text-black shadow-lg shadow-green-500/30'
              : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'"
            class="rounded-xl py-4 flex flex-col items-center gap-1 transition"
          >
            <span class="text-2xl">{{ player.repeat === 'one' ? '🔂' : '🔁' }}</span>
            <span class="text-xs font-semibold">Repeat</span>
            <span class="text-[10px] opacity-70 uppercase">{{ player.repeat }}</span>
          </button>

          <button
            @click="player.autoDj = !player.autoDj"
            :class="player.autoDj
              ? 'bg-pink-500 text-black shadow-lg shadow-pink-500/30'
              : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'"
            class="rounded-xl py-4 flex flex-col items-center gap-1 transition"
          >
            <span class="text-2xl">🤖</span>
            <span class="text-xs font-semibold">Auto-DJ</span>
            <span class="text-[10px] opacity-70">{{ player.autoDj ? 'ON' : 'OFF' }}</span>
          </button>
        </div>

        <button
          @click="player.shuffleLibrary?.(20)"
          class="mt-4 w-full bg-gradient-to-r from-purple-600 to-pink-600
                 hover:from-purple-500 hover:to-pink-500
                 text-white font-semibold rounded-xl py-3 shadow-lg"
        >
          ✨ Surprise me — queue 20 random tracks
        </button>
      </section>

      <!-- ============= Crossfade ============= -->
      <section class="rounded-2xl bg-zinc-900 border border-zinc-800 p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm uppercase tracking-widest text-zinc-400">
            ⤫ Crossfade
          </h2>
          <span class="text-2xl font-black text-cyan-400 tabular-nums">
            {{ player.crossfade }}s
          </span>
        </div>
        <input
          type="range" min="0" max="12" step="0.5"
          v-model.number="player.crossfade"
          class="w-full accent-cyan-500"
        />
        <div class="flex justify-between text-[10px] text-zinc-500 mt-1">
          <span>Off</span><span>4s</span><span>8s</span><span>12s</span>
        </div>

        <p class="text-xs text-zinc-500 mt-4">
          Blends the last {{ player.crossfade }}s of each track into the next one.
          Set to <b>0</b> for a hard cut.
        </p>
      </section>

      <!-- ============= EQ ============= -->
      <section class="rounded-2xl bg-zinc-900 border border-zinc-800 p-5">
        <h2 class="text-sm uppercase tracking-widest text-zinc-400 mb-4">
          🎚️ Equalizer
        </h2>
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="font-medium">Bass</span>
              <span class="tabular-nums" :class="bass === 0 ? 'text-zinc-500' : 'text-green-400'">
                {{ bass > 0 ? '+' : '' }}{{ bass }} dB
              </span>
            </div>
            <input
              type="range" min="-12" max="12" step="1"
              v-model.number="bass"
              @input="player.setBass?.(bass)"
              class="w-full accent-green-500"
            />
          </div>

          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="font-medium">Treble</span>
              <span class="tabular-nums" :class="treble === 0 ? 'text-zinc-500' : 'text-green-400'">
                {{ treble > 0 ? '+' : '' }}{{ treble }} dB
              </span>
            </div>
            <input
              type="range" min="-12" max="12" step="1"
              v-model.number="treble"
              @input="player.setTreble?.(treble)"
              class="w-full accent-green-500"
            />
          </div>

          <button
            @click="resetEQ"
            class="text-xs text-zinc-400 hover:text-white underline"
          >
            Reset EQ
          </button>
        </div>
      </section>

      <!-- ============= Tempo ============= -->
      <section class="rounded-2xl bg-zinc-900 border border-zinc-800 p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm uppercase tracking-widest text-zinc-400">
            ⏩ Playback Speed
          </h2>
          <span class="text-2xl font-black text-yellow-400 tabular-nums">
            {{ (player.playbackRate || 1).toFixed(2) }}×
          </span>
        </div>
        <input
          type="range" min="0.5" max="1.5" step="0.01"
          :value="player.playbackRate || 1"
          @input="e => player.setPlaybackRate?.(+e.target.value)"
          class="w-full accent-yellow-500"
        />
        <div class="flex justify-between text-[10px] text-zinc-500 mt-1">
          <span>0.5×</span><span>1.0×</span><span>1.5×</span>
        </div>
        <div class="flex gap-2 mt-4">
          <button
            v-for="s in [0.85, 1, 1.15]"
            :key="s"
            @click="player.setPlaybackRate?.(s)"
            :class="Math.abs((player.playbackRate || 1) - s) < 0.01
              ? 'bg-yellow-500 text-black'
              : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'"
            class="px-3 py-1 rounded-full text-xs"
          >{{ s }}×</button>
        </div>
      </section>

      <!-- ============= Sleep Timer ============= -->
      <section class="rounded-2xl bg-zinc-900 border border-zinc-800 p-5 lg:col-span-2">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm uppercase tracking-widest text-zinc-400">
            😴 Sleep Timer
          </h2>
          <span v-if="player.sleepRemaining > 0"
                class="text-2xl font-black text-yellow-400 tabular-nums">
            {{ fmtTimer(player.sleepRemaining) }}
          </span>
        </div>

        <div class="grid grid-cols-3 sm:grid-cols-5 gap-2">
          <button
            v-for="m in [5, 15, 30, 45, 60]" :key="m"
            @click="player.startSleep(m)"
            class="bg-zinc-800 hover:bg-zinc-700 rounded-xl py-3 text-sm font-semibold"
          >
            {{ m }}m
          </button>
        </div>

        <button
          v-if="player.sleepRemaining > 0"
          @click="player.cancelSleep()"
          class="mt-4 w-full bg-red-600/80 hover:bg-red-500 text-white font-semibold rounded-xl py-3"
        >
          Cancel sleep timer
        </button>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { usePlayer } from '../stores/player'

const player = usePlayer()
const bass = ref(0)
const treble = ref(0)

function resetEQ() {
  bass.value = 0
  treble.value = 0
  player.setBass?.(0)
  player.setTreble?.(0)
}

function fmtTimer(s) {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}
</script>