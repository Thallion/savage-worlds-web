import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'
import './styles/rollenspiel.css'

import App from './App.vue'
import router from './router'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    // Standardmäßig Pergament: Rollenspiel-Flair wie ein Charakterbogen.
    defaultTheme: 'pergament',
    themes: {
      // Beige/Braun wie alter Charakterbogen bzw. Pergament.
      pergament: {
        dark: false,
        colors: {
          background: '#EDE3CC',
          surface: '#F6EFDD',
          'surface-variant': '#D9C9A3',
          primary: '#6F4A2A',
          secondary: '#A9743B',
          accent: '#8C2A1E',
          error: '#9B2C1E',
          info: '#3E5C76',
          success: '#4E6E3A',
          warning: '#B5852B',
          'on-background': '#3A2C1A',
          'on-surface': '#3A2C1A',
          'on-primary': '#F6EFDD',
        },
      },
      // Dunkle Leder/Gold-Variante des Pergament-Looks.
      pergamentDunkel: {
        dark: true,
        colors: {
          background: '#1A140D',
          surface: '#241B12',
          'surface-variant': '#3A2C1C',
          primary: '#C79A5B',
          secondary: '#9C6B34',
          accent: '#C24A33',
          error: '#CF6152',
          info: '#7FA8C9',
          success: '#8FB36A',
          warning: '#D6A63E',
          'on-background': '#EAD9BC',
          'on-surface': '#EAD9BC',
          'on-primary': '#241B12',
        },
      },
      dark: {
        colors: {
          primary: '#1E88E5',
          secondary: '#FF8F00',
          accent: '#E53935',
          surface: '#1E1E1E',
        },
      },
      light: {
        colors: {
          primary: '#1565C0',
          secondary: '#F57F17',
          accent: '#C62828',
        },
      },
    },
  },
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(vuetify)
app.mount('#app')
