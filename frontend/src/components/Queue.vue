<template>
  <div class="p-4 pb-32">
    <h2 class="text-lg font-bold mb-3">Up Next</h2>
    <ul class="space-y-1">
      <li v-for="(t, i) in player.queue" :key="i"
          class="flex justify-between px-3 py-2 rounded hover:bg-zinc-800">
        <span>{{ t.title }} — <span class="text-zinc-500">{{ t.artist }}</span></span>
        <button @click="player.dequeue(i)" class="text-red-400">Remove</button>
      </li>
      <li v-if="!player.queue.length" class="text-zinc-500 text-sm">Queue is empty.</li>
    </ul>
  </div>
</template>

<script setup>
import { usePlayer } from '../stores/player'
const player = usePlayer()
</script>