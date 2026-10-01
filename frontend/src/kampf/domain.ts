/**
 * Kampfsimulator – Domain-Schicht.
 *
 * Enthält ausschließlich Spielregeln (SWADE, deutsche Begriffe) ohne
 * Abhängigkeiten zu Vue, Store oder API:
 *   - Wuerfel / Eigenschaftsprobe (explodierende Würfel, Wildcard-Würfel)
 *   - Aktionskarte / Aktionsstapel (Karten-Initiative mit Jokern)
 *   - InitiativeRegeln (Kühler Kopf, Schnell, Zögerlich, Taktiker)
 *   - Schadensformel / SchadensRegeln (Robustheit, Steigerungen, Wunden)
 *   - Kaempfer (Entity mit Zustand: Wunden, Angeschlagen, Bennys,
 *     Machtpunkte und aktive Macht-Effekte)
 *
 * Der Machtkatalog liegt in kampf/maechte.ts; die Abhängigkeit geht nur
 * in diese Richtung.
 */

import { MAX_ERSCHOEPFUNG, type AktiverEffekt, type EffektWerte } from '@/kampf/maechte'

// ------------------------------------------------------------------
// Konstanten
// ------------------------------------------------------------------

export const MINDESTWURF = 4
const STEIGERUNG = 4
const MAX_WUNDMALUS = 3
export const JOKER_BONUS = 2
export const RUECKSICHTSLOS_BONUS = 2
const RUECKSICHTSLOS_PARADE_MALUS = 2
const ABGELENKT_MALUS = 2
const VERWUNDBAR_BONUS = 2

export const TALENT = {
  KUEHLER_KOPF: 'Kühler Kopf',
  SEHR_KUEHLER_KOPF: 'Sehr Kühler Kopf',
  SCHNELL: 'Schnell',
  TAKTIKER: 'Taktiker',
  MEISTERTAKTIKER: 'Meistertaktiker',
  BERECHNEND: 'Berechnend',
  KAMPFREFLEXE: 'Kampfreflexe',
  EISENKIEFER: 'Eisenkiefer',
  SCHMERZRESISTENZ: 'Schmerzresistenz',
  STAERKERE_SCHMERZRESISTENZ: 'Stärkere Schmerzresistenz',
  ZAEH_WIE_LEDER: 'Zäh wie Leder',
  ZAEHER_ALS_LEDER: 'Zäher als Leder',
  MAECHTIGER_HIEB: 'Mächtiger Hieb',
  VOLLTREFFER: 'Volltreffer',
} as const

export const HANDICAP = {
  ZOEGERLICH: 'Zögerlich',
} as const

/** Talente und Handicaps, die der Simulator regeltechnisch auswertet. */
export const KAMPF_TALENTE: readonly string[] = Object.values(TALENT)
export const KAMPF_HANDICAPS: readonly string[] = Object.values(HANDICAP)

export const FERTIGKEIT = {
  KAEMPFEN: 'Kämpfen',
  SCHIESSEN: 'Schießen',
  ATHLETIK: 'Athletik',
} as const

export const ATTRIBUT = {
  GESCHICKLICHKEIT: 'Geschicklichkeit',
  VERSTAND: 'Verstand',
  WILLENSKRAFT: 'Willenskraft',
  STAERKE: 'Stärke',
  KONSTITUTION: 'Konstitution',
} as const

export const ATTRIBUTE: readonly string[] = Object.values(ATTRIBUT)

export type Seite = 'helden' | 'gegner'

export const SEITE = {
  HELDEN: 'helden',
  GEGNER: 'gegner',
} as const satisfies Record<string, Seite>

// ------------------------------------------------------------------
// Zufall (injizierbar für Tests)
// ------------------------------------------------------------------

export class Zufall {
  private readonly quelle: () => number

  /** @param quelle liefert Werte in [0, 1) */
  constructor(quelle?: () => number) {
    this.quelle = quelle ?? Math.random
  }

  /** Ganzzahl in [1, seiten]. */
  wuerfle(seiten: number): number {
    return Math.floor(this.quelle() * seiten) + 1
  }

  /** Ganzzahl in [0, anzahl). */
  index(anzahl: number): number {
    return Math.floor(this.quelle() * anzahl)
  }
}

// ------------------------------------------------------------------
// Würfel
// ------------------------------------------------------------------

/** Value Object für einen Eigenschaftswürfel, z. B. W8+1. */
export class Wuerfel {
  constructor(
    public readonly seiten: number,
    public readonly bonus = 0,
  ) {}

  static ungeuebt(): Wuerfel {
    return new Wuerfel(4, -2)
  }

  /** Parst "W8", "w10+1", "d6", "8" oder eine Zahl. */
  static parse(text: unknown): Wuerfel | null {
    if (text instanceof Wuerfel) return text
    if (typeof text === 'number') return new Wuerfel(text, 0)
    const treffer = String(text ?? '')
      .trim()
      .replace(/[–−]/g, '-')
      .match(/^[wWdD]?(\d+)\s*([+-]\s*\d+)?$/)
    if (!treffer) return null
    const seiten = parseInt(treffer[1], 10)
    const bonus = treffer[2] ? parseInt(treffer[2].replace(/\s/g, ''), 10) : 0
    return new Wuerfel(seiten, bonus)
  }

