"""Q6A/MFDS-oriented structure for specification and test method writing."""

from __future__ import annotations

import re


WRITING_STRUCTURE = [
    {
        "section": "1. Specification Definition",
        "mfds_heading": "기준 및 시험방법의 작성 범위",
        "q6a_principle": "Tests + analytical procedures + acceptance criteria",
        "ctd_anchor": "3.2.S.4 / 3.2.P.5",
        "categories": ["specifications", "test_methods"],
        "pattern": r"specification|acceptance criteria|기준|규격|시험방법|analytical procedure|test method",
        "reviewer_action": "Confirm that each proposed criterion is linked to a named test procedure and acceptance criterion.",
    },
    {
        "section": "2. Test Item Inventory",
        "mfds_heading": "성상, 확인시험, 순도시험, 정량법, 제제학적 시험",
        "q6a_principle": "Universal and product-specific tests should be selected based on product attributes.",
        "ctd_anchor": "3.2.S.4.1 / 3.2.P.5.1",
        "categories": ["specifications"],
        "pattern": r"appearance|description|identification|assay|purity|impurity|dissolution|disintegration|uniformity|성상|확인시험|순도시험|정량법|함량|용출|붕해|제제균일성",
        "reviewer_action": "Build the specification table by test item before judging acceptability.",
    },
    {
        "section": "3. Acceptance Criteria",
        "mfds_heading": "규격기준 및 허용기준 설정",
        "q6a_principle": "Acceptance criteria should be numerical limits, ranges, or other clear criteria.",
        "ctd_anchor": "3.2.S.4.1 / 3.2.P.5.1",
        "categories": ["specifications"],
        "pattern": r"NMT|NLT|not more than|not less than|[0-9.]+\s*[-~–]\s*[0-9.]+\s*%|이하|이상|범위|한도",
        "reviewer_action": "Check whether each limit is measurable, justified, and suitable for release/stability use.",
    },
    {
        "section": "4. Analytical Procedure",
        "mfds_heading": "시험방법 및 분석조건",
        "q6a_principle": "Specifications should reference the analytical procedures used to test conformance.",
        "ctd_anchor": "3.2.S.4.2 / 3.2.P.5.2",
        "categories": ["test_methods"],
        "pattern": r"HPLC|UPLC|GC|ICP|UV|column|mobile phase|flow rate|wavelength|dissolution method|pH|buffer|medium|rpm|paddle|분석법|시험방법|용출\s*조건|검액|표준액",
        "reviewer_action": "Separate method parameters from acceptance criteria so the method can be reviewed independently.",
    },
    {
        "section": "5. Method Validation",
        "mfds_heading": "시험방법 밸리데이션",
        "q6a_principle": "Analytical procedures should be suitable for their intended use.",
        "ctd_anchor": "3.2.S.4.3 / 3.2.P.5.3",
        "categories": ["test_methods"],
        "pattern": r"validation|specificity|accuracy|precision|linearity|range|robustness|LOD|LOQ|밸리데이션|특이성|정확성|정밀성|직선성|범위|검출한계|정량한계",
        "reviewer_action": "Confirm the validation package matches the type of test: identification, limit, quantitative impurity, or assay.",
    },
    {
        "section": "6. Justification of Specification",
        "mfds_heading": "기준 설정 근거자료",
        "q6a_principle": "Specifications are proposed and justified by the manufacturer and approved as conditions of approval.",
        "ctd_anchor": "3.2.S.4.5 / 3.2.P.5.6",
        "categories": ["specifications", "stability", "bioequivalence"],
        "pattern": r"justification|rationale|development|selected|decided|optimized|stability|batch|lot|clinical|safety|근거|타당성|실측|실측통계|안정성|안전성|유효성|설정",
        "reviewer_action": "Use P.2 data as rationale, then confirm that the final P.5 specification is explicitly proposed.",
    },
    {
        "section": "7. Batch Analysis / Test Results",
        "mfds_heading": "시험성적 및 로트 분석자료",
        "q6a_principle": "Criteria should be supported by manufacturing, development, and stability experience.",
        "ctd_anchor": "3.2.S.4.4 / 3.2.P.5.4",
        "categories": ["specifications", "compounds", "stability"],
        "pattern": r"batch|lot|certificate|test result|analysis result|manufacturing scale|로트|제조번호|시험성적|시험결과|실측치|실측통계|뱃치",
        "reviewer_action": "Check whether the extracted evidence includes actual lot results, not only narrative statements.",
    },
    {
        "section": "8. Impurity / Compound Control",
        "mfds_heading": "유연물질, 분해산물, 잔류용매, 금속불순물",
        "q6a_principle": "Impurity tests and limits should reflect safety, manufacturing, and stability knowledge.",
        "ctd_anchor": "3.2.S.3.2 / 3.2.P.5.5",
        "categories": ["compounds", "specifications"],
        "pattern": r"impurity|related substance|degradation product|residual solvent|elemental impurity|nitrosamine|유연물질|불순물|분해산물|잔류용매|금속불순물|니트로사민",
        "reviewer_action": "Map impurity identity, origin, analytical method, threshold, qualification, and control strategy.",
    },
    {
        "section": "9. Stability and Shelf-Life Link",
        "mfds_heading": "안정성 자료와 사용기간/저장방법",
        "q6a_principle": "Specifications should remain suitable through shelf life and storage conditions.",
        "ctd_anchor": "3.2.S.7 / 3.2.P.8",
        "categories": ["stability"],
        "pattern": r"stability|long[- ]term|accelerated|shelf[- ]life|expiry|container|packaging|안정성|장기보존|가속|사용기간|유효기간|보관|포장",
        "reviewer_action": "Tie stability trends, packaging, and storage conditions back to release and shelf-life criteria.",
    },
    {
        "section": "10. Compendial / External Standard",
        "mfds_heading": "공정서 및 별규 인용",
        "q6a_principle": "Compendial methods and acceptance criteria can support the control strategy when suitable.",
        "ctd_anchor": "USP / EP / KP / In-house Method",
        "categories": ["specifications", "test_methods"],
        "pattern": r"USP|EP|KP|pharmacopoeia|compendial|in-house|공정서|대한약전|별규|자사기준",
        "reviewer_action": "Identify whether the method is compendial, modified compendial, or in-house and confirm validation needs.",
    },
]


SPECIFICATION_TABLE_RULES = [
    {
        "test": "성상 / Appearance",
        "subtest": "-",
        "presence": r"Appearance|성상|White to slight yellow powder|흰색 또는 미황색",
        "criteria": [r"(White to slight yellow powder)", r"(흰색 또는 미황색의 분말)"],
        "method": [r"(Visual)", r"(육안으로 관찰)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1",
    },
    {
        "test": "확인시험 / Identification",
        "subtest": "IR",
        "presence": r"Identification|확인시험|IR|적외부",
        "criteria": [r"(표준품과 동일 파수)", r"(standard spectrum)", r"(Positive)"],
        "method": [r"(USP<197K>)", r"(적외부 스펙트럼측정법)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1",
    },
    {
        "test": "확인시험 / Identification",
        "subtest": "HPLC",
        "presence": r"Identification|확인시험|retention time|유지시간",
        "criteria": [r"(retention time[^.]{0,140}standard solution)", r"(표준품과 동일 유지시간)", r"(Positive)"],
        "method": [r"(USP<621>,?\s*Chromatography)", r"(액체크로마토그래프법)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1",
    },
    {
        "test": "중금속 / Heavy metals",
        "subtest": "-",
        "presence": r"Heavy metals|중금속",
        "criteria": [r"(Not more than 20 ppm)", r"(20 ppm 이하)"],
        "method": [r"(USP<231>,?\s*Method\s*Ⅱ?)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1",
    },
    {
        "test": "유연물질 / Related substances",
        "subtest": "개개 유연물질 / Individual impurity",
        "presence": r"Individual impurity|개개\s*유연물질|개개유연물질",
        "criteria": [r"(Not more than 1\.0\s*%)", r"(1\.0\s*% 이하)"],
        "method": [r"(USP<621>,?\s*Chromatography)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1; 3.2.S.4.2 / 3.2.P.5.2",
    },
    {
        "test": "유연물질 / Related substances",
        "subtest": "총 유연물질 / Total impurities",
        "presence": r"Total impurities|총\s*유연물질",
        "criteria": [r"(Not more than 2\.0\s*%)", r"(2\.0\s*% 이하)"],
        "method": [r"(USP<621>,?\s*Chromatography)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1; 3.2.S.4.2 / 3.2.P.5.2",
    },
    {
        "test": "건조감량 / Loss on drying",
        "subtest": "-",
        "presence": r"Loss (?:on|and) drying|건조감량",
        "criteria": [r"(Not more than\s+0\.5\s*%)", r"(0\.5\s*% 이하)"],
        "method": [r"(USP<731>)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1",
    },
    {
        "test": "강열잔분 / Residue on ignition",
        "subtest": "-",
        "presence": r"Residue on Ignition|강열잔분",
        "criteria": [r"(Not more than\s+0\.2\s*%)", r"(0\.2\s*% 이하)"],
        "method": [r"(USP<281>)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1",
    },
    {
        "test": "함량 / Assay",
        "subtest": "-",
        "presence": r"\bAssay\b|함량",
        "criteria": [r"(Not less than 97\.0\s*%)", r"(97\.0\s*% 이상)"],
        "method": [r"(USP<621>,?\s*Chromatography)", r"(UPLC)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1; 3.2.S.4.2 / 3.2.P.5.2",
    },
    {
        "test": "잔류용매 I / Residual solvents I",
        "subtest": "Methanol / 메탄올",
        "presence": r"Methanol|메탄올",
        "criteria": [r"(Not more than 3,000 ppm)", r"(3,000 ppm 이하)"],
        "method": [r"(USP<467>,?\s*Residual Solvents)", r"(Headspace method)", r"(GC Condition)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1; ICH Q3C",
    },
    {
        "test": "잔류용매 I / Residual solvents I",
        "subtest": "Dichloromethane / 디클로로메탄",
        "presence": r"Dichloromethane|디클로로메탄",
        "criteria": [r"(Not more than 600 ppm)", r"(600 ppm\s*이하)"],
        "method": [r"(USP<467>,?\s*Residual Solvents)", r"(Headspace method)", r"(GC Condition)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1; ICH Q3C",
    },
    {
        "test": "잔류용매 I / Residual solvents I",
        "subtest": "Isopropyl alcohol/ether / 이소프로필 알코올/에테르",
        "presence": r"Isopropyl alcohol|Isopropyl ether|이소프로필\s*(?:알코올|에테르)",
        "criteria": [r"(Not more than 5,000 ppm)", r"(5,000 ppm 이하)"],
        "method": [r"(USP<467>,?\s*Residual Solvents)", r"(Headspace method)", r"(GC Condition)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1; ICH Q3C",
        "note": "Check solvent naming consistency between the specification table and detailed method.",
    },
    {
        "test": "잔류용매 I / Residual solvents I",
        "subtest": "Ethyl acetate / 아세트산에틸",
        "presence": r"Ethyl acetate|아세트산\s*에틸|아세트산에틸",
        "criteria": [r"(Not more than 5,000 ppm)", r"(5,000 ppm 이하)"],
        "method": [r"(USP<467>,?\s*Residual Solvents)", r"(Headspace method)", r"(GC Condition)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1; ICH Q3C",
    },
    {
        "test": "잔류용매 I / Residual solvents I",
        "subtest": "Dimethylacetamide / 디메틸아세트아마이드",
        "presence": r"Dimethylacetamide|디메틸아세트아(?:마|미)이드",
        "criteria": [r"(Not more than 1,090 ppm)", r"(1,090 ppm 이하)"],
        "method": [r"(USP<467>,?\s*Residual Solvents)", r"(Headspace method)", r"(GC Condition)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1; ICH Q3C",
    },
    {
        "test": "잔류용매 II / Residual solvent II",
        "subtest": "Acetic acid / 아세트산",
        "presence": r"Acetic acid|아세트산",
        "criteria": [r"(Not more than 5,000 ppm)", r"(5,000 ppm 이하)"],
        "method": [r"(USP<621>,?\s*Chromatography)", r"(Capcellpak UG)"],
        "anchor": "3.2.S.4.1 / 3.2.P.5.1; ICH Q3C",
    },
]


def build_specification_writing_structure(summary: dict) -> list[dict]:
    """Build a writing-method matrix from extracted document signals."""
    signal_details = summary.get("signal_details") or {}
    profile = summary.get("document_profile") or {}
    rows = []

    for item in WRITING_STRUCTURE:
        evidence = _collect_matching_evidence(signal_details, item["categories"], item["pattern"])
        rows.append(
            {
                "Writing Section": item["section"],
                "MFDS Writing Heading": item["mfds_heading"],
                "Q6A Principle": item["q6a_principle"],
                "CTD Anchor": _adjust_ctd_anchor(item["ctd_anchor"], profile),
                "Evidence Status": "Detected" if evidence else "Needs source confirmation",
                "Extracted Evidence": _format_evidence(evidence),
                "Reviewer Action": item["reviewer_action"],
            }
        )
    return rows


def build_specification_outline(summary: dict) -> str:
    """Create a short reviewer-facing outline for writing specifications."""
    rows = build_specification_writing_structure(summary)
    detected = sum(1 for row in rows if row["Evidence Status"] == "Detected")
    profile = summary.get("document_profile") or {}
    source = profile.get("source_ctd_section", "Unmapped")
    mode = "supporting rationale" if profile.get("development_mode") else "direct evidence"
    return (
        f"Detected {detected}/{len(rows)} Q6A/MFDS writing sections from the current document. "
        f"Source section: {source}; interpretation mode: {mode}. "
        "Use this matrix to convert extracted signals into a clear criteria/test method/justification package."
    )


def build_specification_table(summary: dict, text: str) -> list[dict]:
    """Build a specification table in the CKD-506/MFDS style."""
    normalized = re.sub(r"\s+", " ", text or "")
    rows = []
    for rule in SPECIFICATION_TABLE_RULES:
        if not re.search(rule["presence"], normalized, flags=re.IGNORECASE):
            continue
        rows.append(
            {
                "No.": len(rows) + 1,
                "항목 / Test": rule["test"],
                "세부항목 / Sub-test": rule["subtest"],
                "기준 / Specification": _first_match(normalized, rule["criteria"]) or _evidence_fallback(summary, rule["presence"]),
                "시험방법 / Test Method": _first_match(normalized, rule["method"]) or "Confirm from detailed method section",
                "CTD Anchor": _adjust_ctd_anchor(rule["anchor"], summary.get("document_profile") or {}),
                "자료위치 / Source": _source_hint(summary, rule["presence"]),
                "검토메모 / Reviewer Note": rule.get(
                    "note",
                    "Verify against final approved specification and method validation package.",
                ),
            }
        )

    return _dedupe_specification_rows(rows)


def build_test_item_matrix(summary: dict) -> list[dict]:
    """Build a one-row-per-test matrix linking criteria and method-section details."""
    rows = []
    signal_details = summary.get("signal_details") or {}
    method_rows = _combined_method_rows(summary, signal_details)
    method_lookup = _method_lookup(method_rows)
    generic_method_details = method_lookup.get("기타 / Other", {})

    for item in summary.get("specification_table") or []:
        criteria = item.get("기준 / Specification", "")
        test_item = item.get("항목 / Test", "Unmapped")
        method_details = _merge_method_details(method_lookup.get(test_item, {}), generic_method_details)
        method = method_details.get("method", "")
        table_method = item.get("시험방법 / Test Method", "")
        if not method and table_method and table_method != "Confirm from detailed method section":
            method = table_method
            method_details["source"] = _append_evidence(
                method_details.get("source", ""),
                item.get("자료위치 / Source", "") or "Specification table",
            )
        status = _test_item_status(criteria, method)
        rows.append(
            {
                "시험항목 / Test Item": test_item,
                "세부항목 / Sub-test": item.get("세부항목 / Sub-test", "-"),
                "기준 / Acceptance Criteria": criteria,
                "기준 출처 / Specification Source": item.get("자료위치 / Source", ""),
                "시험방법 / Test Method": method,
                "표준액 농도 / Standard Solution": method_details.get("standard_solution", ""),
                "검액 농도 / Sample Solution": method_details.get("sample_solution", ""),
                "시험방법 출처 / Method Source": method_details.get("source", ""),
                "CTD 위치 / CTD Anchor": item.get("CTD Anchor", ""),
                "상태 / Status": status,
                "검토 포인트 / Reviewer Focus": _test_item_reviewer_focus(status, {**item, **method_details}),
            }
        )

    if rows:
        return _dedupe_test_item_rows(rows)

    spec_rows = signal_details.get("specifications", [])
    grouped: dict[str, dict] = {}

    for signal in spec_rows:
        evidence = signal.get("Evidence", "")
        key = _infer_test_item(evidence)
        grouped.setdefault(key, _empty_test_item_row(key))
        grouped[key]["기준 / Acceptance Criteria"] = _append_evidence(grouped[key]["기준 / Acceptance Criteria"], evidence)
        grouped[key]["기준 출처 / Specification Source"] = _append_evidence(
            grouped[key]["기준 출처 / Specification Source"],
            f"Page {signal.get('Page', 'N/A')} / {signal.get('Evidence Role', 'Direct Evidence')}",
        )
        grouped[key]["CTD 위치 / CTD Anchor"] = signal.get("CTD Mapping", grouped[key]["CTD 위치 / CTD Anchor"])

    for signal in method_rows:
        evidence = signal.get("Evidence", "")
        key = _infer_test_item(evidence)
        grouped.setdefault(key, _empty_test_item_row(key))
        details = _extract_method_details(evidence)
        grouped[key]["시험방법 / Test Method"] = _append_evidence(
            grouped[key]["시험방법 / Test Method"],
            details["method"] or evidence,
        )
        grouped[key]["표준액 농도 / Standard Solution"] = _append_evidence(
            grouped[key]["표준액 농도 / Standard Solution"],
            details["standard_solution"],
        )
        grouped[key]["검액 농도 / Sample Solution"] = _append_evidence(
            grouped[key]["검액 농도 / Sample Solution"],
            details["sample_solution"],
        )
        grouped[key]["시험방법 출처 / Method Source"] = _append_evidence(
            grouped[key]["시험방법 출처 / Method Source"],
            f"Page {signal.get('Page', 'N/A')} / {signal.get('Evidence Role', 'Direct Evidence')}",
        )
        grouped[key]["CTD 위치 / CTD Anchor"] = signal.get("CTD Mapping", grouped[key]["CTD 위치 / CTD Anchor"])

    for row in grouped.values():
        row["상태 / Status"] = _test_item_status(row["기준 / Acceptance Criteria"], row["시험방법 / Test Method"])
        row["검토 포인트 / Reviewer Focus"] = _test_item_reviewer_focus(row["상태 / Status"], row)
        rows.append(row)

    return _dedupe_test_item_rows(rows)


def _collect_matching_evidence(signal_details: dict, categories: list[str], pattern: str) -> list[dict]:
    matches = []
    for category in categories:
        for row in signal_details.get(category, []):
            evidence = row.get("Evidence", "")
            combined = " ".join(
                [
                    evidence,
                    row.get("Matched Terms", ""),
                    row.get("Reason", ""),
                    row.get("Evidence Role", ""),
                    row.get("CTD Mapping", ""),
                ]
            )
            if re.search(pattern, combined, flags=re.IGNORECASE):
                matches.append(row)
    return matches[:3]


def _first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return ""


def _evidence_fallback(summary: dict, pattern: str) -> str:
    signal_details = summary.get("signal_details") or {}
    for category in ("specifications", "test_methods"):
        for row in signal_details.get(category, []):
            evidence = row.get("Evidence", "")
            if re.search(pattern, evidence, flags=re.IGNORECASE):
                return re.sub(r"\s+", " ", evidence).strip()[:160]
    return "Confirm from source document"


def _source_hint(summary: dict, pattern: str) -> str:
    signal_details = summary.get("signal_details") or {}
    for category in ("specifications", "test_methods"):
        for row in signal_details.get(category, []):
            evidence = row.get("Evidence", "")
            if re.search(pattern, evidence, flags=re.IGNORECASE):
                return f"Page {row.get('Page', 'N/A')} / {row.get('Evidence Role', 'Direct Evidence')}"
    return "Specification table or detailed method section"


def _dedupe_specification_rows(rows: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for row in rows:
        key = (row["항목 / Test"], row["세부항목 / Sub-test"], row["기준 / Specification"])
        if key in seen:
            continue
        seen.add(key)
        row["No."] = len(deduped) + 1
        deduped.append(row)
    return deduped


def _dedupe_test_item_rows(rows: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for row in rows:
        key = (row.get("시험항목 / Test Item", ""), row.get("세부항목 / Sub-test", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _empty_test_item_row(test_item: str) -> dict:
    return {
        "시험항목 / Test Item": test_item,
        "세부항목 / Sub-test": "-",
        "기준 / Acceptance Criteria": "",
        "기준 출처 / Specification Source": "",
        "시험방법 / Test Method": "",
        "표준액 농도 / Standard Solution": "",
        "검액 농도 / Sample Solution": "",
        "시험방법 출처 / Method Source": "",
        "CTD 위치 / CTD Anchor": "",
        "상태 / Status": "Needs source confirmation",
        "검토 포인트 / Reviewer Focus": "",
    }


def _infer_test_item(evidence: str) -> str:
    checks = [
        (r"appearance|description|성상", "성상 / Appearance"),
        (r"identification|retention time|확인시험|유지시간|(?:\bIR\b|infrared|적외부)", "확인시험 / Identification"),
        (r"\bassay\b|content|함량|정량법", "함량 / Assay"),
        (r"related substance|impurit|유연물질|불순물", "유연물질 / Related substances"),
        (r"dissolution|용출", "용출 / Dissolution"),
        (r"content uniformity|uniformity|제제균일성|함량균일성", "제제균일성 / Uniformity"),
        (r"disintegration|붕해", "붕해 / Disintegration"),
        (r"loss on drying|water|moisture|건조감량|수분", "수분/건조감량 / Water or LOD"),
        (r"residual solvent|methanol|dichloromethane|ethyl acetate|잔류용매", "잔류용매 / Residual solvents"),
        (r"pH", "pH"),
        (r"sterility|무균", "무균 / Sterility"),
        (r"endotoxin|엔도톡신", "엔도톡신 / Endotoxin"),
        (r"heavy metals|elemental impurity|중금속|금속불순물", "금속불순물 / Elemental impurities"),
        (r"microbial|미생물", "미생물한도 / Microbial limits"),
    ]
    for pattern, label in checks:
        if re.search(pattern, evidence or "", flags=re.IGNORECASE):
            return label
    return "기타 / Other"


def _append_evidence(current: str, addition: str) -> str:
    addition = re.sub(r"\s+", " ", addition or "").strip()
    if not addition:
        return current
    addition = addition[:260]
    if not current:
        return addition
    if addition in current:
        return current
    return f"{current} | {addition}"


def _method_lookup(method_rows: list[dict]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for signal in method_rows:
        evidence = signal.get("Evidence", "")
        key = _infer_test_item(evidence)
        details = _extract_method_details(evidence)
        current = lookup.setdefault(
            key,
            {
                "method": "",
                "standard_solution": "",
                "sample_solution": "",
                "source": "",
            },
        )
        current["method"] = _append_evidence(current["method"], details["method"] or evidence)
        current["standard_solution"] = _append_evidence(current["standard_solution"], details["standard_solution"])
        current["sample_solution"] = _append_evidence(current["sample_solution"], details["sample_solution"])
        current["source"] = _append_evidence(
            current["source"],
            f"Page {signal.get('Page', 'N/A')} / {signal.get('Evidence Role', 'Direct Evidence')}",
        )
    return lookup


def _combined_method_rows(summary: dict, signal_details: dict) -> list[dict]:
    rows = list(signal_details.get("test_methods", []))
    seen = {row.get("Evidence", "") for row in rows}
    for evidence in summary.get("test_methods") or []:
        if evidence in seen:
            continue
        seen.add(evidence)
        rows.append(
            {
                "Evidence": evidence,
                "Page": "N/A",
                "Evidence Role": "Method Text",
                "CTD Mapping": "3.2.S.4.2 / 3.2.P.5.2 Analytical Procedures",
            }
        )
    return rows


def _merge_method_details(primary: dict[str, str], fallback: dict[str, str]) -> dict[str, str]:
    if not fallback:
        return primary
    if not primary:
        return fallback
    merged = dict(primary)
    for field in ("standard_solution", "sample_solution"):
        if not merged.get(field) and fallback.get(field):
            merged[field] = fallback[field]
            merged["source"] = _append_evidence(merged.get("source", ""), fallback.get("source", ""))
    return merged


def _extract_method_details(evidence: str) -> dict[str, str]:
    clean = re.sub(r"\s+", " ", evidence or "").strip()
    return {
        "method": _summarize_method(clean),
        "standard_solution": _extract_solution_concentration(clean, "standard"),
        "sample_solution": _extract_solution_concentration(clean, "sample"),
    }


def _summarize_method(text: str) -> str:
    matches = []
    checks = [
        r"USP<\d+[A-Z]?>,?\s*[^.;|]{0,60}",
        r"EP\s*\d+(?:\.\d+)*[^.;|]{0,60}",
        r"KP\s*[^.;|]{0,60}",
        r"\b(?:HPLC|UPLC|GC|LC-MS|ICP-MS|UV|Dissolution Tester)\b[^.;|]{0,120}",
        r"(?:액체크로마토그래프법|기체크로마토그래프법|자외가시부흡광도측정법|용출시험법)[^.;|]{0,80}",
        r"(?:column|mobile phase|flow rate|wavelength|medium|paddle|basket|rpm|injection volume)[^.;|]{0,90}",
        r"(?:칼럼|이동상|유량|파장|용출액|패들|회전수|주입량)[^.;|]{0,90}",
    ]
    for pattern in checks:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = re.sub(r"\s+", " ", match.group(0)).strip(" ;,")
            if value and value not in matches:
                matches.append(value)
    if matches:
        return " | ".join(matches[:3])
    return text[:260]


def _extract_solution_concentration(text: str, solution_type: str) -> str:
    if not text:
        return ""

    if solution_type == "standard":
        labels = r"standard solution|reference solution|standard sample|standard preparation|표준액|표준용액|표준품"
    else:
        labels = r"sample solution|test solution|sample preparation|검액|시험액|시료액|검체용액"

    units = r"(?:mg/mL|µg/mL|ug/mL|mcg/mL|ng/mL|mg/L|ppm|%|w/v|㎎/mL|㎍/mL)"
    concentration = rf"(?:about\s*)?\d+(?:\.\d+)?\s*(?:±\s*\d+(?:\.\d+)?\s*)?{units}"
    patterns = [
        rf"(?:{labels})[^.;:：]{{0,140}}?({concentration})",
        rf"({concentration})[^.;:：]{{0,80}}?(?:{labels})",
        rf"(?:concentration|농도)[^.;:：]{{0,80}}?({concentration})[^.;:：]{{0,80}}?(?:{labels})",
    ]
    matches = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = re.sub(r"\s+", " ", match.group(1)).strip()
            if value and value not in matches:
                matches.append(value)
    return " | ".join(matches[:2])


def _test_item_status(criteria: str, method: str) -> str:
    criteria_missing = not criteria or criteria == "Confirm from source document"
    method_missing = not method or method == "Confirm from detailed method section"
    if not criteria_missing and not method_missing:
        return "Linked"
    if criteria_missing and method_missing:
        return "Needs criteria and method"
    if criteria_missing:
        return "Needs criteria"
    return "Needs method"


def _test_item_reviewer_focus(status: str, row: dict) -> str:
    if status == "Linked":
        return "Confirm source page, validation package, and whether the criterion applies to release, stability, or both."
    if status == "Needs method":
        return "Acceptance criterion was found; confirm the detailed analytical procedure and validation reference."
    if status == "Needs criteria":
        return "Method evidence was found; confirm the proposed numerical or qualitative acceptance criterion."
    return "Confirm both the proposed acceptance criterion and the corresponding test method in the source CTD."


def _format_evidence(rows: list[dict]) -> str:
    if not rows:
        return "No direct evidence extracted yet."
    formatted = []
    for row in rows:
        page = row.get("Page", "N/A")
        role = row.get("Evidence Role", "Direct Evidence")
        evidence = re.sub(r"\s+", " ", row.get("Evidence", "")).strip()
        formatted.append(f"p.{page} [{role}] {evidence[:180]}")
    return " | ".join(formatted)


def _adjust_ctd_anchor(anchor: str, profile: dict) -> str:
    if profile.get("development_mode") and anchor in {"3.2.S.4.5 / 3.2.P.5.6", "3.2.S.4.2 / 3.2.P.5.2"}:
        return f"3.2.P.2 rationale -> final {anchor}"
    return anchor
