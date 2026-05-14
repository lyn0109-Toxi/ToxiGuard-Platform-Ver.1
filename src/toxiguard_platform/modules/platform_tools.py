"""ToxiGuard-platform tools adapted as menu-driven utilities."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re

import numpy as np
import pandas as pd

from toxiguard_platform.modules.tox_engine import RDKIT_AVAILABLE, assess_smiles


Chem = None
AllChem = None
RDKIT_REACTIONS_AVAILABLE = False
_RDKIT_REACTIONS_IMPORT_ATTEMPTED = False


KNOWN_IMPURITY_REFERENCES = {
    "acetaminophen": [
        {
            "Reference Impurity": "p-Aminophenol / 4-Aminophenol",
            "Impurity Chemical Name": "4-Aminophenol",
            "Likely Origin": "Raw material or degradation product",
            "Why It Matters": "Potential carryover from synthesis and known degradation-related concern",
            "Control Strategy": "Raw material control, release/stability method, degradation pathway justification",
            "Reference Basis": "USP/EP/JP monograph preferred; verify against submission-specific method.",
        },
        {
            "Reference Impurity": "4-Nitrophenol",
            "Impurity Chemical Name": "4-Nitrophenol",
            "Likely Origin": "Raw material or synthetic intermediate",
            "Why It Matters": "May indicate upstream material carryover or incomplete process clearance",
            "Control Strategy": "Supplier qualification, incoming material specification, purge assessment",
            "Reference Basis": "USP/EP monograph preferred; literature is supportive only.",
        },
    ],
    "telmisartan": [
        {
            "Reference Impurity": "Telmisartan related substance / process-related analog",
            "Impurity Chemical Name": "Route-specific telmisartan related compound",
            "Likely Origin": "Process impurity",
            "Why It Matters": "May arise from coupling, cyclization, or route-specific side reactions",
            "Control Strategy": "Route-specific impurity map, purge factor, batch trend review",
            "Reference Basis": "USP/EP monograph preferred; confirm exact identity with DMF or validated method.",
        },
        {
            "Reference Impurity": "Oxidative or stress degradation product",
            "Impurity Chemical Name": "Route-specific oxidative degradation product",
            "Likely Origin": "Degradation product",
            "Why It Matters": "May appear during forced degradation or long-term stability",
            "Control Strategy": "Forced degradation, stability-indicating method, shelf-life trend evaluation",
            "Reference Basis": "Confirm under validated stability protocol.",
        },
    ],
}


EXPERIMENTAL_EVIDENCE = {
    "c1ccc(N)cc1": {
        "CAS": "62-53-3",
        "Compound": "Aniline",
        "Result": "POSITIVE",
        "Study Type": "Ames mutagenicity assay",
        "Origin": "Representative public toxicology reference",
        "Reviewer Summary": "Aromatic amine concern; typically evaluated with metabolic activation context.",
    },
    "c1ccc(cc1)[N+](=O)[O-]": {
        "CAS": "98-95-3",
        "Compound": "Nitrobenzene",
        "Result": "POSITIVE",
        "Study Type": "Ames / nitro aromatic alert",
        "Origin": "Representative public toxicology reference",
        "Reviewer Summary": "Nitro aromatic concern; reductive activation can produce reactive intermediates.",
    },
    "CC(=O)NC1=CC=C(O)C=C1": {
        "CAS": "103-90-2",
        "Compound": "Acetaminophen",
        "Result": "NEGATIVE/LOW CONCERN",
        "Study Type": "Reference API context",
        "Origin": "Prototype evidence library",
        "Reviewer Summary": "No prototype structural alert for the API; impurity profile remains route-specific.",
    },
}


QSAR_REFERENCE_SOURCES = [
    {
        "Source": "ICH M7(R2)",
        "Reference Focus": "Two complementary QSAR methodologies for bacterial mutagenicity, one expert rule-based and one statistical-based, plus expert review where needed.",
        "Use in Matrix": "Checks whether the impurity package has both complementary QSAR outputs and a weight-of-evidence conclusion.",
        "URL": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/guidance-industry-m7r2-assessment-and-control-dna-reactive-mutagenic-impurities-pharmaceuticals",
    },
    {
        "Source": "FDA M7(R2) Q&A",
        "Reference Focus": "FDA implementation context for ICH M7(R2) mutagenic impurity assessment and control.",
        "Use in Matrix": "Supports reviewer interpretation, expert override, and documentation expectations.",
        "URL": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/questions-and-answers-m7r2-assessment-and-control-dna-reactive-mutagenic-impurities-pharmaceuticals",
    },
    {
        "Source": "OECD QAF 2nd edition",
        "Reference Focus": "Regulatory assessment framework for QSAR models, predictions, and multiple-prediction results.",
        "Use in Matrix": "Provides model/prediction checklist logic, including confidence in multiple QSAR predictions.",
        "URL": "https://www.oecd.org/en/publications/q-sar-assessment-framework-guidance-for-the-regulatory-assessment-of-quantitative-structure-activity-relationship-models-and-predictions-second-edition_bbdac345-en.html",
    },
    {
        "Source": "OECD QSAR validation principles",
        "Reference Focus": "Defined endpoint, unambiguous algorithm, applicability domain, robustness/predictivity, and mechanistic interpretation.",
        "Use in Matrix": "Maps each compound/model package to regulatory model-validation criteria.",
        "URL": "https://www.oecd.org/en/publications/q-sar-assessment-framework-guidance-for-the-regulatory-assessment-of-quantitative-structure-activity-relationship-models-and-predictions-second-edition_bbdac345-en.html",
    },
]


SIMILARITY_NEIGHBORS = {
    "c1ccc(N)cc1": [
        {"Neighbor": "2-Methylaniline", "Similarity": 0.88, "Result": "Positive", "Reference": "Representative aromatic amine set"},
        {"Neighbor": "o-Toluidine", "Similarity": 0.85, "Result": "Positive", "Reference": "Representative aromatic amine set"},
    ],
    "CCCC1=NC2=C(N1CC3=CC=C(C=C3)C4=CC=CC=C4C(=O)O)C=C(C=C2C)C5=NC6=CC=CC=C6N5C": [
        {"Neighbor": "Irbesartan", "Similarity": 0.72, "Result": "Negative", "Reference": "Sartan class analog context"},
        {"Neighbor": "Candesartan", "Similarity": 0.68, "Result": "Negative", "Reference": "Sartan class analog context"},
    ],
}


DEGRADATION_RULES = {
    "Ester Hydrolysis": "[CX3:1](=[OX1:2])[OX2:3][CX4:4]>>[CX3:1](=[OX1:2])[OX2:3].[OX2][CX4:4]",
    "Amide Hydrolysis": "[CX3:1](=[OX1:2])[NX3:3][CX4:4]>>[CX3:1](=[OX1:2])[OX2].[NX3:3][CX4:4]",
    "N-Oxidation": "[NX3:1]([CX4:2])([CX4:3])[CX4:4]>>[NX3+:1]([CX4:2])([CX4:3])([CX4:4])[O-]",
    "O-Dealkylation": "[OX2:1][CX4:2]>>[OX2:1].[CX4:2][OH]",
    "Nitro Reduction": "[N+:1](=[O:2])([O-:3])>>[NX3:1]([H])[H]",
}


VALIDATION_MOLECULES = [
    {"Name": "Aniline", "SMILES": "c1ccc(N)cc1", "Expected": "Alert"},
    {"Name": "Nitrobenzene", "SMILES": "c1ccc(cc1)[N+](=O)[O-]", "Expected": "Alert"},
    {"Name": "Ethylene Oxide", "SMILES": "C1OC1", "Expected": "Alert"},
    {"Name": "Acetaminophen", "SMILES": "CC(=O)NC1=CC=C(O)C=C1", "Expected": "Clean or low concern"},
]


DEFAULT_DISSOLUTION_PROFILE = pd.DataFrame(
    [
        {
            "Time (min)": 5,
            "Reference Mean (%)": 13.3,
            "Reference SD": 0.0,
            "Reference n": 12,
            "Test Mean (%)": 24.1,
            "Test SD": 0.0,
            "Test n": 12,
        },
        {
            "Time (min)": 10,
            "Reference Mean (%)": 46.2,
            "Reference SD": 0.0,
            "Reference n": 12,
            "Test Mean (%)": 46.5,
            "Test SD": 0.0,
            "Test n": 12,
        },
        {
            "Time (min)": 15,
            "Reference Mean (%)": 59.6,
            "Reference SD": 0.0,
            "Reference n": 12,
            "Test Mean (%)": 56.6,
            "Test SD": 0.0,
            "Test n": 12,
        },
        {
            "Time (min)": 30,
            "Reference Mean (%)": 72.1,
            "Reference SD": 0.0,
            "Reference n": 12,
            "Test Mean (%)": 68.7,
            "Test SD": 0.0,
            "Test n": 12,
        },
        {
            "Time (min)": 45,
            "Reference Mean (%)": 77.7,
            "Reference SD": 0.0,
            "Reference n": 12,
            "Test Mean (%)": 74.8,
            "Test SD": 0.0,
            "Test n": 12,
        },
        {
            "Time (min)": 60,
            "Reference Mean (%)": 81.0,
            "Reference SD": 0.0,
            "Reference n": 12,
            "Test Mean (%)": 79.0,
            "Test SD": 0.0,
            "Test n": 12,
        },
        {
            "Time (min)": 90,
            "Reference Mean (%)": 84.4,
            "Reference SD": 0.0,
            "Reference n": 12,
            "Test Mean (%)": 83.2,
            "Test SD": 0.0,
            "Test n": 12,
        },
        {
            "Time (min)": 120,
            "Reference Mean (%)": 85.9,
            "Reference SD": 0.0,
            "Reference n": 12,
            "Test Mean (%)": 84.2,
            "Test SD": 0.0,
            "Test n": 12,
        },
    ]
)


@dataclass
class ToolResult:
    title: str
    summary: str
    table: pd.DataFrame


@dataclass
class BioequivalenceResult:
    f2: float
    conclusion: str
    ci_low: float
    ci_high: float
    bootstrap_median: float
    bootstrap_p05: float
    bootstrap_p95: float
    probability_f2_ge_50: float
    bootstrap_runs: int
    cv_flag: str
    method_note: str
    fda_decision: str
    fda_risk: str
    fda_next_action: str


def assess_impurity_table(df: pd.DataFrame) -> pd.DataFrame:
    """Assess observed impurity results against proposed specifications."""
    rows = []
    if df is None or df.empty:
        return pd.DataFrame(rows)

    for _, row in df.iterrows():
        code = str(row.get("Impurity Code", "")).strip()
        if not code or code.lower() == "nan":
            continue

        observed = _to_float(row.get("Observed (%)"))
        limit = _to_float(row.get("Specification (%)"))
        origin = str(row.get("Origin", "")).strip() or "Unknown"
        concern = str(row.get("Concern", "")).strip() or "Not specified"

        if observed is None or limit is None:
            status = "Review needed"
            action = "Check numeric result and proposed limit format."
        elif observed <= limit:
            status = "Within specification"
            action = "Document as controlled and verify method suitability."
        else:
            status = "Above specification"
            action = "Investigate root cause, qualification threshold, and regulatory impact."

        rows.append(
            {
                "Impurity Code": code,
                "Chemical Name": str(row.get("Chemical Name", "")).strip(),
                "Origin": origin,
                "Observed (%)": observed,
                "Specification (%)": limit,
                "Concern": concern,
                "Status": status,
                "Reviewer Action": action,
            }
        )

    return pd.DataFrame(rows)


def build_pharmaceutical_equivalence_matrix(summary: dict, context: dict | None = None) -> pd.DataFrame:
    """Build a clean pharmaceutical-equivalence checklist without raw spec/method lists."""
    context = context or {}
    signal_details = summary.get("signal_details") or {}
    has_identity = bool(_context_value(context, "active_substance") or _first_context_substance(context))
    has_strength_form_route = any(
        _context_value(context, key) for key in ("strength", "dosage_form", "route")
    )

    rows = [
        _equivalence_row(
            "주성분 동일성 / API sameness",
            "Module 2.3 / 3.2.P.1 / 5.3",
            has_identity,
            "시험약과 대조약의 주성분, 염/수화물, 결정형, 등급 차이를 확인합니다.",
            "제품 정보와 대조약/시험약의 주성분 동일성을 확인합니다.",
            "Molecule Screening",
        ),
        _equivalence_row(
            "함량, 제형, 투여경로 동일성 / Strength, dosage form, route sameness",
            "3.2.P.1 / 1.12 / 5.3",
            has_strength_form_route,
            "동일 함량, 동일 제형, 동일 투여경로 여부를 확인합니다.",
            "동등성 판단 전 동일 함량, 동일 제형, 동일 투여경로 여부를 고정합니다.",
            "Pharmaceutical Equivalence Matrix",
        ),
        _equivalence_row(
            "시험약/대조약 설정 / Test-reference product definition",
            "Module 1 / Module 5",
            _has_signal(signal_details, ["bioequivalence"], r"reference product|test product|대조약|시험약|RLD|comparator"),
            "대조약, 시험약, 로트, 제조원, 함량, 사용 목적을 확인합니다.",
            "대조약과 시험약의 비교 단위가 명확해야 동등성 판단이 가능합니다.",
            "Document Analyzer",
        ),
        _equivalence_row(
            "조성 및 첨가제 비교 / Formulation comparability",
            "3.2.P.1 / 3.2.P.2",
            bool(context.get("formulation")),
            "주성분 외 첨가제, 기능, 양적 차이, 흡수/안정성 영향 가능성을 확인합니다.",
            "첨가제 차이가 용출, 안정성, 안전성 또는 흡수에 영향을 줄 수 있는지 확인합니다.",
            "Document Analyzer",
        ),
        _equivalence_row(
            "비교용출 / Comparative dissolution",
            "3.2.P.2 / 3.2.P.5 / 5.3",
            _has_signal(signal_details, ["bioequivalence", "test_methods"], r"comparative dissolution|dissolution profile|\bf2\b|비교용출|용출\s*동등성"),
            "비교용출 조건, 매질, 시간점, f2 또는 동등성 판정 결과를 확인합니다.",
            "기준 및 시험방법 상세값은 별도 매트릭스에서 보고, 여기서는 동등성 판단 항목만 확인합니다.",
            "Bioequivalence / Dissolution Tool",
        ),
        _equivalence_row(
            "생동성 또는 면제 근거 / BE or biowaiver evidence",
            "5.3.1 / 5.3.2",
            _has_signal(signal_details, ["bioequivalence"], r"bioequivalence|AUC|Cmax|90\s*%\s*CI|BCS|biowaiver|생동성|의약품\s*동등성|생물학적\s*동등성"),
            "AUC, Cmax, 90% CI, BCS biowaiver 또는 비교용출 기반 면제 여부를 확인합니다.",
            "AUC, Cmax, 90% CI 또는 면제/비교용출 근거를 구분합니다.",
            "Bioequivalence / Dissolution Tool",
        ),
        _equivalence_row(
            "불순물 프로파일 비교 / Impurity profile comparability",
            "3.2.P.5.5 / 3.2.P.8",
            _has_signal(signal_details, ["specifications", "compounds", "stability"], r"related substance|impurit|degradation|유연물질|불순물|분해산물"),
            "신규 불순물, 증가 불순물, 분해산물, 대조약과의 profile 차이를 확인합니다.",
            "시험약과 대조약의 불순물 profile 차이, 기준 초과, 신규 유연물질을 연결 평가합니다.",
            "Related Substances Evaluation",
        ),
        _equivalence_row(
            "유전독성 불순물 차이 / Genotoxic impurity delta",
            "3.2.P.5.5 / ICH M7",
            _has_signal(signal_details, ["compounds", "specifications"], r"nitrosamine|mutagen|genotoxic|structural alert|니트로사민|유전독성|변이원성"),
            "신규 GTI, nitrosamine, 구조 alert, TTC/AI 적용 가능성을 확인합니다.",
            "구조 경고, ICH M7 class, TTC/AI 기준 적용 가능성을 확인합니다.",
            "Genotoxicity Assessment",
        ),
        _equivalence_row(
            "안정성 브리징 / Stability bridging",
            "3.2.P.8",
            _has_signal(signal_details, ["stability"], r"stability|long[- ]term|accelerated|shelf[- ]life|expiry|안정성|장기보존|가속|유효기간"),
            "저장조건, 포장, 유효기간, 분해산물 증가가 동등성에 미치는 영향을 확인합니다.",
            "장기/가속 추세가 제안 유효기간과 저장조건을 뒷받침하는지 확인합니다.",
            "Stability Shelf-Life Prediction",
        ),
    ]
    return pd.DataFrame(rows)


def dissolution_profile_from_document_text(text: str) -> tuple[pd.DataFrame, float | None, str]:
    """Extract a comparative dissolution table when CTD text carries reference/test rows."""
    if not text:
        return pd.DataFrame(), None, ""

    lines = [line.strip() for line in text.splitlines()]
    candidates: list[tuple[int, pd.DataFrame, float | None, str]] = []
    for index, line in enumerate(lines):
        if not re_search(r"time\s*\(min(?:ute)?s?\)", line):
            continue

        compact_candidate = _compact_dissolution_candidate(lines, index)
        if compact_candidate is not None:
            candidates.append(compact_candidate)
            continue

        times: list[float] = []
        cursor = index + 1
        lookahead_limit = min(index + 35, len(lines))
        while cursor < lookahead_limit and not re_search(r"^f\s*\(?2\)?$", lines[cursor]):
            times.extend(_numbers_from_numeric_line(lines[cursor]))
            cursor += 1
        if cursor >= lookahead_limit or len(times) < 3:
            continue

        numeric_values: list[float] = []
        context_lines: list[str] = []
        for row_line in lines[cursor + 1 : min(cursor + 90, len(lines))]:
            if re_search(r"figure|ctd-module|---\s*page|dissolution factor|according\s+to", row_line):
                break
            context_lines.append(row_line)
            numeric_values.extend(_numbers_from_numeric_line(row_line))
            if len(numeric_values) >= (2 * len(times)) + 1:
                break

        required = len(times)
        if len(numeric_values) < required * 2:
            continue

        reference = numeric_values[:required]
        test = numeric_values[required : required * 2]
        reported_f2 = numeric_values[required * 2] if len(numeric_values) > required * 2 else None
        profile = pd.DataFrame(
            [
                {
                    "Time (min)": time,
                    "Reference Mean (%)": ref,
                    "Reference SD": 0.0,
                    "Reference n": 12,
                    "Test Mean (%)": tst,
                    "Test SD": 0.0,
                    "Test n": 12,
                }
                for time, ref, tst in zip(times, reference, test, strict=False)
            ]
        )
        source_hint = " ".join(context_lines[:8]).strip()
        candidates.append((index, profile, reported_f2, source_hint[:240]))

    if not candidates:
        return pd.DataFrame(), None, ""
    _, profile, reported_f2, source_hint = candidates[-1]
    return profile, reported_f2, source_hint


def _compact_dissolution_candidate(lines: list[str], index: int) -> tuple[int, pd.DataFrame, float | None, str] | None:
    """Parse one-line CTD dissolution tables with Reference/Test rows.

    Example:
    Time (minutes) 5 10 15 30 45 60 90 120 F(2)
    Reference 13.3 ... 85.9 67 Test Drug 24.1 ... 84.2
    """
    time_line = re.sub(r"F\s*\(?2\)?", "", lines[index], flags=re.IGNORECASE)
    times = _numbers_from_numeric_line(re.sub(r"(?i)time\s*\(min(?:ute)?s?\)", "", time_line))
    if len(times) < 3:
        return None

    window = " ".join(lines[index + 1 : min(index + 8, len(lines))])
    window = re.split(r"\b(?:Figure|Fig\.?|Table)\s+\d", window, maxsplit=1, flags=re.IGNORECASE)[0]
    reference_pos = window.lower().find("reference")
    if reference_pos < 0:
        return None
    compact_numbers = _numbers_from_dissolution_text(window[reference_pos:])
    if len(compact_numbers) < len(times) * 2:
        return None

    reference = compact_numbers[: len(times)]
    test = compact_numbers[-len(times) :]
    reported_f2 = None
    if len(compact_numbers) > len(times) * 2:
        possible_f2 = compact_numbers[len(times)]
        if 0 <= possible_f2 <= 100:
            reported_f2 = possible_f2
    profile = pd.DataFrame(
        [
            {
                "Time (min)": time,
                "Reference Mean (%)": ref,
                "Reference SD": 0.0,
                "Reference n": 12,
                "Test Mean (%)": tst,
                "Test SD": 0.0,
                "Test n": 12,
            }
            for time, ref, tst in zip(times, reference, test, strict=False)
        ]
    )
    return index, profile, reported_f2, window[:240]


def _numbers_from_dissolution_text(value: str) -> list[float]:
    numbers: list[float] = []
    for token in re.findall(r"[-+]?\d+(?:\.\d+)?", value):
        try:
            numbers.append(float(token))
        except ValueError:
            continue
    return numbers


def dissolution_profile_summary(profile_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize reference/test dissolution profile differences and variability."""
    df = _clean_dissolution_profile(profile_df)
    df["Difference (%)"] = df["Test Mean (%)"] - df["Reference Mean (%)"]
    df["Reference CV (%)"] = np.where(
        df["Reference Mean (%)"] > 0,
        df["Reference SD"] / df["Reference Mean (%)"] * 100,
        np.nan,
    )
    df["Test CV (%)"] = np.where(
        df["Test Mean (%)"] > 0,
        df["Test SD"] / df["Test Mean (%)"] * 100,
        np.nan,
    )
    return df.round(2)


