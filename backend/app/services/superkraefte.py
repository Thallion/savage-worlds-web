"""Superkräfte (Original: superkraft_funktionen.py, Superkräfte-Kompendium).

- Die Kampagnen-Machtstufe (setting["machtstufen"], I–V) bestimmt das
  Superkraftpunkte-Budget (SKP) und die Kraftobergrenze (max. SKP pro Kraft,
  normal 1/3 des Budgets; mit dem Talent "Der Beste" 1/2).
- Voraussetzung ist das Talent "Superkräfte" (im Kompendium normalerweise
  kostenlos, hier ein regulärer Talent-Slot/Kauf).
- Kräfte (setting["krafte"]) haben heterogene Kosten-Angaben ("2", "1-5",
  "1/Stufe", "speziell", ...). Der Spieler investiert daher frei wählbare
  Punkte pro Kraft (Standard: der erste parsebare Zahlenwert); Modifikatoren
  (kraftspezifisch oder generisch aus setting["kraft_modifikatoren"]) addieren
  ihre Kosten, negative Modifikatoren senken sie.
- Validiert werden Kraftobergrenze (Gesamtkosten pro Kraft) und SKP-Budget.

Auswahl liegt in daten["selected_superkraefte"] =
{name: {"punkte": int, "modifikatoren": {mod_name: kosten}}},
die Stufe in daten["superkraft_stufe"] (Standard "I").
"""

import re

TALENT_NAME = "Superkräfte"
DER_BESTE_TALENT = "Der Beste"
STANDARD_STUFE = "I"

_ZAHL_RE = re.compile(r"-?\d+")


def ist_superkraefte_setting(setting: dict) -> bool:
    return bool(setting.get("machtstufen")) and bool(setting.get("krafte"))


def hat_superkraefte_talent(daten: dict) -> bool:
    return TALENT_NAME in daten.get("selected_talente", [])


def basis_kosten(kosten) -> int:
    """Erster Zahlenwert einer Kosten-Angabe ("2", "1-5", "2/Stufe", "speziell")."""
    if isinstance(kosten, (int, float)):
        return max(1, int(kosten))
    m = _ZAHL_RE.search(str(kosten or ""))
    return max(1, int(m.group())) if m else 1


def _stufen_daten(daten: dict, setting: dict) -> dict:
    stufen = setting.get("machtstufen", {})
    stufe = daten.get("superkraft_stufe", STANDARD_STUFE)
    return stufen.get(stufe) or stufen.get(STANDARD_STUFE) or {}

def skp_budget(daten: dict, setting: dict) -> int:
    return _stufen_daten(daten, setting).get("superkraftpunkte", 0)


def kraftobergrenze(daten: dict, setting: dict) -> int:
    stufe = _stufen_daten(daten, setting)
    if DER_BESTE_TALENT in daten.get("selected_talente", []):
        return stufe.get("superkraftpunkte", 0) // 2
    return stufe.get("kraftobergrenze", 0)


def kraft_kosten(eintrag: dict) -> int:
    return eintrag.get("punkte", 0) + sum((eintrag.get("modifikatoren") or {}).values())


def skp_ausgegeben(daten: dict) -> int:
    return sum(kraft_kosten(e) for e in daten.get("selected_superkraefte", {}).values())


def _pruefe_grundlagen(daten: dict, setting: dict) -> str | None:
    if not ist_superkraefte_setting(setting):
        return "Dieses Setting nutzt kein Superkräfte-System"
    if not hat_superkraefte_talent(daten):
        return f"Zuerst das Talent '{TALENT_NAME}' wählen"
    return None


def _pruefe_grenzen(daten: dict, setting: dict, kraft_name: str) -> str | None:
    """Prüft Kraftobergrenze und Budget für den aktuellen Stand der Auswahl."""
    eintrag = daten.get("selected_superkraefte", {}).get(kraft_name)
    if eintrag:
        grenze = kraftobergrenze(daten, setting)
        gesamt = kraft_kosten(eintrag)
        if gesamt > grenze:
            return f"Kraftobergrenze überschritten ({gesamt} > {grenze} SKP für '{kraft_name}')"
        if gesamt < 1:
            return f"'{kraft_name}' muss mindestens 1 SKP kosten"
    budget = skp_budget(daten, setting)
    ausgegeben = skp_ausgegeben(daten)
    if ausgegeben > budget:
        return f"Nicht genug Superkraftpunkte ({ausgegeben} > {budget})"
    return None


