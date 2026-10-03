<template>
  <v-dialog v-model="sichtbar" max-width="640" scrollable>
    <v-card>
      <v-card-title class="text-wrap">Ausprägungen: {{ machtName }}</v-card-title>
      <v-card-subtitle class="text-wrap">
        Welche Zauber bzw. Liturgien beherrscht der Charakter? Jederzeit änderbar.
      </v-card-subtitle>
      <div class="d-flex ga-2 align-center px-4 pt-2">
        <v-text-field
          v-model="suche"
          label="Ausprägung suchen..."
          prepend-inner-icon="mdi-magnify"
          clearable
          density="compact"
          hide-details
        />
        <v-switch
          v-model="nurGewaehlte"
          label="Nur gewählte"
          density="compact"
          hide-details
          color="primary"
          class="flex-grow-0"
        />
      </div>
      <v-card-text style="max-height: 60vh">
        <v-list density="compact">
          <v-list-item
            v-for="a in gefiltert"
            :key="a.name"
            @click="umschalten(a.name)"
          >
            <template #prepend>
              <v-checkbox-btn :model-value="auswahl.has(a.name)" @click.stop="umschalten(a.name)" />
            </template>
            <v-list-item-title class="text-wrap">{{ a.name }}</v-list-item-title>
            <v-list-item-subtitle v-if="a.beschreibung" class="text-wrap" style="-webkit-line-clamp: unset">
              {{ a.beschreibung }}
            </v-list-item-subtitle>
          </v-list-item>
          <v-list-item v-if="!gefiltert.length" class="text-medium-emphasis">
            Keine Treffer.
          </v-list-item>
        </v-list>
      </v-card-text>
      <v-card-actions>
        <span class="text-caption text-medium-emphasis ml-2">
          {{ auswahl.size }} von {{ auspraegungen.length }} gewählt
        </span>
        <v-spacer />
        <v-btn variant="text" @click="sichtbar = false">Abbrechen</v-btn>
        <v-btn color="primary" variant="tonal" :loading="speichert" @click="uebernehmen">
          Übernehmen
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCharakterStore } from '@/stores/charakter'

interface Auspraegung {
  name: string
  beschreibung?: string
}

const emit = defineEmits<{ fehler: [meldung: string] }>()

const store = useCharakterStore()
const sichtbar = ref(false)
const machtName = ref('')
const auspraegungen = ref<Auspraegung[]>([])
const auswahl = ref(new Set<string>())
const suche = ref('')
const nurGewaehlte = ref(false)
const speichert = ref(false)

const gefiltert = computed(() => {
  const s = suche.value?.toLowerCase() ?? ''
  return auspraegungen.value.filter(
    (a) =>
      (!nurGewaehlte.value || auswahl.value.has(a.name)) &&
      (!s || a.name.toLowerCase().includes(s) || a.beschreibung?.toLowerCase().includes(s)),
  )
})

function umschalten(name: string) {
  const neu = new Set(auswahl.value)
  if (neu.has(name)) neu.delete(name)
  else neu.add(name)
  auswahl.value = neu
}

function oeffne(name: string, macht: Record<string, any>) {
  machtName.value = name
  auspraegungen.value = macht.auspraegungen ?? []
  const gewaehlt = store.aktuellerCharakter?.charakter_daten.macht_auspraegungen?.[name] ?? []
  auswahl.value = new Set(gewaehlt)
  suche.value = ''
  nurGewaehlte.value = false
  sichtbar.value = true
}

async function uebernehmen() {
  speichert.value = true
  try {
    const result = await store.spiellogikAktion('macht/auspraegungen', machtName.value, false, {
      auswahl: [...auswahl.value],
    })
    if (result.success) sichtbar.value = false
    else if (result.message) emit('fehler', result.message)
  } finally {
    speichert.value = false
  }
}

defineExpose({ oeffne })
</script>
