"""PDF-Charakterbogen (DIN A4) mit reportlab.

Rendert denselben Charakterbogen wie ``charakterbogen.py`` (HTML), nur als
echtes PDF im DIN-A4-Format. Design und Sektionen sind eins zu eins vom
HTML-Bogen übernommen: Pergament-Papier, Serifenschrift, Sektionsbänder in
dunklem Braun mit hellen Kapitälchen, Genre-Icons im Kopf und Werte in
eigenen Zellen. ``printer_friendly`` rendert dieselbe Struktur in Schwarz-Weiß
ohne Flächenfarben.

Die Datenextraktion (welche Zeilen/Spalten pro Sektion) teilt sich die
Helfer mit dem HTML-Bogen, damit beide Darstellungen synchron bleiben.
"""

from io import BytesIO
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.aufstiege import charakter_rang
from app.services.charakterbogen import (
    ANLEGBARE_KATEGORIEN,
    _COST_ENTRY_TYPEN,
    _ICON_DIR,
    _ICON_NAMES,
    _STEIGERUNGS_TYPEN,
    _gekaufte_items,
    _kosten_text,
    _wuerfel,
)
from app.services.statblock import ATTRIBUT_REIHENFOLGE

# DIN A4 mit schmalen Rändern
SEITE = A4
RAND = 15 * mm
INHALT_BREITE = SEITE[0] - 2 * RAND


def _farbschema(printer_friendly: bool) -> dict:
    """Wie ``charakterbogen._farbschema``, aber als reportlab-Color-Objekte."""
    if printer_friendly:
        return {
            "papier": colors.white,
            "zeile": colors.white,
            "hervor": colors.white,
            "band_bg": colors.white,
            "tinte": colors.HexColor("#111111"),
            "band_fg": colors.HexColor("#111111"),
            "band_rand": colors.HexColor("#111111"),
            "gedeckt": colors.HexColor("#444444"),
            "linie": colors.HexColor("#999999"),
        }
    return {
        "papier": colors.HexColor("#f6f1e3"),   # Pergament
        "zeile": colors.HexColor("#faf6ea"),    # Tabellenzeilen
        "hervor": colors.HexColor("#e8dfc8"),   # Tabellenköpfe, Gesamt-Zellen
        "tinte": colors.HexColor("#2f2a22"),
        "gedeckt": colors.HexColor("#6a5f4b"),  # Beschriftungen, Beschreibungen
        "band_bg": colors.HexColor("#6b5138"),  # Sektionsbänder
        "band_fg": colors.HexColor("#f6f1e3"),
        "band_rand": colors.HexColor("#6b5138"),
        "linie": colors.HexColor("#c4b596"),
    }


