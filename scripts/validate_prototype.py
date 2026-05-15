from __future__ import annotations

import importlib
import importlib.util
import io
import json
import os
import py_compile
import re
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
VENDOR = ROOT / "vendor_py314"
REPORT_DIR = ROOT / "validation_reports"

for import_path in (SRC, VENDOR):
    if import_path.exists() and str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


class Validator:
    def __init__(self) -> None:
        self.results: list[CheckResult] = []

    def pass_(self, name: str, detail: str = "") -> None:
        self.results.append(CheckResult(name, "PASS", detail))

    def warn(self, name: str, detail: str = "") -> None:
        self.results.append(CheckResult(name, "WARN", detail))

    def fail(self, name: str, detail: str = "") -> None:
        self.results.append(CheckResult(name, "FAIL", detail))

    def require(self, condition: bool, name: str, detail: str = "") -> None:
        if condition:
            self.pass_(name, detail)
        else:
            self.fail(name, detail)

    @property
    def failed(self) -> bool:
        return any(result.status == "FAIL" for result in self.results)


def _import(name: str):
    return importlib.import_module(name)


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def check_dependencies(v: Validator) -> None:
    required = ["streamlit", "pandas", "reportlab"]
    optional_pdf = ["pypdf", "pdfminer"]
    optional_chem = ["rdkit"]

    for module in required:
        if _module_available(module):
            v.pass_(f"dependency:{module}", "Installed")
        else:
            v.fail(f"dependency:{module}", "Not installed")

    pdf_available = False
    for module in optional_pdf:
        if _module_available(module):
            pdf_available = True
            v.pass_(f"pdf_dependency:{module}", "Installed")
        else:
            v.warn(f"pdf_dependency:{module}", "Not installed")
    if not pdf_available:
        v.warn(
            "pdf_text_extraction_dependencies",
            "Neither pypdf nor pdfminer.six is installed in this Python environment. Text-based PDF upload will return little or no text until requirements are installed.",
        )

    for module in optional_chem:
        if _module_available(module):
            v.pass_(f"chem_dependency:{module}", "Installed")
        else:
            v.warn(f"chem_dependency:{module}", "Not installed")


def check_py_compile(v: Validator) -> None:
    package_root = ROOT / "src" / "toxiguard_platform"
    module_root = package_root / "modules"
    files = [
        ROOT / "app.py",
        ROOT / "streamlit_app.py",
        package_root / "app.py",
        module_root / "document_intelligence.py",
        module_root / "product_context.py",
        module_root / "project_intake.py",
        module_root / "regulatory_ontology.py",
        module_root / "regulatory_sources.py",
        module_root / "worksheet.py",
        module_root / "reporting.py",
        module_root / "reviewer_workflow.py",
        module_root / "platform_tools.py",
        module_root / "tox_engine.py",
    ]
    for file in files:
        try:
            py_compile.compile(str(file), doraise=True)
            v.pass_(f"compile:{file.relative_to(ROOT)}", "Compiled successfully")
        except Exception as exc:
            v.fail(f"compile:{file.relative_to(ROOT)}", str(exc))


def check_document_classifier(v: Validator) -> None:
    from toxiguard_platform.modules.document_intelligence import analyze_ctd_text

    text = """--- PAGE 1 ---
3.2.P.5.1 Specifications 기준 및 시험방법: 함량은 표시량의 95.0~105.0% 이어야 한다. 개개 유연물질은 0.1% 이하, 총 불순물은 0.5% 이하이다.
--- PAGE 2 ---
3.2.P.5.2 Analytical Procedures HPLC analytical method and dissolution test condition were selected during development. Standard solution concentration is 0.10 mg/mL and sample solution concentration is 0.10 mg/mL.
--- PAGE 3 ---
비교용출시험에서 시험약과 대조약의 f2 값은 65로 의약품동등성이 확인되었다.
--- PAGE 4 ---
3.2.P.8 Stability 장기보존 안정성 시험은 25°C/60%RH 조건에서 24개월 동안 기준에 적합하였다. 포장은 PVC/알루미늄 PTP 포장이다.
--- PAGE 5 ---
아세트아미노펜 주성분 및 관련 유연물질을 평가하였다."""
    summary = analyze_ctd_text(text)
    details = summary["signal_details"]

    v.require(len(summary["evidence_blocks"]) >= 5, "document:evidence_blocks", f"{len(summary['evidence_blocks'])} blocks")
    v.require(len(details["specifications"]) >= 2, "document:specifications_detected", f"{len(details['specifications'])} rows")
    v.require(len(details["test_methods"]) >= 1, "document:test_methods_detected", f"{len(details['test_methods'])} rows")
    v.require(len(details["bioequivalence"]) >= 1, "document:bioequivalence_detected", f"{len(details['bioequivalence'])} rows")
    v.require(len(details["stability"]) >= 1, "document:stability_detected", f"{len(details['stability'])} rows")
    v.require(len(details["compounds"]) >= 1, "document:compounds_detected", f"{len(details['compounds'])} rows")
    v.require(len(summary["writing_structure"]) == 10, "document:writing_structure", f"{len(summary['writing_structure'])} writing rows")
    v.require(
        any(row["Evidence Status"] == "Detected" for row in summary["writing_structure"]),
        "document:writing_structure_detected",
        summary.get("writing_outline", ""),
    )

    be_text = "\n".join(row["Evidence"] for row in details["bioequivalence"])
    v.require("f2" in be_text or "의약품동등성" in be_text, "document:be_specific_metric", be_text[:200])
    method_text = "\n".join(row["Evidence"] for row in details["test_methods"])
    v.require("3.2.P.5.2" in method_text or "Analytical Procedures" in method_text, "document:p52_method_mapping", method_text[:300])
    v.require(
        not any("기준 및 시험방법" in row["Evidence"] and "HPLC" not in row["Evidence"] for row in details["test_methods"]),
        "document:spec_heading_not_method",
        method_text[:300],
    )
    v.require(
        not any("PAGE" in row["Evidence"] for rows in details.values() for row in rows),
        "document:page_markers_removed_from_evidence",
        "Fallback evidence should not include internal page markers.",
    )

    dissolution_spec_in_be = any("용출 규격" in row["Evidence"] for row in details["bioequivalence"])
    v.require(not dissolution_spec_in_be, "document:dissolution_spec_not_be", "용출 규격 should remain outside Bioequivalence unless comparative context exists.")

    v.require(summary["candidate_compounds"], "document:candidate_compound_alias", json.dumps(summary["candidate_compounds"], ensure_ascii=False))


