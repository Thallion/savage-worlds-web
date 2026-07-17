<template>
  <!-- Generisches Anlegen/Bearbeiten-Formular für Talente, Handicaps, Mächte
       und Ausrüstung — genutzt von den Charakter-Tabs (ElementEditor) und der
       Setting-Verwaltung (SettingDetailDialog). Der Aufrufer speichert und
       schließt bei Erfolg über die exponierten Methoden. -->
  <v-dialog v-model="sichtbar" max-width="560">
    <v-card>
      <v-card-title>
        {{ bearbeiteterName ? `${label} bearbeiten` : `Neues ${label === 'Ausrüstung' ? 'Element' : label} hinzufügen` }}
      </v-card-title>
      <v-card-text>
        <v-autocomplete
          v-if="modus === 'bearbeiten'"
          :model-value="bearbeiteterName"
          :items="elementNamen"
          :label="`${label} wählen`"
          density="compact"
          class="mb-2"
          @update:model-value="ladeElement"
        />
        <template v-if="modus === 'neu' || bearbeiteterName">
          <v-text-field v-model="formName" label="Name *" density="compact" class="mb-1" />
          <template v-for="feld in sichtbareFelder" :key="feld.key">
            <v-select
              v-if="feld.typ === 'select'"
              v-model="formWerte[feld.key]"
              :items="feld.optionen"
              :label="feld.label"
              density="compact"
              class="mb-1"
            />
            <v-textarea
              v-else-if="feld.typ === 'textarea'"
              v-model="formWerte[feld.key]"
              :label="feld.label"
              rows="2"
              auto-grow
              density="compact"
              class="mb-1"
            />
            <v-text-field
              v-else
              v-model="formWerte[feld.key]"
              :label="feld.label"
              :type="feld.typ === 'int' || feld.typ === 'float' ? 'number' : 'text'"
              density="compact"
              class="mb-1"
            />
          </template>
        </template>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="sichtbar = false">Abbrechen</v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :disabled="modus === 'bearbeiten' && !bearbeiteterName"
          @click="speichern"
        >
          Speichern
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  FELDER,
  TYP_LABEL,
  elementZuFormular,
  formularZuElement,
  type ElementTyp,
} from '@/utils/settingElemente'

const props = defineProps<{
  typ: ElementTyp
  // Bestand für Bearbeiten-Auswahl und das Laden der Formularwerte
  katalog: Record<string, any>
}>()
const emit = defineEmits<{
  (e: 'speichern', payload: { name: string; daten: Record<string, any>; alterName?: string }): void
}>()

const sichtbar = ref(false)
const modus = ref<'neu' | 'bearbeiten'>('neu')
const bearbeiteterName = ref('')
const formName = ref('')
const formWerte = ref<Record<string, any>>({})

const label = computed(() => TYP_LABEL[props.typ])
const elementNamen = computed(() => Object.keys(props.katalog).sort())

const sichtbareFelder = computed(() =>
  FELDER[props.typ].filter(
    (f) => !f.nurKategorie || f.nurKategorie.includes(formWerte.value.kategorie),
  ),
)

function oeffneNeu() {
  modus.value = 'neu'
  bearbeiteterName.value = ''
  formName.value = ''
  formWerte.value = elementZuFormular(props.typ, {})
  if (props.typ === 'ausruestung') formWerte.value.kategorie ||= 'Allgemein'
  if (props.typ === 'handicaps') formWerte.value.stufe ||= 'leicht'
  sichtbar.value = true
}

// Ohne Namen öffnet sich die Auswahl-Liste, mit Namen direkt das Formular
function oeffneBearbeiten(name?: string) {
  modus.value = 'bearbeiten'
  bearbeiteterName.value = ''
  formName.value = ''
  if (name) ladeElement(name)
  sichtbar.value = true
}

function ladeElement(name: string) {
  bearbeiteterName.value = name
  formName.value = name
  formWerte.value = elementZuFormular(props.typ, props.katalog[name] ?? {})
}

function schliesse() {
  sichtbar.value = false
}

defineExpose({ oeffneNeu, oeffneBearbeiten, schliesse })

function speichern() {
  emit('speichern', {
    name: formName.value,
    daten: formularZuElement(props.typ, formWerte.value),
    alterName: modus.value === 'bearbeiten' ? bearbeiteterName.value : undefined,
  })
}
</script>
