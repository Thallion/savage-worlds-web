<template>
  <v-card flat>
    <v-card-text>
      <v-alert type="info" density="compact" class="mb-2">
        Handicap-Punkte: {{ daten.gesamt_handicap_punkte ?? 0 }} / 4
        (Leicht = 1 Punkt, Schwer = 2 Punkte) —
        verfügbar zum Einlösen: <strong>{{ verbleibendePunkte }}</strong>
      </v-alert>

      <div class="mb-4 d-flex ga-2 flex-wrap">
        <v-btn
          size="small"
          color="primary"
          variant="tonal"
          prepend-icon="mdi-arrow-up-bold"
          :disabled="verbleibendePunkte < 2"
          @click="einloesen('attribut')"
        >
          2 Punkte → 1 Attributssteigerung
        </v-btn>
        <v-btn
          size="small"
          color="primary"
          variant="tonal"
          prepend-icon="mdi-school"
          :disabled="verbleibendePunkte < 1"
          @click="einloesen('fertigkeit')"
        >
          1 Punkt → 1 Fertigkeitspunkt
        </v-btn>
        <span class="text-caption align-self-center">
          Talente kosten direkt 2 Punkte im Talente-Tab
        </span>
      </div>

      <v-snackbar v-model="meldungSichtbar" :timeout="3000">{{ meldung }}</v-snackbar>

      <!-- Ausgewählte Handicaps -->
      <div v-if="selectedHandicaps.length" class="mb-4">
        <h3 class="text-subtitle-1 mb-2">Ausgewählt</h3>
        <v-chip
          v-for="name in selectedHandicaps"
          :key="name"
          closable
          color="accent"
          class="mr-2 mb-2"
          @click:close="entferneHandicap(name)"
        >
          {{ name }}
        </v-chip>
      </div>

      <v-text-field
        v-model="suche"
        label="Handicap suchen..."
        prepend-inner-icon="mdi-magnify"
        clearable
        density="compact"
        class="mb-2"
      />

      <v-list density="compact">
        <v-list-item
          v-for="(handicap, name) in gefilterteHandicaps"
          :key="name"
          :disabled="selectedHandicaps.includes(String(name))"
          @click="waehleHandicap(String(name))"
        >
          <template #prepend>
            <v-icon :color="selectedHandicaps.includes(String(name)) ? 'success' : ''">
              {{ selectedHandicaps.includes(String(name)) ? 'mdi-check-circle' : 'mdi-circle-outline' }}
            </v-icon>
          </template>
          <v-list-item-title>
            {{ handicap.name || name }}
            <v-chip size="x-small" class="ml-1" :color="handicap.stufe === 'schwer' ? 'error' : 'warning'">
              {{ handicap.stufe }}
            </v-chip>
          </v-list-item-title>
          <v-list-item-subtitle v-if="handicap.beschreibung" class="text-wrap">
            {{ handicap.beschreibung?.substring(0, 120) }}{{ handicap.beschreibung?.length > 120 ? '...' : '' }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()
const suche = ref('')

const daten = computed(() => store.aktuellerCharakter!.charakter_daten)
const selectedHandicaps = computed(() => daten.value.selected_handicaps || [])
const verbleibendePunkte = computed(() => daten.value.verbleibende_handicap_punkte ?? 0)

const meldung = ref('')
const meldungSichtbar = ref(false)

const handicaps = computed(() => einstellungenStore.aktuellesSetting?.handicaps ?? {})

const gefilterteHandicaps = computed(() => {
  if (!suche.value) return handicaps.value
  const s = suche.value.toLowerCase()
  const result: Record<string, any> = {}
  for (const [key, val] of Object.entries(handicaps.value)) {
    const h = val as any
    if (key.toLowerCase().includes(s) || h.name?.toLowerCase().includes(s)) {
      result[key] = val
    }
  }
  return result
})

async function waehleHandicap(name: string) {
  await store.spiellogikAktion('handicap/waehlen', name)
}

async function entferneHandicap(name: string) {
  const result = await store.spiellogikAktion('handicap/entfernen', name)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

async function einloesen(option: 'attribut' | 'fertigkeit') {
  const result = await store.spiellogikAktion('handicap-punkte/einloesen', option)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}
</script>
