"""Official and public CTD/eCTD source library for reviewer cross-checks."""

from __future__ import annotations

import re


CATEGORY_LABELS = {
    "specifications": "Specifications / 기준",
    "test_methods": "Test Methods / 시험방법",
    "bioequivalence": "Bioequivalence / 생동성",
    "stability": "Stability / 안정성",
    "compounds": "Compounds / 불순물·성분",
}

CATEGORY_ORDER = ["specifications", "test_methods", "bioequivalence", "stability", "compounds"]


SOURCE_LIBRARY = [
    {
        "Short Name": "ICH M4 CTD",
        "Authority": "ICH",
        "Jurisdiction": "International",
        "Source Type": "Official guideline",
        "Document / Resource": "M4: The Common Technical Document",
        "Use In Review": "Defines the common CTD module structure and anchors quality, safety, and efficacy content.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["Module 2", "Module 3", "Module 4", "Module 5"],
        "URL": "https://www.ich.org/page/ctd",
        "Access Note": "Public web page with guideline files.",
    },
    {
        "Short Name": "ICH M4Q Quality",
        "Authority": "ICH",
        "Jurisdiction": "International",
        "Source Type": "Official guideline",
        "Document / Resource": "M4Q: Quality sections of the Common Technical Document",
        "Use In Review": "Frames Module 3 quality sections, including S.4/P.5 controls and stability links.",
        "Related Categories": ["specifications", "test_methods", "stability", "compounds"],
        "CTD Sections": ["3.2.S", "3.2.P"],
        "URL": "https://www.ich.org/page/ctd",
        "Access Note": "Public web page with M4Q materials.",
    },
    {
        "Short Name": "FDA M4Q(R2) Draft",
        "Authority": "FDA / ICH",
        "Jurisdiction": "United States / International",
        "Source Type": "Draft official guidance",
        "Document / Resource": "M4Q(R2) CTD Quality draft guidance",
        "Use In Review": "Emerging quality-dossier organization reference; use as draft context, not as final requirement.",
        "Related Categories": ["specifications", "test_methods", "stability", "compounds"],
        "CTD Sections": ["Module 3"],
        "URL": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/m4qr2-common-technical-document-registration-pharmaceuticals-human-use-quality",
        "Access Note": "Draft guidance; not for implementation until finalized.",
    },
    {
        "Short Name": "ICH Q6A",
        "Authority": "ICH / FDA",
        "Jurisdiction": "International / United States",
        "Source Type": "Official guideline",
        "Document / Resource": "Specifications: Test Procedures and Acceptance Criteria",
        "Use In Review": "Primary basis for tests, analytical procedure references, acceptance criteria, and justification of specifications.",
        "Related Categories": ["specifications", "test_methods", "compounds", "stability"],
        "CTD Sections": ["3.2.S.4", "3.2.P.5", "3.2.P.8"],
        "URL": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/q6a-specifications-test-procedures-and-acceptance-criteria-new-drug-substances-and-new-drug-products",
        "Access Note": "Public FDA guidance page carrying ICH Q6A text.",
    },
    {
        "Short Name": "ICH Q2(R2)",
        "Authority": "ICH / FDA",
        "Jurisdiction": "International / United States",
        "Source Type": "Official guideline",
        "Document / Resource": "Validation of Analytical Procedures",
        "Use In Review": "Checks method validation characteristics such as specificity, accuracy, precision, linearity, range, LOD, and LOQ.",
        "Related Categories": ["test_methods", "specifications"],
        "CTD Sections": ["3.2.S.4.3", "3.2.P.5.3"],
        "URL": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/q2r2-validation-analytical-procedures",
        "Access Note": "Public final guidance page.",
    },
    {
        "Short Name": "ICH Q14",
        "Authority": "ICH / FDA",
        "Jurisdiction": "International / United States",
        "Source Type": "Official guideline",
        "Document / Resource": "Analytical Procedure Development",
        "Use In Review": "Supports method development rationale and lifecycle-oriented analytical control strategy.",
        "Related Categories": ["test_methods", "specifications"],
        "CTD Sections": ["3.2.P.2", "3.2.P.5.2", "3.2.P.5.3"],
        "URL": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/q14-analytical-procedure-development",
        "Access Note": "Public final guidance page.",
    },
    {
        "Short Name": "ICH Q1A/Q1B",
        "Authority": "ICH",
        "Jurisdiction": "International",
        "Source Type": "Official guideline",
        "Document / Resource": "Stability testing and photostability principles",
        "Use In Review": "Supports storage condition, shelf-life, photostability, packaging, and stability-indicating method review.",
        "Related Categories": ["stability", "specifications", "test_methods"],
        "CTD Sections": ["3.2.S.7", "3.2.P.8"],
        "URL": "https://www.ich.org/page/quality-guidelines",
        "Access Note": "Public ICH quality guideline index.",
    },
    {
        "Short Name": "ICH Q3 / M7",
        "Authority": "ICH",
        "Jurisdiction": "International",
        "Source Type": "Official guideline",
        "Document / Resource": "Impurities, residual solvents, elemental impurities, and mutagenic impurities",
        "Use In Review": "Supports impurity identity, qualification thresholds, residual solvent controls, elemental impurity controls, and ICH M7 alerts.",
        "Related Categories": ["compounds", "specifications", "test_methods"],
        "CTD Sections": ["3.2.S.3.2", "3.2.P.5.5", "3.2.P.5.6"],
        "URL": "https://www.ich.org/page/quality-guidelines",
        "Access Note": "Public ICH quality guideline index.",
    },
    {
        "Short Name": "FDA eCTD",
        "Authority": "FDA",
        "Jurisdiction": "United States",
        "Source Type": "Official submission standard",
        "Document / Resource": "Electronic Common Technical Document (eCTD)",
        "Use In Review": "Checks submission format, required eCTD use, supported versions, and FDA submission scope.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["Module 1", "Module 2", "Module 3", "Module 4", "Module 5"],
        "URL": "https://www.fda.gov/drugs/electronic-regulatory-submission-and-review/electronic-common-technical-document-ectd",
        "Access Note": "Public FDA eCTD hub.",
    },
    {
        "Short Name": "FDA eCTD Resources",
        "Authority": "FDA",
        "Jurisdiction": "United States",
        "Source Type": "Official technical resources",
        "Document / Resource": "eCTD resources, submission standards, and technical conformance files",
        "Use In Review": "Supports validation of FDA eCTD technical packaging and lifecycle submissions.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["eCTD v3.2.2", "eCTD v4.0", "Regional M1"],
        "URL": "https://www.fda.gov/drugs/electronic-regulatory-submission-and-review/ectd-resources",
        "Access Note": "Public FDA resources page.",
    },
    {
        "Short Name": "FDA eCTD v4.0",
        "Authority": "FDA",
        "Jurisdiction": "United States",
        "Source Type": "Official technical resources",
        "Document / Resource": "Electronic Common Technical Document (eCTD) v4.0",
        "Use In Review": "Supports new-application v4.0 planning and controlled vocabulary/implementation package checks.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["eCTD v4.0", "Regional M1"],
        "URL": "https://www.fda.gov/drugs/electronic-regulatory-submission-and-review/electronic-common-technical-document-ectd-v40",
        "Access Note": "Public FDA v4.0 implementation page.",
    },
    {
        "Short Name": "EMA eSubmission",
        "Authority": "EMA",
        "Jurisdiction": "European Union",
        "Source Type": "Official submission standard",
        "Document / Resource": "eCTD guidance and EU eSubmission materials",
        "Use In Review": "Supports EU eCTD structure, validation, and submission lifecycle review.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["EU Module 1", "Module 2", "Module 3", "Module 4", "Module 5"],
        "URL": "https://esubmission.ema.europa.eu/ectd/index.html",
        "Access Note": "Public EMA eSubmission page.",
    },
    {
        "Short Name": "EU Module 1",
        "Authority": "EMA / EU",
        "Jurisdiction": "European Union",
        "Source Type": "Official regional module",
        "Document / Resource": "EU Module 1 eCTD specification",
        "Use In Review": "Supports EU regional administrative content and Module 1 placement checks.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["EU Module 1"],
        "URL": "https://esubmission.ema.europa.eu/eumodule1/index.htm",
        "Access Note": "Public EU Module 1 page.",
    },
    {
        "Short Name": "MFDS eCTD Manual",
        "Authority": "MFDS",
        "Jurisdiction": "Korea",
        "Source Type": "Official guidance notice",
        "Document / Resource": "전자국제공통기술문서(eCTD) 자료작성 매뉴얼",
        "Use In Review": "Supports Korean eCTD dossier assembly, file format, security, and Q&A expectations.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["Module 1", "Module 2", "Module 3", "Module 4", "Module 5"],
        "URL": "https://www.mfds.go.kr/brd/m_99/view.do?seq=46841",
        "Access Note": "Public MFDS notice; attached files may change by posting.",
    },
    {
        "Short Name": "MFDS Quality CTD Q&A",
        "Authority": "MFDS / NIFDS",
        "Jurisdiction": "Korea",
        "Source Type": "Official guidance notice",
        "Document / Resource": "국제공통기술문서 작성 질의응답집(품질) / 신약 규격설정 가이드라인",
        "Use In Review": "Supports Korean quality CTD writing, specification-setting rationale, and reviewer-facing CMC organization.",
        "Related Categories": ["specifications", "test_methods", "stability", "compounds"],
        "CTD Sections": ["3.2.P.2", "3.2.P.5", "3.2.P.8"],
        "URL": "https://www.mfds.go.kr/brd/m_99/view.do?seq=44651",
        "Access Note": "Public MFDS notice; attached guidance files may change by posting.",
    },
    {
        "Short Name": "MFDS BE Standard",
        "Authority": "MFDS",
        "Jurisdiction": "Korea",
        "Source Type": "Official regulation notice",
        "Document / Resource": "의약품동등성시험기준",
        "Use In Review": "Supports Korean bioequivalence, comparative dissolution, reference product, and equivalence-judgment checks.",
        "Related Categories": ["bioequivalence", "test_methods", "specifications"],
        "CTD Sections": ["Module 5", "5.3.1", "3.2.P.2"],
        "URL": "https://mfds.go.kr/brd/m_207/view.do?seq=14715",
        "Access Note": "Public MFDS regulation notice; verify latest consolidated rule separately.",
    },
    {
        "Short Name": "USP-NF",
        "Authority": "USP",
        "Jurisdiction": "United States / Pharmacopeial",
        "Source Type": "Official compendial standard",
        "Document / Resource": "USP-NF monographs and general chapters",
        "Use In Review": "Supports compendial methods such as chromatography, residual solvents, identification, and general tests.",
        "Related Categories": ["specifications", "test_methods", "compounds"],
        "CTD Sections": ["3.2.S.4", "3.2.P.5"],
        "URL": "https://www.usp.org/excipients/general-chapters",
        "Access Note": "Public overview; USP-NF text generally requires subscription or licensed access.",
    },
    {
        "Short Name": "Ph. Eur.",
        "Authority": "EDQM",
        "Jurisdiction": "Europe / Pharmacopeial",
        "Source Type": "Official compendial standard",
        "Document / Resource": "European Pharmacopoeia",
        "Use In Review": "Supports EP monograph/general-chapter alignment and European quality-control standards.",
        "Related Categories": ["specifications", "test_methods", "compounds", "stability"],
        "CTD Sections": ["3.2.S.4", "3.2.P.5", "3.2.P.8"],
        "URL": "https://www.edqm.eu/en/web/edqm/european-pharmacopoeia",
        "Access Note": "Public overview; Ph. Eur. Online access generally requires a license.",
    },
    {
        "Short Name": "PMDA eCTD v4",
        "Authority": "PMDA",
        "Jurisdiction": "Japan",
        "Source Type": "Official submission standard",
        "Document / Resource": "eCTD version 4 domestic implementation package",
        "Use In Review": "Supports Japan eCTD v4 implementation guide, file specification, and validation package checks.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["eCTD v4.0", "JP Module 1"],
        "URL": "https://www.pmda.go.jp/int-activities/int-harmony/ich/0119.html",
        "Access Note": "Public PMDA page with Japanese and English implementation materials.",
    },
    {
        "Short Name": "Health Canada eCTD",
        "Authority": "Health Canada",
        "Jurisdiction": "Canada",
        "Source Type": "Official validation rules",
        "Document / Resource": "Validation rules for eCTD regulatory transactions",
        "Use In Review": "Supports PDF, XML, folder, sequence, lifecycle, and validation-rule checks.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["Canadian Module 1", "eCTD v3.2.2"],
        "URL": "https://www.canada.ca/en/health-canada/services/drugs-health-products/drug-products/applications-submissions/guidance-documents/ectd/notice-validation-rules-regulatory-transactions-submitted-health-canada-electronic-common-technical-document-format-2016-12-1.html",
        "Access Note": "Public Health Canada validation rules page.",
    },
    {
        "Short Name": "TGA CTD",
        "Authority": "TGA",
        "Jurisdiction": "Australia",
        "Source Type": "Official CTD guidance",
        "Document / Resource": "Understanding the Common Technical Document",
        "Use In Review": "Supports CTD module orientation and Australian dossier organization.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["Module 1", "Module 2", "Module 3", "Module 4", "Module 5"],
        "URL": "https://www.tga.gov.au/resources/guidance/understanding-common-technical-document-ctd",
        "Access Note": "Public TGA guidance page.",
    },
    {
        "Short Name": "TGA eCTD AU M1",
        "Authority": "TGA",
        "Jurisdiction": "Australia",
        "Source Type": "Official regional module",
        "Document / Resource": "eCTD AU module 1 and regional information",
        "Use In Review": "Supports AU regional Module 1 and validation criteria checks.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["AU Module 1", "eCTD"],
        "URL": "https://www.tga.gov.au/resources/resources/user-guide/ectd-au-module-1-and-regional-information-v32",
        "Access Note": "Public TGA technical resource page.",
    },
    {
        "Short Name": "MHRA eCTD",
        "Authority": "MHRA",
        "Jurisdiction": "United Kingdom",
        "Source Type": "Official submission guidance",
        "Document / Resource": "eCTD guidance for marketing authorisation and post-authorisation applications",
        "Use In Review": "Supports UK eCTD sequence and lifecycle expectations for marketing authorisation work.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["UK Module 1", "eCTD"],
        "URL": "https://www.gov.uk/government/publications/international-recognition-procedure/ectd-guidance-for-irp-mas-and-lifecycle",
        "Access Note": "Public GOV.UK guidance page.",
    },
    {
        "Short Name": "Swissmedic eCTD",
        "Authority": "Swissmedic",
        "Jurisdiction": "Switzerland",
        "Source Type": "Official submission guidance",
        "Document / Resource": "Swiss eCTD guidance and validation criteria",
        "Use In Review": "Supports Swiss Module 1, validation criteria, and eCTD lifecycle checks.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["Swiss Module 1", "eCTD v3.2.2"],
        "URL": "https://www.swissmedic.ch/swissmedic/en/home/services/submissions/ectd.html",
        "Access Note": "Public Swissmedic eCTD page.",
    },
    {
        "Short Name": "WHO CTD",
        "Authority": "WHO",
        "Jurisdiction": "International",
        "Source Type": "Official public-health dossier guidance",
        "Document / Resource": "CTD preparation and submission",
        "Use In Review": "Supports CTD-based dossier preparation for WHO prequalification contexts.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["Module 1", "Module 2", "Module 3", "Module 4", "Module 5"],
        "URL": "https://extranet.who.int/prequal/vaccines/ctd-preparation-submission",
        "Access Note": "Public WHO prequalification page.",
    },
    {
        "Short Name": "ASEAN ACTD",
        "Authority": "ASEAN / NPRA mirror",
        "Jurisdiction": "ASEAN",
        "Source Type": "Official regional dossier guideline",
        "Document / Resource": "ASEAN Common Technical Dossier organization",
        "Use In Review": "Supports ACTD organization where ASEAN dossier format is used instead of ICH CTD.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["ACTD Parts I-IV"],
        "URL": "https://www.npra.gov.my/images/Guidelines_Central/ASEAN_Common_Technical_Dossier_ACTD/ACTD_OrganizationofDossier.pdf",
        "Access Note": "Public PDF hosted by Malaysia NPRA.",
    },
    {
        "Short Name": "HSA eCTD",
        "Authority": "HSA",
        "Jurisdiction": "Singapore",
        "Source Type": "Official submission standard",
        "Document / Resource": "Singapore eCTD submissions",
        "Use In Review": "Supports Singapore eCTD v1.1 implementation, document matrix, and portal submission planning.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["SG Module 1", "eCTD"],
        "URL": "https://www.hsa.gov.sg/therapeutic-products/register/ectd-submissions",
        "Access Note": "Public HSA page.",
    },
    {
        "Short Name": "GitHub eCTD Indexer",
        "Authority": "Open-source community",
        "Jurisdiction": "Tooling",
        "Source Type": "Open-source tool",
        "Document / Resource": "dayzero/ectd_indexer",
        "Use In Review": "Can inspire local parsing of eCTD index XML and dossier folder metadata.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["index.xml", "regional XML"],
        "URL": "https://github.com/dayzero/ectd_indexer",
        "Access Note": "Public GitHub repository; validate license before reuse.",
    },
    {
        "Short Name": "EU XML Validator",
        "Authority": "European Commission / ISAITB",
        "Jurisdiction": "Tooling",
        "Source Type": "Open-source validator",
        "Document / Resource": "ISAITB/xml-validator",
        "Use In Review": "Can inspire XML validation workflows for eCTD backbones and regional metadata.",
        "Related Categories": CATEGORY_ORDER,
        "CTD Sections": ["XML validation"],
        "URL": "https://github.com/ISAITB/xml-validator",
        "Access Note": "Public GitHub repository; general XML validator, not CTD-specific by itself.",
    },
]


