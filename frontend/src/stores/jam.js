import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'

export const useJam = defineStore('jam', () => {
  const roomId = ref('main')
  const connected = ref(false)
  const user = 'user-' + Math.random().toString(36).slice(2, 6)

  const state = reactive({
    track_id: null,
    position: 0,
    playing: false,
    queue: [],
    from: null,
  })

  let ws = null
  let reconnectTimer = null

  function connect(id = roomId.value) {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
    roomId.value = id

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    ws = new WebSocket(`${proto}//${location.host}/ws/jam/${id}`)

    ws.onopen = () => {
      connected.value = true
      send({ type: 'sync', user })
    }
    ws.onmessage = e => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'state') {
          Object.assign(state, {
            track_id: msg.track_id,
            position: msg.position,
            playing: msg.playing,
            queue: msg.queue || [],
            from: msg.from,
          })
        }
      } catch {}
    }
    ws.onclose = () => {
      connected.value = false
      // auto-reconnect after 2s
      clearTimeout(reconnectTimer)
      reconnectTimer = setTimeout(() => connect(roomId.value), 2000)
    }
    ws.onerror = () => { connected.value = false }
  }

  function disconnect() {
    clearTimeout(reconnectTimer)
    ws?.close()
    ws = null
    connected.value = false
  }

  function send(msg) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ ...msg, user }))
    }
  }

  // ---- Convenience actions ----
  function addToQueue(trackId) {
    send({ type: 'queue_add', track_id: trackId })
  }
  function removeFromQueue(index) {
    send({ type: 'queue_remove', index })
  }
  function play(trackId) {
    send({ type: 'load', track_id: trackId })
  }
  function pause() { send({ type: 'pause' }) }
  function resume() { send({ type: 'play' }) }
  function seek(position) { send({ type: 'seek', position }) }

  return {
    roomId, connected, user, state,
    connect, disconnect, send,
    addToQueue, removeFromQueue, play, pause, resume, seek,
  }
})