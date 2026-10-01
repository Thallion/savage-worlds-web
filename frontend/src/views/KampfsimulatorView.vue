<template>
  <v-container fluid class="kampf">
    <!-- Kopf: Titel, Rundenstand und Ablaufsteuerung -->
    <v-row class="mb-2" align="center">
      <v-col cols="12" md="">
        <h1 class="text-h4">Kampfsimulator</h1>
      </v-col>
      <v-col cols="12" md="auto" class="d-flex flex-wrap align-center ga-2">
        <v-chip variant="tonal" prepend-icon="mdi-cards-playing-outline">
          {{ kampf.kampfLaeuft ? `Runde ${kampf.runde}` : 'Vorbereitung' }},
          {{ kampf.stapel.anzahlVerbleibend }} {{ kampf.stapel.anzahlVerbleibend === 1 ? 'Karte' : 'Karten' }} im Stapel
        </v-chip>
        <template v-if="kampf.kampfLaeuft">
          <v-btn color="primary" prepend-icon="mdi-skip-next" :disabled="!!kampf.offenerSchaden" @click="kampf.naechsterZug()">
            Nächster Zug
          </v-btn>
          <v-btn variant="tonal" prepend-icon="mdi-flag-checkered" @click="kampf.beendeKampf()">Kampf beenden</v-btn>
        </template>
        <v-btn
          v-else
          color="primary"
          prepend-icon="mdi-sword-cross"
          :disabled="kampf.kaempfer.length < 2"
          @click="kampf.starteKampf()"
        >
          Kampf starten
        </v-btn>
      </v-col>
    </v-row>

    <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>

    <v-row>
      <!-- Linke Spalte: Kämpfer hinzufügen und verwalten -->
      <!-- Im laufenden Kampf steht der Kartentisch auf schmalen Screens oben. -->
      <v-col
        cols="12"
        md="4"
        class="d-flex flex-column ga-4"
        :class="{ 'order-last order-md-first': kampf.kampfLaeuft }"
      >
        <v-card>
          <v-card-title>Kämpfer hinzufügen</v-card-title>
          <v-tabs v-model="quelle" density="compact" show-arrows>
            <v-tab value="charakter">Charaktere</v-tab>
            <v-tab value="archetyp">Archetypen</v-tab>
            <v-tab value="kreatur">Bestiarium</v-tab>
            <v-tab value="schnell">Schnellanlage</v-tab>
          </v-tabs>
          <v-card-text>
            <v-window v-model="quelle">
              <v-window-item value="charakter">
                <v-autocomplete
                  v-model="auswahlCharakter"
                  :items="charakterOptionen"
                  label="Eigener Charakter"
                  density="compact"
                  no-data-text="Keine Charaktere vorhanden"
                />
              </v-window-item>
              <v-window-item value="archetyp">
                <v-autocomplete
                  v-model="auswahlArchetyp"
                  :items="archetypOptionen"
                  label="Archetyp"
                  density="compact"
                  no-data-text="Keine Archetypen gefunden"
                />
              </v-window-item>
              <v-window-item value="kreatur">
                <v-select
                  v-model="kreaturKategorie"
                  :items="kategorieOptionen"
                  label="Kategorie"
                  density="compact"
                />
                <v-autocomplete
                  v-model="auswahlKreatur"
                  :items="kreaturOptionen"
                  label="Kreatur"
                  density="compact"
                  no-data-text="Keine Kreaturen gefunden"
                />
                <div v-if="kreatur" class="kreatur">
                  <p class="text-body-2 text-medium-emphasis mb-2">{{ kreatur.beschreibung }}</p>
                  <div class="text-body-2 mb-1">
                    <strong>Parade</strong> {{ kreatur.parade }} ·
                    <strong>Robustheit</strong> {{ kreatur.robustheit }}<span v-if="kreatur.panzerung">
                      ({{ kreatur.panzerung }})</span
                    >
                    · <strong>Bewegungsweite</strong> {{ kreatur.bewegungsweite ?? '—' }}
                    <span v-if="kreatur.groesse"> · <strong>Größe</strong> {{ kreatur.groesse }}</span>
                  </div>
                  <div v-if="kreatur.parade_hinweis" class="text-caption text-medium-emphasis mb-1">
                    {{ kreatur.parade_hinweis }}
                  </div>
                  <div v-if="kreatur.waffen.length" class="text-body-2 mb-1">
                    <strong>Angriffe:</strong>
                    {{ kreatur.waffen.map((w) => `${w.name} (${w.schaden})`).join(', ') }}
                  </div>
                  <div v-if="kreatur.ausruestung" class="text-body-2 mb-1">
                    <strong>Ausrüstung:</strong> {{ kreatur.ausruestung }}
                  </div>
                  <div v-if="kreatur.talente.length" class="text-body-2 mb-1">
                    <strong>Talente:</strong> {{ kreatur.talente.join(', ') }}
                  </div>
                  <div v-if="kreatur.handicaps.length" class="text-body-2 mb-1">
                    <strong>Handicaps:</strong> {{ kreatur.handicaps.join(', ') }}
                  </div>
                  <v-expansion-panels v-if="kreatur.spezialfaehigkeiten.length" variant="accordion" class="mt-2">
                    <v-expansion-panel
                      :title="`Spezialfähigkeiten (${kreatur.spezialfaehigkeiten.length})`"
                    >
                      <v-expansion-panel-text>
                        <p v-for="f in kreatur.spezialfaehigkeiten" :key="f.name" class="text-body-2 mb-2">
                          <strong>{{ f.name }}:</strong> {{ f.text }}
                        </p>
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>
                  <v-alert
                    v-if="nichtSimulierteRegeln.length"
                    type="info"
                    variant="tonal"
                    density="compact"
                    class="mt-2 text-body-2"
                  >
                    Vom Simulator nicht automatisch angewendet:
                    {{ nichtSimulierteRegeln.join(', ') }}. Bitte als SL selbst berücksichtigen.
                  </v-alert>
                </div>
              </v-window-item>
              <v-window-item value="schnell">
                <v-text-field v-model="schnell.name" label="Name" density="compact" />
                <div class="text-subtitle-2 mb-1">Attribute</div>
                <div class="raster">
                  <v-select
                    v-for="name in ATTRIBUTE"
                    :key="name"
                    v-model="schnell.attribute[name]"
                    :items="WUERFEL_OPTIONEN"
                    :label="name"
                    density="compact"
                  />
                </div>
                <div class="text-subtitle-2 mb-1">Kampfwerte</div>
                <div class="raster">
                  <v-select
                    v-for="name in SCHNELL_FERTIGKEITEN"
                    :key="name"
                    v-model="schnell.fertigkeiten[name]"
                    :items="['–', ...WUERFEL_OPTIONEN]"
                    :label="name"
                    density="compact"
                  />
                  <v-text-field v-model.number="schnell.parade" type="number" label="Parade" density="compact" />
                  <v-text-field v-model.number="schnell.robustheit" type="number" label="Robustheit" density="compact" hint="ohne Panzerung" />
                  <v-text-field v-model.number="schnell.panzerung" type="number" label="Panzerung" density="compact" />
                </div>
                <div class="text-subtitle-2 mb-1">Waffe</div>
                <div class="raster">
                  <v-text-field v-model="schnell.waffeName" label="Name" density="compact" />
                  <v-text-field
                    v-model="schnell.waffeSchaden"
                    label="Schaden"
                    density="compact"
                    :error-messages="schadenFehler"
                  />
                  <v-select v-model="schnell.waffeFertigkeit" :items="SCHNELL_FERTIGKEITEN" label="Fertigkeit" density="compact" />
                  <v-text-field v-model.number="schnell.waffePb" type="number" label="PB" density="compact" />
                </div>
                <div class="text-subtitle-2 mb-1">Kampftalente und Handicaps</div>
                <v-chip-group v-model="schnell.merkmale" multiple column>
                  <v-chip
                    v-for="name in MERKMALE"
                    :key="name"
                    :value="name"
                    size="small"
                    filter
                    variant="outlined"
                  >
                    {{ name }}
                  </v-chip>
                </v-chip-group>
                <div class="text-subtitle-2 mb-1 mt-2">Spezialfähigkeiten</div>
                <div class="raster">
                  <v-text-field
                    v-model.number="schnell.widerstandsfaehig"
                    type="number"
                    min="0"
                    max="3"
                    label="Widerstandsfähig"
                    hint="Wunden, die ein Statist einstecken kann"
                    persistent-hint
                    density="compact"
                  />
                  <v-switch
                    v-model="schnell.zaeh"
                    label="Zäh"
                    color="primary"
                    density="compact"
                    hide-details
                  />
                </div>
              </v-window-item>
            </v-window>

            <v-divider class="my-3" />
            <v-btn-toggle v-model="hinzufuegen.seite" mandatory density="compact" color="primary" class="mb-3">
              <v-btn value="helden">Helden</v-btn>
              <v-btn value="gegner">Gegner</v-btn>
            </v-btn-toggle>
            <div class="raster">
              <v-switch v-model="hinzufuegen.wildcard" label="Wildcard" color="primary" density="compact" hide-details />
              <v-text-field
                v-if="!hinzufuegen.wildcard"
                v-model.number="hinzufuegen.anzahl"
                type="number"
                min="1"
                max="30"
                label="Anzahl"
                density="compact"
              />
              <v-text-field
                v-else-if="quelle === 'schnell'"
                v-model.number="schnell.bennys"
                type="number"
                min="0"
                label="Bennys"
                density="compact"
              />
            </div>
            <v-btn
              color="primary"
              prepend-icon="mdi-account-plus"
              class="mt-2"
              :loading="laedt"
              :disabled="!kannHinzufuegen"
              @click="fuegeHinzu"
            >
              Hinzufügen
            </v-btn>
          </v-card-text>
        </v-card>

        <v-card>
          <v-card-title>Im Kampf</v-card-title>
          <v-card-text>
            <p v-if="kampf.kaempfer.length === 0" class="text-medium-emphasis">Noch niemand im Kampf.</p>
            <template v-for="gruppe in statusGruppen" :key="gruppe.seite">
              <div v-if="gruppe.liste.length" class="text-subtitle-1 mt-2 mb-1">{{ gruppe.titel }}</div>
              <v-sheet
                v-for="k in gruppe.liste"
                :key="k.id"
                rounded
                border
                class="status pa-2 mb-2"
                :class="{ 'status-aus': !k.istKampffaehig }"
              >
                <div class="d-flex justify-space-between ga-2">
                  <strong>{{ k.name }}</strong>
                  <span class="text-medium-emphasis text-no-wrap">
                    Parade {{ k.aktuelleParade }}, Robustheit {{ k.gesamtRobustheit }}{{ k.gesamtPanzerung ? ` (${k.gesamtPanzerung})` : '' }}
                  </span>
                </div>
                <div class="d-flex flex-wrap align-center ga-2 mt-1">
                  <!-- Wundspur: Wildcards und widerstandsfähige Statisten. -->
                  <template v-if="k.maxWunden > 0">
                    <span class="wunden" :aria-label="`${k.wunden} von ${k.maxWunden} Wunden`">
                      <span v-for="i in k.maxWunden" :key="i" class="wunde" :class="{ 'wunde-voll': i <= k.wunden }" />
                    </span>
                    <v-btn icon="mdi-minus" size="x-small" variant="text" title="Wunde entfernen" @click="kampf.aendereWunden(k.id, -1)" />
                    <v-btn icon="mdi-plus" size="x-small" variant="text" title="Wunde hinzufügen" @click="kampf.aendereWunden(k.id, 1)" />
                  </template>
                  <v-chip v-if="!k.wildcard" size="x-small" variant="outlined">Statist</v-chip>
                  <template v-if="k.wildcard">
                    <v-spacer />
                    <v-btn icon="mdi-minus" size="x-small" variant="text" title="Benny abziehen" @click="kampf.aendereBennys(k.id, -1)" />
                    <span>{{ k.bennys }} Benny{{ k.bennys === 1 ? '' : 's' }}</span>
                    <v-btn icon="mdi-plus" size="x-small" variant="text" title="Benny hinzufügen" @click="kampf.aendereBennys(k.id, 1)" />
                  </template>
                </div>
                <div v-if="kampfMerkmale(k).length" class="text-caption text-primary">{{ kampfMerkmale(k).join(', ') }}</div>
                <div v-if="k.istWirker" class="text-caption text-medium-emphasis">
                  {{ k.arkaneFertigkeit }}: {{ k.machtpunkte }}/{{ k.maxMachtpunkte }} MP
                  <span v-if="k.erschoepfung"> · {{ ERSCHOEPFUNG_NAMEN[Math.min(k.erschoepfung, 2)] }}</span>
                </div>
                <div v-if="k.effekte.length" class="d-flex flex-wrap ga-1 mt-1">
                  <v-chip
                    v-for="e in k.effekte"
                    :key="`${e.macht}-${e.wirkerId}`"
                    size="x-small"
                    color="primary"
                    variant="tonal"
                    :title="e.beschreibung"
                  >
                    {{ e.macht }} ({{ e.verbleibend }})
                  </v-chip>
                </div>
                <div v-if="zustaende(k).length" class="d-flex flex-wrap ga-1 mt-1">
                  <v-chip
                    v-for="z in zustaende(k)"
                    :key="z.text"
                    size="x-small"
                    color="warning"
                    variant="tonal"
                    :title="z.hinweis"
                  >
                    {{ z.text }}
                  </v-chip>
                </div>
                <div class="d-flex flex-wrap ga-1 mt-1">
                  <v-chip
                    size="small"
                    :color="k.angeschlagen ? 'error' : undefined"
                    :variant="k.angeschlagen ? 'flat' : 'outlined'"
                    @click="kampf.schalteAngeschlagen(k.id)"
                  >
                    Angeschlagen
                  </v-chip>
                  <v-chip
                    v-if="k.angeschlagen && k.wildcard && k.bennys > 0"
                    size="small"
                    variant="outlined"
                    @click="kampf.bennyGegenAngeschlagen(k.id)"
                  >
                    Benny: aufheben
                  </v-chip>
                  <v-chip
                    size="small"
                    :color="k.betaeubt ? 'error' : undefined"
                    :variant="k.betaeubt ? 'flat' : 'outlined'"
                    title="Keine Aktionen, Abgelenkt und Verwundbar; Konstitutionsprobe zu Zugbeginn"
                    @click="kampf.schalteBetaeubt(k.id)"
                  >
                    Betäubt
                  </v-chip>
                  <v-chip
                    size="small"
                    :color="k.ausserGefecht ? 'error' : undefined"
                    :variant="k.ausserGefecht ? 'flat' : 'outlined'"
                    @click="kampf.schalteAusserGefecht(k.id)"
                  >
                    Außer Gefecht
                  </v-chip>
                  <v-chip size="small" variant="outlined" prepend-icon="mdi-close" @click="kampf.entferne(k.id)">
                    Entfernen
                  </v-chip>
                </div>
              </v-sheet>
            </template>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Rechte Spalte: Kartentisch, Zug, Probe, Protokoll -->
      <v-col cols="12" md="8" class="d-flex flex-column ga-4">
        <section class="tisch" aria-label="Initiative-Reihenfolge">
          <p v-if="!kampf.kampfLaeuft" class="tisch-leer">
            {{
              kampf.kaempfer.length < 2
                ? 'Füge mindestens zwei Kämpfer hinzu und starte dann den Kampf.'
                : `${kampf.kaempfer.length} Kämpfer bereit. Mit „Kampf starten" werden die Aktionskarten ausgeteilt.`
            }}
          </p>
          <ol v-else ref="reihe" class="reihe">
            <li
              v-for="(k, i) in kampf.reihenfolge"
              :key="k.id"
              class="platz"
              :class="{
                'platz-aktiv': k === aktueller,
                'platz-fertig': i < kampf.aktuellerIndex,
                'platz-aus': !k.istKampffaehig,
                'platz-held': k.seite === SEITE.HELDEN,
              }"
            >
              <div
                v-if="k.karte"
                class="karte"
                :class="{ 'karte-rot': k.karte.istRot, 'karte-joker': k.karte.joker }"
                :aria-label="k.karte.name"
              >
                <span class="karte-ecke">{{ k.karte.kuerzel }}<br />{{ k.karte.symbol }}</span>
                <span class="karte-mitte">{{ k.karte.joker ? 'Joker' : k.karte.symbol }}</span>
                <span class="karte-ecke karte-ecke-unten">{{ k.karte.kuerzel }}<br />{{ k.karte.symbol }}</span>
              </div>
              <span class="platz-name">{{ k.name }}</span>
              <span class="platz-zustand">{{ zustandText(k) }}</span>
            </li>
          </ol>
        </section>

        <!-- Aktueller Zug -->
        <v-card v-if="kampf.kampfLaeuft && aktueller">
          <v-card-text>
            <v-alert v-if="kampf.offenerSchaden" type="warning" variant="tonal" border="start" class="mb-0">
              <div class="text-h6">
                {{ kampf.offenerSchaden.ziel.name }} droht {{ offeneWunden }} Wunde{{ offeneWunden === 1 ? '' : 'n' }}
              </div>
              <p class="my-2">
                Mit einem Benny wird eine Konstitutionsprobe gewürfelt. Jeder Erfolg und jede Steigerung verhindert eine
                Wunde.
                <template v-if="kampf.offenerSchaden.versuche">
                  Bisher {{ Math.min(kampf.offenerSchaden.reduziert, kampf.offenerSchaden.wunden) }} verhindert.
                </template>
              </p>
              <div class="d-flex flex-wrap ga-2">
                <v-btn color="primary" :disabled="!kampf.offenerSchaden.ziel.bennys" @click="kampf.wegstecken()">
                  Schaden wegstecken ({{ kampf.offenerSchaden.ziel.bennys }} Benny{{ kampf.offenerSchaden.ziel.bennys === 1 ? '' : 's' }})
                </v-btn>
                <v-btn variant="tonal" @click="kampf.schadenAnnehmen()">Schaden annehmen</v-btn>
              </div>
            </v-alert>

            <template v-else>
              <div class="text-h5 mb-1">{{ aktueller.name }} ist am Zug</div>
              <p class="text-medium-emphasis mb-4">{{ zugInfo }}</p>

              <v-alert v-if="aktueller.betaeubt" type="warning" variant="tonal">
                {{ aktueller.name }} ist Betäubt: keine Aktionen, keine Bewegung, am Boden – und Verwundbar
                (+2 für Angreifer). Die Konstitutionsprobe zu Zugbeginn ist bereits gewürfelt.
              </v-alert>
              <v-alert v-else-if="!kampf.zugDarfHandeln" type="info" variant="tonal">
                {{ aktueller.name }} ist Angeschlagen und kann in diesem Zug nur freie Aktionen ausführen.
                <template v-if="aktueller.wildcard && aktueller.bennys > 0" #append>
                  <v-btn color="primary" @click="kampf.bennyGegenAngeschlagen(aktueller.id)">Benny ausgeben und handeln</v-btn>
                </template>
              </v-alert>

              <v-row v-else dense>
                <v-col cols="12" sm="6">
                  <v-select v-model="angriff.zielId" :items="zielOptionen" label="Ziel" density="compact" />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-select v-model="angriff.waffenIndex" :items="waffenOptionen" label="Waffe" density="compact" />
                </v-col>
                <v-col v-if="gewaehlteWaffe?.istNahkampf" cols="12" sm="6">
                  <v-checkbox
                    v-model="angriff.ruecksichtslos"
                    label="Rücksichtslos (+2 Angriff und Schaden, –2 Parade)"
                    density="compact"
                    hide-details
                  />
                </v-col>
                <v-col v-else cols="12" sm="6">
                  <v-select
                    v-model="angriff.reichweite"
                    :items="REICHWEITEN"
                    :label="`Reichweite${gewaehlteWaffe?.reichweite ? ` (${gewaehlteWaffe.reichweite})` : ''}`"
                    density="compact"
                  />
                </v-col>
                <v-col cols="6" sm="3">
                  <v-select v-model="angriff.aktionen" :items="AKTIONEN" label="Aktionen im Zug" density="compact" />
                </v-col>
                <v-col cols="6" sm="3">
                  <v-text-field v-model.number="angriff.modifikator" type="number" label="Situativ" density="compact" />
                </v-col>
                <v-col cols="12">
                  <v-btn color="primary" prepend-icon="mdi-sword" :disabled="!angriff.zielId" @click="greifeAn">
                    Angreifen
                  </v-btn>
                </v-col>
              </v-row>

              <!-- Mächte sind volle Aktionen: gleiche Sperren wie beim Angriff. -->
              <template v-if="aktueller.istWirker && kampf.zugDarfHandeln && !kampf.offenerSchaden">
                <v-divider class="my-3" />
                <div class="d-flex align-center ga-2 mb-2">
                  <v-icon icon="mdi-auto-fix" />
                  <strong>Macht wirken</strong>
                  <v-chip size="small" variant="outlined">
                    {{ aktueller.machtpunkte }}/{{ aktueller.maxMachtpunkte }} Machtpunkte
                  </v-chip>
                  <span class="text-caption text-medium-emphasis">volle Aktion</span>
                </div>
                <v-row dense>
                  <v-col cols="12" sm="6">
                    <v-select v-model="macht.name" :items="machtOptionen" label="Macht" density="compact" />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-select v-model="macht.zielId" :items="machtZielOptionen" label="Ziel" density="compact" />
                  </v-col>
                  <v-col v-if="gewaehlteMacht?.modifikatoren.length" cols="12">
                    <v-chip-group v-model="macht.modifikatoren" multiple column>
                      <v-chip
                        v-for="m in gewaehlteMacht.modifikatoren"
                        :key="m.name"
                        :value="m.name"
                        size="small"
                        filter
                        variant="outlined"
                        :title="m.beschreibung"
                      >
                        {{ m.name }} (+{{ m.kosten }})
                      </v-chip>
                    </v-chip-group>
                  </v-col>
                  <v-col v-if="macht.name === MACHT.ABWEHREN" cols="12" sm="6">
                    <v-select
                      v-model="macht.abwehrArt"
                      :items="ABWEHR_ARTEN"
                      label="Abzug gilt für"
                      hint="Bei einer Steigerung gilt er ohnehin für beides"
                      persistent-hint
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="6" sm="3">
                    <v-select v-model="macht.aktionen" :items="AKTIONEN" label="Aktionen im Zug" density="compact" />
                  </v-col>
                  <v-col cols="6" sm="3">
                    <v-text-field v-model.number="macht.modifikator" type="number" label="Situativ" density="compact" />
                  </v-col>
                  <v-col cols="12">
                    <p v-if="gewaehlteMacht" class="text-caption text-medium-emphasis mb-2">
                      {{ gewaehlteMacht.zusammenfassung }} — Kosten {{ machtGesamtkosten }} MP,
                      Wirkungsdauer
                      {{ gewaehlteMacht.wirkungsdauer === SOFORT ? 'Sofort' : `${gewaehlteMacht.wirkungsdauer} Runden` }}
                    </p>
                    <v-btn
                      color="primary"
                      prepend-icon="mdi-auto-fix"
                      :disabled="!macht.zielId || !macht.name || machtGesamtkosten > aktueller.machtpunkte"
                      @click="wirkeMacht"
                    >
                      Wirken
                    </v-btn>
                    <span v-if="machtGesamtkosten > aktueller.machtpunkte" class="text-caption text-error ml-2">
                      Nicht genug Machtpunkte
                    </span>
                  </v-col>
                </v-row>
              </template>
            </template>
          </v-card-text>
        </v-card>

        <v-row>
          <v-col cols="12" lg="5">
            <v-card class="h-100">
              <v-card-title>Freie Probe</v-card-title>
              <v-card-text>
                <p v-if="kampf.kaempfer.length === 0" class="text-medium-emphasis">Noch keine Kämpfer vorhanden.</p>
                <template v-else>
                  <v-select v-model="probe.kaempferId" :items="kaempferOptionen" label="Kämpfer" density="compact" />
                  <v-select v-model="probe.eigenschaft" :items="eigenschaftsOptionen" label="Eigenschaft" density="compact" />
                  <div class="raster">
                    <v-text-field v-model.number="probe.modifikator" type="number" label="Modifikator" density="compact" />
                    <v-text-field v-model.number="probe.mindestwurf" type="number" min="1" label="Mindestwurf" density="compact" />
                  </div>
                  <v-btn variant="tonal" prepend-icon="mdi-dice-multiple" @click="wuerfleProbe">Würfeln</v-btn>
                </template>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" lg="7">
            <v-card class="h-100">
              <v-card-title>Protokoll</v-card-title>
              <v-card-text>
                <ol ref="protokollListe" class="protokoll" aria-live="polite">
                  <li v-for="eintrag in kampf.protokoll" :key="eintrag.id" :class="`eintrag eintrag-${eintrag.art}`">
                    {{ eintrag.text }}
                  </li>
                </ol>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { KampfController } from '@/kampf/controller'
