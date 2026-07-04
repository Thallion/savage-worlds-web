<template>
  <v-card flat>
    <v-card-text>
      <v-alert type="info" density="compact" class="mb-4">
        Freie Talent-Slots: <strong>{{ verbleibendeTalente }}</strong> ·
        Handicap-Punkte: <strong>{{ verbleibendeHandicapPunkte }}</strong>
        — ein Talent kostet 1 Slot oder 2 Handicap-Punkte
      </v-alert>

      <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>

      <!-- "Trotzdem auswählen" bei nicht erfüllten Voraussetzungen / zu hohem Rang -->
      <v-dialog v-model="bestaetigungSichtbar" max-width="480">
        <v-card>
          <v-card-title>Prüfung nicht bestanden</v-card-title>
          <v-card-text>{{ bestaetigungMeldung }}</v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="bestaetigungSichtbar = false">Abbrechen</v-btn>
            <v-btn color="warning" variant="tonal" @click="trotzdemWaehlen">
              Trotzdem auswählen
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <!-- Ausgewählte Talente -->
      <div v-if="selectedTalente.length" class="mb-4">
        <h3 class="text-subtitle-1 mb-2">Ausgewählt</h3>
        <v-chip
          v-for="name in selectedTalente"
          :key="name"
          closable
          color="secondary"
          class="mr-2 mb-2"
          @click:close="entferneTalent(name)"
        >
          {{ name }}
        </v-chip>
      </div>

      <ElementEditor typ="talente" />

      <div class="d-flex ga-2 flex-wrap align-center mb-2">
        <v-text-field
          v-model="suche"
          label="Talent suchen..."
          prepend-inner-icon="mdi-magnify"
          clearable
          density="compact"
          hide-details
          style="min-width: 220px; max-width: 300px"
        />
        <v-select
          v-model="kategorieFilter"
          :items="kategorien"
          label="Kategorie"
          density="compact"
          hide-details
          style="max-width: 200px"
        />
        <v-select
          v-model="rangFilter"
          :items="['Alle', 'Anfänger', 'Fortgeschritten', 'Veteran', 'Heroisch', 'Legendär']"
          label="Rang-Filter"
          density="compact"
          hide-details
          style="max-width: 180px"
        />
        <v-select
          v-model="sortOption"
          :items="['Name', 'Rang', 'Kategorie']"
          label="Sortierung"
          density="compact"
          hide-details
          style="max-width: 150px"
        />
        <v-btn
          :icon="sortAbsteigend ? 'mdi-sort-descending' : 'mdi-sort-ascending'"
          size="small"
          variant="text"
          :title="sortAbsteigend ? 'Absteigend' : 'Aufsteigend'"
          @click="sortAbsteigend = !sortAbsteigend"
        />
        <v-switch
          v-model="nurGewaehlte"
          label="Nur gewählte"
          density="compact"
          hide-details
          color="primary"
        />
        <v-switch
          v-model="nurVerfuegbare"
          label="Nur verfügbare"
          density="compact"
          hide-details
          color="primary"
        />
      </div>

      <v-list density="compact">
        <v-list-item
          v-for="(talent, name) in gefilterteTalente"
          :key="name"
          :disabled="selectedTalente.includes(String(name))"
          @click="waehleTalent(String(name))"
        >
          <template #prepend>
            <v-icon :color="selectedTalente.includes(String(name)) ? 'success' : ''">
              {{ selectedTalente.includes(String(name)) ? 'mdi-check-circle' : 'mdi-circle-outline' }}
            </v-icon>
          </template>
          <v-list-item-title>
            {{ talent.name || name }}
            <v-chip size="x-small" class="ml-1">{{ RANG_NAMEN[talent.rang] ?? talent.rang }}</v-chip>
            <v-chip v-if="talent.kategorie" size="x-small" class="ml-1" variant="outlined">
              {{ talent.kategorie }}
            </v-chip>
          </v-list-item-title>
          <v-list-item-subtitle v-if="talent.voraussetzungen?.length" class="text-wrap">
            Voraussetzungen: {{ talent.voraussetzungen.join(', ') }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'
import { api } from '@/api/client'
import ElementEditor from '@/components/charakter/ElementEditor.vue'
import { mergeKatalog } from '@/utils/settingElemente'
import { RANG_ORDNUNG, sortiertesObjekt } from '@/utils/sortierung'

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()
const suche = ref('')
const rangFilter = ref('Alle')
const kategorieFilter = ref('Alle Kategorien')
const sortOption = ref('Name')
const sortAbsteigend = ref(false)
const nurGewaehlte = ref(false)
const nurVerfuegbare = ref(false)

const daten = computed(() => store.aktuellerCharakter!.charakter_daten)
const selectedTalente = computed(() => daten.value.selected_talente || [])
const verbleibendeTalente = computed(() => daten.value.verbleibende_talente ?? 0)
const verbleibendeHandicapPunkte = computed(() => daten.value.verbleibende_handicap_punkte ?? 0)

const meldung = ref('')
const meldungSichtbar = ref(false)

const bestaetigungSichtbar = ref(false)
const bestaetigungMeldung = ref('')
const bestaetigungTalent = ref('')

const talente = computed(() =>
  mergeKatalog(einstellungenStore.aktuellesSetting?.talente, daten.value, 'talente'),
)

const RANG_NAMEN: Record<string, string> = {
  A: 'Anfänger',
  F: 'Fortgeschritten',
  V: 'Veteran',
  H: 'Heroisch',
  L: 'Legendär',
}

const kategorien = computed(() => [
  'Alle Kategorien',
  ...[...new Set(
    Object.values(talente.value)
      .map((t: any) => t.kategorie as string)
      .filter(Boolean),
  )].sort(),
])

// "Nur verfügbare": Rang- und Voraussetzungs-Prüfung liegt im Backend
const verfuegbareTalente = ref<Set<string> | null>(null)
watch(
  [nurVerfuegbare, daten],
  async ([aktiv]) => {
    if (!aktiv) {
      verfuegbareTalente.value = null
      return
    }
    const result = await api.post<{ verfuegbar: string[] }>('/spiellogik/talente/verfuegbar', {
      charakter_daten: daten.value,
    })
    verfuegbareTalente.value = new Set(result.verfuegbar)
  },
  { immediate: false },
)

const gefilterteTalente = computed(() => {
  const result: Record<string, any> = {}
  for (const [key, val] of Object.entries(talente.value)) {
    const t = val as any
    if (suche.value) {
      const s = suche.value.toLowerCase()
      if (
        !key.toLowerCase().includes(s) &&
        !t.name?.toLowerCase().includes(s) &&
        !t.beschreibung?.toLowerCase().includes(s)
      )
        continue
    }
    if (rangFilter.value !== 'Alle' && (RANG_NAMEN[t.rang] ?? t.rang) !== rangFilter.value) continue
    if (kategorieFilter.value !== 'Alle Kategorien' && t.kategorie !== kategorieFilter.value)
      continue
    if (nurGewaehlte.value && !selectedTalente.value.includes(key)) continue
    if (
      nurVerfuegbare.value &&
      verfuegbareTalente.value &&
      !verfuegbareTalente.value.has(key) &&
      !selectedTalente.value.includes(key)
    )
      continue
    result[key] = val
  }
  const schluessel =
    sortOption.value === 'Rang'
      ? (_n: string, t: any) => RANG_ORDNUNG[t.rang] ?? 99
      : sortOption.value === 'Kategorie'
        ? (_n: string, t: any) => (t.kategorie ?? '').toLowerCase()
        : (n: string) => n.toLowerCase()
  return sortiertesObjekt(result, schluessel, sortAbsteigend.value)
})

async function waehleTalent(name: string) {
  const result = await store.spiellogikAktion('talent/waehlen', name)
  if (!result.success && result.bestaetigung_moeglich) {
    bestaetigungTalent.value = name
    bestaetigungMeldung.value = `${result.message}. Trotzdem auswählen?`
    bestaetigungSichtbar.value = true
  } else if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

async function trotzdemWaehlen() {
  bestaetigungSichtbar.value = false
  const result = await store.spiellogikAktion('talent/waehlen', bestaetigungTalent.value, true)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

async function entferneTalent(name: string) {
  const result = await store.spiellogikAktion('talent/entfernen', name)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}
</script>
