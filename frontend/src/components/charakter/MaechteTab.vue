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

      <v-text-field
        v-model="suche"
        label="Macht suchen..."
        prepend-inner-icon="mdi-magnify"
        clearable
        density="compact"
        class="mb-2"
      />

      <v-list density="compact">
        <v-list-item
          v-for="(macht, name) in gefilterteMaechte"
          :key="name"
          :disabled="selectedMaechte.includes(String(name))"
          @click="waehleMacht(String(name))"
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
const selectedMaechte = computed(() => daten.value.selected_maechte || [])

const machtpunkte = computed(() => store.abgeleiteteWerte?.machtpunkte ?? 0)
const verbleibendeMaechte = computed(() => store.abgeleiteteWerte?.verbleibende_maechte ?? 0)
const hatArkanenHintergrund = computed(
  () => machtpunkte.value > 0 || verbleibendeMaechte.value > 0 || selectedMaechte.value.length > 0,
)

const meldung = ref('')
const meldungSichtbar = ref(false)

const maechte = computed(() => einstellungenStore.aktuellesSetting?.maechte ?? {})

const gefilterteMaechte = computed(() => {
  if (!suche.value) return maechte.value
  const s = suche.value.toLowerCase()
  const result: Record<string, any> = {}
  for (const [key, val] of Object.entries(maechte.value)) {
    const m = val as any
    if (key.toLowerCase().includes(s) || m.name?.toLowerCase().includes(s)) {
      result[key] = val
    }
  }
  return result
})

async function waehleMacht(name: string) {
  const result = await store.spiellogikAktion('macht/waehlen', name)
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