import {
  ATTRIBUTE,
  FERTIGKEIT,
  KAMPF_HANDICAPS,
  KAMPF_TALENTE,
  Kaempfer,
  MINDESTWURF,
  SEITE,
  Schadensformel,
  Waffe,
  Wuerfel,
  type Seite,
} from '@/kampf/domain'
import {
  ERSCHOEPFUNG_NAMEN,
  MACHT,
  SOFORT,
  machtDefinition,
  machtKosten,
  type AbwehrArt,
} from '@/kampf/maechte'
import type { BestiariumKreatur, Kampfprofil } from '@/types/charakter'

const ABWEHR_ARTEN = [
  { value: 'nahkampf' as AbwehrArt, title: 'Nahkampfangriffe' },
  { value: 'fernkampf' as AbwehrArt, title: 'Fernkampfangriffe' },
]

const ALLE_KATEGORIEN = 'Alle'
const WUERFEL_OPTIONEN = ['W4', 'W6', 'W8', 'W10', 'W12', 'W12+1', 'W12+2']
const SCHNELL_FERTIGKEITEN: string[] = [FERTIGKEIT.KAEMPFEN, FERTIGKEIT.SCHIESSEN, FERTIGKEIT.ATHLETIK]
const MERKMALE = [...KAMPF_TALENTE, ...KAMPF_HANDICAPS]
const PROBE_ZUSATZ_FERTIGKEITEN = ['Kämpfen', 'Schießen', 'Athletik', 'Wahrnehmung', 'Einschüchtern', 'Provozieren', 'Heimlichkeit']
const REICHWEITEN = [
  { value: 0, title: 'Kurz (±0)' },
  { value: -2, title: 'Mittel (–2)' },
  { value: -4, title: 'Weit (–4)' },
  { value: -8, title: 'Extrem (–8)' },
]
const AKTIONEN = [
  { value: 1, title: '1 (±0)' },
  { value: 2, title: '2 (–2)' },
  { value: 3, title: '3 (–4)' },
]