class _Bogen:
    """Bündelt Farbschema und Absatzstile für einen Renderdurchlauf."""

    def __init__(self, printer_friendly: bool):
        self.printer_friendly = printer_friendly
        f = _farbschema(printer_friendly)
        self.f = f
        self.text = ParagraphStyle(
            "text", fontName="Times-Roman", fontSize=9, leading=12, textColor=f["tinte"]
        )
        self.wert = ParagraphStyle(
            "wert", parent=self.text, fontName="Times-Bold", alignment=TA_CENTER
        )
        self.feld = ParagraphStyle(
            "feld", fontName="Times-Roman", fontSize=8, leading=11, textColor=f["gedeckt"]
        )
        self.kopfzelle = ParagraphStyle(
            "kopfzelle", fontName="Times-Roman", fontSize=7.5, leading=10,
            textColor=f["gedeckt"],
        )
        self.beschreibung = ParagraphStyle(
            "beschreibung", fontName="Times-Italic", fontSize=8, leading=11,
            textColor=f["gedeckt"],
        )
        self.band = ParagraphStyle(
            "band", fontName="Times-Roman", fontSize=9.5, leading=13,
            textColor=f["band_fg"],
        )
        self.h1 = ParagraphStyle(
            "h1", fontName="Times-Bold", fontSize=20, leading=24, alignment=TA_CENTER,
            textColor=f["tinte"],
        )
        self.untertitel = ParagraphStyle(
            "untertitel", fontName="Times-Roman", fontSize=8, leading=11,
            alignment=TA_CENTER, textColor=f["gedeckt"],
        )
        self.hinweis = ParagraphStyle(
            "hinweis", fontName="Times-Italic", fontSize=8.5, leading=12,
            textColor=f["gedeckt"],
        )

    # -- Bausteine -----------------------------------------------------

    def p(self, text, style) -> Paragraph:
        return Paragraph(_xml_escape("" if text is None else str(text)), style)

    def band_flow(self, titel: str, breite: float = INHALT_BREITE) -> Table:
        """Sektionsband (entspricht <h2> im HTML)."""
        t = Table(
            [[self.p(titel.upper(), self.band)]],
            colWidths=[breite],
        )
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), self.f["band_bg"]),
            ("BOX", (0, 0), (-1, -1), 0.75, self.f["band_rand"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    def _basis_tabellenstil(self) -> list:
        return [
            ("BACKGROUND", (0, 0), (-1, -1), self.f["zeile"]),
            ("BOX", (0, 0), (-1, -1), 0.5, self.f["linie"]),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, self.f["linie"]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]

    def werte_tabelle(self, paare, breite: float, wert_breite: float = 24 * mm) -> Table:
        """Zweispaltige Beschriftung/Wert-Tabelle (Profil, Attribute, …)."""
        if not paare:
            return self.p("Keine Einträge.", self.hinweis)
        zeilen = [
            [self.p(name, self.feld), self.p(wert, self.wert)] for name, wert in paare
        ]
        t = Table(zeilen, colWidths=[breite - wert_breite, wert_breite])
        stil = self._basis_tabellenstil()
        stil.append(("BACKGROUND", (1, 0), (1, -1), self.f["zeile"]))
        t.setStyle(TableStyle(stil))
        return t

    def beschriftung_tabelle(self, paare, breite: float) -> Table:
        """Beschriftung/Wert mit linksbündigem Fließtext (Profil, wie im HTML)."""
        if not paare:
            return self.p("Keine Einträge.", self.hinweis)
        feld_breite = breite * 0.34
        zeilen = [
            [self.p(name, self.feld), self.p(wert, self.text)] for name, wert in paare
        ]
        t = Table(zeilen, colWidths=[feld_breite, breite - feld_breite])
        t.setStyle(TableStyle(self._basis_tabellenstil()))
        return t


def _icon_row(bogen: _Bogen):
    """Vier Genre-Icons zentriert, wie die Icon-Reihe im HTML-Kopf."""
    variante = "black" if bogen.printer_friendly else "brown"
    groesse = 7 * mm
    bilder = []
    for name in _ICON_NAMES:
        pfad = _ICON_DIR / f"{name}_{variante}.png"
        bilder.append(Image(str(pfad), width=groesse, height=groesse))
    t = Table([bilder], colWidths=[12 * mm] * len(bilder))
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    t.hAlign = "CENTER"
    return t


def _kopf(bogen: _Bogen, daten: dict) -> list:
    name = daten.get("profil_daten", {}).get("Name") or "Unbenannter Charakter"
    untertitel = "Charakterbogen"
    setting_name = daten.get("active_setting_name")
    if setting_name:
        untertitel += f" · {setting_name}"

    trennlinie = Table([[""]], colWidths=[INHALT_BREITE], rowHeights=[3])
    trennlinie.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1.2, bogen.f["band_rand"]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, bogen.f["band_rand"]),
    ]))
    return [
        _icon_row(bogen),
        Spacer(1, 4),
        bogen.p(name.upper(), bogen.h1),
        bogen.p(untertitel.upper(), bogen.untertitel),
        Spacer(1, 3),
        trennlinie,
        Spacer(1, 6),
    ]


