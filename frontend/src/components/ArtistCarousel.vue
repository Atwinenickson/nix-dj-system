<template>
  <section class="mx-4 my-6">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-xl font-bold">🎤 Top Musicians</h2>
      <div class="flex gap-2">
        <button @click="scroll(-1)" class="bg-zinc-800 hover:bg-zinc-700 rounded-full w-8 h-8">‹</button>
        <button @click="scroll(1)"  class="bg-zinc-800 hover:bg-zinc-700 rounded-full w-8 h-8">›</button>
      </div>
    </div>

    <div ref="track" class="flex gap-4 overflow-x-auto scroll-smooth pb-2 scrollbar-hide">
      <div
        v-for="a in artists" :key="a.artist"
        class="shrink-0 w-40 cursor-pointer group"
        @click="$emit('filter-artist', a.artist)"
      >
        <div class="relative w-40 h-40 rounded-full overflow-hidden ring-2 ring-transparent
                    group-hover:ring-green-500 transition-all shadow-lg">
          <img
            v-if="!broken[a.artist]"
            :src="`/api/art/${a.sample_track_id}`"
            :alt="a.artist"
            class="w-full h-full object-cover"
            @error="broken[a.artist] = true"
          />
          <div
            v-else
            class="w-full h-full flex items-center justify-center text-4xl font-black text-white"
            :style="{ background: gradientFor(a.artist) }"
          >
            {{ initials(a.artist) }}
          </div>
        </div>
        <div class="mt-2 text-center">
          <div class="font-semibold text-sm truncate">{{ a.artist }}</div>
          <div class="text-xs text-zinc-500">{{ a.track_count }} tracks</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'

defineEmits(['filter-artist'])
const track = ref(null)
const artists = ref([])
const broken = reactive({})

onMounted(async () => {
  try {
    const r = await fetch('/api/tracks/top-artists?limit=20')
    if (r.ok) artists.value = await r.json()
  } catch {}
})

function scroll(dir) {
  track.value?.scrollBy({ left: dir * 400, behavior: 'smooth' })
}

function initials(name) {
  return name.split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
}

function gradientFor(name) {
  let h = 0
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360
  return `linear-gradient(135deg, hsl(${h},60%,45%), hsl(${(h+60)%360},70%,35%))`
}
</script>

<style scoped>
.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
</style>