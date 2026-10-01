/**
 * Kampfsimulator – Mächte (SWADE, Kapitel 5).
 *
 * Reine Datenschicht: Katalog der implementierten Mächte und die Form der
 * aktiven Effekte. Keine Abhängigkeit zu Kaempfer/Controller, damit die
 * Domain in eine Richtung importieren kann.
 *
 * Regelgrundlage (S. 150 f.):
 * - Jede Macht wird mit einer **eigenen Aktion** aktiviert; mehrere Mächte
 *   in einem Zug sind eine Mehrfachaktion (–2 je zusätzlicher Aktion).
 *   Angeschlagene können keine Mächte wirken (nur freie Aktionen).
 * - Wurf auf die arkane Fertigkeit gegen MW 4.
 * - Unter 4: Macht wird nicht aktiviert, **1 Machtpunkt ist trotzdem weg**.
 * - 4+: Macht aktiviert, alle zugeteilten Machtpunkte werden verbraucht –
 *   auch wenn das Ziel verfehlt wird (Geschoss) oder widersteht.
 * - Kritischer Fehlschlag: Rückschlag → eine Stufe Erschöpfung und alle
 *   eigenen aktiven Mächte enden.
 * - Wirkungsdauer zählt die Runde der Aktivierung mit.
 */

/** Wirkungsdauer „Sofort“. */
export const SOFORT = 0

/** Mächte werden gegen MW 4 gewirkt – wie eine normale Probe. */
export const MACHT_MINDESTWURF = 4

/** Bei Misserfolg ist mindestens dieser eine Machtpunkt verbraucht. */
export const MINDESTKOSTEN = 1

/** Rückschlag verursacht eine Stufe Erschöpfung. */
export const RUECKSCHLAG_ERSCHOEPFUNG = 1

export type MachtZiel = 'gegner' | 'verbuendeter' | 'selbst_oder_verbuendeter'
export type MachtTyp = 'angriff' | 'effekt' | 'heilung' | 'widerstand'
export type AbwehrArt = 'nahkampf' | 'fernkampf'

export const MACHT = {
  GESCHOSS: 'Geschoss',
  SCHUTZ: 'Schutz',
  ABWEHREN: 'Abwehren',
  WAFFE_VERBESSERN: 'Waffe verbessern',
  HEILUNG: 'Heilung',
  BETAEUBEN: 'Betäuben',
} as const

/** Abzug auf die Konstitutionsprobe, wenn der Wirker eine Steigerung erzielt. */
export const BETAEUBEN_STEIGERUNG_MALUS = 2

export interface MachtModifikator {
  name: string
  kosten: number
  beschreibung: string
}

export interface MachtDefinition {
  name: string
  typ: MachtTyp
  rang: string
  kosten: number
  reichweite: string
  /** In Runden; SOFORT für Wirkungsdauer „Sofort“. */
  wirkungsdauer: number
  ziel: MachtZiel
  zusammenfassung: string
  modifikatoren: MachtModifikator[]
}

/** Werte, die ein aktiver Effekt an seinem Träger verändert. */
export interface EffektWerte {
  /** Zusätzliche Panzerung (Schutz). */
  panzerung?: number
  /** Zusätzliche Robustheit (Schutz mit Steigerung). */
  robustheit?: number
  /** Zusätzlicher Waffenschaden (Waffe verbessern). */
  schaden?: number
  /** Abzug, den Angreifer im Nahkampf gegen den Träger erleiden (Abwehren). */
  abwehrNahkampf?: number
  /** Abzug, den Angreifer im Fernkampf gegen den Träger erleiden (Abwehren). */
  abwehrFernkampf?: number
}

export interface AktiverEffekt extends EffektWerte {
  macht: string
  /** Wer die Macht gewirkt hat – bei Rückschlag enden dessen Effekte. */
  wirkerId: string
  /** Verbleibende Runden; wird zu Rundenbeginn heruntergezählt. */
  verbleibend: number
  beschreibung: string
}

const ZUSAETZLICHE_EMPFAENGER: MachtModifikator = {
  name: 'Zusätzliche Empfänger',
  kosten: 1,
  beschreibung: 'Ein weiteres Ziel je zusätzlichem Machtpunkt (hier: nicht simuliert).',
}

