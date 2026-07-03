<template>
  <v-card flat>
    <v-card-text>
      <v-alert v-if="selectedVolk" type="info" class="mb-4" density="compact" closable>
        Gewähltes Volk: <strong>{{ selectedVolk }}</strong>
      </v-alert>

      <!-- Wahlmöglichkeit des Volkes (z. B. Halbelf: Talent ODER Attribut) -->
      <v-card v-if="volkWahl" variant="tonal" color="primary" class="mb-4">
        <v-card-title class="text-body-1">Wahlmöglichkeit: {{ selectedVolk }}</v-card-title>
        <v-card-text>
          <div class="d-flex ga-2 flex-wrap align-center">
            <v-btn
              v-if="volkWahl.optionen.includes('talent')"
              size="small"
              :variant="aktuelleWahl?.typ === 'talent' ? 'elevated' : 'outlined'"
              prepend-icon="mdi-star"
              @click="waehleVolkWahl('talent')"
            >
              Freies Talent (+1 Slot)
            </v-btn>
            <v-btn
              v-if="volkWahl.optionen.includes('fertigkeitspunkte')"
              size="small"
              :variant="aktuelleWahl?.typ === 'fertigkeitspunkte' ? 'elevated' : 'outlined'"
              prepend-icon="mdi-school"
              @click="waehleVolkWahl('fertigkeitspunkte')"
            >
              +2 Fertigkeitspunkte
            </v-btn>
            <v-select
              v-if="volkWahl.optionen.includes('attribut')"
              :model-value="aktuelleWahl?.typ === 'attribut' ? aktuelleWahl.ziel : null"
              :items="wahlAttribute"
              label="Freies Attribut (+1 Würfeltyp)"
              density="compact"
              hide-details
              style="max-width: 280px"
              @update:model-value="(name: string) => waehleVolkWahl(name)"
            />
          </div>
          <div v-if="aktuelleWahl" class="text-caption mt-2">
            Aktuelle Wahl:
            <strong>{{ wahlBeschreibung }}</strong> — erneut wählen zum Wechseln.
          </div>
        </v-card-text>
      </v-card>

      <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>

      <v-text-field
        v-model="suche"
        label="Volk suchen..."
        prepend-inner-icon="mdi-magnify"
        clearable
        class="mb-4"
      />

      <v-row>
        <v-col
          v-for="(volk, name) in gefilterteVoelker"
          :key="name"
          cols="12"
          sm="6"
          md="4"
        >
          <v-card
            :color="selectedVolk === String(name) ? 'primary' : undefined"
            :variant="selectedVolk === String(name) ? 'elevated' : 'outlined'"
            hover
            @click="waehleVolk(String(name))"
          >
            <v-card-title class="text-body-1">{{ volk.name || name }}</v-card-title>
            <v-card-text>
              <div v-if="volk.besonderheiten?.length" class="text-caption">
                <strong>Besonderheiten:</strong>
                <ul class="ml-4">
                  <li v-for="b in volk.besonderheiten.slice(0, 3)" :key="b">{{ b }}</li>
                  <li v-if="volk.besonderheiten.length > 3">
                    ... und {{ volk.besonderheiten.length - 3 }} weitere
                  </li>
                </ul>
              </div>
              <div v-if="volk.handicaps?.length" class="text-caption mt-1">
                <strong>Handicaps:</strong> {{ volk.handicaps.join(', ') }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-alert v-if="Object.keys(gefilterteVoelker).length === 0" type="warning" class="mt-4">
        Keine Völker gefunden.
      </v-alert>
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
const selectedVolk = computed(() => {
  const keys = Object.keys(daten.value.voelker_selected || {})
  return keys.length > 0 ? keys[0] : null
})

const voelker = computed(() => einstellungenStore.aktuellesSetting?.voelker ?? {})

const meldung = ref('')
const meldungSichtbar = ref(false)

// Spiegelt verfuegbare_volk_wahl aus backend/app/services/volk_effekte.py
const volkWahl = computed<{ optionen: string[]; attribute: string[] | null } | null>(() => {
  if (!selectedVolk.value) return null
  const wm = (voelker.value as any)[selectedVolk.value]?.effects?.wahlmoeglichkeiten ?? {}
  if (wm.freies_talent_oder_attribut) return { optionen: ['talent', 'attribut'], attribute: null }
  if (wm.freies_talent_oder_fertigkeitspunkte)
    return { optionen: ['talent', 'fertigkeitspunkte'], attribute: null }
  if (wm.freies_attribut) return { optionen: ['attribut'], attribute: null }
  if (wm.attribut_staerke_oder_konstitution)
    return { optionen: ['attribut'], attribute: ['Stärke', 'Konstitution'] }
  return null
})

const wahlAttribute = computed(
  () => volkWahl.value?.attribute ?? Object.keys(daten.value.attribute ?? {}),
)

const aktuelleWahl = computed(() => daten.value.volk_effekte?.wahl ?? null)

const wahlBeschreibung = computed(() => {
  const w = aktuelleWahl.value
  if (!w) return ''
  if (w.typ === 'talent') return 'Freies Talent (+1 Slot)'
  if (w.typ === 'fertigkeitspunkte') return '+2 Fertigkeitspunkte'
  return `Attribut ${w.ziel} (+1 Würfeltyp)`
})

async function waehleVolkWahl(element: string) {
  const result = await store.spiellogikAktion('volk/wahl', element)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

const gefilterteVoelker = computed(() => {
  if (!suche.value) return voelker.value
  const s = suche.value.toLowerCase()
  const result: Record<string, any> = {}
  for (const [key, val] of Object.entries(voelker.value)) {
    if (key.toLowerCase().includes(s) || (val as any).name?.toLowerCase().includes(s)) {
      result[key] = val
    }
  }
  return result
})

async function waehleVolk(name: string) {
  await store.spiellogikAktion('volk/waehlen', name)
}
</script>
