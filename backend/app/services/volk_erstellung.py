"""Erstellung eigener Völker/Abstammungen aus Volkseigenarten (Original:
volk_erstellen_popup + volkseigenarten_config.json).

Ein eigenes Volk wird aus Eigenarten nach dem Savage-Worlds-Punktesystem
zusammengesetzt: positive Eigenarten kosten Punkte, negative geben Punkte,
das Budget beträgt START_PUNKTE. Die gewählten Eigenarten (inkl. Stufe und
ggf. Auswahl wie Attribut, Fertigkeit, Talent oder Freitext) werden hier in
das strukturierte "effects"-Objekt kompiliert, das die Spiellogik
(volk_effekte.py, /spiellogik/berechne) bereits versteht. Die Roh-Auswahl
bleibt als volk["eigenarten"] erhalten, damit Bearbeiten sie wieder ins
Formular laden kann.

Eigenarten mit verzögerter Auswahl (freies Talent, freies Attribut,
Magieaffin) werden nicht hier aufgelöst, sondern als wahlmoeglichkeiten
kompiliert — der Spieler entscheidet dann pro Charakter nach der
Volkauswahl, wie bei den nativen Völkern.
"""

from app.services.charakter_init import load_config
from app.services.superkraefte import ist_superkraefte_setting

START_PUNKTE = 2

GRUNDFERTIGKEITEN = ("Allgemeinwissen", "Athletik", "Heimlichkeit", "Überreden", "Wahrnehmung")

# Options-Typen, bei denen dieselbe Auswahl nur einmal pro Eigenart erlaubt
# ist ("Einmal pro Fertigkeit" u. ä.)
_EINMALIGE_AUSWAHL_TYPEN = (
    "grundfertigkeit_auswahl",
    "nicht_grundfertigkeit_auswahl",
    "fertigkeit_auswahl",
    "talent_rang_auswahl",
    "handicap_auswahl",
    "macht_auswahl",
)


def lade_eigenarten_config() -> dict:
    return load_config("volkseigenarten_config.json")


def _definitionen(cfg: dict) -> dict:
    return {
        e["id"]: {**e, "negativ": negativ}
        for negativ, liste in ((False, cfg.get("positive") or []), (True, cfg.get("negative") or []))
        for e in liste
    }


def _leere_effects() -> dict:
    return {
        "attribute_bonuses": {},
        "attribut_modifikatoren": {},
        "fertigkeits_startboni": {},
        "fertigkeits_modifier_boni": {},
        "robustheit_bonus": 0,
        "groesse_modifikator": 0,
        "bewegungsweite_bonus": 0,
        "parade_bonus": 0,
        "panzerung_bonus": 0,
        "auto_talente": [],
        "auto_handicaps": [],
        "auto_maechte": [],
        "spezielle_effekte": {},
        "wahlmoeglichkeiten": {},
    }


def _ist_verzoegert(defn: dict, effekt: dict) -> bool:
    """Eigenarten, deren Auswahl erst nach der Volkauswahl pro Charakter fällt."""
    if defn.get("effekt_typ") == "wahlmoeglichkeit":
        return True
    return bool(effekt.get("attribut_wahl") or effekt.get("magieaffin"))


def _pruefe_auswahl(defn: dict, effekt: dict, auswahl: str, setting: dict, cfg: dict) -> str:
    """Validiert die Auswahl einer Eigenart; leerer String = ok."""
    optionen = defn.get("optionen") or {}
    typ = optionen.get("typ")
    if not typ or _ist_verzoegert(defn, effekt):
        return ""
    if not auswahl:
        return f"'{defn['name']}' braucht eine Auswahl ({optionen.get('beschreibung') or typ})"

    if typ == "attribut_auswahl":
        erlaubt = optionen.get("attribute") or cfg.get("attribute") or []
        if erlaubt and auswahl not in erlaubt:
            return f"'{auswahl}' ist kein gültiges Attribut für '{defn['name']}'"
    elif typ == "grundfertigkeit_auswahl":
        erlaubt = optionen.get("fertigkeiten") or list(GRUNDFERTIGKEITEN)
        if auswahl not in erlaubt:
            return f"'{auswahl}' ist keine gültige Fertigkeit für '{defn['name']}'"
    elif typ == "nicht_grundfertigkeit_auswahl":
        if auswahl in GRUNDFERTIGKEITEN:
            return f"'{auswahl}' ist eine Grundfertigkeit — '{defn['name']}' verlangt eine andere Fertigkeit"
    elif typ == "talent_rang_auswahl":
        if auswahl not in (setting.get("talente") or {}):
            return f"Talent '{auswahl}' nicht im Setting gefunden"
    elif typ == "handicap_auswahl":
        if auswahl not in (setting.get("handicaps") or {}):
            return f"Handicap '{auswahl}' nicht im Setting gefunden"
    elif typ == "macht_auswahl":
        if auswahl not in (setting.get("maechte") or {}):
            return f"Macht '{auswahl}' nicht im Setting gefunden"
    elif typ == "superkraft_auswahl":
        if not ist_superkraefte_setting(setting):
            return f"'{defn['name']}' ist nur in Superkräfte-Settings verfügbar"
    # fertigkeit_auswahl / text_eingabe: jeder nicht-leere Text ist erlaubt
    return ""


