<template>
  <v-container class="py-8">
    <v-row justify="center">
      <v-col cols="12" md="8" lg="7">
        <h1 class="text-h4 mb-6">Impressum</h1>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">Angaben gemäß § 5 DDG</v-card-title>
          <v-card-text>
            <p class="mb-1">Jean-Michel Fenske</p>
            <p class="mb-1">Fahrner Straße 167</p>
            <p class="mb-0">47169 Duisburg</p>
          </v-card-text>
        </v-card>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">Kontakt</v-card-title>
          <v-card-text>
            <p class="mb-0">
              E-Mail:
              <a href="mailto:Thallion81@gmail.com">Thallion81@gmail.com</a>
            </p>
          </v-card-text>
        </v-card>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">
            Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV
          </v-card-title>
          <v-card-text>
            <p class="mb-1">Jean-Michel Fenske</p>
            <p class="mb-1">Fahrner Straße 167</p>
            <p class="mb-0">47169 Duisburg</p>
          </v-card-text>
        </v-card>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">Haftungsausschluss</v-card-title>
          <v-card-text>
            <p class="mb-4">
              Dies ist ein nicht-kommerzielles, privates Fan-Projekt. Die Inhalte
              dieser Anwendung wurden mit größtmöglicher Sorgfalt erstellt. Für die
              Richtigkeit, Vollständigkeit und Aktualität der Inhalte kann jedoch
              keine Gewähr übernommen werden.
            </p>
            <p class="mb-4">
              Diese Anwendung enthält Links zu externen Websites Dritter, auf deren
              Inhalte kein Einfluss besteht. Deshalb kann für diese fremden Inhalte
              auch keine Gewähr übernommen werden. Für die Inhalte der verlinkten
              Seiten ist stets der jeweilige Anbieter oder Betreiber der Seiten
              verantwortlich.
            </p>
            <p class="mb-0">
              Savage Worlds Fan-Produkt: Dieses Produkt bezieht sich auf das
              Regelsystem Savage Worlds der Pinnacle Entertainment Group
              (www.peginc.com). Savage Worlds und alle zugehörigen Logos und
              Warenzeichen sind urheberrechtlich geschützt durch die Pinnacle
              Entertainment Group. Verwendung mit Genehmigung.
            </p>
          </v-card-text>
        </v-card>

        <div class="text-center">
          <v-btn variant="text" to="/info" class="mx-1">Info</v-btn>
          <v-btn variant="text" to="/datenschutz" class="mx-1">Datenschutz</v-btn>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts"></script>
