"""Regulatory ontology for CTD/CTA document signal classification."""

from __future__ import annotations

import re


CATEGORY_META = {
    "specifications": {
        "label": "Specifications",
        "ctd_mapping": "3.2.S.4 / 3.2.P.5 Control; 3.2.P.5.1 Specifications; 3.2.P.5.2 Analytical Procedures; 3.2.P.5.6 Justification",
        "regulatory_basis": "ICH M4Q, ICH Q6A, ICH Q2(R2), ICH Q14, MFDS criteria/test methods review, USP/EP monographs",
    },
    "test_methods": {
        "label": "Test Methods",
        "ctd_mapping": "3.2.P.2 Pharmaceutical Development; 3.2.S.4.2 / 3.2.P.5.2 Analytical Procedures; 3.2.S.4.3 / 3.2.P.5.3 Validation",
        "regulatory_basis": "ICH M4Q, ICH Q2(R2), ICH Q14, MFDS criteria/test methods review, USP/EP/KP procedure suitability",
    },
    "bioequivalence": {
        "label": "Bioequivalence",
        "ctd_mapping": "Module 5; 5.3.1 Biopharmaceutic Studies; comparative dissolution / BE evidence",
        "regulatory_basis": "ICH M4E/M4, MFDS pharmaceutical equivalence criteria, comparative dissolution and BE study principles",
    },
    "stability": {
        "label": "Stability",
        "ctd_mapping": "3.2.S.7 Stability; 3.2.P.8 Stability; 3.2.P.8.1-3",
        "regulatory_basis": "ICH Q1A(R2), ICH Q1B, ICH M4Q, MFDS stability requirements",
    },
    "compounds": {
        "label": "Compounds",
        "ctd_mapping": "3.2.S.1 General Information; 3.2.S.3 Characterisation; 3.2.P.4 Excipients; 3.2.P.5.5 Impurities",
        "regulatory_basis": "ICH M4Q, ICH Q3A/Q3B/Q3C/Q3D, ICH M7, USP/EP monographs",
    },
}


SECTION_HINTS = [
    (r"\b3\.2\.P\.2\b|pharmaceutical development|development studies|formulation development", "test_methods"),
    (r"\b3\.2\.P\.5\.5\b|characteri[sz]ation of impurities|유연물질|불순물", "compounds"),
    (r"\b3\.2\.P\.5\.3\b|validation of analytical|밸리데이션", "test_methods"),
    (r"\b3\.2\.P\.5\.2\b|analytical procedure|시험방법|분석법|정량법", "test_methods"),
    (r"\b3\.2\.P\.5\.1\b|\b3\.2\.P\.5\b(?!\.)|specification|acceptance criteria|기준\s*및\s*시험방법|규격", "specifications"),
    (r"\b3\.2\.P\.8\b|\b3\.2\.S\.7\b|stability|안정성|장기보존|가속", "stability"),
    (r"\b5\.3\.1\b|bioequivalence|comparative dissolution|생물학적\s*동등성|의약품\s*동등성|비교\s*용출", "bioequivalence"),
]