def check_project_intake(v: Validator) -> None:
    from toxiguard_platform.modules.document_intelligence import analyze_ctd_text
    from toxiguard_platform.modules.project_intake import combine_project_documents, document_signal_overview, manual_document_record

    spec_doc = manual_document_record(
        "3.2.P.5.1 Specifications. Assay 95.0-105.0%. "
        "3.2.P.5.2 Analytical Procedures. HPLC standard solution 0.10 mg/mL sample solution 0.10 mg/mL.",
        "3.2.P.5 Specification.pdf",
    )
    be_doc = manual_document_record(
        "Comparative dissolution against reference drug was performed. The f2 value was 67 and supports similarity.",
        "Module 5 BE.pdf",
    )
    project = combine_project_documents("Validation Dossier", [spec_doc, be_doc])
    summary = analyze_ctd_text(project["combined_text"])
    per_doc = [
        document_signal_overview(spec_doc, analyze_ctd_text(spec_doc["text"])),
        document_signal_overview(be_doc, analyze_ctd_text(be_doc["text"])),
    ]

    v.require(project["document_count"] == 2, "project_intake:document_count", str(project["inventory"]))
    v.require(len(project["pages"]) == 2, "project_intake:project_pages", str(project["pages"]))
    v.require("Document: Module 5 BE.pdf" in project["combined_text"], "project_intake:document_marker", project["combined_text"][:260])
    v.require(len(summary["signal_details"]["specifications"]) >= 1, "project_intake:combined_spec_signals", str(summary["signal_details"]["specifications"][:1]))
    v.require(len(summary["signal_details"]["bioequivalence"]) >= 1, "project_intake:combined_be_signals", str(summary["signal_details"]["bioequivalence"][:1]))
    v.require(per_doc[0]["Test Methods"] >= 1 and per_doc[1]["Bioequivalence"] >= 1, "project_intake:per_document_summary", str(per_doc))


def check_specification_table_format(v: Validator) -> None:
    from toxiguard_platform.modules.document_intelligence import analyze_ctd_text
    from toxiguard_platform.modules.specification_structure import build_test_item_matrix

    text = """--- PAGE 1 ---
4.1. Specification
Tests Specification Test Methods
Appearance White to slight yellow powder Visual
Identification - IR - HPLC Positive Positive USP<197K> USP<621>, Chromatography
Heavy metals Not more than 20 ppm USP<231>, MethodⅡ
Related substances - Individual impurity - Total impurities Not more than 1.0 % Not more than 2.0 % USP<621>, Chromatography
Loss on drying Not more than 0.5 % USP<731>
Residue on ignition Not more than 0.2 % USP<281>
Assay Not less than 97.0 % USP<621>, Chromatography
Residual solvents - Methanol - Dichloromethane - Ethyl acetate Not more than 3,000 ppm Not more than 600 ppm Not more than 5,000 ppm USP<467>, Residual Solvents
"""
    summary = analyze_ctd_text(text)
    table = summary["specification_table"]
    v.require(len(table) >= 9, "spec_table:rows", f"{len(table)} rows")
    v.require(
        any(row["항목 / Test"].startswith("함량") and "97.0" in row["기준 / Specification"] for row in table),
        "spec_table:assay_limit",
        json.dumps(table, ensure_ascii=False)[:500],
    )
    v.require(
        any("Methanol" in row["세부항목 / Sub-test"] and "3,000" in row["기준 / Specification"] for row in table),
        "spec_table:residual_solvent_limit",
        json.dumps(table, ensure_ascii=False)[:500],
    )
    matrix = build_test_item_matrix(summary)
    v.require(len(matrix) >= 9, "test_item_matrix:rows", f"{len(matrix)} rows")
    v.require(
        any(row["시험항목 / Test Item"].startswith("함량") and row["상태 / Status"] == "Linked" for row in matrix),
        "test_item_matrix:assay_linked",
        json.dumps(matrix, ensure_ascii=False)[:500],
    )


def check_regulatory_sources(v: Validator) -> None:
    from toxiguard_platform.modules.document_intelligence import analyze_ctd_text
    from toxiguard_platform.modules.regulatory_sources import CATEGORY_ORDER, SOURCE_LIBRARY, source_catalog_rows
    from toxiguard_platform.modules.worksheet import DEFAULT_APPLICATION_PROFILE, build_reviewer_worksheet

    v.require(len(SOURCE_LIBRARY) >= 20, "sources:library_size", f"{len(SOURCE_LIBRARY)} sources")
    v.require(
        any(row["Source Type"] == "Open-source tool" for row in SOURCE_LIBRARY),
        "sources:open_source_tools",
        "Open-source tooling references are included.",
    )
    for category in CATEGORY_ORDER:
        v.require(
            bool(source_catalog_rows(category)),
            f"sources:category:{category}",
            f"{len(source_catalog_rows(category))} source rows",
        )

    summary = analyze_ctd_text(
        "--- PAGE 1 ---\n3.2.P.5.1 Specifications: Assay 95.0~105.0%. HPLC analytical procedure validation was performed.\n"
        "--- PAGE 2 ---\n비교용출시험에서 시험약과 대조약의 f2 값은 65였다.\n"
        "--- PAGE 3 ---\n3.2.P.8 Stability: 25°C/60%RH long-term stability was acceptable."
    )
    v.require(bool(summary["regulatory_source_crosswalk"]), "sources:summary_crosswalk", f"{len(summary['regulatory_source_crosswalk'])} rows")
    v.require(bool(summary["regulatory_source_matches"]), "sources:summary_matches", f"{len(summary['regulatory_source_matches'])} rows")
    source_names = " ".join(row.get("Primary Source", "") for row in summary["regulatory_source_matches"])
    v.require(
        "ICH Q6A" in source_names or "ICH Q2(R2)" in source_names,
        "sources:primary_quality_mapping",
        source_names,
    )

    worksheet = build_reviewer_worksheet(DEFAULT_APPLICATION_PROFILE, summary, [])
    v.require(bool(worksheet["regulatory_source_crosswalk"]), "sources:worksheet_crosswalk", "Worksheet carries source crosswalk.")
    v.require(bool(worksheet["regulatory_source_matches"]), "sources:worksheet_matches", "Worksheet carries evidence-source matches.")