def setze_machtstufe(daten: dict, setting: dict, stufe: str) -> tuple[bool, str]:
    if not ist_superkraefte_setting(setting):
        return False, "Dieses Setting nutzt kein Superkräfte-System"
    if stufe not in setting.get("machtstufen", {}):
        gueltig = ", ".join(setting.get("machtstufen", {}))
        return False, f"Unbekannte Machtstufe '{stufe}' (gültig: {gueltig})"

    vorher = daten.get("superkraft_stufe", STANDARD_STUFE)
    daten["superkraft_stufe"] = stufe
    # Absenken darf keine bereits gekauften Kräfte ungültig machen
    for kraft_name in daten.get("selected_superkraefte", {}):
        fehler = _pruefe_grenzen(daten, setting, kraft_name)
        if fehler:
            daten["superkraft_stufe"] = vorher
            return False, f"Stufe nicht änderbar: {fehler} — zuerst Kräfte reduzieren"
    return True, ""


def waehle_kraft(daten: dict, setting: dict, kraft_name: str, punkte: int | None = None) -> tuple[bool, str]:
    fehler = _pruefe_grundlagen(daten, setting)
    if fehler:
        return False, fehler

    kraft = setting.get("krafte", {}).get(kraft_name)
    if not kraft:
        return False, f"Superkraft '{kraft_name}' nicht gefunden"

    auswahl = daten.setdefault("selected_superkraefte", {})
    if kraft_name in auswahl:
        return False, f"'{kraft_name}' ist bereits gewählt"

    auswahl[kraft_name] = {
        "punkte": punkte if punkte is not None else basis_kosten(kraft.get("kosten")),
        "modifikatoren": {},
    }
    fehler = _pruefe_grenzen(daten, setting, kraft_name)
    if fehler:
        del auswahl[kraft_name]
        return False, fehler
    return True, ""


def entferne_kraft(daten: dict, kraft_name: str) -> tuple[bool, str]:
    auswahl = daten.get("selected_superkraefte", {})
    if kraft_name not in auswahl:
        return False, f"'{kraft_name}' ist nicht gewählt"
    del auswahl[kraft_name]
    return True, ""


def setze_punkte(daten: dict, setting: dict, kraft_name: str, punkte: int) -> tuple[bool, str]:
    eintrag = daten.get("selected_superkraefte", {}).get(kraft_name)
    if not eintrag:
        return False, f"'{kraft_name}' ist nicht gewählt"

    vorher = eintrag["punkte"]
    eintrag["punkte"] = punkte
    fehler = _pruefe_grenzen(daten, setting, kraft_name)
    if fehler:
        eintrag["punkte"] = vorher
        return False, fehler
    return True, ""


def toggle_modifikator(daten: dict, setting: dict, kraft_name: str, mod_name: str) -> tuple[bool, str]:
    eintrag = daten.get("selected_superkraefte", {}).get(kraft_name)
    if not eintrag:
        return False, f"'{kraft_name}' ist nicht gewählt"

    mods = eintrag.setdefault("modifikatoren", {})
    if mod_name in mods:
        del mods[mod_name]
        return True, ""

    kraft = setting.get("krafte", {}).get(kraft_name, {})
    mod = (kraft.get("modifikatoren") or {}).get(mod_name) or (
        setting.get("kraft_modifikatoren") or {}
    ).get(mod_name)
    if not mod:
        return False, f"Modifikator '{mod_name}' nicht gefunden"

    kosten = mod.get("kosten", 0)
    if isinstance(kosten, (int, float)):
        mods[mod_name] = int(kosten)
    else:
        # Modifikator-Kosten können negativ sein ("-1"), daher signiert parsen
        m = _ZAHL_RE.search(str(kosten))
        mods[mod_name] = int(m.group()) if m else 0
    fehler = _pruefe_grenzen(daten, setting, kraft_name)
    if fehler:
        del mods[mod_name]
        return False, fehler
    return True, ""
