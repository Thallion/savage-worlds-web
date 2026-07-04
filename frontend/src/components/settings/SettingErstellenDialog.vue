<template>
  <v-dialog :model-value="modelValue" max-width="700" @update:model-value="schliessen">
    <v-card>
      <v-card-title>Neues Setting</v-card-title>
      <v-card-text>
        <v-text-field v-model="name" label="Name" autofocus />
        <v-text-field v-model="beschreibung" label="Beschreibung (optional)" />

        <v-select
          v-model="modus"
          :items="MODI"
          item-title="label"
          item-value="wert"
          label="Erstellen aus"
        />
        <p class="text-caption text-grey mb-4">{{ modusBeschreibung }}</p>

        <v-select
          v-if="modus === 'kopie'"
          v-model="kopieQuelle"
          :items="settingNamen"
          label="Vorlage"
        />

        <v-autocomplete
          v-if="modus === 'zusammenfuehrung'"
          v-model="mergeQuellen"
          :items="settingNamen"
          label="Settings (Reihenfolge: bei Konflikten gewinnt das spätere)"
          multiple
          chips
          closable-chips
        />

        <v-select
          v-if="modus === 'aus_charakter'"
          v-model="charakterId"
          :items="charakterStore.liste"
          item-title="char_name"
          item-value="id"
          label="Charakter"
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps" :subtitle="item.raw.active_setting_name" />
          </template>
        </v-select>

        <template v-if="modus === 'elementauswahl'">
          <v-select
            v-model="basis"
            :items="settingNamen"
            label="Basis-Setting (liefert Attribute, Settingregeln und Startgeld)"
            class="mb-2"
          />
          <ElementAuswahl v-model="elemente" />
        </template>

        <v-alert v-if="fehler" type="error" density="compact" class="mt-2">
          {{ fehler }}
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="schliessen">Abbrechen</v-btn>
        <v-btn color="primary" :loading="ladend" :disabled="!gueltig" @click="erstellen">
          Erstellen
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  useEinstellungenStore,
  type SettingErstellenPayload,
  type SettingVerwaltungAntwort,
} from '@/stores/einstellungen'
import { useCharakterStore } from '@/stores/charakter'
import ElementAuswahl from './ElementAuswahl.vue'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', wert: boolean): void
  (e: 'erstellt', antwort: SettingVerwaltungAntwort): void
}>()

const store = useEinstellungenStore()
const charakterStore = useCharakterStore()

const MODI = [
  { wert: 'leer', label: 'Leerem Setting' },
  { wert: 'kopie', label: 'Kopie eines Settings' },
  { wert: 'zusammenfuehrung', label: 'Zusammenführung mehrerer Settings' },
  { wert: 'aus_charakter', label: 'Einem Charakter' },
  { wert: 'elementauswahl', label: 'Einzeln gewählten Elementen' },
] as const

const BESCHREIBUNGEN: Record<string, string> = {
  leer: 'Startet ohne Elemente — Völker, Talente usw. später über „Elemente hinzufügen" ergänzen.',
  kopie: 'Übernimmt ein Setting komplett als bearbeitbare Kopie.',
  zusammenfuehrung:
    'Mischt die Elemente aller gewählten Settings; gleichnamige Elemente mit abweichenden Daten werden als Konflikt gemeldet.',
  aus_charakter:
    'Schnappschuss des aktiven Settings eines Charakters inklusive seiner eigenen, bearbeiteten und gelöschten Elemente.',
  elementauswahl:
    'Stellt das Setting aus einzeln gewählten Elementen beliebiger Settings zusammen; ohne gewählte Fertigkeiten kommen die der Basis.',
}

const name = ref('')
const beschreibung = ref('')
const modus = ref<SettingErstellenPayload['modus']>('kopie')
const kopieQuelle = ref('SWAE')
const mergeQuellen = ref<string[]>([])
const charakterId = ref<number | null>(null)
const basis = ref('SWAE')
const elemente = ref<Record<string, Record<string, string[]>>>({})
const fehler = ref('')
const ladend = ref(false)

const settingNamen = computed(() => store.verfuegbareSettings.map((s) => s.name))
const modusBeschreibung = computed(() => BESCHREIBUNGEN[modus.value])

const gueltig = computed(() => {
  if (!name.value.trim()) return false
  if (modus.value === 'kopie') return !!kopieQuelle.value
  if (modus.value === 'zusammenfuehrung') return mergeQuellen.value.length >= 2
  if (modus.value === 'aus_charakter') return charakterId.value != null
  if (modus.value === 'elementauswahl') return !!basis.value
  return true
})

function schliessen() {
  fehler.value = ''
  emit('update:modelValue', false)
}

async function erstellen() {
  fehler.value = ''
  ladend.value = true
  try {
    const payload: SettingErstellenPayload = {
      name: name.value,
      beschreibung: beschreibung.value,
      modus: modus.value,
    }
    if (modus.value === 'kopie') payload.quellen = [kopieQuelle.value]
    if (modus.value === 'zusammenfuehrung') payload.quellen = mergeQuellen.value
    if (modus.value === 'aus_charakter') payload.charakter_id = charakterId.value ?? undefined
    if (modus.value === 'elementauswahl') {
      payload.basis = basis.value
      payload.elemente = elemente.value
    }
    const antwort = await store.erstelleSetting(payload)
    emit('erstellt', antwort)
    name.value = ''
    beschreibung.value = ''
    elemente.value = {}
    mergeQuellen.value = []
    emit('update:modelValue', false)
  } catch (e: any) {
    fehler.value = e?.message || 'Erstellen fehlgeschlagen'
  } finally {
    ladend.value = false
  }
}
</script>