def check_product_context(v: Validator) -> None:
    from toxiguard_platform.modules.document_intelligence import analyze_ctd_text
    from toxiguard_platform.modules.product_context import primary_context_name, primary_context_smiles
    from toxiguard_platform.modules.worksheet import DEFAULT_APPLICATION_PROFILE, build_reviewer_worksheet

    summary = analyze_ctd_text(
        "--- PAGE 1 ---\nMycophenolate mofetil (Myrept) 500 mg Tablet\n"
        "Active Ingredient: Mycophenolate mofetil. Dosage Form: Tablet. Route: oral.\n"
        "--- PAGE 2 ---\nThe formulation contains microcrystalline cellulose, povidone, crospovidone, magnesium stearate and LUVITEC.\n"
        "--- PAGE 3 ---\nThe product is packaged in PVC/Aluminium PTP and stability was evaluated at 25°C/60%RH."
    )
    context = summary["product_context"]
    v.require(context.get("product_name") == "Myrept", "context:product_name", context.get("product_name", ""))
    v.require(context.get("active_substance") == "Mycophenolate mofetil", "context:active_substance", context.get("active_substance", ""))
    v.require(context.get("dosage_form") == "Tablet", "context:dosage_form", context.get("dosage_form", ""))
    v.require(bool(context.get("linked_substances")), "context:linked_substances", json.dumps(context.get("linked_substances"), ensure_ascii=False)[:300])
    v.require(len(context.get("formulation", [])) >= 4, "context:formulation", json.dumps(context.get("formulation"), ensure_ascii=False)[:300])
    v.require(bool(primary_context_name(context)), "context:primary_name", primary_context_name(context))
    v.require(bool(primary_context_smiles(context)), "context:primary_smiles_or_fallback", primary_context_smiles(context)[:80])

    worksheet = build_reviewer_worksheet(DEFAULT_APPLICATION_PROFILE, summary, [])
    v.require(bool(worksheet["product_context"]), "context:worksheet_link", "Worksheet carries product context.")

    korean_summary = analyze_ctd_text(
        "--- PAGE 1 ---\n기준 및 시험방법\n"
        "제품명: 마이렙트정 500밀리그램\n"
        "주성분: 미코페놀레이트 모페틸\n"
        "함량: 500 mg\n"
        "제형: 정제\n"
        "투여경로: 경구\n"
        "성상: 흰색의 장방형 필름코팅정"
    )
    korean_context = korean_summary["product_context"]
    v.require(korean_context.get("product_name") == "마이렙트정 500밀리그램", "context:korean_product_name", korean_context.get("product_name", ""))
    v.require(korean_context.get("active_substance") == "미코페놀레이트 모페틸", "context:korean_active", korean_context.get("active_substance", ""))
    v.require(korean_context.get("strength") == "500 mg", "context:korean_strength", korean_context.get("strength", ""))
    v.require(korean_context.get("dosage_form") == "Tablet", "context:korean_dosage_form", korean_context.get("dosage_form", ""))
    v.require(korean_context.get("route") == "Oral", "context:korean_route", korean_context.get("route", ""))

    korean_table_summary = analyze_ctd_text(
        "--- PAGE 1 ---\n1. 제품정보\n"
        "제품명\n마이렙트정500밀리그램\n"
        "원료약품 및 그 분량\n1정 중 미코페놀레이트 모페틸 500 mg\n"
        "제형\n필름코팅정\n"
        "투여경로\n경구"
    )
    korean_table_context = korean_table_summary["product_context"]
    v.require(korean_table_context.get("product_name") == "마이렙트정500밀리그램", "context:korean_table_product", korean_table_context.get("product_name", ""))
    v.require(korean_table_context.get("active_substance") == "미코페놀레이트 모페틸", "context:korean_table_active", korean_table_context.get("active_substance", ""))
    v.require(korean_table_context.get("strength") == "500 mg", "context:korean_table_strength", korean_table_context.get("strength", ""))
    v.require(korean_table_context.get("dosage_form") == "Film-coated tablet", "context:korean_table_dosage", korean_table_context.get("dosage_form", ""))

    english_header_summary = analyze_ctd_text(
        "--- PAGE 1 ---\n"
        "Chong Kun Dang Pharm Confidential Mycophenolate mofetil (Myrept) 500 mg Tablet\n"
        "3.2.P.2 Pharmaceutical Development\n"
        "API\ninformation\nMycophenolate mofetil Manufacturer : Biocon Limited(India)\n"
    )
    english_header_context = english_header_summary["product_context"]
    v.require(
        english_header_context.get("active_substance") == "Mycophenolate mofetil",
        "context:english_pdf_header_active",
        english_header_context.get("active_substance", ""),
    )


def check_reviewer_correction_logic(v: Validator) -> None:
    from toxiguard_platform.modules.document_intelligence import analyze_ctd_text
    from toxiguard_platform.modules.reviewer_workflow import apply_reviewer_corrections

    summary = analyze_ctd_text("비교용출시험에서 시험약과 대조약의 f2 값은 70이었다.")
    rows = []
    for detail in summary["signal_details"]["bioequivalence"]:
        row = dict(detail)
        row["Reviewer Category"] = "Specifications"
        row["Reviewer Status"] = "Corrected"
        row["Reviewer Note"] = "Intentional validation correction"
        rows.append(row)
    edited = pd.DataFrame(rows)
    corrected = apply_reviewer_corrections(summary, edited)
    v.require(
        bool(corrected["signal_details"]["specifications"]),
        "reviewer_correction:category_move",
        "Bioequivalence row moved to Specifications for validation.",
    )
    v.require(
        not corrected["signal_details"]["bioequivalence"],
        "reviewer_correction:source_category_empty",
        "Original category emptied after correction.",
    )


