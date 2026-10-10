<template>
  <!-- Porträt bzw. Platzhalter mit Initialen in der Theme-Primärfarbe. avatar ist
       quadratisch und rund, gross/karte im Hochformat 3:4. -->
  <div
    class="portraet"
    :class="{ rund: variante === 'avatar' }"
    :style="{ width: `${breite}px`, height: `${hoehe}px` }"
  >
    <img
      v-if="url && !fehler"
      :src="url"
      :alt="`Porträt von ${name || 'Charakter'}`"
      loading="lazy"
      @error="fehler = true"
    />
    <div v-else class="platzhalter">
      <span :style="{ fontSize: `${Math.round(breite * 0.38)}px` }">{{ initialen(name) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { bildUrl, initialen, type BildVariante } from '@/utils/charakterBild'

const props = withDefaults(
  defineProps<{
    bildId?: string | null
    name?: string | null
    variante?: BildVariante
    breite?: number
  }>(),
  { bildId: null, name: '', variante: 'avatar', breite: 48 },
)

const url = computed(() => bildUrl(props.bildId, props.variante))
const hoehe = computed(() =>
  props.variante === 'avatar' ? props.breite : Math.round((props.breite * 4) / 3),
)

const fehler = ref(false)
watch(url, () => (fehler.value = false))
</script>

<style scoped>
.portraet {
  flex: none;
  overflow: hidden;
  border-radius: 6px;
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}
.portraet.rund {
  border-radius: 50%;
}
.portraet img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.platzhalter {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(var(--v-theme-primary), 0.18);
  color: rgb(var(--v-theme-primary));
  font-weight: 600;
  font-family: Georgia, 'Times New Roman', serif;
  letter-spacing: 0.05em;
  user-select: none;
}
</style>