CATEGORY_RULES = {
    "specifications": {
        "strong": [
            r"\bAssay\b|함량|정량법|역가",
            r"acceptance criteria|specification|기준|규격|판정기준",
            r"\bNMT\b|\bNLT\b|not more than|not less than|이하|이상",
            r"95\.0\s*[-~–]\s*105\.0\s*%|[0-9.]+\s*[-~–]\s*[0-9.]+\s*%",
            r"related substances?|impurities?|유연물질|불순물|개개\s*불순물|총\s*불순물",
            r"identification|확인시험|dissolution\s*(?:test|specification)|용출\s*규격",
            r"content uniformity|uniformity|제제균일성|붕해|마손도|수분|\bpH\b\s*(?:specification|기준|[0-9.]+\s*[-~–]\s*[0-9.]+)|microbial|미생물",
        ],
        "context": [
            r"analytical procedure|test method|시험방법|분석법|\b(?:HPLC|UPLC|GC|ICP|UV)\b|Dissolution Tester",
            r"ICH Q6A|ICH Q2|ICH Q14|\b(?:USP|EP|KP)\b|공정서|별규",
        ],
        "negative": [
            r"comparative dissolution|비교\s*용출|f2|AUC|Cmax|90\s*%\s*CI|80\s*[-~]\s*125",
            r"dissolution\s+(?:test\s+)?condition|dissolution profile|performed in pH|formulation|selected|decided|discriminated",
            r"stability|안정성|장기보존|가속\s*시험|[0-9]+\s*(?:개월|month|months)|[0-9]+\s*(?:°C|℃)\s*/\s*[0-9]+\s*%\s*RH",
        ],
    },
    "test_methods": {
        "strong": [
            r"analytical method|analytical procedure|test method|시험방법|분석법|기시법",
            r"dissolution test condition|dissolution method|dissolution medium|용출\s*(?:조건|시험방법|방법)",
            r"\bpH\s*[0-9.]+|buffer|medium|rpm|paddle|basket|USP apparatus|sink condition",
            r"\b(?:HPLC|UPLC|GC|ICP[- ]?MS|UV|MS/MS)\b|chromatographic|chromatogram",
            r"column|mobile phase|flow rate|wavelength|detector|injection volume|run time",
            r"standard solution|sample solution|system suitability|검액|표준액|시스템적합성",
            r"method validation|validation|밸리데이션|specificity|accuracy|precision|linearity|range|robustness",
            r"method transfer|transfer|시험법\s*이전",
            r"(?:method|condition|medium|procedure|dissolution|용출|시험방법).{0,80}(?:selected|decided|optimized|discriminated|선정|설정|비교)",
            r"(?:selected|decided|optimized|discriminated|선정|설정|비교).{0,80}(?:method|condition|medium|procedure|dissolution|용출|시험방법)",
        ],
        "context": [
            r"3\.2\.P\.2|3\.2\.P\.5\.2|3\.2\.S\.4\.2|ICH Q2|ICH Q14|\b(?:USP|EP|KP)\b|공정서|별규",
        ],
        "negative": [
            r"기준\s*및\s*시험방법[^.;。]*(?:함량|표시량|이하|이상|%)",
            r"bioequivalence|의약품\s*동등성|생물학적\s*동등성|\bf2\b|AUC|Cmax|대조약|시험약",
        ],
    },
    "bioequivalence": {
        "strong": [
            r"bioequivalence|pharmaceutical equivalence|생물학적\s*동등성|생동성|의약품\s*동등성",
            r"comparative dissolution|비교\s*용출|용출\s*동등성|dissolution profile",
            r"\bf2\b|f2\s*(?:value|factor|값|인자)",
            r"\bAUC\b|\bCmax\b|\bTmax\b|90\s*%\s*CI|80\s*[-~]\s*125\s*%",
            r"reference product|test product|대조약|시험약",
        ],
        "context": [
            r"Module\s*5|5\.3\.1|biopharmaceutic|BE study|in vivo|in vitro dissolution",
            r"MFDS|식약처|의약품동등성시험기준",
        ],
        "negative": [
            r"Q\s*=\s*[0-9]+|NLT\s*[0-9.]+\s*%|용출\s*규격",
        ],
    },
    "stability": {
        "strong": [
            r"stability|안정성|장기보존|가속\s*시험|accelerated|long[- ]term|intermediate",
            r"[0-9]+\s*(?:month|months|개월)|shelf[- ]life|expiry|expiration|유효기간|사용기간",
            r"[0-9]+\s*(?:°C|℃)\s*/\s*[0-9]+\s*%\s*RH|[0-9]+\s*°?\s*C(?![A-Za-z])",
            r"container closure|packaging|포장|PTP|PVC|aluminium|aluminum|HDPE|병|블리스터",
            r"photostability|degradation product|분해산물|stability[- ]indicating",
        ],
        "context": [
            r"3\.2\.P\.8|3\.2\.S\.7|ICH Q1A|ICH Q1B|보관조건|저장방법",
        ],
        "negative": [],
    },
    "compounds": {
        "strong": [
            r"active pharmaceutical ingredient|API|drug substance|주성분|유효성분|원료의약품",
            r"excipient|첨가제|완제의약품|drug product",
            r"impurity|related substance|degradation product|residual solvent|elemental impurity|nitrosamine",
            r"유연물질|불순물|분해산물|잔류용매|금속불순물|니트로사민",
            r"CAS\s*(?:No\.?|number)?|molecular formula|분자식|structure|구조식|SMILES",
            r"acetaminophen|아세트아미노펜|telmisartan|텔미사르탄|mycophenolate|미코페놀",
        ],
        "context": [
            r"3\.2\.S\.1|3\.2\.S\.3|3\.2\.P\.4|3\.2\.P\.5\.5|ICH Q3|ICH M7|\b(?:USP|EP)\b|DMF",
        ],
        "negative": [],
    },
}