export const MAECHTE: Record<string, MachtDefinition> = {
  [MACHT.GESCHOSS]: {
    name: MACHT.GESCHOSS,
    typ: 'angriff',
    rang: 'Anfänger',
    kosten: 1,
    reichweite: 'Verstand ×2',
    wirkungsdauer: SOFORT,
    ziel: 'gegner',
    zusammenfassung: 'Fernkampfangriff mit 2W6 Schaden, 3W6 mit Steigerung. Keine Entfernungsabzüge.',
    modifikatoren: [
      { name: 'Schaden', kosten: 2, beschreibung: '3W6 Schaden (4W6 bei einer Steigerung).' },
      { name: 'Panzerbrechend', kosten: 1, beschreibung: 'PB 2.' },
    ],
  },
  [MACHT.SCHUTZ]: {
    name: MACHT.SCHUTZ,
    typ: 'effekt',
    rang: 'Anfänger',
    kosten: 1,
    reichweite: 'Verstand',
    wirkungsdauer: 5,
    ziel: 'selbst_oder_verbuendeter',
    zusammenfassung: 'Panzerung +2; mit Steigerung stattdessen Robustheit +2.',
    modifikatoren: [ZUSAETZLICHE_EMPFAENGER],
  },
  [MACHT.ABWEHREN]: {
    name: MACHT.ABWEHREN,
    typ: 'effekt',
    rang: 'Anfänger',
    kosten: 3,
    reichweite: 'Verstand',
    wirkungsdauer: 5,
    ziel: 'selbst_oder_verbuendeter',
    zusammenfassung:
      'Feinde ziehen –2 von Nahkampf- oder Fernkampfangriffen (Wahl des Wirkers) gegen das Ziel ab; bei einer Steigerung von beidem.',
    modifikatoren: [ZUSAETZLICHE_EMPFAENGER],
  },
  [MACHT.WAFFE_VERBESSERN]: {
    name: MACHT.WAFFE_VERBESSERN,
    typ: 'effekt',
    rang: 'Anfänger',
    kosten: 2,
    reichweite: 'Verstand',
    wirkungsdauer: 5,
    ziel: 'selbst_oder_verbuendeter',
    zusammenfassung: 'Waffenschaden +2, mit Steigerung +4.',
    modifikatoren: [ZUSAETZLICHE_EMPFAENGER],
  },
  [MACHT.BETAEUBEN]: {
    name: MACHT.BETAEUBEN,
    typ: 'widerstand',
    rang: 'Anfänger',
    kosten: 2,
    reichweite: 'Verstand',
    wirkungsdauer: SOFORT,
    ziel: 'gegner',
    zusammenfassung:
      'Das Opfer legt eine Konstitutionsprobe ab (–2 bei einer Steigerung des Wirkers), um nicht Betäubt zu werden.',
    modifikatoren: [
      {
        name: 'Flächeneffekt',
        kosten: 2,
        beschreibung: 'Alle in einer mittleren Flächenschablone (+3 für eine große) – hier: nicht simuliert.',
      },
    ],
  },
  [MACHT.HEILUNG]: {
    name: MACHT.HEILUNG,
    typ: 'heilung',
    rang: 'Anfänger',
    kosten: 3,
    reichweite: 'Berührung',
    wirkungsdauer: SOFORT,
    ziel: 'selbst_oder_verbuendeter',
    zusammenfassung: 'Heilt eine Wunde, mit Steigerung zwei (nur Wunden unter einer Stunde).',
    modifikatoren: [],
  },
}

export const MACHT_NAMEN: readonly string[] = Object.keys(MAECHTE)

export function machtDefinition(name: string): MachtDefinition | null {
  return MAECHTE[name] ?? null
}

/** Gesamtkosten inklusive gewählter Machtmodifikatoren. */
export function machtKosten(macht: MachtDefinition, modifikatoren: readonly string[] = []): number {
  return macht.modifikatoren
    .filter((m) => modifikatoren.includes(m.name))
    .reduce((summe, m) => summe + m.kosten, macht.kosten)
}

/**
 * Schadensformel für Geschoss. Die Steigerung erhöht hier die Würfelzahl,
 * statt wie bei Waffen einen Bonuswürfel zu addieren.
 */
export function geschossSchaden(steigerung: boolean, verstaerkt: boolean): string {
  if (verstaerkt) return steigerung ? '4W6' : '3W6'
  return steigerung ? '3W6' : '2W6'
}

/** Erschöpfungsstufen: –1 je Stufe auf alle Eigenschaftsproben. */
export const ERSCHOEPFUNG_NAMEN = ['', 'Erschöpft', 'Entkräftet'] as const
export const MAX_ERSCHOEPFUNG = 3
