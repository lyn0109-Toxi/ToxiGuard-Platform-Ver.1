"""Document extraction and CTD-oriented text analysis."""

from __future__ import annotations

import io
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from toxiguard_platform.modules.regulatory_ontology import (
    CATEGORY_META,
    KNOWN_COMPOUNDS,
    classify_document_signals,
    detect_document_profile,
    split_evidence_blocks,
)
from toxiguard_platform.modules.product_context import build_product_context
from toxiguard_platform.modules.regulatory_sources import (
    build_regulatory_source_crosswalk,
    build_regulatory_source_matches,
)
from toxiguard_platform.modules.specification_structure import (
    build_specification_outline,
    build_specification_table,
    build_specification_writing_structure,
)


_VENDOR_PATH = Path(__file__).resolve().parents[3] / "vendor_py314"
if _VENDOR_PATH.exists() and str(_VENDOR_PATH) not in sys.path:
    sys.path.insert(0, str(_VENDOR_PATH))


@dataclass
class DocumentResult:
    text: str
    source: str
    bytes_received: int
    warnings: list[str]
    pages: list[dict]


def extract_document_text(content: bytes, content_type: str | None) -> DocumentResult:
    """Extract text from a PDF, DOCX, TXT, or image-like upload."""
    content_type = content_type or ""
    warnings: list[str] = []
    normalized_type = content_type.lower()

    if "pdf" in normalized_type:
        pages = _extract_pdf_pages(content, warnings)
    elif "wordprocessingml" in normalized_type or "msword" in normalized_type:
        text = _extract_docx_text(content, warnings)
        pages = [{"page": 1, "text": text}]
    elif normalized_type.startswith("text/") or normalized_type in {"", "application/octet-stream"}:
        text = _extract_plain_text(content, warnings)
        if text.strip():
            pages = [{"page": 1, "text": text}]
        else:
            text = _extract_image(content, warnings)
            pages = [{"page": 1, "text": text}]
    else:
        text = _extract_image(content, warnings)
        pages = [{"page": 1, "text": text}]

    text = _join_pages(pages)

    return DocumentResult(
        text=text.strip() or "[No text extracted]",
        source=content_type,
        bytes_received=len(content),
        warnings=warnings,
        pages=pages,
    )


def _extract_plain_text(content: bytes, warnings: list[str]) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp949", "euc-kr", "latin-1"):
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            continue
        if _looks_like_text(text):
            return text
    warnings.append("Plain-text decoding did not produce reviewable text.")
    return ""


def _looks_like_text(text: str) -> bool:
    if not text.strip():
        return False
    sample = text[:4000]
    printable = len(re.findall(r"[\w\s.,;:()/+\-%가-힣]", sample))
    return printable / max(len(sample), 1) >= 0.72


def _extract_docx_text(content: bytes, warnings: list[str]) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml")
    except KeyError:
        warnings.append("DOCX document.xml was not found.")
        return ""
    except zipfile.BadZipFile:
        warnings.append("DOCX extraction failed because the file is not a valid DOCX archive.")
        return ""
    except Exception as exc:
        warnings.append(f"DOCX extraction failed: {exc}")
        return ""

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as exc:
        warnings.append(f"DOCX XML parsing failed: {exc}")
        return ""

    namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespaces):
        parts = [node.text for node in paragraph.findall(".//w:t", namespaces) if node.text]
        if parts:
            paragraphs.append("".join(parts))
    return "\n".join(paragraphs)


def _extract_pdf_pages(content: bytes, warnings: list[str]) -> list[dict]:
    pypdf_pages = _extract_pdf_pages_with_pypdf(content, warnings)
    if _has_reviewable_pdf_text(pypdf_pages):
        return pypdf_pages
    if (
        pypdf_pages
        and _pages_quality_score(pypdf_pages) >= 0.72
        and _pages_artifact_rate(pypdf_pages) <= 1.2
    ):
        return pypdf_pages

    pdfminer_pages = _extract_pdf_pages_with_pdfminer(content, warnings)
    if pypdf_pages and pdfminer_pages:
        return _choose_better_pages(pypdf_pages, pdfminer_pages)
    if pdfminer_pages:
        return pdfminer_pages
    if pypdf_pages:
        return pypdf_pages
    return [{"page": 1, "text": ""}]


