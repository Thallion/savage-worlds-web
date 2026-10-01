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
 *   Angeschlagene können keine Mächte wirken (nur freie Aktionen),
 *   Gebundene ebenfalls nicht (Wirkvoraussetzungen).
 * - Wurf auf die arkane Fertigkeit gegen MW 4.
 * - Unter 4: Macht wird nicht aktiviert, **1 Machtpunkt ist trotzdem weg**.
 * - 4+: Macht aktiviert, alle zugeteilten Machtpunkte werden verbraucht –
 *   auch wenn das Ziel verfehlt wird (Geschoss) oder widersteht.
 * - Kritischer Fehlschlag: Rückschlag → eine Stufe Erschöpfung und alle
 *   eigenen aktiven Mächte enden.
 * - Wirkungsdauer zählt die Runde der Aktivierung mit.
 * - Arkane Resistenz und Arkaner Schutz ziehen feindlichen Mächten 2/4
 *   Punkte ab; scheitert die Macht nur daran, ist sie trotzdem aktiviert.
 */

/** Wirkungsdauer „Sofort“. */
export const SOFORT = 0

/** Mächte werden gegen MW 4 gewirkt – wie eine normale Probe. */
export const MACHT_MINDESTWURF = 4

/** Bei Misserfolg ist mindestens dieser eine Machtpunkt verbraucht. */
export const MINDESTKOSTEN = 1

/** Rückschlag verursacht eine Stufe Erschöpfung. */
export const RUECKSCHLAG_ERSCHOEPFUNG = 1

/**
 * Wem eine Macht gilt: Gegnern, Verbündeten (inkl. Wirker) oder – bei
 * Eigenschaft erhöhen/senken – je nach gewähltem Modus beiden.
 */
export type MachtZiel = 'gegner' | 'selbst_oder_verbuendeter' | 'beliebig'
export type MachtTyp = 'angriff' | 'effekt' | 'heilung' | 'widerstand' | 'zustand'
export type AbwehrArt = 'nahkampf' | 'fernkampf'
export type EigenschaftModus = 'erhoehen' | 'senken'
export type LinderungModus = 'erholen' | 'abschwaechen'
export type VerwirrungWahl = 'abgelenkt' | 'verwundbar'

export const MACHT = {
  GESCHOSS: 'Geschoss',
  SCHUTZ: 'Schutz',
  ABWEHREN: 'Abwehren',
  WAFFE_VERBESSERN: 'Waffe verbessern',
  HEILUNG: 'Heilung',
  BETAEUBEN: 'Betäuben',
  VERWIRRUNG: 'Verwirrung',
  LINDERUNG: 'Linderung',
  BLENDEN: 'Blenden',
  EIGENSCHAFT: 'Eigenschaft erhöhen/senken',
  VERSTRICKEN: 'Verstricken',
  FLAECHENSCHLAG: 'Flächenschlag',
  STRAHL: 'Strahl',
  ARKANER_SCHUTZ: 'Arkaner Schutz',
  SCHLUMMER: 'Schlummer',
} as const

/** Namen der Machtmodifikatoren, auf die der Controller reagiert. */
export const MODIFIKATOR = {
  SCHADEN: 'Schaden',
  PB2: 'Panzerbrechend (PB 2)',
  PB4: 'Panzerbrechend (PB 4)',
  PB6: 'Panzerbrechend (PB 6)',
  FLAECHE_MITTEL: 'Flächeneffekt (MFS)',
  FLAECHE_GROSS: 'Flächeneffekt (GFS)',
  GROSSE_SCHABLONE: 'Große Flächenschablone',
  STARK: 'Stark',
  ZAEH: 'Zäh',
  BETAEUBT: 'Betäubt',
} as const

/** Abzug auf Widerstandsproben, wenn der Wirker eine Steigerung erzielt. */
export const STEIGERUNG_WIDERSTAND_MALUS = 2
/** Stark: Abzug auf die Probe, mit der das Opfer den Effekt abschüttelt. */
export const STARK_MALUS = 2
/** Linderung (Abschwächen) hält eine Stunde – im Kampf praktisch dauerhaft. */
export const EINE_STUNDE_IN_RUNDEN = 600

