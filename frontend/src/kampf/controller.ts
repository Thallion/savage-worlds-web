/**
 * Kampfsimulator – Anwendungsschicht (Controller).
 *
 * Koordiniert den Kampfablauf auf Basis der Domain:
 * Runden, Kartenausgabe, Zugreihenfolge, Proben, Angriffe, Kampfoptionen
 * (Herausfordern, Ringen, Verteidigen), Mächte, Schaden wegstecken und
 * Protokoll. Die View hält eine reaktive Instanz (Vue reactive) und ruft
 * ausschließlich öffentliche Methoden auf.
 *
 * Mehrere Treffer einer Aktion (Schneller Angriff, Flächenschlag) werden
 * nacheinander abgewickelt: jeder Schadenswurf vollständig inklusive
 * Wegstecken, ehe der nächste gewürfelt wird (SWAE S. 95, „Timing“).
 */
import {
  ATTRIBUT,
  Aktionsstapel,
  Eigenschaftsprobe,
  FERTIGKEIT,
  HANDICAP,
  InitiativeRegeln,
  JOKER_BONUS,
  Kaempfer,
  MINDESTWURF,
  RUECKSICHTSLOS_BONUS,
  SEITE,
  SchadensRegeln,
  TALENT,
  VERTEIDIGEN_BONUS,
  Waffe,
  Zufall,
  beschreibeMehrfach,
  formatiereModifikator,
  Schadensformel,
  vergleiche,
  wuerfleMehrfach,
  type Fessel,
  type MehrfachProbe,
  type Modifikator,
  type ProbenErgebnis,
  type TrefferBewertung,
} from './domain'
import {
  EINE_STUNDE_IN_RUNDEN,
  MACHT,
  MACHT_MINDESTWURF,
  MAX_ERSCHOEPFUNG,
  MINDESTKOSTEN,
  MODIFIKATOR,
  RUECKSCHLAG_ERSCHOEPFUNG,
  SOFORT,
  STARK_MALUS,
  STEIGERUNG_WIDERSTAND_MALUS,
  erlaubtMehrereZiele,
  machtDefinition,
  machtKosten,
  machtPanzerbrechend,
  machtSchaden,
  type AbwehrArt,
  type AktiverEffekt,
  type EigenschaftModus,
  type LinderungModus,
  type MachtDefinition,
  type VerwirrungWahl,
} from './maechte'

const BERECHNEND_MAX_IGNORIERT = 2
const KAMPFREFLEXE_BONUS = 2
const EISENKIEFER_BONUS = 2
const MEHRFACHAKTION_MALUS = 2
const MAX_UEBERZAHL = 4
const UNBEWAFFNETER_VERTEIDIGER_BONUS = 2
const UEBERRASCHUNG_BONUS = 4
const DOPPELSCHUSS_BONUS = 1
const AUSWEICHEN_MALUS = 2
const RIESENTOETER_GROESSE = 3
const ANFUEHRER_BONUS = 1
const BEFREIEN_STAERKE_MALUS = 2
const BERSERKER_ENDE_MALUS = 2
const BERSERKER_ERSCHOEPFUNG_RUNDEN = 5
const BERSERKER_MAX_RUNDEN = 10
const BLIND_MALUS = 6
const EINAEUGIG_MALUS = 2
const TOLLPATSCHIG_MALUS = 2
const LANGSAM_MALUS = 2
const EINARMIG_MALUS = 4
const SANFTMUETIG_MALUS = 2
const FEIGE_MALUS = 2
/** Rücksichtsloser Angriff: Verwundbar bis zum Ende des **nächsten** Zugs. */
const VERWUNDBAR_BIS_NAECHSTER_ZUG = 2

/** Angesagte Ziele (S. 97) für Normale Kreaturen. */
export const ANGESAGTE_ZIELE = {
  keins: { name: 'Kein', malus: 0, schaden: 0 },
  gliedmasse: { name: 'Gliedmaße', malus: -2, schaden: 0 },
  hand: { name: 'Hand (entwaffnen)', malus: -4, schaden: 0 },
  kopf: { name: 'Kopf oder lebenswichtige Organe', malus: -4, schaden: 4 },
} as const

export type AngesagtesZiel = keyof typeof ANGESAGTE_ZIELE

/** Mit welchem Attribut der Verteidiger einer Herausforderung widersteht (S. 104). */
export const HERAUSFORDERN_ATTRIBUT: Record<string, string> = {
  [FERTIGKEIT.KAEMPFEN]: ATTRIBUT.GESCHICKLICHKEIT,
  [FERTIGKEIT.SCHIESSEN]: ATTRIBUT.GESCHICKLICHKEIT,
  [FERTIGKEIT.ATHLETIK]: ATTRIBUT.GESCHICKLICHKEIT,
  Heimlichkeit: ATTRIBUT.GESCHICKLICHKEIT,
  Provozieren: ATTRIBUT.VERSTAND,
  Einschüchtern: ATTRIBUT.WILLENSKRAFT,
  Überreden: ATTRIBUT.WILLENSKRAFT,
}

/** Herausforderungen ohne Körpereinsatz – auch Gebundenen möglich. */
const VERBALE_FERTIGKEITEN = ['Provozieren', 'Einschüchtern', 'Überreden']

export type ProtokollArt = 'info' | 'runde' | 'zug' | 'erfolg' | 'fehlschlag' | 'schaden' | 'warnung'

export interface ProtokollEintrag {
  id: number
  runde: number
  text: string
  art: ProtokollArt
}

export interface OffenerSchaden {
  ziel: Kaempfer
  wunden: number
  reduziert: number
  versuche: number
}

export interface AngriffsOptionen {
  /** situativer Modifikator */
  modifikator?: number
  /** Anzahl Aktionen im Zug (Mehrfachaktion) */
  aktionen?: number
  /** Reichweitenmodifikator (0/–2/–4/–8) */
  reichweite?: number
  /** Rücksichtsloser Angriff (nur Nahkampf) */
  ruecksichtslos?: boolean
  /** Verzweifelter Angriff: +2/+4 auf Kämpfen, gleicher Abzug auf Schaden */
  verzweifelt?: number
  angesagtesZiel?: AngesagtesZiel
  /** Deckung des Ziels (0/–2/–4/–6/–8) */
  deckung?: number
  /** Beleuchtung (0/–2/–4/–6) */
  beleuchtung?: number
  /** Zusätzliche angrenzende Gegner des Ziels (Überzahlbonus, nur Nahkampf) */
  ueberzahl?: number
  /** Überraschungsangriff: +4 auf Angriff und Schaden */
  ueberraschung?: boolean
  /** Talent Doppelschuss: +1 auf Schießen und Schaden */
  doppelschuss?: boolean
  /** Talent (Blitz-)Schneller Angriff: zusätzliche Kämpfen-Würfel */
  schnellerAngriff?: boolean
}

export interface MachtOptionen {
  /** situativer Modifikator */
  modifikator?: number
  /** Anzahl Aktionen im Zug — Mächte sind volle Aktionen */
  aktionen?: number
  /** gewählte Machtmodifikatoren (Namen aus der Definition) */
  modifikatoren?: string[]
  /** Abwehren ohne Steigerung: Nah- oder Fernkampf */
  abwehrArt?: AbwehrArt
  /** Deckung des Ziels (Geschoss) */
  deckung?: number
  /** Beleuchtung */
  beleuchtung?: number
  /** Eigenschaft erhöhen/senken */
  eigenschaftModus?: EigenschaftModus
  eigenschaft?: string
  linderungModus?: LinderungModus
  verwirrung?: VerwirrungWahl
}

export interface AktionsOptionen {
  modifikator?: number
  aktionen?: number
}

export interface HerausfordernOptionen extends AktionsOptionen {
  fertigkeit: string
  wirkung: 'abgelenkt' | 'verwundbar'
}

export interface RingenOptionen extends AktionsOptionen {
  ueberzahl?: number
}

/** Kontext einer Probe für situationsabhängige Handicaps. */
interface ProbenKontext {
  /** erfordert Sicht (Angriffe, Mächte auf andere, Wahrnehmung) */
  sicht?: boolean
  /** Fernkampf (Einäugig, Schlechte Augen) */
  fernkampf?: boolean
}

export class KampfController {
  private readonly zufall: Zufall
  readonly stapel: Aktionsstapel
  kaempfer: Kaempfer[] = []
  reihenfolge: Kaempfer[] = []
  aktuellerIndex = -1
  runde = 0
  protokoll: ProtokollEintrag[] = []
  offenerSchaden: OffenerSchaden | null = null
  zugDarfHandeln = false
  private naechsteProtokollId = 1
  /** Weitere Treffer derselben Aktion, die nach dem offenen Schaden folgen. */
  private warteschlange: (() => void)[] = []

  constructor(zufall?: Zufall) {
    this.zufall = zufall ?? new Zufall()
    this.stapel = new Aktionsstapel(this.zufall)
  }

  protokolliere(text: string, art: ProtokollArt = 'info'): void {
    this.protokoll.push({ id: this.naechsteProtokollId++, runde: this.runde, text, art })
  }

  // --------------------------------------------------------------
  // Abfragen
  // --------------------------------------------------------------

  get kampfLaeuft(): boolean {
    return this.runde > 0
  }

  get aktueller(): Kaempfer | null {
    return this.reihenfolge[this.aktuellerIndex] ?? null
  }

  finde(id: string): Kaempfer | null {
    return this.kaempfer.find((k) => k.id === id) ?? null
  }

  moeglicheZiele(angreifer: Kaempfer): Kaempfer[] {
    return this.kaempfer.filter((k) => k !== angreifer && k.istKampffaehig)
  }

  /**
   * Gilt ein Anführertalent eines Verbündeten für diesen Kämpfer? Es wirkt
   * auf Statisten, mit Geborener Anführer auch auf Wildcards. Der
   * Befehlsradius wird als erfüllt angenommen.
   */
  anfuehrerBonus(k: Kaempfer, talent: string): boolean {
    return this.kaempfer.some(
      (a) =>
        a !== k &&
        a.seite === k.seite &&
        a.istKampffaehig &&
        a.hatTalent(talent) &&
        (!k.wildcard || a.hatTalent(TALENT.GEBORENER_ANFUEHRER)),
    )
  }

  /** Robustheit inklusive Haltet die Stellung! eines Anführers. */
  robustheitVon(k: Kaempfer, pb = 0): number {
    return k.robustheitGegen(pb) + (this.anfuehrerBonus(k, TALENT.HALTET_DIE_STELLUNG) ? ANFUEHRER_BONUS : 0)
  }

  // --------------------------------------------------------------
  // Kämpferverwaltung
  // --------------------------------------------------------------

  fuegeHinzu(kaempfer: Kaempfer, anzahl = 1): void {
    const menge = Math.max(1, anzahl)
    for (let i = 0; i < menge; i += 1) {
      const neu = menge > 1 ? kaempfer.klone(`${kaempfer.name} ${i + 1}`) : kaempfer
      this.kaempfer.push(neu)
      this.protokolliere(`${neu.name} betritt den Kampf (${neu.wildcard ? 'Wildcard' : 'Statist'}).`)
    }
  }

  entferne(id: string): void {
    const kaempfer = this.finde(id)
    if (!kaempfer) return
    const warAktuell = kaempfer === this.aktueller
    this.kaempfer = this.kaempfer.filter((k) => k !== kaempfer)
    this.reihenfolge = this.reihenfolge.filter((k) => k !== kaempfer)
    if (kaempfer.karte) {
      this.stapel.ablegen([kaempfer.karte])
      kaempfer.karte = null
    }
    if (this.offenerSchaden && this.offenerSchaden.ziel === kaempfer) {
      this.offenerSchaden = null
      this.arbeiteWarteschlangeAb()
    }
    this.aktualisiereFesseln()
    this.protokolliere(`${kaempfer.name} wurde entfernt.`)
    if (warAktuell) {
      this.aktuellerIndex -= 1
      this.naechsterZug()
    }
  }

