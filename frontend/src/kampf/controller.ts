/**
 * Kampfsimulator – Anwendungsschicht (Controller).
 *
 * Koordiniert den Kampfablauf auf Basis der Domain:
 * Runden, Kartenausgabe, Zugreihenfolge, Proben, Angriffe,
 * Schaden wegstecken und Protokoll. Die View hält eine reaktive
 * Instanz (Vue reactive) und ruft ausschließlich öffentliche Methoden auf.
 */
import {
  ATTRIBUT,
  Aktionsstapel,
  Eigenschaftsprobe,
  InitiativeRegeln,
  JOKER_BONUS,
  Kaempfer,
  MINDESTWURF,
  RUECKSICHTSLOS_BONUS,
  SEITE,
  SchadensRegeln,
  TALENT,
  Waffe,
  Zufall,
  formatiereModifikator,
  Schadensformel,
  type Modifikator,
  type ProbenErgebnis,
  type TrefferBewertung,
} from './domain'
import {
  BETAEUBEN_STEIGERUNG_MALUS,
  MACHT,
  MACHT_MINDESTWURF,
  MAX_ERSCHOEPFUNG,
  MINDESTKOSTEN,
  RUECKSCHLAG_ERSCHOEPFUNG,
  SOFORT,
  geschossSchaden,
  machtDefinition,
  machtKosten,
  type AbwehrArt,
  type AktiverEffekt,
  type MachtDefinition,
} from './maechte'

const BERECHNEND_MAX_IGNORIERT = 2
const KAMPFREFLEXE_BONUS = 2
const EISENKIEFER_BONUS = 2
const MEHRFACHAKTION_MALUS = 2

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
}