  toString(): string {
    if (this.bonus === 0) return `W${this.seiten}`
    return `W${this.seiten}${this.bonus > 0 ? '+' : ''}${this.bonus}`
  }
}

export interface Wurf {
  seiten: number
  summe: number
  wuerfe: number[]
}

/** Explodierender Würfelwurf: bei Maximalwurf wird erneut gewürfelt. */
export function wuerfleExplodierend(seiten: number, zufall: Zufall): Wurf {
  const wuerfe: number[] = []
  let summe = 0
  let wurf: number
  do {
    wurf = zufall.wuerfle(seiten)
    wuerfe.push(wurf)
    summe += wurf
  } while (wurf === seiten && seiten > 1)
  return { seiten, summe, wuerfe }
}

function formatiereWurf(wurf: Wurf): string {
  return `W${wurf.seiten}[${wurf.wuerfe.join('+')}]`
}

function steigerungen(ergebnis: number, mindestwurf: number): number {
  if (ergebnis < mindestwurf) return 0
  return Math.floor((ergebnis - mindestwurf) / STEIGERUNG)
}

export function formatiereModifikator(wert: number): string {
  if (!wert) return '±0'
  return wert > 0 ? `+${wert}` : `${wert}`
}

export interface Modifikator {
  name: string
  wert: number
}

export interface ProbenErgebnis {
  wuerfel: Wuerfel
  eigenschaftsWurf: Wurf
  wildWurf: Wurf | null
  modifikator: number
  mindestwurf: number
  gesamt: number
  erfolg: boolean
  kritisch: boolean
  steigerungen: number
  modifikatoren: Modifikator[]
  ungeuebt: boolean
}

/**
 * Eigenschaftsprobe nach SWADE.
 * Wildcards würfeln zusätzlich einen W6 (Wildcard-Würfel) und nehmen
 * das höhere Ergebnis. Doppel-1 ist ein Kritischer Fehlschlag.
 */
export class Eigenschaftsprobe {
  static wuerfle(p: {
    wuerfel: Wuerfel
    wildcard: boolean
    modifikator?: number
    mindestwurf?: number
    zufall: Zufall
  }): ProbenErgebnis {
    const modifikator = p.modifikator ?? 0
    const mindestwurf = p.mindestwurf || MINDESTWURF
    const eigenschaftsWurf = wuerfleExplodierend(p.wuerfel.seiten, p.zufall)
    const wildWurf = p.wildcard ? wuerfleExplodierend(6, p.zufall) : null

    const bester = wildWurf && wildWurf.summe > eigenschaftsWurf.summe ? wildWurf : eigenschaftsWurf
    const gesamt = bester.summe + p.wuerfel.bonus + modifikator

    const kritisch = Boolean(wildWurf && eigenschaftsWurf.wuerfe[0] === 1 && wildWurf.wuerfe[0] === 1)
    const erfolg = !kritisch && gesamt >= mindestwurf

    return {
      wuerfel: p.wuerfel,
      eigenschaftsWurf,
      wildWurf,
      modifikator,
      mindestwurf,
      gesamt,
      erfolg,
      kritisch,
      steigerungen: erfolg ? steigerungen(gesamt, mindestwurf) : 0,
      modifikatoren: [],
      ungeuebt: false,
    }
  }

  static beschreibe(ergebnis: ProbenErgebnis): string {
    let text = `${ergebnis.wuerfel}: ${formatiereWurf(ergebnis.eigenschaftsWurf)}`
    if (ergebnis.wildWurf) text += `, Wild ${formatiereWurf(ergebnis.wildWurf)}`
    const summeBoni = ergebnis.wuerfel.bonus + ergebnis.modifikator
    if (summeBoni !== 0) text += ` ${formatiereModifikator(summeBoni)}`
    text += ` = ${ergebnis.gesamt} gegen ${ergebnis.mindestwurf}`
    if (ergebnis.kritisch) return `${text} – Kritischer Fehlschlag!`
    if (!ergebnis.erfolg) return `${text} – Fehlschlag`
    if (ergebnis.steigerungen > 0) return `${text} – Erfolg mit ${ergebnis.steigerungen} Steigerung(en)`
    return `${text} – Erfolg`
  }
}

// ------------------------------------------------------------------
// Aktionskarten
// ------------------------------------------------------------------

const FARBEN = [
  { name: 'Kreuz', symbol: '♣', rot: false },
  { name: 'Karo', symbol: '♦', rot: true },
  { name: 'Herz', symbol: '♥', rot: true },
  { name: 'Pik', symbol: '♠', rot: false },
] as const

const WERT_NAMEN: Record<number, string> = { 11: 'Bube', 12: 'Dame', 13: 'König', 14: 'Ass' }
const WERT_KUERZEL: Record<number, string> = { 11: 'B', 12: 'D', 13: 'K', 14: 'A' }