def _sektion(bogen: _Bogen, titel: str, inhalt) -> list:
    """Band + Inhalt, Band bleibt beim ersten Inhalt (kein verwaister Titel)."""
    inhalte = inhalt if isinstance(inhalt, list) else [inhalt]
    return [KeepTogether([bogen.band_flow(titel), Spacer(1, 3), inhalte[0]]), *inhalte[1:],
            Spacer(1, 6)]


# --- Sektionen -------------------------------------------------------


def _profil(bogen: _Bogen, daten: dict) -> list:
    paare = list(daten.get("profil_daten", {}).items())
    return _sektion(bogen, "Profil", bogen.beschriftung_tabelle(paare, INHALT_BREITE))


def _attribute_fertigkeiten(bogen: _Bogen, daten: dict, setting: dict, werte: dict) -> list:
    spalte_breite = (INHALT_BREITE - 8 * mm) / 2

    # Linke Spalte: Attribute + Fertigkeiten
    attribute = daten.get("attribute", {})
    reihenfolge = [n for n in ATTRIBUT_REIHENFOLGE if n in attribute] + [
        n for n in attribute if n not in ATTRIBUT_REIHENFOLGE
    ]
    attr_paare = [
        (name, _wuerfel(attribute[name].get("wert", 4), attribute[name].get("modifier", 0)))
        for name in reihenfolge
    ]

    fert_paare = []
    for name, fert in sorted(daten.get("fertigkeiten", {}).items()):
        wuerfel = fert.get("wuerfel", {})
        if wuerfel.get("modifier", 0) == -2:  # ungelernt
            continue
        fert_paare.append((name, _wuerfel(wuerfel.get("value", 4), wuerfel.get("modifier", 0))))

    links = [
        bogen.band_flow("Attribute", spalte_breite), Spacer(1, 3),
        bogen.werte_tabelle(attr_paare, spalte_breite, 18 * mm), Spacer(1, 6),
        bogen.band_flow("Fertigkeiten", spalte_breite), Spacer(1, 3),
        bogen.werte_tabelle(fert_paare, spalte_breite, 18 * mm),
    ]
    rechts = _volk(bogen, daten, setting, spalte_breite) + [Spacer(1, 6)] + \
        _abgeleitete_werte(bogen, daten, werte, spalte_breite)

    zwei_spalten = Table(
        [[links, rechts]],
        colWidths=[spalte_breite, spalte_breite],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, 0), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), 4 * mm),
            ("LEFTPADDING", (1, 0), (1, 0), 4 * mm),
            ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )
    return [zwei_spalten, Spacer(1, 6)]


def _volk(bogen: _Bogen, daten: dict, setting: dict, breite: float) -> list:
    selected_volk = None
    volk_data = None
    for volk, eintrag in daten.get("voelker_selected", {}).items():
        if eintrag:
            selected_volk = volk
            volk_data = eintrag if isinstance(eintrag, dict) else None
            break

    if not selected_volk:
        return [bogen.p("Keine Abstammung ausgewählt.", bogen.hinweis)]

    if volk_data is None:
        volk_data = setting.get("voelker", {}).get(selected_volk)

    flows = [bogen.band_flow(f"Abstammung: {selected_volk}", breite), Spacer(1, 3)]
    if not volk_data:
        flows.append(bogen.p("Keine Daten für die ausgewählte Abstammung vorhanden.", bogen.hinweis))
        return flows

    for feld, spalte in (("talente", "Talent"), ("handicaps", "Handicap"),
                         ("besonderheiten", "Besonderheit")):
        eintraege = volk_data.get(feld) or []
        if eintraege:
            zeilen = [[bogen.p(spalte.upper(), bogen.kopfzelle)]]
            zeilen += [[bogen.p(e, bogen.text)] for e in eintraege]
            flows.append(_daten_tabelle(bogen, zeilen, [breite], kopf=True))
            flows.append(Spacer(1, 4))
    return flows