export interface MachtModifikator {
  name: string
  kosten: number
  beschreibung: string
  /** Modifikatoren derselben Gruppe schließen sich gegenseitig aus. */
  gruppe?: string
  /** Erlaubt mehrere Ziele (Flächeneffekt). */
  flaeche?: boolean
  /** Nur in diesem Modus wählbar (Eigenschaft senken: Stark). */
  modus?: EigenschaftModus
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
  /** Die Macht wirkt von sich aus auf eine Fläche (mehrere Ziele frei). */
  flaeche?: boolean
  /** Zusätzliche Empfänger: Kosten je weiterem Ziel. */
  empfaengerKosten?: number
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
  /** Abzug für feindliche Mächte und magischen Schaden (Arkaner Schutz). */
  arkanerSchutz?: number
  /** Ignorierte Punkte Wund- und Erschöpfungsabzug (Linderung). */
  linderung?: number
}

export interface AktiverEffekt extends EffektWerte {
  macht: string
  /** Wer die Macht gewirkt hat – bei Rückschlag enden dessen Effekte. */
  wirkerId: string
  /** Verbleibende Runden; wird zu Rundenbeginn heruntergezählt. */
  verbleibend: number
  beschreibung: string
  /** Eigenschaft erhöhen: betroffene Eigenschaft und Würfelstufen. */
  eigenschaft?: string
  stufen?: number
}

const ZUSAETZLICHE_EMPFAENGER_KOSTEN = 1

const PANZERBRECHEND: MachtModifikator[] = [
  { name: MODIFIKATOR.PB2, kosten: 1, beschreibung: 'PB 2.', gruppe: 'pb' },
  { name: MODIFIKATOR.PB4, kosten: 2, beschreibung: 'PB 4.', gruppe: 'pb' },
  { name: MODIFIKATOR.PB6, kosten: 3, beschreibung: 'PB 6.', gruppe: 'pb' },
]

const FLAECHENEFFEKT: MachtModifikator[] = [
  {
    name: MODIFIKATOR.FLAECHE_MITTEL,
    kosten: 2,
    beschreibung: 'Alle in einer mittleren Flächenschablone.',
    gruppe: 'flaeche',
    flaeche: true,
  },
  {
    name: MODIFIKATOR.FLAECHE_GROSS,
    kosten: 3,
    beschreibung: 'Alle in einer großen Flächenschablone.',
    gruppe: 'flaeche',
    flaeche: true,
  },
]