/** Value Object: eine Karte des Aktionsstapels. */
export class Aktionskarte {
  /**
   * @param wert 2..14 (14 = Ass); bei Jokern 0
   * @param farbe 0..3 (Kreuz < Karo < Herz < Pik); bei Jokern 0/1
   */
  constructor(
    public readonly wert: number,
    public readonly farbe: number,
    public readonly joker = false,
  ) {}

  /** Sortierschlüssel: höher handelt zuerst. */
  get rang(): number {
    if (this.joker) return 1000 + this.farbe
    return this.wert * 4 + this.farbe
  }

  get istRot(): boolean {
    return this.joker ? this.farbe === 1 : FARBEN[this.farbe].rot
  }

  get kuerzel(): string {
    if (this.joker) return 'J'
    return WERT_KUERZEL[this.wert] ?? String(this.wert)
  }

  get symbol(): string {
    return this.joker ? '★' : FARBEN[this.farbe].symbol
  }

  get name(): string {
    if (this.joker) return this.istRot ? 'Roter Joker' : 'Schwarzer Joker'
    return `${FARBEN[this.farbe].name} ${WERT_NAMEN[this.wert] ?? String(this.wert)}`
  }

  istBesserAls(andere: Aktionskarte | null): boolean {
    return !andere || this.rang > andere.rang
  }
}

/** Aggregat: Aktionsstapel mit 54 Karten (52 + 2 Joker). */
export class Aktionsstapel {
  stapel: Aktionskarte[] = []
  ablage: Aktionskarte[] = []
  jokerGezogen = false

  constructor(private readonly zufall: Zufall) {
    this.neuMischen()
  }

  static alleKarten(): Aktionskarte[] {
    const karten: Aktionskarte[] = []
    for (let farbe = 0; farbe < FARBEN.length; farbe += 1) {
      for (let wert = 2; wert <= 14; wert += 1) {
        karten.push(new Aktionskarte(wert, farbe, false))
      }
    }
    karten.push(new Aktionskarte(0, 0, true))
    karten.push(new Aktionskarte(0, 1, true))
    return karten
  }

  /** Mischt alle 54 Karten neu (Karten in der Hand verfallen). */
  neuMischen(): void {
    this.stapel = Aktionsstapel.alleKarten()
    this.ablage = []
    this.jokerGezogen = false
    this.mischen(this.stapel)
  }

  private mischen(karten: Aktionskarte[]): void {
    for (let i = karten.length - 1; i > 0; i -= 1) {
      const j = this.zufall.index(i + 1)
      ;[karten[i], karten[j]] = [karten[j], karten[i]]
    }
  }

  get anzahlVerbleibend(): number {
    return this.stapel.length
  }

  ziehe(): Aktionskarte {
    if (this.stapel.length === 0) {
      this.stapel = this.ablage
      this.ablage = []
      this.mischen(this.stapel)
    }
    const karte = this.stapel.pop()!
    if (karte.joker) this.jokerGezogen = true
    return karte
  }

  ablegen(karten: (Aktionskarte | null)[]): void {
    karten.forEach((karte) => {
      if (karte) this.ablage.push(karte)
    })
  }

  /** Nach einer Runde mit Joker wird der gesamte Stapel neu gemischt. */
  rundenende(): boolean {
    if (this.jokerGezogen) {
      this.neuMischen()
      return true
    }
    return false
  }
}

// ------------------------------------------------------------------
// Initiative-Regeln
// ------------------------------------------------------------------

export class InitiativeRegeln {
  /**
   * Zieht die Aktionskarte eines Kämpfers unter Berücksichtigung von
   * Kühler Kopf, Sehr Kühler Kopf, Zögerlich und Schnell.
   */
  static zieheFuer(kaempfer: Kaempfer, stapel: Aktionsstapel): { karte: Aktionskarte; notizen: string[] } {
    const notizen: string[] = []
    let gezogen: Aktionskarte[]
    let karte: Aktionskarte

    if (kaempfer.hatHandicap(HANDICAP.ZOEGERLICH)) {
      gezogen = [stapel.ziehe(), stapel.ziehe()]
      const joker = gezogen.find((k) => k.joker)
      karte = joker ?? gezogen.reduce((a, b) => (a.rang < b.rang ? a : b))
      notizen.push(`Zögerlich: ${gezogen.map((k) => k.name).join(' / ')} → ${karte.name}`)
    } else {
      const zusatz = InitiativeRegeln.zusatzkarten(kaempfer)
      gezogen = []
      for (let i = 0; i <= zusatz; i += 1) gezogen.push(stapel.ziehe())
      karte = gezogen.reduce((a, b) => (a.rang > b.rang ? a : b))
      if (zusatz > 0) {
        const talent = zusatz === 2 ? TALENT.SEHR_KUEHLER_KOPF : TALENT.KUEHLER_KOPF
        notizen.push(`${talent}: ${gezogen.map((k) => k.name).join(' / ')} → ${karte.name}`)
      }
    }
    stapel.ablegen(gezogen.filter((k) => k !== karte))

    if (kaempfer.hatTalent(TALENT.SCHNELL)) {
      while (!karte.joker && karte.wert <= 5) {
        const alt = karte
        stapel.ablegen([alt])
        karte = stapel.ziehe()
        notizen.push(`Schnell: ${alt.name} abgeworfen → ${karte.name}`)
      }
    }
    return { karte, notizen }
  }