KNOWN_COMPOUNDS = {
    "mycophenolate mofetil": {
        "name": "Mycophenolate Mofetil",
        "smiles": "COC1=C(C=C2C(=C1)C(=O)OC2)C/C=C(\\C)/C(=O)OCCN1CCOCC1",
        "role": "API or related substance",
    },
    "mycophenolic acid": {
        "name": "Mycophenolic Acid",
        "smiles": "COC1=C(C=C2C(=C1)C(=O)OC2)C/C=C(\\C)/C(=O)O",
        "role": "active metabolite or related substance",
    },
    "acetaminophen": {
        "name": "Acetaminophen",
        "smiles": "CC(=O)NC1=CC=C(O)C=C1",
        "role": "API",
    },
    "아세트아미노펜": {
        "name": "Acetaminophen",
        "smiles": "CC(=O)NC1=CC=C(O)C=C1",
        "role": "API",
    },
    "타이레놀": {
        "name": "Acetaminophen",
        "smiles": "CC(=O)NC1=CC=C(O)C=C1",
        "role": "API or reference product",
    },
    "telmisartan": {
        "name": "Telmisartan",
        "smiles": "CCCC1=NC2=C(N1CC3=CC=C(C=C3)C4=CC=CC=C4C(=O)O)C=C(C=C2C)C5=NC6=CC=CC=C6N5C",
        "role": "API",
    },
    "텔미사르탄": {
        "name": "Telmisartan",
        "smiles": "CCCC1=NC2=C(N1CC3=CC=C(C=C3)C4=CC=CC=C4C(=O)O)C=C(C=C2C)C5=NC6=CC=CC=C6N5C",
        "role": "API",
    },
    "미코페놀레이트 모페틸": {
        "name": "Mycophenolate Mofetil",
        "smiles": "COC1=C(C=C2C(=C1)C(=O)OC2)C/C=C(\\C)/C(=O)OCCN1CCOCC1",
        "role": "API or related substance",
    },
    "미코페놀산": {
        "name": "Mycophenolic Acid",
        "smiles": "COC1=C(C=C2C(=C1)C(=O)OC2)C/C=C(\\C)/C(=O)O",
        "role": "active metabolite or related substance",
    },
}


def split_evidence_blocks(text: str) -> list[dict]:
    """Split extracted text into reviewable evidence blocks."""
    blocks = []
    current_section = "Unmapped"
    page = 1
    raw_parts = re.split(r"(\n?\s*---\s*PAGE\s+\d+\s*---\s*\n?)", text or "", flags=re.IGNORECASE)

    if len(raw_parts) > 1:
        chunks = []
        current_page = 1
        for part in raw_parts:
            page_match = re.search(r"PAGE\s+(\d+)", part, flags=re.IGNORECASE)
            if page_match:
                current_page = int(page_match.group(1))
                continue
            chunks.append((current_page, part))
    else:
        chunks = [(1, text or "")]

    for page, chunk in chunks:
        normalized = _merge_wrapped_lines(chunk)
        candidates = re.split(
            r"(?<=[.;。])\s+(?=(?:[A-Z가-힣0-9]|According|Eventually|The|If|For|When|This|These))"
            r"|(?=(?<!\d\.)(?<![A-Za-z]\.)\b\d+(?:\.\d+)*\.?\s+[A-Z가-힣])"
            r"|(?=•)"
            r"|(?=\s+-\s+)",
            normalized,
        )
        for candidate in candidates:
            block_text = re.sub(r"\s+", " ", candidate).strip(" -•\t")
            if len(block_text) < 8:
                continue
            section_hint = infer_section_hint(block_text) or current_section
            if section_hint != "Unmapped":
                current_section = section_hint
            if _is_boilerplate_block(block_text):
                continue
            if _is_low_information_block(block_text):
                continue
            blocks.append(
                {
                    "text": block_text[:900],
                    "page": page,
                    "section_hint": section_hint,
                    "evidence_type": "table-like row" if _looks_table_like(block_text) else "paragraph",
                }
            )
    return blocks