  // --------------------------------------------------------------
  // Rundenablauf
  // --------------------------------------------------------------

  starteKampf(): void {
    if (this.kaempfer.length < 2) {
      this.protokolliere('Für einen Kampf werden mindestens zwei Kämpfer benötigt.', 'warnung')
      return
    }
    this.stapel.neuMischen()
    this.runde = 0
    this.protokolliere('Der Kampf beginnt. Der Aktionsstapel wird gemischt.', 'runde')
    this.neueRunde()
  }

  beendeKampf(): void {
    this.kaempfer.forEach((k) => {
      k.karte = null
      k.verteidigt = false
    })
    this.reihenfolge = []
    this.aktuellerIndex = -1
    this.offenerSchaden = null
    this.warteschlange = []
    this.protokolliere(`Der Kampf endet nach Runde ${this.runde}.`, 'runde')
    this.runde = 0
  }

  neueRunde(): void {
    this.stapel.ablegen(this.kaempfer.map((k) => k.karte))
    if (this.runde > 0 && this.stapel.rundenende()) {
      this.protokolliere('In der letzten Runde wurde ein Joker gezogen – der Stapel wird neu gemischt.')
    }
    this.runde += 1
    this.protokolliere(`Runde ${this.runde}`, 'runde')

    this.kaempfer.forEach((k) => {
      k.karte = null
      // Wirkungsdauern laufen ab; die Runde der Aktivierung zählt mit.
      k.neueRunde().forEach((n) => this.protokolliere(n))
      if (k.berserker && k.istKampffaehig) this.zaehleBerserkerRunde(k)
    })
    this.kaempfer
      .filter((k) => k.istKampffaehig)
      .forEach((k) => {
        const { karte, notizen } = InitiativeRegeln.zieheFuer(k, this.stapel)
        k.karte = karte
        notizen.forEach((n) => this.protokolliere(`${k.name} – ${n}`))
      })
    InitiativeRegeln.verteileTaktikerKarten(this.kaempfer, this.stapel).forEach((n) => this.protokolliere(n))

    this.reihenfolge = InitiativeRegeln.sortiere(this.kaempfer)
    if (this.reihenfolge.length === 0) {
      this.protokolliere('Niemand ist mehr kampffähig.', 'warnung')
      this.beendeKampf()
      return
    }
    this.reihenfolge
      .filter((k) => k.hatJoker)
      .forEach((k) => {
        this.protokolliere(
          `${k.name} zieht einen Joker: +${JOKER_BONUS} auf alle Eigenschafts- und Schadenswürfe dieser Runde.`,
          'erfolg',
        )
      })
    this.verteileJokerBennys()
    this.aktuellerIndex = -1
    this.naechsterZug()
  }

  /**
   * Die Macht des Jokers (S. 89): zieht ein Held einen Joker, erhalten alle
   * Helden-Wildcards einen Benny; ziehen die Schurken einen, erhält jede
   * ihrer Wildcards einen.
   */
  private verteileJokerBennys(): void {
    ;[SEITE.HELDEN, SEITE.GEGNER].forEach((seite) => {
      const joker = this.reihenfolge.filter((k) => k.seite === seite && k.hatJoker).length
      if (!joker) return
      const empfaenger = this.kaempfer.filter((k) => k.seite === seite && k.wildcard)
      if (!empfaenger.length) return
      empfaenger.forEach((k) => {
        k.bennys += joker
      })
      const wer = seite === SEITE.HELDEN ? 'Helden' : 'gegnerischen'
      this.protokolliere(`Die Macht des Jokers: alle ${wer} Wildcards erhalten ${joker} Benny${joker > 1 ? 's' : ''}.`, 'erfolg')
    })
  }

  naechsterZug(): void {
    if (this.offenerSchaden) return
    const bisher = this.aktueller
    if (bisher) {
      // Abgelenkt/Verwundbar laufen „bis zum Ende des Zuges" aus; Blenden
      // und Eigenschaft senken werden am Zugende abgeschüttelt.
      bisher.zugEnde().forEach((n) => this.protokolliere(n))
      if (bisher.istKampffaehig) this.schuettleAbAmZugende(bisher)
    }
    do {
      this.aktuellerIndex += 1
    } while (this.aktueller && !this.aktueller.istKampffaehig)

    const aktueller = this.aktueller
    if (!aktueller) {
      this.neueRunde()
      return
    }
    this.beginneZug(aktueller)
  }

  private beginneZug(kaempfer: Kaempfer): void {
    kaempfer.zugBeginn()
    this.zugDarfHandeln = true
    this.protokolliere(`${kaempfer.name} ist am Zug (${kaempfer.karte?.name ?? 'ohne Karte'}).`, 'zug')
    if (kaempfer.schlaeft) {
      this.zugDarfHandeln = false
      this.protokolliere(`${kaempfer.name} schläft und kann nicht handeln.`, 'fehlschlag')
      return
    }
    // Betäubt wiegt schwerer als Angeschlagen: solange es anhält, geht gar nichts.
    if (kaempfer.betaeubt) this.betaeubungsErholung(kaempfer)
    if (kaempfer.angeschlagen && !kaempfer.betaeubt) this.erholungsprobe(kaempfer)
  }

  /** Boni auf Erholungsproben gegen Angeschlagen und Betäubt. */
  private erholungsBoni(kaempfer: Kaempfer): Modifikator[] {
    const modifikatoren: Modifikator[] = []
    if (kaempfer.hatTalent(TALENT.KAMPFREFLEXE)) {
      modifikatoren.push({ name: 'Kampfreflexe', wert: KAMPFREFLEXE_BONUS })
    }
    if (this.anfuehrerBonus(kaempfer, TALENT.ANFUEHRER)) {
      modifikatoren.push({ name: 'Anführer', wert: ANFUEHRER_BONUS })
    }
    return modifikatoren
  }

  /** Willenskraftprobe zu Beginn des Zuges, um Angeschlagen aufzuheben. */
  private erholungsprobe(kaempfer: Kaempfer): void {
    const ergebnis = this.wuerfleProbe(kaempfer, ATTRIBUT.WILLENSKRAFT, this.erholungsBoni(kaempfer))
    if (ergebnis.erfolg) {
      kaempfer.angeschlagen = false
      this.protokolliere(
        `${kaempfer.name} erholt sich: ${Eigenschaftsprobe.beschreibe(ergebnis)}` +
          `${KampfController.beschreibeModifikatoren(ergebnis.modifikatoren)}. Nicht mehr Angeschlagen.`,
        'erfolg',
      )
    } else {
      this.zugDarfHandeln = false
      this.protokolliere(
        `${kaempfer.name} bleibt Angeschlagen: ${Eigenschaftsprobe.beschreibe(ergebnis)}` +
          `${KampfController.beschreibeModifikatoren(ergebnis.modifikatoren)}. Nur freie Aktionen möglich.`,
        'fehlschlag',
      )
    }
  }

  /**
   * Blenden und Eigenschaft senken schüttelt das Opfer am Ende seiner
   * Züge automatisch als freie Aktion ab (Konstitution bzw. Willenskraft,
   * –2 mit dem Modifikator Stark).
   */
  private schuettleAbAmZugende(k: Kaempfer): void {
    if (k.blendung) {
      const blendung = k.blendung
      const probe = this.wuerfleProbe(k, ATTRIBUT.KONSTITUTION, [
        { name: MODIFIKATOR.STARK, wert: blendung.stark ? -STARK_MALUS : 0 },
      ])
      const text = `${k.name} versucht die Blendung abzuschütteln: ${Eigenschaftsprobe.beschreibe(probe)}`
      if (probe.steigerungen > 0 || (probe.erfolg && blendung.malus <= 2)) {
        k.blendung = null
        this.protokolliere(`${text}. Die Blendung endet.`, 'erfolg')
      } else if (probe.erfolg) {
        k.blendung = { ...blendung, malus: blendung.malus - 2 }
        this.protokolliere(`${text}. Abzug sinkt auf –${k.blendung.malus}.`, 'erfolg')
      } else {
        this.protokolliere(`${text}. Bleibt geblendet (–${blendung.malus}).`, 'fehlschlag')
      }
    }
    ;[...k.senkungen].forEach((senkung) => {
      const probe = this.wuerfleProbe(k, ATTRIBUT.WILLENSKRAFT, [
        { name: MODIFIKATOR.STARK, wert: senkung.stark ? -STARK_MALUS : 0 },
      ])
      const text = `${k.name} wehrt sich gegen die Senkung von ${senkung.eigenschaft}: ${Eigenschaftsprobe.beschreibe(probe)}`
      if (probe.steigerungen > 0 || (probe.erfolg && senkung.stufen <= 1)) {
        k.senkungen = k.senkungen.filter((s) => s !== senkung)
        this.protokolliere(`${text}. Die Senkung endet.`, 'erfolg')
      } else if (probe.erfolg) {
        senkung.stufen -= 1
        this.protokolliere(`${text}. Nur noch ${senkung.stufen} Würfeltyp(en) gesenkt.`, 'erfolg')
      } else {
        this.protokolliere(`${text}. Die Senkung bleibt.`, 'fehlschlag')
      }
    })
  }

  // --------------------------------------------------------------
  // Proben
  // --------------------------------------------------------------

  /** Abzüge durch Handicaps und Blenden, abhängig von Eigenschaft und Kontext. */
  private situationsModifikatoren(k: Kaempfer, eigenschaft: string, kontext: ProbenKontext): Modifikator[] {
    const liste: Modifikator[] = []
    if (eigenschaft === FERTIGKEIT.ATHLETIK || eigenschaft === 'Heimlichkeit') {
      if (k.hatHandicap(HANDICAP.TOLLPATSCHIG)) liste.push({ name: 'Tollpatschig', wert: -TOLLPATSCHIG_MALUS })
    }
    if (eigenschaft === FERTIGKEIT.ATHLETIK) {
      if (k.handicapStufe(HANDICAP.LANGSAM) === 'schwer') liste.push({ name: 'Langsam', wert: -LANGSAM_MALUS })
      if (k.hatHandicap(HANDICAP.EINARMIG)) liste.push({ name: 'Einarmig', wert: -EINARMIG_MALUS })
    }
    if (eigenschaft === 'Einschüchtern' && k.hatHandicap(HANDICAP.SANFTMUETIG)) {
      liste.push({ name: 'Sanftmütig', wert: -SANFTMUETIG_MALUS })
    }
    if (kontext.sicht) {
      if (k.hatHandicap(HANDICAP.BLIND)) liste.push({ name: 'Blind', wert: -BLIND_MALUS })
      if (k.blendmalus) liste.push({ name: 'Geblendet', wert: k.blendmalus })
      const augen = k.handicapStufe(HANDICAP.SCHLECHTE_AUGEN)
      if (augen && (kontext.fernkampf || eigenschaft === 'Wahrnehmung')) {
        liste.push({ name: 'Schlechte Augen', wert: augen === 'schwer' ? -2 : -1 })
      }
      if (kontext.fernkampf && k.hatHandicap(HANDICAP.EINAEUGIG)) {
        liste.push({ name: 'Einäugig', wert: -EINAEUGIG_MALUS })
      }
    }
    return liste
  }

