"""FDA-style reviewer worksheet builders.

The structures here are modeled as a practical review workspace rather than as
official FDA templates. They organize evidence, reviewer judgment, deficiencies,
and final review language in a way that mirrors regulatory assessment work.
"""

from __future__ import annotations

from toxiguard_platform.modules.regulatory_sources import (
    build_regulatory_source_crosswalk,
    build_regulatory_source_matches,
)
from toxiguard_platform.modules.specification_structure import build_specification_writing_structure

DEFAULT_APPLICATION_PROFILE = {
    "application_type": "ANDA",
    "application_number": "TBD",
    "product_name": "TBD",
    "applicant": "TBD",
    "dosage_form": "TBD",
    "route": "TBD",
    "review_cycle": "Cycle 1",
    "discipline_owner": "Quality / Toxicology",
    "review_status": "In Review",
}


def build_reviewer_worksheet(profile: dict, document_summary: dict | None, assessments: list) -> dict:
    """Build a complete worksheet package from document and molecule outputs."""
    summary = document_summary or {}
    clean_profile = {**DEFAULT_APPLICATION_PROFILE, **(profile or {})}

    worksheet = {
        "application_snapshot": clean_profile,
        "submission_map": build_submission_map(summary),
        "product_context": summary.get("product_context", {}),
        "regulatory_source_crosswalk": summary.get("regulatory_source_crosswalk") or build_regulatory_source_crosswalk(summary),
        "regulatory_source_matches": summary.get("regulatory_source_matches") or build_regulatory_source_matches(summary),
        "specification_table": summary.get("specification_table", []),
        "specification_writing_structure": build_specification_writing_structure(summary),
        "quality_assessment": build_quality_assessment(summary),
        "ich_m7_review": build_ich_m7_review(assessments),
        "deficiency_tracker": build_deficiency_tracker(summary, assessments),
        "integrated_assessment": build_integrated_assessment(clean_profile, summary, assessments),
    }
    worksheet["final_review_language"] = build_final_review_language(worksheet)
    return worksheet


def build_submission_map(summary: dict) -> list[dict]:
    rows = []
    signal_details = summary.get("signal_details") or {}
    detail_sources = [
        ("specifications", signal_details.get("specifications", [])),
        ("test_methods", signal_details.get("test_methods", [])),
        ("compounds", signal_details.get("compounds", [])),
        ("stability", signal_details.get("stability", [])),
        ("bioequivalence", signal_details.get("bioequivalence", [])),
    ]
    for _, details in detail_sources:
        for item in details:
            rows.append(
                {
                    "eCTD Section": item.get("CTD Mapping", "Unmapped"),
                    "Evidence Extract": item.get("Evidence", ""),
                    "Source Location": f"Page {item.get('Page', 'N/A')} / {item.get('Evidence Type', 'evidence')}",
                    "Reviewer Note": f"{item.get('Reason', 'Verify against submitted source document.')} Confidence: {item.get('Confidence', 'N/A')}",
                    "Disposition": "Needs review",
                }
            )
    if rows:
        return rows

    for section, items in [
        ("3.2.P.5.1 Specifications", summary.get("specifications", [])),
        ("3.2.P.5.2 Analytical Procedures", summary.get("test_methods", [])),
        ("3.2.P.5.5 Characterisation of Impurities", _compound_items(summary)),
        ("3.2.P.5.6 Justification of Specification", summary.get("specifications", [])),
        ("3.2.P.8 Stability", summary.get("stability", [])),
        ("5.3 Bioequivalence / Comparative Performance", summary.get("bioequivalence", [])),
    ]:
        for index, item in enumerate(items, start=1):
            rows.append(
                {
                    "eCTD Section": section,
                    "Evidence Extract": item,
                    "Source Location": f"Auto-extracted item {index}",
                    "Reviewer Note": "Verify against submitted source document.",
                    "Disposition": "Needs review",
                }
            )
    if not rows:
        rows.append(
            {
                "eCTD Section": "Unmapped",
                "Evidence Extract": "No mapped evidence available.",
                "Source Location": "N/A",
                "Reviewer Note": "Run document analysis or paste CTD text.",
                "Disposition": "Open",
            }
        )
    return rows