def _abgeleitete_werte(bogen: _Bogen, daten: dict, werte: dict, breite: float) -> list:
    groesse = werte.get("groesse", 0)
    robustheit = str(werte.get("robustheit", 4))
    if werte.get("panzerung"):
        robustheit += f" ({werte['panzerung']})"

    anzeige = {
        "Bewegungsweite": werte.get("bewegungsweite", 6),
        "Parade": werte.get("parade", 2),
        "Größe": f"{groesse:+d}" if groesse != 0 else "0",
        "Robustheit": robustheit,
        "Machtpunkte": werte.get("machtpunkte", 0),
        "Bennys": werte.get("bennys", 3),
        "Maximale Traglast": f"{werte.get('gesamtgewicht', 0):g} / {werte.get('traglast', 0):g} kg",
    }
    if daten.get("char_gen_completed") and werte.get("rang"):
        anzeige["Rang"] = f"{werte['rang']} ({daten.get('aufstiege_gesamt', 0)} Aufstiege)"

    paare = list(anzeige.items())
    cyber = werte.get("cyberware")
    if cyber:
        paare.append((
            "Cyberware Stress",
            f"{cyber.get('stress')} / {cyber.get('stresslimit')} (Max: {cyber.get('stress_maximum')})",
        ))
        installationen = len(daten.get("cyberware_installationen", {}))
        if installationen:
            paare.append(("Installationen", installationen))

    return [
        bogen.band_flow("Abgeleitete Werte", breite), Spacer(1, 3),
        bogen.werte_tabelle(paare, breite, 26 * mm),
    ]


def _daten_tabelle(bogen: _Bogen, zeilen: list, col_widths: list, kopf: bool = False,
                   gesamt_zeile: int | None = None) -> Table:
    """Generische Tabelle mit optionalem Kopf (erste Zeile) und Gesamt-Zeile."""
    t = Table(zeilen, colWidths=col_widths)
    stil = bogen._basis_tabellenstil()
    if kopf:
        stil.append(("BACKGROUND", (0, 0), (-1, 0), bogen.f["hervor"]))
    if gesamt_zeile is not None:
        stil.append(("BACKGROUND", (0, gesamt_zeile), (-1, gesamt_zeile), bogen.f["hervor"]))
        stil.append(("FONTNAME", (0, gesamt_zeile), (-1, gesamt_zeile), "Times-Bold"))
    t.setStyle(TableStyle(stil))
    return t


def _tabelle_mit_beschreibung(bogen: _Bogen, kopf: list, eintraege: list, col_widths: list) -> list:
    """Tabelle, deren Einträge optional eine Beschreibungszeile (span) haben.

    ``eintraege``: Liste von (zellen: list[str], beschreibung: str | None).
    """
    if not eintraege:
        return [bogen.p("Keine Einträge.", bogen.hinweis)]

    zeilen = [[bogen.p(k.upper(), bogen.kopfzelle) for k in kopf]]
    span_zeilen = []
    for zellen, beschreibung in eintraege:
        zeilen.append([bogen.p(z, bogen.text) for z in zellen])
        if beschreibung:
            span_zeilen.append(len(zeilen))
            zeilen.append([bogen.p(beschreibung, bogen.beschreibung)] +
                          [""] * (len(kopf) - 1))

    t = Table(zeilen, colWidths=col_widths)
    stil = bogen._basis_tabellenstil()
    stil.append(("BACKGROUND", (0, 0), (-1, 0), bogen.f["hervor"]))
    for zi in span_zeilen:
        stil.append(("SPAN", (0, zi), (-1, zi)))
    t.setStyle(TableStyle(stil))
    return [t]


