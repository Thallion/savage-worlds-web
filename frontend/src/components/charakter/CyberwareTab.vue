<template>
  <v-card flat>
    <v-card-text>
      <v-alert :type="cyber && cyber.ueber_limit > 0 ? 'warning' : 'info'" density="compact" class="mb-4">
        Stress: <strong>{{ cyber?.stress ?? 0 }}</strong> / Limit {{ cyber?.stresslimit ?? 0 }}
        (hartes Maximum {{ cyber?.stress_maximum ?? 0 }}) — Geld:
        <strong>{{ (werte?.vermoegen ?? 0).toLocaleString('de-DE') }}</strong>
        <template v-if="cyber && cyber.ueber_limit > 0">
          — Stresslimit um {{ cyber.ueber_limit }} überschritten!
        </template>
      </v-alert>

      <div v-if="cyber && cyber.ueber_limit > 0" class="mb-4">
        <v-btn size="small" color="warning" variant="tonal" prepend-icon="mdi-dice-d20" @click="nebenwirkungWuerfeln">
          Nebenwirkung auswürfeln (W20)
        </v-btn>
      </div>

      <v-snackbar v-model="meldungSichtbar" :timeout="6000">{{ meldung }}</v-snackbar>

      <!-- Wahl für konfigurierbare Implantate (Original: Konfigurations-Dialog) -->
      <v-dialog v-model="konfigSichtbar" max-width="420">
        <v-card>
          <v-card-title>{{ konfigItem }}</v-card-title>
          <v-card-text>
            <v-autocomplete
              v-model="konfigWahl"
              :items="konfigOptionen"
              :label="konfigLabel"
              density="compact"
              autofocus
            />
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="konfigSichtbar = false">Abbrechen</v-btn>
            <v-btn color="primary" variant="tonal" :disabled="!konfigWahl" @click="konfigBestaetigen">
              Installieren
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <!-- Erlittene Nebenwirkungen -->
      <div v-if="nebenwirkungen.length" class="mb-4">
        <h3 class="text-subtitle-1 mb-2">Nebenwirkungen</h3>
        <v-chip
          v-for="(nw, index) in nebenwirkungen"
          :key="index"
          closable
          color="warning"
          class="mr-2 mb-2"
          @click:close="nebenwirkungEntfernen(index)"
        >
          [{{ nw.wurf }}] {{ nw.name }}: {{ nw.effekt }}
        </v-chip>
      </div>

      <!-- Installationen -->
      <div v-if="installationen.length" class="mb-6">
        <h3 class="text-subtitle-1 mb-2">Installierte Cyberware</h3>
        <v-table density="compact">
          <thead>
            <tr>
              <th>Implantat</th>
              <th class="text-center">Aktiv</th>
              <th class="text-right">Anzahl</th>
              <th class="text-right">Stress</th>
              <th class="text-right">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="inst in installationen" :key="inst.name" :class="{ 'text-medium-emphasis': !inst.aktiv }">
              <td>
                {{ inst.name }}
                <v-chip
                  v-for="(wahl, i) in inst.konfigurationen"
                  :key="i"
                  size="x-small"
                  class="ml-1"
                  variant="outlined"
                >
                  {{ wahl }}
                </v-chip>
                <span v-if="!inst.aktiv" class="text-caption font-italic">(inaktiv)</span>
                <div class="text-caption text-medium-emphasis">{{ inst.beschreibung.slice(0, 100) }}</div>
              </td>
              <td class="text-center">
                <v-switch
                  :model-value="inst.aktiv"
                  color="primary"
                  density="compact"
                  hide-details
                  inset
                  class="d-inline-flex"
                  @update:model-value="aktivUmschalten(inst.name, $event as boolean)"
                />
              </td>
              <td class="text-right">{{ inst.anzahl }}</td>
              <td class="text-right">{{ inst.stress * inst.anzahl }}</td>
              <td class="text-right">
                <div class="d-flex ga-1 align-center justify-end flex-nowrap">
                  <v-text-field
                    :model-value="preisWert(besitzPreis, inst.name, inst.kosten)"
                    type="number"
                    min="0"
                    label="Preis"
                    density="compact"
                    hide-details
                    variant="outlined"
                    style="width: 100px"
                    @update:model-value="(v: string) => setPreis(besitzPreis, inst.name, v)"
                  />
                  <v-btn
                    icon="mdi-plus"
                    size="x-small"
                    variant="text"
                    title="Installieren"
                    @click="installieren(inst.name, preisWert(besitzPreis, inst.name, inst.kosten))"
                  />
                  <v-btn
                    icon="mdi-minus"
                    size="x-small"
                    variant="text"
                    title="Deinstallieren"
                    @click="deinstallieren(inst.name, preisWert(besitzPreis, inst.name, inst.kosten))"
                  />
                </div>
              </td>
            </tr>
          </tbody>
        </v-table>
        <div v-if="erschaffungAbgeschlossen" class="text-caption mt-1">
          Nach der Erschaffung gibt es keine Erstattung, und der Eingriff kostet 25 % des Kaufpreises.
        </div>
      </div>

      <!-- Katalog -->
      <v-text-field
        v-model="suche"
        label="Cyberware suchen..."
        prepend-inner-icon="mdi-magnify"
        clearable
        density="compact"
        hide-details
        class="mb-2"
        style="max-width: 320px"
      />
      <v-table density="compact">
        <thead>
          <tr>
            <th>Implantat</th>
            <th class="text-right">Preis</th>
            <th class="text-right">Stress</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in katalogGefiltert" :key="item.name">
            <td>
              <div>
                {{ item.name }}
                <span class="text-caption text-medium-emphasis">({{ item.unterkategorie }})</span>
              </div>
              <div class="text-caption text-medium-emphasis">{{ (item.beschreibung || '').slice(0, 110) }}</div>
            </td>
            <td class="text-right">
              <v-text-field
                :model-value="preisWert(katalogPreis, item.name, item.kosten ?? 0)"
                type="number"
                min="0"
                density="compact"
                hide-details
                variant="outlined"
                style="width: 110px"
                class="ml-auto"
                @update:model-value="(v: string) => setPreis(katalogPreis, item.name, v)"
              />
            </td>
            <td class="text-right">{{ item.stress }}</td>
            <td class="text-right">
              <v-btn
                size="small"
                variant="tonal"
                color="primary"
                @click="installieren(item.name, preisWert(katalogPreis, item.name, item.kosten ?? 0))"
              >
                Installieren
              </v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const suche = ref('')
