"""Ausprägungen von Mächten (Savage Aventurien: DSA-Zauber und -Liturgien).

Eine Macht kann im Setting eine Liste möglicher Ausprägungen tragen:

    "auspraegungen": [{"name": "Ignifaxius", "beschreibung": "..."}, ...]

Welche davon ein Charakter beherrscht, steht in

    charakter_daten["macht_auspraegungen"] = {"Strahl": ["Ignifaxius"], ...}

Charakterbogen und Statblock zeigen nur die gewählten Ausprägungen.
"""

from __future__ import annotations


def verfuegbare_auspraegungen(macht: dict) -> list[dict]:
    return [a for a in (macht.get("auspraegungen") or []) if isinstance(a, dict) and a.get("name")]


def gewaehlte_auspraegungen(daten: dict, macht_name: str) -> list[str]:
    return list((daten.get("macht_auspraegungen") or {}).get(macht_name) or [])


def setze_auspraegungen(daten: dict, macht: dict, macht_name: str, auswahl: list[str]) -> list[str]:
    """Übernimmt die Auswahl (Reihenfolge wie im Setting, Unbekanntes verworfen)."""
    namen = [a["name"] for a in verfuegbare_auspraegungen(macht)]
    gewaehlt = [n for n in namen if n in set(auswahl)]
    alle = daten.setdefault("macht_auspraegungen", {})
    if gewaehlt:
        alle[macht_name] = gewaehlt
    else:
        alle.pop(macht_name, None)
    return gewaehlt


def entferne_auspraegungen(daten: dict, macht_name: str) -> None:
    (daten.get("macht_auspraegungen") or {}).pop(macht_name, None)


def macht_anzeigename(daten: dict, macht_name: str) -> str:
    """'Strahl (Ignifaxius, Frigifaxius)' bzw. nur der Name ohne Auswahl."""
    gewaehlt = gewaehlte_auspraegungen(daten, macht_name)
    return f"{macht_name} ({', '.join(gewaehlt)})" if gewaehlt else macht_name


def macht_beschreibung(daten: dict, macht_name: str, macht: dict) -> str:
    """Regeltext der Macht plus Text der gewählten Ausprägungen."""
    teile = [macht.get("beschreibung") or ""]
    gewaehlt = set(gewaehlte_auspraegungen(daten, macht_name))
    zeilen = [
        f"{a['name']}: {a['beschreibung']}" if a.get("beschreibung") else a["name"]
        for a in verfuegbare_auspraegungen(macht)
        if a["name"] in gewaehlt
    ]
    if zeilen:
        teile.append("\n".join(zeilen))
    return "\n\n".join(t for t in teile if t)
