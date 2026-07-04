"""HTML-Charakterbogen (Original: utils/html_utils.py).

Erzeugt den kompletten Charakterbogen als eigenständiges HTML5-Dokument mit
Inline-CSS — Layout, Farben und Sektionen wie im Kivy-Original: Profil,
Attribute/Fertigkeiten neben Abstammung/abgeleiteten Werten, Handicaps,
Talente, Mächte, Superkräfte, Ausrüstung, Waffen, Rüstungen, Schilde.

Abweichungen vom Original:
- Wunden, Erschöpfung und Entschlossenheit fehlen (Spielzustand, den die
  Web-App nicht verwaltet).
- Die Steigerungen-Sektion fehlt (kein Steigerungs-Journal in der Web-App).
- Waffen werden alle gekauften gelistet ("angelegt" gibt es hier nur für
  Rüstungen und Schilde).
"""

import html

from app.services.statblock import ATTRIBUT_REIHENFOLGE

ANLEGBARE_KATEGORIEN = ("Rüstung", "Schild")


def _esc(text) -> str:
    return html.escape(str(text)) if text is not None else ""


def _wuerfel(wert: int, modifier: int = 0) -> str:
    if modifier:
        return f"W{wert} {modifier:+d}"
    return f"W{wert}"


def _tabelle(kopf: list[str], zeilen: str) -> str:
    kopf_html = "".join(f"<th>{_esc(k)}</th>" for k in kopf)
    return f"<table>\n<tr>{kopf_html}</tr>\n{zeilen}</table>"


def _erzeuge_html_dokument(title: str, body_content: str, printer_friendly: bool) -> str:
    if printer_friendly:
        header_bg = row_bg = body_bg = "#ffffff"
    else:
        header_bg = "#ffb961"
        row_bg = "#FFE4B5"
        body_bg = "#FFF8DC"

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10pt;
    color: #000;
    background-color: {body_bg};
    margin: 10px;
    padding: 0;
}}
h1 {{
    font-size: 16pt;
    margin: 0 0 8px 0;
}}
h2 {{
    font-size: 12pt;
    margin: 12px 0 4px 0;
}}
table {{
    border-collapse: collapse;
    margin-bottom: 8px;
}}
th, td {{
    border: 1px solid #000;
    padding: 3px 6px;
    text-align: left;
    vertical-align: top;
}}
th {{
    background-color: {header_bg};
    font-weight: bold;
}}
td {{
    background-color: {row_bg};
}}
td.gesamt {{
    background-color: {header_bg};
    font-weight: bold;
}}
.two-column {{
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    align-items: flex-start;
}}
.two-column > div {{
    flex: 0 1 auto;
}}
.beschreibung {{
    font-style: normal;
    font-size: 9pt;
}}
@media print {{
    body {{
        background-color: #fff;
    }}
    th {{
        background-color: {header_bg if not printer_friendly else '#fff'};
    }}
    td {{
        background-color: {row_bg if not printer_friendly else '#fff'};
    }}
    td.gesamt {{
        background-color: {header_bg if not printer_friendly else '#fff'};
    }}
}}
@media (max-width: 600px) {{
    .two-column {{
        flex-direction: column;
    }}
    table {{
        width: 100%;
    }}
}}
</style>
</head>
<body>
<h1>Charakterbogen:</h1>
{body_content}
</body>
</html>"""


def _profil_sektion(daten: dict) -> str:
    rows = ""
    for key, value in daten.get("profil_daten", {}).items():
        rows += f"<tr><td><b>{_esc(key)}</b></td><td>{_esc(value)}</td></tr>\n"
    return "<h2>Profil</h2>\n" + _tabelle(["Attribut", "Beschreibung"], rows)


def _attribute_fertigkeiten_sektion(daten: dict, setting: dict, werte: dict) -> str:
    attribute = daten.get("attribute", {})
    reihenfolge = [n for n in ATTRIBUT_REIHENFOLGE if n in attribute] + [
        n for n in attribute if n not in ATTRIBUT_REIHENFOLGE
    ]
    attr_rows = ""
    for name in reihenfolge:
        attr = attribute[name]
        kombi = _wuerfel(attr.get("wert", 4), attr.get("modifier", 0))
        attr_rows += f"<tr><td>{_esc(name)}</td><td>{_esc(kombi)}</td></tr>\n"

    left_html = "<h2>Attribute</h2>\n" + _tabelle(["Attribut", "Wert"], attr_rows)

    fert_rows = ""
    for name, fert in sorted(daten.get("fertigkeiten", {}).items()):
        wuerfel = fert.get("wuerfel", {})
        if wuerfel.get("modifier", 0) == -2:  # ungelernt
            continue
        kombi = _wuerfel(wuerfel.get("value", 4), wuerfel.get("modifier", 0))
        fert_rows += f"<tr><td>{_esc(name)}</td><td>{_esc(kombi)}</td></tr>\n"

    left_html += "\n<h2>Fertigkeiten</h2>\n" + _tabelle(["Fertigkeit", "Wert"], fert_rows)

    right_html = _volk_sektion(daten, setting) + _abgeleitete_werte_sektion(daten, werte)

    return f"""<div class="two-column">
<div>{left_html}</div>
<div>{right_html}</div>
</div>"""


def _volk_sektion(daten: dict, setting: dict) -> str:
    # Alt-Format aus der Kivy-App: {volk_name: bool} — nur truthy Einträge sind gewählt
    selected_volk = None
    volk_data = None
    for volk, eintrag in daten.get("voelker_selected", {}).items():
        if eintrag:
            selected_volk = volk
            volk_data = eintrag if isinstance(eintrag, dict) else None
            break

    if not selected_volk:
        return "<p>Keine Abstammung ausgewählt.</p>"

    if volk_data is None:
        volk_data = setting.get("voelker", {}).get(selected_volk)

    result = f"<h2>Abstammung: {_esc(selected_volk)}</h2>"
    if not volk_data:
        return result + "<p>Keine Daten für die ausgewählte Abstammung vorhanden.</p>"

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
        rows += f"<tr><td>{_esc(key)}</td><td>{_esc(value)}</td></tr>\n"

    cyber = werte.get("cyberware")
    if cyber:
        rows += (
            f"<tr><td>Cyberware Stress</td><td>{_esc(cyber.get('stress'))} / "
            f"{_esc(cyber.get('stresslimit'))} (Max: {_esc(cyber.get('stress_maximum'))})</td></tr>\n"
        )
        installationen = len(daten.get("cyberware_installationen", {}))
        if installationen:
            rows += f"<tr><td>Installationen</td><td>{_esc(installationen)}</td></tr>\n"

    return "<h2>Abgeleitete Werte</h2>\n" + _tabelle(["Beschreibung", "Wert"], rows)


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
    ):
        if optional:
            sections.append(optional)

    name = daten.get("profil_daten", {}).get("Name") or "Charakterbogen"
    return _erzeuge_html_dokument(_esc(name), "\n".join(sections), printer_friendly)