def calculate_f2(profile_df: pd.DataFrame, bootstrap_runs: int = 2000, seed: int = 1729) -> BioequivalenceResult:
    """Calculate f2 similarity factor and bootstrap uncertainty for reference/test profiles."""
    df = _clean_dissolution_profile(profile_df)
    f2 = _f2_from_means(df["Reference Mean (%)"], df["Test Mean (%)"])
    cv_flag = _dissolution_cv_flag(df)
    bootstrap_stats = _python_bootstrap_f2(df, bootstrap_runs=bootstrap_runs, seed=seed)
    conclusion = "Similar dissolution profile" if f2 >= 50 else "Not similar by f2 criterion"
    fda_decision = (
        "Supports FDA-style comparative dissolution similarity rationale"
        if f2 >= 50
        else "Does not support FDA-style f2 similarity rationale"
    )
    fda_risk = "Low" if f2 >= 50 and cv_flag == "Acceptable" else "Review needed"
    fda_next_action = (
        "Verify reference product, USP/FDA dissolution method, media, apparatus, rpm, and sampling times before using this in a submission package."
        if f2 >= 50
        else "Review formulation, process, particle size/polymorph, dissolution method, or in vivo BE strategy before relying on comparative dissolution."
    )
    return BioequivalenceResult(
        f2=round(f2, 2),
        ci_low=round(bootstrap_stats["ci_low"], 2),
        ci_high=round(bootstrap_stats["ci_high"], 2),
        bootstrap_median=round(bootstrap_stats["median"], 2),
        bootstrap_p05=round(bootstrap_stats["p05"], 2),
        bootstrap_p95=round(bootstrap_stats["p95"], 2),
        probability_f2_ge_50=round(bootstrap_stats["probability_f2_ge_50"], 1),
        bootstrap_runs=int(bootstrap_runs),
        conclusion=conclusion,
        cv_flag=cv_flag,
        method_note="Python bootstrap uses the ToxiGuard-platform f2 formula and resamples each time point from entered mean, SD, and n.",
        fda_decision=fda_decision,
        fda_risk=fda_risk,
        fda_next_action=fda_next_action,
    )