def _merge_spezialeffekt(spezielle: dict, key: str, wert) -> None:
    """Text-Werte derselben Eigenart (z. B. zwei Immunitäten) kommasepariert sammeln."""
    vorhanden = spezielle.get(key)
    if isinstance(vorhanden, str) and isinstance(wert, str) and vorhanden and wert not in vorhanden:
        spezielle[key] = f"{vorhanden}, {wert}"
    else:
        spezielle[key] = wert


def _kompiliere_effekt(effects: dict, defn: dict, effekt: dict, auswahl: str) -> None:
    typ = defn.get("effekt_typ", "spezieller_effekt")
    spezielle = effects["spezielle_effekte"]
    text_eingabe = (defn.get("optionen") or {}).get("typ") == "text_eingabe"

    if typ == "wahlmoeglichkeit":
        effects["wahlmoeglichkeiten"].update(effekt)
    elif typ == "attribut_bonus":
        if effekt.get("attribut_wahl"):
            effects["wahlmoeglichkeiten"]["freies_attribut"] = True
        else:
            boni = effects["attribute_bonuses"]
            boni[auswahl] = boni.get(auswahl, 0) + effekt.get("attribut_bonus", 0)
    elif typ == "attribut_malus":
        mods = effects["attribut_modifikatoren"]
        mods[auswahl] = mods.get(auswahl, 0) - effekt.get("attribut_malus", 0)
    elif typ in ("fertigkeits_bonus", "fertigkeits_malus"):
        startboni = effects["fertigkeits_startboni"]
        modifier = effects["fertigkeits_modifier_boni"]
        if "grundfertigkeit_bonus" in effekt or "nicht_grundfertigkeit_bonus" in effekt:
            bonus = effekt.get("grundfertigkeit_bonus") or effekt.get("nicht_grundfertigkeit_bonus") or 0
            startboni[auswahl] = startboni.get(auswahl, 0) + bonus
        elif "fertigkeit_w4_bonus" in effekt:
            # Startet die Fertigkeit auf W4 (Bonus 0 über dem Grundwürfel)
            startboni.setdefault(auswahl, 0)
        elif "fertigkeits_bonus" in effekt or "fertigkeits_malus" in effekt:
            wert = effekt.get("fertigkeits_bonus", effekt.get("fertigkeits_malus", 0))
            modifier[auswahl] = modifier.get(auswahl, 0) + wert
        else:  # z. B. geschaeftssinn: beschreibender Effekt
            for key, wert in effekt.items():
                _merge_spezialeffekt(spezielle, key, auswahl if wert is True and text_eingabe else wert)
    elif typ in ("robustheit_bonus", "robustheit_malus"):
        effects["robustheit_bonus"] += effekt.get("robustheit_bonus", 0)
    elif typ in ("bewegungsweite_bonus", "bewegungsweite_malus"):
        effects["bewegungsweite_bonus"] += effekt.get("bewegungsweite_bonus", 0)
        for key, wert in effekt.items():
            if key != "bewegungsweite_bonus":
                _merge_spezialeffekt(spezielle, key, wert)
    elif typ in ("parade_bonus", "parade_malus"):
        effects["parade_bonus"] += effekt.get("parade_bonus", 0)
    elif typ == "panzerung_bonus":
        effects["panzerung_bonus"] += effekt.get("panzerung_bonus", 0)
    elif typ == "reichweite_bonus":
        spezielle["reichweite_bonus"] = spezielle.get("reichweite_bonus", 0) + effekt.get("reichweite_bonus", 0)
    elif typ == "handicap_volk":
        effects["auto_handicaps"].append(auswahl)
    elif typ == "talent_volk":
        effects["auto_talente"].append(auswahl)
    elif typ == "macht_volk":
        effects["auto_maechte"].append(auswahl)
    elif typ == "superkraft_volk":
        _merge_spezialeffekt(spezielle, "superkraft", auswahl)
    else:  # spezieller_effekt, kombinierter_effekt, natuerliche_waffe, ...
        for key, wert in effekt.items():
            if key == "groesse_punkt":
                effects["groesse_modifikator"] += wert
            elif key == "robustheit_bonus":
                effects["robustheit_bonus"] += wert
            elif key == "bewegungsweite_bonus":
                effects["bewegungsweite_bonus"] += wert
            elif key == "magieaffin":
                effects["wahlmoeglichkeiten"]["magieaffin"] = True
            elif key == "wahrnehmung_w6":
                startboni = effects["fertigkeits_startboni"]
                startboni["Wahrnehmung"] = max(startboni.get("Wahrnehmung", 0), 2)
                spezielle[key] = wert
            elif key == "wahrnehmung_w8":
                startboni = effects["fertigkeits_startboni"]
                startboni["Wahrnehmung"] = max(startboni.get("Wahrnehmung", 0), 4)
                spezielle[key] = wert
            elif key == "natuerlicher_kaempfer":
                startboni = effects["fertigkeits_startboni"]
                startboni["Kämpfen"] = max(startboni.get("Kämpfen", 0), 2)
                spezielle[key] = wert
            else:
                _merge_spezialeffekt(spezielle, key, auswahl if wert is True and text_eingabe else wert)