SOURCE_PRIORITY = {
    "specifications": ["ICH Q6A", "MFDS Quality CTD Q&A", "ICH M4Q Quality", "FDA M4Q(R2) Draft", "USP-NF", "Ph. Eur."],
    "test_methods": ["ICH Q2(R2)", "ICH Q14", "ICH Q6A", "MFDS Quality CTD Q&A", "USP-NF", "Ph. Eur."],
    "bioequivalence": ["MFDS BE Standard", "ICH M4 CTD", "FDA eCTD", "HSA eCTD"],
    "stability": ["ICH Q1A/Q1B", "ICH M4Q Quality", "ICH Q6A", "MFDS Quality CTD Q&A", "Ph. Eur."],
    "compounds": ["ICH Q3 / M7", "ICH M4Q Quality", "ICH Q6A", "USP-NF", "Ph. Eur."],
}


def source_catalog_rows(category: str | None = None, source_type: str | None = None) -> list[dict]:
    """Return a dataframe-friendly view of the source library."""
    rows = []
    for source in SOURCE_LIBRARY:
        if category and category != "All" and category not in source["Related Categories"]:
            continue
        if source_type and source_type != "All" and source["Source Type"] != source_type:
            continue
        rows.append(_public_source_row(source))
    return rows


def source_type_options() -> list[str]:
    return ["All"] + sorted({source["Source Type"] for source in SOURCE_LIBRARY})


