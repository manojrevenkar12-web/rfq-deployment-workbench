"""Tenders as buyers send them (PDF specification, sometimes an Excel bill of quantities, a cover e-mail) and the
answer key a supplier's sales engineers would have produced: every requirement, whether it is met, the norms
cited, the bid decision and the product variant."""

from __future__ import annotations

import datetime as dt
import random
from dataclasses import asdict, dataclass, field
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from .profiles import COMMERCIAL_TEMPLATES, Kind, Profile, Template

# Share of sampled knockout values kept: rail and fire buyers rarely ask for the impossible, charging tenders
# from fleets more often ask for power or voltage ranges a supplier does not have.
KEEP_KNOCKOUTS = {"gleiswerk": 0.2, "voltaro": 0.75, "brandt": 0.4}

# How a bill of quantities (Leistungsverzeichnis) row names each kind: label, value text.
LV_ROWS: dict[str, tuple[str, str, str, str]] = {
    # kind: (label de, value de, label en, value en)
    "travel_speed_kmh": (
        "Höchstgeschwindigkeit Eigenfahrt",
        "mind. {v} km/h",
        "Travel speed, self-propelled",
        "min. {v} km/h",
    ),
    "axle_load_t": ("Radsatzlast", "max. {v} t", "Axle load", "max. {v} t"),
    "engine_power_kw": ("Motorleistung", "mind. {v} kW", "Engine power", "min. {v} kW"),
    "noise_dba": (
        "Schalldruckpegel am Arbeitsplatz",
        "max. {v} dB(A)",
        "Sound pressure at operator position",
        "max. {v} dB(A)",
    ),
    "availability_percent": ("Technische Verfügbarkeit", "mind. {v} %", "Technical availability", "min. {v} %"),
    "gradient_permille": ("Befahrbare Steigung", "bis {v} ‰", "Gradient", "up to {v} ‰"),
    "charging_power_kw": (
        "Ladeleistung je Ladepunkt",
        "mind. {v} kW",
        "Charging power per charge point",
        "min. {v} kW",
    ),
    "max_current_a": ("Maximaler Ladestrom", "mind. {v} A", "Maximum charging current", "min. {v} A"),
    "efficiency_percent": ("Wirkungsgrad bei Nennleistung", "mind. {v} %", "Efficiency at rated power", "min. {v} %"),
    "cable_length_m": ("Länge Ladekabel", "mind. {v} m", "Charging cable length", "min. {v} m"),
    "service_response_hours": ("Reaktionszeit Service", "max. {v} h", "Service response time", "max. {v} h"),
    "gross_mass_t": ("Zulässige Gesamtmasse Fahrgestell", "max. {v} t", "", ""),
    "water_tank_l": ("Löschwasserbehälter", "mind. {v} l", "", ""),
    "foam_tank_l": ("Schaummitteltank", "{v} l", "", ""),
    "generator_kva": ("Tragbarer Stromerzeuger", "mind. {v} kVA", "", ""),
}

NORM_SENTENCES_DE = [
    "Die Konformität mit {n} {ist} durch ein gültiges Zertifikat nachzuweisen.",
    "Die Ausführung {muss} den Anforderungen der {n} entsprechen.",
    "Nachweis der Erfüllung von {n}: Zertifikat einer anerkannten Prüfstelle.",
]
NORM_SENTENCES_EN = [
    "Conformity with {n} {shall} be demonstrated by a valid certificate.",
    "The design {shall} comply with {n}.",
]

# Obligations about the bid itself: real requirements, but nothing a product has to meet.
PROCEDURAL_DE = [
    "Das Angebot {ist} ausschließlich elektronisch über die Vergabeplattform einzureichen.",
    "Dem Angebot {muss} ein Nachweis über eine Betriebshaftpflichtversicherung beigefügt werden.",
    "Der Bieter hat mit dem Angebot drei Referenzen über vergleichbare Lieferungen der letzten fünf Jahre vorzulegen.",
    "Nebenangebote sind nicht zugelassen.",
    "Der Bieter {muss} die Eigenerklärung zur Eignung vollständig ausgefüllt einreichen.",
    "Bieterfragen sind bis spätestens sieben Kalendertage vor Ablauf der Angebotsfrist schriftlich zu stellen.",
]
PROCEDURAL_EN = [
    "The offer {shall} be submitted exclusively via the e-procurement platform.",
    "Bidders {shall} enclose three references for comparable deliveries within the last five years.",
    "Variant offers are not permitted.",
    "Bidders {shall} provide proof of liability insurance with their offer.",
]