const meldung = ref('')
const meldungSichtbar = ref(false)

// Pro Implantat einstellbarer Preis (wie im Original anpassbar).
// Leer = Katalogpreis.
const katalogPreis = reactive<Record<string, number>>({})
const besitzPreis = reactive<Record<string, number>>({})

const daten = computed(() => store.aktuellerCharakter!.charakter_daten)
const werte = computed(() => store.abgeleiteteWerte)
const cyber = computed(() => werte.value?.cyberware ?? null)
const erschaffungAbgeschlossen = computed(() => daten.value.char_gen_completed === true)
const nebenwirkungen = computed(() => daten.value.cyberware_nebenwirkungen ?? [])

const katalog = computed<Record<string, any>>(() => {
  const alle = einstellungenStore.aktuellesSetting?.ausruestung ?? {}
  const cyberware: Record<string, any> = {}
  for (const [name, item] of Object.entries(alle)) {
    if ((item as any).kategorie === 'Cyberware') cyberware[name] = item
  }
  return cyberware
})

const installationen = computed(() => {
  const inaktiv = daten.value.cyberware_inaktiv ?? []
  const effekte = daten.value.cyberware_effekte ?? {}
  return Object.entries(daten.value.cyberware_installationen ?? {})
    .filter(([, anzahl]) => anzahl > 0)
    .map(([name, anzahl]) => ({
      name,
      anzahl,
      aktiv: !inaktiv.includes(name),
      stress: katalog.value[name]?.stress ?? 0,
      kosten: katalog.value[name]?.kosten ?? 0,
      beschreibung: katalog.value[name]?.beschreibung ?? '',
      // getroffene Wahlen der Instanzen (z. B. "Stärke" bei Attributerhöhung)
      konfigurationen: (effekte[name] ?? [])
        .map((s) => Object.values(s.konfiguration ?? {}).join(', '))
        .filter(Boolean),
    }))
    .sort((a, b) => a.name.localeCompare(b.name))
})