  /**
   * Sammelt alle Modifikatoren einer Probe (Wunden, Erschöpfung, Joker,
   * Berechnend, Handicaps) und würfelt.
   */
  private sammleModifikatoren(
    kaempfer: Kaempfer,
    eigenschaft: string,
    modifikatoren: Modifikator[],
    kontext: ProbenKontext,
  ): Modifikator[] {
    const liste = [...modifikatoren, ...this.situationsModifikatoren(kaempfer, eigenschaft, kontext)].filter(
      (m) => m.wert,
    )
    if (kaempfer.wundmalus) liste.push({ name: 'Wunden', wert: kaempfer.wundmalus })
    if (kaempfer.erschoepfungsmalus) liste.push({ name: 'Erschöpfung', wert: kaempfer.erschoepfungsmalus })
    if (kaempfer.linderungsbonus > 0) liste.push({ name: MACHT.LINDERUNG, wert: kaempfer.linderungsbonus })
    if (kaempfer.abgelenktmalus) liste.push({ name: 'Abgelenkt', wert: kaempfer.abgelenktmalus })
    if (kaempfer.hatJoker) liste.push({ name: 'Joker', wert: JOKER_BONUS })
    const malus = liste.filter((m) => m.wert < 0).reduce((s, m) => s + m.wert, 0)
    const karte = kaempfer.karte
    if (malus < 0 && kaempfer.hatTalent(TALENT.BERECHNEND) && karte && !karte.joker && karte.wert <= 5) {
      liste.push({ name: 'Berechnend', wert: Math.min(BERECHNEND_MAX_IGNORIERT, -malus) })
    }
    return liste
  }

  private wuerfleProbe(
    kaempfer: Kaempfer,
    eigenschaft: string,
    modifikatoren: Modifikator[],
    mindestwurf?: number,
    kontext: ProbenKontext = {},
  ): ProbenErgebnis {
    const liste = this.sammleModifikatoren(kaempfer, eigenschaft, modifikatoren, kontext)
    const { wuerfel, ungeuebt } = kaempfer.wuerfelFuer(eigenschaft)
    const ergebnis = Eigenschaftsprobe.wuerfle({
      wuerfel,
      wildcard: kaempfer.wildcard,
      modifikator: liste.reduce((s, m) => s + m.wert, 0),
      mindestwurf,
      zufall: this.zufall,
    })
    ergebnis.modifikatoren = liste
    ergebnis.ungeuebt = ungeuebt
    return ergebnis
  }

  private wuerfleMehrfachProbe(
    kaempfer: Kaempfer,
    eigenschaft: string,
    anzahl: number,
    modifikatoren: Modifikator[],
    mindestwurf: number,
    kontext: ProbenKontext,
  ): MehrfachProbe {
    const liste = this.sammleModifikatoren(kaempfer, eigenschaft, modifikatoren, kontext)
    const { wuerfel, ungeuebt } = kaempfer.wuerfelFuer(eigenschaft)
    const probe = wuerfleMehrfach({
      anzahl,
      wuerfel,
      wildcard: kaempfer.wildcard,
      modifikator: liste.reduce((s, m) => s + m.wert, 0),
      mindestwurf,
      zufall: this.zufall,
    })
    probe.modifikatoren = liste
    probe.ungeuebt = ungeuebt
    return probe
  }

  private static beschreibeModifikatoren(liste: Modifikator[]): string {
    const relevant = liste.filter((m) => m.wert)
    if (relevant.length === 0) return ''
    return ` [${relevant.map((m) => `${m.name} ${formatiereModifikator(m.wert)}`).join(', ')}]`
  }

  private static mehrfachaktion(aktionen?: number): Modifikator {
    return { name: 'Mehrfachaktion', wert: -MEHRFACHAKTION_MALUS * Math.max(0, (aktionen ?? 1) - 1) }
  }

  /** Freie Eigenschaftsprobe (Attribut oder Fertigkeit). */
  probe(kaempferId: string, eigenschaft: string, modifikator = 0, mindestwurf = MINDESTWURF): ProbenErgebnis | null {
    const kaempfer = this.finde(kaempferId)
    if (!kaempfer || !eigenschaft) return null
    const ergebnis = this.wuerfleProbe(kaempfer, eigenschaft, [{ name: 'Situativ', wert: modifikator }], mindestwurf, {
      sicht: eigenschaft === 'Wahrnehmung',
    })
    const zusatz = ergebnis.ungeuebt ? ' (ungeübt)' : ''
    this.protokolliere(
      `${kaempfer.name} – ${eigenschaft}${zusatz}: ${Eigenschaftsprobe.beschreibe(ergebnis)}` +
        KampfController.beschreibeModifikatoren(ergebnis.modifikatoren),
      ergebnis.erfolg ? 'erfolg' : 'fehlschlag',
    )
    return ergebnis
  }

  // --------------------------------------------------------------
  // Gemeinsame Prüfungen für Aktionen
  // --------------------------------------------------------------

  /**
   * Darf der Kämpfer jetzt eine (volle) Aktion ausführen?
   * @param koerperlich Gebundene können nur sich befreien (S. 103)
   */
  private pruefeAktion(k: Kaempfer | null, koerperlich = true): string | null {
    if (!k) return 'Kämpfer fehlt.'
    if (this.offenerSchaden) return 'Zuerst muss der offene Schaden abgehandelt werden.'
    if (k !== this.aktueller) return `${k.name} ist nicht am Zug.`
    if (k.betaeubt) return `${k.name} ist Betäubt und kann keine Aktionen ausführen.`
    if (k.schlaeft) return `${k.name} schläft und kann keine Aktionen ausführen.`
    if (!this.zugDarfHandeln || k.angeschlagen) {
      return `${k.name} ist Angeschlagen oder hat seinen Zug verbraucht und kann nur freie Aktionen ausführen.`
    }
    if (koerperlich && k.fessel === 'gebunden') {
      return `${k.name} ist Gebunden und kann nur versuchen, sich zu befreien.`
    }
    return null
  }

  // --------------------------------------------------------------
  // Angriff
  // --------------------------------------------------------------

  /** Talent-Stufe von Schneller Angriff: Zahl der zusätzlichen Kämpfen-Würfel. */
  static zusatzKaempfenWuerfel(k: Kaempfer): number {
    if (k.hatTalent(TALENT.BLITZSCHNELLER_ANGRIFF)) return 2
    if (k.hatTalent(TALENT.SCHNELLER_ANGRIFF)) return 1
    return 0
  }

  /** Überzahlbonus nach Block/Harter Block des Verteidigers (S. 107). */
  private static ueberzahl(ziel: Kaempfer, gegner?: number): number {
    let block = 0
    if (ziel.hatTalent(TALENT.HARTER_BLOCK)) block = 2
    else if (ziel.hatTalent(TALENT.BLOCK)) block = 1
    return Math.max(0, Math.min(MAX_UEBERZAHL, gegner ?? 0) - block)
  }

  private angriffsModifikatoren(
    angreifer: Kaempfer,
    ziel: Kaempfer,
    waffe: Waffe,
    optionen: AngriffsOptionen,
    art: { ruecksichtslos: boolean; verzweifelt: number },
  ): Modifikator[] {
    const nahkampf = waffe.istNahkampf
    const angesagt = ANGESAGTE_ZIELE[optionen.angesagtesZiel ?? 'keins']
    const modifikatoren: Modifikator[] = [
      { name: 'Situativ', wert: optionen.modifikator ?? 0 },
      KampfController.mehrfachaktion(optionen.aktionen),
      { name: angesagt.name, wert: angesagt.malus },
      { name: 'Beleuchtung', wert: optionen.beleuchtung ?? 0 },
    ]
    if (!nahkampf) modifikatoren.push({ name: 'Reichweite', wert: optionen.reichweite ?? 0 })
    // Ausweichen ist nicht kumulativ mit Deckung: es zählt der größere Abzug.
    const deckung = optionen.deckung ?? 0
    const ausweichen = !nahkampf && !optionen.ueberraschung && ziel.hatTalent(TALENT.AUSWEICHEN) ? -AUSWEICHEN_MALUS : 0
    if (ausweichen < deckung) modifikatoren.push({ name: 'Ausweichen', wert: ausweichen })
    else modifikatoren.push({ name: 'Deckung', wert: deckung })
    // Die kleinere Kreatur addiert die Differenz der Größenkategorien.
    modifikatoren.push({ name: 'Größenkategorie', wert: ziel.groessenKategorie - angreifer.groessenKategorie })
    const abwehr = ziel.abwehrMalus(nahkampf)
    if (abwehr) modifikatoren.push({ name: MACHT.ABWEHREN, wert: abwehr })
    // Überraschungsangriff ist weder mit Verwundbar noch mit Unbewaffneter
    // Verteidiger kumulativ – es zählt der höhere Bonus (+4).
    if (optionen.ueberraschung) {
      modifikatoren.push({ name: 'Überraschungsangriff', wert: UEBERRASCHUNG_BONUS })
    } else {
      modifikatoren.push({ name: 'Verwundbar', wert: ziel.verwundbarBonus })
      if (nahkampf && !ziel.istBewaffnet && (!waffe.istWaffenlos || angreifer.istBewaffnet)) {
        modifikatoren.push({ name: 'Unbewaffneter Verteidiger', wert: UNBEWAFFNETER_VERTEIDIGER_BONUS })
      }
    }
    if (nahkampf) modifikatoren.push({ name: 'Überzahl', wert: KampfController.ueberzahl(ziel, optionen.ueberzahl) })
    if (art.ruecksichtslos) modifikatoren.push({ name: 'Rücksichtslos', wert: RUECKSICHTSLOS_BONUS })
    if (art.verzweifelt) modifikatoren.push({ name: 'Verzweifelter Angriff', wert: art.verzweifelt })
    if (!nahkampf && optionen.doppelschuss && angreifer.hatTalent(TALENT.DOPPELSCHUSS)) {
      modifikatoren.push({ name: TALENT.DOPPELSCHUSS, wert: DOPPELSCHUSS_BONUS })
    }
    return modifikatoren
  }

  angriff(angreiferId: string, zielId: string, waffenIndex: number, optionen: AngriffsOptionen = {}): void {
    const angreifer = this.finde(angreiferId)
    const ziel = this.finde(zielId)
    const fehler = this.pruefeAktion(angreifer) ?? this.pruefeZiel(ziel)
    if (fehler || !angreifer || !ziel) {
      this.protokolliere(fehler ?? 'Angreifer oder Ziel fehlt.', 'warnung')
      return
    }
    const waffe = angreifer.waffen[waffenIndex] ?? angreifer.waffen[0]
    const paradeVorher = angreifer.aktuelleParade
    angreifer.fuehre(waffe)
    if (angreifer.aktuelleParade !== paradeVorher) {
      this.protokolliere(`${angreifer.name} führt jetzt ${waffe.name} (Parade ${angreifer.aktuelleParade}).`)
    }
    const nahkampf = waffe.istNahkampf
    // Im Berserkerrausch müssen alle Angriffe Rücksichtslos sein.
    const ruecksichtslos = nahkampf && Boolean(optionen.ruecksichtslos || angreifer.berserker)
    // Verzweifelter Angriff lässt sich nicht mit Rücksichtslos kombinieren.
    const verzweifelt = nahkampf && !ruecksichtslos ? Math.max(0, optionen.verzweifelt ?? 0) : 0
    const modifikatoren = this.angriffsModifikatoren(angreifer, ziel, waffe, optionen, { ruecksichtslos, verzweifelt })
    const mindestwurf = nahkampf ? ziel.aktuelleParade : MINDESTWURF
    const kontext: ProbenKontext = { sicht: true, fernkampf: !nahkampf }
    const zusatzWuerfel =
      nahkampf && optionen.schnellerAngriff ? KampfController.zusatzKaempfenWuerfel(angreifer) : 0

    if (ruecksichtslos) {
      angreifer.setzeVerwundbar(VERWUNDBAR_BIS_NAECHSTER_ZUG)
    }
    const schaden = { ruecksichtslos, verzweifelt, optionen }

    if (zusatzWuerfel > 0) {
      const probe = this.wuerfleMehrfachProbe(angreifer, waffe.fertigkeit, 1 + zusatzWuerfel, modifikatoren, mindestwurf, kontext)
      const talent = zusatzWuerfel === 2 ? TALENT.BLITZSCHNELLER_ANGRIFF : TALENT.SCHNELLER_ANGRIFF
      this.protokolliere(
        `${angreifer.name} greift ${ziel.name} mit ${waffe.name} an (${talent}, ${waffe.fertigkeit}` +
          `${probe.ungeuebt ? ', ungeübt' : ''}): ${beschreibeMehrfach(probe)}` +
          KampfController.beschreibeModifikatoren(probe.modifikatoren),
        probe.treffer.some((t) => t.erfolg) ? 'erfolg' : 'fehlschlag',
      )
      this.nachAngriffswurf(angreifer, waffe, ruecksichtslos, probe.kritisch)
      probe.treffer
        .filter((t) => t.erfolg)
        .forEach((t) => this.plane(() => this.wuerfleSchaden(angreifer, ziel, waffe, t.steigerungen, schaden)))
      this.arbeiteWarteschlangeAb()
      return
    }

    const probe = this.wuerfleProbe(angreifer, waffe.fertigkeit, modifikatoren, mindestwurf, kontext)
    this.protokolliere(
      `${angreifer.name} greift ${ziel.name} mit ${waffe.name} an (${waffe.fertigkeit}` +
        `${probe.ungeuebt ? ', ungeübt' : ''}): ${Eigenschaftsprobe.beschreibe(probe)}` +
        KampfController.beschreibeModifikatoren(probe.modifikatoren),
      probe.erfolg ? 'erfolg' : 'fehlschlag',
    )
    this.nachAngriffswurf(angreifer, waffe, ruecksichtslos, probe.kritisch)
    if (probe.erfolg) this.wuerfleSchaden(angreifer, ziel, waffe, probe.steigerungen, schaden)
  }