def _beschriftung(defn: dict, stufe_label: str | None, auswahl: str) -> str:
    details = [d for d in (stufe_label, auswahl or None) if d]
    if details:
        return f"{defn['name']} ({', '.join(details)})"
    return defn["name"]


def baue_volk(name: str, volk_daten: dict, setting: dict) -> tuple[dict | None, str]:
    """Kompiliert Name + Eigenarten-Auswahl zu einem Volk-Dict (oder Fehler).

    volk_daten: {"beschreibung": str, "eigenarten": [{"id", "stufe"?, "auswahl"?}]}
    """
    cfg = lade_eigenarten_config()
    defs = _definitionen(cfg)
    eintraege = volk_daten.get("eigenarten") or []
    if not isinstance(eintraege, list):
        return None, "eigenarten muss eine Liste sein"

    effects = _leere_effects()
    besonderheiten: list[str] = []
    handicaps_text: list[str] = []
    talente_text: list[str] = []
    normalisiert: list[dict] = []
    punkte = 0
    anzahl_je_id: dict[str, int] = {}
    belegte_auswahl: set[tuple[str, str]] = set()

    for eintrag in eintraege:
        if not isinstance(eintrag, dict):
            return None, "Jede Eigenart braucht die Form {id, stufe?, auswahl?}"
        eid = eintrag.get("id") or ""
        defn = defs.get(eid)
        if not defn:
            return None, f"Unbekannte Volkseigenart '{eid}'"
        if defn.get("voraussetzung") == "setting_hat_superkraefte" and not ist_superkraefte_setting(setting):
            return None, f"'{defn['name']}' ist nur in Superkräfte-Settings verfügbar"

        stufen = defn.get("stufen")
        stufe_label = None
        if stufen:
            stufe = eintrag.get("stufe")
            if not isinstance(stufe, int) or not 0 <= stufe < len(stufen):
                return None, f"'{defn['name']}' braucht eine gültige Stufe"
            kosten = stufen[stufe].get("kosten", 0)
            effekt = stufen[stufe].get("effekt") or {}
            stufe_label = stufen[stufe].get("label")
        else:
            kosten = defn.get("kosten", 0)
            effekt = defn.get("effekt") or {}

        auswahl = str(eintrag.get("auswahl") or "").strip()
        fehler = _pruefe_auswahl(defn, effekt, auswahl, setting, cfg)
        if fehler:
            return None, fehler

        anzahl_je_id[eid] = anzahl_je_id.get(eid, 0) + 1
        max_auswahl = defn.get("max_auswahl", 0)
        if max_auswahl and anzahl_je_id[eid] > max_auswahl:
            return None, f"'{defn['name']}' ist höchstens {max_auswahl}x wählbar"
        if (defn.get("optionen") or {}).get("typ") in _EINMALIGE_AUSWAHL_TYPEN and auswahl:
            if (eid, auswahl) in belegte_auswahl:
                return None, f"'{defn['name']}' wurde bereits für '{auswahl}' gewählt"
            belegte_auswahl.add((eid, auswahl))

        punkte += kosten
        _kompiliere_effekt(effects, defn, effekt, auswahl)
        for talent in defn.get("auto_talente") or []:
            if talent in (setting.get("talente") or {}) and talent not in effects["auto_talente"]:
                effects["auto_talente"].append(talent)

        label = _beschriftung(defn, stufe_label, auswahl)
        besonderheiten.append(label)
        if defn.get("effekt_typ") == "handicap_volk":
            handicaps_text.append(label)
        elif defn.get("effekt_typ") == "talent_volk":
            talente_text.append(auswahl)

        normal = {"id": eid}
        if stufen:
            normal["stufe"] = eintrag.get("stufe")
        if auswahl:
            normal["auswahl"] = auswahl
        normalisiert.append(normal)

    if punkte > START_PUNKTE:
        return None, (
            f"Punktelimit überschritten: {punkte} von {START_PUNKTE} Punkten ausgegeben — "
            "negative Eigenarten geben Punkte zurück"
        )

    volk = {
        "name": name,
        "custom": True,
        "aktiv": True,
        "ausgewaehlt": False,
        "beschreibung": str(volk_daten.get("beschreibung") or ""),
        "besonderheiten": besonderheiten,
        "handicaps": handicaps_text,
        "talente": talente_text,
        "eigenarten": normalisiert,
        "eigenarten_punkte": punkte,
        "effects": effects,
    }
    return volk, ""
