<template>
  <div class="d-flex align-center ga-2 mb-2">
    <v-btn size="small" variant="tonal" prepend-icon="mdi-plus" @click="oeffneNeu">
      {{ label }} hinzufügen
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
  <v-dialog v-model="formSichtbar" max-width="560">
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
        <v-btn variant="text" @click="formSichtbar = false">Abbrechen</v-btn>
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

  <!-- Löschen -->
  <v-dialog v-model="loeschenSichtbar" max-width="480">
    <v-card>
      <v-card-title>{{ label }} löschen</v-card-title>
      <v-card-text>
        <v-autocomplete
          v-model="loeschName"
          :items="elementNamen"
          :label="`${label} wählen`"
          density="compact"
        />
        <p class="text-caption">
          Eigene Elemente werden entfernt, native Elemente des Settings nur für diesen
          Charakter ausgeblendet.
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
import { computed, ref } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'
import {
  FELDER,
  TYP_LABEL,
  elementZuFormular,
  formularZuElement,
  mergeKatalog,
  type ElementTyp,
} from '@/utils/settingElemente'

const props = defineProps<{ typ: ElementTyp }>()

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const label = TYP_LABEL[props.typ]

const meldung = ref('')
const meldungSichtbar = ref(false)

const formSichtbar = ref(false)
const loeschenSichtbar = ref(false)
const modus = ref<'neu' | 'bearbeiten'>('neu')
const bearbeiteterName = ref('')
const formName = ref('')
const formWerte = ref<Record<string, any>>({})
const loeschName = ref('')

const katalog = computed(() =>
  mergeKatalog(
    (einstellungenStore.aktuellesSetting as any)?.[props.typ],
    store.aktuellerCharakter?.charakter_daten,
    props.typ,
  ),
)
const elementNamen = computed(() => Object.keys(katalog.value).sort())

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
  formSichtbar.value = true
}

function oeffneBearbeiten() {
  modus.value = 'bearbeiten'
  bearbeiteterName.value = ''
  formName.value = ''
  formSichtbar.value = true
}

function ladeElement(name: string) {
  bearbeiteterName.value = name
  formName.value = name
  formWerte.value = elementZuFormular(props.typ, katalog.value[name] ?? {})
}

function oeffneLoeschen() {
  loeschName.value = ''
  loeschenSichtbar.value = true
}

async function speichern() {
  const elementDaten = formularZuElement(props.typ, formWerte.value)
  const result = await store.elementSpeichern(
    props.typ,
    formName.value,
    elementDaten,
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
  const result = await store.elementLoeschen(props.typ, loeschName.value)
  if (result.success) {
    loeschenSichtbar.value = false
  } else {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}
</script>