def _has_reviewable_pdf_text(pages: list[dict]) -> bool:
    """Return True when pypdf already produced enough CTD text to review.

    Some regulatory PDFs are text-readable but have line-spacing artifacts that
    make a strict quality score look worse than the actual reviewer value. In
    that case, using pypdf immediately is better than falling into a slow
    whole-document pdfminer pass.
    """
    if not pages:
        return False
    text = "\n".join(page.get("text", "") for page in pages)
    chars = len(text.strip())
    if chars < 1500:
        return False
    meaningful = len(re.findall(r"[A-Za-z가-힣0-9]", text))
    meaningful_ratio = meaningful / max(len(text), 1)
    markers = len(
        re.findall(
            r"3\.2\.|CTD|pharmaceutical development|specification|method|"
            r"dissolution|stability|formulation|excipient|제품명|주성분|"
            r"기준|시험방법|용출|안정성|제형|첨가제",
            text,
            flags=re.IGNORECASE,
        )
    )
    damaged = len(re.findall(r"[■�□]", text))
    return meaningful_ratio >= 0.45 and markers >= 3 and damaged <= max(chars * 0.02, 20)


def _extract_pdf_pages_with_pypdf(content: bytes, warnings: list[str]) -> list[dict]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                warnings.append(f"pypdf page {index} extraction failed: {exc}")
                text = ""
            pages.append({"page": index, "text": text})
        if any(page["text"].strip() for page in pages):
            return pages
    except ImportError:
        warnings.append("pypdf is not installed; trying pdfminer.six for PDF text extraction.")
    except Exception as exc:
        warnings.append(f"pypdf PDF extraction failed; trying pdfminer.six. Detail: {exc}")
    return []


def _extract_pdf_pages_with_pdfminer(content: bytes, warnings: list[str]) -> list[dict]:
    try:
        from pdfminer.high_level import extract_text

        text = extract_text(io.BytesIO(content)) or ""
        parts = [part.strip("\n") for part in text.split("\f")]
        pages = [
            {"page": index + 1, "text": part}
            for index, part in enumerate(parts)
            if part.strip()
        ]
        if pages:
            return pages
    except ImportError:
        warnings.append("pdfminer.six is not installed, so PDF text extraction is unavailable.")
    except Exception as exc:
        warnings.append(f"PDF extraction failed: {exc}")
    return []


def _choose_better_pages(primary_pages: list[dict], secondary_pages: list[dict]) -> list[dict]:
    primary_score = _pages_quality_score(primary_pages) - (_pages_artifact_rate(primary_pages) * 0.03)
    secondary_score = _pages_quality_score(secondary_pages) - (_pages_artifact_rate(secondary_pages) * 0.03)
    return secondary_pages if secondary_score > primary_score else primary_pages


def _pages_quality_score(pages: list[dict]) -> float:
    text = "\n".join(page.get("text", "") for page in pages)
    if not text.strip():
        return 0.0
    chars = len(text)
    meaningful = len(re.findall(r"[A-Za-z가-힣0-9]", text))
    markers = len(
        re.findall(
            r"3\.2\.|specification|assay|HPLC|method|stability|dissolution|제품명|주성분|기준|시험방법|함량|안정성|용출",
            text,
            flags=re.IGNORECASE,
        )
    )
    damaged = len(re.findall(r"[■�□]", text))
    meaningful_ratio = meaningful / max(chars, 1)
    damage_penalty = min(damaged / max(chars, 1), 0.4)
    length_score = min(chars / 2500, 1.0)
    marker_score = min(markers / 12, 1.0)
    return round((meaningful_ratio * 0.45) + (length_score * 0.35) + (marker_score * 0.2) - damage_penalty, 3)


