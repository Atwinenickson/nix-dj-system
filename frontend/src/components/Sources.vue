<template>
  <div class="pb-32">
    <!-- Hero -->
    <div class="mx-4 mt-4 mb-6 rounded-2xl overflow-hidden relative
                bg-gradient-to-br from-sky-700 via-blue-700 to-indigo-800 p-6 shadow-2xl">
      <div class="absolute -top-10 -right-10 w-64 h-64 rounded-full bg-white/10 blur-3xl"></div>

      <div class="relative">
        <div class="text-xs tracking-[0.3em] uppercase text-white/70 mb-1">
          Library
        </div>
        <h1 class="text-3xl md:text-4xl font-black text-white drop-shadow">
          🌐 Sources
        </h1>
        <p class="text-white/80 text-sm mt-2 max-w-2xl">
          Add music from local folders, files, or online URLs. Everything you add is scanned
          and streamed by the backend.
        </p>

        <div class="mt-4 flex items-center gap-3 flex-wrap text-white/90 text-sm">
          <div class="bg-black/30 rounded-full px-3 py-1 backdrop-blur">
            {{ sources.length }} source{{ sources.length === 1 ? '' : 's' }}
          </div>
          <button
            @click="load"
            class="bg-white/20 hover:bg-white/30 rounded-full px-4 py-1.5 font-semibold text-sm backdrop-blur"
          >↻ Refresh</button>
        </div>
      </div>
    </div>

    <!-- Add new source -->
    <div class="mx-4 mb-6 rounded-2xl bg-zinc-900 border border-zinc-800 p-5">
      <h2 class="text-sm uppercase tracking-widest text-zinc-400 mb-4">
        ➕ Add source
      </h2>

      <!-- Kind tabs -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
        <button
          v-for="k in kinds" :key="k.id"
          @click="kind = k.id"
          :class="kind === k.id
            ? 'bg-sky-500 text-black font-semibold'
            : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'"
          class="rounded-xl py-3 text-xs flex flex-col items-center gap-1"
        >
          <span class="text-lg">{{ k.emoji }}</span>
          <span>{{ k.label }}</span>
        </button>
      </div>

      <!-- Hint -->
      <p class="text-xs text-zinc-500 mb-3">{{ currentKind.hint }}</p>

      <!-- Location input -->
      <div class="flex flex-col sm:flex-row gap-2">
        <input
          v-model="location"
          :placeholder="currentKind.placeholder"
          @keyup.enter="addSource"
          class="flex-1 bg-zinc-800 rounded-lg px-4 py-3 outline-none
                 focus:ring-2 ring-sky-500"
        />
        <button
          v-if="kind === 'folder' && canPickFolder"
          @click="pickLocalFolder"
          class="bg-zinc-700 hover:bg-zinc-600 text-white px-4 py-3 rounded-lg font-semibold whitespace-nowrap"
          title="Pick a folder from this device (Chromium only)"
        >📂 Browse…</button>
        <button
          @click="addSource"
          :disabled="busy || !location.trim()"
          class="bg-sky-500 hover:bg-sky-400 text-black px-6 py-3 rounded-lg font-semibold disabled:opacity-50"
        >{{ busy ? 'Adding…' : 'Add' }}</button>
      </div>

      <!-- Label -->
      <input
        v-model="label"
        placeholder="Optional label (e.g. 'Afro Mix 2024')"
        class="mt-2 w-full bg-zinc-800 rounded-lg px-4 py-2 text-sm outline-none
               focus:ring-2 ring-sky-500"
      />

      <!-- Feedback -->
      <div v-if="error" class="mt-3 text-sm text-red-400">⚠️ {{ error }}</div>
      <div v-if="success" class="mt-3 text-sm text-green-400">✓ {{ success }}</div>
    </div>

    <!-- Existing sources -->
    <div class="mx-4">
      <div class="text-xs uppercase tracking-widest text-zinc-500 mb-3">
        Connected sources
      </div>

      <div v-if="!sources.length" class="text-center py-16 text-zinc-500">
        <div class="text-6xl mb-4 opacity-40">🌐</div>
        <div>No sources yet</div>
        <div class="text-sm text-zinc-600 mt-1">
          Add a folder, file, or URL above to start building your library
        </div>
      </div>

      <ul v-else class="space-y-2">
        <li
          v-for="s in sources" :key="s.id"
          class="flex items-center gap-3 px-4 py-3 rounded-xl bg-zinc-900/60
                 hover:bg-zinc-800 border border-zinc-800/50 group"
        >
          <div class="text-2xl shrink-0">{{ iconFor(s.kind) }}</div>

          <div class="min-w-0 flex-1">
            <div class="font-medium text-sm truncate">
              {{ s.label || shortLoc(s.location) }}
            </div>
            <div class="text-xs text-zinc-500 truncate">{{ s.location }}</div>
          </div>

          <div class="text-[10px] uppercase px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 shrink-0">
            {{ s.kind }}
          </div>

          <button
            @click="removeSource(s)"
            class="text-red-400 hover:text-red-300 w-8 h-8 rounded hover:bg-zinc-700
                   opacity-0 group-hover:opacity-100 transition"
            title="Remove"
          >×</button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const sources = ref([])
