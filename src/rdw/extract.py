"""Requirement extraction: which segments are requirements, of which kind, with which value and priority.

Deterministic on purpose: a vocabulary per domain (config/domains), obligation words in German and English,
unit-aware number parsing. The same input always gives the same requirements, every requirement points at its
source, and what the vocabulary does not know is marked "other" for a person instead of being guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .config import KindSpec
from .ingest import Segment

MANDATORY_DE = re.compile(
    r"\b(muss|müssen|darf|dürfen|zwingend|erforderlich|gefordert|verpflichtet|nicht zugelassen|unzulässig|"
    r"sicherzustellen|nachzuweisen|vorzusehen|vorzulegen|einzureichen|beizufügen|zu liefern|zu stellen|"
    r"durchzuführen|auszustatten|auszuführen|zu erbringen|zu gewährleisten)\b|\b(ist|sind|hat|haben)\b[^.]*\bzu\s+\w+",
    re.I,
)
DESIRABLE_DE = re.compile(r"\b(soll|sollen|sollte|sollten|wünschenswert|optional|vorzugsweise)\b", re.I)
MANDATORY_EN = re.compile(r"\b(shall|must|is required|are required|not permitted|not allowed|mandatory)\b", re.I)
DESIRABLE_EN = re.compile(r"\b(should|desirable|preferably|optional)\b", re.I)
# Sentences that inform rather than require.
INFORMATIVE = re.compile(
    r"\b(zu entnehmen|enthält|enthalten|siehe|hinweise|weitere anforderungen sind|derzeit|bisher|bestehende?n?|"
    r"betreibt|betreiben|verfügt über|im jahr \d{4}|wurden|wurde|plant|umfasst|zur verfügung|can be found|"
    r"further requirements are|currently|existing|comprises|is available|in \d{4},|runs \d+)\b",
    re.I,
)
PROCEDURAL = re.compile(
    r"\b(angebot|angebots|bieter|vergabe|referenz|eignung|nebenangebot|eigenerklärung|haftpflichtversicherung|"
    r"offer|bidder|tender|references|insurance|variant offers|e-procurement)\w*",
    re.I,
)
NORM = re.compile(
    r"\b(DIN EN ISO|DIN EN|DIN|EN ISO|EN|ISO|IEC|VDE-AR-N|PTB-A)\s?(\d{2,5}(?:[-.]\d+)*)(?::\d{4})?|\b(TSI\s?NOI)\b"
)
NUMBER = r"[-−–]?\d{1,3}(?:[.,  ]\d{3})+(?:[.,]\d+)?|[-−–]?\d+(?:[.,]\d+)?"


@dataclass
class Found:
    segment: Segment
    kind: str
    value: Any
    priority: str
    norms: list[str]
    confidence: float


def norms_in(text: str) -> list[str]:
    out = []
    for m in NORM.finditer(text):
        if m.group(3):
            out.append("TSI NOI")
            continue
        prefix, number = m.group(1), m.group(2)
        if prefix == "EN" and re.match(r"^\d{2}$", number):  # "EN 50" in running text is not a norm
            continue
        out.append(f"{prefix} {number}".replace("  ", " "))
    return list(dict.fromkeys(out))


def parse_number(s: str, lang: str) -> float:
    s = s.replace("−", "-").replace("–", "-").replace(" ", "").replace(" ", "")
    if lang == "de":
        if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", s):
            s = s.replace(".", "")
        s = s.replace(",", ".")
    else:
        if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", s):
            s = s.replace(",", "")
        elif re.fullmatch(r"-?\d+,\d+", s):
            s = s.replace(",", ".")
    return float(s)


def _clean(n: float) -> float | int:
    return int(n) if float(n).is_integer() else round(n, 2)


def _strip_norms(text: str) -> str:
    return NORM.sub(" ", text)


def _numbers_with_unit(text: str, units: list[str], lang: str) -> list[tuple[float, str]]:
    found = []
    t = _strip_norms(text)
    for unit in sorted(units, key=len, reverse=True):
        pattern = rf"({NUMBER})\s*{re.escape(unit)}(?![a-zäöüß])"
        for m in re.finditer(pattern, t, re.I):
            try:
                found.append((parse_number(m.group(1), lang), unit))
            except ValueError:
                continue
    if not found:
        # Counted things: "2 gleichzeitig nutzbare Ladepunkte", "4 charge points that can be used"
        for unit in units:
            if len(unit) < 4:
                continue
            for m in re.finditer(rf"\b(\d{{1,3}})\s+(?:[\wäöüß-]+\s+){{1,3}}{re.escape(unit)}", t, re.I):
                found.append((float(m.group(1)), unit))
    return found


def value_of(spec: KindSpec, text: str, lang: str) -> Any:
    low = text.lower()
    v = spec.value
    if v == "bool":
        return True
    if v in ("enum", "enum_number"):
        for p in spec.patterns:
            if m := re.search(p, text, re.I):
                raw = re.sub(r"\s+", " ", m.group(1)).strip()
                if v == "enum_number":
                    return int(raw)
                if re.fullmatch(r"HL ?\d", raw, re.I):
                    return raw.upper().replace(" ", "")
                if re.fullmatch(r"FP[NH] ?\d+-\d+", raw, re.I):
                    return re.sub(r"(FP[NH]) ?", r"\1 ", raw.upper())
                if re.fullmatch(r"1 ?\+ ?\d", raw):
                    return raw.replace(" ", "")
                if re.fullmatch(r"(HLF|LF|TLF|DLK|RW|MLF) ?\d.*", raw, re.I):
                    return re.sub(r"^([A-Za-z]+) ?", lambda mm: mm.group(1).upper() + " ", raw)
                return raw
        return None
    if v == "penalty":
        if re.search(r"nicht begrenzt|unbegrenzt|ohne obergrenze|not be capped|uncapped|unlimited", low):
            return "unlimited"
        m = re.search(
            rf"(?:höchstens|maximal|max\.|begrenzt auf|insgesamt|capped at|limited to|maximum of|up to)\s*({NUMBER})\s*%",
            text,
            re.I,
        )
        if m:
            return _clean(parse_number(m.group(1), lang))
        percents = re.findall(rf"({NUMBER})\s*%", text)
        return _clean(parse_number(percents[-1], lang)) if len(percents) > 1 else None
    if v == "duration_months":
        if m := re.search(rf"({NUMBER})\s*(monate|monaten|months)", low):
            return _clean(parse_number(m.group(1), lang))
        if m := re.search(rf"({NUMBER})\s*(jahre|jahren|years)", low):
            return _clean(parse_number(m.group(1), lang) * 12)
        return None
    if v == "duration_weeks":
        if m := re.search(rf"({NUMBER})\s*(wochen|weeks)", low):
            return _clean(parse_number(m.group(1), lang))
        if m := re.search(rf"({NUMBER})\s*(monate|monaten|months)", low):
            return round(parse_number(m.group(1), lang) * 52 / 12, 1)
        return None
    if v == "liability":
        if re.search(r"unbegrenzt|unlimited|in unbegrenzter", low):
            return "unlimited"
        if re.search(r"doppelte|twice|double", low):
            return "double_contract_value"
        if re.search(r"mio|million", low):
            return "limited"
        if re.search(r"auftragswert|contract value|order value", low):
            return "contract_value"
        return None
    if v == "language":
        for word, code in (
            ("deutsch", "de"),
            ("german", "de"),
            ("englisch", "en"),
            ("english", "en"),
            ("französisch", "fr"),
            ("french", "fr"),
        ):
            if word in low:
                return code
        return None
    if v == "range":
        t = _strip_norms(text).replace("−", "-").replace("–", "-")
        unit = re.escape(spec.unit or "")
        m = re.search(
            rf"([-]?\d+(?:[.,]\d+)?)\s*(?:{unit})?\s*(?:bis|to|-|/|und|and)\s*\+?([-]?\d+(?:[.,]\d+)?)\s*{unit}",
            t,
            re.I,
        )
        if m:
            lo, hi = parse_number(m.group(1), lang), parse_number(m.group(2), lang)
            return [_clean(lo), _clean(hi)]
        return None
    if v == "number":
        found = _numbers_with_unit(text, spec.units or ([spec.unit.lower()] if spec.unit else []), lang)
        if not found and spec.name == "water_tank_l":
            found = _numbers_with_unit(text, ["liter"], lang)
        if not found:
            return None
        n, unit = found[0]
        if unit == "mw" and spec.unit == "kW":
            n *= 1000
        return _clean(n)
    return None


def _score(spec: KindSpec, low: str, text: str) -> float:
    score = 0.0
    for kw in spec.keywords_de + spec.keywords_en:
        if kw in low:
            score += 1 + len(kw) / 20
    if score == 0 and not any(re.search(p, text, re.I) for p in spec.patterns):
        return 0.0
    for p in spec.patterns:
        if re.search(p, text, re.I):
            score += 2
    for u in spec.units:
        if re.search(rf"\d\s*{re.escape(u)}(?![a-zäöüß])", low):
            score += 1.5
    return score


def classify(segment: Segment, kinds: dict[str, KindSpec], lang: str) -> tuple[str, Any, float]:
    text = segment.text
    bare = _strip_norms(text)  # a norm number is evidence of a norm, not of a product property
    low = bare.lower()
    ranked = sorted(((s, k) for k, spec in kinds.items() if (s := _score(spec, low, bare)) > 0), reverse=True)
    for score, k in ranked:
        value = value_of(kinds[k], text, lang)
        if value is not None:
            return k, value, min(1.0, 0.6 + score / 10)
    if ranked:
        return ranked[0][1], None, 0.5
    return "", None, 0.0


def is_obligation(text: str) -> bool:
    return bool(
        MANDATORY_DE.search(text) or DESIRABLE_DE.search(text) or MANDATORY_EN.search(text) or DESIRABLE_EN.search(text)
    )


def priority_of(segment: Segment) -> str:
    cat = segment.meta.get("category", "").lower()
    if cat:
        return "desirable" if cat.startswith(("soll", "desir", "opt", "kann")) else "mandatory"
    t = segment.text
    if DESIRABLE_DE.search(t) or DESIRABLE_EN.search(t):
        return "desirable"
    return "mandatory"


CONFORMITY = re.compile(
    r"konformität|entsprechen|gemäß|nach |zertifikat|nachweis|comply|conformity|certificate|according to", re.I
)


def extract(segments: list[Segment], kinds: dict[str, KindSpec], lang: str) -> list[Found]:
    found: list[Found] = []
    for seg in segments:
        text = seg.text
        if len(text) < 8 or re.match(r"^(Auftraggeber|Vergabenummer|Contracting authority|Reference)\s*:", text):
            continue
        obligation = is_obligation(text)
        informative = bool(INFORMATIVE.search(text))
        if informative and not (obligation and not re.search(r"zu entnehmen|can be found|siehe", text, re.I)):
            continue
        kind, value, confidence = classify(seg, kinds, lang)
        norms = norms_in(text)
        statement = seg.doc == "lv" or (kind and value is not None and kinds[kind].value not in ("bool",))
        if seg.doc == "eml" and (not (kind and value is not None) or PROCEDURAL.search(text)):
            continue  # the cover e-mail carries logistics; only clear product or contract requirements count
        evidence = bool(norms and re.search(r"nachweis|zertifikat|certificate|conformity|konformität", text, re.I))
        if not (obligation or statement or evidence):
            continue
        if kind and value is None and kinds[kind].value != "bool" and PROCEDURAL.search(text) and not norms:
            kind = ""  # "Lieferungen" in a reference requirement is not a delivery term
        if not kind or (value is None and kinds[kind].value not in ("bool",) and norms and CONFORMITY.search(text)):
            if norms and CONFORMITY.search(text):
                kind, value, confidence = "norm", norms[0], 0.9
            elif PROCEDURAL.search(text):
                kind, value, confidence = "procedural", None, 0.8
            else:
                kind, value, confidence = "other", None, 0.3
        found.append(Found(seg, kind, value, priority_of(seg), norms, confidence))
    return found