LIABILITY = {
    "contract_value": (
        "auf die Höhe des Auftragswertes begrenzt",
        "bis zur Höhe des Auftragswertes",
        "limited to the contract value",
    ),
    "limited": (
        "auf 1 Mio. EUR je Schadensfall begrenzt",
        "bis zu 1 Mio. EUR je Schadensfall",
        "limited to EUR 1 million per event",
    ),
    "double_contract_value": (
        "auf das Doppelte des Auftragswertes begrenzt",
        "bis zum Doppelten des Auftragswertes",
        "limited to twice the contract value",
    ),
    "unlimited": ("der Höhe nach unbegrenzt", "in unbegrenzter Höhe", "unlimited in amount"),
}
LANGS = {"de": ("deutscher", "German"), "en": ("englischer", "English"), "fr": ("französischer", "French")}


@dataclass
class TruthRequirement:
    id: str
    doc: str
    text: str
    kind: str
    value: Any
    unit: str | None
    priority: str  # mandatory | desirable
    verdict: str  # comply | clarify | deviate
    severity: str | None  # knockout | major | minor when a red flag
    red_flag: bool
    norms: list[str] = field(default_factory=list)


@dataclass
class TruthTender:
    id: str
    customer: str
    language: str
    buyer: str
    subject: str
    received: str
    due: str
    requirements: list[TruthRequirement]
    norms: dict[str, str]  # norm -> certified | not_certified
    bid: str  # bid | no_bid
    variant: str | None
    documents: list[str]


def verdict(kind: Kind, value: Any) -> str:
    if kind.op == "max":
        if value is None:
            return "deviate"
        return "comply" if value <= kind.standard else "clarify" if value <= kind.limit else "deviate"
    if kind.op == "min":
        return "comply" if value >= kind.standard else "clarify" if value >= kind.limit else "deviate"
    if kind.op == "range":
        lo, hi = value
        if kind.standard[0] <= lo and hi <= kind.standard[1]:
            return "comply"
        if kind.limit[0] <= lo and hi <= kind.limit[1]:
            return "clarify"
        return "deviate"
    if kind.op == "set":
        return "comply" if value in kind.standard else "clarify" if value in kind.limit else "deviate"
    if kind.op == "bool":
        return "comply" if kind.standard else "clarify" if kind.limit else "deviate"
    raise ValueError(kind.op)


def _num(v: Any, lang: str, thousands: bool = False) -> str:
    if isinstance(v, float) and not v.is_integer():
        s = f"{v:.1f}"
        return s.replace(".", ",") if lang == "de" else s
    n = int(v)
    if thousands and n >= 1000:
        s = f"{n:,}"
        return s.replace(",", ".") if lang == "de" else s
    return str(n)


def _modal(text: str, lang: str, mandatory: bool) -> str:
    if lang == "de":
        forms = {
            "{muss}": ("muss", "soll"),
            "{muessen}": ("müssen", "sollen"),
            "{darf}": ("darf", "sollte"),
            "{ist}": ("ist", "ist"),
        }
    else:
        forms = {"{shall}": ("shall", "should")}
    for token, (m, d) in forms.items():
        text = text.replace(token, m if mandatory else d)
    return text