def check_worksheet(v: Validator) -> None:
    from toxiguard_platform.modules.document_intelligence import analyze_ctd_text
    from toxiguard_platform.modules.tox_engine import assess_smiles
    from toxiguard_platform.modules.worksheet import DEFAULT_APPLICATION_PROFILE, build_reviewer_worksheet

    summary = analyze_ctd_text(
        "--- PAGE 1 ---\n함량은 표시량의 95.0~105.0% 이어야 한다.\n"
        "--- PAGE 2 ---\n장기보존 안정성 시험은 25°C/60%RH 조건에서 24개월 동안 기준에 적합하였다.\n"
        "--- PAGE 3 ---\n아세트아미노펜 주성분을 평가하였다."
    )
    assessments = [assess_smiles("CC(=O)NC1=CC=C(O)C=C1")]
    worksheet = build_reviewer_worksheet(DEFAULT_APPLICATION_PROFILE, summary, assessments)

    v.require(bool(worksheet["submission_map"]), "worksheet:submission_map", f"{len(worksheet['submission_map'])} rows")
    v.require(
        bool(worksheet["specification_writing_structure"]),
        "worksheet:specification_writing_structure",
        f"{len(worksheet['specification_writing_structure'])} rows",
    )
    v.require("final_review_language" in worksheet, "worksheet:final_language", worksheet.get("final_review_language", "")[:200])
    v.require(bool(worksheet["quality_assessment"]), "worksheet:quality_assessment", f"{len(worksheet['quality_assessment'])} rows")
    v.require(bool(worksheet["ich_m7_review"]), "worksheet:ich_m7_review", f"{len(worksheet['ich_m7_review'])} rows")


def check_tox_engine(v: Validator) -> None:
    from toxiguard_platform.modules.tox_engine import assess_smiles

    aniline = assess_smiles("c1ccc(N)cc1")
    v.require(aniline.valid_structure, "tox_engine:aniline_valid", aniline.conclusion)
    v.require(bool(aniline.alerts), "tox_engine:aniline_alert", str(aniline.alerts))

    acetaminophen = assess_smiles("CC(=O)NC1=CC=C(O)C=C1")
    v.require(acetaminophen.valid_structure, "tox_engine:acetaminophen_valid", acetaminophen.conclusion)
    v.require(0 <= acetaminophen.risk_score <= 1, "tox_engine:risk_score_range", str(acetaminophen.risk_score))