const store = useCharakterStore()

// Der Controller wird reaktiv gehalten: alle Mutationen über seine
// Methoden aktualisieren die Oberfläche automatisch.
const kampf = reactive(new KampfController()) as KampfController

const meldung = ref('')
const meldungSichtbar = ref(false)
const laedt = ref(false)
const reihe = ref<HTMLElement | null>(null)
const protokollListe = ref<HTMLElement | null>(null)

function zeigeMeldung(text: string) {
  meldung.value = text
  meldungSichtbar.value = true
}

// ---------------------------------------------------------------
// Kämpfer hinzufügen
// ---------------------------------------------------------------

type Quelle = 'charakter' | 'archetyp' | 'kreatur' | 'schnell'

const quelle = ref<Quelle>('charakter')
const auswahlCharakter = ref<number | null>(null)
const auswahlArchetyp = ref<string | null>(null)
const auswahlKreatur = ref<string | null>(null)
const kreaturKategorie = ref<string>(ALLE_KATEGORIEN)
const kreatur = ref<BestiariumKreatur | null>(null)
const hinzufuegen = reactive({ seite: SEITE.HELDEN as Seite, wildcard: true, anzahl: 1 })

const schnell = reactive({
  name: 'Ork',
  attribute: {
    Geschicklichkeit: 'W6',
    Verstand: 'W4',
    Willenskraft: 'W6',
    Stärke: 'W8',
    Konstitution: 'W8',
  } as Record<string, string>,
  fertigkeiten: { Kämpfen: 'W6', Schießen: '–', Athletik: 'W6' } as Record<string, string>,
  parade: 5,
  robustheit: 6,
  panzerung: 1,
  waffeName: 'Axt',
  waffeSchaden: 'Stä+W6',
  waffeFertigkeit: FERTIGKEIT.KAEMPFEN as string,
  waffePb: 0,
  bennys: 2,
  merkmale: [] as string[],
  widerstandsfaehig: 0,
  zaeh: false,
})