  static zusatzkarten(kaempfer: Kaempfer): number {
    if (kaempfer.hatTalent(TALENT.SEHR_KUEHLER_KOPF)) return 2
    if (kaempfer.hatTalent(TALENT.KUEHLER_KOPF)) return 1
    return 0
  }

  static taktikerKarten(kaempfer: Kaempfer): number {
    if (kaempfer.hatTalent(TALENT.MEISTERTAKTIKER)) return 2
    if (kaempfer.hatTalent(TALENT.TAKTIKER)) return 1
    return 0
  }

  /**
   * Taktiker/Meistertaktiker: zusätzliche Karten gehen an verbündete
   * Statisten. Jede Karte ersetzt die schlechteste Karte eines
   * Verbündeten, sofern sie besser ist. Angeschlagene Taktiker
   * verteilen keine Karten.
   */
  static verteileTaktikerKarten(kaempferListe: Kaempfer[], stapel: Aktionsstapel): string[] {
    const notizen: string[] = []
    kaempferListe
      .filter((t) => t.istKampffaehig && !t.angeschlagen)
      .forEach((taktiker) => {
        const anzahl = InitiativeRegeln.taktikerKarten(taktiker)
        for (let i = 0; i < anzahl; i += 1) {
          const statisten = kaempferListe
            .filter((k) => k !== taktiker && k.seite === taktiker.seite && !k.wildcard && k.istKampffaehig && k.karte)
            .sort((a, b) => a.karte!.rang - b.karte!.rang)
          const karte = stapel.ziehe()
          const empfaenger = statisten[0]
          if (empfaenger && karte.istBesserAls(empfaenger.karte)) {
            stapel.ablegen([empfaenger.karte])
            notizen.push(
              `${taktiker.name} (Taktiker) gibt ${karte.name} an ${empfaenger.name} (statt ${empfaenger.karte!.name}).`,
            )
            empfaenger.karte = karte
          } else {
            stapel.ablegen([karte])
            notizen.push(`${taktiker.name} (Taktiker) zieht ${karte.name} – kein Statist profitiert.`)
          }
        }
      })
    return notizen
  }

  static sortiere(kaempferListe: Kaempfer[]): Kaempfer[] {
    return kaempferListe.filter((k) => k.karte).sort((a, b) => b.karte!.rang - a.karte!.rang)
  }
}

// ------------------------------------------------------------------
// Schaden
// ------------------------------------------------------------------

/**
 * Value Object für eine Schadensangabe des Generators,
 * z. B. "Stä+W6+1", "2W8–1", "W4-2", "1-3W6".
 * Bei Bereichsangaben wie "1-3W6" wird die höchste Würfelanzahl verwendet.
 */
export class Schadensformel {
  constructor(
    public readonly staerke: boolean,
    public readonly wuerfel: number[],
    public readonly bonus: number,
    public readonly text: string,
  ) {}

  static parse(text: unknown): Schadensformel | null {
    const roh = String(text ?? '').trim()
    const normal = roh.replace(/[–−]/g, '-').replace(/\s/g, '').replace(/\*$/, '')
    const staerke = /^St[äa]/i.test(normal)
    const rest = normal.replace(/^St[äa][a-zä]*\+?/i, '')
    const wuerfel: number[] = []
    let bonus = 0

    const wuerfelRegex = /(\d+)?[wWdD](\d+)/g
    let treffer: RegExpExecArray | null
    while ((treffer = wuerfelRegex.exec(rest)) !== null) {
      const anzahl = treffer[1] ? parseInt(treffer[1], 10) : 1
      for (let i = 0; i < anzahl; i += 1) wuerfel.push(parseInt(treffer[2], 10))
    }
    const bonusTreffer = rest.replace(/(\d+)?[wWdD](\d+)/g, '').match(/[+-]\d+$/)
    if (bonusTreffer) bonus = parseInt(bonusTreffer[0], 10)
    if (!staerke && wuerfel.length === 0) return null
    return new Schadensformel(staerke, wuerfel, bonus, roh)
  }

  toString(): string {
    return this.text
  }
}

export interface SchadensWurf {
  wuerfe: Wurf[]
  bonus: number
  gesamt: number
  verdoppelt: boolean
}

export type TrefferErgebnis = 'kein' | 'angeschlagen' | 'wunden'

export interface TrefferBewertung {
  ergebnis: TrefferErgebnis
  wunden: number
  differenz: number
}

