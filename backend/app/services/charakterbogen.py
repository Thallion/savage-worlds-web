"""HTML-Charakterbogen (Original: utils/html_utils.py).

Erzeugt den kompletten Charakterbogen als eigenständiges HTML5-Dokument mit
Inline-CSS. Sektionen wie im Kivy-Original: Profil, Attribute/Fertigkeiten
neben Abstammung/abgeleiteten Werten, Handicaps, Talente, Mächte,
Superkräfte, Ausrüstung, Waffen, Rüstungen, Schilde.

Das Layout ist an klassische Pen-&-Paper-Bögen angelehnt: Pergament-Papier,
Serifenschrift, Sektionsbänder in dunklem Braun mit hellen Kapitälchen und
Werte in eigenen Kästchen. `printer_friendly` rendert dieselbe Struktur in
Schwarz-Weiß ohne Flächenfarben.

Abweichungen vom Original:
- Wunden, Erschöpfung und Entschlossenheit fehlen (Spielzustand, den die
  Web-App nicht verwaltet).
- Waffen werden alle gekauften gelistet ("angelegt" gibt es hier nur für
  Rüstungen und Schilde).
"""

import base64
import functools
import html
from pathlib import Path

from app.services.aufstiege import rang_fuer_aufstiege
from app.services.statblock import ATTRIBUT_REIHENFOLGE
from app.services.volk_effekte import gewaehltes_volk

ANLEGBARE_KATEGORIEN = ("Rüstung", "Schild")

# Vier Genre-Icons (Schwert, Totenkopf, Ray-Gun, Zeppelin), direkt aus den
# Roundels des offiziellen Savage-Worlds-Logos ausgeschnitten und als flache
# Silhouette in Tinten- bzw. Sektionsband-Farbe eingefärbt (statt Nachbau als
# SVG). Zwei Farbvarianten liegen als PNG bereit ("brown" fürs Pergament-
# Layout, "black" für printer_friendly), damit der Bogen ein eigenständiges
# HTML-Dokument ohne Bild-Referenzen nach außen bleibt.
_ICON_NAMES = ("sword", "skull", "raygun", "airship")
_ICON_DIR = Path(__file__).parent / "assets" / "charakterbogen_icons"


