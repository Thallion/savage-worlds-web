<template>
  <v-card class="cursor-pointer" hover @click="emit('oeffnen')">
    <v-card-title>{{ char.char_name || 'Unbenannt' }}</v-card-title>
    <v-card-subtitle>{{ char.active_setting_name }}</v-card-subtitle>
    <v-card-text>
      <v-chip :color="char.char_gen_completed ? 'success' : 'warning'" size="small">
        {{ char.char_gen_completed ? 'Fertig' : 'In Bearbeitung' }}
      </v-chip>
      <span class="text-caption ml-2">
        {{ new Date(char.aktualisiert_am).toLocaleDateString('de-DE') }}
      </span>
    </v-card-text>
    <v-card-actions>
      <!-- Verschieben -->
      <v-menu>
        <template #activator="{ props }">
          <v-btn icon="mdi-folder-move" size="small" v-bind="props" @click.stop />
        </template>
        <v-list density="compact">
          <v-list-subheader>Verschieben nach</v-list-subheader>
          <v-list-item :disabled="char.ordner_id === null" @click="emit('verschieben', null)">
            <template #prepend><v-icon>mdi-folder-outline</v-icon></template>
            <v-list-item-title>Ohne Ordner</v-list-item-title>
          </v-list-item>
          <v-divider v-if="ordnerListe.length" />
          <v-list-item
            v-for="o in ordnerListe"
            :key="o.id"
            :disabled="char.ordner_id === o.id"
            @click="emit('verschieben', o.id)"
          >
            <template #prepend><v-icon>mdi-folder</v-icon></template>
            <v-list-item-title>{{ o.name }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
      <v-spacer />
      <v-btn icon="mdi-download" size="small" @click.stop="emit('exportieren')" />
      <v-btn icon="mdi-delete" color="error" size="small" @click.stop="emit('loeschen')" />
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import type { CharakterListItem, Ordner } from '@/types/charakter'

defineProps<{
  char: CharakterListItem
  ordnerListe: Ordner[]
}>()

const emit = defineEmits<{
  oeffnen: []
  exportieren: []
  loeschen: []
  verschieben: [ordnerId: number | null]
}>()
</script>
