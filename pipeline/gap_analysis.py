"""
Gap-Analyse — amtliches Plenarprotokoll (Goldstandard) ↔ ASR-Transkript aus dem
öffentlichen Video. Quantifiziert, wo eine automatische Lösung heute Lücken hat.

Metriken:
  • WER (Word Error Rate) inkl. Substitutionen/Einfügungen/Löschungen
  • Reaktions-Recall: Anteil der amtlichen <kommentar> (Beifall/Zuruf/…),
    die ein reines ASR NICHT erfasst (ohne Sound-Event-Detection = 0 %)
  • Sprecher-Abdeckung: Sprecher im Protokoll vs. in der Diarisierung
  • Inhalts-Lücken: Protokollsätze, die im ASR fehlen (Auslassungen/Korrekturen)

Der Selbsttest erzeugt aus dem amtlichen XML ein realistisch verrauschtes
„ASR"-Transkript (ohne Saalreaktionen, mit Zahlendreher und Auslassung) und
zeigt den Report — so ist die Methodik ohne echtes Video reproduzierbar.
"""

from __future__ import annotations

import re


def _norm(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def wer(ref: list[str], hyp: list[str]) -> dict:
    """Word Error Rate per Levenshtein-DP über Wortlisten."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    # Backtrace für S/I/D
    i, j, sub, ins, dele = n, m, 0, 0, 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1):
            sub += 0 if ref[i - 1] == hyp[j - 1] else 1
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            dele += 1; i -= 1
        else:
            ins += 1; j -= 1
    return {"wer": round(d[n][m] / max(n, 1), 3), "subst": sub, "ins": ins,
            "del": dele, "ref_woerter": n}


def analyze_gaps(protocol, asr_text: str, asr_speakers: set[str] | None = None,
                 sed_erkannt: int = 0) -> dict:
    ref_text = " ".join(u.text for u in protocol.utterances if u.text)
    w = wer(_norm(ref_text), _norm(asr_text))

    reaktionen = len(protocol.kommentare)
    reaktions_recall = round((sed_erkannt / reaktionen), 3) if reaktionen else 1.0

    prot_speakers = {u.speaker_name for u in protocol.utterances if u.text}
    asr_speakers = asr_speakers or set()
    sprecher_fehlend = sorted(prot_speakers - asr_speakers) if asr_speakers else sorted(prot_speakers)

    # Inhalts-Lücken: Protokollsätze, deren Wörter im ASR kaum vorkommen
    asr_words = set(_norm(asr_text))
    luecken = []
    for u in protocol.utterances:
        for sent in re.split(r"(?<=[.!?])\s+", u.text):
            toks = _norm(sent)
            if len(toks) >= 4:
                overlap = sum(1 for t in toks if t in asr_words) / len(toks)
                if overlap < 0.6:
                    luecken.append({"sprecher": u.speaker_name, "satz": sent.strip()[:140],
                                    "abdeckung": round(overlap, 2)})

    return {
        "wer": w,
        "reaktionen": {"amtlich": reaktionen, "asr_erkannt": sed_erkannt,
                       "recall": reaktions_recall,
                       "hinweis": "Reines ASR erfasst Saalreaktionen nicht — Sound-Event-Detection nötig."},
        "sprecher": {"im_protokoll": sorted(prot_speakers), "fehlend_in_asr": sprecher_fehlend},
        "inhalts_luecken": luecken,
        "bewertung": _bewertung(w["wer"], reaktions_recall, luecken),
    }


def _bewertung(wer_val: float, recall: float, luecken: list) -> list[str]:
    out = []
    out.append(f"WER {wer_val:.1%} — " + ("gut" if wer_val < 0.1 else
               "akzeptabel" if wer_val < 0.2 else "zu hoch (Nachbearbeitung nötig)"))
    out.append(f"Saalreaktionen-Recall {recall:.0%} — " +
               ("ok" if recall > 0.7 else "Lücke: Sound-Event-Detection ergänzen"))
    if luecken:
        out.append(f"{len(luecken)} Inhalts-Lücke(n) — fehlende/abweichende Passagen prüfen")
    return out


# ── Selbsttest: simuliertes ASR aus dem amtlichen XML ───────────────────────────

def simulate_asr(protocol) -> tuple[str, set[str]]:
    """Erzeugt ein realistisch verrauschtes ASR: ohne Saalreaktionen, mit
    Zahlendreher und einer Auslassung (wie sie ein ASR ohne Korrektur erzeugt)."""
    parts = []
    for k, u in enumerate(x for x in protocol.utterances if x.text):
        t = u.text.replace("150.000", "130.000")            # Zahlendreher
        if "über 40 Prozent" in t:                          # Auslassung eines Satzes
            t = re.sub(r"Mein Eindruck ist.*?defekt sind\.", "", t)
        parts.append(t)
    asr_text = " ".join(parts)
    # Diarisierung trifft 2 von 3 Sprechern (Staatssekretär verwechselt)
    speakers = {u.speaker_name for u in protocol.utterances if u.text}
    speakers.discard("Jonas Reuter")
    return asr_text, speakers