// Eigene Charaktere sind meist Helden, alles andere meist Gegner.
watch(quelle, (neu) => {
  const held = neu === 'charakter'
  hinzufuegen.seite = held ? SEITE.HELDEN : SEITE.GEGNER
  hinzufuegen.wildcard = held
  hinzufuegen.anzahl = 1
  // Beim Bestiarium gibt der Statblock vor, ob die Kreatur Wildcard ist.
  if (neu === 'kreatur' && kreatur.value) hinzufuegen.wildcard = kreatur.value.wildcard
})

// Details der gewählten Kreatur nachladen; das Buch gibt vor, ob sie
// üblicherweise Wildcard ist (Drache, Lich, Vampir ...).
watch(auswahlKreatur, async (id) => {
  if (!id) {
    kreatur.value = null
    return
  }
  try {
    kreatur.value = await store.ladeKreatur(id)
    hinzufuegen.wildcard = kreatur.value.wildcard
    hinzufuegen.anzahl = 1
  } catch {
    kreatur.value = null
    zeigeMeldung('Kreatur konnte nicht geladen werden')
  }
})

const charakterOptionen = computed(() =>
  store.liste.map((c) => ({ value: c.id, title: `${c.char_name} (${c.active_setting_name})` })),
)

const archetypOptionen = computed(() =>
  [...store.archetypen]
    .sort((a, b) => a.setting.localeCompare(b.setting) || a.name.localeCompare(b.name))
    .map((a) => ({ value: a.id, title: `${a.name} (${a.setting})` })),
)