def detect_document_profile(text: str) -> dict:
    """Detect the CTD document profile so P.2 rationale is not treated as final P.5 evidence."""
    head = (text or "")[:5000]
    if re.search(r"\b3\.2\.P\.2\b|Pharmaceutical Development", head, flags=re.IGNORECASE):
        return {
            "document_type": "Pharmaceutical Development",
            "source_ctd_section": "3.2.P.2",
            "development_mode": True,
        }
    section_hits = []
    for pattern, label in [
        (r"\b3\.2\.P\.5\.1\b", "3.2.P.5.1 Specifications"),
        (r"\b3\.2\.P\.5\.2\b", "3.2.P.5.2 Analytical Procedures"),
        (r"\b3\.2\.P\.5\.3\b", "3.2.P.5.3 Validation"),
        (r"\b3\.2\.P\.5\.5\b", "3.2.P.5.5 Impurities"),
        (r"\b3\.2\.P\.8\b|\b3\.2\.S\.7\b", "3.2.P.8 / 3.2.S.7 Stability"),
        (r"\b5\.3\.1\b", "5.3.1 Biopharmaceutic Studies"),
    ]:
        if re.search(pattern, head, flags=re.IGNORECASE):
            section_hits.append(label)
    if len(section_hits) > 1:
        return {
            "document_type": "Mixed CTD Quality Evidence",
            "source_ctd_section": "; ".join(section_hits[:4]),
            "development_mode": False,
        }
    return {
        "document_type": "General CTD Evidence",
        "source_ctd_section": infer_section_hint(head) or "Unmapped",
        "development_mode": False,
    }


def classify_evidence_block(block: dict, document_profile: dict | None = None) -> list[dict]:
    """Classify one block into one or more document signal categories."""
    text = block["text"]
    if _is_low_information_block(text):
        return []
    results = []
    section_category = infer_section_category(block.get("section_hint", ""))
    document_profile = document_profile or {"source_ctd_section": "Unmapped", "development_mode": False}

    for category, rules in CATEGORY_RULES.items():
        strong = _matched_patterns(text, rules["strong"])
        context = _matched_patterns(text, rules["context"])
        negative = _matched_patterns(text, rules["negative"])

        if not strong and not context:
            continue

        score = len(strong) * 0.24 + len(context) * 0.11 - len(negative) * 0.12
        reasons = []
        if strong:
            reasons.append("matched core terms: " + ", ".join(strong[:5]))
        if context:
            reasons.append("matched regulatory/section context: " + ", ".join(context[:4]))
        if section_category == category:
            score += 0.22
            reasons.append("section heading supports this category")

        if category == "specifications" and _has_numeric_acceptance(text):
            score += 0.18
            reasons.append("numeric acceptance criterion detected")
        if category == "bioequivalence" and re.search(r"\bf2\b|AUC|Cmax|90\s*%\s*CI|대조약|시험약", text, re.IGNORECASE):
            score += 0.18
            reasons.append("BE-specific comparison metric detected")
        if category == "stability" and re.search(r"[0-9]+\s*(?:개월|month|months)|[0-9]+\s*(?:°C|℃)|[0-9]+\s*°?\s*C(?![A-Za-z])|RH|유효기간", text, re.IGNORECASE):
            score += 0.18
            reasons.append("stability time/condition evidence detected")

        if document_profile.get("development_mode") and category in {"specifications", "test_methods", "bioequivalence", "stability"}:
            score += 0.08
            reasons.append("3.2.P.2 development document: evidence treated as supporting rationale")

        if score >= 0.24:
            meta = CATEGORY_META[category]
            evidence_role = infer_evidence_role(category, text, document_profile)
            results.append(
                {
                    "Category": meta["label"],
                    "Evidence": text,
                    "Page": block["page"],
                    "Section Hint": block.get("section_hint", "Unmapped"),
                    "Source CTD Section": document_profile.get("source_ctd_section", "Unmapped"),
                    "CTD Mapping": meta["ctd_mapping"],
                    "Evidence Role": evidence_role,
                    "Regulatory Basis": meta["regulatory_basis"],
                    "Reason": "; ".join(reasons) or "rule-based classification",
                    "Matched Terms": ", ".join((strong + context)[:8]),
                    "Confidence": min(round(0.5 + score, 2), 0.98),
                    "Evidence Type": block.get("evidence_type", "paragraph"),
                }
            )
    return results


