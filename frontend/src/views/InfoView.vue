<template>
  <v-container class="py-8">
    <v-row justify="center">
      <v-col cols="12" md="9" lg="8">
        <!-- Fan-Logo prominent platziert -->
        <div class="text-center mb-8">
          <v-img
            :src="logoUrl"
            alt="Savage Worlds Fanprodukt"
            max-width="480"
            class="mx-auto sw-fanlogo"
            contain
          />
        </div>

        <h1 class="text-h4 text-center mb-2">Savage Worlds Charakter-Generator</h1>
        <p class="text-center text-body-2 mb-6">
          Version {{ appVersion }} &middot; Web-Portierung des deutschen
          Savage-Worlds-Charakter-Generators
        </p>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">
            Lizenz- und Urheberrechtsinformationen
          </v-card-title>
          <v-card-subtitle class="pb-2">Savage Worlds Fan-Produkt</v-card-subtitle>
          <v-card-text>
            <p class="mb-4">
              „Dieses Produkt bezieht sich auf das Regelsystem Savage Worlds,
              erhältlich bei der Pinnacle Entertainment Group unter
              www.peginc.com. Savage Worlds und alle zugehörigen Logos und
              Warenzeichen sind urheberrechtlich geschützt durch die Pinnacle
              Entertainment Group. Verwendung mit Genehmigung. Die deutsche
              Übersetzung der Begrifflichkeiten von Ulisses Spiele darf verwendet
              werden. Pinnacle oder Ulisses Spiele geben keine Zusicherungen oder
              Garantien in Bezug auf die Qualität, Funktionsfähigkeit oder
              Eignung dieses Produkts für einen bestimmten Zweck."
            </p>
            <p class="text-medium-emphasis">
              „This game references the Savage Worlds game system, available from
              Pinnacle Entertainment Group at www.peginc.com. Savage Worlds and
              all associated logos and trademarks are copyrights of Pinnacle
              Entertainment Group. Used with permission. Pinnacle makes no
              representation or warranty as to the quality, viability, or
              suitability for purpose of this product."
            </p>
          </v-card-text>
        </v-card>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">Danksagungen</v-card-title>
          <v-card-text>
            <p class="mb-2">Vielen Dank an Ulisses Spiele für die Genehmigung der App.</p>
            <p class="mb-2">
              Danke an die Pinnacle Entertainment Group für dieses großartige
              Rollenspiel und an Ulisses Spiele für die Übersetzung ins Deutsche.
            </p>
            <p class="mb-2">
              Besonderer Dank gilt allen Testusern, die fleißig Bugs gesammelt
              und tolle Anregungen geliefert haben.
            </p>
            <p class="mb-0">
              Danke an alle Savage-Fans, die dem Spiel Leben einhauchen.
            </p>
          </v-card-text>
        </v-card>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">Links</v-card-title>
          <v-card-text>
            <v-list density="comfortable" bg-color="transparent">
              <v-list-item
                v-for="link in links"
                :key="link.url"
                :href="link.url"
                :target="link.url.startsWith('mailto:') ? undefined : '_blank'"
                rel="noopener noreferrer"
                :prepend-icon="link.icon"
                :title="link.label"
              />
            </v-list>
          </v-card-text>
        </v-card>

        <div class="text-center">
          <v-btn variant="text" to="/impressum" class="mx-1">Impressum</v-btn>
          <v-btn variant="text" to="/datenschutz" class="mx-1">Datenschutz</v-btn>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
const logoUrl = '/assets/savage-worlds-fanprodukt-logo.png'
const appVersion = '0.1.0'

const links = [
  {
    label: 'Feedback senden: Thallion81@gmail.com',
    url: 'mailto:Thallion81@gmail.com',
    icon: 'mdi-email',
  },
  {
    label: 'Original-App im Google Play Store',
    url: 'https://play.google.com/store/apps/details?id=com.github.thallion.savageworlds',
    icon: 'mdi-google-play',
  },
  {
    label: 'Ulisses E-Book-Store',
    url: 'https://www.ulisses-ebooks.de/browse.php?sort=4a&src=fid45795&filters=45795_0_0',
    icon: 'mdi-book-open-variant',
  },
  {
    label: 'Pinnacle Entertainment Group',
    url: 'https://www.peginc.com',
    icon: 'mdi-web',
  },
  {
    label: 'Savage Worlds Deutschland',
    url: 'https://ulisses-spiele.de/game-system/savage-worlds/',
    icon: 'mdi-web',
  },
]
</script>

<style scoped>
.sw-fanlogo {
  filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.35));
}
</style>
