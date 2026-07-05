<template>
  <v-card flat>
    <v-card-text>
      <AbstammungEditor />

      <v-alert v-if="selectedVolk" type="info" class="mb-4" density="compact" closable>
        Gewählte Abstammung: <strong>{{ selectedVolk }}</strong>
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

      <!-- Spezial-Wahlen (heimlich, Spezialisierung, Magieaffin, ...) -->
      <v-card
        v-for="wahl in spezialWahlen"
        :key="wahl.id"
        variant="tonal"
        color="secondary"
        class="mb-4"
      >
        <v-card-title class="text-body-1">{{ wahl.titel }}</v-card-title>
        <v-card-text>
          <div v-if="wahl.beschreibung" class="text-caption mb-2">{{ wahl.beschreibung }}</div>

          <div v-if="wahl.typ === 'handicap_verzicht'" class="d-flex ga-2 flex-wrap">
            <v-btn
              size="small"
              :variant="!aktuelleSpezialWahl(wahl.id) ? 'elevated' : 'outlined'"
              @click="waehleSpezialWahl(wahl.id, wahl.handicap!)"
            >
              {{ wahl.handicap }} behalten
            </v-btn>
            <v-btn
              size="small"
              :variant="aktuelleSpezialWahl(wahl.id) ? 'elevated' : 'outlined'"
              @click="waehleSpezialWahl(wahl.id, 'Außenseiter')"
            >
              Außenseiter statt {{ wahl.handicap }}
            </v-btn>
          </div>

          <v-text-field
            v-else-if="wahl.typ === 'beschreibung' && wahl.optionen.length === 0"
            v-model="freitext[wahl.id]"
            :label="wahl.titel"
            density="compact"
            hide-details
            style="max-width: 320px"
            append-inner-icon="mdi-check"
            @click:append-inner="waehleSpezialWahl(wahl.id, freitext[wahl.id] ?? '')"
            @keyup.enter="waehleSpezialWahl(wahl.id, freitext[wahl.id] ?? '')"
          />

          <v-select
            v-else
            :model-value="spezialWahlWert(wahl)"
            :items="wahl.optionen"
            :label="wahl.titel"
            density="compact"
            hide-details
            style="max-width: 320px"
            @update:model-value="(v: string) => waehleSpezialWahl(wahl.id, v)"
          />

          <div v-if="spezialWahlWert(wahl)" class="text-caption mt-2">
            Aktuelle Wahl: <strong>{{ spezialWahlWert(wahl) }}</strong> — erneut wählen zum
            Wechseln.
          </div>
        </v-card-text>
      </v-card>

      <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>

      <v-text-field
        v-model="suche"
        label="Abstammung suchen..."
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
            <v-card-title class="text-body-1 d-flex align-center">
              {{ volk.name || name }}
              <v-chip v-if="volk.custom" size="x-small" class="ml-2" color="secondary">
                Eigene
              </v-chip>
            </v-card-title>
            <v-card-text>
              <div v-if="volk.beschreibung" class="text-caption mb-1">
                {{ volk.beschreibung }}
              </div>
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
        Keine Abstammungen gefunden.
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watchEffect } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'
import { mergeKatalog } from '@/utils/settingElemente'
import AbstammungEditor from './AbstammungEditor.vue'

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const suche = ref('')

const daten = computed(() => store.aktuellerCharakter!.charakter_daten)
const selectedVolk = computed(() => {
  const keys = Object.keys(daten.value.voelker_selected || {})
  return keys.length > 0 ? keys[0] : null
})

// Setting-Abstammungen plus eigene/ausgeblendete aus den Charakter-Overrides
const voelker = computed(() =>
  mergeKatalog(einstellungenStore.aktuellesSetting?.voelker, daten.value, 'voelker'),
)

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
  // Original "Vielseitig" (Mensch): freies Talent ODER +2 Fertigkeitspunkte
  if (wm.freies_talent || wm.freies_anfaenger_talent)
    return { optionen: ['talent', 'fertigkeitspunkte'], attribute: null }
  return null
})

const wahlAttribute = computed(
  () => volkWahl.value?.attribute ?? Object.keys(daten.value.attribute ?? {}),
)

const aktuelleWahl = computed(() => daten.value.volk_effekte?.wahl ?? null)

// --- Spezial-Wahlen: spiegelt verfuegbare_spezialwahlen aus
// backend/app/services/volk_wahlen.py (inkl. volk_wahl_config.json) ---

interface SpezialWahl {
  id: string
  typ: 'fertigkeit' | 'magieaffin' | 'attribut_malus' | 'handicap_verzicht' | 'beschreibung'
  titel: string
  beschreibung: string
  optionen: string[]
  handicap?: string
}

const PFLANZENERBEN = [
  'Blutrose',
  'Dornen',
  'Efeuranken',
  'Nesselgriff',
  'Parfüm',
  'Rindenhaut',
  'Sporen',
  'Weidenschatten',
]

