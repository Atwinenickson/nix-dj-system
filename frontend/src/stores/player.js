import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useJam } from './jam'

const API = ''

export const usePlayer = defineStore('player', () => {
  const jam = useJam()

  // Two audio elements for true crossfade
  const audioA = new Audio()
  const audioB = new Audio()
  ;[audioA, audioB].forEach(a => { a.crossOrigin = 'anonymous' })
  let activeAudio = audioA
  let idleAudio = audioB

  // ---- State ----
  const current = ref(null)
  const queue = ref([])
  const history = ref([])
  const isPlaying = ref(false)
  const progress = ref(0)
  const duration = ref(0)

  // ---- DJ Settings ----
  const volume = ref(0.9)
  const shuffle = ref(false)
  const repeat = ref('off')
  const crossfade = ref(4)
  const playbackRate = ref(1.0)
  const fadeIn = ref(2)
  const fadeOut = ref(2)
  const normalize = ref(false)

  // ---- Sleep Timer ----
  const sleepMinutes = ref(0)
  const sleepRemaining = ref(0)
  let sleepInterval = null

  // ---- Auto-DJ ----
  const autoDj = ref(false)

  // ---- Computed helpers (reactive!) ----
  const queueCount = computed(() => queue.value.length)
  const hasNext = computed(() => queue.value.length > 0)

  // ---- Web Audio ----
  let audioCtx, sourceA, sourceB, gainA, gainB, bassFilter, trebleFilter, masterGain
  function initAudio() {
    if (audioCtx) return
    audioCtx = new (window.AudioContext || window.webkitAudioContext)()

    sourceA = audioCtx.createMediaElementSource(audioA)
    sourceB = audioCtx.createMediaElementSource(audioB)

    gainA = audioCtx.createGain()
    gainB = audioCtx.createGain()

    bassFilter = audioCtx.createBiquadFilter()
    bassFilter.type = 'lowshelf'
    bassFilter.frequency.value = 200
    bassFilter.gain.value = 0

    trebleFilter = audioCtx.createBiquadFilter()
    trebleFilter.type = 'highshelf'
    trebleFilter.frequency.value = 3000
    trebleFilter.gain.value = 0

    masterGain = audioCtx.createGain()
    masterGain.gain.value = volume.value

    sourceA.connect(gainA).connect(bassFilter).connect(trebleFilter).connect(masterGain).connect(audioCtx.destination)
    sourceB.connect(gainB).connect(bassFilter)
  }

  function setBass(db) { if (bassFilter) bassFilter.gain.value = db }
  function setTreble(db) { if (trebleFilter) trebleFilter.gain.value = db }

  // ---- Core play ----
  async function play(track, { fade = true } = {}) {
    initAudio()
    if (audioCtx.state === 'suspended') await audioCtx.resume()

    current.value = track
    activeAudio.src = `${API}/api/stream/${track.id}`
    activeAudio.playbackRate = playbackRate.value
    activeAudio.volume = 1
    activeAudio.currentTime = 0

    if (fade && fadeIn.value > 0) {
      const now = audioCtx.currentTime
      const g = activeAudio === audioA ? gainA : gainB
      g.gain.cancelScheduledValues(now)
      g.gain.setValueAtTime(0, now)
      g.gain.linearRampToValueAtTime(1, now + fadeIn.value)
    }

    await activeAudio.play().catch(() => {})
    isPlaying.value = true
    fetch(`${API}/api/history/${track.id}`, { method: 'POST' }).catch(() => {})
  }

  // ---- Crossfade ----
  let crossfading = false
  async function crossfadeTo(next) {
    if (crossfading || !next) return
    initAudio()
    if (audioCtx.state === 'suspended') await audioCtx.resume()

    crossfading = true
    const dur = crossfade.value
    const now = audioCtx.currentTime

    idleAudio.src = `${API}/api/stream/${next.id}`
    idleAudio.playbackRate = playbackRate.value
    idleAudio.currentTime = 0

    const gOut = activeAudio === audioA ? gainA : gainB
    const gIn  = activeAudio === audioA ? gainB : gainA

    gOut.gain.cancelScheduledValues(now)
    gIn.gain.cancelScheduledValues(now)
    gOut.gain.setValueAtTime(gOut.gain.value, now)
    gIn.gain.setValueAtTime(0, now)
    gOut.gain.linearRampToValueAtTime(0, now + dur)
    gIn.gain.linearRampToValueAtTime(1, now + dur)

    await idleAudio.play().catch(() => {})

    const old = activeAudio
    activeAudio = idleAudio
    idleAudio = old

    setTimeout(() => {
      old.pause()
      old.currentTime = 0
      crossfading = false
    }, dur * 1000 + 100)

    current.value = next
    fetch(`${API}/api/history/${next.id}`, { method: 'POST' }).catch(() => {})
  }

  // ---- Next track: SINGLE source of truth (fixes Bug 1) ----
  // We use a lock so crossfade + ended-event can't double-fire
  let picking = false
  async function pickNext() {
    if (picking) return null
    picking = true
    try {
      if (queue.value.length) {
        const next = queue.value.shift()
        // Notify Jam that item #0 was consumed
        jam.removeFromQueue(0)
        return next
      }
      if (repeat.value === 'one') return current.value
      if (autoDj.value) {
        const res = await fetch(`${API}/api/tracks/random?exclude_id=${current.value?.id || 0}`)
        return res.ok ? await res.json() : null
      }
      return null
    } finally {
      picking = false
    }
  }

  async function playNext(force = false) {
    if (!force && repeat.value === 'one') {
      return play(current.value, { fade: false })
    }
    const next = await pickNext()
    if (!next) { isPlaying.value = false; return }
    if (crossfade.value > 0) await crossfadeTo(next)
    else await play(next)
  }

  // ---- Tick (progress + crossfade trigger) ----
  let crossfadeFiredFor = null   // track which track already triggered
  function tick() {
    if (!activeAudio.duration) return
    progress.value = activeAudio.currentTime
    duration.value = activeAudio.duration

    const remaining = activeAudio.duration - activeAudio.currentTime

    // Only fire crossfade ONCE per track
    if (
      !crossfading &&
      crossfade.value > 0 &&
      remaining <= crossfade.value + 0.1 &&
      crossfadeFiredFor !== current.value?.id
    ) {
      crossfadeFiredFor = current.value?.id
      playNext()
    }

    // Sleep timer fade
    if (sleepRemaining.value > 0 && sleepRemaining.value <= fadeOut.value) {
      const g = activeAudio === audioA ? gainA : gainB
      if (g) {
        const t = sleepRemaining.value / fadeOut.value
        g.gain.setValueAtTime(Math.max(0, t), audioCtx.currentTime)
      }
    }
  }

  ;[audioA, audioB].forEach(a => {
    a.addEventListener('timeupdate', () => {
      if (a === activeAudio) tick()
    })
    a.addEventListener('ended', () => {
      if (a === activeAudio && !crossfading) {
        crossfadeFiredFor = null
        playNext()
      }
    })
  })

  // ---- Controls ----
  function toggle() {
    if (!current.value) return
    if (isPlaying.value) { activeAudio.pause(); isPlaying.value = false }
    else { activeAudio.play(); isPlaying.value = true }
  }

  function seek(sec) { activeAudio.currentTime = sec }
  function setVolume(v) {
    volume.value = v
    if (masterGain) masterGain.gain.value = v
  }
  function setPlaybackRate(r) {
    playbackRate.value = r
    ;[audioA, audioB].forEach(a => a.playbackRate = r)
  }

  // ---- Queue ops: ALWAYS mirror to Jam (fixes Bugs 2 & 3) ----
  function enqueue(track) {
    // Insert position depends on shuffle
    let pos = queue.value.length
    if (shuffle.value && queue.value.length > 0) {
      pos = Math.floor(Math.random() * (queue.value.length + 1))
    }
    queue.value.splice(pos, 0, track)
    jam.addToQueue(track.id)
  }

  function dequeue(i) {
    if (i < 0 || i >= queue.value.length) return
    queue.value.splice(i, 1)
    jam.removeFromQueue(i)
  }

  function clearQueue() {
    const n = queue.value.length
    queue.value.length = 0
    for (let i = n - 1; i >= 0; i--) jam.removeFromQueue(i)
  }

  function toggleShuffle() {
    shuffle.value = !shuffle.value
    if (shuffle.value) {
      for (let i = queue.value.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[queue.value[i], queue.value[j]] = [queue.value[j], queue.value[i]]
      }
    }
  }

  function cycleRepeat() {
    repeat.value = repeat.value === 'off' ? 'all'
      : repeat.value === 'all' ? 'one' : 'off'
  }

  // ---- Sleep ----
  function startSleep(minutes) {
    sleepMinutes.value = minutes
    sleepRemaining.value = minutes * 60
    clearInterval(sleepInterval)
    if (minutes <= 0) { sleepRemaining.value = 0; return }
    sleepInterval = setInterval(() => {
      sleepRemaining.value -= 1
      if (sleepRemaining.value <= 0) {
        clearInterval(sleepInterval)
        activeAudio.pause()
        isPlaying.value = false
      }
    }, 1000)
  }
  function cancelSleep() {
    clearInterval(sleepInterval)
    sleepMinutes.value = 0
    sleepRemaining.value = 0
    const g = activeAudio === audioA ? gainA : gainB
    if (g && audioCtx) g.gain.setValueAtTime(1, audioCtx.currentTime)
  }

  // ---- Shuffle library ----
  async function shuffleLibrary(limit = 20) {
    const res = await fetch(`${API}/api/tracks/shuffle?limit=${limit}`)
    if (!res.ok) return
    const tracks = await res.json()

    // Clear existing & notify Jam
    clearQueue()

    // Push to local queue + Jam
    for (const t of tracks) {
      queue.value.push(t)
      jam.addToQueue(t.id)
    }

    if (tracks.length) play(tracks[0])
  }

  return {
    // state
    current, queue, isPlaying, progress, duration,
    volume, shuffle, repeat, crossfade, playbackRate, fadeIn, fadeOut, normalize,
    sleepMinutes, sleepRemaining, autoDj,

    // computed
    queueCount, hasNext,

    // actions
    play, toggle, seek, setVolume, setPlaybackRate,
    enqueue, dequeue, clearQueue, playNext, toggleShuffle, cycleRepeat,
    startSleep, cancelSleep, shuffleLibrary,
    setBass, setTreble,
  }
})