const katalogGefiltert = computed(() => {
  const s = (suche.value ?? '').toLowerCase()
  return Object.values(katalog.value)
    .filter((i: any) => i.aktiv !== false && (!s || i.name.toLowerCase().includes(s)))
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
})

function preisWert(rec: Record<string, number>, name: string, standard: number): number {
  const p = Number(rec[name])
  return Number.isFinite(p) && p >= 0 ? p : (standard ?? 0)
}

function setPreis(rec: Record<string, number>, name: string, v: string | number): void {
  const n = Number(v)
  rec[name] = Number.isFinite(n) && n >= 0 ? n : 0
}

async function ausfuehren(aktion: string, element?: string, extra?: Record<string, unknown>) {
  const result = await store.spiellogikAktion(aktion, element, false, extra)
  if (result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

// Konfigurierbare Implantate brauchen eine Wahl vor der Installation
// (Original: get_cyberware_konfiguration)
const konfigSichtbar = ref(false)
const konfigItem = ref('')
const konfigPreis = ref<number | undefined>(undefined)
const konfigTyp = ref('')
const konfigLabel = ref('')
const konfigOptionen = ref<string[]>([])
const konfigWahl = ref('')

function benoetigteKonfiguration(item: any): { typ: string; label: string } | null {
  const effekte = item?.effekte ?? {}
  if (effekte.attribut_erhoehung) return { typ: 'attribut', label: 'Attribut wählen (+1 Würfeltyp)' }
  const fb = effekte.fertigkeit_bonus
  if (fb && fb.fertigkeit === 'waehlbar')
    return { typ: 'fertigkeit', label: `Fertigkeit wählen (+${fb.bonus ?? 1})` }
  if (effekte.fertigkeitschip)
    return { typ: 'fertigkeit', label: `Fertigkeit wählen (wird auf W${effekte.fertigkeit_wert ?? 6} gesetzt)` }
  if (effekte.kampftalent_gewaehrt) return { typ: 'talent', label: 'Kampftalent wählen' }
  return null
}

function konfigOptionenFuer(typ: string): string[] {
  if (typ === 'attribut') return Object.keys(daten.value.attribute ?? {})
  if (typ === 'fertigkeit') return Object.keys(daten.value.fertigkeiten ?? {}).sort()
  // Kampftalente des Settings, die noch nicht gewählt sind
  const talente = einstellungenStore.aktuellesSetting?.talente ?? {}
  const gewaehlt = daten.value.selected_talente ?? []
  return Object.entries(talente)
    .filter(([name, t]: [string, any]) => t.kategorie === 'Kampf' && !gewaehlt.includes(name))
    .map(([name]) => name)
    .sort()
}

function installieren(name: string, preis?: number) {
  const wahl = benoetigteKonfiguration(katalog.value[name])
  if (!wahl) {
    ausfuehren('cyberware/installieren', name, { preis })
    return
  }
  konfigItem.value = name
  konfigPreis.value = preis
  konfigTyp.value = wahl.typ
  konfigLabel.value = wahl.label
  konfigOptionen.value = konfigOptionenFuer(wahl.typ)
  konfigWahl.value = ''
  konfigSichtbar.value = true
}

function konfigBestaetigen() {
  konfigSichtbar.value = false
  ausfuehren('cyberware/installieren', konfigItem.value, {
    preis: konfigPreis.value,
    konfiguration: { [konfigTyp.value]: konfigWahl.value },
  })
}
const deinstallieren = (name: string, preis?: number) =>
  ausfuehren('cyberware/deinstallieren', name, { preis })
const aktivUmschalten = (name: string, aktiv: boolean) =>
  ausfuehren(aktiv ? 'cyberware/aktivieren' : 'cyberware/deaktivieren', name)
const nebenwirkungWuerfeln = () => ausfuehren('cyberware/nebenwirkung')
const nebenwirkungEntfernen = (index: number) => ausfuehren('cyberware/nebenwirkung-entfernen', String(index))
</script>