const FERTIGKEIT_WAHLEN: Record<string, { filter: 'verstand' | 'wissen' | null; titel: string }> = {
  freie_verstandsfertigkeit: { filter: 'verstand', titel: 'Freie Verstand-Fertigkeit (W6)' },
  handwerks_wissen: { filter: 'wissen', titel: 'Handwerks-Wissen (W6)' },
  spezialisierung: { filter: null, titel: 'Spezialisierung (Fertigkeit W6)' },
}

function fertigkeitOptionen(filter: 'verstand' | 'wissen' | null): string[] {
  const ferts = daten.value.fertigkeiten ?? {}
  return Object.keys(ferts)
    .filter((n) =>
      filter === 'verstand'
        ? ferts[n].attribut === 'Verstand'
        : filter === 'wissen'
          ? n.startsWith('Wissen')
          : true,
    )
    .sort()
}

const spezialWahlen = computed<SpezialWahl[]>(() => {
  if (!selectedVolk.value) return []
  const effekte = (voelker.value as any)[selectedVolk.value]?.effects ?? {}
  const wm = effekte.wahlmoeglichkeiten ?? {}
  const se = effekte.spezielle_effekte ?? {}
  const wahlen: SpezialWahl[] = []

  if (wm.heimlich?.optionen?.length) {
    wahlen.push({
      id: 'heimlich',
      typ: 'fertigkeit',
      titel: 'Heimlich (Fertigkeit W6)',
      beschreibung: wm.heimlich.beschreibung ?? '',
      optionen: wm.heimlich.optionen,
    })
  }
  for (const [id, def] of Object.entries(FERTIGKEIT_WAHLEN)) {
    if (wm[id]) {
      wahlen.push({
        id,
        typ: 'fertigkeit',
        titel: def.titel,
        beschreibung: '',
        optionen: fertigkeitOptionen(def.filter),
      })
    }
  }
  if (wm.magieaffin || se.magieaffin) {
    const talente = einstellungenStore.aktuellesSetting?.talente ?? {}
    wahlen.push({
      id: 'magieaffin',
      typ: 'magieaffin',
      titel: 'Magieaffin: Arkaner Hintergrund',
      beschreibung: 'Das AH-Talent ist frei; seine Arkane Fertigkeit beginnt auf W4.',
      optionen: Object.keys(talente)
        .filter(
          (n) => n.startsWith('AH') && (talente[n]?.beschreibung ?? '').includes('Arkane Fertigkeit:'),
        )
        .sort(),
    })
  }
  if (wm.attribut_schwaeche || effekte.attribut_malus) {
    wahlen.push({
      id: 'attribut_schwaeche',
      typ: 'attribut_malus',
      titel: `Attribut-Schwäche (${effekte.attribut_malus_wert ?? -2})`,
      beschreibung: 'Ein Attribut nach Wahl erhält den Volks-Malus.',
      optionen: Object.keys(daten.value.attribute ?? {}),
    })
  }
  if (wm.outsider_statt_trennungsangst) {
    wahlen.push({
      id: 'outsider_statt_trennungsangst',
      typ: 'handicap_verzicht',
      titel: 'Außenseiter statt Trennungsangst',
      beschreibung: '',
      optionen: [],
      handicap: 'Trennungsangst',
    })
  }
  if (wm.pflanzenerbe_auswahl) {
    wahlen.push({
      id: 'pflanzenerbe_auswahl',
      typ: 'beschreibung',
      titel: 'Pflanzenerbe',
      beschreibung: '',
      optionen: PFLANZENERBEN,
    })
  }
  if (wm.tierart_auswahl) {
    wahlen.push({
      id: 'tierart_auswahl',
      typ: 'beschreibung',
      titel: 'Tierart',
      beschreibung: 'Freie Eingabe — mit Enter oder Häkchen bestätigen.',
      optionen: [],
    })
  }
  return wahlen
})

// Eingabepuffer für Freitext-Wahlen (z. B. Tierart), vorbelegt mit der
// gespeicherten Auswahl
const freitext = reactive<Record<string, string>>({})
watchEffect(() => {
  for (const wahl of spezialWahlen.value) {
    if (wahl.typ === 'beschreibung' && wahl.optionen.length === 0 && !(wahl.id in freitext)) {
      freitext[wahl.id] = aktuelleSpezialWahl(wahl.id)?.ziel ?? ''
    }
  }
})

function aktuelleSpezialWahl(id: string) {
  return daten.value.volk_effekte?.wahlen?.[id] ?? null
}

function spezialWahlWert(wahl: SpezialWahl): string | null {
  const w = aktuelleSpezialWahl(wahl.id)
  if (!w) return null
  return wahl.typ === 'magieaffin' ? (w.ah_talent ?? null) : (w.ziel ?? null)
}

async function waehleSpezialWahl(id: string, auswahl: string) {
  if (!auswahl) return
  const result = await store.spiellogikAktion('volk/wahl', `${id}:${auswahl}`)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

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
