<template>
  <v-container class="py-8">
    <v-row justify="center">
      <v-col cols="12" md="8" lg="7">
        <h1 class="text-h4 mb-6">Datenschutzerklärung</h1>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">1. Verantwortlicher</v-card-title>
          <v-card-text>
            <p class="mb-1">Jean-Michel Fenske</p>
            <p class="mb-1">Fahrner Straße 167</p>
            <p class="mb-1">47169 Duisburg</p>
            <p class="mb-0">
              E-Mail:
              <a href="mailto:Thallion81@gmail.com">Thallion81@gmail.com</a>
            </p>
          </v-card-text>
        </v-card>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">2. Überblick</v-card-title>
          <v-card-text>
            <p class="mb-0">
              Diese Anwendung ist ein nicht-kommerzielles Fan-Projekt zur
              Erstellung von Savage-Worlds-Charakteren. Wir verarbeiten nur
              die Daten, die für den Betrieb des Dienstes technisch erforderlich
              sind. Es findet <strong>kein Tracking</strong> statt, es werden
              <strong>keine Analyse- oder Werbedienste</strong> eingesetzt und
              es werden <strong>keine Daten zu Werbezwecken an Dritte
              weitergegeben</strong>.
            </p>
          </v-card-text>
        </v-card>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">3. Benutzerkonto</v-card-title>
          <v-card-text>
            <p class="mb-4">
              Zur Nutzung des Charakter-Generators legen Sie ein Benutzerkonto an.
              Dabei verarbeiten wir folgende Daten:
            </p>
            <ul class="mb-4  pl-6">
              <li>E-Mail-Adresse</li>
              <li>Benutzername</li>
              <li>Passwort (ausschließlich als kryptografischer Hash gespeichert, niemals im Klartext)</li>
              <li>Zeitpunkt der Kontoerstellung</li>
            </ul>
            <p class="mb-2">
              <strong>Zweck:</strong> Bereitstellung des Benutzerkontos,
              Authentifizierung und Zuordnung Ihrer gespeicherten Charaktere.
            </p>
            <p class="mb-0">
              <strong>Rechtsgrundlage:</strong> Art. 6 Abs. 1 lit. b DSGVO
              (Erfüllung des Nutzungsvertrags).
            </p>
          </v-card-text>
        </v-card>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">4. Charakter- und Inhaltsdaten</v-card-title>
          <v-card-text>
            <p class="mb-2">
              Von Ihnen erstellte Charaktere, Ordner und eigene Settings werden auf
              dem Server gespeichert und ausschließlich Ihrem Konto zugeordnet.
              Andere Nutzer haben keinen Zugriff auf Ihre Charaktere.
            </p>
            <p class="mb-0">
              <strong>Rechtsgrundlage:</strong> Art. 6 Abs. 1 lit. b DSGVO
              (Erfüllung des Nutzungsvertrags).
            </p>
          </v-card-text>
        </v-card>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">5. Local Storage im Browser</v-card-title>
          <v-card-text>
            <p class="mb-0">
              Nach der Anmeldung wird ein Anmelde-Token (JWT) im lokalen Speicher
              (Local Storage) Ihres Browsers abgelegt, damit Sie angemeldet bleiben.
              Zusätzlich werden Ihre Anzeige-Einstellungen (z.&nbsp;B. das gewählte
              Theme) lokal gespeichert. Diese Daten verbleiben in Ihrem Browser,
              werden nicht zu Analysezwecken ausgewertet und können jederzeit über
              die Abmeldung bzw. das Löschen der Browserdaten entfernt werden.
            </p>
          </v-card-text>
        </v-card>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">6. Server-Logfiles</v-card-title>
          <v-card-text>
            <p class="mb-0">
              Beim Aufruf des Dienstes können durch den Hosting-Provider technisch
              notwendige Zugriffsdaten (z.&nbsp;B. IP-Adresse, Zeitpunkt des Zugriffs,
              aufgerufene Ressource) in Server-Logfiles verarbeitet werden. Dies dient
              der technischen Bereitstellung und Sicherheit des Dienstes.
              Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse
              am sicheren Betrieb).
            </p>
          </v-card-text>
        </v-card>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">7. Speicherdauer &amp; Löschung</v-card-title>
          <v-card-text>
            <p class="mb-0">
              Ihre Konto- und Charakterdaten werden gespeichert, solange Ihr Konto
              besteht. Sie können die Löschung Ihres Kontos und der zugehörigen
              Daten jederzeit unter der oben genannten Kontaktadresse verlangen.
            </p>
          </v-card-text>
        </v-card>

        <v-card class="pa-4 mb-6" variant="tonal">
          <v-card-title class="text-h6">8. Ihre Rechte</v-card-title>
          <v-card-text>
            <p class="mb-4">Ihnen stehen nach der DSGVO folgende Rechte zu:</p>
            <ul class="mb-4 pl-6">
              <li>Auskunft (Art. 15 DSGVO)</li>
              <li>Berichtigung (Art. 16 DSGVO)</li>
              <li>Löschung (Art. 17 DSGVO)</li>
              <li>Einschränkung der Verarbeitung (Art. 18 DSGVO)</li>
              <li>Datenübertragbarkeit (Art. 20 DSGVO)</li>
              <li>Widerspruch (Art. 21 DSGVO)</li>
            </ul>
            <p class="mb-0">
              Zudem haben Sie das Recht, sich bei einer Datenschutz-Aufsichtsbehörde
              zu beschweren (Art. 77 DSGVO).
            </p>
          </v-card-text>
        </v-card>

        <div class="text-center">
          <v-btn variant="text" to="/info" class="mx-1">Info</v-btn>
          <v-btn variant="text" to="/impressum" class="mx-1">Impressum</v-btn>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts"></script>
