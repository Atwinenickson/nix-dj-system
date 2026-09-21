<template>
  <div class="p-4 pb-32">
    <h2 class="text-lg font-bold mb-3">🕰️ Time Capsule</h2>
    <p class="text-sm text-zinc-400 mb-4">Tracks you loved but haven't played in a while.</p>
    <ul class="space-y-1">
      <li v-for="t in tracks" :key="t.id" class="flex justify-between px-3 py-2 rounded hover:bg-zinc-800">
        <div>
          <div>{{ t.title }}</div>
          <div class="text-xs text-zinc-500">{{ t.artist }} · {{ t.plays }} plays</div>
        </div>
        <button @click="player.play(t)" class="text-green-400">▶</button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePlayer } from '../stores/player'
const tracks = ref([])
const player = usePlayer()
onMounted(async () => {
  tracks.value = await (await fetch('http://127.0.0.1:8000/api/capsule')).json()
})
</script>