export interface MachtOptionen {
  /** situativer Modifikator (Deckung, Beleuchtung, …) */
  modifikator?: number
  /** Anzahl Aktionen im Zug — Mächte sind volle Aktionen */
  aktionen?: number
  /** gewählte Machtmodifikatoren (Namen aus der Definition) */
  modifikatoren?: string[]
  /** Abwehren ohne Steigerung: Nah- oder Fernkampf */
  abwehrArt?: AbwehrArt
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
    }
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
      k.ruecksichtslosAktiv = false
    })
    this.reihenfolge = []
    this.aktuellerIndex = -1
    this.offenerSchaden = null
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
    this.aktuellerIndex = -1
    this.naechsterZug()
  }

  naechsterZug(): void {
    if (this.offenerSchaden) return
    // Abgelenkt/Verwundbar laufen „bis zum Ende des Zuges" aus.
    this.aktueller?.zugEnde().forEach((n) => this.protokolliere(n))
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
    // Betäubt wiegt schwerer als Angeschlagen: solange es anhält, geht gar nichts.
    if (kaempfer.betaeubt) this.betaeubungsErholung(kaempfer)
    if (kaempfer.angeschlagen && !kaempfer.betaeubt) this.erholungsprobe(kaempfer)
  }

  /** Willenskraftprobe zu Beginn des Zuges, um Angeschlagen aufzuheben. */
  private erholungsprobe(kaempfer: Kaempfer): void {
    const modifikatoren: Modifikator[] = []
    if (kaempfer.hatTalent(TALENT.KAMPFREFLEXE)) {
      modifikatoren.push({ name: 'Kampfreflexe', wert: KAMPFREFLEXE_BONUS })
    }
    const ergebnis = this.wuerfleProbe(kaempfer, ATTRIBUT.WILLENSKRAFT, modifikatoren)
    if (ergebnis.erfolg) {
      kaempfer.angeschlagen = false
      this.protokolliere(
        `${kaempfer.name} erholt sich: ${Eigenschaftsprobe.beschreibe(ergebnis)}. Nicht mehr Angeschlagen.`,
        'erfolg',
      )
    } else {
      this.zugDarfHandeln = false
      this.protokolliere(
        `${kaempfer.name} bleibt Angeschlagen: ${Eigenschaftsprobe.beschreibe(ergebnis)}. Nur freie Aktionen möglich.`,
        'fehlschlag',
      )
    }
  }

  // --------------------------------------------------------------
  // Proben
  // --------------------------------------------------------------

  /**
   * Sammelt alle Modifikatoren einer Probe (Wunden, Joker, Berechnend)
   * und würfelt.
   */
  private wuerfleProbe(
    kaempfer: Kaempfer,
    eigenschaft: string,
    modifikatoren: Modifikator[],
    mindestwurf?: number,
  ): ProbenErgebnis {
    const liste = modifikatoren.filter((m) => m.wert)
    if (kaempfer.wundmalus) liste.push({ name: 'Wunden', wert: kaempfer.wundmalus })
    if (kaempfer.erschoepfungsmalus) liste.push({ name: 'Erschöpfung', wert: kaempfer.erschoepfungsmalus })
    if (kaempfer.abgelenktmalus) liste.push({ name: 'Abgelenkt', wert: kaempfer.abgelenktmalus })
    if (kaempfer.hatJoker) liste.push({ name: 'Joker', wert: JOKER_BONUS })
    const malus = liste.filter((m) => m.wert < 0).reduce((s, m) => s + m.wert, 0)
    const karte = kaempfer.karte
    if (malus < 0 && kaempfer.hatTalent(TALENT.BERECHNEND) && karte && !karte.joker && karte.wert <= 5) {
      liste.push({ name: 'Berechnend', wert: Math.min(BERECHNEND_MAX_IGNORIERT, -malus) })
    }
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

  private static beschreibeModifikatoren(liste: Modifikator[]): string {
    if (liste.length === 0) return ''
    return ` [${liste.map((m) => `${m.name} ${formatiereModifikator(m.wert)}`).join(', ')}]`
  }

  /** Freie Eigenschaftsprobe (Attribut oder Fertigkeit). */
  probe(kaempferId: string, eigenschaft: string, modifikator = 0, mindestwurf = MINDESTWURF): ProbenErgebnis | null {
    const kaempfer = this.finde(kaempferId)
    if (!kaempfer || !eigenschaft) return null
    const ergebnis = this.wuerfleProbe(kaempfer, eigenschaft, [{ name: 'Situativ', wert: modifikator }], mindestwurf)
    const zusatz = ergebnis.ungeuebt ? ' (ungeübt)' : ''
    this.protokolliere(
      `${kaempfer.name} – ${eigenschaft}${zusatz}: ${Eigenschaftsprobe.beschreibe(ergebnis)}` +
        KampfController.beschreibeModifikatoren(ergebnis.modifikatoren),
      ergebnis.erfolg ? 'erfolg' : 'fehlschlag',
    )
    return ergebnis
  }

  // --------------------------------------------------------------
  // Angriff
  // --------------------------------------------------------------

  angriff(angreiferId: string, zielId: string, waffenIndex: number, optionen: AngriffsOptionen = {}): void {
    const angreifer = this.finde(angreiferId)
    const ziel = this.finde(zielId)
    const fehler = this.pruefeAngriff(angreifer, ziel)
    if (fehler || !angreifer || !ziel) {
      this.protokolliere(fehler ?? 'Angreifer oder Ziel fehlt.', 'warnung')
      return
    }
    const waffe = angreifer.waffen[waffenIndex] ?? angreifer.waffen[0]
    const ruecksichtslos = Boolean(optionen.ruecksichtslos && waffe.istNahkampf)
    const modifikatoren: Modifikator[] = [
      { name: 'Situativ', wert: optionen.modifikator ?? 0 },
      { name: 'Mehrfachaktion', wert: -MEHRFACHAKTION_MALUS * Math.max(0, (optionen.aktionen ?? 1) - 1) },
    ]
    if (!waffe.istNahkampf) modifikatoren.push({ name: 'Reichweite', wert: optionen.reichweite ?? 0 })
    // Abwehren auf dem Ziel zieht Angreifer ab.
    const abwehr = ziel.abwehrMalus(waffe.istNahkampf)
    if (abwehr) modifikatoren.push({ name: MACHT.ABWEHREN, wert: abwehr })
    // Verwundbare Ziele sind leichter zu treffen.
    if (ziel.verwundbarBonus) modifikatoren.push({ name: 'Verwundbar', wert: ziel.verwundbarBonus })
    if (ruecksichtslos) {
      modifikatoren.push({ name: 'Rücksichtslos', wert: RUECKSICHTSLOS_BONUS })
      angreifer.ruecksichtslosAktiv = true
    }
    const mindestwurf = waffe.istNahkampf ? ziel.aktuelleParade : MINDESTWURF
    const probe = this.wuerfleProbe(angreifer, waffe.fertigkeit, modifikatoren, mindestwurf)

    this.protokolliere(
      `${angreifer.name} greift ${ziel.name} mit ${waffe.name} an (${waffe.fertigkeit}` +
        `${probe.ungeuebt ? ', ungeübt' : ''}): ${Eigenschaftsprobe.beschreibe(probe)}` +
        KampfController.beschreibeModifikatoren(probe.modifikatoren),
      probe.erfolg ? 'erfolg' : 'fehlschlag',
    )
    if (probe.kritisch) {
      this.protokolliere(`${angreifer.name}: Kritischer Fehlschlag – die Spielleitung bestimmt die Folgen.`, 'warnung')
    }
    if (probe.erfolg) this.wuerfleSchaden(angreifer, ziel, waffe, probe, ruecksichtslos)
  }

  // --------------------------------------------------------------
  // Mächte
  // --------------------------------------------------------------

  /** Mögliche Ziele einer Macht — je nachdem, ob sie Freund oder Feind trifft. */
  moeglicheMachtZiele(wirker: Kaempfer, machtName: string): Kaempfer[] {
    const macht = machtDefinition(machtName)
    if (!macht) return []
    if (macht.ziel === 'gegner') {
      return this.kaempfer.filter((k) => k !== wirker && k.seite !== wirker.seite && k.istKampffaehig)
    }
    return this.kaempfer.filter((k) => k.seite === wirker.seite)
  }

  /**
   * Wirkt eine Macht. Das ist eine **volle Aktion**: sie unterliegt dem
   * Mehrfachaktionsabzug und ist Angeschlagenen verwehrt — genau wie ein
   * Angriff. Machtpunkte werden auch bei Misserfolg fällig.
   */
  wirkeMacht(wirkerId: string, machtName: string, zielId: string, optionen: MachtOptionen = {}): void {
    const wirker = this.finde(wirkerId)
    const ziel = this.finde(zielId)
    const macht = machtDefinition(machtName)
    const gewaehlt = optionen.modifikatoren ?? []
    const fehler = this.pruefeMacht(wirker, ziel, macht, gewaehlt)
    if (fehler || !wirker || !ziel || !macht) {
      this.protokolliere(fehler ?? 'Macht konnte nicht gewirkt werden.', 'warnung')
      return
    }

    const kosten = machtKosten(macht, gewaehlt)
    const modifikatoren: Modifikator[] = [
      { name: 'Situativ', wert: optionen.modifikator ?? 0 },
      { name: 'Mehrfachaktion', wert: -MEHRFACHAKTION_MALUS * Math.max(0, (optionen.aktionen ?? 1) - 1) },
    ]
    // Bei Angriffsmächten ist der arkane Wurf der Angriffswurf: Abwehren
    // fängt ausdrücklich auch Geschosse ab, Verwundbar erleichtert den Treffer.
    if (macht.typ === 'angriff') {
      const abwehr = ziel.abwehrMalus(false)
      if (abwehr) modifikatoren.push({ name: MACHT.ABWEHREN, wert: abwehr })
      if (ziel.verwundbarBonus) modifikatoren.push({ name: 'Verwundbar', wert: ziel.verwundbarBonus })
    }
    const probe = this.wuerfleProbe(wirker, wirker.arkaneFertigkeit, modifikatoren, MACHT_MINDESTWURF)
    const zusatz = gewaehlt.length ? ` [${gewaehlt.join(', ')}]` : ''

    this.protokolliere(
      `${wirker.name} wirkt ${macht.name}${zusatz} auf ${ziel.name} (${wirker.arkaneFertigkeit}): ` +
        `${Eigenschaftsprobe.beschreibe(probe)}` +
        KampfController.beschreibeModifikatoren(probe.modifikatoren),
      probe.erfolg ? 'erfolg' : 'fehlschlag',
    )

    if (probe.kritisch) {
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
    this.wendeMachtAn(wirker, ziel, macht, probe, gewaehlt, optionen)
  }

  private pruefeMacht(
    wirker: Kaempfer | null,
    ziel: Kaempfer | null,
    macht: MachtDefinition | null,
    gewaehlt: readonly string[],
  ): string | null {
    if (!wirker || !ziel) return 'Wirker oder Ziel fehlt.'
    if (!macht) return 'Diese Macht ist im Simulator nicht hinterlegt.'
    if (this.offenerSchaden) return 'Zuerst muss der offene Schaden abgehandelt werden.'
    if (wirker !== this.aktueller) return `${wirker.name} ist nicht am Zug.`
    if (wirker.betaeubt) return `${wirker.name} ist Betäubt und kann keine Aktionen ausführen.`
    // Mächte sind volle Aktionen — Angeschlagene können nur freie Aktionen.
    if (!this.zugDarfHandeln || wirker.angeschlagen) {
      return `${wirker.name} ist Angeschlagen und kann nur freie Aktionen ausführen – Mächte sind volle Aktionen.`
    }
    if (!wirker.istWirker) return `${wirker.name} beherrscht keine Mächte.`
    if (!wirker.maechte.includes(macht.name)) return `${wirker.name} beherrscht ${macht.name} nicht.`
    const kosten = machtKosten(macht, gewaehlt)
    if (wirker.machtpunkte < kosten) {
      return `${wirker.name} hat nur ${wirker.machtpunkte} Machtpunkte, ${macht.name} kostet ${kosten}.`
    }
    if (macht.ziel === 'gegner' && !ziel.istKampffaehig) return `${ziel.name} ist bereits Außer Gefecht.`
    return null
  }

  /** Kritischer Fehlschlag: Erschöpfung und alle eigenen Mächte enden. */
  private rueckschlag(wirker: Kaempfer): void {
    wirker.machtpunkte = Math.max(0, wirker.machtpunkte - MINDESTKOSTEN)
    wirker.erschoepfung += RUECKSCHLAG_ERSCHOEPFUNG
    this.protokolliere(
      `Rückschlag! ${wirker.name} erleidet eine Stufe Erschöpfung ` +
        `(${wirker.erschoepfungsmalus} auf Eigenschaftsproben).`,
      'warnung',
    )
    this.kaempfer.forEach((k) => k.beendeEffekteVon(wirker.id).forEach((n) => this.protokolliere(n)))
    if (wirker.erschoepfung >= MAX_ERSCHOEPFUNG) {
      wirker.ausserGefecht = true
      this.protokolliere(`${wirker.name} ist durch Erschöpfung Ausgeschaltet.`, 'schaden')
      this.pruefeKampfende()
    }
  }

  private wendeMachtAn(
    wirker: Kaempfer,
    ziel: Kaempfer,
    macht: MachtDefinition,
    probe: ProbenErgebnis,
    gewaehlt: readonly string[],
    optionen: MachtOptionen,
  ): void {
    const steigerung = probe.steigerungen > 0
    switch (macht.name) {
      case MACHT.GESCHOSS:
        this.wuerfleGeschoss(wirker, ziel, probe, gewaehlt)
        return
      case MACHT.SCHUTZ:
        // Steigerung gibt Robustheit statt Panzerung.
        this.setzeEffekt(wirker, ziel, macht, {
          ...(steigerung ? { robustheit: 2 } : { panzerung: 2 }),
          beschreibung: steigerung ? 'Robustheit +2' : 'Panzerung +2',
        })
        return
      case MACHT.ABWEHREN: {
        const beide = steigerung
        const art: AbwehrArt = optionen.abwehrArt ?? 'nahkampf'
        const werte =
          beide || art === 'nahkampf' ? { abwehrNahkampf: -2 } : {}
        const werteFern = beide || art === 'fernkampf' ? { abwehrFernkampf: -2 } : {}
        this.setzeEffekt(wirker, ziel, macht, {
          ...werte,
          ...werteFern,
          beschreibung: beide
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
      case MACHT.HEILUNG:
        this.heile(ziel, steigerung ? 2 : 1)
        return
      case MACHT.BETAEUBEN:
        this.betaeubungsprobe(ziel, steigerung)
        return
      default:
        this.protokolliere(`${macht.name} hat im Simulator noch keine Wirkung.`, 'warnung')
    }
  }

  private setzeEffekt(
    wirker: Kaempfer,
    ziel: Kaempfer,
    macht: MachtDefinition,
    werte: Partial<AktiverEffekt> & { beschreibung: string },
  ): void {
    const dauer = macht.wirkungsdauer === SOFORT ? 1 : macht.wirkungsdauer
    ziel.fuegeEffektHinzu({
      macht: macht.name,
      wirkerId: wirker.id,
      verbleibend: dauer,
      ...werte,
    })
    this.protokolliere(
      `${macht.name} wirkt auf ${ziel.name}: ${werte.beschreibung} für ${dauer} Runden.`,
      'erfolg',
    )
  }

  private wuerfleGeschoss(
    wirker: Kaempfer,
    ziel: Kaempfer,
    probe: ProbenErgebnis,
    gewaehlt: readonly string[],
  ): void {
    const verstaerkt = gewaehlt.includes('Schaden')
    const pb = gewaehlt.includes('Panzerbrechend') ? 2 : 0
    const text = geschossSchaden(probe.steigerungen > 0, verstaerkt)
    const formel = Schadensformel.parse(text)
    if (!formel) {
      this.protokolliere(`Schadensformel „${text}" ist nicht auswertbar.`, 'warnung')
      return
    }
    let modifikator = 0
    const notizen: string[] = []
    if (wirker.hatJoker) {
      modifikator += JOKER_BONUS
      notizen.push(`Joker +${JOKER_BONUS}`)
    }
    // Die Steigerung erhöht bei Geschoss die Würfelzahl statt einen
    // Bonuswürfel zu addieren – deshalb hier kein steigerung-Flag.
    const schaden = SchadensRegeln.wuerfle({
      formel,
      staerke: wirker.staerke,
      modifikator,
      zufall: this.zufall,
    })
    const robustheit = ziel.robustheitGegen(pb)
    const bewertung = SchadensRegeln.bewerte(schaden.gesamt, robustheit, ziel.angeschlagen, ziel.zaeh)
    const zusatz = [...notizen, pb ? `PB ${pb}` : ''].filter(Boolean).join(', ')
    this.protokolliere(
      `Schaden ${text}${zusatz ? ` (${zusatz})` : ''}: ${SchadensRegeln.beschreibe(schaden)}` +
        ` gegen Robustheit ${robustheit}.`,
    )
    this.verarbeiteTreffer(ziel, bewertung)
  }

  /**
   * Betäuben: Das Opfer wehrt sich mit einer Konstitutionsprobe, bei einer
   * Steigerung des Wirkers mit –2. Misslingt sie, ist es Betäubt.
   */
  private betaeubungsprobe(ziel: Kaempfer, steigerung: boolean): void {
    const modifikatoren: Modifikator[] = steigerung
      ? [{ name: 'Steigerung des Wirkers', wert: -BETAEUBEN_STEIGERUNG_MALUS }]
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
    const ergebnis = this.wuerfleProbe(kaempfer, ATTRIBUT.KONSTITUTION, [])
    if (!ergebnis.erfolg) {
      this.zugDarfHandeln = false
      this.protokolliere(
        `${kaempfer.name} bleibt Betäubt: ${Eigenschaftsprobe.beschreibe(ergebnis)}. Keine Aktionen möglich.`,
        'fehlschlag',
      )
      return
    }
    kaempfer.betaeubt = false
    // Steigerung: nur bis zum Ende dieses Zuges, sonst bis zum Ende des nächsten.
    kaempfer.verwundbarZuege = ergebnis.steigerungen > 0 ? 1 : 2
    this.protokolliere(
      `${kaempfer.name} schüttelt die Betäubung ab: ${Eigenschaftsprobe.beschreibe(ergebnis)}. ` +
        `Noch Verwundbar bis zum Ende ${ergebnis.steigerungen > 0 ? 'dieses' : 'des nächsten'} Zuges.`,
      'erfolg',
    )
  }

  private heile(ziel: Kaempfer, wunden: number): void {
    if (ziel.wunden === 0) {
      this.protokolliere(`${ziel.name} hat keine Wunden, die geheilt werden könnten.`)
      return
    }
    const geheilt = Math.min(wunden, ziel.wunden)
    ziel.wunden -= geheilt
    this.protokolliere(
      `${ziel.name} wird um ${geheilt} Wunde(n) geheilt (jetzt ${ziel.wunden}).`,
      'erfolg',
    )
  }

  private pruefeAngriff(angreifer: Kaempfer | null, ziel: Kaempfer | null): string | null {
    if (!angreifer || !ziel) return 'Angreifer oder Ziel fehlt.'
    if (this.offenerSchaden) return 'Zuerst muss der offene Schaden abgehandelt werden.'
    if (angreifer !== this.aktueller) return `${angreifer.name} ist nicht am Zug.`
    if (angreifer.betaeubt) return `${angreifer.name} ist Betäubt und kann keine Aktionen ausführen.`
    if (!this.zugDarfHandeln || angreifer.angeschlagen) {
      return `${angreifer.name} ist Angeschlagen und kann nur freie Aktionen ausführen.`
    }
    if (!ziel.istKampffaehig) return `${ziel.name} ist bereits Außer Gefecht.`
    return null
  }

  private wuerfleSchaden(
    angreifer: Kaempfer,
    ziel: Kaempfer,
    waffe: Waffe,
    probe: ProbenErgebnis,
    ruecksichtslos: boolean,
  ): void {
    if (!waffe.formel) {
      this.protokolliere(`Schadensangabe „${waffe.schaden}" von ${waffe.name} ist nicht auswertbar.`, 'warnung')
      return
    }
    let modifikator = 0
    const notizen: string[] = []
    if (angreifer.hatJoker) {
      modifikator += JOKER_BONUS
      notizen.push(`Joker +${JOKER_BONUS}`)
    }
    if (ruecksichtslos) {
      modifikator += RUECKSICHTSLOS_BONUS
      notizen.push(`Rücksichtslos +${RUECKSICHTSLOS_BONUS}`)
    }
    if (angreifer.schadensbonus) {
      modifikator += angreifer.schadensbonus
      notizen.push(`${MACHT.WAFFE_VERBESSERN} ${formatiereModifikator(angreifer.schadensbonus)}`)
    }
    const verdoppeln = this.pruefeVerdopplung(angreifer, waffe)
    if (verdoppeln) notizen.push(verdoppeln)

    const schaden = SchadensRegeln.wuerfle({
      formel: waffe.formel,
      staerke: angreifer.staerke,
      mindeststaerke: waffe.mindeststaerke,
      steigerung: probe.steigerungen > 0,
      modifikator,
      verdoppeln: Boolean(verdoppeln),
      zufall: this.zufall,
    })
    const robustheit = ziel.robustheitGegen(waffe.pb)
    const bewertung = SchadensRegeln.bewerte(schaden.gesamt, robustheit, ziel.angeschlagen, ziel.zaeh)
    const zusatz = [probe.steigerungen > 0 ? 'Steigerung +W6' : '', ...notizen, waffe.pb ? `PB ${waffe.pb}` : '']
      .filter(Boolean)
      .join(', ')

    this.protokolliere(
      `Schaden ${waffe.schaden}${zusatz ? ` (${zusatz})` : ''}: ${SchadensRegeln.beschreibe(schaden)}` +
        ` gegen Robustheit ${robustheit}.`,
    )
    this.verarbeiteTreffer(ziel, bewertung)
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
      return
    }
    if (ziel.wildcard && ziel.bennys > 0) {
      this.offenerSchaden = { ziel, wunden: bewertung.wunden, reduziert: 0, versuche: 0 }
      this.protokolliere(`${ziel.name} droht ${bewertung.wunden} Wunde(n) – Schaden wegstecken?`, 'warnung')
      return
    }
    this.protokolliere(ziel.nimmSchaden(bewertung.wunden, true), 'schaden')
    this.pruefeKampfende()
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
      const zustand = offen.ziel.angeschlagen ? 'bleibt aber Angeschlagen' : 'ist nicht Angeschlagen'
      this.protokolliere(`${offen.ziel.name} steckt alle Wunden weg und ${zustand}.`, 'erfolg')
    } else {
      this.protokolliere(offen.ziel.nimmSchaden(verbleibend, true), 'schaden')
    }
    this.pruefeKampfende()
  }

  private pruefeKampfende(): void {
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
    if (kaempfer === this.aktueller) this.zugDarfHandeln = true
    this.protokolliere(`${kaempfer.name} gibt einen Benny aus und ist nicht mehr Angeschlagen.`, 'erfolg')
  }

  aendereWunden(id: string, delta: number): void {
    const kaempfer = this.finde(id)
    if (!kaempfer || !kaempfer.wildcard) return
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

  schalteAusserGefecht(id: string): void {
    const kaempfer = this.finde(id)
    if (!kaempfer) return
    kaempfer.ausserGefecht = !kaempfer.ausserGefecht
    this.protokolliere(
      `${kaempfer.name}: ${kaempfer.ausserGefecht ? 'Außer Gefecht' : 'wieder kampffähig'} (manuell).`,
    )
  }
}
