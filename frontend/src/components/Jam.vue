<template>
  <div class="p-4 border-l border-zinc-800 h-full">
    <h3 class="font-bold mb-2">🎧 Jam Room: <input v-model="roomId" class="bg-zinc-800 rounded px-2 py-1 w-32" /></h3>
    <button @click="connect" class="bg-green-500 text-black px-3 py-1 rounded text-sm">
      {{ connected ? 'Connected ✓' : 'Join' }}
    </button>

    <div v-if="state.track_id" class="mt-4 text-sm">
      <div class="text-zinc-400">Now playing:</div>
      <div class="font-semibold">Track #{{ state.track_id }}</div>
      <div>{{ state.playing ? '▶ playing' : '❚❚ paused' }} @ {{ state.position.toFixed(1) }}s</div>
    </div>

    <h4 class="mt-4 font-semibold">Queue ({{ state.queue?.length || 0 }})</h4>
    <ul class="text-sm space-y-1 mt-1">
      <li v-for="(t, i) in state.queue" :key="i" class="flex justify-between">
        <span>#{{ t }}</span>
        <button @click="send({ type: 'queue_remove', index: i, user: user })" class="text-red-400">×</button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
const roomId = ref('main')
const user = 'user-' + Math.random().toString(36).slice(2, 6)
const connected = ref(false)
const state = reactive({ track_id: null, position: 0, playing: false, queue: [] })
let ws

function connect() {
  ws = new WebSocket(`ws://127.0.0.1:8000/ws/jam/${roomId.value}`)
  ws.onopen = () => { connected.value = true; send({ type: 'sync', user }) }
  ws.onmessage = e => {
    const msg = JSON.parse(e.data)
    if (msg.type === 'state') Object.assign(state, msg)
  }
  ws.onclose = () => { connected.value = false }
}
function send(msg) { ws?.send(JSON.stringify(msg)) }
</script>