@functools.lru_cache(maxsize=None)
def _icon_data_uri(name: str, variante: str) -> str:
    daten = (_ICON_DIR / f"{name}_{variante}.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(daten).decode("ascii")


def _genre_icons(printer_friendly: bool) -> tuple[str, ...]:
    variante = "black" if printer_friendly else "brown"
    return tuple(
        f'<img src="{_icon_data_uri(name, variante)}" alt="">' for name in _ICON_NAMES
    )


def _esc(text) -> str:
    return html.escape(str(text)) if text is not None else ""


def _wuerfel(wert: int, modifier: int = 0) -> str:
    if modifier:
        return f"W{wert} {modifier:+d}"
    return f"W{wert}"


def _tabelle(kopf: list[str] | None, zeilen: str) -> str:
    if not zeilen:
        return '<p class="hinweis">Keine Einträge.</p>'
    kopf_html = ""
    if kopf:
        kopf_html = "<tr>" + "".join(f"<th>{_esc(k)}</th>" for k in kopf) + "</tr>\n"
    return f"<table>\n{kopf_html}{zeilen}</table>"


def _farbschema(printer_friendly: bool) -> dict[str, str]:
    if printer_friendly:
        # Schwarz-Weiß: keine Flächenfarben, nur Linien.
        return {
            "seite": "#ffffff", "papier": "#ffffff", "zeile": "#ffffff",
            "hervor": "#ffffff", "band_bg": "#ffffff",
            "tinte": "#111111", "band_fg": "#111111", "band_rand": "#111111",
            "gedeckt": "#444444", "linie": "#999999", "schatten": "none",
        }
    return {
        "seite": "#e9e2cf",     # Tisch hinter dem Bogen
        "papier": "#f6f1e3",    # Pergament
        "zeile": "#faf6ea",     # Tabellenzeilen
        "hervor": "#e8dfc8",    # Tabellenköpfe, Gesamt-Zellen
        "tinte": "#2f2a22",
        "gedeckt": "#6a5f4b",   # Beschriftungen, Beschreibungen
        "band_bg": "#6b5138", "band_rand": "#6b5138",  # Sektionsbänder
        "band_fg": "#f6f1e3",
        "linie": "#c4b596",
        "schatten": "0 2px 14px rgba(64, 48, 24, 0.25)",
    }


def _erzeuge_html_dokument(
    title: str, kopf_html: str, body_content: str, printer_friendly: bool
) -> str:
    farben = _farbschema(printer_friendly)
    seite = farben["seite"]; papier = farben["papier"]; zeile = farben["zeile"]
    hervor = farben["hervor"]; band_bg = farben["band_bg"]
    tinte = farben["tinte"]; band_fg = farben["band_fg"]; band_rand = farben["band_rand"]
    gedeckt = farben["gedeckt"]; linie = farben["linie"]; schatten = farben["schatten"]

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{
    font-family: Georgia, 'Palatino Linotype', 'Book Antiqua', 'Times New Roman', serif;
    font-size: 10pt;
    line-height: 1.45;
    color: {tinte};
    background-color: {seite};
    margin: 0;
    padding: 24px 12px;
}}
.bogen {{
    max-width: 860px;
    margin: 0 auto;
    background-color: {papier};
    border: 1px solid {linie};
    box-shadow: {schatten};
    padding: 28px 34px 34px;
}}
.kopf {{
    text-align: center;
    border-bottom: 3px double {band_rand};
    padding-bottom: 14px;
    margin-bottom: 4px;
}}
.kopf .icon-row {{
    display: flex;
    justify-content: center;
    gap: 10px;
    margin-bottom: 8px;
}}
.kopf .icon-badge {{
    width: 30px;
    height: 30px;
    border-radius: 50%;
    border: 1.5px solid {band_rand};
    background-color: {hervor};
    color: {band_rand};
    display: flex;
    align-items: center;
    justify-content: center;
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
}}
.kopf .icon-badge img {{
    width: 20px;
    height: 20px;
    display: block;
}}
h1 {{
    font-size: 20pt;
    font-weight: normal;
    text-transform: uppercase;
    letter-spacing: 0.3em;
    margin: 0;
}}
.kopf .untertitel {{
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.4em;
    color: {gedeckt};
    margin-top: 6px;
}}
h2 {{
    font-size: 9.5pt;
    font-weight: normal;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: {band_fg};
    background-color: {band_bg};
    border: 1px solid {band_rand};
    padding: 5px 12px;
    margin: 18px 0 0 0;
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    background-color: {zeile};
    border: 1px solid {linie};
    border-top: none;
    margin: 0 0 4px 0;
}}
th {{
    font-weight: normal;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: {gedeckt};
    background-color: {hervor};
    border-bottom: 1px solid {linie};
    padding: 4px 10px;
    text-align: left;
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
}}
td {{
    padding: 4px 10px;
    text-align: left;
    vertical-align: top;
    border-top: 1px solid {linie};
}}
table tr:first-child > td {{
    border-top: none;
}}
td.wert {{
    width: 72px;
    text-align: center;
    font-weight: bold;
    white-space: nowrap;
    border-left: 1px solid {linie};
}}
td.feld {{
    width: 34%;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {gedeckt};
    padding-top: 6px;
}}
td.gesamt {{
    background-color: {hervor};
    font-weight: bold;
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
}}
td.beschreibung {{
    font-size: 8.5pt;
    font-style: italic;
    color: {gedeckt};
    border-top: none;
    padding-top: 0;
}}
.two-column {{
    display: flex;
    gap: 26px;
    flex-wrap: wrap;
    align-items: flex-start;
}}
.two-column > div {{
    flex: 1 1 300px;
    min-width: 260px;
}}
.hinweis {{
    font-style: italic;
    color: {gedeckt};
    margin: 6px 2px 10px;
}}
@media print {{
    body {{
        background-color: #fff;
        padding: 0;
    }}
    .bogen {{
        max-width: none;
        border: none;
        box-shadow: none;
        padding: 0;
    }}
    h2 {{
        break-after: avoid;
    }}
    tr {{
        break-inside: avoid;
    }}
}}
@media (max-width: 600px) {{
    body {{
        padding: 0;
    }}
    .bogen {{
        border: none;
        padding: 16px 14px 24px;
    }}
    .two-column {{
        flex-direction: column;
    }}
}}
</style>
</head>
<body>
<div class="bogen">
{kopf_html}
{body_content}
</div>
</body>
</html>"""


def _kopf_sektion(daten: dict, printer_friendly: bool) -> str:
    name = daten.get("profil_daten", {}).get("Name") or "Unbenannter Charakter"
    untertitel = "Charakterbogen"
    setting_name = daten.get("active_setting_name")
    if setting_name:
        untertitel += f" · {setting_name}"
    icons = _genre_icons(printer_friendly)
    icon_row = "".join(f'<span class="icon-badge">{svg}</span>' for svg in icons)
    return f"""<header class="kopf">