def check_platform_tools(v: Validator) -> None:
    from toxiguard_platform.modules.platform_tools import (
        DEFAULT_DISSOLUTION_PROFILE,
        assess_genotoxicity_table,
        assess_impurity_table,
        build_evidence_matrix,
        build_genotoxicity_evidence_basis,
        build_pharmaceutical_equivalence_matrix,
        build_qsar_model_validation_matrix,
        build_related_substance_evidence_basis,
        calculate_f2,
        dissolution_profile_from_document_text,
        dissolution_profile_summary,
        evaluate_related_substances,
        predict_degradation_products,
        predict_stability_shelf_life,
        qsar_reference_source_table,
        validate_engine,
    )

    table = pd.DataFrame(
        [
            {
                "Impurity Code": "GTI-1",
                "Chemical Name": "Potential alerting impurity",
                "Origin": "process impurity",
                "Observed (%)": 0.2,
                "Specification (%)": 0.1,
                "Concern": "potential mutagenic impurity",
            }
        ]
    )
    assessed = assess_impurity_table(table)
    v.require(assessed.iloc[0]["Status"] == "Above specification", "platform:impurity_status", assessed.iloc[0].to_json(force_ascii=False))

    related = evaluate_related_substances(table)
    v.require("Spec Usage (%)" in related.columns, "platform:related_substances_usage", related.to_json(force_ascii=False))
    related_basis = build_related_substance_evidence_basis(table, compound_name="acetaminophen")
    v.require(
        not related_basis.empty and "Evidence Layer" in related_basis.columns,
        "platform:related_substance_basis",
        related_basis.to_json(force_ascii=False),
    )

    equivalence = build_pharmaceutical_equivalence_matrix(
        {
            "signal_details": {
                "specifications": [{"Evidence": "Assay 95.0 to 105.0 %", "Page": 1}],
                "test_methods": [{"Evidence": "HPLC assay method", "Page": 2}],
                "bioequivalence": [{"Evidence": "comparative dissolution f2 value 65", "Page": 3}],
                "stability": [{"Evidence": "24 months long-term stability", "Page": 4}],
                "compounds": [{"Evidence": "related substances impurity A", "Page": 5}],
            }
        },
        {"active_substance": "Example API", "strength": "10 mg", "dosage_form": "tablet", "route": "oral"},
    )
    v.require(len(equivalence) >= 8, "platform:pharmaceutical_equivalence_matrix", f"{len(equivalence)} rows")

    be_result = calculate_f2(DEFAULT_DISSOLUTION_PROFILE, bootstrap_runs=200)
    v.require(be_result.f2 >= 50, "platform:be_f2_similarity", f"f2={be_result.f2}; P(f2>=50)={be_result.probability_f2_ge_50}%")
    v.require(
        be_result.bootstrap_runs == 200 and be_result.ci_low is not None and be_result.ci_high is not None,
        "platform:be_bootstrap_interval",
        f"{be_result.ci_low} - {be_result.ci_high}",
    )
    be_summary = dissolution_profile_summary(DEFAULT_DISSOLUTION_PROFILE)
    v.require("Difference (%)" in be_summary.columns, "platform:be_profile_summary", be_summary.head(1).to_json(force_ascii=False))
    extracted_profile, reported_f2, _ = dissolution_profile_from_document_text(
        """
Time (minutes)
5
10
15
30
45
60
90
120
F(2)
Reference
13.3 46.2 59.6 72.1 77.7 81.0 84.4 85.9
Test Drug
24.1
46.5
56.6
68.7
74.8
79.0
83.2
84.2
67
Figure 3.2.P.2.2.1-5.
"""
    )
    v.require(
        len(extracted_profile) == 8 and int(reported_f2 or 0) == 67,
        "platform:be_document_profile_seed",
        extracted_profile.to_json(force_ascii=False),
    )
    compact_profile, compact_f2, compact_hint = dissolution_profile_from_document_text(
        """
Time (minutes) 5 10 15 30 45 60 90 120 F(2)
Reference 13.3  46.2  59.6  72.1  77.7  81.0  84.4  85.9  67 Test Drug  24.1 46.5 56.6 68.7 74.8 79.0 83.2 84.2
Figure 3.2.P.2.2.1-5.
"""
    )
    v.require(
        len(compact_profile) == 8
        and int(compact_f2 or 0) == 67
        and "Test Drug" in compact_hint
        and compact_profile["Test Mean (%)"].round(1).tolist() == [24.1, 46.5, 56.6, 68.7, 74.8, 79.0, 83.2, 84.2],
        "platform:be_compact_document_profile_seed",
        compact_profile.to_json(force_ascii=False),
    )

    genotoxicity = assess_genotoxicity_table(pd.DataFrame([{"Compound": "Aniline", "Role": "impurity", "SMILES": "c1ccc(N)cc1"}]))
    v.require(not genotoxicity.empty and "ICH M7 Class" in genotoxicity.columns, "platform:genotoxicity_assessment", genotoxicity.to_json(force_ascii=False))
    genotoxicity_basis = build_genotoxicity_evidence_basis(
        pd.DataFrame(
            [
                {
                    "Compound": "Aniline",
                    "Role": "impurity",
                    "SMILES": "c1ccc(N)cc1",
                    "Endpoint": "Bacterial reverse mutation / Ames mutagenicity",
                    "Expert Rule-Based Model": "ToxiGuard prototype expert alerts",
                    "Expert Applicability Domain": "In-domain for aromatic amine alert family",
                    "Statistical Model": "Validation statistical QSAR model",
                    "Statistical QSAR Result": "positive alert in external model",
                    "Statistical Applicability Domain": "In-domain based on aromatic amine analogs",
                    "Validation Metrics / External Predictivity": "External validation summary available",
                    "Mechanistic Rationale": "Aromatic amine alert with metabolic activation concern",
                    "Experimental / Literature Data": "Ames positive with S9",
                }
            ]
        )
    )
    v.require(
        not genotoxicity_basis.empty and "Structural Concern" in genotoxicity_basis.columns,
        "platform:genotoxicity_basis",
        genotoxicity_basis.to_json(force_ascii=False),
    )
    qsar_validation = build_qsar_model_validation_matrix(
        pd.DataFrame(
            [
                {
                    "Compound": "Aniline",
                    "Role": "impurity",
                    "SMILES": "c1ccc(N)cc1",
                    "Endpoint": "Bacterial reverse mutation / Ames mutagenicity",
                    "Expert Rule-Based Model": "ToxiGuard prototype expert alerts",
                    "Expert Applicability Domain": "In-domain for aromatic amine alert family",
                    "Statistical Model": "Validation statistical QSAR model",
                    "Statistical QSAR Result": "positive alert in external model",
                    "Statistical Applicability Domain": "In-domain based on aromatic amine analogs",
                    "Validation Metrics / External Predictivity": "External validation summary available",
                    "Mechanistic Rationale": "Aromatic amine alert with metabolic activation concern",
                    "Experimental / Literature Data": "Ames positive with S9",
                }
            ]
        )
    )
    v.require(
        not qsar_validation.empty and "Validation Criterion" in qsar_validation.columns,
        "platform:qsar_validation_matrix",
        qsar_validation.to_json(force_ascii=False),
    )
    v.require(
        any("OECD 3" in row for row in qsar_validation["Validation Criterion"].astype(str)),
        "platform:qsar_applicability_domain_check",
        qsar_validation["Validation Criterion"].to_json(force_ascii=False),
    )
    qsar_sources = qsar_reference_source_table()
    v.require(
        len(qsar_sources) >= 4 and any("ICH M7" in source for source in qsar_sources["Source"].astype(str)),
        "platform:qsar_reference_sources",
        qsar_sources.to_json(force_ascii=False),
    )

    shelf_life = predict_stability_shelf_life(
        pd.DataFrame({"Time (months)": [0, 3, 6, 9], "Impurity (%)": [0.01, 0.02, 0.03, 0.04]}),
        pd.DataFrame({"Time (months)": [0, 1, 2], "Impurity (%)": [0.01, 0.02, 0.04]}),
        0.15,
    )
    v.require(not shelf_life["metrics"].empty, "platform:stability_shelf_life_prediction", shelf_life["interpretation"])

    matrix = build_evidence_matrix("c1ccc(N)cc1")
    v.require(not matrix.empty, "platform:evidence_matrix", f"{len(matrix)} rows")

    products = predict_degradation_products("CC(=O)NC1=CC=C(O)C=C1")
    v.require(not products.empty, "platform:degradation_prediction", f"{len(products)} rows")

    validation = validate_engine()
    v.require(len(validation) >= 4, "platform:engine_validation_panel", f"{len(validation)} rows")