def _pages_artifact_rate(pages: list[dict]) -> float:
    """Estimate word-spacing artifacts common in PDF text extraction."""
    text = "\n".join(page.get("text", "") for page in pages)
    chars = len(text)
    if chars <= 0:
        return 0.0
    spaced_hyphen = len(re.findall(r"[A-Za-z]\s+-\s*[A-Za-z]", text))
    split_tail_letter = len(re.findall(r"\b[A-Za-z]{2,}\s+[bcdefghjklmnopqrstuvwxyz]\b", text))
    odd_space_before_punct = len(re.findall(r"\s+[.,;:)]", text))
    weighted = (spaced_hyphen * 2) + (split_tail_letter * 3) + odd_space_before_punct
    return round(weighted / max(chars / 1000, 1), 3)


def _extract_image(content: bytes, warnings: list[str]) -> str:
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(content))
        try:
            return pytesseract.image_to_string(image, lang="kor+eng")
        except Exception as exc:
            warnings.append(f"Korean OCR language pack may be unavailable; retried with default OCR. Detail: {exc}")
            return pytesseract.image_to_string(image)
    except ImportError:
        warnings.append("pytesseract or Pillow is not installed, so image OCR is unavailable.")
    except Exception as exc:
        warnings.append(f"Image OCR failed: {exc}")
    return ""