<div class="icon-row">{icon_row}</div>
<h1>{_esc(name)}</h1>
<div class="untertitel">{_esc(untertitel)}</div>
</header>"""


def _profil_sektion(daten: dict) -> str:
    rows = ""
    for key, value in daten.get("profil_daten", {}).items():
        rows += f'<tr><td class="feld">{_esc(key)}</td><td>{_esc(value)}</td></tr>\n'
    return "<h2>Profil</h2>\n" + _tabelle(None, rows)


def _attribute_fertigkeiten_sektion(daten: dict, setting: dict, werte: dict) -> str:
    attribute = daten.get("attribute", {})
    reihenfolge = [n for n in ATTRIBUT_REIHENFOLGE if n in attribute] + [
        n for n in attribute if n not in ATTRIBUT_REIHENFOLGE
    ]
    attr_rows = ""
    for name in reihenfolge:
        attr = attribute[name]
        kombi = _wuerfel(attr.get("wert", 4), attr.get("modifier", 0))
        attr_rows += f'<tr><td>{_esc(name)}</td><td class="wert">{_esc(kombi)}</td></tr>\n'

    left_html = "<h2>Attribute</h2>\n" + _tabelle(None, attr_rows)

    fert_rows = ""
    for name, fert in sorted(daten.get("fertigkeiten", {}).items()):
        wuerfel = fert.get("wuerfel", {})
        if wuerfel.get("modifier", 0) == -2:  # ungelernt
            continue
        kombi = _wuerfel(wuerfel.get("value", 4), wuerfel.get("modifier", 0))
        fert_rows += f'<tr><td>{_esc(name)}</td><td class="wert">{_esc(kombi)}</td></tr>\n'

    left_html += "\n<h2>Fertigkeiten</h2>\n" + _tabelle(None, fert_rows)

    right_html = _volk_sektion(daten, setting) + _abgeleitete_werte_sektion(daten, werte)

    return f"""<div class="two-column">
