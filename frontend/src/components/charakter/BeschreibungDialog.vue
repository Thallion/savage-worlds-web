<template>
  <v-dialog v-model="sichtbar" max-width="560" scrollable>
    <v-card v-if="element">
      <v-card-title class="text-wrap">{{ titel }}</v-card-title>
      <v-card-text>
        <div v-if="chips.length" class="d-flex ga-1 flex-wrap mb-3">
          <v-chip v-for="chip in chips" :key="chip" size="small" label>{{ chip }}</v-chip>
        </div>
        <div v-if="element.voraussetzungen?.length" class="text-body-2 mb-3">
          <strong>Voraussetzungen:</strong> {{ element.voraussetzungen.join(', ') }}
        </div>
        <div v-if="element.beschreibung" class="text-body-2" style="white-space: pre-wrap">
          {{ element.beschreibung }}
        </div>
        <div v-else class="text-body-2 text-medium-emphasis">Keine Beschreibung vorhanden.</div>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="sichtbar = false">Schließen</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const RANG_NAMEN: Record<string, string> = {
  A: 'Anfänger',
  F: 'Fortgeschritten',
  V: 'Veteran',
  H: 'Heroisch',
  L: 'Legendär',
}

const sichtbar = ref(false)
const element = ref<Record<string, any> | null>(null)
const fallbackName = ref('')

const titel = computed(() => element.value?.name || fallbackName.value)

// Meta-Angaben als Chips, sofern am Element vorhanden
const chips = computed(() => {
  const el = element.value
  if (!el) return []
  const werte: string[] = []
  if (el.rang) werte.push(RANG_NAMEN[el.rang] ?? el.rang)
  if (el.kategorie) werte.push(el.kategorie)
  if (el.stufe) werte.push(el.stufe)
  if (el.machtpunkte != null) werte.push(`${el.machtpunkte} MP`)
  if (el.reichweite) werte.push(el.reichweite)
  return werte
})

function oeffne(el: Record<string, any>, name = '') {
  element.value = el
  fallbackName.value = name
  sichtbar.value = true
}

defineExpose({ oeffne })
</script>
