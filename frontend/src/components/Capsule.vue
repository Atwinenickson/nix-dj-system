<template>
  <div class="pb-32">
    <!-- ===================== Hero banner ===================== -->
    <div class="mx-4 mt-4 mb-6 rounded-2xl overflow-hidden relative
                bg-gradient-to-br from-amber-700 via-rose-700 to-purple-800 p-6 shadow-2xl">
      <div class="absolute -top-10 -right-10 w-64 h-64 rounded-full bg-white/10 blur-3xl"></div>
      <div class="absolute -bottom-16 -left-10 w-52 h-52 rounded-full bg-black/20 blur-3xl"></div>

      <div class="relative">
        <div class="text-xs tracking-[0.3em] uppercase text-white/70 mb-1">
          Time Machine
        </div>
        <h1 class="text-3xl md:text-4xl font-black text-white drop-shadow">
          🕰️ Capsule
        </h1>
        <p class="text-white/80 text-sm mt-2 max-w-2xl">
          Tracks you loved but haven't heard in a while. Rediscover your own history.
        </p>

        <!-- Live summary + actions -->
        <div class="mt-4 flex items-center gap-3 flex-wrap text-white/90 text-sm">
          <div class="bg-black/30 rounded-full px-3 py-1 backdrop-blur">
            {{ tracks.length }} track{{ tracks.length === 1 ? '' : 's' }}
          </div>
          <div class="bg-black/30 rounded-full px-3 py-1 backdrop-blur">
            {{ fmtTotal(tracksDuration) }} mix
          </div>

          <button
            v-if="tracks.length"
            @click="queueAll(tracks)"
            class="bg-white/20 hover:bg-white/30 rounded-full px-4 py-1.5 font-semibold text-sm backdrop-blur"
          >➕ Queue mix</button>

          <button
            v-if="tracks.length"
            @click="playAll"
            class="bg-green-500 hover:bg-green-400 text-black rounded-full px-4 py-1.5 font-semibold text-sm"
          >▶ Play mix</button>

          <button
            v-if="tracks.length"
            @click="openSaveDialog"
            class="bg-pink-500 hover:bg-pink-400 text-white rounded-full px-4 py-1.5 font-semibold text-sm"
          >💾 Save as playlist</button>

          <button
            @click="toggleCompare"
            :class="compareMode
              ? 'bg-indigo-500 text-white'
              : 'bg-white/20 hover:bg-white/30 text-white'"
            class="rounded-full px-4 py-1.5 font-semibold text-sm backdrop-blur"
          >🔬 {{ compareMode ? 'Exit compare' : 'Compare windows' }}</button>
        </div>
      </div>

      <!-- Dev tools (hover-visible, top-right of banner) -->
      <div class="absolute top-3 right-3 flex gap-2 opacity-40 hover:opacity-100 transition">
        <button
          @click="seed"
          title="DEV: seed fake history"
          class="bg-black/40 hover:bg-black/60 text-white text-[10px] px-2 py-1 rounded"
        >🌱 Seed</button>
        <button
          @click="clearHistory"
          title="DEV: wipe history"
          class="bg-black/40 hover:bg-black/60 text-white text-[10px] px-2 py-1 rounded"
        >🧹 Clear</button>
      </div>
    </div>

    <!-- ===================== Auto-scroll preview strip ===================== -->
    <section v-if="tracks.length && !compareMode" class="mx-4 mb-6">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm uppercase tracking-widest text-zinc-400">
          🎞️ Preview · {{ tracks.length }} tracks
        </h2>
        <button
          @click="autoScrolling = !autoScrolling"
          :class="autoScrolling
            ? 'bg-green-500 text-black'
            : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'"
          class="rounded-full px-3 py-1 text-xs font-semibold"
        >{{ autoScrolling ? '⏸ Pause auto-scroll' : '▶ Auto-scroll' }}</button>
      </div>

      <div
        ref="stripEl"
        class="flex gap-3 overflow-x-auto scroll-smooth pb-3 scrollbar-hide"
      >
        <div
          v-for="(t, i) in tracks" :key="'pv-' + t.id"
          @click="player.play(t)"
          :ref="el => setStripRef(el, i)"
          class="shrink-0 w-32 cursor-pointer group"
        >
          <div class="relative aspect-square rounded-lg overflow-hidden bg-zinc-800 shadow-lg
                      group-hover:ring-2 ring-amber-400 transition">
            <img
              v-if="!broken[t.id]"
              :src="`/api/art/${t.id}`"
              class="w-full h-full object-cover"
              @error="broken[t.id] = true"
            />
            <div
              v-else
              class="w-full h-full flex items-center justify-center text-3xl font-black text-white"
              :style="{ background: gradientFor(t.artist) }"
            >{{ initials(t.artist) }}</div>

            <div
              v-if="player.current?.id === t.id"
              class="absolute inset-0 bg-black/40 flex items-center justify-center"
            >
              <div class="text-2xl text-green-400 animate-pulse">▶</div>
            </div>

            <div class="absolute bottom-1 right-1 bg-black/70 rounded px-1.5 py-0.5 text-[10px] text-white">
              {{ fmt(t.duration) }}
            </div>
          </div>
          <div class="mt-1 text-xs font-medium truncate">{{ t.title }}</div>
          <div class="text-[10px] text-zinc-500 truncate">{{ t.artist }}</div>
        </div>
      </div>
    </section>

    <!-- ===================== COMPARE MODE ===================== -->
    <section v-if="compareMode" class="mx-4 mb-6">
      <!-- Window picker -->
      <div class="rounded-2xl bg-zinc-900 border border-zinc-800 p-5 mb-4">
        <h2 class="text-sm uppercase tracking-widest text-zinc-400 mb-4">
          🔬 Compare two time windows
        </h2>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Left window -->
          <div>
            <div class="text-xs uppercase text-cyan-400 mb-2">Left window</div>
            <div class="grid grid-cols-3 gap-2">
              <button
                v-for="w in comparePresets" :key="'a-' + w.id"
                @click="compareA = w.id; loadCompare()"
                :class="compareA === w.id
                  ? 'bg-cyan-500 text-black font-semibold'
                  : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'"
                class="rounded-lg py-2 text-xs"
              >{{ w.label }}</button>
            </div>
          </div>

          <!-- Right window -->
          <div>
            <div class="text-xs uppercase text-pink-400 mb-2">Right window</div>
            <div class="grid grid-cols-3 gap-2">
              <button
                v-for="w in comparePresets" :key="'b-' + w.id"
                @click="compareB = w.id; loadCompare()"
                :class="compareB === w.id
                  ? 'bg-pink-500 text-black font-semibold'
                  : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'"
                class="rounded-lg py-2 text-xs"
              >{{ w.label }}</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Side-by-side results -->
      <div v-if="compareData" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Left column -->
        <div class="rounded-2xl bg-zinc-900/60 border border-cyan-500/30 p-4">
          <div class="flex items-center justify-between mb-3">
            <div>
              <div class="text-xs uppercase tracking-widest text-cyan-400">
                {{ compareData.a.label }}
              </div>
              <div class="text-sm text-zinc-400">
                {{ compareData.a.tracks.length }} tracks
                · {{ fmtTotal(compareDuration(compareData.a.tracks)) }}
              </div>
            </div>
            <button
              v-if="compareData.a.tracks.length"
              @click="queueAll(compareData.a.tracks)"
              class="text-xs bg-cyan-500 hover:bg-cyan-400 text-black rounded-full px-3 py-1"
            >➕ Queue</button>
          </div>
          <ul class="space-y-1 max-h-96 overflow-y-auto">
            <li
              v-for="t in compareData.a.tracks" :key="'a-' + t.id"
              class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-zinc-800 group"
            >
              <div class="w-9 h-9 rounded overflow-hidden shrink-0 bg-zinc-800">
                <img v-if="!broken[t.id]" :src="`/api/art/${t.id}`"
                     class="w-full h-full object-cover" @error="broken[t.id] = true" />
                <div v-else class="w-full h-full flex items-center justify-center text-[10px] font-bold text-white"
                     :style="{ background: gradientFor(t.artist) }">{{ initials(t.artist) }}</div>
              </div>
              <div class="min-w-0 flex-1">
                <div class="text-sm truncate">{{ t.title }}</div>
                <div class="text-[10px] text-zinc-500 truncate">{{ t.artist }}</div>
              </div>
              <button @click="player.play(t)" class="text-green-400 opacity-0 group-hover:opacity-100">▶</button>
            </li>
            <li v-if="!compareData.a.tracks.length" class="text-xs text-zinc-500 py-4 text-center">
              No tracks in this window
            </li>
          </ul>
        </div>

        <!-- Right column -->
        <div class="rounded-2xl bg-zinc-900/60 border border-pink-500/30 p-4">
          <div class="flex items-center justify-between mb-3">
            <div>
              <div class="text-xs uppercase tracking-widest text-pink-400">
                {{ compareData.b.label }}
              </div>
              <div class="text-sm text-zinc-400">
                {{ compareData.b.tracks.length }} tracks
                · {{ fmtTotal(compareDuration(compareData.b.tracks)) }}
              </div>
            </div>
            <button
              v-if="compareData.b.tracks.length"
              @click="queueAll(compareData.b.tracks)"
              class="text-xs bg-pink-500 hover:bg-pink-400 text-black rounded-full px-3 py-1"
            >➕ Queue</button>
          </div>
          <ul class="space-y-1 max-h-96 overflow-y-auto">
            <li
              v-for="t in compareData.b.tracks" :key="'b-' + t.id"
              class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-zinc-800 group"
            >
              <div class="w-9 h-9 rounded overflow-hidden shrink-0 bg-zinc-800">
                <img v-if="!broken[t.id]" :src="`/api/art/${t.id}`"
                     class="w-full h-full object-cover" @error="broken[t.id] = true" />
                <div v-else class="w-full h-full flex items-center justify-center text-[10px] font-bold text-white"
                     :style="{ background: gradientFor(t.artist) }">{{ initials(t.artist) }}</div>
              </div>
              <div class="min-w-0 flex-1">
                <div class="text-sm truncate">{{ t.title }}</div>
                <div class="text-[10px] text-zinc-500 truncate">{{ t.artist }}</div>
              </div>
              <button @click="player.play(t)" class="text-green-400 opacity-0 group-hover:opacity-100">▶</button>
            </li>
            <li v-if="!compareData.b.tracks.length" class="text-xs text-zinc-500 py-4 text-center">
              No tracks in this window
            </li>
          </ul>
        </div>
      </div>
    </section>

    <!-- ===================== NORMAL MODE FILTERS ===================== -->
    <div v-if="!compareMode" class="mx-4 mb-6 grid grid-cols-1 lg:grid-cols-2 gap-4">

      <!-- Time window -->
      <section class="rounded-2xl bg-zinc-900 border border-zinc-800 p-5">
        <h2 class="text-sm uppercase tracking-widest text-zinc-400 mb-4">
          🗓️ When was it loved?
        </h2>
        <div class="grid grid-cols-4 gap-2">
          <button
            v-for="r in ranges" :key="r.id"
            @click="setRange(r)"
            :class="activeRange === r.id
              ? 'bg-amber-500 text-black font-semibold shadow-lg shadow-amber-500/30'
              : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'"
            class="rounded-xl py-3 text-xs transition flex flex-col items-center gap-1"
          >
            <span class="text-lg">{{ r.emoji }}</span>
            <span>{{ r.label }}</span>
          </button>
        </div>
      </section>

      <!-- Mix length -->
      <section class="rounded-2xl bg-zinc-900 border border-zinc-800 p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm uppercase tracking-widest text-zinc-400">
            ⏱️ Mix length
          </h2>
          <span class="text-2xl font-black text-cyan-400 tabular-nums">
            {{ mixLabel }}
          </span>
        </div>

        <input
          type="range" min="0" max="240" step="5"
          v-model.number="targetMinutes"
          @change="load"
          class="w-full accent-cyan-500"
        />
        <div class="flex justify-between text-[10px] text-zinc-500 mt-1">
          <span>Any</span><span>30m</span><span>1h</span><span>2h</span><span>4h</span>
        </div>

        <div class="grid grid-cols-4 gap-2 mt-4">
          <button
            v-for="p in mixPresets" :key="p.v"
            @click="targetMinutes = p.v; load()"
            :class="targetMinutes === p.v
              ? 'bg-cyan-500 text-black'
              : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'"
            class="rounded-lg py-2 text-xs font-semibold"
          >{{ p.l }}</button>
        </div>
      </section>
    </div>

    <!-- ===================== LOADING / EMPTY ===================== -->
    <div v-if="loading && !compareMode" class="mx-4 text-center py-12 text-zinc-500">
      <div class="inline-block w-6 h-6 border-2 border-zinc-600 border-t-amber-400 rounded-full animate-spin"></div>
      <div class="mt-3 text-sm">Digging through your history…</div>
    </div>

    <div v-else-if="!tracks.length && !compareMode" class="mx-4 text-center py-16">
      <div class="text-6xl mb-4 opacity-40">🕰️</div>
      <div class="text-zinc-400">Nothing in your capsule yet</div>
      <div class="text-zinc-600 text-sm mt-1">
        Try a shorter window, or hit 🌱 Seed in the top-right corner
      </div>
    </div>

    <!-- ===================== NORMAL LIST ===================== -->
    <div v-else-if="!compareMode" class="mx-4">
      <div class="text-xs uppercase tracking-widest text-zinc-500 mb-3">
        {{ tracks.length }} memories · {{ fmtTotal(tracksDuration) }}
      </div>

      <ul class="space-y-2">
        <li
          v-for="(t, i) in tracks" :key="t.id"
          class="flex items-center gap-3 px-3 py-3 rounded-xl bg-zinc-900/60 hover:bg-zinc-800
                 group transition-colors border border-zinc-800/50"
        >
          <div class="text-2xl font-black w-8 text-center shrink-0
                      bg-gradient-to-br from-amber-400 to-rose-500
                      bg-clip-text text-transparent">
            {{ i + 1 }}
          </div>

          <div class="w-14 h-14 rounded-lg overflow-hidden shrink-0 bg-zinc-800 shadow-lg">
            <img
              v-if="!broken[t.id]"
              :src="`/api/art/${t.id}`"
              class="w-full h-full object-cover"
              @error="broken[t.id] = true"
            />
            <div
              v-else
              class="w-full h-full flex items-center justify-center text-base font-bold text-white"
              :style="{ background: gradientFor(t.artist) }"
            >{{ initials(t.artist) }}</div>
          </div>

          <div class="min-w-0 flex-1">
            <div class="font-medium truncate">{{ t.title }}</div>
            <div class="text-xs text-zinc-400 truncate">
              {{ t.artist }}<span v-if="t.album"> — {{ t.album }}</span>
            </div>
            <div class="text-xs mt-1">
              <span v-if="t.plays" class="text-amber-400/90">
                {{ t.plays }} play{{ t.plays === 1 ? '' : 's' }}
              </span>
              <span v-if="t.last_played" class="text-zinc-500">
                · last heard {{ relativeDate(t.last_played) }}
              </span>
            </div>
          </div>

          <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
            <button
              @click="player.play(t)"
              class="bg-amber-500 hover:bg-amber-400 text-black rounded-full w-9 h-9 text-sm shadow"
            >▶</button>
            <button
              @click="player.enqueue(t)"
              class="text-zinc-300 hover:text-white w-9 h-9 rounded hover:bg-zinc-700"
            >+</button>
          </div>
        </li>
      </ul>
    </div>

    <!-- ===================== SAVE-AS-PLAYLIST MODAL ===================== -->
    <div
      v-if="saveDialog"
      class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      @click.self="saveDialog = false"
    >
      <div class="bg-zinc-900 rounded-2xl p-6 w-full max-w-md border border-zinc-700 shadow-2xl">
        <h3 class="text-xl font-bold mb-2">💾 Save mix as playlist</h3>
        <p class="text-zinc-400 text-sm mb-4">
          {{ tracks.length }} tracks · {{ fmtTotal(tracksDuration) }}
        </p>

        <div class="flex gap-2 mb-3">
          <input
            v-model="playlistName"
            placeholder="Playlist name (e.g. 'Late Night 90s')"
            class="flex-1 bg-zinc-800 rounded-lg px-4 py-3 outline-none
                   focus:ring-2 ring-pink-500"
            @keyup.enter="saveMix"
          />
          <button
            @click="autoName"
            class="bg-purple-600 hover:bg-purple-500 text-white px-4 py-3 rounded-lg font-semibold whitespace-nowrap"
            title="Auto-generate name from track mix"
          >🎲 Auto-name</button>
        </div>

        <div v-if="autoNameInfo" class="text-xs text-zinc-400 mb-4 flex flex-wrap gap-3">
          <span v-if="autoNameInfo.dominant_artist">
            🎤 Top artist: <b class="text-zinc-200">{{ autoNameInfo.dominant_artist }}</b>
            ({{ Math.round(autoNameInfo.artist_share * 100) }}%)
          </span>
          <span v-if="autoNameInfo.dominant_genre">
            🎵 Top genre: <b class="text-zinc-200">{{ autoNameInfo.dominant_genre }}</b>
            ({{ Math.round(autoNameInfo.genre_share * 100) }}%)
          </span>
        </div>

        <div class="flex justify-end gap-2">
          <button
            @click="saveDialog = false"
            class="px-4 py-2 rounded-lg text-zinc-300 hover:bg-zinc-800"
          >Cancel</button>
          <button
            @click="saveMix"
            :disabled="!playlistName.trim() || saving"
            class="px-4 py-2 rounded-lg bg-pink-500 hover:bg-pink-400 text-white font-semibold disabled:opacity-50"
          >{{ saving ? 'Saving…' : 'Save' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { usePlayer } from '../stores/player'

const player = usePlayer()

// ---- State ----
const tracks = ref([])
const broken = reactive({})
const loading = ref(false)

// ---- Time window filters ----
const ranges = [
  { id: 'day',   label: 'Today',      days: 1,    emoji: '☀️' },
  { id: 'week',  label: 'This Week',  days: 7,    emoji: '📅' },
  { id: 'month', label: 'This Month', days: 30,   emoji: '🗓️' },
  { id: '3mo',   label: '3 Months',   days: 90,   emoji: '🌱' },
  { id: '6mo',   label: '6 Months',   days: 180,  emoji: '🍂' },
  { id: '1y',    label: '1 Year',     days: 365,  emoji: '🎂' },
  { id: '2y',    label: '2 Years',    days: 730,  emoji: '🕰️' },
  { id: 'all',   label: 'All Time',   days: 3650, emoji: '∞' },
]
const activeRange = ref('month')
const currentRange = computed(() =>
  ranges.find(r => r.id === activeRange.value) || ranges[2]
)
function setRange(r) {
  activeRange.value = r.id
  load()
}

// ---- Mix length ----
const targetMinutes = ref(0)
const mixPresets = [
  { v: 0,   l: 'Any' },
  { v: 10,  l: '10m' },
  { v: 30,  l: '30m' },
  { v: 60,  l: '1h' },
  { v: 120, l: '2h' },
]
const mixLabel = computed(() =>
  targetMinutes.value === 0 ? 'Any length' : fmtTotal(targetMinutes.value * 60)
)

// ---- Auto-scroll strip ----
const stripEl = ref(null)
const autoScrolling = ref(false)
let autoScrollTimer = null
let autoScrollIndex = 0
const stripRefs = []

function setStripRef(el, i) {
  if (el) stripRefs[i] = el
}
function startAutoScroll() {
  stopAutoScroll()
  autoScrollTimer = setInterval(() => {
    if (!stripRefs.length) return
    autoScrollIndex = (autoScrollIndex + 1) % stripRefs.length
    const el = stripRefs[autoScrollIndex]
    if (el?.scrollIntoView) {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
    }
  }, 3000)
}
function stopAutoScroll() {
  clearInterval(autoScrollTimer)
  autoScrollTimer = null
}
watch(autoScrolling, on => { on ? startAutoScroll() : stopAutoScroll() })

// ---- Compare mode ----
const compareMode = ref(false)
const compareData = ref(null)
const compareA = ref('1y')
const compareB = ref('6mo')

const comparePresets = [
  { id: 'week',  label: '1w',  start: 7,    end: 30 },
  { id: 'month', label: '1mo', start: 30,   end: 90 },
  { id: '3mo',   label: '3mo', start: 90,   end: 180 },
  { id: '6mo',   label: '6mo', start: 180,  end: 365 },
  { id: '1y',    label: '1y',  start: 365,  end: 730 },
  { id: '2y',    label: '2y+', start: 730,  end: 3650 },
]

function toggleCompare() {
  compareMode.value = !compareMode.value
  if (compareMode.value) {
    stopAutoScroll()
    autoScrolling.value = false
    loadCompare()
  }
}

function findPreset(id) {
  return comparePresets.find(p => p.id === id) || comparePresets[4]
}

async function loadCompare() {
  const A = findPreset(compareA.value)
  const B = findPreset(compareB.value)
  try {
    const params = new URLSearchParams({
      a_start: A.start, a_end: A.end,
      b_start: B.start, b_end: B.end,
      limit: 25,
    })
    const r = await fetch(`/api/capsule/compare?${params}`)
    compareData.value = r.ok ? await r.json() : null
  } catch {
    compareData.value = null
  }
}

function compareDuration(list) {
  return list.reduce((s, t) => s + (t.duration || 0), 0)
}

// ---- Fetch main capsule ----
async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      days_ago_start: currentRange.value.days,
      days_ago_end: 3650,
      limit: 200,
      target_minutes: targetMinutes.value,
    })
    const r = await fetch(`/api/capsule?${params}`)
    tracks.value = r.ok ? await r.json() : []
    autoScrollIndex = 0
    stripRefs.length = 0
  } catch {
    tracks.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
onUnmounted(stopAutoScroll)

// ---- Bulk actions ----
function queueAll(list) {
  const src = Array.isArray(list) ? list : tracks.value
  src.forEach(t => player.enqueue(t))
}
function playAll() {
  if (!tracks.value.length) return
  const [first, ...rest] = tracks.value
  rest.forEach(t => player.enqueue(t))
  player.play(first)
}

// ---- Save as playlist ----
const saveDialog = ref(false)
const playlistName = ref('')
const saving = ref(false)
const autoNameInfo = ref(null)

function openSaveDialog() {
  playlistName.value = `Capsule · ${new Date().toLocaleDateString()}`
  autoNameInfo.value = null
  saveDialog.value = true
}

async function autoName() {
  if (!tracks.value.length) return
  try {
    const r = await fetch('/api/capsule/auto-name', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ track_ids: tracks.value.map(t => t.id) }),
    })
    if (!r.ok) return
    const data = await r.json()
    playlistName.value = data.name
    autoNameInfo.value = data
  } catch {}
}

