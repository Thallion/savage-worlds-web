<template>
  <!-- Anlegen/Bearbeiten von Superkräften inkl. kraftspezifischer
       Modifikatoren — genutzt vom Superkräfte-Tab und der Setting-Verwaltung.
       Gleiche Schnittstelle wie ElementFormDialog/VolkFormDialog: der
       Aufrufer speichert und schließt bei Erfolg. -->
  <v-dialog v-model="sichtbar" max-width="640">
    <v-card>
      <v-card-title>
        {{ bearbeiteterName ? 'Superkraft bearbeiten' : 'Neue Superkraft hinzufügen' }}
      </v-card-title>
      <v-card-text>
        <v-autocomplete
          v-if="modus === 'bearbeiten'"
          :model-value="bearbeiteterName"
          :items="elementNamen"
          label="Superkraft wählen"
          density="compact"
          class="mb-2"
          @update:model-value="ladeKraft"
        />
        <template v-if="modus === 'neu' || bearbeiteterName">
          <v-text-field v-model="formName" label="Name *" density="compact" class="mb-1" />
          <v-text-field
            v-model="formKosten"
            label="Kosten (SKP, z. B. 2 oder 1/2)"
            density="compact"
            class="mb-1"
          />
          <v-textarea
            v-model="formBeschreibung"
            label="Beschreibung"
            rows="2"
            auto-grow
            density="compact"
            class="mb-2"
          />

          <div class="text-subtitle-2 mb-1">Modifikatoren</div>
          <v-row v-for="(mod, index) in formMods" :key="index" dense align="center">
            <v-col cols="4">
              <v-text-field v-model="mod.name" label="Name" density="compact" />
            </v-col>
            <v-col cols="2">
              <v-text-field v-model="mod.kosten" label="Kosten" density="compact" />
            </v-col>
            <v-col cols="5">
              <v-text-field v-model="mod.beschreibung" label="Beschreibung" density="compact" />
            </v-col>
            <v-col cols="1" class="pb-5">
              <v-btn
                icon="mdi-delete"
                size="x-small"
                variant="text"
                @click="formMods.splice(index, 1)"
              />
            </v-col>
          </v-row>
          <v-btn
            size="small"
            variant="tonal"
            prepend-icon="mdi-plus"
            @click="formMods.push({ name: '', kosten: '', beschreibung: '' })"
          >
            Modifikator hinzufügen
          </v-btn>
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

interface ModZeile {
  name: string
  kosten: string
  beschreibung: string
}

const props = defineProps<{
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
const formKosten = ref('')
const formBeschreibung = ref('')
const formMods = ref<ModZeile[]>([])

const elementNamen = computed(() => Object.keys(props.katalog).sort())

function oeffneNeu() {
  modus.value = 'neu'
  bearbeiteterName.value = ''
  formName.value = ''
  formKosten.value = '1'
  formBeschreibung.value = ''
  formMods.value = []
  sichtbar.value = true
}

// Ohne Namen öffnet sich die Auswahl-Liste, mit Namen direkt das Formular
function oeffneBearbeiten(name?: string) {
  modus.value = 'bearbeiten'
  bearbeiteterName.value = ''
  formName.value = ''
  if (name) ladeKraft(name)
  sichtbar.value = true
}

function ladeKraft(name: string) {
  bearbeiteterName.value = name
  const kraft = props.katalog[name] ?? {}
  formName.value = name
  formKosten.value = String(kraft.kosten ?? '')
  formBeschreibung.value = kraft.beschreibung ?? ''
  formMods.value = Object.entries<any>(kraft.modifikatoren ?? {}).map(([modName, mod]) => ({
    name: modName,
    kosten: String(mod?.kosten ?? ''),
    beschreibung: mod?.beschreibung ?? '',
  }))
}

function schliesse() {
  sichtbar.value = false
}

defineExpose({ oeffneNeu, oeffneBearbeiten, schliesse })

function speichern() {
  const modifikatoren: Record<string, any> = {}
  for (const mod of formMods.value) {
    if (mod.name.trim()) {
      modifikatoren[mod.name.trim()] = { kosten: mod.kosten, beschreibung: mod.beschreibung }
    }
  }
  emit('speichern', {
    name: formName.value,
    daten: { kosten: formKosten.value, beschreibung: formBeschreibung.value, modifikatoren },
    alterName: modus.value === 'bearbeiten' ? bearbeiteterName.value : undefined,
  })
}
</script>