export const MAECHTE: Record<string, MachtDefinition> = {
  [MACHT.GESCHOSS]: {
    name: MACHT.GESCHOSS,
    typ: 'angriff',
    rang: 'Anfänger',
    kosten: 1,
    reichweite: 'Verstand ×2',
    wirkungsdauer: SOFORT,
    ziel: 'gegner',
    zusammenfassung:
      'Fernkampfangriff mit 2W6 Schaden, 3W6 mit Steigerung. Keine Entfernungsabzüge, aber Deckung, Beleuchtung usw. gelten.',
    modifikatoren: [
      { name: MODIFIKATOR.SCHADEN, kosten: 2, beschreibung: '3W6 Schaden (4W6 bei einer Steigerung).' },
      ...PANZERBRECHEND,
    ],
  },
  [MACHT.FLAECHENSCHLAG]: {
    name: MACHT.FLAECHENSCHLAG,
    typ: 'angriff',
    rang: 'Fortgeschritten',
    kosten: 3,
    reichweite: 'Verstand ×2',
    wirkungsdauer: SOFORT,
    ziel: 'gegner',
    flaeche: true,
    zusammenfassung:
      'Mittlere Flächenschablone (kleine kostenlos): jedes Ziel erleidet 2W6 Schaden, 3W6 bei einer Steigerung. Ausweichen und Abwehren gelten nicht.',
    modifikatoren: [
      { name: MODIFIKATOR.GROSSE_SCHABLONE, kosten: 1, beschreibung: 'Große statt mittlerer Flächenschablone.' },
      { name: MODIFIKATOR.SCHADEN, kosten: 2, beschreibung: '3W6 Schaden (4W6 bei einer Steigerung).' },
      ...PANZERBRECHEND,
    ],
  },
  [MACHT.STRAHL]: {
    name: MACHT.STRAHL,
    typ: 'angriff',
    rang: 'Anfänger',
    kosten: 2,
    reichweite: 'Kegelschablone',
    wirkungsdauer: SOFORT,
    ziel: 'gegner',
    flaeche: true,
    zusammenfassung: 'Kegel ab dem Wirker: alle Ziele darin erleiden 2W6 Schaden, 3W6 bei einer Steigerung.',
    modifikatoren: [
      { name: MODIFIKATOR.SCHADEN, kosten: 2, beschreibung: '3W6 Schaden (4W6 bei einer Steigerung).' },
      ...PANZERBRECHEND,
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
    empfaengerKosten: ZUSAETZLICHE_EMPFAENGER_KOSTEN,
    zusammenfassung: 'Panzerung +2; mit Steigerung stattdessen Robustheit +2.',
    modifikatoren: [],
  },
  [MACHT.ABWEHREN]: {
    name: MACHT.ABWEHREN,
    typ: 'effekt',
    rang: 'Anfänger',
    kosten: 3,
    reichweite: 'Verstand',
    wirkungsdauer: 5,
    ziel: 'selbst_oder_verbuendeter',
    empfaengerKosten: ZUSAETZLICHE_EMPFAENGER_KOSTEN,
    zusammenfassung:
      'Feinde ziehen –2 von Nahkampf- oder Fernkampfangriffen (Wahl des Wirkers) gegen das Ziel ab; bei einer Steigerung von beidem.',
    modifikatoren: [],
  },
  [MACHT.WAFFE_VERBESSERN]: {
    name: MACHT.WAFFE_VERBESSERN,
    typ: 'effekt',
    rang: 'Anfänger',
    kosten: 2,
    reichweite: 'Verstand',
    wirkungsdauer: 5,
    ziel: 'selbst_oder_verbuendeter',
    empfaengerKosten: ZUSAETZLICHE_EMPFAENGER_KOSTEN,
    zusammenfassung: 'Waffenschaden +2, mit Steigerung +4.',
    modifikatoren: [],
  },
  [MACHT.ARKANER_SCHUTZ]: {
    name: MACHT.ARKANER_SCHUTZ,
    typ: 'effekt',
    rang: 'Anfänger',
    kosten: 1,
    reichweite: 'Verstand',
    wirkungsdauer: 5,
    ziel: 'selbst_oder_verbuendeter',
    empfaengerKosten: ZUSAETZLICHE_EMPFAENGER_KOSTEN,
    zusammenfassung:
      'Feindliche Mächte gegen das Ziel erleiden –2 (–4 mit Steigerung); ihr Schaden sinkt um denselben Wert. Kumulativ mit Arkaner Resistenz.',
    modifikatoren: [],
  },
  [MACHT.EIGENSCHAFT]: {
    name: MACHT.EIGENSCHAFT,
    typ: 'effekt',
    rang: 'Anfänger',
    kosten: 3,
    reichweite: 'Verstand',
    wirkungsdauer: 5,
    ziel: 'beliebig',
    zusammenfassung:
      'Erhöhen: eine Eigenschaft eines Verbündeten +1 Würfeltyp (+2 mit Steigerung) für 5 Runden. Senken: beim Feind –1/–2 Würfeltypen (min. W4); er schüttelt es am Ende seiner Züge mit Willenskraft ab.',
    modifikatoren: [
      {
        name: MODIFIKATOR.STARK,
        kosten: 1,
        beschreibung: 'Nur Senken: die Willenskraftprobe zum Abschütteln erfolgt mit –2.',
        modus: 'senken',
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
    zusammenfassung:
      'Heilt eine Wunde, mit Steigerung zwei (nur Wunden unter einer Stunde). Ausgeschaltete sind danach wieder dabei.',
    modifikatoren: [],
  },
  [MACHT.LINDERUNG]: {
    name: MACHT.LINDERUNG,
    typ: 'zustand',
    rang: 'Anfänger',
    kosten: 1,
    reichweite: 'Verstand',
    wirkungsdauer: SOFORT,
    ziel: 'selbst_oder_verbuendeter',
    empfaengerKosten: ZUSAETZLICHE_EMPFAENGER_KOSTEN,
    zusammenfassung:
      'Erholen: hebt Angeschlagen, Verwundbar oder Abgelenkt auf (zwei mit Steigerung). Abschwächen: ignoriert 1 (2) Punkte Wund- und Erschöpfungsabzug für eine Stunde.',
    modifikatoren: [
      { name: MODIFIKATOR.BETAEUBT, kosten: 1, beschreibung: 'Erholen kann auch Betäubt entfernen.' },
    ],
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
    modifikatoren: [...FLAECHENEFFEKT],
  },
  [MACHT.SCHLUMMER]: {
    name: MACHT.SCHLUMMER,
    typ: 'widerstand',
    rang: 'Fortgeschritten',
    kosten: 2,
    reichweite: 'Verstand',
    wirkungsdauer: SOFORT,
    ziel: 'gegner',
    zusammenfassung:
      'Das Opfer legt eine Willenskraftprobe ab (–2 bei einer Steigerung des Wirkers), sonst schläft es ein (eine Stunde).',
    modifikatoren: [...FLAECHENEFFEKT],
  },
  [MACHT.BLENDEN]: {
    name: MACHT.BLENDEN,
    typ: 'zustand',
    rang: 'Anfänger',
    kosten: 2,
    reichweite: 'Verstand',
    wirkungsdauer: SOFORT,
    ziel: 'gegner',
    zusammenfassung:
      '–2 auf alle Aktionen, die Sicht erfordern (–4 mit Steigerung). Am Ende seiner Züge schüttelt das Opfer 2 Punkte (Steigerung: alles) mit Konstitution ab.',
    modifikatoren: [
      ...FLAECHENEFFEKT,
      { name: MODIFIKATOR.STARK, kosten: 1, beschreibung: 'Die Konstitutionsprobe zum Abschütteln erfolgt mit –2.' },
    ],
  },
  [MACHT.VERWIRRUNG]: {
    name: MACHT.VERWIRRUNG,
    typ: 'zustand',
    rang: 'Anfänger',
    kosten: 1,
    reichweite: 'Verstand',
    wirkungsdauer: SOFORT,
    ziel: 'gegner',
    flaeche: true,
    zusammenfassung:
      'Alle in einer mittleren Flächenschablone sind Abgelenkt oder Verwundbar (Wahl des Wirkers), mit Steigerung beides.',
    modifikatoren: [
      { name: MODIFIKATOR.GROSSE_SCHABLONE, kosten: 1, beschreibung: 'Große statt mittlerer Flächenschablone.' },
    ],
  },
  [MACHT.VERSTRICKEN]: {
    name: MACHT.VERSTRICKEN,
    typ: 'zustand',
    rang: 'Anfänger',
    kosten: 2,
    reichweite: 'Verstand',
    wirkungsdauer: SOFORT,
    ziel: 'gegner',
    zusammenfassung:
      'Das Ziel ist Festgehalten, mit Steigerung Gebunden (Härte 8). Befreien mit Stärke –2 oder Athletik.',
    modifikatoren: [
      ...FLAECHENEFFEKT,
      { name: MODIFIKATOR.ZAEH, kosten: 1, beschreibung: 'Härte 10 statt 8 (nur beim Zerstören von außen relevant).' },
    ],
  },
}

export const MACHT_NAMEN: readonly string[] = Object.keys(MAECHTE)

export function machtDefinition(name: string): MachtDefinition | null {
  return MAECHTE[name] ?? null
}

/** Wie viele Ziele die Macht mit den gewählten Modifikatoren erfassen darf. */
export function erlaubtMehrereZiele(macht: MachtDefinition, modifikatoren: readonly string[] = []): boolean {
  if (macht.flaeche || macht.empfaengerKosten) return true
  return macht.modifikatoren.some((m) => m.flaeche && modifikatoren.includes(m.name))
}

/** Gesamtkosten inklusive Machtmodifikatoren und zusätzlicher Empfänger. */
export function machtKosten(
  macht: MachtDefinition,
  modifikatoren: readonly string[] = [],
  anzahlZiele = 1,
): number {
  const basis = macht.modifikatoren
    .filter((m) => modifikatoren.includes(m.name))
    .reduce((summe, m) => summe + m.kosten, macht.kosten)
  const empfaenger = macht.empfaengerKosten ? Math.max(0, anzahlZiele - 1) * macht.empfaengerKosten : 0
  return basis + empfaenger
}

/** PB eines Angriffs aus den Panzerbrechend-Modifikatoren. */
export function machtPanzerbrechend(modifikatoren: readonly string[]): number {
  if (modifikatoren.includes(MODIFIKATOR.PB6)) return 6
  if (modifikatoren.includes(MODIFIKATOR.PB4)) return 4
  if (modifikatoren.includes(MODIFIKATOR.PB2)) return 2
  return 0
}

/**
 * Schadensformel für Geschoss, Flächenschlag und Strahl. Die Steigerung
 * erhöht hier die Würfelzahl, statt wie bei Waffen einen Bonuswürfel zu
 * addieren.
 */
export function machtSchaden(steigerung: boolean, verstaerkt: boolean): string {
  if (verstaerkt) return steigerung ? '4W6' : '3W6'
  return steigerung ? '3W6' : '2W6'
}

/** Erschöpfungsstufen: –1 je Stufe auf alle Eigenschaftsproben. */
export const ERSCHOEPFUNG_NAMEN = ['', 'Erschöpft', 'Entkräftet'] as const
export const MAX_ERSCHOEPFUNG = 3
