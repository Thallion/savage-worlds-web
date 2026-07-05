import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Theme- und Farb-Manager.
 *
 * Verwaltet das aktive Vuetify-Theme sowie eine optionale, benutzerdefinierte
 * Akzentfarbe (Primärfarbe). Beides wird in localStorage gespeichert. Das
 * eigentliche Anwenden auf Vuetify passiert in App.vue, wo `useTheme()`
 * verfügbar ist — dieser Store ist die persistente Quelle der Wahrheit.
 */

export interface ThemeDefinition {
  id: string
  name: string
  beschreibung: string
  dark: boolean
  icon: string
  /** Standard-Primärfarbe des Themes (zum Zurücksetzen der Akzentfarbe). */
  standardPrimaer: string
  /** Repräsentative Farben für die Vorschau-Kachel. */
  vorschau: { hintergrund: string; flaeche: string }
}

export const VERFUEGBARE_THEMES: ThemeDefinition[] = [
  {
    id: 'pergament',
    name: 'Pergament',
    beschreibung: 'Beige & Braun wie ein Charakterbogen',
    dark: false,
    icon: 'mdi-scroll',
    standardPrimaer: '#6F4A2A',
    vorschau: { hintergrund: '#EDE3CC', flaeche: '#F6EFDD' },
  },
  {
    id: 'pergamentDunkel',
    name: 'Dunkles Leder',
    beschreibung: 'Gedämpftes Leder & Gold für die Nacht',
    dark: true,
    icon: 'mdi-book-open-page-variant',
    standardPrimaer: '#C79A5B',
    vorschau: { hintergrund: '#1A140D', flaeche: '#241B12' },
  },
  {
    id: 'light',
    name: 'Hell',
    beschreibung: 'Nüchternes, helles Standard-Design',
    dark: false,
    icon: 'mdi-white-balance-sunny',
    standardPrimaer: '#1565C0',
    vorschau: { hintergrund: '#FFFFFF', flaeche: '#F5F5F5' },
  },
  {
    id: 'dark',
    name: 'Dunkel',
    beschreibung: 'Klassisches dunkles Design',
    dark: true,
    icon: 'mdi-weather-night',
    standardPrimaer: '#1E88E5',
    vorschau: { hintergrund: '#121212', flaeche: '#1E1E1E' },
  },
]

export interface AkzentPreset {
  name: string
  farbe: string
}

export const AKZENT_PRESETS: AkzentPreset[] = [
  { name: 'Leder', farbe: '#6F4A2A' },
  { name: 'Ocker', farbe: '#A9743B' },
  { name: 'Blutrot', farbe: '#8C2A1E' },
  { name: 'Waldgrün', farbe: '#4E6E3A' },
  { name: 'Königsblau', farbe: '#3E5C76' },
  { name: 'Amethyst', farbe: '#5E4B8B' },
  { name: 'Altgold', farbe: '#B5852B' },
  { name: 'Schiefer', farbe: '#4A5259' },
]

const SPEICHER_THEME = 'sw-theme'
const SPEICHER_AKZENT = 'sw-akzentfarbe'
const STANDARD_THEME = 'pergament'

function ladeTheme(): string {
  const gespeichert = localStorage.getItem(SPEICHER_THEME)
  if (gespeichert && VERFUEGBARE_THEMES.some((t) => t.id === gespeichert)) {
    return gespeichert
  }
  return STANDARD_THEME
}

export const useThemeStore = defineStore('theme', () => {
  const themeId = ref<string>(ladeTheme())
  // null = Standard-Primärfarbe des jeweiligen Themes verwenden.
  const akzentfarbe = ref<string | null>(localStorage.getItem(SPEICHER_AKZENT))

  function themeDefinition(id: string = themeId.value): ThemeDefinition {
    return VERFUEGBARE_THEMES.find((t) => t.id === id) ?? VERFUEGBARE_THEMES[0]
  }

  /** Effektive Primärfarbe: benutzerdefiniert oder Theme-Standard. */
  function aktivePrimaerfarbe(id: string = themeId.value): string {
    return akzentfarbe.value ?? themeDefinition(id).standardPrimaer
  }

  function setzeTheme(id: string) {
    if (!VERFUEGBARE_THEMES.some((t) => t.id === id)) return
    themeId.value = id
    localStorage.setItem(SPEICHER_THEME, id)
  }

  function setzeAkzentfarbe(farbe: string | null) {
    akzentfarbe.value = farbe
    if (farbe) {
      localStorage.setItem(SPEICHER_AKZENT, farbe)
    } else {
      localStorage.removeItem(SPEICHER_AKZENT)
    }
  }

  function akzentZuruecksetzen() {
    setzeAkzentfarbe(null)
  }

  return {
    themeId,
    akzentfarbe,
    themeDefinition,
    aktivePrimaerfarbe,
    setzeTheme,
    setzeAkzentfarbe,
    akzentZuruecksetzen,
  }
})