def check_reporting(v: Validator) -> None:
    from toxiguard_platform.modules.reporting import create_pdf_report

    pdf = create_pdf_report({"title": "Validation Report", "summary": "Smoke test"})
    v.require(pdf.startswith(b"%PDF"), "reporting:pdf_magic_header", f"{len(pdf)} bytes")
    v.require(len(pdf) > 500, "reporting:pdf_size", f"{len(pdf)} bytes")

    multilingual_payload = {
        "application_snapshot": {
            "application_type": "ANDA",
            "application_number": "TBD",
            "product_name": "검증정 500밀리그램 / Validation tablet 500 mg",
            "applicant": "검증회사 / Validation Company",
            "dosage_form": "정제 / Tablet",
            "route": "경구 / Oral",
            "review_status": "검토 중 / In Review",
        },
        "product_context": {
            "product_name": "검증정 500밀리그램 / Validation tablet 500 mg",
            "active_substance": "검증성분 / Validation API",
            "strength": "500 mg",
            "dosage_form": "필름코팅정 / Film-coated tablet",
            "route": "경구 / Oral",
            "basic_info": [
                {
                    "Field": "제품명 / Product Name",
                    "Value": "검증정 500밀리그램 / Validation tablet 500 mg",
                    "Reviewer Check": "원문 확인 / Verify source",
                }
            ],
        },
        "specification_table": [
            {
                "항목 / Test": "함량 / Assay",
                "세부항목 / Sub-test": "-",
                "기준 / Specification": "표시량의 95.0~105.0% / 95.0-105.0% of label claim",
                "시험방법 / Test Method": "액체크로마토그래프법 / HPLC",
                "CTD Anchor": "3.2.P.5.1",
            }
        ],
        "specifications": ["함량은 표시량의 95.0~105.0%이어야 한다."],
        "test_methods": ["검액과 표준액은 HPLC로 시험한다 / Analyze sample and standard by HPLC."],
        "bioequivalence": ["비교용출시험에서 f2 값은 67이었다 / Comparative dissolution f2 was 67."],
        "stability": ["장기보존 안정성 24개월 적합 / Long-term stability 24 months acceptable."],
        "signal_details": {
            "specifications": [
                {
                    "Page": "N/A",
                    "Evidence Role": "Direct Evidence",
                    "Evidence": "기준 및 시험방법: 함량 95.0~105.0%",
                    "CTD Mapping": "3.2.P.5.1 Specifications",
                }
            ]
        },
        "regulatory_narrative": "유전독성 및 품질 검토는 전문가 확인이 필요하다.",
        "fda_style_reviewer_worksheet": {
            "Integrated Assessment": {
                "Recommended Action": "전문가 확인 후 수용 가능 / Acceptable With Expert Confirmation",
                "Key Review Issues": "기준 및 시험방법 확인 필요 / Specification and method confirmation needed",
                "Residual Uncertainty": "원문 확인 필요 / Source verification needed",
                "Rationale": "Prototype 검토 결과 / Prototype rationale",
            },
            "Final Review Language": "최종 판단은 원문 CTD 확인 후 가능하다.",
        },
    }
    english_pdf = create_pdf_report(multilingual_payload, language="en")
    english_text = _extract_pdf_text(english_pdf)
    v.require(
        "Development Story and Control Strategy" in english_text and "Control Strategy Snapshot" in english_text,
        "reporting:english_development_story_section",
        english_text[:500],
    )
    v.require(
        not re.search(r"[가-힣]", english_text),
        "reporting:english_pdf_no_hangul",
        re.findall(r".{0,20}[가-힣].{0,20}", english_text)[:5].__repr__(),
    )
    korean_pdf = create_pdf_report(multilingual_payload, language="ko")
    korean_text = _extract_pdf_text(korean_pdf)
    v.require(
        "개발 서사 및 관리전략" in korean_text and "관리전략 요약" in korean_text,
        "reporting:korean_development_story_section",
        korean_text[:500],
    )
    v.require(
        "전문가 확인 후 수용 가능 / 전문가 확인 후 수용 가능" not in korean_text,
        "reporting:korean_no_duplicate_recommendation",
        korean_text[:500],
    )
    v.require(
        bool(re.search(r"[가-힣]", korean_text)),
        "reporting:korean_pdf_allows_hangul",
        korean_text[:220],
    )


def check_real_pdf_dependencies(v: Validator) -> None:
    configured_paths = os.environ.get("TOXIGUARD_VALIDATION_PDFS", "").strip()
    if not configured_paths:
        v.pass_("real_pdf:optional_sources", "Optional local PDF dependency validation is not configured.")
        return

    sample_paths = [Path(item).expanduser() for item in configured_paths.split(os.pathsep) if item.strip()]
    for path in sample_paths:
        if not path.exists():
            v.fail(f"real_pdf:{path.name}", "Configured local PDF was not found.")
            continue
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            texts = []
            for page in reader.pages[:5]:
                texts.append(page.extract_text() or "")
            chars = len("\n".join(texts).strip())
            if chars > 200:
                v.pass_(f"real_pdf:{path.name}", f"{len(reader.pages)} pages, {chars} chars extracted from first 5 pages")
            else:
                v.warn(
                    f"real_pdf:{path.name}",
                    f"Only {chars} chars extracted from first 5 pages. Use OCR for scanned/font-encoded PDFs.",
                )
        except Exception as exc:
            v.warn(f"real_pdf:{path.name}", f"Extraction check failed: {exc}")


def check_real_document_pipeline(v: Validator) -> None:
    """Validate an optional local CTD document through the full analyzer path."""
    raw_path = os.environ.get("TOXIGUARD_VALIDATION_REAL_CTD_PDF", "").strip()
    if not raw_path:
        v.pass_("real_document:optional_source_pdf", "Optional local real-document validation is not configured.")
        return

    path = Path(raw_path).expanduser()
    if not path.exists():
        v.fail("real_document:source_pdf", "Configured local CTD PDF was not found.")
        return

    from toxiguard_platform.modules.document_intelligence import analyze_ctd_text, extract_document_text
    from toxiguard_platform.modules.platform_tools import (
        build_pharmaceutical_equivalence_matrix,
        calculate_f2,
        dissolution_profile_from_document_text,
    )
    from toxiguard_platform.modules.specification_structure import build_test_item_matrix

    started = time.perf_counter()
    extracted = extract_document_text(path.read_bytes(), "application/pdf")
    elapsed = time.perf_counter() - started
    summary = analyze_ctd_text(extracted.text)
    context = summary.get("product_context") or {}
    details = summary.get("signal_details") or {}
    matrix = build_test_item_matrix(summary)
    equivalence = build_pharmaceutical_equivalence_matrix(summary, context)
    be_profile, reported_f2, source_hint = dissolution_profile_from_document_text(extracted.text)

    v.require(elapsed < 10, "real_document:extraction_speed", f"{elapsed:.2f}s for {len(extracted.pages)} pages")
    v.require(len(extracted.pages) >= 10 and len(extracted.text) >= 10000, "real_document:text_volume", f"{len(extracted.pages)} pages, {len(extracted.text)} chars")
    v.require(bool(context.get("product_name")), "real_document:product_name", str(context.get("product_name", "")))
    v.require(bool(context.get("active_substance")), "real_document:active_substance", str(context.get("active_substance", "")))
    v.require(bool(context.get("strength")), "real_document:strength", str(context.get("strength", "")))
    v.require(bool(context.get("dosage_form")), "real_document:dosage_form", str(context.get("dosage_form", "")))
    v.require(len(context.get("formulation") or []) >= 3, "real_document:formulation_rows", f"{len(context.get('formulation') or [])} rows")
    v.require(len(details.get("test_methods", [])) >= 10, "real_document:test_method_signals", f"{len(details.get('test_methods', []))} rows")
    v.require(len(details.get("bioequivalence", [])) >= 1, "real_document:bioequivalence_signals", f"{len(details.get('bioequivalence', []))} rows")
    v.require(len(details.get("stability", [])) >= 5, "real_document:stability_signals", f"{len(details.get('stability', []))} rows")
    v.require(len(matrix) >= 5, "real_document:test_item_matrix", f"{len(matrix)} rows")
    v.require(len(equivalence) >= 8, "real_document:equivalence_matrix", f"{len(equivalence)} rows")
    v.require(len(be_profile) >= 3 and reported_f2 is not None, "real_document:dissolution_profile", f"{len(be_profile)} rows; reported f2={reported_f2}")
    if not be_profile.empty:
        f2_result = calculate_f2(be_profile, bootstrap_runs=200)
        v.require(f2_result.f2 >= 50, "real_document:f2_bootstrap", f"f2={f2_result.f2}; P(f2>=50)={f2_result.probability_f2_ge_50}%")


def check_streamlit_language_switch(v: Validator) -> None:
    """Validate Streamlit rerun behavior when switching Korean to English."""
    try:
        from streamlit.testing.v1 import AppTest
    except Exception as exc:
        v.warn("streamlit_language_switch:apptest_import", f"Skipped: {exc}")
        return

    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
    app.run()
    if app.exception:
        v.fail("streamlit_language_switch:initial_render", "; ".join(str(item.value) for item in app.exception))
        return
    opening_buttons = [item.label for item in app.button]
    v.require("Enter ToxiGuard-Platform" in opening_buttons, "streamlit_opening:enter_button", str(opening_buttons[:4]))
    opening_markdown = "\n".join(item.value for item in app.markdown)
    v.require(
        'href="?lang=ko&home=1"' in opening_markdown and 'href="?lang=en&home=1"' in opening_markdown,
        "streamlit_opening:language_links",
        opening_markdown[:500],
    )
    v.require(
        ".tg-opening-map-stage:hover .tg-opening-map-canvas img" in opening_markdown and "transform: scale(1.38)" in opening_markdown,
        "streamlit_opening:hover_zoom_css",
        opening_markdown[:500],
    )
    if "Enter ToxiGuard-Platform" not in opening_buttons:
        return
    app.button[opening_buttons.index("Enter ToxiGuard-Platform")].click()
    app.run(timeout=30)
    if app.exception:
        v.fail("streamlit_language_switch:post_opening_render", "; ".join(str(item.value) for item in app.exception))
        return
    if not app.selectbox:
        v.fail("streamlit_language_switch:selector", "Language selector was not rendered.")
        return
    app.selectbox[0].set_value("en")
    app.run()
    if app.exception:
        v.fail("streamlit_language_switch:english_render", "; ".join(str(item.value) for item in app.exception))
        return
    subheaders = [item.value for item in app.subheader]
    v.require("CTD Document Intake" in subheaders, "streamlit_language_switch:english_intake", str(subheaders[:5]))
    v.require("Document Signals" in subheaders, "streamlit_language_switch:english_signals", str(subheaders[:5]))
    english_menu_text = "\n".join([item.label for item in app.button] + [item.value for item in app.subheader] + [item.value for item in app.caption])
    v.require(
        not re.search(r"[가-힣]", english_menu_text),
        "streamlit_language_switch:english_ui_no_hangul",
        english_menu_text[:600],
    )
    source = (ROOT / "src" / "toxiguard_platform" / "app.py").read_text()
    route_source_start = source.find('raw_home_request = st.query_params.get("home")')
    route_source = source[route_source_start:] if route_source_start >= 0 else source
    query_view_block = re.search(
        r"raw_home_request = st\.query_params\.get\(\"home\"\)(?P<body>.*?)\n\n\ndef current_language",
        route_source,
        flags=re.S,
    )
    v.require(
        bool(query_view_block and "entered_platform = True" in query_view_block.group("body")),
        "streamlit_navigation:view_query_skips_opening",
        query_view_block.group("body")[:300] if query_view_block else "query view block not found",
    )
    v.require(
        bool(query_view_block and "entered_platform = False" in query_view_block.group("body")),
        "streamlit_navigation:base_url_shows_opening",
        query_view_block.group("body")[:400] if query_view_block else "query view block not found",
    )
    v.require(
        bool(query_view_block and "home_requested" in query_view_block.group("body")),
        "streamlit_navigation:explicit_home_overrides_view",
        query_view_block.group("body")[:500] if query_view_block else "query view block not found",
    )
    v.require(
        'st.query_params["view"] = WORKFLOW_SLUGS["Document Analyzer"]' in source,
        "streamlit_navigation:enter_button_sets_app_view",
        "Enter button should move from opening route to the internal app route.",
    )
    v.require(
        "st.query_params.clear()" in source and "home=1" in source,
        "streamlit_navigation:home_links_clear_internal_route",
        "Opening links should have a route-level home state and Enter should clear it before entering the app.",
    )


