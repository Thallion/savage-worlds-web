"""Steigerungs-Journal nach der Erschaffung (Original: historie_view.py).

Das Kivy-Original führt in charakter.steigerungs_journal zwei Listen:
"entries" (Historie-Tab: {timestamp, type, rang, details}) und "cost_entries"
(Kauf-Journal der Erschaffung, das Kivy-Exporte und Archetypen mitbringen).
Der Original-Charakterbogen rendert daraus die Sektion "Steigerungen"
(Rang | Typ | Name | Kosten) und bevorzugt entries.

Die Web-App schreibt entries nur für Änderungen nach Abschluss der
Erschaffung. Senken/Abwählen erstattet dort den Aufstieg vollständig (Undo) —
deshalb wird der letzte passende Eintrag entfernt statt ein Gegen-Eintrag
geloggt. Mitgebrachte cost_entries bleiben unangetastet.
"""

from datetime import datetime

from app.services.aufstiege import charakter_rang


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