export class SchadensRegeln {
  /**
   * Würfelt Schaden. Nahkampfwaffen mit "Stä" addieren den
   * Stärkewürfel; liegt die Stärke unter der Mindeststärke, wird der
   * Waffenwürfel auf den Stärkewürfel begrenzt. Schadenswürfel
   * explodieren, es gibt keinen Wildcard-Würfel.
   */
  static wuerfle(p: {
    formel: Schadensformel
    staerke: Wuerfel
    mindeststaerke?: number
    steigerung?: boolean
    modifikator?: number
    verdoppeln?: boolean
    zufall: Zufall
  }): SchadensWurf {
    const wuerfe: Wurf[] = []
    const formel = p.formel
    if (formel.staerke) wuerfe.push(wuerfleExplodierend(p.staerke.seiten, p.zufall))
    formel.wuerfel.forEach((seiten) => {
      const begrenzt =
        formel.staerke && p.mindeststaerke && p.staerke.seiten < p.mindeststaerke
          ? Math.min(seiten, p.staerke.seiten)
          : seiten
      wuerfe.push(wuerfleExplodierend(begrenzt, p.zufall))
    })
    if (p.steigerung) wuerfe.push(wuerfleExplodierend(6, p.zufall))
    const staerkeBonus = formel.staerke ? p.staerke.bonus : 0
    const bonus = formel.bonus + staerkeBonus + (p.modifikator ?? 0)
    let gesamt = wuerfe.reduce((s, w) => s + w.summe, 0) + bonus
    if (p.verdoppeln) gesamt *= 2
    return { wuerfe, bonus, gesamt: Math.max(0, gesamt), verdoppelt: Boolean(p.verdoppeln) }
  }

  static beschreibe(schaden: SchadensWurf): string {
    let text = schaden.wuerfe.map(formatiereWurf).join(' + ')
    if (schaden.bonus) text += ` ${formatiereModifikator(schaden.bonus)}`
    if (schaden.verdoppelt) text = `(${text}) ×2`
    return `${text} = ${schaden.gesamt}`
  }

  /**
   * Vergleicht Schaden mit Robustheit.
   * Erfolg = Angeschlagen (bei bereits Angeschlagenen: 1 Wunde),
   * jede Steigerung = 1 Wunde.
   *
   * Die Spezialfähigkeit „Zäh“ (Bestiarium) hebt genau den zweiten
   * Angeschlagen-Fall auf: das Ziel bleibt Angeschlagen, statt eine
   * Wunde zu erleiden. Steigerungen verwunden weiterhin normal.
   */
  static bewerte(
    schaden: number,
    robustheit: number,
    bereitsAngeschlagen: boolean,
    zaeh = false,
  ): TrefferBewertung {
    const differenz = schaden - robustheit
    if (differenz < 0) return { ergebnis: 'kein', wunden: 0, differenz }
    const anzahl = Math.floor(differenz / STEIGERUNG)
    if (anzahl === 0) {
      if (bereitsAngeschlagen && !zaeh) return { ergebnis: 'wunden', wunden: 1, differenz }
      return { ergebnis: 'angeschlagen', wunden: 0, differenz }
    }
    return { ergebnis: 'wunden', wunden: anzahl, differenz }
  }
}

// ------------------------------------------------------------------
// Waffe
// ------------------------------------------------------------------

export interface WaffenDaten {
  name: string
  fertigkeit?: string
  schaden: string
  pb?: number
  mindeststaerke?: number
  reichweite?: string
}

export class Waffe {
  readonly name: string
  readonly fertigkeit: string
  readonly schaden: string
  readonly formel: Schadensformel | null
  readonly pb: number
  readonly mindeststaerke: number
  readonly reichweite: string

  constructor(d: WaffenDaten) {
    this.name = d.name
    this.fertigkeit = d.fertigkeit || FERTIGKEIT.KAEMPFEN
    this.schaden = d.schaden
    this.formel = Schadensformel.parse(d.schaden)
    this.pb = d.pb || 0
    this.mindeststaerke = d.mindeststaerke || 0
    this.reichweite = d.reichweite || ''
  }

  get istNahkampf(): boolean {
    return this.fertigkeit === FERTIGKEIT.KAEMPFEN
  }

  static waffenlos(): Waffe {
    return new Waffe({ name: 'Waffenlos', fertigkeit: FERTIGKEIT.KAEMPFEN, schaden: 'Stä' })
  }

  toJSON(): WaffenDaten {
    return {
      name: this.name,
      fertigkeit: this.fertigkeit,
      schaden: this.schaden,
      pb: this.pb,
      mindeststaerke: this.mindeststaerke,
      reichweite: this.reichweite,
    }
  }
}

// ------------------------------------------------------------------
// Kämpfer (Entity)
// ------------------------------------------------------------------

