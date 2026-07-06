<template>
  <v-container>
    <v-row class="mb-2" align="center">
      <v-col>
        <h1 class="text-h4">Setting-Verwaltung</h1>
      </v-col>
      <v-col cols="auto" class="d-flex ga-2">
        <v-btn variant="tonal" prepend-icon="mdi-upload" @click="importDatei?.click()">
          Importieren
        </v-btn>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="erstellenOffen = true">
          Neues Setting
        </v-btn>
        <input
          ref="importDatei"
          type="file"
          accept="application/json,.json"
          class="d-none"
          @change="importiereDatei"
        />
      </v-col>
    </v-row>

    <!-- Konflikte/Warnungen der letzten Erstellung -->
    <v-alert
      v-if="hinweise.length"
      type="warning"
      density="compact"
      closable
      class="mb-4"
      @click:close="hinweise = []"
    >
      <div v-for="(hinweis, i) in hinweise" :key="i">{{ hinweis }}</div>
    </v-alert>
    <v-alert
      v-if="erfolg"
      type="success"
      density="compact"
      closable
      class="mb-4"
      @click:close="erfolg = ''"
    >
      {{ erfolg }}
    </v-alert>

    <v-table hover>
      <thead>
        <tr>
          <th>Name</th>
          <th class="d-none d-md-table-cell">Beschreibung</th>
          <th v-for="typ in STATISTIK_TYPEN" :key="typ" class="text-right d-none d-sm-table-cell">
            {{ TYP_LABELS[typ] }}
          </th>
          <th class="text-right">Aktionen</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="setting in store.verfuegbareSettings"
          :key="setting.name"
          class="cursor-pointer"
          @click="oeffneDetail(setting)"
        >
          <td>
            {{ setting.name }}
            <v-chip v-if="setting.custom" size="x-small" color="primary" class="ml-1">
              eigenes
            </v-chip>
          </td>
          <td class="d-none d-md-table-cell text-truncate" style="max-width: 300px">
            {{ setting.beschreibung }}
          </td>
          <td
            v-for="typ in STATISTIK_TYPEN"
            :key="typ"
            class="text-right d-none d-sm-table-cell"
          >
            {{ setting.statistik?.[typ] ?? 0 }}
          </td>
          <td class="text-right text-no-wrap">
            <v-btn
              icon="mdi-eye"
              size="small"
              variant="text"
              @click.stop="oeffneDetail(setting)"
            />
            <v-btn
              icon="mdi-download"
              size="small"
              variant="text"
              title="Als JSON exportieren"
              @click.stop="exportiereSetting(setting.name)"
            />
            <v-btn
              v-if="setting.custom"
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              @click.stop="loescheSetting(setting.name)"
            />
          </td>
        </tr>
      </tbody>
    </v-table>

    <SettingErstellenDialog v-model="erstellenOffen" @erstellt="nachErstellung" />
    <SettingDetailDialog
      v-model="detailOffen"
      :setting-name="detailName"
      :custom="detailCustom"
      @geaendert="detailName = $event"
    />

    <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  useEinstellungenStore,
  type SettingListItem,
  type SettingVerwaltungAntwort,
} from '@/stores/einstellungen'
import { useCharakterStore } from '@/stores/charakter'
import { ApiError } from '@/api/client'
import { TYP_LABELS, STATISTIK_TYPEN } from '@/utils/settingVerwaltung'
import SettingErstellenDialog from '@/components/settings/SettingErstellenDialog.vue'
import SettingDetailDialog from '@/components/settings/SettingDetailDialog.vue'

const store = useEinstellungenStore()
const charakterStore = useCharakterStore()

const erstellenOffen = ref(false)
const importDatei = ref<HTMLInputElement>()
const detailOffen = ref(false)
const detailName = ref('')
const detailCustom = ref(false)
const hinweise = ref<string[]>([])
const erfolg = ref('')
const meldung = ref('')
const meldungSichtbar = ref(false)

onMounted(async () => {
  // Charakterliste für den Modus „Aus Charakter" im Erstellen-Dialog
  await Promise.all([store.ladeSettings(), charakterStore.ladeListe()])
})

function oeffneDetail(setting: SettingListItem) {
  detailName.value = setting.name
  detailCustom.value = setting.custom
  detailOffen.value = true
}

function nachErstellung(antwort: SettingVerwaltungAntwort) {
  erfolg.value = `Setting '${antwort.name}' wurde angelegt`
  hinweise.value = [
    ...antwort.konflikte.map(
      (k) =>
        `Konflikt bei ${TYP_LABELS[k.typ] ?? k.typ} '${k.name}' ` +
        `(${k.quellen.join(' und ')}) — die spätere Quelle wurde übernommen`,
    ),
    ...antwort.warnungen,
  ]
}

async function loescheSetting(name: string) {
  if (!confirm(`Setting '${name}' wirklich löschen?`)) return
  try {
    await store.loescheSetting(name)
    erfolg.value = `Setting '${name}' wurde gelöscht`
  } catch (e: any) {
    meldung.value = e?.message || 'Löschen fehlgeschlagen'
    meldungSichtbar.value = true
  }
}

async function exportiereSetting(name: string) {
  try {
    await store.exportiereSetting(name)
  } catch (e: any) {
    meldung.value = e?.message || 'Export fehlgeschlagen'
    meldungSichtbar.value = true
  }
}

async function importiereDatei(event: Event) {
  const input = event.target as HTMLInputElement
  const datei = input.files?.[0]
  input.value = ''
  if (!datei) return

  // Führendes UTF-8-BOM (Windows-/Alt-Exporte) vor dem Parsen entfernen.
  let daten: unknown
  try {
    const text = (await datei.text()).replace(/^\uFEFF/, '')
    daten = JSON.parse(text)
  } catch {
    meldung.value = 'Import fehlgeschlagen — die Datei ist kein gültiges JSON.'
    meldungSichtbar.value = true
    return
  }

  try {
    const antwort = await store.importiereSetting(daten)
    erfolg.value = `Setting '${antwort.name}' wurde importiert`
  } catch (e) {
    const grund = e instanceof ApiError ? e.message : 'unbekannter Fehler'
    meldung.value = `Import fehlgeschlagen — ${grund}`
    meldungSichtbar.value = true
  }
}
</script>