const kategorieOptionen = computed(() => [
  ALLE_KATEGORIEN,
  ...[...new Set(store.bestiarium.map((k) => k.kategorie))].filter(Boolean).sort(),
])

const kreaturOptionen = computed(() =>
  store.bestiarium
    .filter((k) => kreaturKategorie.value === ALLE_KATEGORIEN || k.kategorie === kreaturKategorie.value)
    .map((k) => ({
      value: k.id,
      title: `${k.name}${k.wildcard ? ' (Wildcard)' : ''} – P ${k.parade} / R ${k.robustheit}`,
    })),
)

// Wechselt die Kategorie, darf die Auswahl nicht auf einer nun
// ausgeblendeten Kreatur stehen bleiben.
watch(kreaturOptionen, (optionen) => {
  if (!optionen.some((o) => o.value === auswahlKreatur.value)) auswahlKreatur.value = null
})

// Regeln, die im Statblock stehen, aber (noch) nicht vom Simulator
// ausgewertet werden – als Hinweis für die SL.
const nichtSimulierteRegeln = computed(() => {
  const k = kreatur.value
  if (!k) return []
  const regeln: string[] = []
  if (k.groesse) regeln.push(`Größe ${k.groesse > 0 ? '+' : ''}${k.groesse}`)
  const besondere = k.spezialfaehigkeiten
    .map((f) => f.name)
    .filter((n) => /^(Furchterregend|Gift|Unverwundbarkeit|Ätherisch|Schnelle Regeneration)/.test(n))
  return [...regeln, ...besondere]
})