/** Serialisierbare Kämpferdaten, z. B. aus /spiellogik/kampfprofil. */
export interface KaempferDaten {
  name: string
  seite?: Seite
  wildcard?: boolean
  attribute?: Record<string, string>
  fertigkeiten?: Record<string, string>
  parade?: number
  robustheit?: number
  panzerung?: number
  waffen?: WaffenDaten[]
  talente?: string[]
  handicaps?: string[]
  bennys?: number
  /** Bestiarium: Wunden, die ein Statist einstecken kann (Widerstandsfähig). */
  widerstandsfaehig?: number
  /** Bestiarium: zweites Angeschlagen verursacht keine Wunde (Zäh). */
  zaeh?: boolean
  /**
   * Arkane Fertigkeit, z. B. "Zaubern" — leer bei Nicht-Wirkern.
   * Schreibweise wie in der API (snake_case), nicht wie die Klassen-Property.
   */
  arkane_fertigkeit?: string
  machtpunkte?: number
  /** Namen der beherrschten Mächte (siehe kampf/maechte.ts). */
  maechte?: string[]
}

let naechsteId = 1

export class Kaempfer {
  readonly id: string
  name: string
  seite: Seite
  wildcard: boolean
  attribute: Record<string, Wuerfel>
  fertigkeiten: Record<string, Wuerfel>
  parade: number
  robustheit: number
  panzerung: number
  waffen: Waffe[]
  talente: Set<string>
  handicaps: Set<string>
  bennys: number
  widerstandsfaehig: number
  zaeh: boolean
  arkaneFertigkeit: string
  maxMachtpunkte: number
  maechte: string[]

  // Kampfzustand
  wunden = 0
  angeschlagen = false
  ausserGefecht = false
  karte: Aktionskarte | null = null
  ruecksichtslosAktiv = false
  maechtigerHiebGenutzt = false
  volltrefferGenutzt = false
  machtpunkte = 0
  erschoepfung = 0
  effekte: AktiverEffekt[] = []
  betaeubt = false
  /**
   * Abgelenkt/Verwundbar laufen „bis zum Ende des nächsten Zuges" des
   * Trägers. Gezählt werden die verbleibenden eigenen Zugenden: 1 = klingt
   * am Ende des nächsten eigenen Zuges ab, 0 = nicht aktiv.
   */
  abgelenktZuege = 0
  verwundbarZuege = 0

  constructor(d: {
    name: string
    seite?: Seite
    wildcard?: boolean
    attribute?: Record<string, Wuerfel>
    fertigkeiten?: Record<string, Wuerfel>
    parade?: number
    robustheit?: number
    panzerung?: number
    waffen?: Waffe[]
    talente?: Iterable<string>
    handicaps?: Iterable<string>
    bennys?: number
    widerstandsfaehig?: number
    zaeh?: boolean
    arkaneFertigkeit?: string
    machtpunkte?: number
    maechte?: string[]
  }) {
    this.id = `k${naechsteId++}`
    this.name = d.name
    this.seite = d.seite ?? SEITE.GEGNER
    this.wildcard = Boolean(d.wildcard)
    this.attribute = d.attribute ?? {}
    this.fertigkeiten = d.fertigkeiten ?? {}
    this.parade = d.parade ?? 2
    this.robustheit = d.robustheit ?? 4
    this.panzerung = d.panzerung ?? 0
    this.waffen = d.waffen && d.waffen.length ? d.waffen : [Waffe.waffenlos()]
    this.talente = new Set(d.talente ?? [])
    this.handicaps = new Set(d.handicaps ?? [])
    this.bennys = d.bennys ?? (this.wildcard ? 3 : 0)
    this.widerstandsfaehig = Math.max(0, d.widerstandsfaehig ?? 0)
    this.zaeh = Boolean(d.zaeh)
    this.arkaneFertigkeit = d.arkaneFertigkeit ?? ''
    this.maxMachtpunkte = Math.max(0, d.machtpunkte ?? 0)
    this.machtpunkte = this.maxMachtpunkte
    this.maechte = [...(d.maechte ?? [])]
  }

  /** Kann überhaupt Mächte wirken (arkane Fertigkeit und Mächte bekannt). */
  get istWirker(): boolean {
    return Boolean(this.arkaneFertigkeit) && this.maechte.length > 0
  }

  hatTalent(name: string): boolean {
    return this.talente.has(name)
  }

  hatHandicap(name: string): boolean {
    return Array.from(this.handicaps).some((h) => h === name || h.startsWith(`${name} `) || h.startsWith(`${name}_`))
  }

  get istKampffaehig(): boolean {
    return !this.ausserGefecht
  }

  get hatJoker(): boolean {
    return Boolean(this.karte && this.karte.joker)
  }

  /**
   * Wildcards stecken 3 Wunden weg (mehr mit Zäh wie Leder). Statisten
   * normalerweise keine — außer sie sind Widerstandsfähig (Bestiarium),
   * dann so viele, wie die Spezialfähigkeit angibt.
   */
  get maxWunden(): number {
    if (!this.wildcard) return this.widerstandsfaehig
    if (this.hatTalent(TALENT.ZAEHER_ALS_LEDER)) return 5
    if (this.hatTalent(TALENT.ZAEH_WIE_LEDER)) return 4
    return 3
  }