def classify_document_signals(text: str) -> dict:
    blocks = split_evidence_blocks(text)
    document_profile = detect_document_profile(text)
    signals = {key: [] for key in CATEGORY_META}
    for block in blocks:
        if not _has_regulatory_marker(block["text"]):
            continue
        for result in classify_evidence_block(block, document_profile):
            category_key = _category_key(result["Category"])
            if category_key:
                signals[category_key].append(result)

    for key, rows in signals.items():
        signals[key] = _dedupe_signal_rows(rows)
    return signals


def infer_evidence_role(category: str, text: str, document_profile: dict) -> str:
    development_mode = bool(document_profile.get("development_mode"))
    if not development_mode:
        return "Direct Evidence"
    if category == "specifications":
        return "Specification Rationale / Development Justification"
    if category == "test_methods":
        return "Method Development / Selection Rationale"
    if category == "bioequivalence":
        return "BE-Supporting Comparative Dissolution Evidence"
    if category == "stability":
        if re.search(r"packaging|container|PVC|PTP|alumin|HDPE|포장", text, flags=re.IGNORECASE):
            return "Packaging Stability Rationale"
        return "Stability-Supporting Development Rationale"
    if category == "compounds":
        return "Development Material Identity"
    return "Supporting Rationale"


def infer_section_hint(text: str) -> str | None:
    if re.search(r"\b3\.2\.P\.5\.2\b|analytical procedure", text, flags=re.IGNORECASE):
        return "3.2.P.5.2 Analytical Procedures"
    if re.search(r"\b3\.2\.P\.5\.3\b|validation of analytical", text, flags=re.IGNORECASE):
        return "3.2.P.5.3 Validation"
    if re.search(r"\b3\.2\.P\.5\.1\b|기준\s*및\s*시험방법|specifications?\b", text, flags=re.IGNORECASE):
        return "3.2.P.5.1 Specifications"
    for pattern, category in SECTION_HINTS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return CATEGORY_META[category]["ctd_mapping"].split(";")[0]
    return None


def infer_section_category(section_hint: str) -> str | None:
    section_hint = section_hint or ""
    if "Analytical Procedures" in section_hint or "Validation" in section_hint or "Pharmaceutical Development" in section_hint:
        return "test_methods"
    if "Impurities" in section_hint or "General Information" in section_hint:
        return "compounds"
    if "Bioequivalence" in section_hint:
        return "bioequivalence"
    if "Stability" in section_hint:
        return "stability"
    if "Specifications" in section_hint:
        return "specifications"
    for key, meta in CATEGORY_META.items():
        if section_hint and section_hint in meta["ctd_mapping"]:
            return key
    if "Control" in section_hint:
        return "specifications"
    return None


def _category_key(label: str) -> str | None:
    for key, meta in CATEGORY_META.items():
        if meta["label"] == label:
            return key
    return None


def _matched_patterns(text: str, patterns: list[str]) -> list[str]:
    matches = []
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            matches.append(match.group(0)[:60])
    return matches


def _has_numeric_acceptance(text: str) -> bool:
    return bool(
        re.search(
            r"[0-9.]+\s*[-~–]\s*[0-9.]+\s*%|[0-9.]+\s*%\s*(?:이하|이상)|(?:NMT|NLT|not more than|not less than)\s*[0-9.]+",
            text,
            flags=re.IGNORECASE,
        )
    )


def _looks_table_like(text: str) -> bool:
    return bool(re.search(r"\s{2,}|\t|\|", text)) or len(re.findall(r"[0-9.]+\s*%?", text)) >= 2


def _merge_wrapped_lines(chunk: str) -> str:
    """Repair PDF line wraps before evidence splitting."""
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in (chunk or "").splitlines()]
    paragraphs = []
    current = ""

    for line in lines:
        if not line:
            if current:
                paragraphs.append(current)
                current = ""
            continue
        if _is_boilerplate_block(line):
            continue

        if not current:
            current = line
            continue

        if _starts_new_logical_line(line) or _ends_sentence_or_table_row(current):
            paragraphs.append(current)
            current = line
        else:
            current = f"{current} {line}"

    if current:
        paragraphs.append(current)

    return "\n".join(paragraphs)


