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
        <v-btn
          size="small"
          color="primary"
          variant="tonal"
          prepend-icon="mdi-cash-plus"
          :disabled="verbleibendePunkte < 1"
          @click="einloesen('startgeld')"
        >
          1 Punkt → Startkapital erneut
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

      <ElementEditor typ="handicaps" />

      <div class="d-flex ga-2 flex-wrap align-center mb-2">
        <v-text-field
          v-model="suche"
          label="Handicap suchen..."
          prepend-inner-icon="mdi-magnify"
          clearable
          density="compact"
          hide-details
          style="min-width: 220px; max-width: 300px"
        />
        <v-select
          v-model="stufenFilter"
          :items="['Alle Stufen', 'leicht', 'schwer']"
          label="Stufe"
          density="compact"
          hide-details
          style="max-width: 160px"
        />
        <v-btn
          :icon="sortAbsteigend ? 'mdi-sort-alphabetical-descending' : 'mdi-sort-alphabetical-ascending'"
          size="small"
          variant="text"
          :title="sortAbsteigend ? 'Name Z–A' : 'Name A–Z'"
          @click="sortAbsteigend = !sortAbsteigend"
        />
        <v-switch
          v-model="nurGewaehlte"
          label="Nur gewählte"
          density="compact"
          hide-details
          color="primary"
        />
      </div>

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
import ElementEditor from '@/components/charakter/ElementEditor.vue'
import { mergeKatalog } from '@/utils/settingElemente'
import { sortiertesObjekt } from '@/utils/sortierung'

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()
const suche = ref('')
const stufenFilter = ref('Alle Stufen')
const sortAbsteigend = ref(false)
const nurGewaehlte = ref(false)

const daten = computed(() => store.aktuellerCharakter!.charakter_daten)
const selectedHandicaps = computed(() => daten.value.selected_handicaps || [])
const verbleibendePunkte = computed(() => daten.value.verbleibende_handicap_punkte ?? 0)

const meldung = ref('')
const meldungSichtbar = ref(false)

const handicaps = computed(() =>
  mergeKatalog(einstellungenStore.aktuellesSetting?.handicaps, daten.value, 'handicaps'),
)

const gefilterteHandicaps = computed(() => {
  const s = suche.value?.toLowerCase() ?? ''
  const result: Record<string, any> = {}
  for (const [key, val] of Object.entries(handicaps.value)) {
    const h = val as any
    if (
      s &&
      !key.toLowerCase().includes(s) &&
      !h.name?.toLowerCase().includes(s) &&
      !h.beschreibung?.toLowerCase().includes(s)
    )
      continue
    if (stufenFilter.value !== 'Alle Stufen' && h.stufe !== stufenFilter.value) continue
    if (nurGewaehlte.value && !istGewaehlt(key)) continue
    result[key] = val
  }
  return sortiertesObjekt(result, (n) => n.toLowerCase(), sortAbsteigend.value)
})

// Auswahl kann mit Stufen-Suffix gespeichert sein (z. B. "Arm_leicht")
function istGewaehlt(name: string): boolean {
  const gewaehlt = selectedHandicaps.value
  return (
    gewaehlt.includes(name) ||
    gewaehlt.includes(`${name}_leicht`) ||
    gewaehlt.includes(`${name}_schwer`)
  )
}

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

async function einloesen(option: 'attribut' | 'fertigkeit' | 'startgeld') {
  const result = await store.spiellogikAktion('handicap-punkte/einloesen', option)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}
</script>
