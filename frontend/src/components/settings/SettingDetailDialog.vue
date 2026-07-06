<template>
  <v-dialog :model-value="modelValue" max-width="800" @update:model-value="schliessen">
    <v-card v-if="settingName">
      <v-card-title class="d-flex align-center">
        {{ settingName }}
        <v-chip v-if="custom" size="small" color="primary" class="ml-2">Eigenes Setting</v-chip>
        <v-spacer />
        <v-btn
          icon="mdi-download"
          variant="text"
          title="Als JSON exportieren"
          @click="exportiere"
        />
        <v-btn icon="mdi-close" variant="text" @click="schliessen" />
      </v-card-title>

      <v-card-text>
        <v-progress-linear v-if="ladend" indeterminate color="primary" />

        <template v-if="setting">
          <!-- Metadaten: bei eigenen Settings bearbeitbar -->
          <template v-if="custom">
            <v-row dense>
              <v-col cols="12" sm="5">
                <v-text-field v-model="neuerName" label="Name" density="compact" />
              </v-col>
              <v-col cols="12" sm="5">
                <v-text-field v-model="neueBeschreibung" label="Beschreibung" density="compact" />
              </v-col>
              <v-col cols="12" sm="2" class="d-flex align-center">
                <v-btn
                  color="primary"
                  variant="tonal"
                  block
                  :disabled="!metadatenGeaendert"
                  @click="speichereMetadaten"
                >
                  Speichern
                </v-btn>
              </v-col>
            </v-row>
          </template>
          <p v-else class="text-body-2 text-grey mb-4">{{ setting.description }}</p>

          <v-expansion-panels variant="accordion">
            <v-expansion-panel v-for="typ in typenMitElementen" :key="typ">
              <v-expansion-panel-title>
                {{ TYP_LABELS[typ] }} ({{ elementNamen(typ).length }})
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-text-field
                  v-if="elementNamen(typ).length > 20"
                  v-model="filter[typ]"
                  label="Filtern"
                  density="compact"
                  clearable
                  prepend-inner-icon="mdi-magnify"
                  class="mb-2"
                />
                <v-chip
                  v-for="elementName in gefiltert(typ)"
                  :key="elementName"
                  size="small"
                  class="mr-1 mb-1"
                  :closable="custom"
                  @click:close="entferneElement(typ, elementName)"
                >
                  {{ elementName }}
                </v-chip>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <!-- Elemente aus anderen Settings übernehmen -->
          <template v-if="custom">
            <v-divider class="my-4" />
            <div class="text-subtitle-1 mb-2">Elemente hinzufügen</div>
            <ElementAuswahl v-model="hinzufuegenAuswahl" />
            <v-btn
              color="primary"
              class="mt-2"
              :disabled="!hatAuswahl"
              :loading="hinzufuegenLaeuft"
              @click="fuegeElementeHinzu"
            >
              Übernehmen
            </v-btn>
          </template>

          <v-alert v-if="fehler" type="error" density="compact" class="mt-3">{{ fehler }}</v-alert>
        </template>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useEinstellungenStore } from '@/stores/einstellungen'
import { TYP_LABELS } from '@/utils/settingVerwaltung'
import ElementAuswahl from './ElementAuswahl.vue'

const props = defineProps<{
  modelValue: boolean
  settingName: string
  custom: boolean
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', wert: boolean): void
  (e: 'geaendert', neuerName: string): void
}>()

const store = useEinstellungenStore()
const setting = ref<Record<string, any> | null>(null)
const ladend = ref(false)
const fehler = ref('')
const filter = reactive<Record<string, string>>({})
const neuerName = ref('')
const neueBeschreibung = ref('')
const hinzufuegenAuswahl = ref<Record<string, Record<string, string[]>>>({})
const hinzufuegenLaeuft = ref(false)

watch(
  () => [props.modelValue, props.settingName],
  async ([offen]) => {
    if (!offen || !props.settingName) return
    fehler.value = ''
    hinzufuegenAuswahl.value = {}
    await ladeSetting()
    neuerName.value = props.settingName
    neueBeschreibung.value = setting.value?.description ?? ''
  },
)

async function ladeSetting() {
  ladend.value = true
  try {
    setting.value = await store.holeSetting(props.settingName)
  } finally {
    ladend.value = false
  }
}

const typenMitElementen = computed(() =>
  Object.keys(TYP_LABELS).filter((typ) => elementNamen(typ).length > 0),
)

function elementNamen(typ: string): string[] {
  return Object.keys(setting.value?.[typ] ?? {}).sort((a, b) => a.localeCompare(b, 'de'))
}

function gefiltert(typ: string): string[] {
  const suchtext = (filter[typ] ?? '').toLowerCase()
  if (!suchtext) return elementNamen(typ)
  return elementNamen(typ).filter((n) => n.toLowerCase().includes(suchtext))
}

const metadatenGeaendert = computed(
  () =>
    neuerName.value.trim() !== props.settingName ||
    neueBeschreibung.value !== (setting.value?.description ?? ''),
)

const hatAuswahl = computed(() =>
  Object.values(hinzufuegenAuswahl.value).some((typen) =>
    Object.values(typen).some((namen) => namen.length > 0),
  ),
)

async function speichereMetadaten() {
  fehler.value = ''
  try {
    const antwort = await store.aktualisiereSetting(props.settingName, {
      neuer_name: neuerName.value,
      beschreibung: neueBeschreibung.value,
    })
    emit('geaendert', antwort.name)
  } catch (e: any) {
    fehler.value = e?.message || 'Speichern fehlgeschlagen'
  }
}

async function entferneElement(typ: string, elementName: string) {
  fehler.value = ''
  try {
    await store.elementEntfernen(props.settingName, typ, elementName)
    await ladeSetting()
  } catch (e: any) {
    fehler.value = e?.message || 'Entfernen fehlgeschlagen'
  }
}

async function fuegeElementeHinzu() {
  fehler.value = ''
  hinzufuegenLaeuft.value = true
  try {
    // Die API nimmt eine Quelle pro Aufruf — über alle gewählten Quellen laufen
    for (const [quelle, elemente] of Object.entries(hinzufuegenAuswahl.value)) {
      await store.elementeHinzufuegen(props.settingName, quelle, elemente)
    }
    hinzufuegenAuswahl.value = {}
    await ladeSetting()
  } catch (e: any) {
    fehler.value = e?.message || 'Hinzufügen fehlgeschlagen'
  } finally {
    hinzufuegenLaeuft.value = false
  }
}

async function exportiere() {
  fehler.value = ''
  try {
    await store.exportiereSetting(props.settingName)
  } catch (e: any) {
    fehler.value = e?.message || 'Export fehlgeschlagen'
  }
}

function schliessen() {
  emit('update:modelValue', false)
}
</script>
