<template>
  <v-card flat>
    <v-card-text>
      <v-alert v-if="!hatArkanenHintergrund" type="warning" density="compact" class="mb-4">
        Kein arkaner Hintergrund — wähle zuerst ein AH-Talent im Talente-Tab.
      </v-alert>
      <v-alert v-else type="info" density="compact" class="mb-4">
        Mächte-Slots frei: <strong>{{ verbleibendeMaechte }}</strong> ·
        Machtpunkte: <strong>{{ machtpunkte }}</strong>
      </v-alert>

      <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>

      <!-- "Trotzdem auswählen" bei zu hohem Rang -->
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

      <!-- Ausgewählte Mächte -->
      <div v-if="selectedMaechte.length" class="mb-4">
        <h3 class="text-subtitle-1 mb-2">Ausgewählt</h3>
        <v-chip
          v-for="name in selectedMaechte"
          :key="name"
          closable
          color="secondary"
          class="mr-2 mb-2"
          @click:close="entferneMacht(name)"
        >
          {{ name }}
        </v-chip>
      </div>

      <ElementEditor ref="elementEditor" typ="maechte" />

      <div class="d-flex ga-2 flex-wrap align-center mb-2">
        <v-text-field
          v-model="suche"
          label="Macht suchen..."
          prepend-inner-icon="mdi-magnify"
          clearable
          density="compact"
          hide-details
          style="min-width: 220px; max-width: 300px"
        />
        <v-select
          v-model="sortOption"
          :items="['Name', 'Rang']"
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
      </div>

      <v-list density="compact">
        <v-list-item
          v-for="(macht, name) in gefilterteMaechte"
          :key="name"
          @click="!selectedMaechte.includes(String(name)) && waehleMacht(String(name))"
        >
          <template #prepend>
            <v-icon :color="selectedMaechte.includes(String(name)) ? 'success' : ''">
              {{ selectedMaechte.includes(String(name)) ? 'mdi-check-circle' : 'mdi-circle-outline' }}
            </v-icon>
          </template>
          <v-list-item-title>
            {{ macht.name || name }}
            <v-chip size="x-small" class="ml-1">{{ macht.machtpunkte }} MP</v-chip>
            <v-chip v-if="macht.reichweite" size="x-small" class="ml-1" variant="outlined">
              {{ macht.reichweite }}
            </v-chip>
          </v-list-item-title>
          <v-list-item-subtitle v-if="macht.beschreibung" class="text-wrap">
            {{ macht.beschreibung?.substring(0, 120) }}{{ macht.beschreibung?.length > 120 ? '...' : '' }}
          </v-list-item-subtitle>
          <template #append>
            <v-btn
              icon="mdi-information-outline"
              size="x-small"
              variant="text"
              title="Beschreibung"
              @click.stop="beschreibungDialog?.oeffne(macht, String(name))"
            />
            <v-btn
              icon="mdi-pencil"
              size="x-small"
              variant="text"
              title="Bearbeiten"
              @click.stop="elementEditor?.bearbeiteElement(String(name))"
            />
            <v-btn
              icon="mdi-delete-outline"
              size="x-small"
              variant="text"
              title="Löschen"
              @click.stop="elementEditor?.loescheElement(String(name))"
            />
          </template>
        </v-list-item>
      </v-list>

      <BeschreibungDialog ref="beschreibungDialog" />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'
import ElementEditor from '@/components/charakter/ElementEditor.vue'
import BeschreibungDialog from '@/components/charakter/BeschreibungDialog.vue'
import { mergeKatalog } from '@/utils/settingElemente'
import { RANG_ORDNUNG, sortiertesObjekt } from '@/utils/sortierung'

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()
const elementEditor = ref<InstanceType<typeof ElementEditor> | null>(null)
const beschreibungDialog = ref<InstanceType<typeof BeschreibungDialog> | null>(null)
const suche = ref('')
const sortOption = ref('Name')
const sortAbsteigend = ref(false)
const nurGewaehlte = ref(false)

const daten = computed(() => store.aktuellerCharakter!.charakter_daten)
const selectedMaechte = computed(() => daten.value.selected_maechte || [])

const machtpunkte = computed(() => store.abgeleiteteWerte?.machtpunkte ?? 0)
const verbleibendeMaechte = computed(() => store.abgeleiteteWerte?.verbleibende_maechte ?? 0)
const hatArkanenHintergrund = computed(
  () => machtpunkte.value > 0 || verbleibendeMaechte.value > 0 || selectedMaechte.value.length > 0,
)

const meldung = ref('')
const meldungSichtbar = ref(false)

const bestaetigungSichtbar = ref(false)
const bestaetigungMeldung = ref('')
const bestaetigungMacht = ref('')

const maechte = computed(() =>
  mergeKatalog(einstellungenStore.aktuellesSetting?.maechte, daten.value, 'maechte'),
)

const gefilterteMaechte = computed(() => {
  const s = suche.value?.toLowerCase() ?? ''
  const result: Record<string, any> = {}
  for (const [key, val] of Object.entries(maechte.value)) {
    const m = val as any
    if (
      s &&
      !key.toLowerCase().includes(s) &&
      !m.name?.toLowerCase().includes(s) &&
      !m.beschreibung?.toLowerCase().includes(s)
    )
      continue
    if (nurGewaehlte.value && !selectedMaechte.value.includes(key)) continue
    result[key] = val
  }
  const schluessel =
    sortOption.value === 'Rang'
      ? (_n: string, m: any) => RANG_ORDNUNG[m.rang] ?? 99
      : (n: string) => n.toLowerCase()
  return sortiertesObjekt(result, schluessel, sortAbsteigend.value)
})

async function waehleMacht(name: string) {
  const result = await store.spiellogikAktion('macht/waehlen', name)
  if (!result.success && result.bestaetigung_moeglich) {
    bestaetigungMacht.value = name
    bestaetigungMeldung.value = `${result.message}. Trotzdem auswählen?`
    bestaetigungSichtbar.value = true
  } else if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

async function trotzdemWaehlen() {
  bestaetigungSichtbar.value = false
  const result = await store.spiellogikAktion('macht/waehlen', bestaetigungMacht.value, true)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

async function entferneMacht(name: string) {
  const result = await store.spiellogikAktion('macht/entfernen', name)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}
</script>