def evaluate_related_substances(df: pd.DataFrame, material_type: str = "Drug product") -> pd.DataFrame:
    """Evaluate related substances with platform-style status and threshold context."""
    assessed = assess_impurity_table(df)
    if assessed.empty:
        return assessed

    threshold = 0.10 if material_type.lower().startswith("drug substance") else 0.20
    enhanced_rows = []
    for _, row in assessed.iterrows():
        observed = _to_float(row.get("Observed (%)"))
        limit = _to_float(row.get("Specification (%)"))
        usage = None if observed is None or limit in (None, 0) else round((observed / limit) * 100, 1)
        origin = str(row.get("Origin", "")).lower()
        origin_action = {
            "degradation product": "Link to forced degradation, stability trend, and stability-indicating method.",
            "raw material": "Check supplier qualification, incoming specification, and carryover control.",
            "unreacted starting material": "Confirm purge factor, process clearance, and residual starting material control.",
            "process impurity": "Assess process origin, purge strategy, and batch-to-batch trend.",
            "residual solvent": "Compare with ICH Q3C class limit and daily exposure.",
            "unknown impurity": "Identify structure and run genotoxicity assessment before accepting the limit.",
        }.get(origin, "Clarify origin and connect the control strategy to process, method, and stability data.")

        threshold_flag = "Below review threshold"
        if observed is None:
            threshold_flag = "Numeric result needed"
        elif observed >= threshold:
            threshold_flag = f"At/above prototype review threshold ({threshold:.2f}%)"

        enhanced_rows.append(
            {
                **row.to_dict(),
                "Spec Usage (%)": usage,
                "Q3A/B Threshold Context": threshold_flag,
                "Origin-Based Review": origin_action,
            }
        )
    return pd.DataFrame(enhanced_rows)


