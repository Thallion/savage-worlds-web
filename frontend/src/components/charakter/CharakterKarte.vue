<template>
  <v-card class="cursor-pointer" hover @click="emit('oeffnen')">
    <div class="d-flex">
      <!-- Porträt links, damit die Karte so niedrig bleibt wie ohne Bild -->
      <div class="pt-4 ps-4">
        <CharakterPortraet
          :bild-id="char.bild_id"
          :name="char.char_name"
          variante="karte"
          :breite="mobile ? 54 : 72"
        />
      </div>
      <div class="flex-grow-1" style="min-width: 0">
        <v-card-title class="text-truncate">{{ char.char_name || 'Unbenannt' }}</v-card-title>
        <v-card-subtitle>{{ char.active_setting_name }}</v-card-subtitle>
        <v-card-text>
          <!-- Der Chip meint den Stand der Erschaffung (wie „Erschaffung abschließen"
               im Editor), nicht ob der Bogen gerade offen ist. -->
          <v-chip :color="char.char_gen_completed ? 'success' : 'warning'" size="small">
            {{ char.char_gen_completed ? 'Erschaffung abgeschlossen' : 'Erschaffung offen' }}
          </v-chip>
          <div class="text-caption mt-2">
            Zuletzt bearbeitet: {{ new Date(char.aktualisiert_am).toLocaleDateString('de-DE') }}
          </div>
        </v-card-text>
      </div>
    </div>
    <v-card-actions>
      <!-- Verschieben -->
      <v-menu v-if="verschiebbar">
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
import { useDisplay } from 'vuetify'
import type { CharakterListItem, Ordner } from '@/types/charakter'
import CharakterPortraet from './CharakterPortraet.vue'

const { xs: mobile } = useDisplay()

withDefaults(
  defineProps<{
    char: CharakterListItem
    ordnerListe: Ordner[]
    // Gast-Charaktere (nur im Browser) kennen keine Ordner
    verschiebbar?: boolean
  }>(),
  { verschiebbar: true },
)

const emit = defineEmits<{
  oeffnen: []
  exportieren: []
  loeschen: []
  verschieben: [ordnerId: number | null]
}>()
</script>
