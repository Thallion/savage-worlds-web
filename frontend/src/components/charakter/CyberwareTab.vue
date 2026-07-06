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
                <v-btn icon="mdi-plus" size="x-small" variant="text" @click="installieren(inst.name)" />
                <v-btn icon="mdi-minus" size="x-small" variant="text" @click="deinstallieren(inst.name)" />
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
            <th class="text-right">Kosten</th>
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
            <td class="text-right">{{ (item.kosten ?? 0).toLocaleString('de-DE') }}</td>
            <td class="text-right">{{ item.stress }}</td>
            <td class="text-right">
              <v-btn size="small" variant="tonal" color="primary" @click="installieren(item.name)">
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
import { computed, ref } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const suche = ref('')
const meldung = ref('')
const meldungSichtbar = ref(false)

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
  return Object.entries(daten.value.cyberware_installationen ?? {})
    .filter(([, anzahl]) => anzahl > 0)
    .map(([name, anzahl]) => ({
      name,
      anzahl,
      aktiv: !inaktiv.includes(name),
      stress: katalog.value[name]?.stress ?? 0,
      beschreibung: katalog.value[name]?.beschreibung ?? '',
    }))
    .sort((a, b) => a.name.localeCompare(b.name))
})

const katalogGefiltert = computed(() => {
  const s = (suche.value ?? '').toLowerCase()
  return Object.values(katalog.value)
    .filter((i: any) => i.aktiv !== false && (!s || i.name.toLowerCase().includes(s)))
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
})

async function ausfuehren(aktion: string, element?: string) {
  const result = await store.spiellogikAktion(aktion, element)
  if (result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

const installieren = (name: string) => ausfuehren('cyberware/installieren', name)
const deinstallieren = (name: string) => ausfuehren('cyberware/deinstallieren', name)
const aktivUmschalten = (name: string, aktiv: boolean) =>
  ausfuehren(aktiv ? 'cyberware/aktivieren' : 'cyberware/deaktivieren', name)
const nebenwirkungWuerfeln = () => ausfuehren('cyberware/nebenwirkung')
const nebenwirkungEntfernen = (index: number) => ausfuehren('cyberware/nebenwirkung-entfernen', String(index))
</script>
