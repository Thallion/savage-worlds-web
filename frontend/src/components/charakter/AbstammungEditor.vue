<template>
  <div class="d-flex align-center ga-2 mb-2">
    <v-btn size="small" variant="tonal" prepend-icon="mdi-plus" @click="formDialog?.oeffneNeu()">
      Abstammung hinzufügen
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
  <VolkFormDialog
    ref="formDialog"
    :setting="setting"
    :fertigkeiten="fertigkeitenNamen"
    :katalog="katalog"
    :eigene-namen="eigeneNamen"
    @speichern="speichern"
  />

  <!-- Löschen -->
  <v-dialog v-model="loeschenSichtbar" max-width="480">
    <v-card>
      <v-card-title>Abstammung löschen</v-card-title>
      <v-card-text>
        <v-autocomplete
          v-model="loeschName"
          :items="alleNamen"
          label="Abstammung wählen"
          density="compact"
        />
        <p class="text-caption">
          Eigene Abstammungen werden entfernt, native Abstammungen des Settings nur für
          diesen Charakter ausgeblendet. Die aktuell gewählte Abstammung muss zuerst
          abgewählt werden.
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
import { mergeKatalog } from '@/utils/settingElemente'
import VolkFormDialog from '@/components/elemente/VolkFormDialog.vue'

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const meldung = ref('')
const meldungSichtbar = ref(false)

const formDialog = ref<InstanceType<typeof VolkFormDialog>>()
const loeschenSichtbar = ref(false)
const loeschName = ref('')

const daten = computed(() => store.aktuellerCharakter?.charakter_daten as any)
const setting = computed(() => (einstellungenStore.aktuellesSetting as any) ?? {})

const katalog = computed(() =>
  mergeKatalog(setting.value.voelker, daten.value, 'voelker'),
)
const alleNamen = computed(() => Object.keys(katalog.value).sort())
const eigeneNamen = computed(() =>
  Object.keys(katalog.value)
    .filter((n) => katalog.value[n]?.custom && Array.isArray(katalog.value[n]?.eigenarten))
    .sort(),
)
const fertigkeitenNamen = computed(() => Object.keys(daten.value?.fertigkeiten ?? {}))

function oeffneLoeschen() {
  loeschName.value = ''
  loeschenSichtbar.value = true
}

async function speichern(payload: { name: string; daten: Record<string, any>; alterName?: string }) {
  const result = await store.elementSpeichern('voelker', payload.name, payload.daten, payload.alterName)
  if (result.success) {
    formDialog.value?.schliesse()
  } else {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

async function loeschen() {
  const result = await store.elementLoeschen('voelker', loeschName.value)
  if (result.success) {
    loeschenSichtbar.value = false
  } else {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}
</script>