def analyze_ctd_text(text: str) -> dict:
    """Extract practical regulatory signals from CTD-like text."""
    summary = {
        "specifications": [],
        "test_methods": [],
        "bioequivalence": [],
        "stability": [],
        "candidate_compounds": [],
        "signal_details": {
            "specifications": [],
            "test_methods": [],
            "bioequivalence": [],
            "stability": [],
            "compounds": [],
        },
        "evidence_blocks": [],
        "document_profile": {},
        "product_context": {},
        "regulatory_source_crosswalk": [],
        "regulatory_source_matches": [],
        "specification_table": [],
        "writing_structure": [],
        "writing_outline": "",
        "language": "Korean/English" if _contains_korean(text) else "English/Other",
        "narrative": "",
    }

    if not text or len(text.strip()) < 10:
        summary["narrative"] = "The uploaded document did not contain enough readable text for analysis."
        return summary

    fallback_text = re.sub(r"\s*---\s*PAGE\s+\d+\s*---\s*", " ", text, flags=re.IGNORECASE)
    clean_text = re.sub(r"\s+", " ", fallback_text)
    text_lower = clean_text.lower()
    summary["evidence_blocks"] = split_evidence_blocks(text)
    summary["document_profile"] = detect_document_profile(text)
    signal_details = classify_document_signals(text)
    summary["signal_details"] = signal_details

    summary["specifications"] = _unique(
        [row["Evidence"] for row in signal_details.get("specifications", [])]
        +
        _find_all(r"(Assay[^0-9]*[0-9.]+\s*[-–]\s*[0-9.]+\s*%)", clean_text)
        + _find_all(r"([^.;]*impurity[^.;]*not more than [0-9.]+\s*%)", clean_text)
        + _find_all(r"(Hardness[^.;]*[0-9]+[ -]*[0-9]+\s*k[bg])", clean_text)
        + _find_all(r"(Friability[^.;]*not more than[^%]+%)", clean_text)
        + _find_all(r"((?:함량|정량법|역가|순도)[^.;。]*[0-9.]+\s*(?:-|~|–|이상|부터)\s*[0-9.]+\s*%)", clean_text)
        + _find_all(r"((?:유연물질|불순물|개개\s*불순물|총\s*불순물)[^.;。]*(?:[0-9.]+\s*%\s*이하|이하\s*[0-9.]+\s*%|NMT\s*[0-9.]+\s*%))", clean_text)
        + _find_all(r"((?:경도|마손도|붕해|수분)[^.;。]*(?:[0-9.]+\s*(?:kg|kp|%|분)|이하[^.;。]*%))", clean_text)
    )

    summary["test_methods"] = _unique(
        _filter_method_evidence(
            [row["Evidence"] for row in signal_details.get("test_methods", [])]
            + _find_all(r"([^.;。]*(?:analytical method|analytical procedure|test method|HPLC|UPLC|GC|ICP-MS|UV|dissolution test condition|dissolution method|method validation|method transfer)[^.;。]*(?:[.;。]|$))", clean_text)
            + _find_all(r"([^.;。]*(?:standard solution|reference solution|sample solution|test solution|standard preparation|sample preparation|표준액|표준용액|검액|시험액|시료액)[^.;。]*(?:mg/mL|µg/mL|ug/mL|mcg/mL|ng/mL|mg/L|ppm|%|㎎/mL|㎍/mL)[^.;。]*(?:[.;。]|$))", clean_text)
            + _find_solution_phrases(clean_text)
            + _find_all(r"([^.;。]*(?:시험방법|분석법|기시법|용출\s*조건|용출\s*시험방법|밸리데이션|시험법\s*이전|공정서|별규)[^.;。]*(?:[.;。]|$))", clean_text)
        )
    )

    summary["bioequivalence"] = _unique(
        [row["Evidence"] for row in signal_details.get("bioequivalence", [])]
        +
        _find_all(r"([^.;]*dissolution factor 2 was [0-9]+[^.;]*[.;])", clean_text)
        + _find_all(r"([^.;]*pharmaceutical equivalent[^.;]*[.;])", clean_text)
        + _find_all(r"([^.;]*bioequivalence[^.;]*[.;])", clean_text)
        + _find_all(r"([^.;。]*(?:생물학적\s*동등성|생동성|의약품\s*동등성|비교\s*용출|용출\s*동등성|f2\s*값|f2\s*인자)[^.;。]*(?:[.;。]|$))", clean_text)
    )

    summary["stability"] = _unique(
        [row["Evidence"] for row in signal_details.get("stability", [])]
        +
        _find_all(r"([^.;]*polyvinyl chloride with hard aluminium[^.;]*[.;])", clean_text)
        + _find_all(r"([^.;]*stability test[^.;]*satisfied[^.;]*[.;])", clean_text)
        + _find_all(r"([^.;]*long[- ]term stability[^.;]*[.;])", clean_text)
        + _find_all(r"([^.;]*accelerated stability[^.;]*[.;])", clean_text)
        + _find_all(r"([^.;。]*(?:안정성|장기보존|가속\s*시험|보관\s*조건|사용기간|유효기간|포장|PTP|알루미늄|PVC)[^.;。]*(?:[.;。]|$))", clean_text)
    )
    _sync_fallback_signal_details(summary, text)

    compounds = []

    for key, record in KNOWN_COMPOUNDS.items():
        if key in text_lower:
            compounds.append(record)

    smiles_hits = re.findall(r"\b(?:[A-Za-z0-9@+\-\[\]\(\)=#$\\/%.]{6,})\b", clean_text)
    for hit in smiles_hits[:12]:
        if any(token in hit for token in ("=", "(", ")", "Cl", "Br", "[", "]")):
            compounds.append({"name": "Detected structure string", "smiles": hit, "role": "candidate"})

    summary["candidate_compounds"] = _dedupe_compounds(compounds)
    if summary["candidate_compounds"] and not signal_details.get("compounds"):
        summary["signal_details"]["compounds"] = [
            {
                "Category": "Compounds",
                "Evidence": f"{item['name']} ({item.get('role', 'candidate')}): {item.get('smiles', 'N/A')}",
                "Page": 1,
                "Section Hint": "3.2.S.1 / 3.2.P.5.5",
                "CTD Mapping": "3.2.S.1 General Information; 3.2.S.3 Characterisation; 3.2.P.4 Excipients; 3.2.P.5.5 Impurities",
                "Regulatory Basis": "ICH M4Q, ICH Q3A/Q3B/Q3C/Q3D, ICH M7, USP/EP monographs",
                "Reason": "known compound alias detected in text",
                "Matched Terms": item["name"],
                "Confidence": 0.88,
                "Evidence Type": "compound alias",
            }
            for item in summary["candidate_compounds"]
        ]
    summary["product_context"] = build_product_context(summary, text)
    summary["specification_table"] = build_specification_table(summary, text)
    summary["writing_structure"] = build_specification_writing_structure(summary)
    summary["writing_outline"] = build_specification_outline(summary)
    summary["regulatory_source_crosswalk"] = build_regulatory_source_crosswalk(summary)
    summary["regulatory_source_matches"] = build_regulatory_source_matches(summary)
    summary["narrative"] = _build_document_narrative(summary)
    return summary