const kind = ref('folder')
const location = ref('')
const label = ref('')
const busy = ref(false)
const error = ref('')
const success = ref('')

const kinds = [
  { id: 'folder', label: 'Folder',      emoji: '📁',
    placeholder: '/Users/you/Music',
    hint: 'A folder on the machine where the backend runs. Add its full path.' },
  { id: 'file',   label: 'Single file', emoji: '📄',
    placeholder: '/Users/you/song.mp3',
    hint: 'One audio file on the backend machine.' },
  { id: 'url',    label: 'URL',         emoji: '🔗',
    placeholder: 'https://example.com/song.mp3',
    hint: 'A direct link to an audio file. The backend will download and cache it.' },
  { id: 'stream', label: 'Live stream', emoji: '📡',
    placeholder: 'https://stream.radio.com/live',
    hint: 'A radio / live stream URL. Plays endlessly.' },
]
const currentKind = computed(() => kinds.find(k => k.id === kind.value) || kinds[0])

const canPickFolder = typeof window !== 'undefined' && 'showDirectoryPicker' in window

onMounted(load)

async function load() {
  try {
    const r = await fetch('/api/sources')
    sources.value = r.ok ? await r.json() : []
  } catch {
    sources.value = []
  }
}

async function pickLocalFolder() {
  try {
    const handle = await window.showDirectoryPicker()
    // Only the *name* is accessible; we cannot extract the full path for security.
    // So we warn the user to type the full path manually.
    location.value = handle.name
    error.value = `Browser only gives folder name ("${handle.name}"). ` +
                  `Please type the full path manually, e.g. /Users/you/${handle.name}`
  } catch {}
}

async function addSource() {
  error.value = ''
  success.value = ''
  busy.value = true
  try {
    const r = await fetch('/api/sources', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind: kind.value, location: location.value.trim(), label: label.value.trim() }),
    })
    const data = await r.json()
    if (!r.ok) {
      error.value = data.detail || 'Failed to add source'
    } else {
      success.value = `Added · ${data.added} track${data.added === 1 ? '' : 's'} ingested`
      location.value = ''
      label.value = ''
      await load()
      setTimeout(() => (success.value = ''), 4000)
    }
  } catch (e) {
    error.value = 'Network error'
  } finally {
    busy.value = false
  }
}

async function removeSource(s) {
  if (!confirm(`Remove source "${s.label || s.location}"?`)) return
  try {
    await fetch(`/api/sources/${s.id}`, { method: 'DELETE' })
    await load()
  } catch {}
}

function iconFor(k) {
  return { folder: '📁', file: '📄', url: '🔗', stream: '📡' }[k] || '🌐'
}
function shortLoc(loc) {
  if (loc.length < 50) return loc
  return '…' + loc.slice(-47)
}
</script>