<div>{left_html}</div>
<div>{right_html}</div>
</div>"""


def _volk_sektion(daten: dict, setting: dict) -> str:
    selected_volk, volk_data = gewaehltes_volk(daten, setting)
    if not selected_volk:
        return '<p class="hinweis">Keine Abstammung ausgewählt.</p>'

    result = f"<h2>Abstammung: {_esc(selected_volk)}</h2>"
    if not volk_data:
        return result + '<p class="hinweis">Keine Daten für die ausgewählte Abstammung vorhanden.</p>'

    for feld, spalte in (("talente", "Talent"), ("handicaps", "Handicap"), ("besonderheiten", "Besonderheit")):
        eintraege = volk_data.get(feld) or []
        if eintraege:
            rows = "".join(f"<tr><td>{_esc(e)}</td></tr>\n" for e in eintraege)
            result += _tabelle([spalte], rows)

    return result


def _abgeleitete_werte_sektion(daten: dict, werte: dict) -> str:
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

    rows = ""
    for key, value in anzeige.items():
        rows += f'<tr><td>{_esc(key)}</td><td class="wert">{_esc(value)}</td></tr>\n'

    cyber = werte.get("cyberware")
    if cyber:
        rows += (
            f'<tr><td>Cyberware Stress</td><td class="wert">{_esc(cyber.get("stress"))} / '
            f'{_esc(cyber.get("stresslimit"))} (Max: {_esc(cyber.get("stress_maximum"))})</td></tr>\n'
        )
        installationen = len(daten.get("cyberware_installationen", {}))
        if installationen:
            rows += f'<tr><td>Installationen</td><td class="wert">{_esc(installationen)}</td></tr>\n'

    return "<h2>Abgeleitete Werte</h2>\n" + _tabelle(None, rows)


def _handicaps_sektion(daten: dict, setting: dict) -> str:
    setting_handicaps = setting.get("handicaps", {})
    rows = ""
    for name in daten.get("selected_handicaps", []):
        basis, stufe = name, None
        if name.endswith(("_leicht", "_schwer")):
            basis, stufe = name[:-7], name[-6:]
        eintrag = setting_handicaps.get(name) or setting_handicaps.get(basis) or {}
        stufe = stufe or eintrag.get("stufe", "")
        rows += f"<tr><td>{_esc(basis)}</td><td>{_esc(stufe)}</td></tr>\n"
        if eintrag.get("beschreibung"):
            rows += f'<tr><td colspan="2" class="beschreibung">{_esc(eintrag["beschreibung"])}</td></tr>\n'

    return "<h2>Handicaps</h2>\n" + _tabelle(["Handicap", "Stufe"], rows)


def _talente_sektion(daten: dict, setting: dict) -> str:
    setting_talente = setting.get("talente", {})
    rows = ""
    for name in daten.get("selected_talente", []):
        eintrag = setting_talente.get(name) or {}
        rows += f"<tr><td>{_esc(name)}</td><td>{_esc(eintrag.get('rang', ''))}</td></tr>\n"
        if eintrag.get("beschreibung"):
            rows += f'<tr><td colspan="2" class="beschreibung">{_esc(eintrag["beschreibung"])}</td></tr>\n'

    return "<h2>Talente</h2>\n" + _tabelle(["Talent", "Rang"], rows)


def _maechte_sektion(daten: dict, setting: dict) -> str | None:
    maechte = daten.get("selected_maechte", [])
    if not maechte:
        return None

    setting_maechte = setting.get("maechte", {})
    rows = ""
    for name in maechte:
        macht = setting_maechte.get(name) or {}
        rows += (
            f"<tr><td>{_esc(name)}</td><td>{_esc(macht.get('rang', ''))}</td>"
            f"<td>{_esc(macht.get('machtpunkte', ''))}</td><td>{_esc(macht.get('reichweite', ''))}</td>"
            f"<td>{_esc(macht.get('dauer', ''))}</td></tr>\n"
        )
        if macht.get("beschreibung"):
            rows += f'<tr><td colspan="5" class="beschreibung">{_esc(macht["beschreibung"])}</td></tr>\n'

    return "<h2>Mächte</h2>\n" + _tabelle(["Name", "Rang", "MP", "Reichweite", "Dauer"], rows)


def _superkraefte_sektion(daten: dict, setting: dict, werte: dict) -> str | None:
    auswahl = daten.get("selected_superkraefte", {})
    skp = werte.get("superkraefte")
    if not auswahl or not skp:
        return None

    titel = _esc(
        f"Superkräfte (Machtstufe {skp.get('stufe')}, {skp.get('ausgegeben')}/{skp.get('budget')} SKP)"
    )
    krafte = setting.get("krafte", {})
    rows = ""
    for name, eintrag in sorted(auswahl.items()):
        kraft = krafte.get(name) or {}
        punkte = eintrag.get("punkte", 0)
        modifikatoren = eintrag.get("modifikatoren") or {}
        gesamt = punkte + sum(modifikatoren.values())
        mod_text = ", ".join(sorted(modifikatoren))
        rows += (
            f"<tr><td>{_esc(name)}</td><td>{_esc(kraft.get('kosten', ''))}</td>"
            f"<td>{_esc(punkte)}</td><td>{_esc(mod_text)}</td>"
            f"<td>{_esc(gesamt)}</td></tr>\n"
        )
        if kraft.get("beschreibung"):
            rows += f'<tr><td colspan="5" class="beschreibung">{_esc(kraft["beschreibung"])}</td></tr>\n'

    return f"<h2>{titel}</h2>\n" + _tabelle(["Name", "Basis", "SKP", "Modifikatoren", "Gesamt"], rows)


def _gekaufte_items(daten: dict, setting: dict):
    """(name, eintrag, item_daten) für alle gekauften Gegenstände."""
    katalog = setting.get("ausruestung", {})
    for name, eintrag in sorted(daten.get("ausruestung_selected", {}).items()):
        if eintrag.get("anzahl", 0) <= 0:
            continue
        yield name, eintrag, katalog.get(name) or {}


def _allgemeine_ausruestung_sektion(daten: dict, setting: dict) -> str:
    rows = ""
    for name, eintrag, item in _gekaufte_items(daten, setting):
        if item.get("kategorie") in ("Waffe",) + ANLEGBARE_KATEGORIEN:
            continue
        rows += (
            f"<tr><td>{_esc(name)}</td><td>{_esc(eintrag.get('anzahl', 1))}</td>"
            f"<td>{_esc(item.get('beschreibung', '-'))}</td></tr>\n"
        )

    return "<h2>Allgemeine Ausrüstung</h2>\n" + _tabelle(["Name", "Menge", "Beschreibung"], rows)


def _waffen_sektion(daten: dict, setting: dict) -> str | None:
    rows = ""
    for name, _eintrag, item in _gekaufte_items(daten, setting):
        if item.get("kategorie") != "Waffe":
            continue
        eigenschaften = item.get("eigenschaften") or {}
        rows += (
            f"<tr><td>{_esc(name)}</td>"
            f"<td>{_esc(eigenschaften.get('Schaden', '-'))}</td>"
            f"<td>{_esc(eigenschaften.get('Reichweite', '-'))}</td>"
            f"<td>{_esc(eigenschaften.get('FR', '-'))}</td>"
            f"<td>{_esc(eigenschaften.get('Schuss', '-'))}</td>"
            f"<td>{_esc(eigenschaften.get('PB', '-'))}</td></tr>\n"
        )
    if not rows:
        return None

    return "<h2>Waffen</h2>\n" + _tabelle(
        ["Name", "Schaden", "Reichweite", "FR", "Schuss", "PB"], rows
    )


def _ruestungen_sektion(daten: dict, setting: dict) -> str | None:
    angelegte = [
        (name, item)
        for name, eintrag, item in _gekaufte_items(daten, setting)
        if item.get("kategorie") == "Rüstung" and eintrag.get("angelegt")
    ]
    if not angelegte:
        return None

    rows = ""
    gesamt = {"torso": 0, "arme": 0, "beine": 0, "kopf": 0}
    for name, item in angelegte:
        rows += (
            f"<tr><td>{_esc(name)}</td>"
            f"<td>{_esc(item.get('torso', 0))}</td>"
            f"<td>{_esc(item.get('arme', 0))}</td>"
            f"<td>{_esc(item.get('beine', 0))}</td>"
            f"<td>{_esc(item.get('kopf', 0))}</td></tr>\n"
        )
        for teil in gesamt:
            gesamt[teil] += item.get(teil, 0) or 0

    rows += (
        f'<tr><td class="gesamt">Gesamt</td>'
        f'<td class="gesamt">{gesamt["torso"]}</td>'
        f'<td class="gesamt">{gesamt["arme"]}</td>'
        f'<td class="gesamt">{gesamt["beine"]}</td>'
        f'<td class="gesamt">{gesamt["kopf"]}</td></tr>\n'
    )

    return "<h2>Rüstungen</h2>\n" + _tabelle(["Name", "Torso", "Arme", "Beine", "Kopf"], rows)


def _schilde_sektion(daten: dict, setting: dict) -> str | None:
    rows = ""
    for name, eintrag, item in _gekaufte_items(daten, setting):
        if item.get("kategorie") != "Schild" or not eintrag.get("angelegt"):
            continue
        rows += (
            f"<tr><td>{_esc(name)}</td>"
            f"<td>{_esc(item.get('parade', '-'))}</td>"
            f"<td>{_esc(item.get('deckung', '-'))}</td>"
            f"<td>{_esc(item.get('mindeststaerke', '-'))}</td></tr>\n"
        )
    if not rows:
        return None

    return "<h2>Schilde</h2>\n" + _tabelle(["Name", "Parade", "Deckung", "Mindeststärke"], rows)


_STEIGERUNGS_TYPEN = {
    "attribut_steigerung": "Attribut",
    "fertigkeit_steigerung": "Fertigkeit",
    "talent_hinzugefuegt": "Talent",
    "talent_entfernt": "Talent",
    "handicap_hinzugefuegt": "Handicap",
    "handicap_entfernt": "Handicap",
    "handicap_reduziert": "Handicap",
    "macht_hinzugefuegt": "Macht",
    "macht_entfernt": "Macht",
}

_COST_ENTRY_TYPEN = {
    "attribut": "Attribut",
    "fertigkeit": "Fertigkeit",
    "talent": "Talent",
    "handicap": "Handicap",
    "macht": "Macht",
}


def _kosten_text(kosten, einheit: str) -> str:
    if kosten in ("", None):
        return ""
    if isinstance(kosten, (int, float)):
        kosten = f"{kosten:g}"
    return f"{kosten} {einheit}".strip()


def _steigerungen_sektion(daten: dict) -> str | None:
    """Steigerungs-Journal (Original: _erzeuge_steigerungen_sektion in
    utils/html_utils.py). Bevorzugt die Historie-Einträge (entries, von der
    Web-App nach Abschluss der Erschaffung geschrieben); Kivy-Importe und
    Archetypen ohne Historie bringen stattdessen das Kauf-Journal cost_entries
    mit. Dessen Zeilen tragen keinen Rang — Erschaffungs-Käufe werden als
    "Start" ausgewiesen, mit Aufstiegen bezahlte über die laufende Summe der
    ausgegebenen Aufstiege dem damaligen Rang zugeordnet (die Liste ist
    chronologisch)."""
    journal = daten.get("steigerungs_journal")
    if not journal or not isinstance(journal, dict):
        return None

    rows = ""
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
            rows += (
                f"<tr><td>{_esc(entry.get('rang', ''))}</td><td>{_esc(_STEIGERUNGS_TYPEN[entry_type])}</td>"
                f"<td>{_esc(name)}</td><td>{_esc(kosten)}</td></tr>\n"
            )
    elif journal.get("cost_entries"):
        ausgegebene_aufstiege = 0.0
        for eintrag in journal["cost_entries"]:
            quelle = str(eintrag.get("zahlungsquelle", ""))
            if "aufstieg" in quelle.lower():
                kosten_wert = eintrag.get("kosten")
                if isinstance(kosten_wert, (int, float)):
                    ausgegebene_aufstiege += kosten_wert
                rang = rang_fuer_aufstiege(ausgegebene_aufstiege)
            else:
                rang = "Start"
            typ = _COST_ENTRY_TYPEN.get(eintrag.get("typ", ""), eintrag.get("typ", ""))
            name = eintrag.get("name", "")
            if eintrag.get("wert") and eintrag.get("typ") in ("attribut", "fertigkeit"):
                name = f"{name}: W{eintrag['wert']}"
            kosten = _kosten_text(eintrag.get("kosten", ""), quelle)
            rows += (
                f"<tr><td>{_esc(rang)}</td><td>{_esc(typ)}</td>"
                f"<td>{_esc(name)}</td><td>{_esc(kosten)}</td></tr>\n"
            )

    if not rows:
        return None

    return "<h2>Steigerungen</h2>\n" + _tabelle(["Rang", "Typ", "Name", "Kosten"], rows)


def generiere_charakterbogen(
    daten: dict, setting: dict, werte: dict, printer_friendly: bool = False
) -> str:
    """werte: das Ergebnis von /spiellogik/berechne für dieselben daten."""
    sections = [
        _profil_sektion(daten),
        _attribute_fertigkeiten_sektion(daten, setting, werte),
        _handicaps_sektion(daten, setting),
        _talente_sektion(daten, setting),
    ]
    for optional in (
        _maechte_sektion(daten, setting),
        _superkraefte_sektion(daten, setting, werte),
        _allgemeine_ausruestung_sektion(daten, setting),
        _waffen_sektion(daten, setting),
        _ruestungen_sektion(daten, setting),
        _schilde_sektion(daten, setting),
        _steigerungen_sektion(daten),
    ):
        if optional:
            sections.append(optional)

    name = daten.get("profil_daten", {}).get("Name") or "Charakterbogen"
    return _erzeuge_html_dokument(
        _esc(name), _kopf_sektion(daten, printer_friendly), "\n".join(sections), printer_friendly
    )