def build_quality_assessment(summary: dict) -> list[dict]:
    specs = summary.get("specifications", [])
    stability = summary.get("stability", [])
    bioequivalence = summary.get("bioequivalence", [])
    test_methods = summary.get("test_methods", [])

    rows = [
        _quality_row(
            "Specifications",
            "3.2.P.5.1 / 3.2.P.5.6",
            bool(specs),
            f"{len(specs)} specification signal(s) detected.",
            "Confirm acceptance criteria, analytical procedure linkage, and batch result coverage.",
        ),
        _quality_row(
            "Analytical / Test Methods",
            "3.2.S.4.2 / 3.2.P.5.2 / 3.2.P.5.3",
            bool(test_methods),
            f"{len(test_methods)} test method signal(s) detected.",
            "Confirm method procedure, suitability, validation state, and whether P.2 evidence is only development rationale.",
        ),
        _quality_row(
            "Impurity Control",
            "3.2.P.5.5",
            bool(summary.get("candidate_compounds", [])),
            f"{len(summary.get('candidate_compounds', []))} candidate compound(s) detected.",
            "Confirm impurity identity, origin, qualification threshold, and ICH M7 assessment.",
        ),
        _quality_row(
            "Stability / Packaging",
            "3.2.P.8",
            bool(stability),
            f"{len(stability)} stability signal(s) detected.",
            "Verify storage condition, packaging configuration, trend data, and shelf-life rationale.",
        ),
        _quality_row(
            "Bioequivalence / Performance",
            "Module 5",
            bool(bioequivalence),
            f"{len(bioequivalence)} comparative performance signal(s) detected.",
            "Confirm study design, dissolution similarity, and bridge to proposed product.",
        ),
    ]
    return rows


def build_ich_m7_review(assessments: list) -> list[dict]:
    rows = []
    for index, assessment in enumerate(assessments, start=1):
        alert_names = ", ".join(alert["name"] for alert in assessment.alerts) or "None"
        reference = assessment.experimental_reference or {}
        rows.append(
            {
                "Item": index,
                "SMILES": assessment.smiles,
                "Valid Structure": assessment.valid_structure,
                "Structural Alert": alert_names,
                "ICH M7 Class": assessment.ich_m7_class,
                "Risk Score": assessment.risk_score,
                "Evidence Basis": reference.get("basis", "Prototype structural alert assessment."),
                "Reviewer Conclusion": assessment.conclusion,
                "Control Recommendation": _control_recommendation(assessment),
            }
        )
    if not rows:
        rows.append(
            {
                "Item": 1,
                "SMILES": "N/A",
                "Valid Structure": False,
                "Structural Alert": "N/A",
                "ICH M7 Class": "Unclassified",
                "Risk Score": 0.0,
                "Evidence Basis": "No molecular screening has been performed.",
                "Reviewer Conclusion": "No conclusion available.",
                "Control Recommendation": "Run ICH M7 screening for detected or entered impurities.",
            }
        )
    return rows


def build_deficiency_tracker(summary: dict, assessments: list) -> list[dict]:
    deficiencies = []

    if not summary.get("specifications"):
        deficiencies.append(
            _deficiency(
                "Quality",
                "Specification evidence not identified",
                "Major",
                "Provide complete proposed specifications with acceptance criteria and analytical procedure references.",
            )
        )

    if not summary.get("stability"):
        deficiencies.append(
            _deficiency(
                "Quality",
                "Stability justification not identified",
                "Major",
                "Provide long-term and accelerated stability data supporting the proposed shelf life and storage condition.",
            )
        )

    for assessment in assessments:
        if not assessment.valid_structure:
            deficiencies.append(
                _deficiency(
                    "Toxicology",
                    "Invalid structure string",
                    "Major",
                    f"Provide a valid structure representation for the impurity currently submitted as {assessment.smiles!r}.",
                )
            )
        elif assessment.ich_m7_class in {"Class 1", "Class 3"}:
            deficiencies.append(
                _deficiency(
                    "Toxicology",
                    f"Potential mutagenic impurity concern: {assessment.ich_m7_class}",
                    "Major" if assessment.ich_m7_class == "Class 3" else "Critical",
                    "Provide experimental mutagenicity evidence, purge/control justification, or an acceptable specification limit.",
                )
            )

    if not assessments:
        deficiencies.append(
            _deficiency(
                "Toxicology",
                "ICH M7 screen not completed",
                "Major",
                "Identify all actual and potential impurities and provide ICH M7 assessment with structures where applicable.",
            )
        )

    if not deficiencies:
        deficiencies.append(
            {
                "Discipline": "Integrated",
                "Issue": "No blocking deficiency generated by prototype rules",
                "Severity": "None",
                "Information Request Wording": "No information request proposed by the prototype.",
                "Applicant Response Status": "N/A",
                "Resolution": "Closed",
            }
        )

    return deficiencies