def _starts_new_logical_line(line: str) -> bool:
    return bool(
        re.match(r"^(?:\d+(?:\.\d+)*\.?|[A-Z]\.|[가-힣]\)|\(?\d+\)|Table\s+\d+|Figure\s+\d+|Part\s+[A-Z])\s+", line)
        or re.match(r"^(?:Tests?|Specification|Test Methods?|항목|기준|시험방법)\b", line, flags=re.IGNORECASE)
    )


def _ends_sentence_or_table_row(text: str) -> bool:
    if re.search(r"[.;。:]$", text):
        return True
    if _looks_table_like(text) and re.search(r"(?:%|ppm|USP<\d+>|이하|이상|Positive|Visual)$", text, flags=re.IGNORECASE):
        return True
    return False


def _is_low_information_block(text: str) -> bool:
    stripped = re.sub(r"\s+", " ", text or "").strip()
    if not stripped:
        return True
    if len(stripped) < 35 and not re.search(r"[0-9]|%|ppm|USP<|EP<|KP<|HPLC|UPLC|GC|함량|유연물질|불순물", stripped, flags=re.IGNORECASE):
        return True
    if re.search(r"(?:\(|\[|“|\"|')\s*$", stripped):
        return True
    if re.search(r"\b(?:pH|at|of|to|and|or|in|with|from|for|the|a|an)\s*$", stripped, flags=re.IGNORECASE):
        return True
    if re.search(r"^The specification of (?:IPC#?\d+|QC|Quality Control) refers to", stripped, flags=re.IGNORECASE):
        return True
    if re.search(r"(?:The )?Specification of (?:IPC#?\d+|QC|Quality Control) refers to", stripped, flags=re.IGNORECASE):
        return True
    if re.search(r"Request the test to Quality Control|Theoretical Yield|Production Yield|Product yield|Pan speed|drum mixer", stripped, flags=re.IGNORECASE):
        return True
    if re.search(r"^Mycophenolate mofetil\s*\(Myrept\).*3\.2\.P\.2", stripped, flags=re.IGNORECASE):
        return True
    return False


def _has_regulatory_marker(text: str) -> bool:
    return bool(
        re.search(
            r"3\.2\.|specification|assay|impurity|related substance|dissolution|bioequivalence|equivalence|"
            r"stability|shelf life|packaging|container|API|excipient|HPLC|UPLC|GC|ICP|validation|"
            r"method|pH|buffer|medium|rpm|paddle|reference product|test drug|test product|"
            r"기준|시험방법|기시법|분석법|함량|불순물|유연물질|용출|동등성|안정성|포장|"
            r"제품명|품목명|제형|투여경로|주성분|유효성분|원료약품|첨가제",
            text or "",
            flags=re.IGNORECASE,
        )
    )


def _is_boilerplate_block(text: str) -> bool:
    stripped = re.sub(r"\s+", " ", text or "").strip()
    if not stripped:
        return True
    boilerplate_patterns = [
        r"^Chong Kun Dang Pharm Confidential",
        r"^Page:\s*\d+\s*/\s*\d+$",
        r"^Mycophenolate mofetil\s*\(Myrept\)\s*500\s*mg\s*Tablet$",
        r"^3\.2\.P\.2_2\.0$",
        r"^(?:3\.)?2\.P\.2 Pharmaceutical Development(?: May 2016)?$",
        r"^CTD-Module 3\s*[-–]\s*Body of Data\s*/\s*Drug Product$",
        r"^(?:Test\s+Specifications?|Specifications?|Analytical\s+Procedures?|Test\s+Methods?)$",
        r"^Test Specifications Sample Time$",
    ]
    if any(re.search(pattern, stripped, flags=re.IGNORECASE) for pattern in boilerplate_patterns):
        return True
    if re.fullmatch(r"(?:3\.)?2\.P\.2\.\d+(?:\.\d+)?\s+[A-Za-z /-]{3,80}", stripped):
        return True
    return False


def _dedupe_signal_rows(rows: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for row in sorted(rows, key=lambda item: item["Confidence"], reverse=True):
        if _is_low_information_block(row.get("Evidence", "")):
            continue
        key = (row["Category"], row["Evidence"][:160], row["Page"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped
