<template>
  <div>
    <v-select
      v-model="quelle"
      :items="quellenNamen"
      label="Quell-Setting"
      density="compact"
      hide-details
      class="mb-3"
    />

    <v-progress-linear v-if="ladend" indeterminate color="primary" class="mb-3" />

    <template v-if="quelle && !ladend">
      <v-autocomplete
        v-for="typ in typenMitElementen"
        :key="`${quelle}:${typ}`"
        :model-value="auswahlFuer(quelle, typ)"
        :items="elementNamen[typ]"
        :label="`${TYP_LABELS[typ]} (${elementNamen[typ].length})`"
        multiple
        chips
        closable-chips
        clearable
        density="compact"
        class="mb-1"
        @update:model-value="setzeAuswahl(quelle, typ, $event)"
      />
    </template>

    <div v-if="zusammenfassung.length" class="mt-2">
      <div class="text-caption text-grey mb-1">Gewählte Elemente:</div>
      <v-chip
        v-for="eintrag in zusammenfassung"
        :key="eintrag"
        size="small"
        class="mr-1 mb-1"
        variant="tonal"
      >
        {{ eintrag }}
      </v-chip>
    </div>
  </div>
</template>

<script setup lang="ts">
// Elementauswahl über mehrere Quell-Settings hinweg: die Auswahl pro Quelle
// bleibt beim Wechsel des Quell-Settings erhalten (modelValue =
// {quelle: {typ: [namen]}}, das Format von POST /api/settings).
import { computed, ref, watch } from 'vue'
import { useEinstellungenStore } from '@/stores/einstellungen'
import { TYP_LABELS, WAEHLBARE_TYPEN } from '@/utils/settingVerwaltung'

const props = defineProps<{
  modelValue: Record<string, Record<string, string[]>>
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', wert: Record<string, Record<string, string[]>>): void
}>()

const store = useEinstellungenStore()
const quelle = ref('')
const ladend = ref(false)
const quellSetting = ref<Record<string, any> | null>(null)

const quellenNamen = computed(() => store.verfuegbareSettings.map((s) => s.name))

watch(
  quelle,
  async (name) => {
    if (!name) return
    ladend.value = true
    try {
      quellSetting.value = await store.holeSetting(name)
    } finally {
      ladend.value = false
    }
  },
  { immediate: true },
)

const elementNamen = computed<Record<string, string[]>>(() => {
  const setting = quellSetting.value ?? {}
  const result: Record<string, string[]> = {}
  for (const typ of WAEHLBARE_TYPEN) {
    result[typ] = Object.keys(setting[typ] ?? {}).sort((a, b) => a.localeCompare(b, 'de'))
  }
  return result
})

const typenMitElementen = computed(() =>
  WAEHLBARE_TYPEN.filter((typ) => elementNamen.value[typ].length > 0),
)

function auswahlFuer(quellName: string, typ: string): string[] {
  return props.modelValue[quellName]?.[typ] ?? []
}

function setzeAuswahl(quellName: string, typ: string, namen: string[]) {
  const neu = { ...props.modelValue, [quellName]: { ...props.modelValue[quellName] } }
  if (namen.length) {
    neu[quellName][typ] = namen
  } else {
    delete neu[quellName][typ]
    if (!Object.keys(neu[quellName]).length) delete neu[quellName]
  }
  emit('update:modelValue', neu)
}

const zusammenfassung = computed(() => {
  const eintraege: string[] = []
  for (const [quellName, typen] of Object.entries(props.modelValue)) {
    const anzahl = Object.values(typen).reduce((summe, namen) => summe + namen.length, 0)
    if (anzahl) eintraege.push(`${quellName}: ${anzahl}`)
  }
  return eintraege
})
</script>