def category_options() -> list[str]:
    return ["All"] + CATEGORY_ORDER


def build_regulatory_source_crosswalk(summary: dict | None) -> list[dict]:
    """Summarize which source families should be used for each extracted signal type."""
    summary = summary or {}
    signal_details = summary.get("signal_details") or {}
    rows = []
    for category in CATEGORY_ORDER:
        sources = sources_for_category(category)
        rows.append(
            {
                "Signal Category": CATEGORY_LABELS[category],
                "Detected Signals": len(signal_details.get(category, [])),
                "Primary CTD / Review Anchor": _primary_anchor_for_category(category),
                "Primary Standards": _join(source["Short Name"] for source in sources[:5]),
                "Reviewer Use": _reviewer_use_for_category(category),
                "Primary URLs": _join(source["URL"] for source in sources[:3]),
            }
        )
    return rows


def build_regulatory_source_matches(summary: dict | None, limit: int = 120) -> list[dict]:
    """Attach source references to each extracted evidence row."""
    summary = summary or {}
    signal_details = summary.get("signal_details") or {}
    rows = []
    for category in CATEGORY_ORDER:
        for signal in signal_details.get(category, []):
            sources = sources_for_category(category, signal.get("CTD Mapping", "") + " " + signal.get("Evidence", ""))
            primary = sources[0] if sources else None
            rows.append(
                {
                    "Signal Category": CATEGORY_LABELS[category],
                    "Evidence Summary": _compact(signal.get("Evidence", ""), 220),
                    "Page": signal.get("Page", "N/A"),
                    "Evidence Role": signal.get("Evidence Role", "Direct Evidence"),
                    "CTD Mapping": signal.get("CTD Mapping", "Unmapped"),
                    "Primary Source": primary["Short Name"] if primary else "No source mapped",
                    "Authority": primary["Authority"] if primary else "N/A",
                    "Reviewer Use": primary["Use In Review"] if primary else "Manual source review required.",
                    "Additional Sources": _join(source["Short Name"] for source in sources[1:4]),
                    "URL": primary["URL"] if primary else "",
                }
            )
            if len(rows) >= limit:
                return rows
    return rows