def build_integrated_assessment(profile: dict, summary: dict, assessments: list) -> dict:
    deficiencies = build_deficiency_tracker(summary, assessments)
    open_deficiencies = [item for item in deficiencies if item.get("Resolution") != "Closed"]
    high_risk = [
        item
        for item in assessments
        if item.valid_structure and (item.ich_m7_class in {"Class 1", "Class 3"} or item.risk_score >= 0.66)
    ]

    if high_risk or open_deficiencies:
        recommendation = "Information Request Needed"
        rationale = "Outstanding quality or toxicology issues require applicant clarification before an acceptability conclusion."
    else:
        recommendation = "Acceptable With Expert Confirmation"
        rationale = "Prototype review did not identify blocking quality or ICH M7 concerns."

    return {
        "Application": f"{profile.get('application_type')} {profile.get('application_number')}",
        "Key Review Issues": _key_review_issues(summary, assessments),
        "Residual Uncertainty": _residual_uncertainty(summary, assessments),
        "Recommended Action": recommendation,
        "Rationale": rationale,
    }


def build_final_review_language(worksheet: dict) -> str:
    integrated = worksheet["integrated_assessment"]
    deficiencies = [
        item
        for item in worksheet["deficiency_tracker"]
        if item.get("Resolution") != "Closed" and item.get("Severity") != "None"
    ]

    if deficiencies:
        issue_text = "; ".join(item["Issue"] for item in deficiencies[:4])
        return (
            "Based on the current prototype assessment, the submission is not ready for an acceptability "
            f"conclusion. The following issues should be addressed through an information request: {issue_text}. "
            "Final determination requires discipline reviewer verification of the source submission."
        )

    return (
        f"Based on the current prototype assessment, the recommended action is "
        f"{integrated['Recommended Action']}. {integrated['Rationale']} Final determination requires "
        "discipline reviewer verification of the source submission."
    )


def worksheet_tables_for_export(worksheet: dict) -> dict:
    """Return worksheet content in a PDF-friendly dictionary."""
    return {
        "Application Snapshot": worksheet["application_snapshot"],
        "Integrated Assessment": worksheet["integrated_assessment"],
        "Final Review Language": worksheet["final_review_language"],
        "Product Context": worksheet["product_context"],
        "Deficiency Tracker": worksheet["deficiency_tracker"],
        "ICH M7 Review": worksheet["ich_m7_review"],
        "Quality Assessment": worksheet["quality_assessment"],
        "Specification Table": worksheet["specification_table"],
        "Specification Writing Structure": worksheet["specification_writing_structure"],
        "Regulatory Source Crosswalk": worksheet["regulatory_source_crosswalk"],
        "Regulatory Source Matches": worksheet["regulatory_source_matches"],
        "Submission Map": worksheet["submission_map"],
    }


def _compound_items(summary: dict) -> list[str]:
    return [
        f"{item.get('name', 'Unknown')} ({item.get('role', 'candidate')}): {item.get('smiles', 'N/A')}"
        for item in summary.get("candidate_compounds", [])
    ]


def _quality_row(area: str, section: str, detected: bool, evidence: str, reviewer_task: str) -> dict:
    return {
        "Assessment Area": area,
        "eCTD Anchor": section,
        "Evidence Status": "Detected" if detected else "Not detected",
        "Evidence Summary": evidence,
        "Reviewer Task": reviewer_task,
        "Preliminary Disposition": "Review" if detected else "Information gap",
    }


def _control_recommendation(assessment) -> str:
    if not assessment.valid_structure:
        return "Correct structure before review."
    if assessment.ich_m7_class == "Class 1":
        return "Control as known mutagen or justify with authoritative negative evidence."
    if assessment.ich_m7_class == "Class 3":
        return "Provide confirmatory mutagenicity data or control below acceptable intake."
    return "Document no-alert conclusion and confirm impurity-specific context."


def _deficiency(discipline: str, issue: str, severity: str, wording: str) -> dict:
    return {
        "Discipline": discipline,
        "Issue": issue,
        "Severity": severity,
        "Information Request Wording": wording,
        "Applicant Response Status": "Not requested",
        "Resolution": "Open",
    }


def _key_review_issues(summary: dict, assessments: list) -> str:
    issues = []
    if summary.get("specifications"):
        issues.append("proposed specifications and analytical control strategy")
    if summary.get("test_methods"):
        issues.append("analytical or dissolution method rationale")
    if summary.get("stability"):
        issues.append("stability and packaging support")
    if any(item.ich_m7_class in {"Class 1", "Class 3"} for item in assessments):
        issues.append("potential mutagenic impurity control")
    if not issues:
        issues.append("insufficient extracted evidence")
    return ", ".join(issues)


def _residual_uncertainty(summary: dict, assessments: list) -> str:
    uncertainties = []
    if not summary.get("specifications"):
        uncertainties.append("specification adequacy")
    if not summary.get("stability"):
        uncertainties.append("shelf-life support")
    if not assessments:
        uncertainties.append("mutagenic impurity assessment")
    if any(not item.valid_structure for item in assessments):
        uncertainties.append("structure validity")
    if not uncertainties:
        uncertainties.append("source-document verification by discipline reviewer")
    return ", ".join(uncertainties)