def build_related_substance_evidence_basis(
    df: pd.DataFrame,
    compound_name: str = "",
    material_type: str = "Drug product",
) -> pd.DataFrame:
    """Build a transparent evidence basis table for related-substance review."""
    assessed = evaluate_related_substances(df, material_type=material_type)
    rows = []
    if assessed.empty:
        return pd.DataFrame(rows)

    compound_refs = _reference_records_for(compound_name)
    for _, row in assessed.iterrows():
        code = str(row.get("Impurity Code", "")).strip()
        chemical_name = str(row.get("Chemical Name", "")).strip()
        origin = str(row.get("Origin", "")).strip()
        observed = row.get("Observed (%)")
        limit = row.get("Specification (%)")
        status = row.get("Status", "")
        compendial_basis = _compendial_basis(compound_refs, chemical_name, compound_name)
        threshold_basis = _impurity_threshold_basis(origin, material_type)
        method_basis = _method_basis_from_origin(origin)

        rows.extend(
            [
                {
                    "Impurity": code,
                    "Chemical Name": chemical_name,
                    "Evidence Layer": "Compendial / Public Standard",
                    "Basis Type": compendial_basis["type"],
                    "Source or Data": compendial_basis["source"],
                    "What It Supports": compendial_basis["supports"],
                    "Current Finding": status,
                    "Reviewer Confirmation Needed": compendial_basis["confirmation"],
                },
                {
                    "Impurity": code,
                    "Chemical Name": chemical_name,
                    "Evidence Layer": "ICH Qualification Threshold",
                    "Basis Type": threshold_basis["type"],
                    "Source or Data": threshold_basis["source"],
                    "What It Supports": threshold_basis["supports"],
                    "Current Finding": f"Observed {observed}; proposed limit {limit}; {row.get('Q3A/B Threshold Context', '')}",
                    "Reviewer Confirmation Needed": threshold_basis["confirmation"],
                },
                {
                    "Impurity": code,
                    "Chemical Name": chemical_name,
                    "Evidence Layer": "Analytical Method / CTD",
                    "Basis Type": method_basis["type"],
                    "Source or Data": method_basis["source"],
                    "What It Supports": method_basis["supports"],
                    "Current Finding": row.get("Origin-Based Review", ""),
                    "Reviewer Confirmation Needed": method_basis["confirmation"],
                },
                {
                    "Impurity": code,
                    "Chemical Name": chemical_name,
                    "Evidence Layer": "Stability / Degradation Link",
                    "Basis Type": "Stability-indicating evidence",
                    "Source or Data": _stability_basis_from_origin(origin),
                    "What It Supports": "Whether the impurity is process-related, degradation-related, or stability-forming.",
                    "Current Finding": origin or "Origin not specified",
                    "Reviewer Confirmation Needed": "Confirm forced degradation, long-term/accelerated trend, and shelf-life control strategy when relevant.",
                },
            ]
        )
    return pd.DataFrame(rows)


def assess_genotoxicity_table(df: pd.DataFrame) -> pd.DataFrame:
    """Assess impurity or degradant structures using the ToxiGuard ICH M7 engine."""
    rows = []
    if df is None or df.empty:
        return pd.DataFrame(rows)

    for _, row in df.iterrows():
        name = str(row.get("Compound", "") or row.get("Chemical Name", "") or row.get("Impurity Code", "")).strip()
        smiles = str(row.get("SMILES", "")).strip()
        role = str(row.get("Role", "") or row.get("Origin", "") or "Impurity").strip()
        statistical_result = _clean_optional(row.get("Statistical QSAR Result", ""))
        experimental_data = _clean_optional(row.get("Experimental / Literature Data", ""))
        if not name and not smiles:
            continue
        if not smiles or smiles.lower() == "nan":
            rows.append(
                {
                    "Compound": name or "Unnamed impurity",
                    "Role": role,
                    "SMILES": "",
                    "ICH M7 Class": "Unclassified",
                    "Risk Score": 0.0,
                    "Evidence Package": "Structure missing",
                    "Alerts": "SMILES needed",
                    "Reviewer Action": "Enter or confirm structure before ICH M7 assessment.",
                }
            )
            continue

        assessment = assess_smiles(smiles)
        alerts = ", ".join(alert["name"] for alert in assessment.alerts) or "None"
        evidence_package = _genotoxicity_evidence_package(assessment, statistical_result, experimental_data)
        qsar_status = _qsar_package_status(row, assessment)
        if assessment.ich_m7_class in {"Class 1", "Class 2", "Class 3"}:
            action = "Prepare expert review, exposure calculation, purge/control rationale, or Ames evidence."
        elif assessment.ich_m7_class == "Invalid":
            action = "Correct the SMILES before relying on the result."
        else:
            action = "Document negative/low-concern rationale and confirm model applicability domain."

        rows.append(
            {
                "Compound": name or assessment.smiles,
                "Role": role,
                "SMILES": assessment.smiles,
                "Valid Structure": assessment.valid_structure,
                "ICH M7 Class": assessment.ich_m7_class,
                "Risk Score": assessment.risk_score,
                "Evidence Package": evidence_package,
                "QSAR Package Status": qsar_status["status"],
                "QSAR Confidence": qsar_status["confidence"],
                "Alerts": alerts,
                "Reviewer Action": action,
            }
        )
    return pd.DataFrame(rows)