const schadenFehler = computed(() =>
  schnell.waffeSchaden.trim() && !Schadensformel.parse(schnell.waffeSchaden)
    ? 'Nicht lesbar. Beispiele: Stä+W6, 2W8+1'
    : '',
)

const kannHinzufuegen = computed(() => {
  if (quelle.value === 'charakter') return auswahlCharakter.value !== null
  if (quelle.value === 'archetyp') return auswahlArchetyp.value !== null
  if (quelle.value === 'kreatur') return auswahlKreatur.value !== null
  return Boolean(schnell.name.trim()) && !schadenFehler.value
})

function erstelleSchnellKaempfer(): Kaempfer {
  const wuerfelMap = (map: Record<string, string>) => {
    const ergebnis: Record<string, Wuerfel> = {}
    Object.entries(map).forEach(([name, text]) => {
      const wuerfel = Wuerfel.parse(text)
      if (wuerfel) ergebnis[name] = wuerfel
    })
    return ergebnis
  }
  const waffen: Waffe[] = []
  if (schnell.waffeSchaden.trim()) {
    waffen.push(
      new Waffe({
        name: schnell.waffeName.trim() || 'Waffe',
        fertigkeit: schnell.waffeFertigkeit,
        schaden: schnell.waffeSchaden.trim(),
        pb: Number(schnell.waffePb) || 0,
      }),
    )
  }
  waffen.push(Waffe.waffenlos())
  return new Kaempfer({
    name: schnell.name.trim(),
    attribute: wuerfelMap(schnell.attribute),
    fertigkeiten: wuerfelMap(schnell.fertigkeiten),
    parade: Number(schnell.parade) || 2,
    robustheit: Number(schnell.robustheit) || 4,
    panzerung: Number(schnell.panzerung) || 0,
    waffen,
    talente: schnell.merkmale.filter((m) => KAMPF_TALENTE.includes(m)),
    handicaps: schnell.merkmale.filter((m) => KAMPF_HANDICAPS.includes(m)),
    bennys: Number(schnell.bennys) || 0,
    widerstandsfaehig: Number(schnell.widerstandsfaehig) || 0,
    zaeh: schnell.zaeh,
  })
}

async function ladeKaempfer(): Promise<Kaempfer> {
  if (quelle.value === 'schnell') return erstelleSchnellKaempfer()
  let profil: Kampfprofil
  if (quelle.value === 'charakter') profil = await store.ladeKampfprofilCharakter(auswahlCharakter.value!)
  else if (quelle.value === 'kreatur') profil = await store.ladeKampfprofilKreatur(auswahlKreatur.value!)
  else profil = await store.ladeKampfprofilArchetyp(auswahlArchetyp.value!)
  return Kaempfer.ausDaten(profil)
}

async function fuegeHinzu() {
  laedt.value = true
  try {
    const kaempfer = await ladeKaempfer()
    kaempfer.seite = hinzufuegen.seite
    kaempfer.wildcard = hinzufuegen.wildcard
    if (!kaempfer.wildcard) kaempfer.bennys = 0
    const anzahl = kaempfer.wildcard ? 1 : Math.min(30, Math.max(1, Number(hinzufuegen.anzahl) || 1))
    kampf.fuegeHinzu(kaempfer, anzahl)
  } catch (e) {
    zeigeMeldung(e instanceof Error ? e.message : 'Kämpfer konnte nicht geladen werden')
  } finally {
    laedt.value = false
  }
}

// ---------------------------------------------------------------
// Aktueller Zug und Angriff
// ---------------------------------------------------------------

const aktueller = computed(() => kampf.aktueller)

const angriff = reactive({
  zielId: '',
  waffenIndex: 0,
  reichweite: 0,
  aktionen: 1,
  modifikator: 0,
  ruecksichtslos: false,
})

const zielOptionen = computed(() => {
  const k = aktueller.value
  if (!k) return []
  return kampf.moeglicheZiele(k).map((z) => ({
    value: z.id,
    title: `${z.name} (Parade ${z.aktuelleParade}, Robustheit ${z.gesamtRobustheit}${z.panzerung ? ` inkl. ${z.panzerung}` : ''})`,
  }))
})

const waffenOptionen = computed(() =>
  (aktueller.value?.waffen ?? []).map((w, i) => ({
    value: i,
    title: `${w.name} – ${w.fertigkeit}, ${w.schaden}${w.pb ? `, PB ${w.pb}` : ''}`,
  })),
)

const gewaehlteWaffe = computed(() => aktueller.value?.waffen[angriff.waffenIndex] ?? null)

// ---------------------------------------------------------------
// Mächte (volle Aktion)
// ---------------------------------------------------------------

const macht = reactive({
  name: '',
  zielId: '',
  aktionen: 1,
  modifikator: 0,
  modifikatoren: [] as string[],
  abwehrArt: 'nahkampf' as AbwehrArt,
})