  private nachAngriffswurf(angreifer: Kaempfer, waffe: Waffe, ruecksichtslos: boolean, kritisch: boolean): void {
    if (ruecksichtslos) {
      this.protokolliere(`${angreifer.name} greift Rücksichtslos an und ist bis zum Ende des nächsten Zuges Verwundbar.`)
    }
    if (!kritisch) return
    if (angreifer.berserker && waffe.istNahkampf) {
      this.protokolliere(
        `${angreifer.name}: Kritischer Fehlschlag im Berserkerrausch – der Schlag trifft ein zufälliges Ziel in Reichweite (Freund oder Feind, SL).`,
        'warnung',
      )
      return
    }
    this.protokolliere(`${angreifer.name}: Kritischer Fehlschlag – die Spielleitung bestimmt die Folgen.`, 'warnung')
  }

  private pruefeZiel(ziel: Kaempfer | null): string | null {
    if (!ziel) return 'Ziel fehlt.'
    if (!ziel.istKampffaehig) return `${ziel.name} ist bereits Außer Gefecht.`
    return null
  }

  /** Weiteren Schritt einreihen (nächster Treffer derselben Aktion). */
  private plane(schritt: () => void): void {
    this.warteschlange.push(schritt)
  }

  /** Arbeitet Treffer ab, bis einer auf eine Entscheidung (Wegstecken) wartet. */
  private arbeiteWarteschlangeAb(): void {
    while (!this.offenerSchaden && this.warteschlange.length) {
      this.warteschlange.shift()!()
    }
  }

  private wuerfleSchaden(
    angreifer: Kaempfer,
    ziel: Kaempfer,
    waffe: Waffe,
    steigerungen: number,
    art: { ruecksichtslos: boolean; verzweifelt: number; optionen: AngriffsOptionen },
  ): void {
    if (!this.kaempfer.includes(ziel)) return
    if (!ziel.istKampffaehig) {
      this.protokolliere(`${ziel.name} ist bereits Außer Gefecht – der Treffer geht ins Leere.`)
      return
    }
    if (!waffe.formel) {
      this.protokolliere(`Schadensangabe „${waffe.schaden}" von ${waffe.name} ist nicht auswertbar.`, 'warnung')
      return
    }
    const optionen = art.optionen
    const boni: Modifikator[] = []
    if (angreifer.hatJoker) boni.push({ name: 'Joker', wert: JOKER_BONUS })
    if (art.ruecksichtslos) boni.push({ name: 'Rücksichtslos', wert: RUECKSICHTSLOS_BONUS })
    if (art.verzweifelt) boni.push({ name: 'Verzweifelter Angriff', wert: -art.verzweifelt })
    const angesagt = ANGESAGTE_ZIELE[optionen.angesagtesZiel ?? 'keins']
    if (angesagt.schaden) boni.push({ name: angesagt.name, wert: angesagt.schaden })
    if (optionen.ueberraschung) boni.push({ name: 'Überraschungsangriff', wert: UEBERRASCHUNG_BONUS })
    if (!waffe.istNahkampf && optionen.doppelschuss && angreifer.hatTalent(TALENT.DOPPELSCHUSS)) {
      boni.push({ name: TALENT.DOPPELSCHUSS, wert: DOPPELSCHUSS_BONUS })
    }
    if (waffe.istNahkampf && this.anfuehrerBonus(angreifer, TALENT.ANHEIZEN)) {
      boni.push({ name: TALENT.ANHEIZEN, wert: ANFUEHRER_BONUS })
    }
    // Arkane Resistenz verringert auch magische Waffenboni (Waffe verbessern).
    if (angreifer.schadensbonus) {
      const bonus = Math.max(0, angreifer.schadensbonus - ziel.arkaneAbwehr)
      boni.push({ name: MACHT.WAFFE_VERBESSERN, wert: bonus })
    }
    const notizen = boni.filter((b) => b.wert).map((b) => `${b.name} ${formatiereModifikator(b.wert)}`)
    const verdoppeln = this.pruefeVerdopplung(angreifer, waffe)
    if (verdoppeln) notizen.push(verdoppeln)
    const riesentoeter = this.riesentoeter(angreifer, ziel)
    if (riesentoeter) notizen.push('Riesentöter +W6')

    const schaden = SchadensRegeln.wuerfle({
      formel: waffe.formel,
      staerke: angreifer.staerke,
      mindeststaerke: waffe.mindeststaerke,
      steigerung: steigerungen > 0,
      zusatzWuerfel: riesentoeter ? [6] : [],
      modifikator: boni.reduce((s, b) => s + b.wert, 0),
      verdoppeln: Boolean(verdoppeln),
      zufall: this.zufall,
    })
    const robustheit = this.robustheitVon(ziel, waffe.pb)
    const bewertung = SchadensRegeln.bewerte(schaden.gesamt, robustheit, ziel.angeschlagen, ziel.zaeh)
    const zusatz = [steigerungen > 0 ? 'Steigerung +W6' : '', ...notizen, waffe.pb ? `PB ${waffe.pb}` : '']
      .filter(Boolean)
      .join(', ')

    this.protokolliere(
      `Schaden ${waffe.schaden} gegen ${ziel.name}${zusatz ? ` (${zusatz})` : ''}: ${SchadensRegeln.beschreibe(schaden)}` +
        ` gegen Robustheit ${robustheit}.`,
    )
    this.verarbeiteTreffer(ziel, bewertung)
  }

  /** Riesentöter: +W6 gegen Kreaturen, die mindestens 3 Größenstufen größer sind. */
  private riesentoeter(angreifer: Kaempfer, ziel: Kaempfer): boolean {
    return angreifer.hatTalent(TALENT.RIESENTOETER) && ziel.groesse - angreifer.groesse >= RIESENTOETER_GROESSE
  }

  /** Mächtiger Hieb / Volltreffer: erster erfolgreicher Angriff mit Joker verdoppelt den Schaden. */
  private pruefeVerdopplung(angreifer: Kaempfer, waffe: Waffe): string | null {
    if (!angreifer.hatJoker) return null
    if (waffe.istNahkampf && angreifer.hatTalent(TALENT.MAECHTIGER_HIEB) && !angreifer.maechtigerHiebGenutzt) {
      angreifer.maechtigerHiebGenutzt = true
      return 'Mächtiger Hieb ×2'
    }
    if (!waffe.istNahkampf && angreifer.hatTalent(TALENT.VOLLTREFFER) && !angreifer.volltrefferGenutzt) {
      angreifer.volltrefferGenutzt = true
      return 'Volltreffer ×2'
    }
    return null
  }

  private verarbeiteTreffer(ziel: Kaempfer, bewertung: TrefferBewertung): void {
    if (bewertung.ergebnis === 'kein') {
      this.protokolliere(`Der Treffer prallt an ${ziel.name} ab.`)
      return
    }
    if (bewertung.ergebnis === 'angeschlagen') {
      // Zäh fängt genau hier die Wunde ab, die ein zweites Angeschlagen
      // sonst verursachen würde — im Protokoll sichtbar machen.
      const zaehGriff = ziel.zaeh && ziel.angeschlagen
      this.protokolliere(ziel.nimmSchaden(0, true), 'schaden')
      if (zaehGriff) this.protokolliere(`${ziel.name} ist Zäh – das zweite Angeschlagen verursacht keine Wunde.`)
      this.nachKoerperlichemSchaden(ziel)
      return
    }
    if (ziel.wildcard && ziel.bennys > 0) {
      this.offenerSchaden = { ziel, wunden: bewertung.wunden, reduziert: 0, versuche: 0 }
      this.protokolliere(`${ziel.name} droht ${bewertung.wunden} Wunde(n) – Schaden wegstecken?`, 'warnung')
      return
    }
    this.protokolliere(ziel.nimmSchaden(bewertung.wunden, true), 'schaden')
    this.nachKoerperlichemSchaden(ziel)
    this.pruefeKampfende()
  }

  /**
   * Folgen körperlichen Schadens (Angeschlagen oder Wunde): Schlafende
   * dürfen versuchen aufzuwachen, Berserker können in Rage geraten.
   */
  private nachKoerperlichemSchaden(ziel: Kaempfer): void {
    if (!ziel.istKampffaehig) return
    if (ziel.schlaeft) {
      const probe = this.wuerfleProbe(ziel, ATTRIBUT.WILLENSKRAFT, [])
      if (probe.erfolg) {
        ziel.schlaeft = false
        this.protokolliere(`${ziel.name} wacht auf: ${Eigenschaftsprobe.beschreibe(probe)}.`, 'erfolg')
      } else {
        this.protokolliere(`${ziel.name} schläft weiter: ${Eigenschaftsprobe.beschreibe(probe)}.`, 'fehlschlag')
      }
    }
    if (ziel.hatTalent(TALENT.BERSERKER) && !ziel.berserker) {
      const probe = this.wuerfleProbe(ziel, ATTRIBUT.VERSTAND, [])
      if (probe.erfolg) {
        this.protokolliere(
          `${ziel.name} beherrscht den roten Zorn (Berserker): ${Eigenschaftsprobe.beschreibe(probe)}.`,
          'erfolg',
        )
        return
      }
      this.starteBerserker(ziel, `Verstandsprobe misslungen: ${Eigenschaftsprobe.beschreibe(probe)}`)
    }
  }

  // --------------------------------------------------------------
  // Berserker
  // --------------------------------------------------------------

  private starteBerserker(k: Kaempfer, grund: string): void {
    k.berserker = true
    k.berserkerRunden = 0
    this.protokolliere(
      `${k.name} verfällt in den Berserkerrausch (${grund}): Stärke +1 Würfeltyp, Robustheit +2, ` +
        'eine Stufe Wundabzüge ignoriert, alle Nahkampfangriffe Rücksichtslos.',
      'warnung',
    )
  }

