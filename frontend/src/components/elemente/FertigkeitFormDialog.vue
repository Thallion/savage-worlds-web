<template>
  <!-- Anlegen/Bearbeiten von Fertigkeiten im Setting-Katalog
       (fertigkeiten_daten: Name -> [verknüpftes Attribut]) — genutzt von der
       Setting-Verwaltung. Gleiche Schnittstelle wie die anderen
       Formular-Dialoge: der Aufrufer speichert und schließt bei Erfolg. -->
  <v-dialog v-model="sichtbar" max-width="480">
    <v-card>
      <v-card-title>
        {{ bearbeiteterName ? 'Fertigkeit bearbeiten' : 'Neue Fertigkeit hinzufügen' }}
      </v-card-title>
      <v-card-text>
        <v-autocomplete
          v-if="modus === 'bearbeiten'"
          :model-value="bearbeiteterName"
          :items="elementNamen"
          label="Fertigkeit wählen"
          density="compact"
          class="mb-2"
          @update:model-value="ladeFertigkeit"
        />
        <template v-if="modus === 'neu' || bearbeiteterName">
          <v-text-field v-model="formName" label="Name *" density="compact" class="mb-1" />
          <v-select
            v-model="formAttribut"
            :items="attribute"
            label="Verknüpftes Attribut"
            density="compact"
          />
        </template>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="sichtbar = false">Abbrechen</v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :disabled="(modus === 'bearbeiten' && !bearbeiteterName) || !formAttribut"
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

const props = defineProps<{
  // fertigkeiten_daten des Settings: Name -> [Attribut]
  katalog: Record<string, any>
  // wählbare Attributnamen (aus dem Setting bzw. Standard)
  attribute: string[]
}>()
const emit = defineEmits<{
  (e: 'speichern', payload: { name: string; daten: Record<string, any>; alterName?: string }): void
}>()

const sichtbar = ref(false)
const modus = ref<'neu' | 'bearbeiten'>('neu')
const bearbeiteterName = ref('')
const formName = ref('')
const formAttribut = ref('')

const elementNamen = computed(() => Object.keys(props.katalog).sort())

function oeffneNeu() {
  modus.value = 'neu'
  bearbeiteterName.value = ''
  formName.value = ''
  formAttribut.value = ''
  sichtbar.value = true
}

// Ohne Namen öffnet sich die Auswahl-Liste, mit Namen direkt das Formular
function oeffneBearbeiten(name?: string) {
  modus.value = 'bearbeiten'
  bearbeiteterName.value = ''
  formName.value = ''
  if (name) ladeFertigkeit(name)
  sichtbar.value = true
}

function ladeFertigkeit(name: string) {
  bearbeiteterName.value = name
  formName.value = name
  formAttribut.value = props.katalog[name]?.[0] ?? ''
}

function schliesse() {
  sichtbar.value = false
}

defineExpose({ oeffneNeu, oeffneBearbeiten, schliesse })

function speichern() {
  emit('speichern', {
    name: formName.value,
    daten: { attribut: formAttribut.value },
    alterName: modus.value === 'bearbeiten' ? bearbeiteterName.value : undefined,
  })
}
</script>
