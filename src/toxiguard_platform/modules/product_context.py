"""Product, substance, and formulation context extracted from CTD documents."""

from __future__ import annotations

import re


DOSAGE_FORM_TERMS = {
    "tablet": "Tablet",
    "tablets": "Tablet",
    "정제": "Tablet",
    "필름코팅정": "Film-coated tablet",
    "필름 코팅정": "Film-coated tablet",
    "장방형 필름코팅정": "Film-coated tablet",
    "나정": "Tablet",
    "서방정": "Extended-release tablet",
    "정": "Tablet",
    "capsule": "Capsule",
    "capsules": "Capsule",
    "캡슐": "Capsule",
    "injection": "Injection",
    "injectable": "Injection",
    "주사": "Injection",
    "solution": "Solution",
    "suspension": "Suspension",
    "cream": "Cream",
    "ointment": "Ointment",
    "film-coated tablet": "Film-coated tablet",
}


ROUTE_BY_DOSAGE_FORM = {
    "Tablet": "Oral",
    "Film-coated tablet": "Oral",
    "Capsule": "Oral",
    "Solution": "Confirm from label",
    "Suspension": "Confirm from label",
    "Injection": "Parenteral",
    "Cream": "Topical",
    "Ointment": "Topical",
}


EXCIPIENT_TERMS = {
    "microcrystalline cellulose": "Filler / binder",
    "lactose": "Filler",
    "mannitol": "Filler",
    "starch": "Disintegrant / filler",
    "pregelatinized starch": "Binder / disintegrant",
    "povidone": "Binder",
    "crospovidone": "Disintegrant",
    "croscarmellose sodium": "Disintegrant",
    "sodium starch glycolate": "Disintegrant",
    "magnesium stearate": "Lubricant",
    "stearic acid": "Lubricant",
    "colloidal silicon dioxide": "Glidant",
    "silicon dioxide": "Glidant",
    "hypromellose": "Film former",
    "hpmc": "Film former",
    "titanium dioxide": "Colorant / opacifier",
    "polyethylene glycol": "Plasticizer",
    "talc": "Glidant / antiadherent",
    "sodium lauryl sulfate": "Surfactant",
    "luvitec": "Binder / matrix former",
    "미결정셀룰로오스": "Filler / binder",
    "유당": "Filler",
    "만니톨": "Filler",
    "전분": "Disintegrant / filler",
    "포비돈": "Binder",
    "크로스포비돈": "Disintegrant",
    "크로스카멜로오스나트륨": "Disintegrant",
    "스테아르산마그네슘": "Lubricant",
    "이산화규소": "Glidant",
    "히프로멜로오스": "Film former",
    "산화티탄": "Colorant / opacifier",
    "폴리에틸렌글리콜": "Plasticizer",
    "탈크": "Glidant / antiadherent",
}


def build_product_context(summary: dict, text: str) -> dict:
    """Build a cross-menu product context from extracted CTD evidence."""
    raw_text = _normalize_raw_text(text)
    clean_text = re.sub(r"\s+", " ", raw_text).strip()
    title = _extract_title_context(clean_text)
    active_name = _extract_active_name(raw_text, clean_text, summary, title)
    product_name = _extract_product_name(raw_text, clean_text, title)
    strength = _extract_strength(raw_text, clean_text, title)
    dosage_form = _extract_dosage_form(raw_text, clean_text, title)
    route = _extract_route(raw_text, clean_text, dosage_form)

    linked_substances = _linked_substances(summary, active_name)
    formulation = _formulation_records(clean_text, active_name, linked_substances)
    package_storage = _package_storage_records(summary, clean_text)

    basic_info = [
        _info_row("Product Name", product_name, "title / product-name pattern"),
        _info_row("Active Substance", active_name, "active ingredient / known compound pattern"),
        _info_row("Strength", strength, "strength pattern"),
        _info_row("Dosage Form", dosage_form, "dosage-form pattern"),
        _info_row("Route", route, "dosage-form route inference or route pattern"),
    ]
    basic_info = [row for row in basic_info if row["Value"]]

    return {
        "basic_info": basic_info,
        "linked_substances": linked_substances,
        "formulation": formulation,
        "package_storage": package_storage,
        "review_links": build_review_links(linked_substances, formulation, package_storage),
        "primary_substance": _primary_substance(linked_substances, active_name),
        "product_name": product_name,
        "active_substance": active_name,
        "strength": strength,
        "dosage_form": dosage_form,
        "route": route,
    }


def build_review_links(linked_substances: list[dict], formulation: list[dict], package_storage: list[dict]) -> list[dict]:
    """Describe how the extracted context feeds the other menus."""
    primary = linked_substances[0] if linked_substances else {}
    substance_label = primary.get("Name") or "extracted substance"
    return [
        {
            "Linked Menu": "Molecule Screening",
            "Input From Document": substance_label,
            "What To Confirm": "Run ICH M7 alert screening on the extracted API or impurity structure when a SMILES is available.",
        },
        {
            "Linked Menu": "Reference Impurity Lookup",
            "Input From Document": substance_label,
            "What To Confirm": "Check likely related substances, degradation products, and control strategy for the extracted active substance.",
        },
        {
            "Linked Menu": "QSAR Evidence Matrix",
            "Input From Document": primary.get("SMILES") or "SMILES needed",
            "What To Confirm": "Separate structural-alert evidence, known evidence, and reviewer interpretation.",
        },
        {
            "Linked Menu": "Degradation / Impurity Prediction",
            "Input From Document": primary.get("SMILES") or "parent structure needed",
            "What To Confirm": "Use the API/formulation context to judge whether predicted degradation pathways are plausible.",
        },
        {
            "Linked Menu": "FDA Review Worksheet",
            "Input From Document": f"{len(formulation)} formulation item(s), {len(package_storage)} packaging/stability item(s)",
            "What To Confirm": "Carry product, formulation, and package/storage context into CMC and deficiency review.",
        },
    ]


def context_table(context: dict, key: str) -> list[dict]:
    """Return one context table by stable key."""
    return (context or {}).get(key, []) or []


def primary_context_name(context: dict, fallback: str = "Acetaminophen") -> str:
    primary = (context or {}).get("primary_substance") or {}
    return primary.get("Name") or (context or {}).get("active_substance") or fallback


def primary_context_smiles(context: dict, fallback: str = "CC(=O)NC1=CC=C(O)C=C1") -> str:
    primary = (context or {}).get("primary_substance") or {}
    return primary.get("SMILES") or fallback


def substance_options(context: dict) -> list[dict]:
    return (context or {}).get("linked_substances") or []


def _extract_title_context(text: str) -> dict:
    title_text = _strip_repeating_pdf_headers(text)
    patterns = [
        r"([A-Z][A-Za-z0-9 /-]{2,80}?)\s*\(([^)]{2,80})\)\s*([0-9.,]+\s*(?:mg|mcg|µg|g|%))\s*([A-Za-z -]{3,30})",
        r"([A-Z][A-Za-z0-9 /-]{2,80}?)\s+([0-9.,]+\s*(?:mg|mcg|µg|g|%))\s+([A-Za-z -]{3,30})",
    ]
    for pattern in patterns:
        match = re.search(pattern, title_text, flags=re.IGNORECASE)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 4:
            return {
                "active": _clean_value(groups[0]),
                "product": _clean_value(groups[1]),
                "strength": _clean_value(groups[2]),
                "dosage_form": _normalize_dosage_form(groups[3]),
            }
        return {
            "active": "",
            "product": _clean_value(groups[0]),
            "strength": _clean_value(groups[1]),
            "dosage_form": _normalize_dosage_form(groups[2]),
        }
    return {}


def _strip_repeating_pdf_headers(text: str) -> str:
    cleaned = re.sub(r"\bChong\s+Kun\s+Dang\s+Pharm\s+Confidential\b\s*", "", text or "", flags=re.IGNORECASE)
    cleaned = re.sub(r"\bPage\s*:\s*\d+\s*/\s*\d+\b", " ", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _extract_product_name(raw_text: str, clean_text: str, title: dict) -> str:
    value = _extract_labeled_value(raw_text, ["Product Name", "제품명", "품목명", "Brand Name", "Trade Name"], max_len=90)
    if value:
        return _clean_product_name(value)
    for pattern in [
        r"(?:Product Name|제품명|품목명|Brand Name|Trade Name)\s*[:：]\s*([^.;]{2,90})",
    ]:
        match = re.search(pattern, clean_text, flags=re.IGNORECASE)
        if match:
            return _clean_product_name(match.group(1))
    return title.get("product", "")


def _extract_active_name(raw_text: str, clean_text: str, summary: dict, title: dict) -> str:
    value = _extract_labeled_value(
        raw_text,
        ["Active Ingredient", "Active Substance", "Drug Substance", "API", "주성분", "유효성분", "원료의약품"],
        max_len=100,
    )
    if value:
        candidate = _clean_ingredient_name(value)
        if _is_valid_ingredient_candidate(candidate):
            return candidate
    ingredient_value = _extract_ingredient_composition_active(raw_text)
    if _is_valid_ingredient_candidate(ingredient_value):
        return ingredient_value
    for pattern in [
        r"(?:Active Ingredient|Active Substance|Drug Substance|API|주성분|유효성분|원료의약품)\s*[:：]\s*([^.;]{2,100})",
        r"([A-Z][A-Za-z -]{3,80})\s+(?:is|was)\s+the\s+(?:active|drug substance)",
    ]:
        match = re.search(pattern, clean_text, flags=re.IGNORECASE)
        if match:
            candidate = _clean_ingredient_name(match.group(1))
            if _is_valid_ingredient_candidate(candidate):
                return candidate
    if _is_valid_ingredient_candidate(title.get("active", "")):
        return title["active"]
    compounds = summary.get("candidate_compounds") or []
    for compound in compounds:
        role = compound.get("role", "").lower()
        if "api" in role or "active" in role:
            return compound.get("name", "")
    return compounds[0].get("name", "") if compounds else ""


def _is_valid_ingredient_candidate(value: str) -> bool:
    clean = _clean_value(value)
    if not clean:
        return False
    if len(clean) < 3:
        return False
    if re.fullmatch(
        r"information|same|manufacturer|grade|function|component|components|ingredient|ingredients|active|drug product|drug substance|api",
        clean,
        flags=re.IGNORECASE,
    ):
        return False
    if re.search(r"^(?:information|manufacturer|grade|function)\b", clean, flags=re.IGNORECASE):
        return False
    if re.search(r"^Chong\s+Kun\s+Dang\s+Pharm\s+Confidential\b", clean, flags=re.IGNORECASE):
        return False
    return bool(re.search(r"[A-Za-z가-힣]", clean))


def _extract_strength(raw_text: str, clean_text: str, title: dict) -> str:
    value = _extract_labeled_value(raw_text, ["Strength", "함량", "분량"], max_len=60)
    if value:
        strength = _extract_strength_value(value)
        if strength:
            return strength
    for pattern in [
        r"(?:Strength|함량|분량)\s*[:：]\s*([0-9.,]+\s*(?:mg|밀리그램|mcg|µg|마이크로그램|g|%))",
        r"\b([0-9.,]+\s*(?:mg|밀리그램|mcg|µg|마이크로그램|g))\s*(?:Tablet|Capsule|Injection|정제|필름코팅정|캡슐|주사)",
        r"(?:1\s*정\s*중|1\s*capsule\s*contains)[^.;]{0,120}?([0-9.,]+\s*(?:mg|밀리그램|mcg|µg|마이크로그램|g))",
    ]:
        match = re.search(pattern, clean_text, flags=re.IGNORECASE)
        if match:
            return _normalize_strength(match.group(1))
    return title.get("strength", "")


def _extract_dosage_form(raw_text: str, clean_text: str, title: dict) -> str:
    value = _extract_labeled_value(raw_text, ["Dosage Form", "제형", "성상"], max_len=80)
    if value:
        dosage = _normalize_dosage_form(value)
        if dosage:
            return dosage
    for pattern in [
        r"(?:Dosage Form|제형|성상)\s*[:：]\s*([^.;]{2,80})",
        r"\b(Film-coated tablet|Tablet|Capsule|Injection|Solution|Suspension|Cream|Ointment)\b",
        r"(필름\s*코팅정|필름코팅정|서방정|장용정|정제|캡슐|주사제|액제|현탁제|크림제|연고제)",
    ]:
        match = re.search(pattern, clean_text, flags=re.IGNORECASE)
        if match:
            return _normalize_dosage_form(match.group(1))
    return title.get("dosage_form", "")


def _extract_route(raw_text: str, clean_text: str, dosage_form: str) -> str:
    value = _extract_labeled_value(raw_text, ["Route of Administration", "Route", "투여경로", "용법"], max_len=60)
    if value:
        route = _normalize_route(value)
        if route:
            return route
    for pattern in [
        r"(?:Route of Administration|Route|투여경로|용법)\s*[:：]\s*([^.;]{2,60})",
        r"\b(oral|intravenous|subcutaneous|intramuscular|topical|ophthalmic|nasal)\b",
        r"(경구|정맥|피하|근육|국소|점안|비강)",
    ]:
        match = re.search(pattern, clean_text, flags=re.IGNORECASE)
        if match:
            return _normalize_route(match.group(1))
    return ROUTE_BY_DOSAGE_FORM.get(dosage_form, "")


FIELD_STOP_LABELS = [
    "Product Name",
    "제품명",
    "품목명",
    "Brand Name",
    "Trade Name",
    "Active Ingredient",
    "Active Substance",
    "Drug Substance",
    "API",
    "주성분",
    "유효성분",
    "원료의약품",
    "원료약품 및 그 분량",
    "Strength",
    "함량",
    "분량",
    "Dosage Form",
    "제형",
    "성상",
    "Route of Administration",
    "Route",
    "투여경로",
    "용법",
    "기준",
    "시험방법",
    "저장방법",
    "포장",
]


def _normalize_raw_text(text: str) -> str:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"\n?\s*---\s*PAGE\s+\d+\s*---\s*\n?", "\n", normalized, flags=re.IGNORECASE)
    return normalized