  private zaehleBerserkerRunde(k: Kaempfer): void {
    k.berserkerRunden += 1
    if (k.berserkerRunden === BERSERKER_ERSCHOEPFUNG_RUNDEN) {
      this.protokolliere(`${k.name} wütet seit ${BERSERKER_ERSCHOEPFUNG_RUNDEN} Runden und ist erschöpft.`, 'warnung')
      this.erschoepfe(k)
    } else if (k.berserkerRunden >= BERSERKER_MAX_RUNDEN) {
      k.berserker = false
      this.protokolliere(`Nach ${BERSERKER_MAX_RUNDEN} Runden endet der Berserkerrausch von ${k.name}.`, 'warnung')
      this.erschoepfe(k)
    }
  }

  /** Berserkerrausch bewusst beenden: freie Verstandsprobe mit –2. */
  beendeBerserker(id: string): void {
    const k = this.finde(id)
    if (!k || !k.berserker) return
    const probe = this.wuerfleProbe(k, ATTRIBUT.VERSTAND, [{ name: 'Rausch beenden', wert: -BERSERKER_ENDE_MALUS }])
    if (probe.erfolg) {
      k.berserker = false
      this.protokolliere(`${k.name} beendet den Berserkerrausch: ${Eigenschaftsprobe.beschreibe(probe)}.`, 'erfolg')
    } else {
      this.protokolliere(`${k.name} bleibt im Berserkerrausch: ${Eigenschaftsprobe.beschreibe(probe)}.`, 'fehlschlag')
    }
  }

  schalteBerserker(id: string): void {
    const k = this.finde(id)
    if (!k) return
    if (k.berserker) {
      k.berserker = false
      this.protokolliere(`${k.name}: Berserkerrausch beendet (manuell).`)
    } else {
      this.starteBerserker(k, 'manuell')
    }
  }

  /** Eine Stufe Erschöpfung; die dritte schaltet aus. */
  private erschoepfe(k: Kaempfer, stufen = 1): void {
    k.erschoepfung += stufen
    if (k.erschoepfung >= MAX_ERSCHOEPFUNG) {
      k.ausserGefecht = true
      this.protokolliere(`${k.name} ist durch Erschöpfung Ausgeschaltet.`, 'schaden')
      this.pruefeKampfende()
    }
  }

  // --------------------------------------------------------------
  // Kampfoptionen: Verteidigen, Herausfordern, Ringen
  // --------------------------------------------------------------

  /** Verteidigen (S. 108): Parade +4, verbraucht den ganzen Zug. */
  verteidigen(id: string): void {
    const k = this.finde(id)
    const fehler = this.pruefeAktion(k)
    if (fehler || !k) {
      this.protokolliere(fehler ?? 'Kämpfer fehlt.', 'warnung')
      return
    }
    k.verteidigt = true
    this.zugDarfHandeln = false
    this.protokolliere(
      `${k.name} verteidigt sich: Parade +${VERTEIDIGEN_BONUS} (jetzt ${k.aktuelleParade}) bis zum nächsten Zug.`,
      'erfolg',
    )
  }

  /**
   * Herausfordern (S. 104): vergleichender Wurf gegen das mit der
   * Fertigkeit verknüpfte Attribut. Sieg: Abgelenkt oder Verwundbar, mit
   * Steigerung zusätzlich Angeschlagen.
   */
  herausfordern(angreiferId: string, zielId: string, optionen: HerausfordernOptionen): void {
    const angreifer = this.finde(angreiferId)
    const ziel = this.finde(zielId)
    const verbal = VERBALE_FERTIGKEITEN.includes(optionen.fertigkeit)
    const fehler = this.pruefeAktion(angreifer, !verbal) ?? this.pruefeZiel(ziel)
    if (fehler || !angreifer || !ziel) {
      this.protokolliere(fehler ?? 'Angreifer oder Ziel fehlt.', 'warnung')
      return
    }
    let widerstand = HERAUSFORDERN_ATTRIBUT[optionen.fertigkeit] ?? ATTRIBUT.VERSTAND
    // Finte: der Feind widersteht einer Kämpfen-Herausforderung mit Verstand.
    if (optionen.fertigkeit === FERTIGKEIT.KAEMPFEN && angreifer.hatTalent(TALENT.FINTE)) widerstand = ATTRIBUT.VERSTAND

    const probe = this.wuerfleProbe(
      angreifer,
      optionen.fertigkeit,
      [{ name: 'Situativ', wert: optionen.modifikator ?? 0 }, KampfController.mehrfachaktion(optionen.aktionen)],
      MINDESTWURF,
      { sicht: !verbal, fernkampf: optionen.fertigkeit === FERTIGKEIT.SCHIESSEN },
    )
    const gegenwehr = this.wuerfleProbe(ziel, widerstand, this.widerstandGegenHerausfordern(ziel, optionen.fertigkeit))
    const ergebnis = vergleiche(probe, gegenwehr)
    this.protokolliere(
      `${angreifer.name} fordert ${ziel.name} mit ${optionen.fertigkeit} heraus: ${Eigenschaftsprobe.beschreibe(probe)}` +
        `${KampfController.beschreibeModifikatoren(probe.modifikatoren)} – ${ziel.name} widersteht mit ${widerstand}: ` +
        `${Eigenschaftsprobe.beschreibe(gegenwehr)}${KampfController.beschreibeModifikatoren(gegenwehr.modifikatoren)}`,
      ergebnis.gewonnen ? 'erfolg' : 'fehlschlag',
    )
    if (!ergebnis.gewonnen) {
      this.protokolliere(`${ziel.name} lässt sich nicht aus dem Konzept bringen.`)
      return
    }
    if (optionen.wirkung === 'abgelenkt') ziel.setzeAbgelenkt()
    else ziel.setzeVerwundbar()
    const zustand = optionen.wirkung === 'abgelenkt' ? 'Abgelenkt' : 'Verwundbar'
    if (ergebnis.steigerungen > 0) {
      // Ein zweites Angeschlagen durch Herausfordern verursacht keine Wunde.
      ziel.angeschlagen = true
      this.protokolliere(`${ziel.name} ist ${zustand} und durch die Steigerung Angeschlagen.`, 'schaden')
    } else {
      this.protokolliere(`${ziel.name} ist ${zustand} bis zum Ende seines nächsten Zuges.`, 'schaden')
    }
  }

  private widerstandGegenHerausfordern(ziel: Kaempfer, fertigkeit: string): Modifikator[] {
    const liste: Modifikator[] = []
    const duennhaeutig = ziel.handicapStufe(HANDICAP.DUENNHAEUTIG)
    if (fertigkeit === 'Provozieren' && duennhaeutig) {
      liste.push({ name: 'Dünnhäutig', wert: duennhaeutig === 'schwer' ? -4 : -2 })
    }
    if (fertigkeit === 'Einschüchtern' && ziel.hatHandicap(HANDICAP.FEIGE)) {
      liste.push({ name: 'Feige', wert: -FEIGE_MALUS })
    }
    if (fertigkeit === FERTIGKEIT.ATHLETIK && ziel.handicapStufe(HANDICAP.LANGSAM) === 'schwer') {
      liste.push({ name: 'Langsam', wert: -LANGSAM_MALUS })
    }
    return liste
  }

  /**
   * Ringen (S. 105): vergleichende Athletikprobe. Sieg: Festgehalten, mit
   * Steigerung (oder gegen bereits Festgehaltene) Gebunden. Der Angreifer
   * zieht einen Größenkategorie-Unterschied ab.
   */
  ringen(angreiferId: string, zielId: string, optionen: RingenOptionen = {}): void {
    const angreifer = this.finde(angreiferId)
    const ziel = this.finde(zielId)
    const fehler = this.pruefeAktion(angreifer) ?? this.pruefeZiel(ziel)
    if (fehler || !angreifer || !ziel) {
      this.protokolliere(fehler ?? 'Angreifer oder Ziel fehlt.', 'warnung')
      return
    }
    const probe = this.wuerfleProbe(angreifer, FERTIGKEIT.ATHLETIK, [
      { name: 'Situativ', wert: optionen.modifikator ?? 0 },
      KampfController.mehrfachaktion(optionen.aktionen),
      { name: 'Größenkategorie', wert: -Math.abs(ziel.groessenKategorie - angreifer.groessenKategorie) },
      { name: 'Überzahl', wert: KampfController.ueberzahl(ziel, optionen.ueberzahl) },
    ])
    const gegenwehr = this.wuerfleProbe(ziel, FERTIGKEIT.ATHLETIK, this.widerstandGegenHerausfordern(ziel, FERTIGKEIT.ATHLETIK))
    const ergebnis = vergleiche(probe, gegenwehr)
    this.protokolliere(
      `${angreifer.name} ringt mit ${ziel.name}: ${Eigenschaftsprobe.beschreibe(probe)}` +
        `${KampfController.beschreibeModifikatoren(probe.modifikatoren)} – ${ziel.name} wehrt sich: ` +
        `${Eigenschaftsprobe.beschreibe(gegenwehr)}${KampfController.beschreibeModifikatoren(gegenwehr.modifikatoren)}`,
      ergebnis.gewonnen ? 'erfolg' : 'fehlschlag',
    )
    if (!ergebnis.gewonnen) {
      this.protokolliere(`${ziel.name} entwindet sich dem Griff.`)
      return
    }
    const fessel: Fessel = ergebnis.steigerungen > 0 || ziel.fessel !== 'frei' ? 'gebunden' : 'festgehalten'
    ziel.setzeFessel(fessel, angreifer.id)
    this.aktualisiereFesseln()
    this.protokolliere(
      fessel === 'gebunden'
        ? `${ziel.name} ist Gebunden (Abgelenkt, Verwundbar, nur Befreien möglich). ${angreifer.name} ist Verwundbar, solange er festhält.`
        : `${ziel.name} ist Festgehalten (kann sich nicht bewegen, Verwundbar).`,
      'schaden',
    )
  }

  /** Zerquetschen (S. 105): Stärkeschaden gegen ein festgehaltenes Opfer, ohne Angriffswurf. */
  zerquetschen(angreiferId: string, zielId: string): void {
    const angreifer = this.finde(angreiferId)
    const ziel = this.finde(zielId)
    const fehler = this.pruefeAktion(angreifer) ?? this.pruefeZiel(ziel)
    if (fehler || !angreifer || !ziel) {
      this.protokolliere(fehler ?? 'Angreifer oder Ziel fehlt.', 'warnung')
      return
    }
    if (ziel.gehaltenVon !== angreifer.id) {
      this.protokolliere(`${angreifer.name} hält ${ziel.name} nicht fest.`, 'warnung')
      return
    }
    this.protokolliere(`${angreifer.name} zerquetscht ${ziel.name}.`)
    this.wuerfleSchaden(angreifer, ziel, new Waffe({ name: 'Zerquetschen', schaden: 'Stä' }), 0, {
      ruecksichtslos: false,
      verzweifelt: 0,
      optionen: {},
    })
  }

  /** Sich befreien (S. 103): Aktion mit Stärke –2 oder Athletik. */
  befreien(id: string, eigenschaft: string, optionen: AktionsOptionen = {}): void {
    const k = this.finde(id)
    const fehler = this.pruefeAktion(k, false)
    if (fehler || !k) {
      this.protokolliere(fehler ?? 'Kämpfer fehlt.', 'warnung')
      return
    }
    if (k.fessel === 'frei') {
      this.protokolliere(`${k.name} ist weder Festgehalten noch Gebunden.`, 'warnung')
      return
    }
    const modifikatoren: Modifikator[] = [
      { name: 'Situativ', wert: optionen.modifikator ?? 0 },
      KampfController.mehrfachaktion(optionen.aktionen),
    ]
    if (eigenschaft === ATTRIBUT.STAERKE) modifikatoren.push({ name: 'Befreien', wert: -BEFREIEN_STAERKE_MALUS })
    const probe = this.wuerfleProbe(k, eigenschaft, modifikatoren)
    const text = `${k.name} versucht sich zu befreien (${eigenschaft}): ${Eigenschaftsprobe.beschreibe(probe)}${KampfController.beschreibeModifikatoren(probe.modifikatoren)}`
    if (!probe.erfolg) {
      this.protokolliere(`${text}. Es gelingt nicht.`, 'fehlschlag')
      return
    }
    const neu: Fessel = k.fessel === 'gebunden' && probe.steigerungen === 0 ? 'festgehalten' : 'frei'
    k.setzeFessel(neu, k.gehaltenVon)
    this.aktualisiereFesseln()
    this.protokolliere(`${text}. ${k.name} ist ${neu === 'frei' ? 'frei' : 'nur noch Festgehalten'}.`, 'erfolg')
  }

