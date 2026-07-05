<template>
  <v-menu :close-on-content-click="false" location="bottom end" offset="8">
    <template #activator="{ props }">
      <v-btn
        v-bind="props"
        icon="mdi-palette"
        variant="text"
        aria-label="Darstellung & Farben"
      />
    </template>

    <v-card min-width="320" max-width="360">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon icon="mdi-palette-outline" size="small" />
        Darstellung
      </v-card-title>

      <v-divider />

      <v-card-text>
        <div class="text-overline mb-2">Design</div>
        <v-row dense>
          <v-col v-for="thema in themes" :key="thema.id" cols="6">
            <v-card
              :variant="thema.id === themeStore.themeId ? 'tonal' : 'outlined'"
              :color="thema.id === themeStore.themeId ? 'primary' : undefined"
              class="pa-2 h-100"
              @click="themeStore.setzeTheme(thema.id)"
            >
              <div class="d-flex align-center ga-2 mb-1">
                <div
                  class="sw-swatch"
                  :style="{
                    background: thema.vorschau.hintergrund,
                    borderColor: thema.vorschau.flaeche,
                  }"
                />
                <v-icon :icon="thema.icon" size="small" />
                <span class="text-body-2 font-weight-medium">{{ thema.name }}</span>
                <v-spacer />
                <v-icon
                  v-if="thema.id === themeStore.themeId"
                  icon="mdi-check-circle"
                  size="small"
                  color="primary"
                />
              </div>
              <div class="text-caption text-medium-emphasis" style="line-height: 1.2">
                {{ thema.beschreibung }}
              </div>
            </v-card>
          </v-col>
        </v-row>

        <div class="text-overline mt-4 mb-2 d-flex align-center">
          Akzentfarbe
          <v-spacer />
          <v-btn
            v-if="themeStore.akzentfarbe"
            size="x-small"
            variant="text"
            prepend-icon="mdi-restore"
            @click="themeStore.akzentZuruecksetzen()"
          >
            Standard
          </v-btn>
        </div>

        <div class="d-flex flex-wrap ga-2">
          <button
            v-for="preset in presets"
            :key="preset.farbe"
            type="button"
            class="sw-akzent"
            :class="{ 'sw-akzent--aktiv': istAktiv(preset.farbe) }"
            :style="{ background: preset.farbe }"
            :title="preset.name"
            :aria-label="preset.name"
            @click="themeStore.setzeAkzentfarbe(preset.farbe)"
          >
            <v-icon
              v-if="istAktiv(preset.farbe)"
              icon="mdi-check"
              size="small"
              color="white"
            />
          </button>

          <v-menu :close-on-content-click="false" location="bottom">
            <template #activator="{ props }">
              <button
                type="button"
                class="sw-akzent sw-akzent--custom"
                title="Eigene Farbe"
                aria-label="Eigene Farbe wählen"
                v-bind="props"
              >
                <v-icon icon="mdi-eyedropper-variant" size="small" />
              </button>
            </template>
            <v-color-picker
              :model-value="themeStore.aktivePrimaerfarbe()"
              mode="hexa"
              @update:model-value="themeStore.setzeAkzentfarbe($event)"
            />
          </v-menu>
        </div>
      </v-card-text>
    </v-card>
  </v-menu>
</template>

<script setup lang="ts">
import { useThemeStore, VERFUEGBARE_THEMES, AKZENT_PRESETS } from '@/stores/theme'

const themeStore = useThemeStore()
const themes = VERFUEGBARE_THEMES
const presets = AKZENT_PRESETS

function istAktiv(farbe: string): boolean {
  return themeStore.akzentfarbe?.toLowerCase() === farbe.toLowerCase()
}
</script>

<style scoped>
.sw-swatch {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 2px solid;
  flex: none;
}

.sw-akzent {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid rgba(0, 0, 0, 0.25);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.sw-akzent:hover {
  transform: scale(1.12);
}

.sw-akzent--aktiv {
  box-shadow: 0 0 0 2px rgb(var(--v-theme-surface)), 0 0 0 4px currentColor;
}

.sw-akzent--custom {
  background: rgb(var(--v-theme-surface-variant, var(--v-theme-surface)));
  border-style: dashed;
}
</style>
