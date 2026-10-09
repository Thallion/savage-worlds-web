"""Steigerungs-Journal nach der Erschaffung (Original: historie_view.py).

Das Kivy-Original führt in charakter.steigerungs_journal zwei Listen:
"entries" (Historie-Tab: {timestamp, type, rang, details}) und "cost_entries"
(Kauf-Journal der Erschaffung, das Kivy-Exporte und Archetypen mitbringen).
Der Original-Charakterbogen rendert daraus die Sektion "Steigerungen"
(Rang | Typ | Name | Kosten) und bevorzugt entries.

Die Web-App schreibt entries nur für Änderungen nach Abschluss der
Erschaffung. Senken/Abwählen erstattet dort den Aufstieg vollständig (Undo) —
deshalb wird der passende Eintrag entfernt statt ein Gegen-Eintrag geloggt.
Jeder Eintrag lässt sich auch einzeln (nicht nur der letzte) zurücknehmen;
dabei werden die Würfelangaben späterer Einträge desselben Elements und die
Ränge der Folgeeinträge nachgeführt. Mitgebrachte cost_entries bleiben
unangetastet.
"""

from datetime import datetime
from uuid import uuid4

from app.services.aufstiege import (
    ausgegebene_aufstiege,
    charakter_rang,
    rang_erlaubt,
    rang_fuer_aufstiege,
)
from app.services.talent_voraussetzungen import RANG_NAMEN, macht_kapazitaet, pruefe_voraussetzungen


def wuerfel_anzeige(wert: int, modifier: int = 0) -> str:
    """Würfelwert für die von/nach-Felder ("8", "12+1", ungelernt "4-2") —
    der Bogen setzt das W davor."""
    if modifier:
        return f"{wert}{modifier:+d}"
    return str(wert)


def journal_eintrag(daten: dict, entry_type: str, details: dict) -> None:
    """Loggt eine Steigerung; vor Abschluss der Erschaffung passiert nichts.
    Der Rang ist der nach der Buchung erreichte (wie im Original, das nach
    der Änderung den aktuellen Charakterrang festhält)."""
    if not daten.get("char_gen_completed"):
        return
    journal = daten.setdefault("steigerungs_journal", {})
    journal.setdefault("entries", []).append(
        {
            "id": uuid4().hex[:12],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": entry_type,
            "rang": charakter_rang(daten),
            "details": details,
        }
    )


def journal_eintrag_entfernen(
    daten: dict, entry_type: str, name: str, alle: bool = False
) -> None:
    """Nimmt den letzten Eintrag (alle=True: alle Einträge) des Typs für das
    Element zurück — Gegenstück zur Aufstiegs-Erstattung beim Senken/Abwählen."""
    entries = (daten.get("steigerungs_journal") or {}).get("entries") or []
    for i in range(len(entries) - 1, -1, -1):
        eintrag = entries[i]
        if eintrag.get("type") == entry_type and (eintrag.get("details") or {}).get("name") == name:
            del entries[i]
            if not alle:
                return


def journal_eintraege(daten: dict) -> list[dict]:
    return (daten.get("steigerungs_journal") or {}).get("entries") or []


def finde_eintrag(daten: dict, ref: str | None) -> int | None:
    """Index eines Eintrags per ID; Alt-Einträge ohne ID per "#<index>"."""
    entries = journal_eintraege(daten)
    if not ref:
        return None
    if ref.startswith("#") and ref[1:].isdigit():
        index = int(ref[1:])
        if index < len(entries) and not entries[index].get("id"):
            return index
        return None
    return next((i for i, e in enumerate(entries) if e.get("id") == ref), None)


def letzter_eintrag_index(daten: dict, entry_type: str, name: str) -> int | None:
    entries = journal_eintraege(daten)
    for i in range(len(entries) - 1, -1, -1):
        eintrag = entries[i]
        if eintrag.get("type") == entry_type and (eintrag.get("details") or {}).get("name") == name:
            return i
    return None


def eintrag_aufstiegskosten(eintrag: dict) -> float:
    details = eintrag.get("details") or {}
    if details.get("kosten_typ") != "Aufstieg":
        return 0
    try:
        return float(details.get("kosten") or 0)
    except (TypeError, ValueError):
        return 0