  /** Ringen beenden (freie Aktion des Festhaltenden) oder Fessel manuell lösen. */
  loeseFessel(id: string): void {
    const k = this.finde(id)
    if (!k || k.fessel === 'frei') return
    k.setzeFessel('frei')
    this.aktualisiereFesseln()
    this.protokolliere(`${k.name} ist nicht mehr Festgehalten oder Gebunden.`)
  }

  /**
   * Ringer, deren Opfer Gebunden ist, sind Verwundbar; fällt der Ringer aus
   * oder verlässt den Kampf, endet sein Griff.
   */
  private aktualisiereFesseln(): void {
    this.kaempfer.forEach((k) => {
      if (!k.gehaltenVon) return
      const ringer = this.finde(k.gehaltenVon)
      if (!ringer || !ringer.istKampffaehig) {
        k.setzeFessel('frei')
        this.protokolliere(`${k.name} kommt frei – niemand hält ihn mehr fest.`)
      }
    })
    this.kaempfer.forEach((k) => {
      k.haeltGebunden = this.kaempfer.some((o) => o.gehaltenVon === k.id && o.fessel === 'gebunden')
    })
  }

  // --------------------------------------------------------------
  // Mächte
  // --------------------------------------------------------------

  /** Feindliche Macht: Arkane Resistenz und Arkaner Schutz greifen. */
  private static istFeindlich(macht: MachtDefinition, optionen: MachtOptionen): boolean {
    if (macht.ziel === 'gegner') return true
    return macht.name === MACHT.EIGENSCHAFT && optionen.eigenschaftModus === 'senken'
  }

  /** Mögliche Ziele einer Macht — je nachdem, ob sie Freund oder Feind trifft. */
  moeglicheMachtZiele(wirker: Kaempfer, machtName: string, modus: EigenschaftModus = 'erhoehen'): Kaempfer[] {
    const macht = machtDefinition(machtName)
    if (!macht) return []
    if (KampfController.istFeindlich(macht, { eigenschaftModus: modus })) {
      return this.kaempfer.filter((k) => k !== wirker && k.seite !== wirker.seite && k.istKampffaehig)
    }
    return this.kaempfer.filter((k) => k.seite === wirker.seite)
  }

  /**
   * Wirkt eine Macht auf ein oder mehrere Ziele. Das ist eine **volle
   * Aktion**: sie unterliegt dem Mehrfachaktionsabzug und ist Angeschlagenen
   * und Gebundenen verwehrt. Machtpunkte werden auch bei Misserfolg fällig.
   *
   * Die Aktivierung entscheidet der Wurf mit den Modifikatoren des Wirkers;
   * Abzüge, die am Ziel hängen (Arkane Resistenz, Ausweichen, Deckung …),
   * entscheiden danach je Ziel, ob und wie stark die Macht wirkt.
   */
  wirkeMacht(wirkerId: string, machtName: string, zielIds: string | string[], optionen: MachtOptionen = {}): void {
    const wirker = this.finde(wirkerId)
    const ziele = (Array.isArray(zielIds) ? zielIds : [zielIds])
      .map((id) => this.finde(id))
      .filter((k): k is Kaempfer => Boolean(k))
    const macht = machtDefinition(machtName)
    const gewaehlt = optionen.modifikatoren ?? []
    const fehler = this.pruefeMacht(wirker, ziele, macht, gewaehlt, optionen)
    if (fehler || !wirker || !macht) {
      this.protokolliere(fehler ?? 'Macht konnte nicht gewirkt werden.', 'warnung')
      return
    }

    const kosten = machtKosten(macht, gewaehlt, ziele.length)
    const aufAndere = ziele.some((z) => z !== wirker)
    const probe = this.wuerfleProbe(
      wirker,
      wirker.arkaneFertigkeit,
      [
        { name: 'Situativ', wert: optionen.modifikator ?? 0 },
        KampfController.mehrfachaktion(optionen.aktionen),
        { name: 'Beleuchtung', wert: aufAndere ? optionen.beleuchtung ?? 0 : 0 },
      ],
      MACHT_MINDESTWURF,
      { sicht: aufAndere },
    )
    const zusatz = gewaehlt.length ? ` [${gewaehlt.join(', ')}]` : ''

    this.protokolliere(
      `${wirker.name} wirkt ${macht.name}${zusatz} auf ${ziele.map((z) => z.name).join(', ')} (${wirker.arkaneFertigkeit}): ` +
        `${Eigenschaftsprobe.beschreibe(probe)}` +
        KampfController.beschreibeModifikatoren(probe.modifikatoren),
      probe.erfolg ? 'erfolg' : 'fehlschlag',
    )

    if (this.istRueckschlag(wirker, probe)) {
      this.rueckschlag(wirker)
      return
    }
    if (!probe.erfolg) {
      // Fehlschlag kostet trotzdem einen Machtpunkt.
      wirker.machtpunkte = Math.max(0, wirker.machtpunkte - MINDESTKOSTEN)
      this.protokolliere(
        `${macht.name} wird nicht aktiviert. ${MINDESTKOSTEN} Machtpunkt verbraucht ` +
          `(${wirker.machtpunkte}/${wirker.maxMachtpunkte} übrig).`,
      )
      return
    }

    wirker.machtpunkte = Math.max(0, wirker.machtpunkte - kosten)
    this.protokolliere(
      `${kosten} Machtpunkt(e) verbraucht (${wirker.machtpunkte}/${wirker.maxMachtpunkte} übrig).`,
    )
    ziele.forEach((ziel) => {
      this.plane(() => this.wendeMachtAufZielAn(wirker, ziel, macht, probe, gewaehlt, optionen))
    })
    this.arbeiteWarteschlangeAb()
  }

  /**
   * Kritischer Fehlschlag beim Wirken: Wildcards bei Doppel-1, Statisten
   * bei einer 1 auf dem Fertigkeitswürfel und einer 1 auf einem
   * zusätzlichen W6 (S. 88).
   */
  private istRueckschlag(wirker: Kaempfer, probe: ProbenErgebnis): boolean {
    if (probe.kritisch) return true
    if (wirker.wildcard || probe.eigenschaftsWurf.wuerfe[0] !== 1) return false
    const pruefwurf = this.zufall.wuerfle(6)
    this.protokolliere(`${wirker.name} würfelt eine 1 – Prüfwurf auf Kritischen Fehlschlag: W6[${pruefwurf}].`)
    return pruefwurf === 1
  }

  private pruefeMacht(
    wirker: Kaempfer | null,
    ziele: Kaempfer[],
    macht: MachtDefinition | null,
    gewaehlt: readonly string[],
    optionen: MachtOptionen,
  ): string | null {
    if (!wirker || ziele.length === 0) return 'Wirker oder Ziel fehlt.'
    if (!macht) return 'Diese Macht ist im Simulator nicht hinterlegt.'
    // Mächte sind volle Aktionen; Gebundene können nicht wirken (S. 151).
    const aktion = this.pruefeAktion(wirker)
    if (aktion) return aktion
    if (!wirker.istWirker) return `${wirker.name} beherrscht keine Mächte.`
    if (!wirker.maechte.includes(macht.name)) return `${wirker.name} beherrscht ${macht.name} nicht.`
    if (ziele.length > 1 && !erlaubtMehrereZiele(macht, gewaehlt)) {
      return `${macht.name} erfasst ohne Flächeneffekt nur ein Ziel.`
    }
    if (macht.name === MACHT.EIGENSCHAFT && !optionen.eigenschaft) return 'Welche Eigenschaft soll verändert werden?'
    const kosten = machtKosten(macht, gewaehlt, ziele.length)
    if (wirker.machtpunkte < kosten) {
      return `${wirker.name} hat nur ${wirker.machtpunkte} Machtpunkte, ${macht.name} kostet ${kosten}.`
    }
    const erlaubt = this.moeglicheMachtZiele(wirker, macht.name, optionen.eigenschaftModus)
    const unpassend = ziele.find((z) => !erlaubt.includes(z))
    if (unpassend) return `${unpassend.name} ist kein gültiges Ziel für ${macht.name}.`
    return null
  }

  /** Kritischer Fehlschlag: Erschöpfung und alle eigenen Mächte enden. */
  private rueckschlag(wirker: Kaempfer): void {
    wirker.machtpunkte = Math.max(0, wirker.machtpunkte - MINDESTKOSTEN)
    this.protokolliere(
      `Rückschlag! ${wirker.name} erleidet eine Stufe Erschöpfung, alle seine aktiven Mächte enden.`,
      'warnung',
    )
    this.kaempfer.forEach((k) => k.beendeEffekteVon(wirker.id).forEach((n) => this.protokolliere(n)))
    this.erschoepfe(wirker, RUECKSCHLAG_ERSCHOEPFUNG)
  }

  /**
   * Abzüge am Ziel: feindliche Mächte leiden unter Arkaner Resistenz und
   * Arkanem Schutz; Geschoss ist zudem ein Fernkampfangriff (Ausweichen,
   * Deckung, Abwehren, Größe), gezielte Mächte profitieren von Verwundbar.
   */
  private zielModifikatoren(
    wirker: Kaempfer,
    ziel: Kaempfer,
    macht: MachtDefinition,
    gewaehlt: readonly string[],
    optionen: MachtOptionen,
  ): Modifikator[] {
    const liste: Modifikator[] = []
    if (!KampfController.istFeindlich(macht, optionen)) return liste
    if (ziel.arkaneAbwehr) liste.push({ name: 'Arkane Resistenz/Schutz', wert: -ziel.arkaneAbwehr })
    const flaeche = erlaubtMehrereZiele(macht, gewaehlt) && !macht.empfaengerKosten
    if (flaeche) return liste
    liste.push({ name: 'Verwundbar', wert: ziel.verwundbarBonus })
    if (macht.name === MACHT.GESCHOSS) {
      const deckung = optionen.deckung ?? 0
      const ausweichen = ziel.hatTalent(TALENT.AUSWEICHEN) ? -AUSWEICHEN_MALUS : 0
      if (ausweichen < deckung) liste.push({ name: 'Ausweichen', wert: ausweichen })
      else liste.push({ name: 'Deckung', wert: deckung })
      liste.push({ name: MACHT.ABWEHREN, wert: ziel.abwehrMalus(false) })
      liste.push({ name: 'Größenkategorie', wert: ziel.groessenKategorie - wirker.groessenKategorie })
    }
    return liste.filter((m) => m.wert)
  }

  private wendeMachtAufZielAn(
    wirker: Kaempfer,
    ziel: Kaempfer,
    macht: MachtDefinition,
    probe: ProbenErgebnis,
    gewaehlt: readonly string[],
    optionen: MachtOptionen,
  ): void {
    if (!this.kaempfer.includes(ziel)) return
    const mods = this.zielModifikatoren(wirker, ziel, macht, gewaehlt, optionen)
    const gesamt = probe.gesamt + mods.reduce((s, m) => s + m.wert, 0)
    if (mods.length) {
      this.protokolliere(
        `Gegen ${ziel.name}: ${probe.gesamt}${KampfController.beschreibeModifikatoren(mods)} = ${gesamt}.`,
      )
    }
    if (gesamt < MACHT_MINDESTWURF) {
      this.protokolliere(
        macht.typ === 'angriff' ? `${macht.name} verfehlt ${ziel.name}.` : `${macht.name} wirkt nicht auf ${ziel.name}.`,
        'fehlschlag',
      )
      return
    }
    const steigerung = gesamt - MACHT_MINDESTWURF >= 4
    this.wendeMachtAn(wirker, ziel, macht, steigerung, gewaehlt, optionen)
  }