def _find_all(pattern: str, text: str) -> list[str]:
    return [match.strip(" -") for match in re.findall(pattern, text, flags=re.IGNORECASE)]


def _filter_method_evidence(values: list[str]) -> list[str]:
    filtered = []
    method_markers = (
        r"HPLC|UPLC|GC|ICP[- ]?MS|UV|LC-MS|column|mobile phase|flow rate|wavelength|"
        r"standard solution|sample solution|system suitability|validation|dissolution\s*(?:condition|method|medium)|"
        r"표준액|표준용액|검액|시험액|시료액|분석법|기시법|용출\s*(?:조건|시험방법)|밸리데이션|"
        r"칼럼|이동상|유량|파장|시스템적합성"
    )
    be_markers = r"bioequivalence|의약품\s*동등성|생물학적\s*동등성|비교\s*용출|\bf2\b|AUC|Cmax|대조약|시험약"
    spec_heading_markers = r"기준\s*및\s*시험방법|specifications?\b"

    for value in values:
        normalized = re.sub(r"\s+", " ", value or "").strip()
        if not normalized:
            continue
        has_method_detail = bool(re.search(method_markers, normalized, flags=re.IGNORECASE))
        if re.search(spec_heading_markers, normalized, flags=re.IGNORECASE) and not has_method_detail:
            continue
        if re.search(be_markers, normalized, flags=re.IGNORECASE) and not has_method_detail:
            continue
        filtered.append(normalized)
    return filtered


def _sync_fallback_signal_details(summary: dict, original_text: str) -> None:
    """Promote regex fallback findings into the detailed signal tables shown in the UI."""
    signal_details = summary.get("signal_details") or {}
    for category in ("specifications", "test_methods", "bioequivalence", "stability"):
        existing = {
            re.sub(r"\s+", " ", row.get("Evidence", "")).strip().lower()
            for row in signal_details.get(category, [])
        }
        meta = CATEGORY_META[category]
        for evidence in summary.get(category) or []:
            normalized = re.sub(r"\s+", " ", evidence or "").strip()
            if not normalized or normalized.lower() in existing:
                continue
            signal_details.setdefault(category, []).append(
                {
                    "Category": meta["label"],
                    "Evidence": normalized,
                    "Page": _page_for_evidence(original_text, normalized),
                    "Section Hint": infer_fallback_section_hint(category),
                    "Source CTD Section": summary.get("document_profile", {}).get("source_ctd_section", "Unmapped"),
                    "CTD Mapping": meta["ctd_mapping"],
                    "Evidence Role": "Regex Fallback Evidence",
                    "Regulatory Basis": meta["regulatory_basis"],
                    "Reason": "captured by fallback extraction pattern",
                    "Matched Terms": _fallback_matched_terms(category, normalized),
                    "Confidence": 0.68,
                    "Evidence Type": "fallback text",
                }
            )
            existing.add(normalized.lower())
    summary["signal_details"] = signal_details