def _handicaps(bogen: _Bogen, daten: dict, setting: dict) -> list:
    setting_handicaps = setting.get("handicaps", {})
    eintraege = []
    for name in daten.get("selected_handicaps", []):
        basis, stufe = name, None
        if name.endswith(("_leicht", "_schwer")):
            basis, stufe = name[:-7], name[-6:]
        eintrag = setting_handicaps.get(name) or setting_handicaps.get(basis) or {}
        stufe = stufe or eintrag.get("stufe", "")
        eintraege.append(([basis, stufe], eintrag.get("beschreibung")))

    breite_h = INHALT_BREITE - 30 * mm
    inhalt = _tabelle_mit_beschreibung(
        bogen, ["Handicap", "Stufe"], eintraege, [breite_h, 30 * mm]
    )
    return _sektion(bogen, "Handicaps", inhalt)


def _talente(bogen: _Bogen, daten: dict, setting: dict) -> list:
    setting_talente = setting.get("talente", {})
    eintraege = []
    for name in daten.get("selected_talente", []):
        eintrag = setting_talente.get(name) or {}
        eintraege.append(([name, eintrag.get("rang", "")], eintrag.get("beschreibung")))

    breite_t = INHALT_BREITE - 30 * mm
    inhalt = _tabelle_mit_beschreibung(
        bogen, ["Talent", "Rang"], eintraege, [breite_t, 30 * mm]
    )
    return _sektion(bogen, "Talente", inhalt)


def _maechte(bogen: _Bogen, daten: dict, setting: dict) -> list | None:
    maechte = daten.get("selected_maechte", [])
    if not maechte:
        return None

    setting_maechte = setting.get("maechte", {})
    eintraege = []
    for name in maechte:
        macht = setting_maechte.get(name) or {}
        eintraege.append((
            [name, macht.get("rang", ""), macht.get("machtpunkte", ""),
             macht.get("reichweite", ""), macht.get("dauer", "")],
            macht.get("beschreibung"),
        ))

    rest = INHALT_BREITE - 4 * (18 * mm)
    inhalt = _tabelle_mit_beschreibung(
        bogen, ["Name", "Rang", "MP", "Reichweite", "Dauer"], eintraege,
        [rest, 18 * mm, 18 * mm, 18 * mm, 18 * mm],
    )
    return _sektion(bogen, "Mächte", inhalt)


def _superkraefte(bogen: _Bogen, daten: dict, setting: dict, werte: dict) -> list | None:
    auswahl = daten.get("selected_superkraefte", {})
    skp = werte.get("superkraefte")
    if not auswahl or not skp:
        return None

    titel = (f"Superkräfte (Machtstufe {skp.get('stufe')}, "
             f"{skp.get('ausgegeben')}/{skp.get('budget')} SKP)")
    krafte = setting.get("krafte", {})
    eintraege = []
    for name, eintrag in sorted(auswahl.items()):
        kraft = krafte.get(name) or {}
        punkte = eintrag.get("punkte", 0)
        modifikatoren = eintrag.get("modifikatoren") or {}
        gesamt = punkte + sum(modifikatoren.values())
        mod_text = ", ".join(sorted(modifikatoren))
        eintraege.append((
            [name, kraft.get("kosten", ""), punkte, mod_text, gesamt],
            kraft.get("beschreibung"),
        ))

    rest = INHALT_BREITE - (20 * mm + 16 * mm + 40 * mm + 16 * mm)
    inhalt = _tabelle_mit_beschreibung(
        bogen, ["Name", "Basis", "SKP", "Modifikatoren", "Gesamt"], eintraege,
        [rest, 20 * mm, 16 * mm, 40 * mm, 16 * mm],
    )
    return _sektion(bogen, titel, inhalt)


def _allgemeine_ausruestung(bogen: _Bogen, daten: dict, setting: dict) -> list:
    eintraege = []
    for name, eintrag, item in _gekaufte_items(daten, setting):
        if item.get("kategorie") in ("Waffe",) + ANLEGBARE_KATEGORIEN:
            continue
        eintraege.append(([name, eintrag.get("anzahl", 1), item.get("beschreibung", "-")], None))

    rest = INHALT_BREITE - (20 * mm + 70 * mm)
    inhalt = _tabelle_mit_beschreibung(
        bogen, ["Name", "Menge", "Beschreibung"], eintraege, [rest, 20 * mm, 70 * mm]
    )
    return _sektion(bogen, "Allgemeine Ausrüstung", inhalt)