  private wendeMachtAn(
    wirker: Kaempfer,
    ziel: Kaempfer,
    macht: MachtDefinition,
    steigerung: boolean,
    gewaehlt: readonly string[],
    optionen: MachtOptionen,
  ): void {
    switch (macht.name) {
      case MACHT.GESCHOSS:
      case MACHT.FLAECHENSCHLAG:
      case MACHT.STRAHL:
        this.wuerfleMachtSchaden(wirker, ziel, macht, steigerung, gewaehlt)
        return
      case MACHT.SCHUTZ:
        // Steigerung gibt Robustheit statt Panzerung.
        this.setzeEffekt(wirker, ziel, macht, {
          ...(steigerung ? { robustheit: 2 } : { panzerung: 2 }),
          beschreibung: steigerung ? 'Robustheit +2' : 'Panzerung +2',
        })
        return
      case MACHT.ABWEHREN: {
        const art: AbwehrArt = optionen.abwehrArt ?? 'nahkampf'
        this.setzeEffekt(wirker, ziel, macht, {
          ...(steigerung || art === 'nahkampf' ? { abwehrNahkampf: -2 } : {}),
          ...(steigerung || art === 'fernkampf' ? { abwehrFernkampf: -2 } : {}),
          beschreibung: steigerung
            ? 'Angreifer –2 im Nah- und Fernkampf'
            : `Angreifer –2 im ${art === 'nahkampf' ? 'Nahkampf' : 'Fernkampf'}`,
        })
        return
      }
      case MACHT.WAFFE_VERBESSERN:
        this.setzeEffekt(wirker, ziel, macht, {
          schaden: steigerung ? 4 : 2,
          beschreibung: `Waffenschaden +${steigerung ? 4 : 2}`,
        })
        return
      case MACHT.ARKANER_SCHUTZ:
        this.setzeEffekt(wirker, ziel, macht, {
          arkanerSchutz: steigerung ? 4 : 2,
          beschreibung: `Feindliche Mächte und magischer Schaden –${steigerung ? 4 : 2}`,
        })
        return
      case MACHT.EIGENSCHAFT:
        this.veraendereEigenschaft(wirker, ziel, macht, steigerung, gewaehlt, optionen)
        return
      case MACHT.HEILUNG:
        this.heile(ziel, steigerung ? 2 : 1)
        return
      case MACHT.LINDERUNG:
        this.lindere(wirker, ziel, macht, steigerung, gewaehlt, optionen.linderungModus ?? 'erholen')
        return
      case MACHT.BETAEUBEN:
        this.betaeubungsprobe(ziel, steigerung)
        return
      case MACHT.SCHLUMMER:
        this.schlummerprobe(ziel, steigerung)
        return
      case MACHT.BLENDEN: {
        const malus = Math.max(steigerung ? 4 : 2, ziel.blendung?.malus ?? 0)
        ziel.blendung = { malus, stark: gewaehlt.includes(MODIFIKATOR.STARK) }
        this.protokolliere(
          `${ziel.name} ist geblendet: –${malus} auf alle Aktionen, die Sicht erfordern. Abschütteln am Ende seiner Züge (Konstitution).`,
          'schaden',
        )
        return
      }
      case MACHT.VERWIRRUNG: {
        const wahl = optionen.verwirrung ?? 'abgelenkt'
        if (steigerung || wahl === 'abgelenkt') ziel.setzeAbgelenkt()
        if (steigerung || wahl === 'verwundbar') ziel.setzeVerwundbar()
        const zustand = steigerung ? 'Abgelenkt und Verwundbar' : wahl === 'abgelenkt' ? 'Abgelenkt' : 'Verwundbar'
        this.protokolliere(`${ziel.name} ist ${zustand} bis zum Ende seines nächsten Zuges.`, 'schaden')
        return
      }
      case MACHT.VERSTRICKEN: {
        const fessel: Fessel = steigerung || ziel.fessel === 'gebunden' ? 'gebunden' : 'festgehalten'
        ziel.setzeFessel(fessel, ziel.gehaltenVon)
        this.aktualisiereFesseln()
        this.protokolliere(
          `${ziel.name} ist ${fessel === 'gebunden' ? 'Gebunden (Abgelenkt, Verwundbar, nur Befreien möglich)' : 'Festgehalten (Verwundbar)'}.`,
          'schaden',
        )
        return
      }
      default:
        this.protokolliere(`${macht.name} hat im Simulator noch keine Wirkung.`, 'warnung')
    }
  }

  private setzeEffekt(
    wirker: Kaempfer,
    ziel: Kaempfer,
    macht: MachtDefinition,
    werte: Partial<AktiverEffekt> & { beschreibung: string },
    dauer = macht.wirkungsdauer === SOFORT ? 1 : macht.wirkungsdauer,
  ): void {
    ziel.fuegeEffektHinzu({
      macht: macht.name,
      wirkerId: wirker.id,
      verbleibend: dauer,
      ...werte,
    })
    this.protokolliere(
      `${macht.name} wirkt auf ${ziel.name}: ${werte.beschreibung}${dauer >= EINE_STUNDE_IN_RUNDEN ? ' für eine Stunde' : ` für ${dauer} Runden`}.`,
      'erfolg',
    )
  }

  private veraendereEigenschaft(
    wirker: Kaempfer,
    ziel: Kaempfer,
    macht: MachtDefinition,
    steigerung: boolean,
    gewaehlt: readonly string[],
    optionen: MachtOptionen,
  ): void {
    const eigenschaft = optionen.eigenschaft!
    const stufen = steigerung ? 2 : 1
    const vorher = ziel.wuerfelFuer(eigenschaft).wuerfel
    if (optionen.eigenschaftModus === 'senken') {
      const bestehend = ziel.senkungen.find((s) => s.eigenschaft === eigenschaft)
      if (bestehend && bestehend.stufen >= stufen) {
        this.protokolliere(`${eigenschaft} von ${ziel.name} ist bereits mindestens so stark gesenkt.`)
        return
      }
      ziel.senkungen = ziel.senkungen.filter((s) => s.eigenschaft !== eigenschaft)
      ziel.senkungen.push({ eigenschaft, stufen, stark: gewaehlt.includes(MODIFIKATOR.STARK), wirkerId: wirker.id })
      this.protokolliere(
        `${eigenschaft} von ${ziel.name} sinkt um ${stufen} Würfeltyp(en): ${vorher} → ${ziel.wuerfelFuer(eigenschaft).wuerfel}. ` +
          'Abschütteln am Ende seiner Züge (Willenskraft).',
        'schaden',
      )
      return
    }
    this.setzeEffekt(wirker, ziel, macht, {
      eigenschaft,
      stufen,
      beschreibung: `${eigenschaft} +${stufen} Würfeltyp(en) (${vorher} → ${vorher.stufe(stufen)})`,
    })
  }

  /** Linderung: Zustände aufheben (Erholen) oder Abzüge ignorieren (Abschwächen). */
  private lindere(
    wirker: Kaempfer,
    ziel: Kaempfer,
    macht: MachtDefinition,
    steigerung: boolean,
    gewaehlt: readonly string[],
    modus: LinderungModus,
  ): void {
    const anzahl = steigerung ? 2 : 1
    if (modus === 'abschwaechen') {
      this.setzeEffekt(
        wirker,
        ziel,
        macht,
        { linderung: anzahl, beschreibung: `ignoriert ${anzahl} Punkt(e) Wund- und Erschöpfungsabzug` },
        EINE_STUNDE_IN_RUNDEN,
      )
      return
    }
    // Anhaltende Ursachen (Fesseln) bleiben bestehen; Betäubt nur mit Modifikator.
    const aufhebbar: { name: string; aktiv: boolean; aufheben: () => void }[] = [
      {
        name: 'Betäubt',
        aktiv: ziel.betaeubt && gewaehlt.includes(MODIFIKATOR.BETAEUBT),
        aufheben: () => {
          ziel.betaeubt = false
        },
      },
      { name: 'Angeschlagen', aktiv: ziel.angeschlagen, aufheben: () => (ziel.angeschlagen = false) },
      { name: 'Verwundbar', aktiv: ziel.verwundbarZuege > 0, aufheben: () => (ziel.verwundbarZuege = 0) },
      { name: 'Abgelenkt', aktiv: ziel.abgelenktZuege > 0, aufheben: () => (ziel.abgelenktZuege = 0) },
    ]
    const entfernt = aufhebbar.filter((z) => z.aktiv).slice(0, anzahl)
    if (!entfernt.length) {
      this.protokolliere(`${ziel.name} hat keinen Zustand, den Linderung aufheben könnte.`)
      return
    }
    entfernt.forEach((z) => z.aufheben())
    if (ziel === this.aktueller && !ziel.angeschlagen && !ziel.handlungsunfaehig) this.zugDarfHandeln = true
    this.protokolliere(`${ziel.name} ist nicht mehr ${entfernt.map((z) => z.name).join(' und ')}.`, 'erfolg')
  }

  private wuerfleMachtSchaden(
    wirker: Kaempfer,
    ziel: Kaempfer,
    macht: MachtDefinition,
    steigerung: boolean,
    gewaehlt: readonly string[],
  ): void {
    if (!ziel.istKampffaehig) return
    const pb = machtPanzerbrechend(gewaehlt)
    const text = machtSchaden(steigerung, gewaehlt.includes(MODIFIKATOR.SCHADEN))
    const formel = Schadensformel.parse(text)!
    const boni: Modifikator[] = []
    if (wirker.hatJoker) boni.push({ name: 'Joker', wert: JOKER_BONUS })
    // Arkane Resistenz und Arkaner Schutz verringern magischen Schaden.
    if (ziel.arkaneAbwehr) boni.push({ name: 'Arkane Resistenz/Schutz', wert: -ziel.arkaneAbwehr })
    const riesentoeter = this.riesentoeter(wirker, ziel)
    // Die Steigerung erhöht hier die Würfelzahl statt einen Bonuswürfel zu
    // addieren – deshalb kein steigerung-Flag.
    const schaden = SchadensRegeln.wuerfle({
      formel,
      staerke: wirker.staerke,
      zusatzWuerfel: riesentoeter ? [6] : [],
      modifikator: boni.reduce((s, b) => s + b.wert, 0),
      zufall: this.zufall,
    })
    const robustheit = this.robustheitVon(ziel, pb)
    const bewertung = SchadensRegeln.bewerte(schaden.gesamt, robustheit, ziel.angeschlagen, ziel.zaeh)
    const zusatz = [
      ...boni.map((b) => `${b.name} ${formatiereModifikator(b.wert)}`),
      riesentoeter ? 'Riesentöter +W6' : '',
      pb ? `PB ${pb}` : '',
    ]
      .filter(Boolean)
      .join(', ')
    this.protokolliere(
      `${macht.name} trifft ${ziel.name}: Schaden ${text}${zusatz ? ` (${zusatz})` : ''}: ` +
        `${SchadensRegeln.beschreibe(schaden)} gegen Robustheit ${robustheit}.`,
    )
    this.verarbeiteTreffer(ziel, bewertung)
  }