def _wuerfel_eine_stufe_tiefer(anzeige: str | int) -> str:
    """"10" → "8", "12+1" → "12", "4" → "4-2" (Anzeigeformat der von/nach-Felder)."""
    text = str(anzeige)
    for zeichen in ("+", "-"):
        if zeichen in text[1:]:
            wert, modifier = text.split(zeichen, 1)
            wert, modifier = int(wert), int(modifier) * (1 if zeichen == "+" else -1)
            break
    else:
        wert, modifier = int(text), 0
    if wert == 12 and modifier > 0:
        modifier -= 1
    elif wert > 4:
        wert -= 2
    elif modifier == 0:
        modifier = -2
    return wuerfel_anzeige(wert, modifier)


def entferne_journal_eintrag(entries: list[dict], index: int) -> list[dict]:
    """Neue Liste ohne den Eintrag. Spätere Steigerungen desselben Attributs
    bzw. derselben Fertigkeit beginnen eine Stufe tiefer."""
    entfernt = entries[index]
    neu = entries[:index] + entries[index + 1:]
    if entfernt.get("type") not in ("attribut_steigerung", "fertigkeit_steigerung"):
        return neu
    name = (entfernt.get("details") or {}).get("name")
    for eintrag in neu[index:]:
        details = eintrag.get("details") or {}
        if eintrag.get("type") != entfernt.get("type") or details.get("name") != name:
            continue
        try:
            details["von"] = _wuerfel_eine_stufe_tiefer(details["von"])
            details["nach"] = _wuerfel_eine_stufe_tiefer(details["nach"])
        except (KeyError, ValueError):
            pass
    return neu


def aktualisiere_raenge(daten: dict, ab_index: int) -> None:
    """Rang der Einträge ab ab_index neu aus der laufenden Summe der
    Aufstiegskosten ableiten. Vor dem Journal ausgegebene Aufstiege (Importe)
    stecken im Sockel."""
    entries = journal_eintraege(daten)
    sockel = ausgegebene_aufstiege(daten) - sum(eintrag_aufstiegskosten(e) for e in entries)
    summe = max(0, sockel)
    for i, eintrag in enumerate(entries):
        summe += eintrag_aufstiegskosten(eintrag)
        if i >= ab_index and eintrag.get("rang"):
            eintrag["rang"] = rang_fuer_aufstiege(summe)


def abhaengigkeits_konflikte(vorher: dict, nachher: dict, setting: dict) -> list[str]:
    """Was eine Rücknahme kaputtmacht: Talente, deren Voraussetzungen oder
    Rang vorher erfüllt waren und nachher nicht mehr, Mächte über dem Rang
    und Mächte ohne Slot. Schon vorher verletzte Prüfungen (per "Trotzdem
    auswählen" übergangen) zählen nicht."""
    talente = setting.get("talente", {})
    handicaps = setting.get("handicaps")
    maechte = setting.get("maechte", {})
    konflikte = []
    for name in dict.fromkeys(nachher.get("selected_talente", [])):
        talent = talente.get(name)
        if not talent:
            continue
        neu_fehlend = [
            v for v in pruefe_voraussetzungen(talent, nachher, talente, handicaps)
            if v not in pruefe_voraussetzungen(talent, vorher, talente, handicaps)
        ]
        if neu_fehlend:
            konflikte.append(f"{name} (braucht {', '.join(neu_fehlend)})")
        rang = talent.get("rang", "A")
        if rang_erlaubt(rang, vorher) and not rang_erlaubt(rang, nachher):
            konflikte.append(f"{name} (braucht Rang {RANG_NAMEN.get(rang, rang)})")
    for name in nachher.get("selected_maechte", []):
        rang = maechte.get(name, {}).get("rang", "A")
        if rang_erlaubt(rang, vorher) and not rang_erlaubt(rang, nachher):
            konflikte.append(f"{name} (braucht Rang {RANG_NAMEN.get(rang, rang)})")
    slots_vorher, _ = macht_kapazitaet(vorher, talente)
    slots_nachher, _ = macht_kapazitaet(nachher, talente)
    anzahl = len(nachher.get("selected_maechte", []))
    if anzahl > slots_nachher and anzahl <= slots_vorher:
        konflikte.append(f"Mächte ({anzahl} gewählt, nur noch {slots_nachher} Slots)")
    return konflikte
