<template>
  <v-card flat>
    <v-card-text>
      <v-alert type="info" density="compact" class="mb-4">
        Geld: <strong>{{ geldAnzeige(werte?.vermoegen) }}{{ waehrungSuffix }}</strong> von
        {{ geldAnzeige(werte?.startkapital_gesamt) }}{{ waehrungSuffix }}
        <v-btn
          icon="mdi-pencil"
          size="x-small"
          variant="text"
          title="Vermögen & Währung anpassen"
          @click="oeffneVermoegen"
        />
        — Traglast:
        <strong :class="ueberladen ? 'text-error' : ''">
          {{ gewichtAnzeige(werte?.gesamtgewicht) }} / {{ gewichtAnzeige(werte?.traglast) }} kg
        </strong>
        <span v-if="ueberladen"> (überladen!)</span>
        <span v-if="(werte?.panzerung ?? 0) > 0"> — Panzerung: +{{ werte?.panzerung }}</span>
      </v-alert>

      <!-- Vermögen & Währung anpassen (Original: Vermögens-Popup) -->
      <v-dialog v-model="vermoegenSichtbar" max-width="420">
        <v-card>
          <v-card-title>Vermögen & Währung</v-card-title>
          <v-card-text>
            <v-text-field
              v-model.number="vermoegenStartkapital"
              label="Startkapital"
              type="number"
              min="0"
            />
            <v-text-field v-model="vermoegenWaehrung" label="Währung" placeholder="z. B. Gold" />
            <v-text-field
              v-model.number="vermoegenBetrag"
              label="Geld erhalten (+) / verlieren (−)"
              type="number"
              placeholder="0"
            />
            <div class="text-caption text-medium-emphasis">
              Das Startkapital ersetzt das Setting-Startgeld; Talente wie Reich und eingelöste
              Handicap-Punkte rechnen weiter darauf auf. Leere Währung = Setting-Währung. Der
              Betrag wird einmalig auf das verfügbare Geld angerechnet (z. B. Belohnung oder
              Diebstahl).
            </div>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="vermoegenSichtbar = false">Abbrechen</v-btn>
            <v-btn
              color="primary"
              variant="tonal"
              :disabled="startkapitalWert === null"
              @click="bestaetigeVermoegen"
            >
              Übernehmen
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>

      <!-- Besitz -->
      <div v-if="besitz.length" class="mb-6">
        <h3 class="text-subtitle-1 mb-2">Besitz</h3>
        <v-table density="compact">
          <thead>
            <tr>
              <th>Gegenstand</th>
              <th class="text-right">Anzahl</th>
              <th class="text-right">Gewicht</th>
              <th>Angelegt</th>
              <th class="text-right">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="eintrag in besitz" :key="eintrag.name">
              <td>
                {{ eintrag.name }}
                <span class="text-caption text-medium-emphasis">({{ eintrag.kategorie }})</span>
              </td>
              <td class="text-right">{{ eintrag.anzahl }}</td>
              <td class="text-right">{{ gewichtAnzeige(eintrag.gewicht * eintrag.anzahl) }} kg</td>
              <td>
                <v-switch
                  v-if="eintrag.anlegbar"
                  :model-value="eintrag.angelegt"
                  density="compact"
                  hide-details
                  color="primary"
                  @update:model-value="(v: unknown) => anlegen(eintrag.name, Boolean(v))"
                />
              </td>
              <td>
                <div class="d-flex ga-1 align-center justify-end flex-nowrap">
                  <v-text-field
                    :model-value="mengeWert(besitzMenge, eintrag.name)"
                    type="number"
                    min="1"
                    label="Menge"
                    density="compact"
                    hide-details
                    variant="outlined"
                    style="width: 80px"
                    @update:model-value="(v: string) => setMenge(besitzMenge, eintrag.name, v)"
                  />
                  <v-text-field
                    :model-value="preisWert(besitzPreis, eintrag.name, eintrag.kosten)"
                    type="number"
                    min="0"
                    label="Preis"
                    density="compact"
                    hide-details
                    variant="outlined"
                    style="width: 90px"
                    @update:model-value="(v: string) => setPreis(besitzPreis, eintrag.name, v)"
                  />
                  <v-btn
                    icon="mdi-plus"
                    size="x-small"
                    variant="text"
                    title="Kaufen"
                    :disabled="
                      preisWert(besitzPreis, eintrag.name, eintrag.kosten) *
                        mengeWert(besitzMenge, eintrag.name) >
                      (werte?.vermoegen ?? 0)
                    "
                    @click="
                      kaufen(
                        eintrag.name,
                        mengeWert(besitzMenge, eintrag.name),
                        preisWert(besitzPreis, eintrag.name, eintrag.kosten),
                      )
                    "
                  />
                  <v-btn
                    icon="mdi-minus"
                    size="x-small"
                    variant="text"
                    title="Verkaufen"
                    @click="
                      verkaufen(
                        eintrag.name,
                        mengeWert(besitzMenge, eintrag.name),
                        preisWert(besitzPreis, eintrag.name, eintrag.kosten),
                      )
                    "
                  />
                </div>
              </td>
            </tr>
          </tbody>
        </v-table>
        <div v-if="erschaffungAbgeschlossen" class="text-caption mt-1">
          Nach der Erschaffung bringt Verkaufen nur noch 50 % des Kaufpreises.
        </div>
      </div>

      <!-- Katalog -->
      <ElementEditor typ="ausruestung" />
      <div class="d-flex ga-2 flex-wrap mb-2">
        <v-text-field
          v-model="suche"
          label="Ausrüstung suchen..."
          prepend-inner-icon="mdi-magnify"
          clearable
          density="compact"
          hide-details
          style="max-width: 320px"
        />
        <v-select
          v-model="kategorieFilter"
          :items="kategorien"
          label="Kategorie"
          clearable
          density="compact"
          hide-details
          style="max-width: 220px"
        />
        <v-select
          v-model="sortOption"
          :items="['Name', 'Gewicht', 'Kosten', 'Kategorie']"
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
      </div>

      <v-table density="compact">
        <thead>
          <tr>
            <th>Gegenstand</th>
            <th class="text-right">Preis</th>
            <th class="text-right">Gewicht</th>
            <th class="text-right">Menge</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in gefilterterKatalog" :key="item.name">
            <td>
              <div>
                {{ item.name }}
                <span class="text-caption text-medium-emphasis">({{ item.kategorie }})</span>
              </div>
              <div class="text-caption text-medium-emphasis">
                {{ (item.beschreibung || '').slice(0, 110) }}
              </div>
            </td>
            <td class="text-right">
              <v-text-field
                :model-value="preisWert(katalogPreis, item.name, item.kosten ?? 0)"
                type="number"
                min="0"
                density="compact"
                hide-details
                variant="outlined"
                style="width: 100px"
                class="ml-auto"
                @update:model-value="(v: string) => setPreis(katalogPreis, item.name, v)"
              />
            </td>
            <td class="text-right">{{ gewichtAnzeige(item.gewicht) }} kg</td>
            <td class="text-right">
              <v-text-field
                :model-value="mengeWert(katalogMenge, item.name)"
                type="number"
                min="1"
                density="compact"
                hide-details
                variant="outlined"
                style="width: 80px"
                class="ml-auto"
                @update:model-value="(v: string) => setMenge(katalogMenge, item.name, v)"
              />
            </td>
            <td class="text-right">
              <v-btn
                size="small"
                variant="tonal"
                color="primary"
                :disabled="
                  preisWert(katalogPreis, item.name, item.kosten ?? 0) *
                    mengeWert(katalogMenge, item.name) >
                  (werte?.vermoegen ?? 0)
                "
                @click="
                  kaufen(
                    item.name,
                    mengeWert(katalogMenge, item.name),
                    preisWert(katalogPreis, item.name, item.kosten ?? 0),
                  )
                "
              >
                Kaufen
              </v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>

      <v-alert v-if="gefilterterKatalog.length === 0" type="warning" class="mt-4">
        Keine Ausrüstung gefunden.
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'
import ElementEditor from '@/components/charakter/ElementEditor.vue'
import { mergeKatalog } from '@/utils/settingElemente'

const ANLEGBARE_KATEGORIEN = ['Rüstung', 'Schild']

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const suche = ref('')
const kategorieFilter = ref<string | null>(null)
const sortOption = ref('Name')
const sortAbsteigend = ref(false)
const meldung = ref('')
const meldungSichtbar = ref(false)

// Pro Gegenstand einstellbare Menge/Preis (wie im Original anpassbar).
// Leer = Standard (Menge 1 bzw. Katalogpreis).
const katalogMenge = reactive<Record<string, number>>({})
const katalogPreis = reactive<Record<string, number>>({})
const besitzMenge = reactive<Record<string, number>>({})
const besitzPreis = reactive<Record<string, number>>({})

const daten = computed(() => store.aktuellerCharakter!.charakter_daten)
const werte = computed(() => store.abgeleiteteWerte)
const waehrungSuffix = computed(() => (werte.value?.waehrung ? ` ${werte.value.waehrung}` : ''))

const vermoegenSichtbar = ref(false)
const vermoegenStartkapital = ref<number | string>(500)
const vermoegenWaehrung = ref('')
const vermoegenBetrag = ref<number | string>('')

const startkapitalWert = computed(() => {
  const n = Number(vermoegenStartkapital.value)
  return vermoegenStartkapital.value !== '' && Number.isFinite(n) && n >= 0 ? n : null
})