def _render(t: Template, value: Any, lang: str, rnd: random.Random, mandatory: bool) -> str | None:
    pool = t.de if lang == "de" else t.en
    if not pool:
        return None
    options = list(pool)
    rnd.shuffle(options)
    for fmt in options:
        if "{y}" in fmt and (not isinstance(value, int) or value % 12):
            continue
        if "{m}" in fmt and value not in (26, 52, 78):
            continue
        params: dict[str, str] = {}
        if isinstance(value, tuple):
            lo, hi = value
            minus = "−" if lang == "de" and rnd.random() < 0.3 else "-"
            params["lo"] = (minus + str(abs(lo))) if lo < 0 else str(lo)
            params["hi"] = str(hi)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            params["v"] = params["vd"] = _num(value, lang)
            params["vt"] = _num(value, lang, thousands=True)
            if isinstance(value, int):
                params["y"] = str(value // 12)
                params["m"] = str(round(value * 12 / 52))
        elif value is None:
            params["v"] = "unbegrenzt"
        else:
            params["v"] = str(value)
        if t.kind == "liability":
            de1, de2, en = LIABILITY[value]
            params.update(liab_de=de1, liab_de2=de2, liab_en=en)
        if t.kind == "documentation_language":
            params.update(lang_de=LANGS[value][0], lang_en=LANGS[value][1])
        text = _modal(fmt, lang, mandatory)
        for k, v in params.items():
            text = text.replace("{" + k + "}", v)
        if not mandatory and lang == "de" and not any(w in text for w in (" soll", " sollte", " sollen")):
            text = text.rstrip(".") + " (wünschenswert)."
        if not mandatory and lang == "en" and " should" not in text:
            text = text.rstrip(".") + " (desirable)."
        return text
    return None


def _truth_value(t: Template, value: Any, text: str) -> Any:
    """The value as stated: months stated for a delivery are converted the way an engineer would (52/12 weeks)."""
    if t.kind == "delivery_weeks" and ("Monate" in text or "months" in text):
        return round(round(value * 12 / 52) * 52 / 12, 1)
    return value


class TenderWriter:
    def __init__(self, profile: Profile, rnd: random.Random):
        self.p = profile
        self.rnd = rnd

    def make(self, index: int, received: dt.date) -> tuple[TruthTender, dict[str, Any]]:
        p, rnd = self.p, self.rnd
        lang = rnd.choices(list(p.languages), weights=list(p.languages.values()))[0]
        tid = f"{p.id[:2].upper()}-{received.year}-{index:03d}"
        buyer = rnd.choice([b for b in p.buyers if (lang == "en") == (not _german_name(b))] or p.buyers)
        reqs: list[TruthRequirement] = []
        lines: list[tuple[str, str]] = []  # (section, text)
        rows: list[tuple[str, str, str, TruthRequirement]] = []
        use_lv = rnd.random() < 0.35 and any(k in LV_ROWS and LV_ROWS[k][2 if lang == "en" else 0] for k in p.kinds)

        # Subject and variant
        variant = None
        if p.variant_kind == "subject":
            v = rnd.choice(p.variants)
            variant = v.name
            subject = f"Beschaffung einer {v.subject}" if lang == "de" else f"Supply of a {v.subject_en}"
        elif p.id == "voltaro":
            subject = (
                f"Lieferung und Installation von {rnd.choice([4, 6, 8, 12, 20])} DC-Schnellladesäulen"
                if lang == "de"
                else f"Supply and installation of {rnd.choice([4, 6, 10, 16])} DC fast chargers"
            )
        else:
            subject = ""

        technical = [t for t in p.templates if (t.de if lang == "de" else t.en)]
        rnd.shuffle(technical)
        chosen = [t for t in technical if rnd.random() < 0.75]
        if p.variant_kind not in ("subject",):
            key = [t for t in technical if t.kind == p.variant_kind]
            if key and key[0] not in chosen:
                chosen.insert(0, key[0])
        for t in chosen:
            value = rnd.choice(t.values)
            kind = p.kinds[t.kind]
            # Buyers usually ask for what the market offers: most knockouts are rare, as in real tenders.
            if (
                kind.severity == "knockout"
                and verdict(kind, value) == "deviate"
                and rnd.random() > KEEP_KNOCKOUTS[p.id]
            ):
                fitting = [x for x in t.values if verdict(kind, x) != "deviate"]
                value = rnd.choice(fitting) if fitting else value
            mandatory = rnd.random() < 0.78 or t.kind == p.variant_kind
            text = _render(t, value, lang, rnd, mandatory)
            if text is None:
                continue
            req = self._req(tid, len(reqs), t, value, text, mandatory)
            if t.kind == "vehicle_type":
                subject = f"Beschaffung eines Feuerwehrfahrzeugs {value}"
                variant = next((v.name for v in p.variants if v.subject == value), None)
            if t.kind == p.variant_kind and p.id == "voltaro":
                variant = next((v.name for v in p.variants if v.fits["charging_power_kw"] >= value), None)
            reqs.append(req)
            if use_lv and t.kind in LV_ROWS and LV_ROWS[t.kind][2 if lang == "en" else 0] and rnd.random() < 0.6:
                label, val = (
                    (LV_ROWS[t.kind][0], LV_ROWS[t.kind][1])
                    if lang == "de"
                    else (LV_ROWS[t.kind][2], LV_ROWS[t.kind][3])
                )
                val = val.replace("{v}", _num(value, lang))
                prio = (
                    ("Muss" if mandatory else "Soll") if lang == "de" else ("Mandatory" if mandatory else "Desirable")
                )
                req.doc = "lv"
                req.text = f"{label}: {val}"
                rows.append((label, val, prio, req))
            else:
                lines.append(("tech", text))

        # Norm requirements stated on their own
        pool = p.norms_certified + p.norms_certified + p.norms_not_certified
        for norm in rnd.sample(pool, k=min(len(pool), rnd.randint(2, 4))):
            if any(norm in r.norms for r in reqs):
                continue
            fmt = rnd.choice(NORM_SENTENCES_DE if lang == "de" else NORM_SENTENCES_EN)
            mandatory = rnd.random() < 0.85
            text = _modal(fmt, lang, mandatory).replace("{n}", norm)
            if not mandatory and lang == "de" and " soll" not in text:
                text = text.rstrip(".") + " (wünschenswert)."
            certified = norm in p.norms_certified
            nv = "comply" if certified else "deviate"
            reqs.append(
                TruthRequirement(
                    f"{tid}-R{len(reqs) + 1:02d}",
                    "spec",
                    text,
                    "norm",
                    norm,
                    None,
                    "mandatory" if mandatory else "desirable",
                    nv,
                    ("major" if mandatory else "minor") if nv == "deviate" else None,
                    nv == "deviate",
                    [norm],
                )
            )
            lines.append(("norms", text))

        # Commercial terms
        for t in rnd.sample(COMMERCIAL_TEMPLATES, k=rnd.randint(5, 8)):
            value = rnd.choice(t.values)
            text = _render(t, value, lang, rnd, True)
            if text is None:
                continue
            if t.kind == "penalty_cap_percent" and value is None:
                text = (
                    "Die Vertragsstrafe für Lieferverzug ist der Höhe nach nicht begrenzt."
                    if lang == "de"
                    else "Liquidated damages for late delivery shall not be capped."
                )
            reqs.append(self._req(tid, len(reqs), t, value, text, True))
            lines.append(("commercial", text))

        # Obligations about the bid itself
        for fmt in rnd.sample(PROCEDURAL_DE if lang == "de" else PROCEDURAL_EN, k=rnd.randint(2, 4)):
            text = _modal(fmt, lang, True)
            reqs.append(
                TruthRequirement(
                    f"{tid}-R{len(reqs) + 1:02d}",
                    "spec",
                    text,
                    "procedural",
                    None,
                    None,
                    "mandatory",
                    "comply",
                    None,
                    False,
                    [],
                )
            )
            lines.append(("procedure", text))

        # Background that looks like requirements but is not
        pool_bg = p.background_de if lang == "de" else (p.background_en or p.background_de)
        background = [self._fill(s) for s in rnd.sample(pool_bg, k=min(len(pool_bg), rnd.randint(2, 4)))]

        norms = {}
        for r in reqs:
            for n in r.norms:
                norms[n] = "certified" if n in p.norms_certified else "not_certified"
        knockout = any(r.red_flag and r.severity == "knockout" for r in reqs)
        bid = "no_bid" if knockout or (variant is None and p.variant_kind != "subject") else "bid"
        due = received + dt.timedelta(days=rnd.choice([14, 21, 28, 35, 42]))
        docs = ["spec.pdf", "cover.eml"] + (["lv.xlsx"] if rows else [])
        truth = TruthTender(
            tid, p.id, lang, buyer, subject, received.isoformat(), due.isoformat(), reqs, norms, bid, variant, docs
        )
        layout = {"lines": lines, "rows": rows, "background": background}
        return truth, layout

    def _req(self, tid: str, n: int, t: Template, value: Any, text: str, mandatory: bool) -> TruthRequirement:
        kind = self.p.kinds[t.kind]
        stated = _truth_value(t, value, text)
        v = verdict(kind, stated)
        priority = "mandatory" if mandatory else "desirable"
        red = v == "deviate" or (v == "clarify" and kind.commercial and kind.severity == "major")
        severity = None
        if red:
            if not mandatory:
                severity = "minor"
            elif v == "deviate":
                severity = kind.severity
            else:
                severity = "major" if kind.severity in ("knockout", "major") else "minor"
        norms = []
        if t.norm and t.norm.replace("{v}", str(value)) in text:
            norms = [t.norm.replace("{v}", str(value))]
        if isinstance(stated, tuple):
            stated = list(stated)
        return TruthRequirement(
            f"{tid}-R{n + 1:02d}", "spec", text, t.kind, stated, kind.unit, priority, v, severity, red, norms
        )

    def _fill(self, s: str) -> str:
        r = self.rnd
        return (
            s.replace("{n}", str(r.choice([42, 120, 312, 860, 1250, 2400])))
            .replace("{year}", str(r.choice([1998, 2004, 2011, 2017, 2023])))
            .replace("{h}", str(r.choice([4, 5, 6])))
            .replace("{m}", str(r.choice(["3,4", "3,6", "3,8"])))
        )


def _german_name(buyer: str) -> bool:
    return not any(w in buyer for w in ("Northfield", "Fleetway", "Nordic"))


# ---------------------------------------------------------------- rendering


def write_documents(
    truth: TruthTender, layout: dict[str, Any], folder: Path, profile: Profile, rnd: random.Random
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    de = truth.language == "de"
    _pdf(folder / "spec.pdf", truth, layout, profile, de)
    if layout["rows"]:
        _xlsx(folder / "lv.xlsx", layout["rows"], de)
    _eml(folder / "cover.eml", truth, profile, de)


def _pdf(path: Path, truth: TruthTender, layout: dict[str, Any], profile: Profile, de: bool) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    story: list[Any] = []
    title = "Leistungsbeschreibung" if de else "Technical specification"
    story.append(Paragraph(f"{title}: {truth.subject}", styles["Title"]))
    story.append(
        Paragraph(
            f"{'Auftraggeber' if de else 'Contracting authority'}: {truth.buyer}<br/>"
            f"{'Vergabenummer' if de else 'Reference'}: {truth.id}",
            body,
        )
    )
    sections = [
        ("bg", "1 Allgemeines" if de else "1 General"),
        ("tech", "2 Technische Anforderungen" if de else "2 Technical requirements"),
        ("norms", "3 Normen und Nachweise" if de else "3 Standards and certificates"),
        ("commercial", "4 Kaufmännische und vertragliche Bedingungen" if de else "4 Commercial and contractual terms"),
        ("procedure", "5 Angebotsabgabe" if de else "5 Submission of offers"),
    ]
    for key, heading in sections:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(heading, styles["Heading2"]))
        items = layout["background"] if key == "bg" else [t for s, t in layout["lines"] if s == key]
        if key == "tech" and layout["rows"]:
            items = [
                *items,
                (
                    "Weitere Anforderungen sind im beigefügten Leistungsverzeichnis aufgeführt."
                    if de
                    else "Further requirements are listed in the attached price schedule."
                ),
            ]
        for i, text in enumerate(items, 1):
            number = sections.index((key, heading)) + 1
            story.append(Paragraph(f"{number}.{i} {_escape(text)}", body))
    SimpleDocTemplate(str(path), pagesize=A4, title=title, author=truth.buyer).build(story)


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _xlsx(path: Path, rows: list[tuple[str, str, str, Any]], de: bool) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "LV" if de else "Schedule"
    ws.append(
        ["Pos.", "Beschreibung", "Anforderung", "Kategorie"]
        if de
        else ["Item", "Description", "Requirement", "Category"]
    )
    for i, (label, value, prio, _req) in enumerate(rows, 1):
        ws.append([f"1.{i:02d}", label, value, prio])
    wb.save(path)


def _eml(path: Path, truth: TruthTender, profile: Profile, de: bool) -> None:
    m = EmailMessage()
    m["From"] = f"vergabe@{_domain(truth.buyer)}"
    m["To"] = f"angebote@{profile.id}.example"
    m["Subject"] = (
        f"Aufforderung zur Angebotsabgabe {truth.id}: {truth.subject}"
        if de
        else f"Invitation to tender {truth.id}: {truth.subject}"
    )
    m["Date"] = dt.datetime.fromisoformat(truth.received + "T09:30:00").strftime("%a, %d %b %Y %H:%M:%S +0100")
    due = dt.date.fromisoformat(truth.due).strftime("%d.%m.%Y" if de else "%d %B %Y")
    body = (
        f"Sehr geehrte Damen und Herren,\n\nhiermit fordern wir Sie zur Abgabe eines Angebots für {truth.subject} auf. "
        f"Die Unterlagen finden Sie im Anhang. Angebote sind bis zum {due}, 12:00 Uhr, einzureichen. "
        f"Bieterfragen richten Sie bitte bis spätestens sieben Tage vor Ablauf der Angebotsfrist an diese Adresse.\n\n"
        f"Mit freundlichen Grüßen\nZentrale Vergabestelle\n{truth.buyer}\n"
        if de
        else f"Dear Sir or Madam,\n\nplease submit your offer for the {truth.subject}. The documents are attached. "
        f"The deadline for offers is {due}, 12:00 CET. Questions can be sent to this address until seven days before the deadline.\n\n"
        f"Kind regards\nProcurement\n{truth.buyer}\n"
    )
    m.set_content(body)
    path.write_bytes(bytes(m))


def _domain(buyer: str) -> str:
    return (
        "".join(c for c in buyer.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue") if c.isalnum())[:20]
        + ".example"
    )


def truth_json(t: TruthTender) -> dict[str, Any]:
    return asdict(t)