def sources_for_category(category: str, evidence_context: str = "") -> list[dict]:
    """Return ranked sources for a signal category and optional evidence context."""
    matches = [source for source in SOURCE_LIBRARY if category in source["Related Categories"]]
    return sorted(matches, key=lambda source: _rank_source(source, category, evidence_context))


def _rank_source(source: dict, category: str, evidence_context: str) -> tuple[int, int, str]:
    priority = SOURCE_PRIORITY.get(category, [])
    try:
        base = priority.index(source["Short Name"])
    except ValueError:
        base = 99

    context_score = 9
    context = evidence_context or ""
    for section in source["CTD Sections"]:
        if section and re.search(re.escape(section), context, flags=re.IGNORECASE):
            context_score = 0
            break
    if source["Authority"] in {"FDA", "FDA / ICH", "ICH", "ICH / FDA"}:
        context_score = min(context_score, 2)
    return (base, context_score, source["Short Name"])


def _public_source_row(source: dict) -> dict:
    return {
        "Short Name": source["Short Name"],
        "Authority": source["Authority"],
        "Jurisdiction": source["Jurisdiction"],
        "Source Type": source["Source Type"],
        "Document / Resource": source["Document / Resource"],
        "Related Categories": _join(CATEGORY_LABELS.get(category, category) for category in source["Related Categories"]),
        "CTD Sections": _join(source["CTD Sections"]),
        "Use In Review": source["Use In Review"],
        "Access Note": source["Access Note"],
        "URL": source["URL"],
    }


def _primary_anchor_for_category(category: str) -> str:
    return {
        "specifications": "3.2.S.4 / 3.2.P.5.1 / 3.2.P.5.6",
        "test_methods": "3.2.P.2 / 3.2.S.4.2 / 3.2.P.5.2 / 3.2.P.5.3",
        "bioequivalence": "Module 5 / 5.3.1 / comparative dissolution",
        "stability": "3.2.S.7 / 3.2.P.8",
        "compounds": "3.2.S.3.2 / 3.2.P.5.5 / ICH M7",
    }[category]


def _reviewer_use_for_category(category: str) -> str:
    return {
        "specifications": "Check whether each test has an acceptance criterion, analytical procedure reference, and justification.",
        "test_methods": "Check procedure description, method development rationale, suitability, and validation expectations.",
        "bioequivalence": "Check BE/comparative dissolution evidence against Module 5 and local equivalence criteria.",
        "stability": "Check storage conditions, time points, packaging, trends, and shelf-life justification.",
        "compounds": "Check API, excipient, impurity, degradation product, solvent, elemental impurity, and ICH M7 controls.",
    }[category]


def _compact(text: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _join(values) -> str:
    return " | ".join(str(value) for value in values if value)