def _extract_labeled_value(text: str, labels: list[str], max_len: int = 100) -> str:
    """Extract label/value pairs from colon, same-line, or next-line layouts."""
    lines = [_clean_value(line) for line in (text or "").splitlines()]
    lines = [line for line in lines if line and not re.search(r"^PAGE\s+\d+$", line, flags=re.IGNORECASE)]
    label_pattern = "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True))

    for index, line in enumerate(lines):
        colon_match = re.match(rf"^(?:{label_pattern})\s*[:：]\s*(.+)$", line, flags=re.IGNORECASE)
        if colon_match:
            return _limit_field_value(_trim_at_next_label(colon_match.group(1)), max_len)

        exact_match = re.fullmatch(rf"(?:{label_pattern})", line, flags=re.IGNORECASE)
        if exact_match:
            for next_line in lines[index + 1 : index + 5]:
                if _is_field_label(next_line):
                    continue
                return _limit_field_value(_trim_at_next_label(next_line), max_len)

        same_line_match = re.match(rf"^(?:{label_pattern})\s+(.+)$", line, flags=re.IGNORECASE)
        if same_line_match and not _is_field_label(same_line_match.group(1)):
            return _limit_field_value(_trim_at_next_label(same_line_match.group(1)), max_len)

    collapsed = re.sub(r"\s+", " ", text or "").strip()
    inline_match = re.search(rf"(?:{label_pattern})\s*[:：]\s*(.+)", collapsed, flags=re.IGNORECASE)
    if inline_match:
        return _limit_field_value(_trim_at_next_label(inline_match.group(1)), max_len)
    return ""


def _is_field_label(value: str) -> bool:
    return any(re.fullmatch(re.escape(label), value or "", flags=re.IGNORECASE) for label in FIELD_STOP_LABELS)


