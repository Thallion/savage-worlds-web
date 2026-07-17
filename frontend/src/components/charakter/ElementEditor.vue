<template>
  <div class="d-flex align-center ga-2 mb-2">
    <v-btn size="small" variant="tonal" prepend-icon="mdi-plus" @click="formDialog?.oeffneNeu()">
      {{ label }} hinzufügen
    </v-btn>
    <v-btn
      size="small"
      variant="tonal"
      prepend-icon="mdi-pencil"
      @click="formDialog?.oeffneBearbeiten()"
    >
      Bearbeiten
    </v-btn>
    <v-btn size="small" variant="tonal" prepend-icon="mdi-delete" @click="oeffneLoeschen">
      Löschen
    </v-btn>
  </div>

  <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>

  <!-- Hinzufügen / Bearbeiten -->
  <ElementFormDialog ref="formDialog" :typ="typ" :katalog="katalog" @speichern="speichern" />

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
import { TYP_LABEL, mergeKatalog, type ElementTyp } from '@/utils/settingElemente'
import ElementFormDialog from '@/components/elemente/ElementFormDialog.vue'

const props = defineProps<{ typ: ElementTyp }>()

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const label = TYP_LABEL[props.typ]

const meldung = ref('')
const meldungSichtbar = ref(false)

const formDialog = ref<InstanceType<typeof ElementFormDialog>>()
const loeschenSichtbar = ref(false)
const loeschName = ref('')

const katalog = computed(() =>
  mergeKatalog(
    (einstellungenStore.aktuellesSetting as any)?.[props.typ],
    store.aktuellerCharakter?.charakter_daten,
    props.typ,
  ),
)
const elementNamen = computed(() => Object.keys(katalog.value).sort())

function oeffneLoeschen() {
  loeschName.value = ''
  loeschenSichtbar.value = true
}

// Direkt-Aufruf von den Element-Zeilen der Tabs (ohne Suchfeld im Dialog)
function bearbeiteElement(name: string) {
  formDialog.value?.oeffneBearbeiten(name)
}

function loescheElement(name: string) {
  loeschName.value = name
  loeschenSichtbar.value = true
}

defineExpose({ bearbeiteElement, loescheElement })

async function speichern(payload: { name: string; daten: Record<string, any>; alterName?: string }) {
  const result = await store.elementSpeichern(props.typ, payload.name, payload.daten, payload.alterName)
  if (result.success) {
    formDialog.value?.schliesse()
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