// Nur Mächte anbieten, die der Simulator auch auswerten kann.
const machtOptionen = computed(() =>
  (aktueller.value?.maechte ?? [])
    .filter((n) => machtDefinition(n))
    .map((n) => ({ value: n, title: `${n} (${machtDefinition(n)!.kosten} MP)` })),
)

const gewaehlteMacht = computed(() => (macht.name ? machtDefinition(macht.name) : null))

const machtGesamtkosten = computed(() =>
  gewaehlteMacht.value ? machtKosten(gewaehlteMacht.value, macht.modifikatoren) : 0,
)

const machtZielOptionen = computed(() => {
  const k = aktueller.value
  if (!k || !macht.name) return []
  return kampf.moeglicheMachtZiele(k, macht.name).map((z) => ({
    value: z.id,
    title: z === k ? `${z.name} (selbst)` : z.name,
  }))
})

// Machtwechsel: Modifikatoren verwerfen und ein passendes Ziel vorwählen.
watch(
  () => macht.name,
  () => {
    macht.modifikatoren = []
    const optionen = machtZielOptionen.value
    if (!optionen.some((o) => o.value === macht.zielId)) macht.zielId = optionen[0]?.value ?? ''
  },
)

function wirkeMacht() {
  kampf.wirkeMacht(aktueller.value!.id, macht.name, macht.zielId, {
    modifikator: Number(macht.modifikator) || 0,
    aktionen: macht.aktionen,
    modifikatoren: [...macht.modifikatoren],
    abwehrArt: macht.abwehrArt,
  })
}

const zugInfo = computed(() => {
  const k = aktueller.value
  if (!k || !k.karte) return ''
  return [
    `${k.karte.name}${k.hatJoker ? ' (+2 auf alle Würfe)' : ''}`,
    `Parade ${k.aktuelleParade}`,
    `Robustheit ${k.gesamtRobustheit}`,
    k.wildcard ? `${k.bennys} Benny${k.bennys === 1 ? '' : 's'}` : '',
    k.wundmalus ? `Wundmalus ${k.wundmalus}` : '',
  ]
    .filter(Boolean)
    .join(', ')
})

const offeneWunden = computed(() => {
  const o = kampf.offenerSchaden
  return o ? Math.max(0, o.wunden - o.reduziert) : 0
})

// Bei jedem Zugwechsel: Ziel auf die Gegenseite setzen, Optionen zurücksetzen.
watch(
  () => [kampf.runde, kampf.aktuellerIndex, kampf.aktueller?.id] as const,
  ([, , id]) => {
    const k = kampf.aktueller
    if (!id || !k) return
    const ziele = kampf.moeglicheZiele(k)
    const gegner = ziele.find((z) => z.seite !== k.seite) ?? ziele[0]
    angriff.zielId = gegner?.id ?? ''
    angriff.waffenIndex = 0
    angriff.ruecksichtslos = false
    angriff.aktionen = 1
    macht.name = machtOptionen.value[0]?.value ?? ''
    macht.aktionen = 1
    macht.modifikator = 0
    macht.modifikatoren = []
    probe.kaempferId = id
    nextTick(() => reihe.value?.querySelector('.platz-aktiv')?.scrollIntoView({ block: 'nearest', inline: 'center' }))
  },
)

// Fällt das gewählte Ziel aus, auf ein anderes kampffähiges Ziel wechseln.
watch(zielOptionen, (optionen) => {
  if (!optionen.some((o) => o.value === angriff.zielId)) {
    const k = kampf.aktueller
    const gegner = k ? kampf.moeglicheZiele(k).find((z) => z.seite !== k.seite) : undefined
    angriff.zielId = gegner?.id ?? optionen[0]?.value ?? ''
  }
})

function greifeAn() {
  const k = kampf.aktueller
  if (!k) return
  kampf.angriff(k.id, angriff.zielId, angriff.waffenIndex, {
    modifikator: Number(angriff.modifikator) || 0,
    aktionen: angriff.aktionen,
    reichweite: angriff.reichweite,
    ruecksichtslos: angriff.ruecksichtslos,
  })
}

// ---------------------------------------------------------------
// Freie Probe
// ---------------------------------------------------------------

const probe = reactive({ kaempferId: '', eigenschaft: '', modifikator: 0, mindestwurf: MINDESTWURF })

const kaempferOptionen = computed(() => kampf.kaempfer.map((k) => ({ value: k.id, title: k.name })))

const eigenschaftsOptionen = computed(() => {
  const k = kampf.finde(probe.kaempferId)
  if (!k) return []
  const eigene = Object.keys(k.fertigkeiten).sort((a, b) => a.localeCompare(b))
  return [
    ...ATTRIBUTE.map((n) => ({ value: n, title: `${n} ${k.wuerfelFuer(n).wuerfel}` })),
    ...eigene.map((n) => ({ value: n, title: `${n} ${k.fertigkeiten[n]}` })),
    ...PROBE_ZUSATZ_FERTIGKEITEN.filter((n) => !eigene.includes(n)).map((n) => ({ value: n, title: `${n} (ungeübt)` })),
  ]
})

watch(kaempferOptionen, (optionen) => {
  if (!optionen.some((o) => o.value === probe.kaempferId)) probe.kaempferId = optionen[0]?.value ?? ''
})

watch(eigenschaftsOptionen, (optionen) => {
  if (!optionen.some((o) => o.value === probe.eigenschaft)) probe.eigenschaft = optionen[0]?.value ?? ''
})

function wuerfleProbe() {
  kampf.probe(probe.kaempferId, probe.eigenschaft, Number(probe.modifikator) || 0, Number(probe.mindestwurf) || MINDESTWURF)
}

// ---------------------------------------------------------------
// Status und Protokoll
// ---------------------------------------------------------------

const statusGruppen = computed(() => [
  { seite: SEITE.HELDEN, titel: 'Helden', liste: kampf.kaempfer.filter((k) => k.seite === SEITE.HELDEN) },
  { seite: SEITE.GEGNER, titel: 'Gegner', liste: kampf.kaempfer.filter((k) => k.seite === SEITE.GEGNER) },
])