async function saveMix() {
  if (!playlistName.value.trim() || !tracks.value.length) return
  saving.value = true
  try {
    const trackIds = tracks.value.map(t => t.id)
    const r = await fetch(
      `/api/playlists/${encodeURIComponent(playlistName.value)}/bulk`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ track_ids: trackIds }),
      }
    )
    if (r.ok) saveDialog.value = false
    else alert('Failed to save playlist')
  } catch {
    alert('Failed to save playlist')
  } finally {
    saving.value = false
  }
}

// ---- DEV: seed / clear history ----
async function seed() {
  loading.value = true
  try {
    const r = await fetch('/api/dev/seed-history?count=40&spread_days=400', { method: 'POST' })
    if (r.ok) await load()
  } catch {}
  loading.value = false
}
async function clearHistory() {
  if (!confirm('Wipe ALL play history? This cannot be undone.')) return
  try {
    await fetch('/api/dev/clear-history', { method: 'DELETE' })
    await load()
  } catch {}
}

// ---- Totals & formatting ----
const tracksDuration = computed(() =>
  tracks.value.reduce((sum, t) => sum + (t.duration || 0), 0)
)

const fmt = s => {
  if (!s || isNaN(s)) return '—'
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60).toString().padStart(2, '0')
  return `${m}:${sec}`
}
const fmtTotal = s => {
  if (!s) return '0m'
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
function relativeDate(iso) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days < 1) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 30) return `${days} days ago`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months} month${months === 1 ? '' : 's'} ago`
  const years = Math.floor(months / 12)
  return `${years} year${years === 1 ? '' : 's'} ago`
}
</script>

<style scoped>
.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
</style>