def infer_fallback_section_hint(category: str) -> str:
    hints = {
        "specifications": "3.2.P.5.1 Specifications",
        "test_methods": "3.2.P.5.2 Analytical Procedures",
        "bioequivalence": "Module 5 Bioequivalence / Comparative Dissolution",
        "stability": "3.2.P.8 Stability",
    }
    return hints.get(category, "Unmapped")


def _fallback_matched_terms(category: str, evidence: str) -> str:
    terms = {
        "specifications": r"assay|specification|함량|기준|유연물질|불순물|NMT|NLT|이하|이상",
        "test_methods": r"HPLC|UPLC|GC|시험방법|기시법|분석법|표준액|검액|method|standard solution|sample solution",
        "bioequivalence": r"bioequivalence|comparative dissolution|f2|AUC|Cmax|생동성|의약품동등성|비교용출",
        "stability": r"stability|long-term|accelerated|안정성|장기보존|가속|유효기간|포장",
    }
    pattern = terms.get(category, r"\w+")
    return ", ".join(dict.fromkeys(match.group(0) for match in re.finditer(pattern, evidence, flags=re.IGNORECASE)))[:180]


def _page_for_evidence(text: str, evidence: str) -> int | str:
    evidence_key = re.sub(r"\s+", " ", evidence or "").strip()[:80]
    if not evidence_key:
        return "N/A"
    current_page = 1
    for part in re.split(r"(\n?\s*---\s*PAGE\s+\d+\s*---\s*\n?)", text or "", flags=re.IGNORECASE):
        page_match = re.search(r"PAGE\s+(\d+)", part, flags=re.IGNORECASE)
        if page_match:
            current_page = int(page_match.group(1))
            continue
        normalized_part = re.sub(r"\s+", " ", part)
        if evidence_key in normalized_part:
            return current_page
    return "N/A"


def _find_solution_phrases(text: str) -> list[str]:
    labels = r"standard solution|reference solution|sample solution|test solution|standard preparation|sample preparation|표준액|표준용액|검액|시험액|시료액"
    units = r"(?:mg/mL|µg/mL|ug/mL|mcg/mL|ng/mL|mg/L|ppm|%|㎎/mL|㎍/mL)"
    concentration = rf"\d+(?:\.\d+)?\s*{units}"
    pattern = rf"((?:{labels}).{{0,180}}?{concentration})"
    matches = []
    for match in re.finditer(pattern, text or "", flags=re.IGNORECASE):
        value = re.sub(r"\s+", " ", match.group(1)).strip(" -;.")
        if value:
            matches.append(value)
    return matches


def _contains_korean(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text or ""))


def _join_pages(pages: list[dict]) -> str:
    parts = []
    for page in pages:
        page_number = page.get("page", len(parts) + 1)
        text = page.get("text", "")
        parts.append(f"\n--- PAGE {page_number} ---\n{text}")
    return "\n".join(parts)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(v for v in values if v))


def _dedupe_compounds(compounds: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for compound in compounds:
        key = (compound.get("name"), compound.get("smiles"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(compound)
    return deduped


def _build_document_narrative(summary: dict) -> str:
    parts = []
    if summary.get("language") == "Korean/English":
        parts.append("Korean regulatory document signals were detected and normalized into the reviewer worksheet.")
    if summary["specifications"]:
        parts.append("Specification and assay controls were identified and should be mapped to CTD 3.2.P.5.1/3.2.P.5.6.")
    if summary["test_methods"]:
        parts.append("Analytical or dissolution method evidence was identified and mapped as method procedure or development rationale.")
    if summary["bioequivalence"]:
        parts.append("Bioequivalence or dissolution language was detected and should be reconciled with comparative performance data.")
    if summary["stability"]:
        parts.append("Stability or packaging evidence was detected and should be linked to shelf-life justification.")
    if summary["candidate_compounds"]:
        parts.append("Candidate compounds were identified for ICH M7 structural alert screening.")
    if not parts:
        parts.append("No major CTD control signals were detected by the prototype rules.")
    return " ".join(parts)
