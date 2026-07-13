<template>
  <v-card flat>
    <v-card-text>
      <v-row>
        <!-- Abgeleitete Werte -->
        <v-col cols="12" md="4">
          <h3 class="text-h6 mb-3">Abgeleitete Werte</h3>
          <v-card variant="outlined" class="mb-2 pa-3">
            <div class="d-flex justify-space-between">
              <span>Parade</span>
              <strong>{{ abgeleiteteWerte.parade }}</strong>
            </div>
          </v-card>
          <v-card variant="outlined" class="mb-2 pa-3">
            <div class="d-flex justify-space-between">
              <span>Robustheit</span>
              <strong>{{ robustheitAnzeige }}</strong>
            </div>
          </v-card>
          <v-card variant="outlined" class="mb-2 pa-3">
            <div class="d-flex justify-space-between">
              <span>Bewegungsweite</span>
              <strong>{{ abgeleiteteWerte.bewegungsweite }}</strong>
            </div>
          </v-card>
          <v-card variant="outlined" class="mb-2 pa-3">
            <div class="d-flex justify-space-between">
              <span>Größe</span>
              <strong>{{ abgeleiteteWerte.groesse }}</strong>
            </div>
          </v-card>
          <v-card variant="outlined" class="mb-2 pa-3">
            <div class="d-flex justify-space-between">
              <span>Bennys</span>
              <strong>{{ abgeleiteteWerte.bennys }}</strong>
            </div>
          </v-card>
        </v-col>

        <!-- Profil-Zusammenfassung -->
        <v-col cols="12" md="4">
          <h3 class="text-h6 mb-3">Profil</h3>
          <v-table density="compact">
            <tbody>
              <tr v-for="(val, key) in daten.profil_daten" :key="key">
                <td class="font-weight-medium">{{ key }}</td>
                <td>{{ val }}</td>
              </tr>
              <tr>
                <td class="font-weight-medium">Setting</td>
                <td>{{ daten.active_setting_name }}</td>
              </tr>
              <tr>
                <td class="font-weight-medium">Abstammung</td>
                <td>{{ gewaehlteVoelker || '-' }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-col>

        <!-- Attribute Zusammenfassung -->
        <v-col cols="12" md="4">
          <h3 class="text-h6 mb-3">Attribute</h3>
          <v-table density="compact">
            <tbody>
              <tr v-for="(attr, name) in daten.attribute" :key="name">
                <td class="font-weight-medium">{{ name }}</td>
                <td>{{ formatWuerfel(attr.wert, attr.modifier) }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-col>
      </v-row>

      <v-row class="mt-4">
        <!-- Handicaps -->
        <v-col cols="12" md="4">
          <h3 class="text-h6 mb-3">Handicaps</h3>
          <v-chip
            v-for="h in daten.selected_handicaps"
            :key="h"
            class="mr-1 mb-1"
            color="accent"
          >
            {{ h }}
          </v-chip>
          <p v-if="!daten.selected_handicaps?.length" class="text-grey">Keine</p>
        </v-col>

        <!-- Talente -->
        <v-col cols="12" md="4">
          <h3 class="text-h6 mb-3">Talente</h3>
          <v-chip
            v-for="t in daten.selected_talente"
            :key="t"
            class="mr-1 mb-1"
            color="secondary"
          >
            {{ t }}
          </v-chip>
          <p v-if="!daten.selected_talente?.length" class="text-grey">Keine</p>
        </v-col>

        <!-- Fertigkeiten -->
        <v-col cols="12" md="4">
          <h3 class="text-h6 mb-3">Fertigkeiten</h3>
          <v-table density="compact">
            <tbody>
              <tr v-for="(fert, name) in aktiveFertigkeiten" :key="name">
                <td class="text-body-2">{{ name }}</td>
                <td>{{ formatWuerfel(fert.wuerfel?.value ?? 4, fert.wuerfel?.modifier ?? 0) }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-col>
      </v-row>

      <v-row class="mt-4">
        <!-- Mächte -->
        <v-col cols="12" md="4">
          <h3 class="text-h6 mb-3">Mächte</h3>
          <v-chip
            v-for="m in daten.selected_maechte"
            :key="m"
            class="mr-1 mb-1"
            color="primary"
          >
            {{ m }}
          </v-chip>
          <p v-if="!daten.selected_maechte?.length" class="text-grey">Keine</p>
          <p v-else-if="abgeleiteteWerte.machtpunkte" class="text-caption mt-1">
            {{ abgeleiteteWerte.machtpunkte }} Machtpunkte
          </p>
        </v-col>

        <!-- Ausrüstung -->
        <v-col cols="12" md="8">
          <h3 class="text-h6 mb-3">Ausrüstung</h3>
          <v-table v-if="besitz.length" density="compact">
            <tbody>
              <tr v-for="eintrag in besitz" :key="eintrag.name">
                <td>{{ eintrag.name }}</td>
                <td class="text-right">
                  <span v-if="eintrag.anzahl > 1">{{ eintrag.anzahl }}x</span>
                  <v-chip v-if="eintrag.angelegt" size="x-small" class="ml-2" color="success">
                    angelegt
                  </v-chip>
                </td>
              </tr>
            </tbody>
          </v-table>
          <p v-else class="text-grey">Keine</p>
        </v-col>
      </v-row>

      <!-- Statblock-Export -->
      <v-row class="mt-4">
        <v-col cols="12">
          <div class="d-flex align-center ga-2 mb-3">
            <h3 class="text-h6">Statblock</h3>
            <v-btn
              size="small"
              variant="tonal"
              prepend-icon="mdi-refresh"
              @click="ladeStatblock"
            >
              Erzeugen
            </v-btn>
            <v-btn
              v-if="statblockText"
              size="small"
              variant="tonal"
              prepend-icon="mdi-content-copy"
              @click="kopiereStatblock"
            >
              Kopieren
            </v-btn>
            <v-btn
              v-if="statblockText"
              size="small"
              variant="tonal"
              prepend-icon="mdi-download"
              @click="downloadStatblock"
            >
              Als .txt speichern
            </v-btn>
            <span v-if="statblockMeldung" class="text-caption">{{ statblockMeldung }}</span>
          </div>
          <v-card v-if="statblockText" variant="outlined" class="pa-4">
            <pre class="statblock-text">{{ statblockText }}</pre>
          </v-card>
        </v-col>
      </v-row>

      <!-- Charakterbogen (HTML, wie im Original) -->
      <v-row class="mt-4">
        <v-col cols="12">
          <div class="d-flex align-center flex-wrap ga-2 mb-3">
            <h3 class="text-h6">Charakterbogen</h3>
            <v-btn
              size="small"
              variant="tonal"
              prepend-icon="mdi-open-in-new"
              @click="oeffneCharakterbogen"
            >
              Im Browser öffnen
            </v-btn>
            <v-btn
              size="small"
              variant="tonal"
              prepend-icon="mdi-download"
              @click="downloadCharakterbogen"
            >
              Als .html speichern
            </v-btn>
            <v-checkbox
              v-model="druckerfreundlich"
              label="Druckerfreundliche Version (ohne Farben)"
              density="compact"
              hide-details
            />
            <span v-if="bogenMeldung" class="text-caption">{{ bogenMeldung }}</span>
          </div>
        </v-col>
      </v-row>

      <!-- Steigerungen (Journal-Sektion wie im Original-Charakterbogen) -->
      <v-row v-if="steigerungen.length" class="mt-4">
        <v-col cols="12">
          <h3 class="text-h6 mb-3">Steigerungen</h3>
          <v-table density="compact">
            <thead>
              <tr>
                <th>Rang</th>
                <th>Typ</th>
                <th>Name</th>
                <th>Kosten</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(zeile, i) in steigerungen" :key="i">
                <td>{{ zeile.rang }}</td>
                <td>{{ zeile.typ }}</td>
                <td>{{ zeile.name }}</td>
                <td>{{ zeile.kosten }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.statblock-text {
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 0.85rem;
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { api } from '@/api/client'

const store = useCharakterStore()

const statblockText = ref('')
const statblockMeldung = ref('')

async function ladeStatblock() {
  statblockMeldung.value = ''
  try {
    const result = await api.post<{ statblock: string }>('/spiellogik/statblock', {
      charakter_daten: daten.value,
    })
    statblockText.value = result.statblock
  } catch (e) {
    statblockMeldung.value =
      e instanceof Error ? `Fehler: ${e.message}` : 'Statblock konnte nicht erzeugt werden.'
  }
}

async function kopiereStatblock() {
  await navigator.clipboard.writeText(statblockText.value)
  statblockMeldung.value = 'In die Zwischenablage kopiert.'
}

const druckerfreundlich = ref(false)
const bogenMeldung = ref('')

async function ladeBogenHtml(): Promise<string> {
  const result = await api.post<{ html: string }>('/spiellogik/charakterbogen', {
    charakter_daten: daten.value,
    printer_friendly: druckerfreundlich.value,
  })
  return result.html
}

async function oeffneCharakterbogen() {
  bogenMeldung.value = ''
  // Fenster synchron öffnen, damit der Popup-Blocker den Klick noch zuordnet
  const fenster = window.open('', '_blank')
  try {
    const html = await ladeBogenHtml()
    if (fenster) {
      fenster.document.open()
      fenster.document.write(html)
      fenster.document.close()
    }
  } catch (e) {
    fenster?.close()
    bogenMeldung.value =
      e instanceof Error ? `Fehler: ${e.message}` : 'Charakterbogen konnte nicht erzeugt werden.'
  }
}

async function downloadCharakterbogen() {
  bogenMeldung.value = ''
  try {
    const html = await ladeBogenHtml()
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${daten.value.profil_daten?.Name || 'charakter'}.html`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    bogenMeldung.value =
      e instanceof Error ? `Fehler: ${e.message}` : 'Charakterbogen konnte nicht erzeugt werden.'
  }
}

function downloadStatblock() {
  const blob = new Blob([statblockText.value], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${daten.value.profil_daten?.Name || 'charakter'}-statblock.txt`
  a.click()
  URL.revokeObjectURL(url)
}

const daten = computed(() => store.aktuellerCharakter!.charakter_daten)

const abgeleiteteWerte = computed(
  () =>
    store.abgeleiteteWerte ?? {
      parade: 2,
      robustheit: 4,
      bewegungsweite: 6,
      groesse: 0,
      bennys: 3,
      panzerung: 0,
      machtpunkte: 0,
    },
)

// Robustheit inkl. Rüstungsschutz wie im Original: "9 (2)" — der Klammerwert
// ist der Torso-Panzerungsanteil, der bereits in der Robustheit steckt.
const robustheitAnzeige = computed(() => {
  const { robustheit, panzerung } = abgeleiteteWerte.value
  return panzerung ? `${robustheit} (${panzerung})` : `${robustheit}`
})

// Alt-Format aus der Kivy-App: {volk_name: bool} — nur truthy Einträge sind gewählt
const gewaehlteVoelker = computed(() =>
  Object.entries(daten.value.voelker_selected || {})
    .filter(([, v]) => v)
    .map(([name]) => name)
    .join(', '),
)

const besitz = computed(() =>
  Object.entries(daten.value.ausruestung_selected ?? {})
    .filter(([, e]: [string, any]) => (e.anzahl ?? 0) > 0)
    .map(([name, e]: [string, any]) => ({
      name,
      anzahl: e.anzahl ?? 1,
      angelegt: e.angelegt ?? false,
    }))
    .sort((a, b) => a.name.localeCompare(b.name)),
)

onMounted(() => {
  if (!store.abgeleiteteWerte) store.berechneWerte()
})

const aktiveFertigkeiten = computed(() => {
  const all = daten.value.fertigkeiten || {}
  const result: Record<string, any> = {}
  for (const [key, val] of Object.entries(all)) {
    const f = val as any
    // Eine Fertigkeit ist gelernt, wenn sie eine Grundfertigkeit ist, explizit
    // ausgewählt wurde oder über den ungelernten Grundzustand (W4-2) hinaus
    // gesteigert wurde. Letzteres deckt importierte Archetypen ab, bei denen
    // gesteigerte Fertigkeiten teils mit ausgewaehlt=false gespeichert sind.
    const wert = f.wuerfel?.value ?? 4
    const modifier = f.wuerfel?.modifier ?? -2
    const gelernt = wert > 4 || modifier > -2
    if (f.ausgewaehlt || f.grundfertigkeit || gelernt) {
      result[key] = val
    }
  }
  return result
})

function formatWuerfel(wert: number, modifier: number): string {
  if (modifier > 0) return `W${wert}+${modifier}`
  if (modifier < 0) return `W${wert}${modifier}`
  return `W${wert}`
}

// Steigerungs-Journal wie die Sektion "Steigerungen" im Original-Charakterbogen
// (utils/html_utils.py der Kivy-App): Historie-Einträge bevorzugt, sonst das
// Erschaffungs-Kauf-Journal aus Kivy-Importen/Archetypen mit dem aktuellen Rang.
const STEIGERUNGS_TYPEN: Record<string, string> = {
  attribut_steigerung: 'Attribut',
  fertigkeit_steigerung: 'Fertigkeit',
  talent_hinzugefuegt: 'Talent',
  talent_entfernt: 'Talent',
  handicap_hinzugefuegt: 'Handicap',
  handicap_entfernt: 'Handicap',
  handicap_reduziert: 'Handicap',
  macht_hinzugefuegt: 'Macht',
  macht_entfernt: 'Macht',
}

const COST_ENTRY_TYPEN: Record<string, string> = {
  attribut: 'Attribut',
  fertigkeit: 'Fertigkeit',
  talent: 'Talent',
  handicap: 'Handicap',
  macht: 'Macht',
}

function formatKosten(kosten: number | string | undefined, einheit: string | undefined): string {
  if (kosten === undefined || kosten === null || kosten === '') return ''
  return `${kosten} ${einheit ?? ''}`.trim()
}

interface SteigerungsZeile {
  rang: string
  typ: string
  name: string
  kosten: string
}

const steigerungen = computed<SteigerungsZeile[]>(() => {
  const journal = daten.value.steigerungs_journal
  if (!journal) return []

  if (journal.entries?.length) {
    return journal.entries
      .filter((e) => e.type in STEIGERUNGS_TYPEN)
      .map((e) => {
        const details = e.details ?? {}
        let name = details.name ?? ''
        if (e.type === 'attribut_steigerung' || e.type === 'fertigkeit_steigerung') {
          name = `${name}: W${details.von ?? ''} → W${details.nach ?? ''}`
        } else if (e.type.includes('entfernt')) {
          name = `${name} (entfernt)`
        } else if (e.type === 'handicap_reduziert') {
          name = `${name} (reduziert)`
        }
        return {
          rang: e.rang ?? '',
          typ: STEIGERUNGS_TYPEN[e.type],
          name,
          kosten: formatKosten(details.kosten ?? details.punkte, details.kosten_typ),
        }
      })
  }

  const rang = abgeleiteteWerteRang.value
  return (journal.cost_entries ?? []).map((e) => {
    let name = e.name ?? ''
    if (e.wert && (e.typ === 'attribut' || e.typ === 'fertigkeit')) {
      name = `${name}: W${e.wert}`
    }
    return {
      rang,
      typ: COST_ENTRY_TYPEN[e.typ ?? ''] ?? e.typ ?? '',
      name,
      kosten: formatKosten(e.kosten, e.zahlungsquelle),
    }
  })
})

const abgeleiteteWerteRang = computed(() => store.abgeleiteteWerte?.rang ?? '')
</script>