  /** Wundmalus (negativ), max. –3, reduziert durch Schmerzresistenz. */
  get wundmalus(): number {
    let ignoriert = 0
    if (this.hatTalent(TALENT.STAERKERE_SCHMERZRESISTENZ)) ignoriert = 2
    else if (this.hatTalent(TALENT.SCHMERZRESISTENZ)) ignoriert = 1
    return -Math.max(0, Math.min(this.wunden, MAX_WUNDMALUS) - ignoriert)
  }

  /** Erschöpft –1, Entkräftet –2 auf alle Eigenschaftsproben. */
  get erschoepfungsmalus(): number {
    return -Math.min(this.erschoepfung, MAX_ERSCHOEPFUNG - 1)
  }

  get istAbgelenkt(): boolean {
    return this.abgelenktZuege > 0
  }

  /** Betäubte sind durchgehend Verwundbar, unabhängig vom Zähler. */
  get istVerwundbar(): boolean {
    return this.betaeubt || this.verwundbarZuege > 0
  }

  /** Abgelenkt: –2 auf alle Eigenschaftsproben. */
  get abgelenktmalus(): number {
    return this.istAbgelenkt ? -ABGELENKT_MALUS : 0
  }

  /** Verwundbar: Angriffe gegen diesen Kämpfer erhalten +2. */
  get verwundbarBonus(): number {
    return this.istVerwundbar ? VERWUNDBAR_BONUS : 0
  }

  /** Setzt Abgelenkt bzw. Verwundbar bis zum Ende des nächsten eigenen Zuges. */
  setzeAbgelenkt(zuege = 1): void {
    this.abgelenktZuege = Math.max(this.abgelenktZuege, zuege)
  }

  setzeVerwundbar(zuege = 1): void {
    this.verwundbarZuege = Math.max(this.verwundbarZuege, zuege)
  }

  /** Summe eines Effektwerts über alle aktiven Mächte. */
  private effektSumme(feld: keyof EffektWerte): number {
    return this.effekte.reduce((summe, e) => summe + (e[feld] ?? 0), 0)
  }

  /** Panzerung inklusive Schutz und ähnlicher Mächte. */
  get gesamtPanzerung(): number {
    return this.panzerung + this.effektSumme('panzerung')
  }

  /** Schadensbonus der eigenen Waffen (Waffe verbessern). */
  get schadensbonus(): number {
    return this.effektSumme('schaden')
  }

  /** Abzug, den ein Angreifer gegen diesen Kämpfer erleidet (Abwehren). */
  abwehrMalus(istNahkampf: boolean): number {
    return this.effektSumme(istNahkampf ? 'abwehrNahkampf' : 'abwehrFernkampf')
  }

  get aktuelleParade(): number {
    return this.parade - (this.ruecksichtslosAktiv ? RUECKSICHTSLOS_PARADE_MALUS : 0)
  }

  robustheitGegen(pb: number): number {
    const basis = this.robustheit + this.effektSumme('robustheit')
    return basis + Math.max(0, this.gesamtPanzerung - (pb || 0))
  }

  get gesamtRobustheit(): number {
    return this.robustheitGegen(0)
  }

  /** Würfel für Attribut oder Fertigkeit; ungeübt W4–2. */
  wuerfelFuer(eigenschaft: string): { wuerfel: Wuerfel; ungeuebt: boolean } {
    const attribut = this.attribute[eigenschaft]
    if (attribut) return { wuerfel: attribut, ungeuebt: false }
    const fertigkeit = this.fertigkeiten[eigenschaft]
    if (fertigkeit) return { wuerfel: fertigkeit, ungeuebt: false }
    if (ATTRIBUTE.includes(eigenschaft)) return { wuerfel: new Wuerfel(4, 0), ungeuebt: false }
    return { wuerfel: Wuerfel.ungeuebt(), ungeuebt: true }
  }

  get staerke(): Wuerfel {
    return this.attribute[ATTRIBUT.STAERKE] ?? new Wuerfel(4, 0)
  }

  /**
   * Zustand zu Beginn einer neuen Runde zurücksetzen und Wirkungsdauern
   * herunterzählen. Die Runde der Aktivierung zählt mit, deshalb wird erst
   * ab der Folgerunde reduziert.
   * @returns Beschreibungen der Effekte, die jetzt ausgelaufen sind
   */
  neueRunde(): string[] {
    this.maechtigerHiebGenutzt = false
    this.volltrefferGenutzt = false
    const abgelaufen: string[] = []
    this.effekte = this.effekte.filter((effekt) => {
      effekt.verbleibend -= 1
      if (effekt.verbleibend > 0) return true
      abgelaufen.push(`${effekt.macht} auf ${this.name} endet.`)
      return false
    })
    return abgelaufen
  }

  /** Effekt hinzufügen; dieselbe Macht desselben Wirkers ersetzt sich. */
  fuegeEffektHinzu(effekt: AktiverEffekt): void {
    this.effekte = this.effekte.filter(
      (e) => !(e.macht === effekt.macht && e.wirkerId === effekt.wirkerId),
    )
    this.effekte.push(effekt)
  }