def check_streamlit_document_analyzer_flow(v: Validator) -> None:
    """Validate that pasted CTD text produces visible Document Analyzer results."""
    try:
        from streamlit.testing.v1 import AppTest
    except Exception as exc:
        v.warn("streamlit_document_flow:apptest_import", f"Skipped: {exc}")
        return

    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=120)
    app.run(timeout=120)
    if app.exception:
        v.fail("streamlit_document_flow:initial_render", "; ".join(str(item.value) for item in app.exception))
        return
    opening_buttons = [item.label for item in app.button]
    if "Enter ToxiGuard-Platform" in opening_buttons:
        app.button[opening_buttons.index("Enter ToxiGuard-Platform")].click()
        app.run(timeout=120)
        if app.exception:
            v.fail("streamlit_document_flow:post_opening_render", "; ".join(str(item.value) for item in app.exception))
            return
    button_labels = [item.label for item in app.button]
    text_area_labels = [item.label for item in app.text_area]
    v.require("프로젝트 분석" in button_labels, "streamlit_document_flow:analyze_button", str(button_labels))
    v.require("또는 CTD 문서 텍스트 붙여넣기" in text_area_labels, "streamlit_document_flow:text_area", str(text_area_labels))
    v.require(
        any(label.startswith("DOC") and "문서 분석" in label for label in button_labels),
        "streamlit_sidebar:document_nav_button",
        str(button_labels),
    )
    v.require(
        any(label.startswith("MOL") and "분자" in label for label in button_labels),
        "streamlit_sidebar:molecule_nav_button",
        str(button_labels),
    )
    v.require("코멘트" in text_area_labels, "streamlit_sidebar:comment_box", str(text_area_labels))

    ctd_text = (
        "3.2.P.5.1 Specifications. Assay 95.0-105.0%. "
        "3.2.P.5.2 Analytical Procedures. HPLC standard solution 0.10 mg/mL "
        "sample solution 0.10 mg/mL. Comparative dissolution f2 value 67. "
        "Stability 24 months."
    )
    ctd_text_area = text_area_labels.index("또는 CTD 문서 텍스트 붙여넣기")
    app.text_area[ctd_text_area].set_value(ctd_text)
    app.button[button_labels.index("프로젝트 분석")].click()
    app.run(timeout=120)
    if app.exception:
        v.fail("streamlit_document_flow:analysis_render", "; ".join(str(item.value) for item in app.exception))
        return
    metric_values = {item.label: item.value for item in app.metric}
    success_messages = [item.value for item in app.success]
    v.require("프로젝트 문서 분석이 완료되었습니다." in success_messages, "streamlit_document_flow:success", str(success_messages))
    v.require(metric_values.get("문서 수") == "1", "streamlit_document_flow:project_metrics", str(metric_values))
    v.require(len(app.dataframe) >= 3, "streamlit_document_flow:visible_tables", f"{len(app.dataframe)} dataframes")
    button_labels = [item.label for item in app.button]
    report_button_index = next(
        (index for index, label in enumerate(button_labels) if label.startswith("RPT") and "보고서" in label),
        None,
    )
    if report_button_index is None:
        v.fail("streamlit_report_flow:report_nav_button", str(button_labels))
        return
    app.button[report_button_index].click()
    app.run(timeout=120)
    if app.exception:
        v.fail("streamlit_report_flow:report_render", "; ".join(str(item.value) for item in app.exception))
        return
    warning_messages = [item.value for item in app.warning]
    v.require(
        not any("문서를 먼저 분석" in message or "Analyze a document first" in message for message in warning_messages),
        "streamlit_report_flow:no_reanalysis_warning_after_navigation",
        str(warning_messages),
    )
    source = (ROOT / "src" / "toxiguard_platform" / "app.py").read_text()
    download_labels = ["PDF 보고서 다운로드"] if "st.download_button(" in source and "can_download_report" in source else []
    v.require(
        "PDF 보고서 다운로드" in download_labels or "Download PDF Report" in download_labels,
        "streamlit_report_flow:download_button_present",
        str(download_labels),
    )


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        try:
            from pdfminer.high_level import extract_text

            return extract_text(io.BytesIO(pdf_bytes)) or ""
        except Exception:
            return ""


def write_report(v: Validator) -> Path:
    REPORT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"validation_report_{timestamp}.md"

    total = len(v.results)
    passed = sum(1 for result in v.results if result.status == "PASS")
    warned = sum(1 for result in v.results if result.status == "WARN")
    failed = sum(1 for result in v.results if result.status == "FAIL")

    lines = [
        "# ToxiGuard-Platform Ver.1 Validation Report",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Total checks: {total}",
        f"- PASS: {passed}",
        f"- WARN: {warned}",
        f"- FAIL: {failed}",
        "",
        "| Status | Check | Detail |",
        "| --- | --- | --- |",
    ]
    for result in v.results:
        detail = result.detail.replace("\n", " ").replace("|", "\\|")
        lines.append(f"| {result.status} | `{result.name}` | {detail} |")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    sys.path.insert(0, str(ROOT))
    vendor_path = ROOT / "vendor_py314"
    if vendor_path.exists():
        sys.path.insert(0, str(vendor_path))
    v = Validator()
    checks = [
        check_dependencies,
        check_py_compile,
        check_document_classifier,
        check_project_intake,
        check_specification_table_format,
        check_regulatory_sources,
        check_product_context,
        check_reviewer_correction_logic,
        check_worksheet,
        check_tox_engine,
        check_platform_tools,
        check_reporting,
        check_real_pdf_dependencies,
        check_real_document_pipeline,
        check_streamlit_language_switch,
        check_streamlit_document_analyzer_flow,
    ]

    for check in checks:
        try:
            check(v)
        except Exception:
            v.fail(check.__name__, traceback.format_exc())

    report = write_report(v)
    for result in v.results:
        print(f"{result.status:4} {result.name}: {result.detail}")
    print(f"\nReport: {report}")
    return 1 if v.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