  /**
   * Betäuben: Das Opfer wehrt sich mit einer Konstitutionsprobe, bei einer
   * Steigerung des Wirkers mit –2. Misslingt sie, ist es Betäubt.
   */
  private betaeubungsprobe(ziel: Kaempfer, steigerung: boolean): void {
    const modifikatoren: Modifikator[] = steigerung
      ? [{ name: 'Steigerung des Wirkers', wert: -STEIGERUNG_WIDERSTAND_MALUS }]
      : []
    const ergebnis = this.wuerfleProbe(ziel, ATTRIBUT.KONSTITUTION, modifikatoren)
    if (ergebnis.erfolg) {
      this.protokolliere(
        `${ziel.name} widersteht: ${Eigenschaftsprobe.beschreibe(ergebnis)}` +
          KampfController.beschreibeModifikatoren(ergebnis.modifikatoren),
        'erfolg',
      )
      return
    }
    this.protokolliere(
      `${ziel.name} unterliegt: ${Eigenschaftsprobe.beschreibe(ergebnis)}` +
        KampfController.beschreibeModifikatoren(ergebnis.modifikatoren),
      'fehlschlag',
    )
    this.betaeube(ziel)
  }

  /** Schlummer: Willenskraftprobe (–2 bei Steigerung), sonst schläft das Opfer ein. */
  private schlummerprobe(ziel: Kaempfer, steigerung: boolean): void {
    const modifikatoren: Modifikator[] = steigerung
      ? [{ name: 'Steigerung des Wirkers', wert: -STEIGERUNG_WIDERSTAND_MALUS }]
      : []
    const ergebnis = this.wuerfleProbe(ziel, ATTRIBUT.WILLENSKRAFT, modifikatoren)
    const text = `${Eigenschaftsprobe.beschreibe(ergebnis)}${KampfController.beschreibeModifikatoren(ergebnis.modifikatoren)}`
    if (ergebnis.erfolg) {
      this.protokolliere(`${ziel.name} widersteht dem Schlummer: ${text}`, 'erfolg')
      return
    }
    ziel.schlaeft = true
    this.protokolliere(
      `${ziel.name} schläft ein: ${text}. Laute Geräusche oder Wachrütteln erlauben eine neue Willenskraftprobe.`,
      'schaden',
    )
  }

  /** Setzt den Zustand Betäubt inklusive Abgelenkt und Verwundbar. */
  private betaeube(ziel: Kaempfer): void {
    ziel.betaeubt = true
    ziel.setzeAbgelenkt()
    this.protokolliere(
      `${ziel.name} ist Betäubt: Abgelenkt (–2), Verwundbar (+2 für Angreifer), am Boden, ` +
        'keine Aktionen. Erholungsprobe zu Beginn des eigenen Zuges.',
      'schaden',
    )
  }

  /**
   * Freie Konstitutionsprobe zu Beginn des Zuges gegen Betäubt. Erfolg
   * beendet die Betäubung, das Ziel bleibt aber bis zum Ende seines
   * nächsten Zuges Verwundbar — bei einer Steigerung nur bis zum Ende
   * dieses Zuges.
   */
  private betaeubungsErholung(kaempfer: Kaempfer): void {
    const ergebnis = this.wuerfleProbe(kaempfer, ATTRIBUT.KONSTITUTION, this.erholungsBoni(kaempfer))
    const text = `${Eigenschaftsprobe.beschreibe(ergebnis)}${KampfController.beschreibeModifikatoren(ergebnis.modifikatoren)}`
    if (!ergebnis.erfolg) {
      this.zugDarfHandeln = false
      this.protokolliere(`${kaempfer.name} bleibt Betäubt: ${text}. Keine Aktionen möglich.`, 'fehlschlag')
      return
    }
    kaempfer.betaeubt = false
    // Steigerung: nur bis zum Ende dieses Zuges, sonst bis zum Ende des nächsten.
    kaempfer.verwundbarZuege = ergebnis.steigerungen > 0 ? 1 : 2
    this.protokolliere(
      `${kaempfer.name} schüttelt die Betäubung ab: ${text}. ` +
        `Noch Verwundbar bis zum Ende ${ergebnis.steigerungen > 0 ? 'dieses' : 'des nächsten'} Zuges.`,
      'erfolg',
    )
  }

  /**
   * Heilung: entfernt Wunden. Wird bei einem Ausgeschalteten mindestens
   * eine Wunde geheilt, ist er wieder dabei (S. 96).
   */
  private heile(ziel: Kaempfer, wunden: number): void {
    if (ziel.wunden === 0) {
      this.protokolliere(`${ziel.name} hat keine Wunden, die geheilt werden könnten.`)
      return
    }
    const geheilt = Math.min(wunden, ziel.wunden)
    ziel.wunden -= geheilt
    let zusatz = ''
    if (ziel.ausserGefecht && ziel.erschoepfung < MAX_ERSCHOEPFUNG) {
      ziel.ausserGefecht = false
      zusatz = ' und ist nicht mehr Außer Gefecht'
    }
    this.protokolliere(
      `${ziel.name} wird um ${geheilt} Wunde(n) geheilt (jetzt ${ziel.wunden})${zusatz}.`,
      'erfolg',
    )
  }

  // --------------------------------------------------------------
  // Schaden wegstecken
  // --------------------------------------------------------------

  /**
   * Benny ausgeben und Konstitutionsprobe würfeln. Jeder Erfolg und
   * jede Steigerung verhindert eine Wunde. Bei mehreren Versuchen
   * zählt das beste Ergebnis.
   */
  wegstecken(): void {
    const offen = this.offenerSchaden
    if (!offen || !offen.ziel.benutzeBenny()) return
    const ziel = offen.ziel
    const modifikatoren: Modifikator[] = []
    if (ziel.hatTalent(TALENT.EISENKIEFER)) modifikatoren.push({ name: 'Eisenkiefer', wert: EISENKIEFER_BONUS })
    const probe = this.wuerfleProbe(ziel, ATTRIBUT.KONSTITUTION, modifikatoren)
    const reduktion = probe.erfolg ? 1 + probe.steigerungen : 0
    offen.versuche += 1
    offen.reduziert = Math.max(offen.reduziert, reduktion)

    this.protokolliere(
      `${ziel.name} steckt Schaden weg (Benny, ${ziel.bennys} übrig): ${Eigenschaftsprobe.beschreibe(probe)}` +
        `${KampfController.beschreibeModifikatoren(probe.modifikatoren)} → bestes Ergebnis: ` +
        `${Math.min(offen.reduziert, offen.wunden)} von ${offen.wunden} Wunde(n) verhindert.`,
      probe.erfolg ? 'erfolg' : 'fehlschlag',
    )
    if (offen.reduziert >= offen.wunden || ziel.bennys === 0) this.schadenAnnehmen()
  }

  schadenAnnehmen(): void {
    const offen = this.offenerSchaden
    if (!offen) return
    this.offenerSchaden = null
    const verbleibend = Math.max(0, offen.wunden - offen.reduziert)
    if (verbleibend === 0) {
      // Wer alle Wunden eines Angriffs wegsteckt, ist auch nicht mehr
      // Angeschlagen – selbst wenn er es vorher schon war (S. 96).
      const warAngeschlagen = offen.ziel.angeschlagen
      offen.ziel.angeschlagen = false
      if (offen.ziel === this.aktueller && !offen.ziel.handlungsunfaehig) this.zugDarfHandeln = true
      this.protokolliere(
        `${offen.ziel.name} steckt alle Wunden weg${warAngeschlagen ? ' und ist nicht mehr Angeschlagen' : ''}.`,
        'erfolg',
      )
    } else {
      this.protokolliere(offen.ziel.nimmSchaden(verbleibend, true), 'schaden')
      this.nachKoerperlichemSchaden(offen.ziel)
    }
    this.pruefeKampfende()
    this.arbeiteWarteschlangeAb()
  }

  private pruefeKampfende(): void {
    this.aktualisiereFesseln()
    ;[SEITE.HELDEN, SEITE.GEGNER].forEach((seite) => {
      const gruppe = this.kaempfer.filter((k) => k.seite === seite)
      if (gruppe.length > 0 && gruppe.every((k) => !k.istKampffaehig)) {
        const name = seite === SEITE.HELDEN ? 'Helden' : 'Gegner'
        this.protokolliere(`Alle ${name} sind Außer Gefecht.`, 'runde')
      }
    })
  }

  // --------------------------------------------------------------
  // Manuelle Eingriffe der Spielleitung
  // --------------------------------------------------------------

  bennyGegenAngeschlagen(id: string): void {
    const kaempfer = this.finde(id)
    if (!kaempfer || !kaempfer.angeschlagen || !kaempfer.benutzeBenny()) return
    kaempfer.angeschlagen = false
    if (kaempfer === this.aktueller && !kaempfer.handlungsunfaehig) this.zugDarfHandeln = true
    this.protokolliere(`${kaempfer.name} gibt einen Benny aus und ist nicht mehr Angeschlagen.`, 'erfolg')
  }

  aendereWunden(id: string, delta: number): void {
    const kaempfer = this.finde(id)
    if (!kaempfer || kaempfer.maxWunden === 0) return
    kaempfer.wunden = Math.max(0, Math.min(kaempfer.maxWunden, kaempfer.wunden + delta))
    this.protokolliere(`${kaempfer.name}: Wunden manuell auf ${kaempfer.wunden} gesetzt.`)
  }

  aendereBennys(id: string, delta: number): void {
    const kaempfer = this.finde(id)
    if (!kaempfer) return
    kaempfer.bennys = Math.max(0, kaempfer.bennys + delta)
  }

  schalteAngeschlagen(id: string): void {
    const kaempfer = this.finde(id)
    if (!kaempfer) return
    kaempfer.angeschlagen = !kaempfer.angeschlagen
    this.protokolliere(
      `${kaempfer.name}: ${kaempfer.angeschlagen ? 'Angeschlagen' : 'nicht mehr Angeschlagen'} (manuell).`,
    )
  }

  schalteBetaeubt(id: string): void {
    const kaempfer = this.finde(id)
    if (!kaempfer) return
    if (kaempfer.betaeubt) {
      kaempfer.betaeubt = false
      kaempfer.verwundbarZuege = 0
      this.protokolliere(`${kaempfer.name}: nicht mehr Betäubt (manuell).`)
      return
    }
    kaempfer.betaeubt = true
    kaempfer.setzeAbgelenkt()
    this.protokolliere(`${kaempfer.name}: Betäubt (manuell).`)
  }

  schalteSchlaeft(id: string): void {
    const kaempfer = this.finde(id)
    if (!kaempfer) return
    kaempfer.schlaeft = !kaempfer.schlaeft
    this.protokolliere(`${kaempfer.name}: ${kaempfer.schlaeft ? 'schläft' : 'ist wach'} (manuell).`)
  }

  /** Blendung oder Eigenschaftssenkungen manuell beenden. */
  beendeBlendung(id: string): void {
    const kaempfer = this.finde(id)
    if (!kaempfer || !kaempfer.blendung) return
    kaempfer.blendung = null
    this.protokolliere(`${kaempfer.name}: Blendung beendet (manuell).`)
  }

  beendeSenkung(id: string, eigenschaft: string): void {
    const kaempfer = this.finde(id)
    if (!kaempfer) return
    kaempfer.senkungen = kaempfer.senkungen.filter((s) => s.eigenschaft !== eigenschaft)
    this.protokolliere(`${kaempfer.name}: Senkung von ${eigenschaft} beendet (manuell).`)
  }

  schalteAusserGefecht(id: string): void {
    const kaempfer = this.finde(id)
    if (!kaempfer) return
    kaempfer.ausserGefecht = !kaempfer.ausserGefecht
    this.aktualisiereFesseln()
    this.protokolliere(
      `${kaempfer.name}: ${kaempfer.ausserGefecht ? 'Außer Gefecht' : 'wieder kampffähig'} (manuell).`,
    )
  }
}