def _waffen(bogen: _Bogen, daten: dict, setting: dict) -> list | None:
    eintraege = []
    for name, _eintrag, item in _gekaufte_items(daten, setting):
        if item.get("kategorie") != "Waffe":
            continue
        eig = item.get("eigenschaften") or {}
        eintraege.append(([
            name, eig.get("Schaden", "-"), eig.get("Reichweite", "-"),
            eig.get("FR", "-"), eig.get("Schuss", "-"), eig.get("PB", "-"),
        ], None))
    if not eintraege:
        return None

    sp = 18 * mm
    rest = INHALT_BREITE - 5 * sp
    inhalt = _tabelle_mit_beschreibung(
        bogen, ["Name", "Schaden", "Reichweite", "FR", "Schuss", "PB"], eintraege,
        [rest, sp, sp, sp, sp, sp],
    )
    return _sektion(bogen, "Waffen", inhalt)


def _ruestungen(bogen: _Bogen, daten: dict, setting: dict) -> list | None:
    angelegte = [
        (name, item)
        for name, eintrag, item in _gekaufte_items(daten, setting)
        if item.get("kategorie") == "Rüstung" and eintrag.get("angelegt")
    ]
    if not angelegte:
        return None

    sp = 22 * mm
    rest = INHALT_BREITE - 4 * sp
    zeilen = [[bogen.p(k.upper(), bogen.kopfzelle)
               for k in ("Name", "Torso", "Arme", "Beine", "Kopf")]]
    gesamt = {"torso": 0, "arme": 0, "beine": 0, "kopf": 0}
    for name, item in angelegte:
        zeilen.append([
            bogen.p(name, bogen.text),
            bogen.p(item.get("torso", 0), bogen.wert),
            bogen.p(item.get("arme", 0), bogen.wert),
            bogen.p(item.get("beine", 0), bogen.wert),
            bogen.p(item.get("kopf", 0), bogen.wert),
        ])
        for teil in gesamt:
            gesamt[teil] += item.get(teil, 0) or 0
    zeilen.append([
        bogen.p("Gesamt", bogen.text),
        bogen.p(gesamt["torso"], bogen.wert),
        bogen.p(gesamt["arme"], bogen.wert),
        bogen.p(gesamt["beine"], bogen.wert),
        bogen.p(gesamt["kopf"], bogen.wert),
    ])

    tabelle = _daten_tabelle(bogen, zeilen, [rest, sp, sp, sp, sp], kopf=True,
                             gesamt_zeile=len(zeilen) - 1)
    return _sektion(bogen, "Rüstungen", tabelle)


def _schilde(bogen: _Bogen, daten: dict, setting: dict) -> list | None:
    eintraege = []
    for name, eintrag, item in _gekaufte_items(daten, setting):
        if item.get("kategorie") != "Schild" or not eintrag.get("angelegt"):
            continue
        eintraege.append(([
            name, item.get("parade", "-"), item.get("deckung", "-"),
            item.get("mindeststaerke", "-"),
        ], None))
    if not eintraege:
        return None

    sp = 30 * mm
    rest = INHALT_BREITE - 3 * sp
    inhalt = _tabelle_mit_beschreibung(
        bogen, ["Name", "Parade", "Deckung", "Mindeststärke"], eintraege,
        [rest, sp, sp, sp],
    )
    return _sektion(bogen, "Schilde", inhalt)


