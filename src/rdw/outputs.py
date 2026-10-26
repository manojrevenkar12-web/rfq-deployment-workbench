"""What the agents hand to the sales engineer: the compliance matrix (Excel) and the clarification letter."""

from __future__ import annotations

import io

from .models import TenderAnalysis

VERDICT_DE = {"comply": "erfüllt", "clarify": "Klärung", "deviate": "Abweichung"}
VERDICT_EN = {"comply": "comply", "clarify": "to clarify", "deviate": "deviation"}


def compliance_matrix(a: TenderAnalysis, reviews: dict[str, str] | None = None) -> bytes:
    """The matrix buyers ask for: every requirement, its source, the answer, and a person's review where given."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    reviews = reviews or {}
    de = a.language == "de"
    words = VERDICT_DE if de else VERDICT_EN
    wb = Workbook()
    ws = wb.active
    ws.title = "Compliance"
    header = (
        ["Nr.", "Quelle", "Anforderung", "Art", "Priorität", "Antwort", "Begründung", "Geprüft"]
        if de
        else ["No.", "Source", "Requirement", "Kind", "Priority", "Answer", "Reason", "Reviewed"]
    )
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    fills = {"clarify": PatternFill("solid", fgColor="FFF4D6"), "deviate": PatternFill("solid", fgColor="FBE0DD")}
    for i, r in enumerate(a.requirements, 1):
        verdict = reviews.get(r.id, r.verdict)
        prio = ("Muss" if r.priority == "mandatory" else "Soll") if de else r.priority
        ws.append(
            [
                i,
                f"{r.source.file}, {r.source.locator}",
                r.source.text,
                r.label,
                prio,
                words[verdict],
                r.reason,
                ("ja" if de else "yes") if r.id in reviews else "",
            ]
        )
        if verdict in fills:
            for cell in ws[ws.max_row]:
                cell.fill = fills[verdict]
    for col, width in zip("ABCDEFGH", (5, 22, 70, 26, 10, 12, 50, 9), strict=True):
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def clarification_letter(a: TenderAnalysis, company: str) -> str:
    """Every open question in one letter: one round with the buyer instead of three."""
    questions = [r for r in a.requirements if r.verdict == "clarify" and r.kind not in ("procedural",)]
    deviations = [r for r in a.requirements if r.verdict == "deviate"]
    if a.language == "de":
        lines = [
            f"Betreff: Bieterfragen zu {a.tender_id}: {a.subject}",
            "",
            "Sehr geehrte Damen und Herren,",
            "",
            "zur Vorbereitung unseres Angebots bitten wir um Klärung der folgenden Punkte:",
            "",
        ]
        lines += [
            f"{i}. Zu „{r.source.text}“ ({r.source.locator}): {_question_de(r)}" for i, r in enumerate(questions, 1)
        ]
        if deviations:
            lines += ["", "Darüber hinaus weisen wir vorsorglich auf folgende Abweichungen hin:", ""]
            lines += [f"- {r.label}: {r.source.text}" for r in deviations]
        lines += [
            "",
            "Für eine kurze Rückmeldung bis zum Ablauf der Fragefrist danken wir Ihnen.",
            "",
            "Mit freundlichen Grüßen",
            company,
        ]
    else:
        lines = [
            f"Subject: Clarification questions on {a.tender_id}: {a.subject}",
            "",
            "Dear Sir or Madam,",
            "",
            "to prepare our offer, we kindly ask you to clarify the following points:",
            "",
        ]
        lines += [
            f'{i}. On "{r.source.text}" ({r.source.locator}): {_question_en(r)}' for i, r in enumerate(questions, 1)
        ]
        if deviations:
            lines += ["", "In addition, please note the following deviations:", ""]
            lines += [f"- {r.label}: {r.source.text}" for r in deviations]
        lines += ["", "Thank you for your answer before the question deadline.", "", "Kind regards", company]
    return "\n".join(lines) + "\n"


def _question_de(r) -> str:  # type: ignore[no-untyped-def]
    if r.kind == "other":
        return "Bitte erläutern Sie die Anforderung und die erwarteten Nachweise."
    if r.kind == "norm":
        return f"Ist ein gleichwertiger Nachweis anstelle einer Zertifizierung nach {r.value} zulässig?"
    if r.value is None:
        return "Bitte nennen Sie den geforderten Wert."
    return f"Ist eine Ausführung abweichend vom geforderten Wert ({r.value}{' ' + r.unit if r.unit else ''}) nach Abstimmung möglich?"


def _question_en(r) -> str:  # type: ignore[no-untyped-def]
    if r.kind == "other":
        return "Please explain the requirement and the evidence expected."
    if r.kind == "norm":
        return f"Is equivalent evidence acceptable instead of a certification to {r.value}?"
    if r.value is None:
        return "Please state the required value."
    return f"Is a solution deviating from the requested value ({r.value}{' ' + r.unit if r.unit else ''}) acceptable after agreement?"
