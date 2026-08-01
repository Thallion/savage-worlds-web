"""Statblock-Export (Original: statblock_generator.py).

Erzeugt einen kompakten Text-Statblock im SWADE-Stil:

    Name
    Abstammung: Zwerg (SWAE)
    Attribute: Geschicklichkeit W6, Verstand W4, ...
    Fertigkeiten: Athletik W4, Kämpfen W6, ...
    Bewegungsweite: 5; Parade: 5; Robustheit: 7 (1); Größe: +0
    Handicaps: ...  / Talente: ...  / Mächte: ... (10 Machtpunkte)
    Abstammungs-Handicaps: Blutrünstig (...), Nichtschwimmer (...)
    Besonderheiten: Klauen (Stä+W4 Schaden, PB 2, +2 Athletik Klettern), ...
    Superkräfte: Fliegen [4 SKP, Senkrechtstarter] (Machtstufe I, 4/15 SKP)
    Cyberware: Scanner (Stress 1/2)
    Ausrüstung: Fackel (2x), ... — Geld: 475

Abweichung vom Original: Fertigkeiten listen alle gelernten Werte (auch W4),
nicht nur die über W4 — Grundfertigkeiten wären sonst unsichtbar. Ebenfalls
ergänzt sind die Abstammungs-Zeilen: Volks-Handicaps und -Besonderheiten stehen
nicht in selected_handicaps/selected_talente und fehlten sonst im Export.
"""

from app.services.volk_effekte import gewaehltes_volk

# Anzeige-Reihenfolge nach SWADE-Statblock (Agility, Smarts, Spirit, Strength, Vigor)
ATTRIBUT_REIHENFOLGE = ["Geschicklichkeit", "Verstand", "Willenskraft", "Stärke", "Konstitution"]

MAX_AUSRUESTUNG_EINTRAEGE = 8


def _wuerfel(wert: int, modifier: int = 0) -> str:
    if modifier:
        return f"W{wert}{modifier:+d}"
    return f"W{wert}"


def _attribute(daten: dict) -> str:
    attribute = daten.get("attribute", {})
    reihenfolge = [n for n in ATTRIBUT_REIHENFOLGE if n in attribute] + [
        n for n in attribute if n not in ATTRIBUT_REIHENFOLGE
    ]
    return ", ".join(
        f"{name} {_wuerfel(attribute[name].get('wert', 4), attribute[name].get('modifier', 0))}"
        for name in reihenfolge
    )


def _fertigkeiten(daten: dict) -> str:
    gelernt = []
    for name, fert in sorted(daten.get("fertigkeiten", {}).items()):
        wuerfel = fert.get("wuerfel", {})
        if wuerfel.get("modifier", 0) == -2:  # ungelernt
            continue
        gelernt.append(f"{name} {_wuerfel(wuerfel.get('value', 4), wuerfel.get('modifier', 0))}")
    return ", ".join(gelernt)


def _handicaps(daten: dict, setting: dict) -> str:
    setting_handicaps = setting.get("handicaps", {})
    teile = []
    for name in daten.get("selected_handicaps", []):
        stufe = setting_handicaps.get(name, {}).get("stufe")
        if name.endswith(("_leicht", "_schwer")):
            name, stufe = name[:-7], name[-6:]
        teile.append(f"{name} ({stufe})" if stufe else name)
    return ", ".join(teile)


def _basisname(eintrag: str) -> str:
    """Vergleichsname ohne Stufen-Suffix und erklärenden Klammerzusatz —
    "Schwur_schwer" und "Schwur (schwer: ...)" sind dasselbe Handicap."""
    if eintrag.endswith(("_leicht", "_schwer")):
        eintrag = eintrag[:-7]
    return eintrag.split(" (", 1)[0].strip()


def _volk_zeilen(daten: dict, setting: dict) -> list[tuple[str, str]]:
    """Talente, Handicaps und Besonderheiten der Abstammung.

    Sie stehen nur am Volk und fehlten deshalb im Statblock. Einträge, die als
    Auto-Talent/-Handicap ohnehin schon in den Zeilen darüber stehen, werden
    nicht doppelt gelistet.
    """
    _, volk_data = gewaehltes_volk(daten, setting)
    if not volk_data:
        return []

    zeilen = []
    for feld, label, gewaehlt in (
        ("talente", "Abstammungs-Talente", daten.get("selected_talente", [])),
        ("handicaps", "Abstammungs-Handicaps", daten.get("selected_handicaps", [])),
        ("besonderheiten", "Besonderheiten", []),
    ):
        bekannt = {_basisname(e) for e in gewaehlt}
        eintraege = [e for e in volk_data.get(feld) or [] if _basisname(e) not in bekannt]
        zeilen.append((label, ", ".join(eintraege)))
    return zeilen