def _steigerungen(bogen: _Bogen, daten: dict) -> list | None:
    journal = daten.get("steigerungs_journal")
    if not journal or not isinstance(journal, dict):
        return None

    eintraege = []
    if journal.get("entries"):
        for entry in journal["entries"]:
            entry_type = entry.get("type")
            if entry_type not in _STEIGERUNGS_TYPEN:
                continue
            details = entry.get("details") or {}
            name = details.get("name", "")
            if entry_type in ("attribut_steigerung", "fertigkeit_steigerung"):
                name = f"{name}: W{details.get('von', '')} → W{details.get('nach', '')}"
            elif "entfernt" in entry_type:
                name = f"{name} (entfernt)"
            elif entry_type == "handicap_reduziert":
                name = f"{name} (reduziert)"
            kosten = _kosten_text(
                details.get("kosten", details.get("punkte", "")), details.get("kosten_typ", "")
            )
            eintraege.append([entry.get("rang", ""), _STEIGERUNGS_TYPEN[entry_type], name, kosten])
    elif journal.get("cost_entries"):
        char_rang = charakter_rang(daten)
        for eintrag in journal["cost_entries"]:
            typ = _COST_ENTRY_TYPEN.get(eintrag.get("typ", ""), eintrag.get("typ", ""))
            name = eintrag.get("name", "")
            if eintrag.get("wert") and eintrag.get("typ") in ("attribut", "fertigkeit"):
                name = f"{name}: W{eintrag['wert']}"
            kosten = _kosten_text(eintrag.get("kosten", ""), eintrag.get("zahlungsquelle", ""))
            eintraege.append([char_rang, typ, name, kosten])

    if not eintraege:
        return None

    inhalt = _tabelle_mit_beschreibung(
        bogen, ["Rang", "Typ", "Name", "Kosten"],
        [(zellen, None) for zellen in eintraege],
        [20 * mm, 26 * mm, INHALT_BREITE - 20 * mm - 26 * mm - 30 * mm, 30 * mm],
    )
    return _sektion(bogen, "Steigerungen", inhalt)


def _mach_hintergrund(bogen: _Bogen):
    """Füllt jede Seite mit Pergament (bzw. weiß bei printer_friendly)."""
    papier = bogen.f["papier"]
    linie = bogen.f["linie"]
    printer = bogen.printer_friendly

    def zeichne(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(papier)
        canvas.rect(0, 0, SEITE[0], SEITE[1], stroke=0, fill=1)
        if not printer:
            canvas.setStrokeColor(linie)
            canvas.setLineWidth(0.75)
            canvas.rect(RAND / 2, RAND / 2, SEITE[0] - RAND, SEITE[1] - RAND,
                        stroke=1, fill=0)
        canvas.restoreState()

    return zeichne


def generiere_charakterbogen_pdf(
    daten: dict, setting: dict, werte: dict, printer_friendly: bool = False
) -> bytes:
    """Erzeugt den Charakterbogen als PDF (DIN A4).

    werte: das Ergebnis von /spiellogik/berechne für dieselben daten.
    """
    bogen = _Bogen(printer_friendly)
    puffer = BytesIO()
    name = daten.get("profil_daten", {}).get("Name") or "Charakterbogen"
    doc = SimpleDocTemplate(
        puffer, pagesize=SEITE,
        leftMargin=RAND, rightMargin=RAND, topMargin=RAND, bottomMargin=RAND,
        title=name, author="Savage Worlds Charakter-Generator",
    )

    flowables = _kopf(bogen, daten)
    flowables += _profil(bogen, daten)
    flowables += _attribute_fertigkeiten(bogen, daten, setting, werte)
    flowables += _handicaps(bogen, daten, setting)
    flowables += _talente(bogen, daten, setting)
    for optional in (
        _maechte(bogen, daten, setting),
        _superkraefte(bogen, daten, setting, werte),
        _allgemeine_ausruestung(bogen, daten, setting),
        _waffen(bogen, daten, setting),
        _ruestungen(bogen, daten, setting),
        _schilde(bogen, daten, setting),
        _steigerungen(bogen, daten),
    ):
        if optional:
            flowables += optional

    hintergrund = _mach_hintergrund(bogen)
    doc.build(flowables, onFirstPage=hintergrund, onLaterPages=hintergrund)
    return puffer.getvalue()