def build_qsar_model_validation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Build an ICH M7/OECD-style QSAR validation and concordance matrix."""
    rows = []
    if df is None or df.empty:
        return pd.DataFrame(rows)

    for _, row in df.iterrows():
        name = str(row.get("Compound", "") or row.get("Chemical Name", "") or row.get("Impurity Code", "")).strip() or "Unnamed impurity"
        smiles = str(row.get("SMILES", "")).strip()
        role = str(row.get("Role", "") or row.get("Origin", "") or "Impurity").strip()
        statistical_result = _clean_optional(row.get("Statistical QSAR Result", ""))
        experimental_data = _clean_optional(row.get("Experimental / Literature Data", ""))
        assessment = assess_smiles(smiles) if smiles and smiles.lower() != "nan" else None
        expert_prediction = _expert_prediction_from_assessment(assessment)
        statistical_prediction = _prediction_label(statistical_result)
        package_status = _qsar_package_status(row, assessment)

        rows.extend(
            [
                _qsar_validation_row(
                    name,
                    role,
                    "ICH M7 complementary methods",
                    "Expert rule-based and statistical-based QSAR are both expected for mutagenicity assessment.",
                    _has_expert_model(row, assessment) and bool(statistical_result),
                    f"Expert: {expert_prediction}; Statistical: {statistical_result or 'not provided'}",
                    package_status["status"],
                    "FDA/ICH M7(R2)",
                ),
                _qsar_validation_row(
                    name,
                    role,
                    "OECD 1 - Defined endpoint",
                    "Endpoint should be explicit, typically bacterial reverse mutation/Ames mutagenicity for ICH M7.",
                    bool(_endpoint(row)),
                    _endpoint(row) or "Endpoint not entered; assume Ames mutagenicity only if confirmed by model output.",
                    "Confirm endpoint is bacterial mutagenicity, not a broad genotoxicity label.",
                    "OECD QSAR validation principle 1",
                ),
                _qsar_validation_row(
                    name,
                    role,
                    "OECD 2 - Unambiguous algorithm",
                    "Model name, version, rule set or statistical method should be identifiable.",
                    bool(_model_identity(row, "expert") and _model_identity(row, "statistical")),
                    f"Expert model: {_model_identity(row, 'expert') or 'ToxiGuard prototype only'}; Statistical model: {_model_identity(row, 'statistical') or 'not provided'}",
                    "Add model name/version and whether the model is expert-rule or statistical.",
                    "OECD QSAR validation principle 2",
                ),
                _qsar_validation_row(
                    name,
                    role,
                    "OECD 3 - Applicability domain",
                    "Prediction reliability depends on whether the query structure is inside the model domain.",
                    bool(_applicability_domain(row, "expert") and _applicability_domain(row, "statistical")),
                    f"Expert AD: {_applicability_domain(row, 'expert') or 'not documented'}; Statistical AD: {_applicability_domain(row, 'statistical') or 'not documented'}",
                    "Document in-domain/out-of-domain status and nearest analogs for each model.",
                    "OECD QSAR validation principle 3",
                ),
                _qsar_validation_row(
                    name,
                    role,
                    "OECD 4 - Predictivity / robustness",
                    "Model performance or external validation evidence should support regulatory reliance.",
                    bool(_validation_metrics(row)),
                    _validation_metrics(row) or "No model validation metric or external predictivity note entered.",
                    "Add sensitivity/specificity, concordance, external validation, or vendor validation summary.",
                    "OECD QSAR validation principle 4",
                ),
                _qsar_validation_row(
                    name,
                    role,
                    "OECD 5 - Mechanistic interpretation",
                    "A mechanistic rationale is preferred, especially for alerts and expert overrides.",
                    bool(_mechanistic_rationale(row) or (assessment and assessment.alerts)),
                    _mechanistic_rationale(row) or _structural_concern_text(assessment.alerts if assessment else []),
                    "Explain alerting fragment, detoxifying feature, or why a model call is overridden.",
                    "OECD QSAR validation principle 5",
                ),
                _qsar_validation_row(
                    name,
                    role,
                    "Concordance and expert review",
                    "Concordant negative calls can support low mutagenic concern only when both models are valid and in-domain; positives/equivocals need follow-up.",
                    package_status["confidence"] in {"High", "Medium"},
                    _qsar_concordance_text(expert_prediction, statistical_prediction, experimental_data),
                    package_status["next_action"],
                    "ICH M7(R2) weight-of-evidence",
                ),
                _qsar_validation_row(
                    name,
                    role,
                    "Experimental / literature check",
                    "Direct Ames or relevant public/literature evidence can qualify QSAR predictions.",
                    bool(experimental_data or (assessment and assessment.experimental_reference)),
                    _experimental_finding(assessment, experimental_data) if assessment else experimental_data or "No experimental evidence linked.",
                    "Confirm study quality, strain panel, S9, dose range, purity, and relevance to the submitted impurity.",
                    "ICH M7(R2) / OECD QAF",
                ),
            ]
        )
    return pd.DataFrame(rows)


def qsar_reference_source_table() -> pd.DataFrame:
    """Return reference sources used by the QSAR validation matrix."""
    return pd.DataFrame(QSAR_REFERENCE_SOURCES)


def build_genotoxicity_evidence_basis(df: pd.DataFrame) -> pd.DataFrame:
    """Build layered evidence explaining why a genotoxicity conclusion was reached."""
    rows = []
    if df is None or df.empty:
        return pd.DataFrame(rows)

    for _, row in df.iterrows():
        name = str(row.get("Compound", "") or row.get("Chemical Name", "") or row.get("Impurity Code", "")).strip() or "Unnamed impurity"
        smiles = str(row.get("SMILES", "")).strip()
        role = str(row.get("Role", "") or row.get("Origin", "") or "Impurity").strip()
        statistical_result = _clean_optional(row.get("Statistical QSAR Result", ""))
        experimental_data = _clean_optional(row.get("Experimental / Literature Data", ""))

        if not smiles or smiles.lower() == "nan":
            rows.append(
                {
                    "Compound": name,
                    "Role": role,
                    "Evidence Layer": "Structure Readiness",
                    "Basis Type": "Structure missing",
                    "Source or Model": "SMILES not provided",
                    "Key Finding": "No structural screening can be justified until structure is confirmed.",
                    "Structural Concern": "Unknown",
                    "Reviewer Confirmation Needed": "Confirm identity, structure, salt/tautomer state, and impurity role.",
                }
            )
            continue

        assessment = assess_smiles(smiles)
        alert_rows = assessment.alerts or []
        structural_concern = _structural_concern_text(alert_rows)
        rows.append(
            {
                "Compound": name,
                "Role": role,
                "Evidence Layer": "Expert Rule-Based QSAR",
                "Basis Type": "Expert structural alert",
                "Source or Model": "ToxiGuard prototype alert library; ICH M7 structural-alert logic",
                "Key Finding": _expert_finding(assessment),
                "Structural Concern": structural_concern,
                "Reviewer Confirmation Needed": "Confirm with a qualified expert review and, for regulatory use, a validated expert-rule system or documented rationale.",
            }
        )
        rows.append(
            {
                "Compound": name,
                "Role": role,
                "Evidence Layer": "Statistical QSAR",
                "Basis Type": "Statistical model output",
                "Source or Model": statistical_result or "Not provided in prototype input",
                "Key Finding": _statistical_finding(statistical_result),
                "Structural Concern": "Depends on model applicability domain and nearest training analogs.",
                "Reviewer Confirmation Needed": "Add output from a validated statistical QSAR model, applicability-domain statement, and concordance/discordance explanation.",
            }
        )
        rows.append(
            {
                "Compound": name,
                "Role": role,
                "Evidence Layer": "Experimental / Literature Data",
                "Basis Type": "Ames or public/reference evidence",
                "Source or Model": _experimental_source(assessment, experimental_data),
                "Key Finding": _experimental_finding(assessment, experimental_data),
                "Structural Concern": "Experimental data can override or qualify structural alerts when directly relevant.",
                "Reviewer Confirmation Needed": "Confirm strain panel, S9 condition, purity, dose range, cytotoxicity, and GLP/study quality where available.",
            }
        )
        rows.append(
            {
                "Compound": name,
                "Role": role,
                "Evidence Layer": "ICH M7 Classification Logic",
                "Basis Type": "Weight-of-evidence classification",
                "Source or Model": "ICH M7 classes interpreted from expert alerts plus available evidence",
                "Key Finding": f"{assessment.ich_m7_class}; risk score {assessment.risk_score:.2f}. {assessment.conclusion}",
                "Structural Concern": structural_concern,
                "Reviewer Confirmation Needed": "If Class 3 or higher concern remains, justify AI/TTC limit, purge, control strategy, or confirmatory testing.",
            }
        )
    return pd.DataFrame(rows)


def predict_stability_shelf_life(
    long_term_df: pd.DataFrame,
    accelerated_df: pd.DataFrame | None,
    specification_limit: float,
) -> dict:
    """Predict shelf-life using a lightweight ICH Q1E-style regression workflow."""
    long_result = _fit_stability_condition(long_term_df, specification_limit, "Long-term", max_projection=60)
    accelerated_result = _fit_stability_condition(accelerated_df, specification_limit, "Accelerated", max_projection=12)

    metric_rows = []
    projections = {}
    for result in [long_result, accelerated_result]:
        if not result:
            continue
        metric_rows.append(
            {
                "Condition": result["condition"],
                "Data Points": result["n"],
                "Slope (%/month)": round(result["slope"], 5),
                "R²": round(result["r_squared"], 4),
                "95% UCI Cross Month": _format_month(result["shelf_life"]),
                "Status": result["status"],
            }
        )
        projections[result["condition"]] = result["projection"]

    interpretation = _stability_interpretation(long_result, accelerated_result, specification_limit)
    return {
        "metrics": pd.DataFrame(metric_rows),
        "projections": projections,
        "interpretation": interpretation,
    }


def get_impurity_references(compound_name: str) -> pd.DataFrame:
    key = compound_name.strip().lower()
    records = KNOWN_IMPURITY_REFERENCES.get(key)
    if not records:
        records = [
            {
                "Reference Impurity": f"{compound_name or 'Compound'} related substances",
                "Impurity Chemical Name": "To be confirmed",
                "Likely Origin": "To be confirmed",
                "Why It Matters": "Compound-specific impurity profile should be verified from authoritative references.",
                "Control Strategy": "Search compendial monograph, DMF, validated method, forced degradation, and literature.",
                "Reference Basis": "No verified prototype entry loaded for this compound.",
            }
        ]
    return pd.DataFrame(records)


def get_experimental_evidence(smiles: str) -> dict | None:
    clean = smiles.strip().replace("\n", "").replace("\r", "")
    return EXPERIMENTAL_EVIDENCE.get(clean)


def get_similarity_neighbors(smiles: str) -> pd.DataFrame:
    clean = smiles.strip().replace("\n", "").replace("\r", "")
    return pd.DataFrame(SIMILARITY_NEIGHBORS.get(clean, []))


def predict_degradation_products(smiles: str) -> pd.DataFrame:
    if not _load_rdkit_reactions():
        return pd.DataFrame(
            [
                {
                    "Pathway": "Unavailable",
                    "Predicted Product SMILES": "N/A",
                    "Reviewer Note": "RDKit reaction engine is not available.",
                }
            ]
        )

    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        return pd.DataFrame(
            [
                {
                    "Pathway": "Invalid structure",
                    "Predicted Product SMILES": "N/A",
                    "Reviewer Note": "Enter a valid SMILES string.",
                }
            ]
        )

    products = []
    seen = {Chem.MolToSmiles(mol)}
    for pathway, smarts in DEGRADATION_RULES.items():
        rxn = AllChem.ReactionFromSmarts(smarts)
        for outcome in rxn.RunReactants((mol,)):
            for product_mol in outcome:
                try:
                    Chem.SanitizeMol(product_mol)
                    product_smiles = Chem.MolToSmiles(product_mol)
                except Exception:
                    continue
                if product_smiles in seen:
                    continue
                seen.add(product_smiles)
                assessment = assess_smiles(product_smiles)
                products.append(
                    {
                        "Pathway": pathway,
                        "Predicted Product SMILES": product_smiles,
                        "ICH M7 Class": assessment.ich_m7_class,
                        "Risk Score": assessment.risk_score,
                        "Alerts": ", ".join(alert["name"] for alert in assessment.alerts) or "None",
                    }
                )

    if not products:
        products.append(
            {
                "Pathway": "No rule fired",
                "Predicted Product SMILES": "None",
                "ICH M7 Class": "N/A",
                "Risk Score": 0.0,
                "Alerts": "No degradation product predicted by prototype rules.",
            }
        )
    return pd.DataFrame(products)


def validate_engine() -> pd.DataFrame:
    rows = []
    for item in VALIDATION_MOLECULES:
        assessment = assess_smiles(item["SMILES"])
        found_alert = bool(assessment.alerts)
        expected_alert = item["Expected"] == "Alert"
        rows.append(
            {
                "Molecule": item["Name"],
                "SMILES": item["SMILES"],
                "Expected": item["Expected"],
                "Found Alerts": ", ".join(alert["name"] for alert in assessment.alerts) or "None",
                "ICH M7 Class": assessment.ich_m7_class,
                "Result": "PASS" if found_alert == expected_alert or item["Expected"] != "Alert" else "REVIEW",
            }
        )
    return pd.DataFrame(rows)


def build_evidence_matrix(smiles: str) -> pd.DataFrame:
    assessment = assess_smiles(smiles)
    rows = []
    for alert in assessment.alerts:
        rows.append(
            {
                "Model": "Expert rule-based",
                "Signal": alert["name"],
                "Priority": alert["priority"],
                "Mechanism": alert["mechanism"],
                "Reference": alert["reference"],
            }
        )

    evidence = get_experimental_evidence(smiles)
    if evidence:
        rows.append(
            {
                "Model": "Experimental evidence",
                "Signal": evidence["Result"],
                "Priority": "High relevance",
                "Mechanism": evidence["Reviewer Summary"],
                "Reference": evidence["Origin"],
            }
        )

    if not rows:
        rows.append(
            {
                "Model": "Expert rule-based",
                "Signal": "No prototype alert",
                "Priority": "Low",
                "Mechanism": assessment.conclusion,
                "Reference": "Prototype alert library",
            }
        )
    return pd.DataFrame(rows)


def _clean_dissolution_profile(profile_df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "Time (min)",
        "Reference Mean (%)",
        "Reference SD",
        "Reference n",
        "Test Mean (%)",
        "Test SD",
        "Test n",
    ]
    df = profile_df.copy() if profile_df is not None else pd.DataFrame()
    for column in required:
        if column not in df.columns:
            df[column] = np.nan
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["Time (min)", "Reference Mean (%)", "Test Mean (%)"])
    df = df.sort_values("Time (min)").reset_index(drop=True)
    if len(df) < 3:
        raise ValueError("At least three dissolution time points are required for f2.")
    return df[required]


def _f2_from_means(ref_values, test_values) -> float:
    ref = np.asarray(ref_values, dtype=float)
    test = np.asarray(test_values, dtype=float)
    if len(ref) != len(test) or len(ref) < 3:
        raise ValueError("Reference and test profiles must contain the same three or more time points.")
    mean_square_diff = np.mean((ref - test) ** 2)
    return float(50 * math.log10(100 / math.sqrt(1 + mean_square_diff)))


def _dissolution_cv_flag(df: pd.DataFrame) -> str:
    flags = []
    for _, row in df.iterrows():
        time_point = row["Time (min)"]
        for arm in ("Reference", "Test"):
            mean = row[f"{arm} Mean (%)"]
            sd = row[f"{arm} SD"]
            if mean and mean > 0 and not pd.isna(sd):
                cv = sd / mean * 100
                threshold = 20 if time_point <= 15 else 10
                if cv > threshold:
                    flags.append(f"{arm} CV {cv:.1f}% at {time_point:g} min")
    return "Acceptable" if not flags else "; ".join(flags)


def _python_bootstrap_f2(profile_df: pd.DataFrame, bootstrap_runs: int = 2000, seed: int = 1729) -> dict:
    rng = np.random.default_rng(seed)
    values = []
    runs = max(int(bootstrap_runs), 1)
    for _ in range(runs):
        ref_draw = []
        test_draw = []
        for _, row in profile_df.iterrows():
            ref_n = max(int(row.get("Reference n", 12) or 12), 1)
            test_n = max(int(row.get("Test n", 12) or 12), 1)
            ref_sd = max(float(row.get("Reference SD", 0) or 0), 0)
            test_sd = max(float(row.get("Test SD", 0) or 0), 0)
            ref_draw.append(rng.normal(row["Reference Mean (%)"], ref_sd, ref_n).mean())
            test_draw.append(rng.normal(row["Test Mean (%)"], test_sd, test_n).mean())
        values.append(_f2_from_means(ref_draw, test_draw))
    arr = np.asarray(values, dtype=float)
    return {
        "ci_low": float(np.percentile(arr, 2.5)),
        "ci_high": float(np.percentile(arr, 97.5)),
        "median": float(np.percentile(arr, 50)),
        "p05": float(np.percentile(arr, 5)),
        "p95": float(np.percentile(arr, 95)),
        "probability_f2_ge_50": float(np.mean(arr >= 50) * 100),
    }


def _numbers_from_numeric_line(value: str) -> list[float]:
    clean = value.strip()
    if not clean or not re.fullmatch(r"[\d.\s+-]+", clean):
        return []
    numbers = []
    for token in re.findall(r"[-+]?\d+(?:\.\d+)?", clean):
        try:
            numbers.append(float(token))
        except ValueError:
            continue
    return numbers


def _load_rdkit_reactions() -> bool:
    global Chem, AllChem, RDKIT_REACTIONS_AVAILABLE, _RDKIT_REACTIONS_IMPORT_ATTEMPTED
    if RDKIT_REACTIONS_AVAILABLE:
        return True
    if _RDKIT_REACTIONS_IMPORT_ATTEMPTED:
        return False
    _RDKIT_REACTIONS_IMPORT_ATTEMPTED = True
    try:
        from rdkit import Chem as rdkit_chem
        from rdkit.Chem import AllChem as rdkit_all_chem
    except Exception:
        Chem = None
        AllChem = None
        RDKIT_REACTIONS_AVAILABLE = False
        return False
    Chem = rdkit_chem
    AllChem = rdkit_all_chem
    RDKIT_REACTIONS_AVAILABLE = True
    return True


def _equivalence_row(item: str, anchor: str, found: bool, scope: str, review_focus: str, linked_tool: str) -> dict:
    return {
        "동등성 항목 / Equivalence Item": item,
        "검토 범위 / Review Scope": scope,
        "CTD 위치 / CTD Anchor": anchor,
        "상태 / Status": "Evidence found" if found else "Needs source confirmation",
        "연결 도구 / Linked Tool": linked_tool,
        "검토 포인트 / Reviewer Focus": review_focus,
    }


def _has_signal(signal_details: dict, categories: list[str], pattern: str) -> bool:
    return bool(_signal_evidence(signal_details, categories, pattern))


def _signal_evidence(signal_details: dict, categories: list[str], pattern: str) -> str:
    matches = []
    for category in categories:
        for row in signal_details.get(category, []):
            evidence = str(row.get("Evidence", "")).strip()
            if re_search(pattern, evidence):
                matches.append(f"p.{row.get('Page', 'N/A')} {evidence[:180]}")
    return " | ".join(matches[:3])


def _context_value(context: dict, key: str) -> str:
    value = context.get(key)
    if value:
        return str(value)
    target = key.replace("_", " ").lower()
    for row in context.get("basic_info") or []:
        field = str(row.get("Field", "")).lower()
        if target in field:
            return str(row.get("Value", "")).strip()
    return ""


def _first_context_substance(context: dict) -> str:
    substances = context.get("linked_substances") or []
    if not substances:
        return ""
    first = substances[0]
    return str(first.get("Name") or first.get("Substance") or first.get("Compound") or "").strip()


def _count_context(context: dict, key: str) -> str:
    rows = context.get(key) or []
    return f"{len(rows)} extracted item(s)" if rows else ""


def _evidence_text(evidence) -> str:
    if evidence is None:
        return ""
    if isinstance(evidence, str):
        return evidence.strip()
    return str(evidence).strip()


def re_search(pattern: str, value: str) -> bool:
    return bool(re.search(pattern, value or "", flags=re.IGNORECASE))


def _reference_records_for(compound_name: str) -> list[dict]:
    key = (compound_name or "").strip().lower()
    return KNOWN_IMPURITY_REFERENCES.get(key, [])


def _compendial_basis(compound_refs: list[dict], chemical_name: str, compound_name: str) -> dict:
    matched = _match_reference_record(compound_refs, chemical_name)
    if matched:
        return {
            "type": "Loaded compendial/public reference candidate",
            "source": matched.get("Reference Basis", "USP/EP/JP monograph or verified public reference preferred."),
            "supports": (
                f"{matched.get('Reference Impurity', 'Reference impurity')} - "
                f"{matched.get('Likely Origin', 'origin to be confirmed')}; "
                f"{matched.get('Why It Matters', 'risk relevance to be confirmed')}"
            ),
            "confirmation": "Verify exact monograph, impurity identity, acceptance criterion, and whether the submitted method modifies compendial conditions.",
        }

    if compound_refs:
        available = "; ".join(record.get("Reference Impurity", "") for record in compound_refs if record.get("Reference Impurity"))
        return {
            "type": "Compound reference available, impurity not matched",
            "source": f"Prototype has reference candidates for {compound_name or 'the API'}: {available}",
            "supports": "Use as a search lead only; this specific impurity still needs exact identity confirmation.",
            "confirmation": "Search USP, EP, KP/JP, DMF, approved monograph, and validated method package for this exact impurity.",
        }

    return {
        "type": "No loaded pharmacopeial match",
        "source": "No USP/EP/KP/JP monograph entry is loaded in this prototype for the entered compound/impurity.",
        "supports": "The current assessment relies on submitted specification, observed result, origin, and ICH threshold logic until a monograph is verified.",
        "confirmation": "Confirm whether a USP, EP, KP, JP, in-house, or submitted CTD method is the controlling standard.",
    }


def _match_reference_record(records: list[dict], chemical_name: str) -> dict | None:
    if not records or not chemical_name:
        return None
    normalized = _normalize_token_text(chemical_name)
    for record in records:
        haystack = _normalize_token_text(
            " ".join(
                str(record.get(field, ""))
                for field in ("Reference Impurity", "Impurity Chemical Name", "Likely Origin", "Why It Matters")
            )
        )
        words = [word for word in re.split(r"\s+", normalized) if len(word) >= 4]
        if normalized and normalized in haystack:
            return record
        if words and any(word in haystack for word in words[:4]):
            return record
    return None


def _normalize_token_text(value: str) -> str:
    return re.sub(r"[^a-z0-9가-힣]+", " ", str(value or "").lower()).strip()


def _impurity_threshold_basis(origin: str, material_type: str) -> dict:
    lowered = (origin or "").lower()
    if "residual solvent" in lowered or "solvent" in lowered or "용매" in lowered:
        return {
            "type": "ICH Q3C residual solvent limit",
            "source": "ICH Q3C class/PDE logic; compendial residual solvent procedures may also apply.",
            "supports": "Whether a residual solvent level is acceptable by class-specific exposure limits.",
            "confirmation": "Confirm solvent class, PDE calculation, daily dose, and whether USP<467>/EP 2.4.24 or submitted GC method applies.",
        }
    if "elemental" in lowered or "metal" in lowered or "금속" in lowered:
        return {
            "type": "ICH Q3D elemental impurity limit",
            "source": "ICH Q3D PDE and route-specific permitted daily exposure logic.",
            "supports": "Whether elemental impurity control is needed and which exposure limit applies.",
            "confirmation": "Confirm route, daily dose, risk assessment, and validated ICP method.",
        }
    if material_type.lower().startswith("drug substance"):
        source = "ICH Q3A drug-substance impurity identification/qualification threshold logic."
    else:
        source = "ICH Q3B drug-product degradation product identification/qualification threshold logic."
    return {
        "type": "ICH Q3A/Q3B organic impurity threshold",
        "source": source,
        "supports": "Whether the observed level and proposed limit require identification, qualification, or tighter control.",
        "confirmation": "Confirm maximum daily dose, reporting/identification/qualification thresholds, and product-specific justification.",
    }


def _method_basis_from_origin(origin: str) -> dict:
    lowered = (origin or "").lower()
    if "residual solvent" in lowered or "solvent" in lowered:
        return {
            "type": "GC / headspace method basis",
            "source": "USP<467>/EP residual solvent method or submitted validated GC method.",
            "supports": "Specificity and quantitation of volatile impurities.",
            "confirmation": "Confirm standard solution, sample solution, system suitability, validation, and class-specific limit.",
        }
    return {
        "type": "Stability-indicating chromatographic method",
        "source": "USP/EP/KP monograph if applicable, otherwise submitted CTD 3.2.P.5.2 analytical procedure.",
        "supports": "Whether impurity peaks are separated, identified, quantified, and controlled at the proposed limit.",
        "confirmation": "Confirm specificity, relative response factor, LOQ, peak purity, system suitability, and validation package.",
    }


def _stability_basis_from_origin(origin: str) -> str:
    lowered = (origin or "").lower()
    if "degradation" in lowered or "분해" in lowered:
        return "Degradation-product origin was entered; link to forced degradation and P.8 stability trend."
    if "process" in lowered or "starting" in lowered or "raw material" in lowered:
        return "Process-related origin was entered; link to route, purge, batch trend, and release control."
    return "Origin not definitive; use stability and batch data to confirm whether the impurity grows over shelf life."


def _clean_optional(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "not provided", "n/a"}:
        return ""
    return text


def _endpoint(row) -> str:
    return _clean_optional(row.get("Endpoint", ""))


def _model_identity(row, kind: str) -> str:
    if kind == "expert":
        return _clean_optional(row.get("Expert Rule-Based Model", "")) or _clean_optional(row.get("Expert Model", ""))
    return _clean_optional(row.get("Statistical Model", "")) or _clean_optional(row.get("Statistical QSAR Model", ""))


def _applicability_domain(row, kind: str) -> str:
    if kind == "expert":
        return _clean_optional(row.get("Expert Applicability Domain", "")) or _clean_optional(row.get("Expert AD", ""))
    return _clean_optional(row.get("Statistical Applicability Domain", "")) or _clean_optional(row.get("Statistical AD", ""))


def _validation_metrics(row) -> str:
    return (
        _clean_optional(row.get("Validation Metrics / External Predictivity", ""))
        or _clean_optional(row.get("Model Validation Evidence", ""))
        or _clean_optional(row.get("External Validation", ""))
    )


def _mechanistic_rationale(row) -> str:
    return (
        _clean_optional(row.get("Mechanistic Rationale", ""))
        or _clean_optional(row.get("Alert Rationale", ""))
        or _clean_optional(row.get("Expert Rationale", ""))
    )


def _has_expert_model(row, assessment) -> bool:
    return bool(_model_identity(row, "expert") or (assessment and assessment.valid_structure))


def _expert_prediction_from_assessment(assessment) -> str:
    if not assessment:
        return "not assessable"
    if not assessment.valid_structure:
        return "invalid structure"
    if assessment.alerts:
        return "positive alert"
    return "negative/no alert"


def _prediction_label(text: str) -> str:
    normalized = (text or "").lower()
    if not normalized:
        return "not provided"
    if re.search(r"negative|non[- ]?mutagen|no alert|clean", normalized):
        return "negative"
    if re.search(r"equivocal|indeterminate|inconclusive", normalized):
        return "equivocal"
    if re.search(r"positive|alert|mutagenic|class\s*[123]|out\s*of\s*domain", normalized):
        return "positive/equivocal"
    return "provided"


def _qsar_package_status(row, assessment) -> dict:
    statistical_result = _clean_optional(row.get("Statistical QSAR Result", ""))
    experimental_data = _clean_optional(row.get("Experimental / Literature Data", ""))
    expert_ad = _applicability_domain(row, "expert")
    statistical_ad = _applicability_domain(row, "statistical")
    validation_metrics = _validation_metrics(row)
    mechanistic = _mechanistic_rationale(row)
    expert_prediction = _expert_prediction_from_assessment(assessment)
    statistical_prediction = _prediction_label(statistical_result)

    if not assessment or not assessment.valid_structure:
        return {
            "status": "Structure not ready",
            "confidence": "Low",
            "next_action": "Confirm identity, SMILES, salt/tautomer state, and impurity role before QSAR reliance.",
        }
    if not statistical_result:
        return {
            "status": "Incomplete QSAR package",
            "confidence": "Low",
            "next_action": "Add a validated statistical QSAR prediction with applicability-domain statement.",
        }
    if not (expert_ad and statistical_ad):
        return {
            "status": "Domain documentation gap",
            "confidence": "Low",
            "next_action": "Document applicability domain and nearest analog rationale for both QSAR calls.",
        }
    if "positive" in expert_prediction or statistical_prediction in {"positive/equivocal", "equivocal"}:
        confidence = "Medium" if validation_metrics and (mechanistic or experimental_data) else "Low"
        return {
            "status": "Alert requires expert review",
            "confidence": confidence,
            "next_action": "Resolve positive/equivocal call with expert review, Ames evidence, TTC/AI calculation, purge, or control strategy.",
        }
    if statistical_prediction == "negative":
        confidence = "High" if validation_metrics and mechanistic else "Medium"
        return {
            "status": "Two-method negative package",
            "confidence": confidence,
            "next_action": "Document concordant negative calls, in-domain status, model validation, and expert review sign-off.",
        }
    return {
        "status": "Manual interpretation needed",
        "confidence": "Low",
        "next_action": "Clarify statistical model result and document expert review of concordance/discordance.",
    }


def _qsar_validation_row(
    compound: str,
    role: str,
    criterion: str,
    expectation: str,
    passed: bool,
    current_evidence: str,
    reviewer_action: str,
    reference_source: str,
) -> dict:
    return {
        "Compound": compound,
        "Role": role,
        "Validation Criterion": criterion,
        "Regulatory Expectation": expectation,
        "Status": "Adequate" if passed else "Gap",
        "Current Evidence": current_evidence,
        "Reviewer Action": reviewer_action,
        "Reference Source": reference_source,
    }


def _qsar_concordance_text(expert_prediction: str, statistical_prediction: str, experimental_data: str) -> str:
    base = f"Expert rule-based: {expert_prediction}; Statistical: {statistical_prediction}."
    if experimental_data:
        base += f" Experimental/literature: {experimental_data}."
    if expert_prediction.startswith("negative") and statistical_prediction == "negative":
        return base + " Concordant negative package may support non-mutagenic rationale if both models are valid and in-domain."
    if "positive" in expert_prediction or statistical_prediction in {"positive/equivocal", "equivocal"}:
        return base + " Positive/equivocal evidence requires expert review or confirmatory evidence."
    return base + " Concordance cannot be concluded from the current inputs."


def _genotoxicity_evidence_package(assessment, statistical_result: str, experimental_data: str) -> str:
    layers = ["expert rule"]
    if statistical_result:
        layers.append("statistical QSAR")
    else:
        layers.append("statistical QSAR missing")
    if experimental_data or assessment.experimental_reference:
        layers.append("experimental/literature")
    else:
        layers.append("experimental data missing")
    return " + ".join(layers)


def _structural_concern_text(alert_rows: list[dict]) -> str:
    if not alert_rows:
        return "No prototype structural alert detected."
    parts = []
    for alert in alert_rows:
        parts.append(
            f"{alert.get('name', 'Alert')}: {alert.get('mechanism', 'mechanism to be confirmed')} "
            f"[{alert.get('reference', 'reference not specified')}]"
        )
    return " | ".join(parts)


def _expert_finding(assessment) -> str:
    if not assessment.valid_structure:
        return "Structure could not be parsed; expert alert result is invalid."
    if assessment.alerts:
        return f"{len(assessment.alerts)} expert structural alert(s) detected."
    return "No expert structural alert detected by the prototype rule set."


def _statistical_finding(statistical_result: str) -> str:
    if not statistical_result:
        return "No statistical QSAR output was entered; current conclusion is not a two-method ICH M7 package."
    return f"User-provided statistical QSAR result: {statistical_result}"


def _experimental_source(assessment, experimental_data: str) -> str:
    if experimental_data:
        return experimental_data
    if assessment.experimental_reference:
        ref = assessment.experimental_reference
        return f"{ref.get('name', 'Reference compound')} - {ref.get('result', 'result not specified')}"
    return "No direct experimental record loaded or entered."


def _experimental_finding(assessment, experimental_data: str) -> str:
    if experimental_data:
        return f"User-provided data should be reviewed for relevance and study quality: {experimental_data}"
    if assessment.experimental_reference:
        ref = assessment.experimental_reference
        return f"{ref.get('result', 'Result')}: {ref.get('basis', 'basis to be confirmed')}"
    return "No Ames, in vivo, or directly relevant public/literature evidence has been linked yet."


def _fit_stability_condition(df: pd.DataFrame | None, spec_limit: float, condition: str, max_projection: int) -> dict | None:
    if df is None or df.empty:
        return None
    clean = df.copy()
    clean.iloc[:, 0] = pd.to_numeric(clean.iloc[:, 0], errors="coerce")
    clean.iloc[:, 1] = pd.to_numeric(clean.iloc[:, 1], errors="coerce")
    clean = clean.dropna()
    if len(clean) < 3:
        return None

    x = clean.iloc[:, 0].to_numpy(dtype=float)
    y = clean.iloc[:, 1].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 if ss_tot == 0 else max(0.0, 1 - ss_res / ss_tot)

    x_pred = np.linspace(0, max(float(np.max(x)) * 2, max_projection), 240)
    y_pred = slope * x_pred + intercept
    dof = max(len(x) - 2, 1)
    residual_std = np.sqrt(ss_res / dof) if dof else 0.0
    x_mean = np.mean(x)
    denom = np.sum((x - x_mean) ** 2)
    leverage = 1 / len(x) + ((x_pred - x_mean) ** 2 / denom if denom else 0)
    y_upper = y_pred + _t95(dof) * residual_std * np.sqrt(leverage)
    cross = np.where(y_upper >= spec_limit)[0]
    shelf_life = float(x_pred[cross[0]]) if len(cross) else None
    status = "Crosses specification" if shelf_life else "No projected crossing"

    projection = pd.DataFrame(
        {
            "Time (months)": x_pred,
            "Predicted Impurity (%)": y_pred,
            "95% Upper Confidence (%)": y_upper,
            "Specification Limit (%)": spec_limit,
        }
    )
    return {
        "condition": condition,
        "n": len(clean),
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r_squared),
        "shelf_life": shelf_life,
        "status": status,
        "projection": projection,
        "max_observed_month": float(np.max(x)),
    }


def _stability_interpretation(long_result: dict | None, accelerated_result: dict | None, spec_limit: float) -> str:
    if not long_result:
        return "Long-term data requires at least three numeric time/result points before shelf-life prediction."

    significant_change = False
    rate_ratio = None
    if accelerated_result and long_result["slope"] > 0 and accelerated_result["slope"] > 0:
        rate_ratio = accelerated_result["slope"] / long_result["slope"]
        significant_change = rate_ratio > 3.0 or (
            accelerated_result["shelf_life"] is not None and accelerated_result["shelf_life"] < 6
        )

    if significant_change:
        return (
            f"Accelerated trend suggests significant change ({rate_ratio:.1f}x long-term rate). "
            f"Per ICH Q1E logic, avoid extrapolating beyond available long-term coverage "
            f"({long_result['max_observed_month']:.0f} months) without additional data."
        )

    shelf = long_result["shelf_life"]
    if shelf is None:
        return (
            f"The 95% upper confidence trend remains below the specification ({spec_limit}%) "
            "within the projection range. A 24+ month shelf life may be supportable if all other attributes remain stable."
        )
    if shelf >= 24:
        return f"The long-term 95% UCI crosses at {shelf:.1f} months; a 24-month shelf life is supportable by this prototype model."
    if shelf >= 12:
        return f"The long-term 95% UCI crosses at {shelf:.1f} months; a shorter rounded shelf life may be supportable."
    return f"The long-term 95% UCI crosses at {shelf:.1f} months; the proposed shelf life should be reduced or reformulation/process work considered."


def _format_month(value: float | None) -> str:
    return "> projection range" if value is None else f"{value:.1f} months"


def _t95(dof: int) -> float:
    table = {
        1: 6.314,
        2: 2.920,
        3: 2.353,
        4: 2.132,
        5: 2.015,
        6: 1.943,
        7: 1.895,
        8: 1.860,
        9: 1.833,
        10: 1.812,
        11: 1.796,
        12: 1.782,
        13: 1.771,
        14: 1.761,
        15: 1.753,
        16: 1.746,
        17: 1.740,
        18: 1.734,
        19: 1.729,
        20: 1.725,
    }
    return table.get(min(max(int(dof), 1), 20), 1.645)


def _to_float(value) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(str(value).strip().replace("%", ""))
    except ValueError:
        return None