function oeffneVermoegen() {
  vermoegenStartkapital.value = werte.value?.startkapital_basis ?? 500
  vermoegenWaehrung.value = daten.value.waehrungseinheit ?? ''
  vermoegenBetrag.value = ''
  vermoegenSichtbar.value = true
}

async function bestaetigeVermoegen() {
  if (startkapitalWert.value === null) return
  const betrag = Number(vermoegenBetrag.value)
  const result = await store.spiellogikAktion('startkapital/setzen', undefined, false, {
    startkapital: startkapitalWert.value,
    waehrung: vermoegenWaehrung.value,
    betrag: vermoegenBetrag.value !== '' && Number.isFinite(betrag) ? betrag : 0,
  })
  if (result.success) {
    vermoegenSichtbar.value = false
  } else if (result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}
const erschaffungAbgeschlossen = computed(() => daten.value.char_gen_completed === true)
const ueberladen = computed(
  () => (werte.value?.gesamtgewicht ?? 0) > (werte.value?.traglast ?? Infinity),
)

const katalog = computed<Record<string, any>>(() =>
  mergeKatalog(einstellungenStore.aktuellesSetting?.ausruestung, daten.value, 'ausruestung'),
)

const kategorien = computed(() =>
  [...new Set(Object.values(katalog.value).map((i: any) => i.kategorie as string))].sort(),
)

const besitz = computed(() =>
  Object.entries(daten.value.ausruestung_selected ?? {})
    .filter(([, e]) => (e.anzahl ?? 0) > 0)
    .map(([name, e]) => {
      const item = katalog.value[name] ?? {}
      return {
        name,
        anzahl: e.anzahl,
        angelegt: e.angelegt ?? false,
        kategorie: item.kategorie ?? '?',
        gewicht: item.gewicht ?? 0,
        kosten: item.kosten ?? 0,
        anlegbar: ANLEGBARE_KATEGORIEN.includes(item.kategorie),
      }
    })
    .sort((a, b) => a.name.localeCompare(b.name)),
)

const gefilterterKatalog = computed(() => {
  const s = (suche.value ?? '').toLowerCase()
  const richtung = sortAbsteigend.value ? -1 : 1
  const vergleich: Record<string, (a: any, b: any) => number> = {
    Name: (a, b) => a.name.localeCompare(b.name),
    Gewicht: (a, b) => (a.gewicht ?? 0) - (b.gewicht ?? 0),
    Kosten: (a, b) => (a.kosten ?? 0) - (b.kosten ?? 0),
    Kategorie: (a, b) => (a.kategorie ?? '').localeCompare(b.kategorie ?? ''),
  }
  return Object.values(katalog.value)
    .filter(
      (i: any) =>
        i.aktiv !== false &&
        (!kategorieFilter.value || i.kategorie === kategorieFilter.value) &&
        (!s ||
          i.name.toLowerCase().includes(s) ||
          (i.beschreibung ?? '').toLowerCase().includes(s)),
    )
    .sort((a: any, b: any) => (vergleich[sortOption.value] ?? vergleich.Name)(a, b) * richtung)
})

function geldAnzeige(wert?: number | null): string {
  return (wert ?? 0).toLocaleString('de-DE', { maximumFractionDigits: 2 })
}

function gewichtAnzeige(wert?: number | null): string {
  return (wert ?? 0).toLocaleString('de-DE', { maximumFractionDigits: 1 })
}

function mengeWert(rec: Record<string, number>, name: string): number {
  const m = Math.floor(Number(rec[name]))
  return Number.isFinite(m) && m >= 1 ? m : 1
}

function setMenge(rec: Record<string, number>, name: string, v: string | number): void {
  const n = Math.floor(Number(v))
  rec[name] = Number.isFinite(n) && n >= 1 ? n : 1
}

function preisWert(rec: Record<string, number>, name: string, standard: number): number {
  const p = Number(rec[name])
  return Number.isFinite(p) && p >= 0 ? p : (standard ?? 0)
}

function setPreis(rec: Record<string, number>, name: string, v: string | number): void {
  const n = Number(v)
  rec[name] = Number.isFinite(n) && n >= 0 ? n : 0
}

async function ausfuehren(aktion: string, name: string, extra?: Record<string, unknown>) {
  const result = await store.spiellogikAktion(aktion, name, false, extra)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

const kaufen = (name: string, menge = 1, preis?: number) =>
  ausfuehren('ausruestung/kaufen', name, { menge, preis })
const verkaufen = (name: string, menge = 1, preis?: number) =>
  ausfuehren('ausruestung/verkaufen', name, { menge, preis })
const anlegen = (name: string, an: boolean) =>
  ausfuehren(an ? 'ausruestung/anlegen' : 'ausruestung/ablegen', name)
</script>
