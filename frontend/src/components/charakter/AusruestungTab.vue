<template>
  <v-card flat>
    <v-card-text>
      <v-alert type="info" density="compact" class="mb-4">
        Geld: <strong>{{ geldAnzeige(werte?.vermoegen) }}</strong> von
        {{ geldAnzeige(werte?.startkapital_gesamt) }} —
        Traglast:
        <strong :class="ueberladen ? 'text-error' : ''">
          {{ gewichtAnzeige(werte?.gesamtgewicht) }} / {{ gewichtAnzeige(werte?.traglast) }} kg
        </strong>
        <span v-if="ueberladen"> (überladen!)</span>
        <span v-if="(werte?.panzerung ?? 0) > 0"> — Panzerung: +{{ werte?.panzerung }}</span>
      </v-alert>

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
              <td class="text-right">
                <v-btn
                  icon="mdi-plus"
                  size="x-small"
                  variant="text"
                  :disabled="eintrag.kosten > (werte?.vermoegen ?? 0)"
                  @click="kaufen(eintrag.name)"
                />
                <v-btn
                  icon="mdi-minus"
                  size="x-small"
                  variant="text"
                  @click="verkaufen(eintrag.name)"
                />
              </td>
            </tr>
          </tbody>
        </v-table>
        <div v-if="erschaffungAbgeschlossen" class="text-caption mt-1">
          Nach der Erschaffung bringt Verkaufen nur noch 50 % des Kaufpreises.
        </div>
      </div>

      <!-- Katalog -->
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
      </div>

      <v-table density="compact">
        <thead>
          <tr>
            <th>Gegenstand</th>
            <th class="text-right">Kosten</th>
            <th class="text-right">Gewicht</th>
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
            <td class="text-right">{{ geldAnzeige(item.kosten) }}</td>
            <td class="text-right">{{ gewichtAnzeige(item.gewicht) }} kg</td>
            <td class="text-right">
              <v-btn
                size="small"
                variant="tonal"
                color="primary"
                :disabled="(item.kosten ?? 0) > (werte?.vermoegen ?? 0)"
                @click="kaufen(item.name)"
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
import { computed, ref } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'

const ANLEGBARE_KATEGORIEN = ['Rüstung', 'Schild']

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const suche = ref('')
const kategorieFilter = ref<string | null>(null)
const meldung = ref('')
const meldungSichtbar = ref(false)

const daten = computed(() => store.aktuellerCharakter!.charakter_daten)
const werte = computed(() => store.abgeleiteteWerte)
const erschaffungAbgeschlossen = computed(() => daten.value.char_gen_completed === true)
const ueberladen = computed(
  () => (werte.value?.gesamtgewicht ?? 0) > (werte.value?.traglast ?? Infinity),
)

const katalog = computed<Record<string, any>>(
  () => einstellungenStore.aktuellesSetting?.ausruestung ?? {},
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
  return Object.values(katalog.value)
    .filter(
      (i: any) =>
        i.aktiv !== false &&
        (!kategorieFilter.value || i.kategorie === kategorieFilter.value) &&
        (!s || i.name.toLowerCase().includes(s)),
    )
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
})

function geldAnzeige(wert?: number | null): string {
  return (wert ?? 0).toLocaleString('de-DE', { maximumFractionDigits: 2 })
}

function gewichtAnzeige(wert?: number | null): string {
  return (wert ?? 0).toLocaleString('de-DE', { maximumFractionDigits: 1 })
}

async function ausfuehren(aktion: string, name: string) {
  const result = await store.spiellogikAktion(aktion, name)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

const kaufen = (name: string) => ausfuehren('ausruestung/kaufen', name)
const verkaufen = (name: string) => ausfuehren('ausruestung/verkaufen', name)
const anlegen = (name: string, an: boolean) =>
  ausfuehren(an ? 'ausruestung/anlegen' : 'ausruestung/ablegen', name)
</script>
