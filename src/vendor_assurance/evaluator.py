"""Deterministic training evaluator for the synthetic report."""

from __future__ import annotations

import calendar
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import Literal

Status = Literal["Pass", "Fail", "Unclear"]
Sensitivity = Literal["High", "Medium", "Low"]


@dataclass(frozen=True)
class Finding:
    """One checklist result grounded in source evidence."""

    control: str
    status: Status
    evidence: str
    reasoning: str


@dataclass(frozen=True)
class Evaluation:
    """Merged document metadata, findings, score, and sensitivity."""

    vendor: str
    system: str
    data_types: list[str]
    hosting_region: str
    data_residency: str
    subprocessors: list[str]
    soc2_type: str
    report_date: str
    findings: list[Finding]
    score: int
    sensitivity: Sensitivity
    gaps: list[str]

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize the evaluation to JSON."""
        return json.dumps(asdict(self), indent=indent)


@dataclass(frozen=True)
class ControlRule:
    name: str
    pass_pattern: str
    fail_pattern: str
    unclear_pattern: str = ""
    mention_pattern: str = ""


# Controls 1-6 and 10 are decided from narrative text; 7-9 are decided from the
# metadata header, so they are evaluated separately in evaluate_document.
CONTROL_RULES = (
    ControlRule("MFA on privileged access", r"\bMFA\b[^.!?]{0,40}\b(required|enforced)\b[^.!?]{0,60}\b(privileged|administrator)", r"\bMFA\b[^.!?]{0,80}\bnot\s+(required|enforced)"),
    ControlRule(
        "TLS 1.2+ in transit",
        r"\bTLS\s+(1\.[2-9]|[2-9])\b",
        r"\bTLS\s+1\.[01]\b|\b(?:not|never)\s+(?:use|require|enforce|support)\s+TLS\s+(?:1\.[2-9]|[2-9])\b"
        r"|\bTLS\s+(?:1\.[2-9]|[2-9])\s+(?:is\s+)?(?:not\s+(?:used|required|enforced|supported)|disabled)\b",
        r"\bTLS\s+(?:1\.[2-9]|[2-9])\s+(?:is\s+)?(?:planned|pending|not\s+confirmed)\b",
    ),
    ControlRule(
        "AES-256 at rest",
        r"\bAES-256\b",
        r"\b(AES-128|unencrypted at rest)\b|\b(?:not|never)\s+(?:use|require|enforce)\s+AES-256\b"
        r"|\bAES-256\s+(?:is\s+)?(?:not\s+(?:used|required|enforced)|disabled)\b",
        r"\bAES-256\s+(?:is\s+)?(?:planned|pending|not\s+confirmed)\b",
    ),
    ControlRule(
        "Defined retention schedule",
        r"\b(?:retained\s+for|retention\s+(?:schedule|period))[^.!?]{0,100}"
        r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:days?|years?|months?)\b",
        r"\bno\s+defined\s+retention\s+schedule\b",
        r"\bretention\s+(?:schedule|period)\b[^.!?]{0,100}\b(?:planned|pending|not\s+(?:defined|stated)|no\s+period)\b",
        r"\bretention\s+(?:schedule|period)\b|\bretained\s+for\b",
    ),
    ControlRule(
        "Documented disposal",
        r"\b(documented\s+disposal|secure\s+disposal|cryptographic\s+erasure)\b",
        r"\bdisposal\s+(?:process\s+)?(?:is\s+)?not\s+documented\b"
        r"|\bno\s+(?:documented\s+disposal|secure\s+disposal|cryptographic\s+erasure)\b",
    ),
    ControlRule(
        "Incident response SLA within 72 hours",
        r"\bincident[^.]{0,160}\b(?:[1-9]|[1-6][0-9]|7[0-2])\s*hours?\b",
        r"\bincident[^.]{0,160}\b(?:7[3-9]|[89][0-9]|\d{3,})\s*hours?\b",
    ),
)

DATA_SUBJECT_RIGHTS_RULE = ControlRule(
    "Data subject rights",
    r"\b(data\s+subject\s+rights\s+process|process\s+for\s+access,\s+correction,\s+and\s+deletion\s+requests)\b",
    r"\bno\s+(?:process\s+for\s+data\s+subject\s+rights|data\s+subject\s+rights\s+process)\b"
    r"|\bdata\s+subject\s+rights\s+process\s+(?:is\s+)?not\s+(?:documented|implemented|defined)\b",
    r"\bno\s+direct\s+statement\s+about\s+a\s+process\s+for\s+data\s+subject\s+rights\b",
)

REMEDIATION = {
    "MFA on privileged access": "Request written confirmation that MFA is enforced for privileged and user access.",
    "TLS 1.2+ in transit": "Request the TLS configuration standard confirming version 1.2 or higher.",
    "AES-256 at rest": "Request confirmation of AES-256 or equivalent encryption at rest.",
    "Defined retention schedule": "Request a retention schedule stating a defined retention period.",
    "Documented disposal": "Request the documented deletion and disposal procedure.",
    "Incident response SLA within 72 hours": "Request a contractual incident notification SLA of 72 hours or less.",
    "Sub-processor disclosure": "Request a current sub-processor list and a change-notification commitment.",
    "SOC 2 Type II within 12 months": "Request a SOC 2 Type II report issued within the last twelve months.",
    "Data residency stated and consistent": "Request an explicit hosting region and a matching residency commitment.",
    "Data subject rights": "Request the documented DSAR handling process and response timelines.",
}


def _sentence_for_match(text: str, match: re.Match[str]) -> str:
    """Return source text without treating a wrapped line as a new sentence."""
    before = text[: match.start()]
    starts = [0]
    starts.extend(boundary.end() for boundary in re.finditer(r"\n[ \t]*\n|[.!?]\s+", before))
    starts.extend(
        boundary.end()
        for boundary in re.finditer(r"(?m)^[A-Za-z][\w /-]*:[^\n]*\n", before)
    )
    start = max(starts)
    after = text[match.end() :]
    boundary = re.search(r"[.!?](?=\s|\Z)|\n[ \t]*\n", after)
    end = match.end() + boundary.end() if boundary else len(text)
    return text[start:end].strip()


def _find(rule: ControlRule, chunks: list[str]) -> Finding:
    for status, pattern in (
        ("Fail", rule.fail_pattern),
        ("Unclear", rule.unclear_pattern),
        ("Pass", rule.pass_pattern),
    ):
        if not pattern:
            continue
        for chunk in chunks:
            # DOTALL so a wrapped line cannot hide a control: text extracted from a
            # PDF breaks sentences that the source document kept on one line.
            match = re.search(pattern, chunk, re.IGNORECASE | re.DOTALL)
            if match:
                evidence = _sentence_for_match(chunk, match)
                reasons = {
                    "Fail": "The quoted statement contradicts the required control.",
                    "Pass": "The quoted statement directly supports the required control.",
                    "Unclear": "The quoted statement confirms that the report lacks decisive evidence.",
                }
                reason = reasons[status]
                return Finding(rule.name, status, evidence, reason)
    if rule.mention_pattern:
        for chunk in chunks:
            match = re.search(rule.mention_pattern, chunk, re.IGNORECASE | re.DOTALL)
            if match:
                return Finding(
                    rule.name, "Unclear", _sentence_for_match(chunk, match),
                    "The source mentions the control but does not establish the required details.",
                )
    return Finding(
        rule.name,
        "Unclear",
        "",
        "The report does not provide enough evidence to determine implementation.",
    )


_FIELD_END = r"(?=\r?\n[A-Za-z][\w /-]*:|\r?\n[ \t]*\r?\n|\r?\n#|\r?\n[^\r\n]*[.!?][ \t]*(?:\r?\n|\Z)|\Z)"


def _field_match(text: str, label: str) -> re.Match[str] | None:
    return re.search(
        rf"^{re.escape(label)}:[ \t]*(.*?){_FIELD_END}",
        text,
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )


def _field(text: str, label: str, default: str = "Not stated") -> str:
    match = _field_match(text, label)
    return (" ".join(match.group(1).split()) or default) if match else default


def _field_line(text: str, label: str) -> str:
    """Return the original metadata field, including any line wrapping."""
    match = _field_match(text, label)
    return match.group(0).strip() if match else ""


def _subprocessor_disclosure(text: str) -> Finding:
    control = "Sub-processor disclosure"
    line = _field_line(text, "Sub-processors")
    if not line:
        return Finding(control, "Unclear", "", "The report does not state a sub-processor list.")
    value = _field(text, "Sub-processors", "").lower()
    if value in {"", "none stated", "not stated", "unknown", "not provided", "pending"}:
        return Finding(control, "Unclear", line, "The report does not provide a sub-processor disclosure.")
    if value in {"none", "none used"}:
        return Finding(control, "Pass", line, "The report explicitly states that no sub-processors are used.")
    return Finding(control, "Pass", line, "The report provides a named sub-processor list.")


def _soc2_currency(text: str, today: date) -> Finding:
    control = "SOC 2 Type II within 12 months"
    type_line = _field_line(text, "SOC 2 type")
    date_line = _field_line(text, "Report date")
    if not type_line:
        return Finding(control, "Unclear", "", "The report does not state a SOC 2 report type.")
    report_type = _field(text, "SOC 2 type", "")
    if report_type.lower() in {"", "not stated", "none stated", "unknown", "not provided"}:
        return Finding(control, "Unclear", type_line, "The source leaves the SOC 2 report type unresolved.")
    if not re.fullmatch(r"(?:SOC\s+2\s+)?Type\s+(?:II|2)", report_type, re.IGNORECASE):
        return Finding(control, "Fail", type_line, "The stated report type is not SOC 2 Type II.")
    try:
        reported = date.fromisoformat(_field(text, "Report date", ""))
    except ValueError:
        return Finding(control, "Unclear", date_line, "The report date is missing or not a valid date.")
    if reported > today:
        return Finding(control, "Unclear", date_line, "The report date is in the future and needs clarification.")
    cutoff = date.min if today.year == 1 else date(
        today.year - 1, today.month,
        min(today.day, calendar.monthrange(today.year - 1, today.month)[1]),
    )
    if reported < cutoff:
        return Finding(control, "Fail", date_line, "The Type II report is older than twelve months.")
    return Finding(control, "Pass", date_line, "The Type II report is dated within the last twelve months.")


def _data_residency(text: str) -> Finding:
    control = "Data residency stated and consistent"
    region = _field(text, "Hosting region", "")
    residency = _field(text, "Data residency", "")
    evidence = _field_line(text, "Data residency") or _field_line(text, "Hosting region")
    unresolved = {"", "not stated", "none stated", "unknown", "not provided", "pending"}
    if (
        region.lower() in unresolved or residency.lower() in unresolved
        or "not stated" in f"{region} {residency}".lower()
    ):
        return Finding(control, "Unclear", evidence, "The report does not state both a hosting region and a residency commitment.")
    region_pattern = re.escape(region)
    contradiction = (
        r"\bnot\s+(?:remain|stay|reside|be\s+(?:stored|hosted|kept))\s+"
        rf"(?:in|within)\s+(?:the\s+)?{region_pattern}\b"
        rf"|\b(?:stored|hosted|kept)\s+outside\s+(?:the\s+)?{region_pattern}\b"
    )
    if re.search(contradiction, residency, re.IGNORECASE):
        return Finding(control, "Fail", evidence, "The source explicitly contradicts residency in the stated hosting region.")
    if region.lower() in residency.lower():
        return Finding(control, "Pass", evidence, "The residency statement repeats the stated hosting region.")
    return Finding(control, "Fail", evidence, "The residency statement does not match the stated hosting region.")


def evaluate_document(chunks: list[str], *, today: date | None = None) -> Evaluation:
    """Evaluate all chunks and merge each control into one evidence-backed result."""
    text = "\n\n".join(chunks)
    findings = [_find(rule, chunks) for rule in CONTROL_RULES]
    findings.append(_subprocessor_disclosure(text))
    findings.append(_soc2_currency(text, today or datetime.now(tz=UTC).date()))
    findings.append(_data_residency(text))
    findings.append(_find(DATA_SUBJECT_RIGHTS_RULE, chunks))
    raw_types = _field(text, "Data types", "none")
    data_types = [value.strip() for value in raw_types.split(",") if value.strip()]
    normalized = {value.upper() for value in data_types}
    sensitivity: Sensitivity = (
        "High" if normalized & {"PII", "PHI"} else "Medium" if normalized & {"EMPLOYEE", "PAYMENT"} else "Low"
    )
    return Evaluation(
        vendor=_field(text, "Vendor", "Synthetic Vendor"),
        system=_field(text, "System"),
        data_types=data_types,
        hosting_region=_field(text, "Hosting region"),
        data_residency=_field(text, "Data residency"),
        subprocessors=[value.strip() for value in _field(text, "Sub-processors", "None stated").split(",")],
        soc2_type=_field(text, "SOC 2 type"),
        report_date=_field(text, "Report date"),
        findings=findings,
        score=sum(finding.status == "Pass" for finding in findings),
        sensitivity=sensitivity,
        gaps=[
            f"{finding.control} ({finding.status}): {REMEDIATION[finding.control]}"
            for finding in findings
            if finding.status != "Pass"
        ],
    )