def _maechte(daten: dict, werte: dict) -> str:
    maechte = ", ".join(daten.get("selected_maechte", []))
    if maechte and werte.get("machtpunkte"):
        maechte += f" ({werte['machtpunkte']} Machtpunkte)"
    return maechte


def _superkraefte(daten: dict, werte: dict) -> str:
    auswahl = daten.get("selected_superkraefte", {})
    skp = werte.get("superkraefte")
    if not auswahl or not skp:
        return ""
    teile = []
    for name, eintrag in sorted(auswahl.items()):
        gesamt = eintrag.get("punkte", 0) + sum((eintrag.get("modifikatoren") or {}).values())
        mods = ", ".join(sorted(eintrag.get("modifikatoren") or {}))
        teile.append(f"{name} [{gesamt} SKP{', ' + mods if mods else ''}]")
    return (
        ", ".join(teile)
        + f" (Machtstufe {skp.get('stufe')}, {skp.get('ausgegeben')}/{skp.get('budget')} SKP)"
    )


def _cyberware(daten: dict, werte: dict) -> str:
    installationen = daten.get("cyberware_installationen", {})
    cyber = werte.get("cyberware")
    if not installationen or not cyber:
        return ""
    inaktiv = daten.get("cyberware_inaktiv", [])
    teile = []
    for name, anzahl in sorted(installationen.items()):
        kurz = name.removeprefix("Cyberware: ")
        if anzahl > 1:
            kurz = f"{kurz} ({anzahl}x)"
        if name in inaktiv:
            kurz = f"{kurz} [inaktiv]"
        teile.append(kurz)
    return ", ".join(teile) + f" (Stress {cyber.get('stress')}/{cyber.get('stresslimit')})"


def _ausruestung(daten: dict, werte: dict) -> str:
    teile = []
    for name, eintrag in sorted(daten.get("ausruestung_selected", {}).items()):
        anzahl = eintrag.get("anzahl", 0)
        if anzahl <= 0:
            continue
        text = f"{name} ({anzahl}x)" if anzahl > 1 else name
        if eintrag.get("angelegt"):
            text += " [angelegt]"
        teile.append(text)
    if len(teile) > MAX_AUSRUESTUNG_EINTRAEGE:
        teile = teile[:MAX_AUSRUESTUNG_EINTRAEGE] + ["..."]
    text = ", ".join(teile)
    if text:
        geld = werte.get("vermoegen")
        if geld is not None:
            text += f" — Geld: {geld:g}"
    return text


def generiere_statblock(daten: dict, setting: dict, werte: dict) -> str:
    """werte: das Ergebnis von /spiellogik/berechne für dieselben daten."""
    name = daten.get("profil_daten", {}).get("Name") or "Unbenannter Charakter"
    zeilen = [name]

    # Alt-Format aus der Kivy-App: {volk_name: bool} — nur truthy Einträge sind gewählt
    volk = ", ".join(k for k, v in daten.get("voelker_selected", {}).items() if v)
    setting_name = daten.get("active_setting_name", "")
    if volk:
        zeilen.append(f"Abstammung: {volk} ({setting_name})" if setting_name else f"Abstammung: {volk}")
    elif setting_name:
        zeilen.append(f"Setting: {setting_name}")

    zeilen.append(f"Attribute: {_attribute(daten)}")
    fertigkeiten = _fertigkeiten(daten)
    if fertigkeiten:
        zeilen.append(f"Fertigkeiten: {fertigkeiten}")

    robustheit = str(werte.get("robustheit", 4))
    if werte.get("panzerung"):
        robustheit += f" ({werte['panzerung']})"
    zeilen.append(
        f"Bewegungsweite: {werte.get('bewegungsweite', 6)}; "
        f"Parade: {werte.get('parade', 2)}; "
        f"Robustheit: {robustheit}; "
        f"Größe: {werte.get('groesse', 0):+d}"
    )

    for label, text in (
        ("Handicaps", _handicaps(daten, setting)),
        ("Talente", ", ".join(daten.get("selected_talente", []))),
        *_volk_zeilen(daten, setting),
        ("Mächte", _maechte(daten, werte)),
        ("Superkräfte", _superkraefte(daten, werte)),
        ("Cyberware", _cyberware(daten, werte)),
        ("Ausrüstung", _ausruestung(daten, werte)),
    ):
        if text:
            zeilen.append(f"{label}: {text}")

    aufstiege = daten.get("aufstiege_gesamt", 0)
    if daten.get("char_gen_completed") and werte.get("rang"):
        zeilen.append(f"Aufstiege: {aufstiege} ({werte['rang']})")

    return "\n".join(zeilen)