def _trim_at_next_label(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    stop_pattern = "|".join(re.escape(label) for label in sorted(FIELD_STOP_LABELS, key=len, reverse=True))
    match = re.search(rf"\s+(?:{stop_pattern})\s*[:：]?", text, flags=re.IGNORECASE)
    if match:
        text = text[: match.start()]
    return _clean_value(text)


def _limit_field_value(value: str, max_len: int) -> str:
    value = _clean_value(value)
    if len(value) <= max_len:
        return value
    return _clean_value(value[:max_len])


def _extract_ingredient_composition_active(text: str) -> str:
    lines = [_clean_value(line) for line in (text or "").splitlines()]
    for index, line in enumerate(lines):
        if not re.search(r"원료약품\s*및\s*그\s*분량|성분명|원료약품", line, flags=re.IGNORECASE):
            continue
        window = " ".join(lines[index + 1 : index + 6])
        for pattern in [
            r"(?:1\s*정\s*중|1\s*캡슐\s*중|1\s*vial\s*중|per\s+tablet|each\s+tablet\s+contains)\s*([A-Za-z가-힣][A-Za-z가-힣0-9 .,'()-]{2,80}?)\s+[0-9.,]+\s*(?:mg|밀리그램|mcg|µg|마이크로그램|g)",
            r"([A-Za-z가-힣][A-Za-z가-힣0-9 .,'()-]{2,80}?)\s+[0-9.,]+\s*(?:mg|밀리그램|mcg|µg|마이크로그램|g)",
        ]:
            match = re.search(pattern, window, flags=re.IGNORECASE)
            if match:
                return _clean_ingredient_name(match.group(1))
    return ""


def _extract_strength_value(value: str) -> str:
    match = re.search(r"([0-9.,]+\s*(?:mg|밀리그램|mcg|µg|마이크로그램|g|%))", value or "", flags=re.IGNORECASE)
    return _normalize_strength(match.group(1)) if match else ""


def _normalize_strength(value: str) -> str:
    text = _clean_value(value)
    text = re.sub(r"밀리그램", "mg", text, flags=re.IGNORECASE)
    text = re.sub(r"마이크로그램", "mcg", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text)


def _clean_product_name(value: str) -> str:
    value = _trim_at_next_label(value)
    return _clean_value(value)


def _clean_ingredient_name(value: str) -> str:
    value = _trim_at_next_label(value)
    value = re.sub(r"^(?:1\s*정\s*중|1\s*캡슐\s*중|per\s+tablet|each\s+tablet\s+contains)\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+[0-9.,]+\s*(?:mg|밀리그램|mcg|µg|마이크로그램|g|%)\b.*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\b(?:as|equivalent to)\b.*$", "", value, flags=re.IGNORECASE)
    return _clean_value(value)


def _normalize_route(value: str) -> str:
    clean = _trim_at_next_label(value)
    checks = [
        (r"oral|경구", "Oral"),
        (r"intravenous|정맥", "Intravenous"),
        (r"subcutaneous|피하", "Subcutaneous"),
        (r"intramuscular|근육", "Intramuscular"),
        (r"topical|국소", "Topical"),
        (r"ophthalmic|점안", "Ophthalmic"),
        (r"nasal|비강", "Nasal"),
    ]
    for pattern, route in checks:
        if re.search(pattern, clean, flags=re.IGNORECASE):
            return route
    return clean.title() if re.search(r"[A-Za-z]", clean) else clean


def _linked_substances(summary: dict, active_name: str) -> list[dict]:
    rows = []
    for compound in summary.get("candidate_compounds", []):
        name = compound.get("name", "")
        role = compound.get("role", "candidate")
        if active_name and _same_name(active_name, name):
            role = "Active substance / API"
        rows.append(
            {
                "Name": name,
                "Role": role,
                "SMILES": compound.get("smiles", ""),
                "Source": "Document Analyzer candidate compound",
                "Linked Review": "Molecule Screening / Reference Impurity Lookup",
            }
        )
    if active_name and not any(_same_name(active_name, row.get("Name", "")) for row in rows):
        rows.insert(
            0,
            {
                "Name": active_name,
                "Role": "Active substance / API",
                "SMILES": "",
                "Source": "Product context extraction",
                "Linked Review": "Compound identity confirmation needed before screening",
            },
        )
    return _dedupe_rows(rows, ["Name", "SMILES"])


def _formulation_records(text: str, active_name: str, linked_substances: list[dict]) -> list[dict]:
    records = []
    if active_name:
        records.append(
            {
                "Ingredient": active_name,
                "Role": "Active substance / API",
                "Evidence": "Inferred from product/active-substance context.",
                "Reviewer Check": "Confirm strength, salt form, and grade against 3.2.P.1 / 3.2.P.2.",
            }
        )
    for term, role in EXCIPIENT_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b" if re.fullmatch(r"[A-Za-z0-9 -]+", term) else re.escape(term), text, flags=re.IGNORECASE):
            records.append(
                {
                    "Ingredient": _display_term(term),
                    "Role": role,
                    "Evidence": _context_snippet(text, term),
                    "Reviewer Check": "Confirm amount, grade, function, compatibility, and regulatory acceptability.",
                }
            )
    for row in linked_substances:
        if row.get("Name") and row.get("Role") != "Active substance / API" and "related" in row.get("Role", "").lower():
            records.append(
                {
                    "Ingredient": row["Name"],
                    "Role": "Related substance / impurity context",
                    "Evidence": "Detected as compound evidence in the document.",
                    "Reviewer Check": "Do not treat as formulation ingredient unless confirmed in composition table.",
                }
            )
    return _dedupe_rows(records, ["Ingredient", "Role"])


def _package_storage_records(summary: dict, text: str) -> list[dict]:
    records = []
    package_terms = [
        r"PVC/알루미늄\s*PTP",
        r"polyvinyl chloride with hard aluminium",
        r"\bPVC\b",
        r"\bPTP\b",
        r"\bHDPE\b",
        r"aluminium|aluminum",
        r"blister|bottle|container closure|포장|블리스터|병",
    ]
    storage_terms = [
        r"[0-9]+\s*(?:°C|℃)\s*/\s*[0-9]+\s*%\s*RH",
        r"long[- ]term|accelerated|장기보존|가속\s*시험|보관조건|저장방법|shelf[- ]life|유효기간",
    ]
    for label, patterns in [("Packaging / Container Closure", package_terms), ("Storage / Stability Condition", storage_terms)]:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                records.append(
                    {
                        "Context Type": label,
                        "Extracted Value": _clean_value(match.group(0)),
                        "Evidence": _context_snippet(text, match.group(0)),
                        "Linked Review": "Stability / CMC Quality / FDA Review Worksheet",
                    }
                )
                break
    for row in (summary.get("signal_details") or {}).get("stability", [])[:2]:
        records.append(
            {
                "Context Type": "Stability Evidence",
                "Extracted Value": row.get("Evidence Role", "Stability evidence"),
                "Evidence": re.sub(r"\s+", " ", row.get("Evidence", ""))[:220],
                "Linked Review": "Stability / shelf-life justification",
            }
        )
    return _dedupe_rows(records, ["Context Type", "Extracted Value"])


def _primary_substance(linked_substances: list[dict], active_name: str) -> dict:
    if active_name:
        for row in linked_substances:
            if _same_name(active_name, row.get("Name", "")):
                return row
    for row in linked_substances:
        role = row.get("Role", "").lower()
        if "api" in role or "active" in role:
            return row
    return linked_substances[0] if linked_substances else {}


def _info_row(field: str, value: str, source: str) -> dict:
    return {
        "Field": field,
        "Value": value,
        "Source": source,
        "Reviewer Check": "Confirm against final submitted CTD source.",
    }


def _normalize_dosage_form(value: str) -> str:
    value = _clean_value(value).lower()
    for term, normalized in sorted(DOSAGE_FORM_TERMS.items(), key=lambda item: len(item[0]), reverse=True):
        if term in value:
            return normalized
    return _clean_value(value).title()


def _context_snippet(text: str, needle: str, radius: int = 130) -> str:
    match = re.search(re.escape(needle), text, flags=re.IGNORECASE)
    if not match:
        return ""
    start = max(match.start() - radius, 0)
    end = min(match.end() + radius, len(text))
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _same_name(left: str, right: str) -> bool:
    left_clean = re.sub(r"[^a-z0-9가-힣]+", "", (left or "").lower())
    right_clean = re.sub(r"[^a-z0-9가-힣]+", "", (right or "").lower())
    return bool(left_clean and right_clean and (left_clean in right_clean or right_clean in left_clean))


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" -:;,.")


def _display_term(term: str) -> str:
    return " ".join(part.capitalize() if part.islower() else part for part in term.split())


def _dedupe_rows(rows: list[dict], keys: list[str]) -> list[dict]:
    seen = set()
    deduped = []
    for row in rows:
        key = tuple(str(row.get(item, "")).lower() for item in keys)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped
