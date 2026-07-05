<template>
  <div class="d-flex align-center ga-2 mb-2">
    <v-btn size="small" variant="tonal" prepend-icon="mdi-plus" @click="oeffneNeu">
      Abstammung hinzufügen
    </v-btn>
    <v-btn size="small" variant="tonal" prepend-icon="mdi-pencil" @click="oeffneBearbeiten">
      Bearbeiten
    </v-btn>
    <v-btn size="small" variant="tonal" prepend-icon="mdi-delete" @click="oeffneLoeschen">
      Löschen
    </v-btn>
  </div>

  <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>

  <!-- Hinzufügen / Bearbeiten -->
  <v-dialog v-model="formSichtbar" max-width="720">
    <v-card>
      <v-card-title>
        {{ bearbeiteterName ? 'Abstammung bearbeiten' : 'Neue Abstammung erstellen' }}
      </v-card-title>
      <v-card-text>
        <v-autocomplete
          v-if="modus === 'bearbeiten'"
          :model-value="bearbeiteterName"
          :items="eigeneNamen"
          label="Eigene Abstammung wählen"
          density="compact"
          class="mb-2"
          @update:model-value="ladeVolk"
        />

        <template v-if="modus === 'neu' || bearbeiteterName">
          <v-text-field v-model="formName" label="Name *" density="compact" class="mb-1" />
          <v-textarea
            v-model="formBeschreibung"
            label="Beschreibung"
            rows="2"
            auto-grow
            density="compact"
            class="mb-2"
          />

          <v-alert
            :type="punkteVerbleibend < 0 ? 'error' : 'info'"
            density="compact"
            variant="tonal"
            class="mb-3"
          >
            Volkseigenarten-Punkte: {{ punkteAusgegeben }} von {{ START_PUNKTE }} ausgegeben
            ({{ punkteVerbleibend }} verbleibend) — negative Eigenarten geben Punkte zurück.
          </v-alert>

          <!-- Gewählte Eigenarten -->
          <v-list v-if="gewaehlte.length" density="compact" class="mb-3 border rounded">
            <v-list-item v-for="(eintrag, index) in gewaehlte" :key="index">
              <v-list-item-title>{{ eintragLabel(eintrag) }}</v-list-item-title>
              <v-list-item-subtitle>
                {{ kostenText(eintragKosten(eintrag)) }} Punkt(e)
              </v-list-item-subtitle>
              <template #append>
                <v-btn
                  icon="mdi-delete"
                  size="x-small"
                  variant="text"
                  @click="entferneEigenart(index)"
                />
              </template>
            </v-list-item>
          </v-list>

          <!-- Eigenart hinzufügen -->
          <v-card variant="outlined" class="pa-3">
            <div class="text-subtitle-2 mb-2">Volkseigenart hinzufügen</div>
            <v-autocomplete
              v-model="neueId"
              :items="eigenartItems"
              label="Eigenart"
              density="compact"
              class="mb-1"
              @update:model-value="neueStufe = null; neueAuswahl = ''"
            />
            <template v-if="neueDef">
              <p class="text-caption mb-2">{{ neueDef.beschreibung }}</p>
              <v-select
                v-if="neueDef.stufen"
                v-model="neueStufe"
                :items="stufenItems(neueDef)"
                label="Stufe"
                density="compact"
                class="mb-1"
              />
              <template v-if="brauchtAuswahl">
                <v-text-field
                  v-if="auswahlTyp === 'text_eingabe' || auswahlTyp === 'fertigkeit_auswahl'"
                  v-model="neueAuswahl"
                  :label="neueDef.optionen?.beschreibung || 'Auswahl'"
                  :placeholder="neueDef.optionen?.platzhalter"
                  density="compact"
                  class="mb-1"
                />
                <v-autocomplete
                  v-else
                  v-model="neueAuswahl"
                  :items="auswahlOptionen"
                  :label="neueDef.optionen?.beschreibung || 'Auswahl'"
                  density="compact"
                  class="mb-1"
                />
              </template>
              <p v-if="maxErreicht" class="text-caption text-error mb-1">
                Diese Eigenart ist höchstens {{ neueDef.max_auswahl }}x wählbar.
              </p>
              <v-btn
                size="small"
                color="primary"
                variant="tonal"
                prepend-icon="mdi-plus"
                :disabled="!hinzufuegenMoeglich"
                @click="fuegeEigenartHinzu"
              >
                Hinzufügen ({{ kostenText(neueKosten) }} Punkt(e))
              </v-btn>
            </template>
          </v-card>
        </template>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="formSichtbar = false">Abbrechen</v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :disabled="(modus === 'bearbeiten' && !bearbeiteterName) || punkteVerbleibend < 0"
          @click="speichern"
        >
          Speichern
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Löschen -->
  <v-dialog v-model="loeschenSichtbar" max-width="480">
    <v-card>
      <v-card-title>Abstammung löschen</v-card-title>
      <v-card-text>
        <v-autocomplete
          v-model="loeschName"
          :items="alleNamen"
          label="Abstammung wählen"
          density="compact"
        />
        <p class="text-caption">
          Eigene Abstammungen werden entfernt, native Abstammungen des Settings nur für
          diesen Charakter ausgeblendet. Die aktuell gewählte Abstammung muss zuerst
          abgewählt werden.
        </p>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="loeschenSichtbar = false">Abbrechen</v-btn>
        <v-btn color="error" variant="tonal" :disabled="!loeschName" @click="loeschen">
          Löschen
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'
import { mergeKatalog } from '@/utils/settingElemente'

interface EigenartEintrag {
  id: string
  stufe?: number
  auswahl?: string
}

const START_PUNKTE = 2
const GRUNDFERTIGKEITEN = ['Allgemeinwissen', 'Athletik', 'Heimlichkeit', 'Überreden', 'Wahrnehmung']

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

onMounted(() => einstellungenStore.ladeVolkseigenarten())

const meldung = ref('')
const meldungSichtbar = ref(false)

const formSichtbar = ref(false)
const loeschenSichtbar = ref(false)
const modus = ref<'neu' | 'bearbeiten'>('neu')
const bearbeiteterName = ref('')
const formName = ref('')
const formBeschreibung = ref('')
const gewaehlte = ref<EigenartEintrag[]>([])
const loeschName = ref('')

const neueId = ref<string | null>(null)
const neueStufe = ref<number | null>(null)
const neueAuswahl = ref('')

const daten = computed(() => store.aktuellerCharakter?.charakter_daten as any)
const setting = computed(() => (einstellungenStore.aktuellesSetting as any) ?? {})

const katalog = computed(() =>
  mergeKatalog(setting.value.voelker, daten.value, 'voelker'),
)
const alleNamen = computed(() => Object.keys(katalog.value).sort())
const eigeneNamen = computed(() =>
  Object.keys(katalog.value)
    .filter((n) => katalog.value[n]?.custom && Array.isArray(katalog.value[n]?.eigenarten))
    .sort(),
)

// --- Volkseigenarten-Katalog (Spiegel von volk_erstellung.py) ---

const cfg = computed(() => (einstellungenStore.volkseigenarten as any) ?? null)
const istSuperkraefteSetting = computed(
  () => Boolean(setting.value.machtstufen) && Boolean(setting.value.krafte),
)

const defs = computed<Record<string, any>>(() => {
  const map: Record<string, any> = {}
  for (const e of cfg.value?.positive ?? []) map[e.id] = { ...e, negativ: false }
  for (const e of cfg.value?.negative ?? []) map[e.id] = { ...e, negativ: true }
  return map
})

function kostenSpanne(def: any): string {
  if (def.stufen) {
    const werte = def.stufen.map((s: any) => s.kosten ?? 0)
    const min = Math.min(...werte)
    const max = Math.max(...werte)
    return min === max ? kostenText(min) : `${kostenText(min)} bis ${kostenText(max)}`
  }
  return kostenText(def.kosten ?? 0)
}

function kostenText(k: number): string {
  return k > 0 ? `+${k}` : String(k)
}

const eigenartItems = computed(() => {
  const items: { title: string; value: string }[] = []
  for (const negativ of [false, true]) {
    const liste = (negativ ? cfg.value?.negative : cfg.value?.positive) ?? []
    for (const def of liste) {
      if (def.voraussetzung === 'setting_hat_superkraefte' && !istSuperkraefteSetting.value) continue
      items.push({ title: `${def.name} (${kostenSpanne(def)})`, value: def.id })
    }
  }
  return items
})

const neueDef = computed(() => (neueId.value ? defs.value[neueId.value] : null))

function stufenItems(def: any) {
  return def.stufen.map((s: any, i: number) => ({
    title: `${s.label} (${kostenText(s.kosten ?? 0)})`,
    value: i,
  }))
}

const neuerEffekt = computed(() => {
  const def = neueDef.value
  if (!def) return {}
  if (def.stufen) return neueStufe.value != null ? (def.stufen[neueStufe.value]?.effekt ?? {}) : {}
  return def.effekt ?? {}
})

// Wahlen, die erst pro Charakter nach der Volkauswahl fallen (freies Talent,
// freies Attribut, Magieaffin) — spiegeln _ist_verzoegert im Backend
const istVerzoegert = computed(() => {
  const def = neueDef.value
  if (!def) return false
  return (
    def.effekt_typ === 'wahlmoeglichkeit' ||
    Boolean(neuerEffekt.value?.attribut_wahl) ||
    Boolean(neuerEffekt.value?.magieaffin)
  )
})

const auswahlTyp = computed(() => neueDef.value?.optionen?.typ ?? null)
const brauchtAuswahl = computed(() => Boolean(auswahlTyp.value) && !istVerzoegert.value)

const auswahlOptionen = computed<string[]>(() => {
  const def = neueDef.value
  if (!def) return []
  const optionen = def.optionen ?? {}
  const fertigkeiten = Object.keys(daten.value?.fertigkeiten ?? {})
  switch (optionen.typ) {
    case 'attribut_auswahl':
      return optionen.attribute ?? cfg.value?.attribute ?? []
    case 'grundfertigkeit_auswahl':
      return optionen.fertigkeiten ?? GRUNDFERTIGKEITEN
    case 'nicht_grundfertigkeit_auswahl':
      return fertigkeiten.filter((f) => !GRUNDFERTIGKEITEN.includes(f)).sort()
    case 'talent_auswahl':
    case 'talent_rang_auswahl':
      // Volks-Talente: bis Helden-Rang (A/F/V/H)
      return Object.keys(setting.value.talente ?? {})
        .filter((n) => ['A', 'F', 'V', 'H'].includes(setting.value.talente[n]?.rang ?? 'A'))
        .sort()
    case 'handicap_auswahl':
      return Object.keys(setting.value.handicaps ?? {}).sort()
    case 'macht_auswahl':
      return Object.keys(setting.value.maechte ?? {}).sort()
    case 'superkraft_auswahl':
      return Object.keys(setting.value.krafte ?? {}).sort()
    default:
      return []
  }
})

const maxErreicht = computed(() => {
  const def = neueDef.value
  if (!def || !def.max_auswahl) return false
  return gewaehlte.value.filter((e) => e.id === def.id).length >= def.max_auswahl
})

const hinzufuegenMoeglich = computed(() => {
  const def = neueDef.value
  if (!def || maxErreicht.value) return false
  if (def.stufen && neueStufe.value == null) return false
  if (brauchtAuswahl.value && !neueAuswahl.value.trim()) return false
  return true
})

const neueKosten = computed(() => {
  const def = neueDef.value
  if (!def) return 0
  if (def.stufen) return neueStufe.value != null ? (def.stufen[neueStufe.value]?.kosten ?? 0) : 0
  return def.kosten ?? 0
})

// --- Punkte & Beschriftung der gewählten Eigenarten ---

function eintragKosten(eintrag: EigenartEintrag): number {
  const def = defs.value[eintrag.id]
  if (!def) return 0
  if (def.stufen) return def.stufen[eintrag.stufe ?? 0]?.kosten ?? 0
  return def.kosten ?? 0
}

function eintragLabel(eintrag: EigenartEintrag): string {
  const def = defs.value[eintrag.id]
  if (!def) return eintrag.id
  const details: string[] = []
  if (def.stufen && eintrag.stufe != null) details.push(def.stufen[eintrag.stufe]?.label ?? '')
  if (eintrag.auswahl) details.push(eintrag.auswahl)
  const detail = details.filter(Boolean).join(', ')
  return detail ? `${def.name} (${detail})` : def.name
}

const punkteAusgegeben = computed(() =>
  gewaehlte.value.reduce((summe, e) => summe + eintragKosten(e), 0),
)
const punkteVerbleibend = computed(() => START_PUNKTE - punkteAusgegeben.value)

// --- Aktionen ---

function fuegeEigenartHinzu() {
  const def = neueDef.value
  if (!def || !hinzufuegenMoeglich.value) return
  const eintrag: EigenartEintrag = { id: def.id }
  if (def.stufen) eintrag.stufe = neueStufe.value!
  if (brauchtAuswahl.value) eintrag.auswahl = neueAuswahl.value.trim()
  gewaehlte.value.push(eintrag)
  neueStufe.value = null
  neueAuswahl.value = ''
}

function entferneEigenart(index: number) {
  gewaehlte.value.splice(index, 1)
}

function oeffneNeu() {
  modus.value = 'neu'
  bearbeiteterName.value = ''
  formName.value = ''
  formBeschreibung.value = ''
  gewaehlte.value = []
  neueId.value = null
  neueStufe.value = null
  neueAuswahl.value = ''
  formSichtbar.value = true
}

function oeffneBearbeiten() {
  modus.value = 'bearbeiten'
  bearbeiteterName.value = ''
  formName.value = ''
  formSichtbar.value = true
}

function ladeVolk(name: string) {
  bearbeiteterName.value = name
  const volk = katalog.value[name] ?? {}
  formName.value = name
  formBeschreibung.value = volk.beschreibung ?? ''
  gewaehlte.value = (volk.eigenarten ?? []).map((e: EigenartEintrag) => ({ ...e }))
}

function oeffneLoeschen() {
  loeschName.value = ''
  loeschenSichtbar.value = true
}

async function speichern() {
  const result = await store.elementSpeichern(
    'voelker',
    formName.value,
    { beschreibung: formBeschreibung.value, eigenarten: gewaehlte.value },
    modus.value === 'bearbeiten' ? bearbeiteterName.value : undefined,
  )
  if (result.success) {
    formSichtbar.value = false
  } else {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

async function loeschen() {
  const result = await store.elementLoeschen('voelker', loeschName.value)
  if (result.success) {
    loeschenSichtbar.value = false
  } else {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}
</script>