  /** Rückschlag: alle von diesem Wirker ausgehenden Effekte enden. */
  beendeEffekteVon(wirkerId: string): string[] {
    const beendet = this.effekte.filter((e) => e.wirkerId === wirkerId)
    this.effekte = this.effekte.filter((e) => e.wirkerId !== wirkerId)
    return beendet.map((e) => `${e.macht} auf ${this.name} endet.`)
  }

  /** Zustand zu Beginn des eigenen Zuges. */
  zugBeginn(): void {
    this.ruecksichtslosAktiv = false
  }

  /**
   * Ende des eigenen Zuges: Abgelenkt und Verwundbar klingen ab.
   * Betäubte bleiben Verwundbar, solange die Betäubung anhält.
   * @returns Beschreibungen der beendeten Zustände
   */
  zugEnde(): string[] {
    const beendet: string[] = []
    if (this.abgelenktZuege > 0) {
      this.abgelenktZuege -= 1
      if (this.abgelenktZuege === 0) beendet.push(`${this.name} ist nicht mehr Abgelenkt.`)
    }
    if (this.verwundbarZuege > 0) {
      this.verwundbarZuege -= 1
      if (this.verwundbarZuege === 0 && !this.betaeubt) {
        beendet.push(`${this.name} ist nicht mehr Verwundbar.`)
      }
    }
    return beendet
  }

  benutzeBenny(): boolean {
    if (this.bennys <= 0) return false
    this.bennys -= 1
    return true
  }

  /**
   * Übernimmt Schaden nach eventuellem Wegstecken.
   * @param wunden bereits reduzierte Wundenzahl
   * @param angeschlagenDurchTreffer Treffer verursacht Angeschlagen
   * @returns Beschreibung des neuen Zustands
   */
  nimmSchaden(wunden: number, angeschlagenDurchTreffer: boolean): string {
    if (wunden <= 0) {
      if (angeschlagenDurchTreffer) {
        this.angeschlagen = true
        return `${this.name} ist Angeschlagen.`
      }
      return `${this.name} bleibt unverletzt.`
    }
    // Statisten gehen beim ersten Treffer zu Boden — es sei denn, sie sind
    // Widerstandsfähig und können wie Wildcards Wunden ansammeln.
    if (this.maxWunden === 0) {
      this.ausserGefecht = true
      this.angeschlagen = false
      return `${this.name} ist Außer Gefecht.`
    }
    this.wunden += wunden
    this.angeschlagen = true
    if (this.wunden > this.maxWunden) {
      this.wunden = this.maxWunden
      this.ausserGefecht = true
      return `${this.name} erleidet ${wunden} Wunde(n) und ist Außer Gefecht.`
    }
    return `${this.name} erleidet ${wunden} Wunde(n) (jetzt ${this.wunden}) und ist Angeschlagen.`
  }

  toJSON(): KaempferDaten {
    const wuerfelMap = (map: Record<string, Wuerfel>) =>
      Object.fromEntries(Object.entries(map).map(([k, w]) => [k, w.toString()]))
    return {
      name: this.name,
      seite: this.seite,
      wildcard: this.wildcard,
      attribute: wuerfelMap(this.attribute),
      fertigkeiten: wuerfelMap(this.fertigkeiten),
      parade: this.parade,
      robustheit: this.robustheit,
      panzerung: this.panzerung,
      waffen: this.waffen.map((w) => w.toJSON()),
      talente: Array.from(this.talente),
      handicaps: Array.from(this.handicaps),
      bennys: this.bennys,
      widerstandsfaehig: this.widerstandsfaehig,
      zaeh: this.zaeh,
      arkane_fertigkeit: this.arkaneFertigkeit,
      machtpunkte: this.maxMachtpunkte,
      maechte: [...this.maechte],
    }
  }

  /** Erzeugt eine unabhängige Kopie (z. B. für mehrere Statisten). */
  klone(name?: string): Kaempfer {
    return Kaempfer.ausDaten({ ...this.toJSON(), name: name ?? this.name })
  }

  static ausDaten(d: KaempferDaten): Kaempfer {
    const wuerfelMap = (map?: Record<string, string>) => {
      const ergebnis: Record<string, Wuerfel> = {}
      Object.entries(map ?? {}).forEach(([k, w]) => {
        const wuerfel = Wuerfel.parse(w)
        if (wuerfel) ergebnis[k] = wuerfel
      })
      return ergebnis
    }
    const waffen = (d.waffen ?? []).map((w) => new Waffe(w))
    if (!waffen.some((w) => w.name === 'Waffenlos')) waffen.push(Waffe.waffenlos())
    return new Kaempfer({
      ...d,
      attribute: wuerfelMap(d.attribute),
      fertigkeiten: wuerfelMap(d.fertigkeiten),
      waffen,
      arkaneFertigkeit: d.arkane_fertigkeit,
    })
  }
}