function kampfMerkmale(k: Kaempfer): string[] {
  const merkmale = [...k.talente, ...k.handicaps].filter((m) => MERKMALE.includes(m))
  if (k.widerstandsfaehig) merkmale.push('Widerstandsfähig')
  if (k.zaeh) merkmale.push('Zäh')
  return merkmale
}

/** Abgelenkt/Verwundbar als eigene Chips — sie laufen zugweise ab. */
function zustaende(k: Kaempfer): { text: string; hinweis: string }[] {
  const liste: { text: string; hinweis: string }[] = []
  if (k.istAbgelenkt) liste.push({ text: 'Abgelenkt –2', hinweis: '–2 auf alle Eigenschaftsproben bis zum Ende des nächsten Zuges' })
  if (k.istVerwundbar) liste.push({ text: 'Verwundbar +2', hinweis: 'Angriffe gegen diesen Kämpfer erhalten +2' })
  return liste
}

function zustandText(k: Kaempfer): string {
  if (!k.istKampffaehig) return 'Außer Gefecht'
  const teile: string[] = []
  if (k.wunden) teile.push(`${k.wunden} Wunde${k.wunden > 1 ? 'n' : ''}`)
  if (k.betaeubt) teile.push('Betäubt')
  if (k.angeschlagen) teile.push('Angeschlagen')
  return teile.join(', ')
}

watch(
  () => kampf.protokoll.length,
  () =>
    nextTick(() => {
      const el = protokollListe.value
      if (el) el.scrollTop = el.scrollHeight
    }),
)

onMounted(async () => {
  try {
    await Promise.all([
      store.liste.length ? Promise.resolve() : store.ladeListe(),
      store.archetypen.length ? Promise.resolve() : store.ladeArchetypen(),
      store.bestiarium.length ? Promise.resolve() : store.ladeBestiarium(),
    ])
  } catch {
    zeigeMeldung('Charaktere, Archetypen oder Bestiarium konnten nicht geladen werden')
  }
})
</script>

<style scoped>
.raster {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
  column-gap: 0.75rem;
}

/* ---------- Kartentisch ---------- */

.tisch {
  background:
    radial-gradient(ellipse at 50% 0%, rgba(255, 255, 255, 0.12), transparent 70%),
    rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  border-radius: 8px;
  padding: 1rem;
  min-height: 12rem;
  box-shadow: inset 0 0 0 2px rgba(0, 0, 0, 0.15);
}

.tisch-leer {
  margin: 0;
  opacity: 0.9;
}

.reihe {
  list-style: none;
  margin: 0;
  padding: 0.5rem 0.25rem 0.5rem;
  display: flex;
  gap: 0.9rem;
  overflow-x: auto;
}

.platz {
  flex: 0 0 auto;
  width: 6.5rem;
  display: grid;
  justify-items: center;
  gap: 0.3rem;
  text-align: center;
}

.platz-fertig .karte,
.platz-fertig .platz-name {
  opacity: 0.55;
}

.platz-aus {
  opacity: 0.35;
}

.platz-aus .karte {
  filter: grayscale(1);
}

.platz-name {
  font-family: var(--sw-font-titel);
  font-weight: 600;
  font-size: 0.9rem;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.platz-held .platz-name {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.platz-zustand {
  font-size: 0.8rem;
  min-height: 1.1em;
  font-weight: 600;
}

.karte {
  position: relative;
  width: 5.25rem;
  aspect-ratio: 5 / 7;
  background: #fbfaf7;
  border: 1px solid #d9d4c7;
  border-radius: 10px;
  color: #1e1b18;
  font-family: var(--sw-font-titel);
  box-shadow: 0 3px 0 rgba(0, 0, 0, 0.25);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.karte-rot {
  color: #b3261e;
}

.karte-ecke {
  position: absolute;
  top: 0.3rem;
  left: 0.4rem;
  font-size: 0.95rem;
  font-weight: 700;
  line-height: 1;
  text-align: center;
}

.karte-ecke-unten {
  top: auto;
  left: auto;
  bottom: 0.3rem;
  right: 0.4rem;
  transform: rotate(180deg);
}

.karte-mitte {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 2.2rem;
}

.karte-joker {
  background: linear-gradient(160deg, #fbfaf7 55%, #e3c98e);
}

.karte-joker .karte-mitte {
  font-size: 1.05rem;
  font-weight: 700;
}

.platz-aktiv .karte {
  transform: translateY(-0.5rem);
  box-shadow: 0 0 0 3px #e3c98e, 0 10px 18px rgba(0, 0, 0, 0.35);
}

/* ---------- Status ---------- */

.status-aus {
  opacity: 0.55;
}

.wunden {
  display: inline-flex;
  gap: 0.25rem;
}

.wunde {
  width: 0.8rem;
  height: 0.8rem;
  border-radius: 50%;
  border: 2px solid rgb(var(--v-theme-error));
}

.wunde-voll {
  background: rgb(var(--v-theme-error));
}

/* ---------- Protokoll ---------- */

.protokoll {
  list-style: none;
  margin: 0;
  padding: 0 0.25rem 0 0;
  max-height: 28rem;
  overflow-y: auto;
  display: grid;
  gap: 0.3rem;
  font-size: 0.95rem;
}

.eintrag {
  padding-left: 0.6rem;
  border-left: 3px solid rgba(var(--v-border-color), var(--v-border-opacity));
  overflow-wrap: anywhere;
}

.eintrag-runde {
  border-left: none;
  padding: 0.5rem 0 0;
  font-family: var(--sw-font-titel);
  font-weight: 600;
  color: rgb(var(--v-theme-primary));
}

.eintrag-zug {
  border-left-color: rgb(var(--v-theme-primary));
  font-weight: 600;
  margin-top: 0.25rem;
}

.eintrag-erfolg {
  border-left-color: rgb(var(--v-theme-success));
}

.eintrag-fehlschlag {
  border-left-color: rgb(var(--v-theme-warning));
  opacity: 0.8;
}

.eintrag-schaden {
  border-left-color: rgb(var(--v-theme-error));
  color: rgb(var(--v-theme-error));
  font-weight: 600;
}

.eintrag-warnung {
  border-left-color: rgb(var(--v-theme-warning));
  color: rgb(var(--v-theme-warning));
}

@media (prefers-reduced-motion: reduce) {
  .karte {
    transition: none;
  }
}
</style>
