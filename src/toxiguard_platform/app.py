from __future__ import annotations

import base64
import hashlib
import re

import pandas as pd
import streamlit as st

from toxiguard_platform.modules.document_intelligence import analyze_ctd_text, extract_document_text
from toxiguard_platform.modules.platform_tools import (
    DEFAULT_DISSOLUTION_PROFILE,
    assess_impurity_table,
    assess_genotoxicity_table,
    build_evidence_matrix,
    build_genotoxicity_evidence_basis,
    build_pharmaceutical_equivalence_matrix,
    build_qsar_model_validation_matrix,
    build_related_substance_evidence_basis,
    calculate_f2,
    dissolution_profile_from_document_text,
    dissolution_profile_summary,
    evaluate_related_substances,
    get_experimental_evidence,
    get_impurity_references,
    get_similarity_neighbors,
    predict_degradation_products,
    predict_stability_shelf_life,
    qsar_reference_source_table,
    validate_engine,
)
from toxiguard_platform.modules.product_context import (
    context_table,
    primary_context_name,
    primary_context_smiles,
    substance_options,
)
from toxiguard_platform.modules.project_intake import (
    combine_project_documents,
    document_signal_overview,
    manual_document_record,
    normalize_document_record,
)
from toxiguard_platform.modules.reporting import create_pdf_report
from toxiguard_platform.modules.reviewer_workflow import apply_reviewer_corrections, signal_details_dataframe
from toxiguard_platform.modules.regulatory_sources import (
    CATEGORY_LABELS,
    build_regulatory_source_crosswalk,
    build_regulatory_source_matches,
    category_options,
    source_catalog_rows,
    source_type_options,
)
from toxiguard_platform.modules.specification_structure import build_test_item_matrix
from toxiguard_platform.modules.tox_engine import RDKIT_AVAILABLE, assess_smiles, build_regulatory_narrative
from toxiguard_platform.modules.worksheet import (
    DEFAULT_APPLICATION_PROFILE,
    build_reviewer_worksheet,
    worksheet_tables_for_export,
)


st.set_page_config(
    page_title="ToxiGuard-Platform Ver.1",
    page_icon="TG",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
<style>
:root {
  --ink: #18212f;
  --muted: #5f6c7b;
  --line: #d8dee8;
  --surface: #ffffff;
  --soft: #f6f8fb;
  --blue: #155e75;
  --gold: #b7791f;
  --green: #147a5c;
  --red: #b42318;
  --amber: #a15c07;
}

.stApp {
  background: #f7f9fc;
  color: var(--ink);
}

.block-container {
  max-width: 1280px;
  padding-top: 1.6rem;
}

[data-testid="stSidebar"] {
  background: #101828;
}

[data-testid="stSidebar"] * {
  color: #eef4ff !important;
}

[data-testid="stSidebar"] [data-testid="stButton"] button {
  width: 100%;
  min-height: 2.6rem;
  justify-content: flex-start;
  border-radius: 10px;
  border: 1px solid rgba(238, 244, 255, 0.16);
  background: rgba(255, 255, 255, 0.04);
  color: #eef4ff !important;
  font-weight: 680;
  text-align: left;
  padding: 0.55rem 0.75rem;
}

[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
  border-color: rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.1);
}

[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"],
[data-testid="stSidebar"] [data-testid="baseButton-primary"] {
  border-color: rgba(255, 91, 91, 0.85) !important;
  background: #ff4b4b !important;
  color: #ffffff !important;
}

[data-testid="stSidebar"] [data-baseweb="textarea"],
[data-testid="stSidebar"] [data-testid="stTextArea"] [data-baseweb="base-input"],
[data-testid="stSidebar"] [data-testid="stTextArea"] [data-baseweb="textarea"] > div,
[data-testid="stSidebar"] textarea {
  background-color: #172233 !important;
  border: 1px solid rgba(238, 244, 255, 0.18) !important;
  color: #eef4ff !important;
}

[data-testid="stSidebar"] [data-baseweb="textarea"] textarea {
  background-color: transparent !important;
  color: #eef4ff !important;
  caret-color: #ffffff !important;
}

[data-testid="stSidebar"] textarea::placeholder {
  color: rgba(238, 244, 255, 0.52) !important;
  opacity: 1 !important;
}

.sidebar-dev-card {
  border-top: 1px solid rgba(238, 244, 255, 0.12);
  margin-top: 1.4rem;
  padding-top: 1rem;
}

.sidebar-dev-card strong {
  display: block;
  font-size: 0.9rem;
  margin-bottom: 0.45rem;
}

.sidebar-dev-card span {
  display: block;
  color: rgba(238, 244, 255, 0.72) !important;
  font-size: 0.78rem;
  line-height: 1.45;
}

#MainMenu,
footer,
[data-testid="stDeployButton"],
[aria-label="Deploy"],
[title="Deploy"] {
  display: none !important;
  visibility: hidden !important;
}

.tg-header {
  border-bottom: 1px solid var(--line);
  padding-bottom: 1rem;
  margin-bottom: 1.2rem;
}

.tg-title {
  font-size: 2.2rem;
  font-weight: 760;
  letter-spacing: 0;
  margin: 0;
}

.tg-subtitle {
  color: var(--muted);
  font-size: 1rem;
  margin-top: 0.35rem;
}

.status-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 1rem 0 1.35rem;
}

.status-cell {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.85rem 1rem;
}

.status-label {
  color: var(--muted);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0;
}

.status-value {
  font-size: 1.05rem;
  font-weight: 720;
  margin-top: 0.25rem;
}

.section-band {
  background: var(--surface);
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  padding: 1rem 0;
  margin: 1rem 0;
}

.review-banner {
  background: #ffffff;
  border: 1px solid var(--line);
  border-left: 5px solid var(--blue);
  border-radius: 8px;
  padding: 1rem 1.1rem;
  margin: 0.5rem 0 1rem;
}

.review-banner strong {
  display: block;
  font-size: 1rem;
  margin-bottom: 0.25rem;
}

.review-banner span {
  color: var(--muted);
}

@media (max-width: 820px) {
  .status-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .tg-title {
    font-size: 1.6rem;
  }
}
</style>
""",
    unsafe_allow_html=True,
)


LANGUAGE_OPTIONS = ["ko", "en"]
LANGUAGE_LABELS = {"ko": "한국어", "en": "English"}

TRANSLATIONS = {
    "language": {"ko": "언어", "en": "Language"},
    "subtitle": {
        "ko": "CTD 문서 인텔리전스와 ICH M7 구조 경고 스크리닝을 통합한 리뷰 워크스페이스입니다.",
        "en": "Integrated CTD document intelligence and ICH M7 structural alert screening.",
    },
    "engine": {"ko": "엔진", "en": "Engine"},
    "rdkit_active": {"ko": "RDKit 활성", "en": "RDKit active"},
    "fallback_mode": {"ko": "Fallback 모드", "en": "Fallback mode"},
    "document_flow": {"ko": "문서 흐름", "en": "Document Flow"},
    "regulatory_frame": {"ko": "규제 프레임", "en": "Regulatory Frame"},
    "output": {"ko": "출력", "en": "Output"},
    "view": {"ko": "화면", "en": "View"},
    "workspace": {"ko": "워크스페이스", "en": "Workspace"},
    "prototype_status": {"ko": "프로토타입 상태", "en": "Prototype status"},
    "decision_support_only": {"ko": "의사결정 보조용", "en": "Decision-support only"},
    "expert_review_required": {"ko": "전문가 검토 필요", "en": "Expert review required"},
    "developer_info": {"ko": "개발자 정보", "en": "Developer information"},
    "developer_name": {"ko": "개발자", "en": "Developer"},
    "developer_role": {"ko": "역할", "en": "Role"},
    "developer_role_value": {"ko": "Regulatory AI Prototype Design", "en": "Regulatory AI Prototype Design"},
    "developer_project": {"ko": "프로젝트", "en": "Project"},
    "sidebar_comment": {"ko": "코멘트", "en": "Comment"},
    "sidebar_comment_placeholder": {
        "ko": "개발/검토 메모를 남겨두세요.",
        "en": "Leave development or review notes here.",
    },
    "save_comment": {"ko": "코멘트 저장", "en": "Save comment"},
    "comment_saved": {"ko": "코멘트를 이 세션에 저장했습니다.", "en": "Comment saved in this session."},
    "Document Analyzer": {"ko": "문서 분석", "en": "Document Analyzer"},
    "Molecule Screening": {"ko": "분자 스크리닝", "en": "Molecule Screening"},
    "ToxiGuard Tools": {"ko": "ToxiGuard 도구", "en": "ToxiGuard Tools"},
    "FDA Review Worksheet": {"ko": "FDA 리뷰 워크시트", "en": "FDA Review Worksheet"},
    "Regulatory Sources": {"ko": "규제 출처", "en": "Regulatory Sources"},
    "Regulatory Report": {"ko": "규제 보고서", "en": "Regulatory Report"},
    "no_rows": {"ko": "표시할 행이 없습니다.", "en": "No rows available."},
    "no_source_rows": {"ko": "표시할 출처 행이 없습니다.", "en": "No source rows available."},
    "Category Crosswalk": {"ko": "카테고리 연결표", "en": "Category Crosswalk"},
    "Evidence Matches": {"ko": "근거-출처 매칭", "en": "Evidence Matches"},
    "Source Library": {"ko": "출처 라이브러리", "en": "Source Library"},
    "Signal Category": {"ko": "신호 카테고리", "en": "Signal Category"},
    "Source Type": {"ko": "출처 유형", "en": "Source Type"},
    "All": {"ko": "전체", "en": "All"},
    "no_source_crosswalk": {"ko": "규제 출처 연결표가 없습니다.", "en": "No regulatory source crosswalk available."},
    "no_evidence_matches": {
        "ko": "문서를 분석하면 추출 근거와 기준 출처가 연결됩니다.",
        "en": "Analyze a document to map extracted evidence to source standards.",
    },
    "No evidence-to-source matches available.": {
        "ko": "근거-출처 매칭 정보가 없습니다.",
        "en": "No evidence-to-source matches available.",
    },
    "no_source_filter": {"ko": "선택한 조건에 맞는 출처가 없습니다.", "en": "No source rows match the selected filters."},
    "no_product_context": {
        "ko": "아직 제품, 물질, 제형 정보가 추출되지 않았습니다.",
        "en": "No product, substance, or formulation context has been extracted yet.",
    },
    "linked_document_context": {"ko": "연결된 문서 정보", "en": "Linked Document Context"},
    "Linked Substances": {"ko": "연결 물질", "en": "Linked Substances"},
    "Formulation": {"ko": "제형/Formulation", "en": "Formulation"},
    "Basic Info": {"ko": "기본 정보", "en": "Basic Info"},
    "Package / Storage": {"ko": "포장 / 보관", "en": "Package / Storage"},
    "Menu Links": {"ko": "메뉴 연결", "en": "Menu Links"},
    "no_basic_info": {"ko": "제품 기본 정보가 추출되지 않았습니다.", "en": "No product basic information extracted."},
    "no_linked_substances": {"ko": "연결 물질이 추출되지 않았습니다.", "en": "No linked substances extracted."},
    "no_formulation": {"ko": "제형 또는 첨가제 정보가 추출되지 않았습니다.", "en": "No formulation or excipient context extracted."},
    "no_package_storage": {"ko": "포장 또는 보관 정보가 추출되지 않았습니다.", "en": "No packaging or storage context extracted."},
    "no_menu_links": {"ko": "메뉴 연결 정보가 생성되지 않았습니다.", "en": "No cross-menu links generated."},
    "Application Type": {"ko": "신청 유형", "en": "Application Type"},
    "Application Number": {"ko": "신청 번호", "en": "Application Number"},
    "Product Name": {"ko": "제품명", "en": "Product Name"},
    "Applicant": {"ko": "신청사", "en": "Applicant"},
    "Dosage Form": {"ko": "제형", "en": "Dosage Form"},
    "Route": {"ko": "투여경로", "en": "Route"},
    "Review Cycle": {"ko": "검토 차수", "en": "Review Cycle"},
    "Discipline Owner": {"ko": "검토 분야", "en": "Discipline Owner"},
    "Review Status": {"ko": "검토 상태", "en": "Review Status"},
    "Update Snapshot": {"ko": "신청 정보 업데이트", "en": "Update Snapshot"},
    "snapshot_updated": {"ko": "신청 정보가 업데이트되었습니다.", "en": "Application snapshot updated."},
    "CTD Document Intake": {"ko": "CTD 문서 입력", "en": "CTD Document Intake"},
    "Project Name": {"ko": "프로젝트명", "en": "Project Name"},
    "Project Dossier": {"ko": "프로젝트 문서함", "en": "Project Dossier"},
    "project_dossier_body": {
        "ko": "여러 CTD/PDF를 하나의 프로젝트로 묶어 문서별 신호와 통합 분석을 함께 생성합니다.",
        "en": "Group multiple CTD/PDF files into one project dossier and generate both per-document signals and integrated analysis.",
    },
    "project_default_name": {"ko": "ToxiGuard-Platform Ver.1", "en": "ToxiGuard-Platform Ver.1"},
    "kor_eng_enabled_title": {"ko": "한글/영어 문서 검토 지원", "en": "Korean and English review enabled"},
    "kor_eng_enabled_body": {
        "ko": "한글 기준 및 시험방법, 유연물질, 용출/생동성, 안정성 문구를 FDA-style worksheet 항목으로 정리합니다.",
        "en": "Korean and English specifications, test methods, impurities, dissolution/BE, and stability language are organized into FDA-style worksheet fields.",
    },
    "Upload CTD, PDF, or scanned image": {"ko": "CTD, PDF 또는 스캔 이미지 업로드", "en": "Upload CTD, PDF, or scanned image"},
    "Upload CTD documents": {"ko": "CTD/PDF/스캔 이미지 여러 개 업로드", "en": "Upload multiple CTD/PDF/scanned files"},
    "manual_text_label": {"ko": "또는 CTD 문서 텍스트 붙여넣기", "en": "Or paste extracted CTD text"},
    "manual_text_placeholder": {
        "ko": "예: 기준 및 시험방법: 함량 95.0~105.0%, 유연물질 개개 불순물 0.1% 이하...",
        "en": "Example: Specifications: assay 95.0-105.0%, individual impurity NMT 0.1%...",
    },
    "manual_text_document": {"ko": "붙여넣은 CTD 텍스트", "en": "Pasted CTD Text"},
    "Analyze Document": {"ko": "문서 분석", "en": "Analyze Document"},
    "Analyze Project": {"ko": "프로젝트 분석", "en": "Analyze Project"},
    "Analyze Uploaded Files": {"ko": "업로드 파일 분석", "en": "Analyze Uploaded Files"},
    "Analyze Pasted Text": {"ko": "붙여넣은 텍스트 분석", "en": "Analyze Pasted Text"},
    "Clear Analysis": {"ko": "분석 초기화", "en": "Clear Analysis"},
    "Selected Files": {"ko": "선택된 파일", "en": "Selected Files"},
    "processing_documents": {"ko": "문서를 추출하고 CTD 신호를 정리하는 중입니다.", "en": "Extracting documents and organizing CTD signals."},
    "auto_analysis_complete": {"ko": "업로드된 파일이 자동 분석되었습니다.", "en": "Uploaded files were analyzed automatically."},
    "analysis_cleared": {"ko": "분석 결과를 초기화했습니다.", "en": "Analysis results were cleared."},
    "analysis_complete": {"ko": "문서 분석이 완료되었습니다.", "en": "Document analysis complete."},
    "project_analysis_complete": {"ko": "프로젝트 문서 분석이 완료되었습니다.", "en": "Project dossier analysis complete."},
    "project_empty_warning": {"ko": "분석할 파일 또는 붙여넣은 텍스트가 필요합니다.", "en": "Add at least one file or pasted text before analysis."},
    "analysis_persist_hint": {
        "ko": "분석 결과는 이 세션에 유지되며, 다른 메뉴에서도 제품/물질/제형 정보가 연결됩니다.",
        "en": "Analysis results stay in this session and feed product, substance, and formulation context into linked menus.",
    },
    "Project Overview": {"ko": "프로젝트 개요", "en": "Project Overview"},
    "Documents": {"ko": "문서 수", "en": "Documents"},
    "Project Pages": {"ko": "프로젝트 페이지", "en": "Project Pages"},
    "Readable Characters": {"ko": "추출 문자 수", "en": "Readable Characters"},
    "Extraction Warnings": {"ko": "추출 경고", "en": "Extraction Warnings"},
    "Uploaded Documents": {"ko": "업로드 문서", "en": "Uploaded Documents"},
    "Per-Document Signal Summary": {"ko": "문서별 신호 요약", "en": "Per-Document Signal Summary"},
    "No project documents analyzed.": {"ko": "아직 프로젝트 문서가 분석되지 않았습니다.", "en": "No project documents analyzed yet."},
    "Document Signals": {"ko": "문서 신호", "en": "Document Signals"},
    "upload_to_begin": {"ko": "파일을 업로드하거나 CTD 텍스트를 붙여넣어 시작하세요.", "en": "Upload a file or paste CTD text to begin."},
    "detected_language": {"ko": "감지된 문서 언어", "en": "Detected document language"},
    "document_profile": {"ko": "문서 프로필", "en": "Document profile"},
    "supporting_rationale_mode": {"ko": "근거자료 모드", "en": "supporting rationale mode"},
    "direct_evidence_mode": {"ko": "직접 근거 모드", "en": "direct evidence mode"},
    "Product Context": {"ko": "제품 정보", "en": "Product Context"},
    "Spec Table": {"ko": "기준/시험방법 표", "en": "Spec Table"},
    "Writing Structure": {"ko": "작성 구조", "en": "Writing Structure"},
    "Signals": {"ko": "신호", "en": "Signals"},
    "Raw Pages": {"ko": "원문 페이지", "en": "Raw Pages"},
    "Evidence Blocks": {"ko": "근거 블록", "en": "Evidence Blocks"},
    "Reviewer Correction": {"ko": "검토자 수정", "en": "Reviewer Correction"},
    "No specification table generated.": {"ko": "기준 및 시험방법 표가 생성되지 않았습니다.", "en": "No specification table generated."},
    "writing_structure_default": {
        "ko": "문서 분석 후 Q6A/MFDS 작성 구조가 생성됩니다.",
        "en": "Q6A/MFDS writing structure is generated after document analysis.",
    },
    "No writing structure generated.": {"ko": "작성 구조가 생성되지 않았습니다.", "en": "No writing structure generated."},
    "Specifications": {"ko": "기준", "en": "Specifications"},
    "Test Method": {"ko": "시험방법", "en": "Test Method"},
    "Bioequivalence": {"ko": "생물학적동등성", "en": "Bioequivalence"},
    "Stability": {"ko": "안정성", "en": "Stability"},
    "Compounds": {"ko": "물질", "en": "Compounds"},
    "No specification signals detected.": {"ko": "기준 신호가 감지되지 않았습니다.", "en": "No specification signals detected."},
    "No test method signals detected.": {"ko": "시험방법 신호가 감지되지 않았습니다.", "en": "No test method signals detected."},
    "No bioequivalence signals detected.": {"ko": "생동성 신호가 감지되지 않았습니다.", "en": "No bioequivalence signals detected."},
    "No stability signals detected.": {"ko": "안정성 신호가 감지되지 않았습니다.", "en": "No stability signals detected."},
    "No compound evidence details detected.": {"ko": "물질 근거가 감지되지 않았습니다.", "en": "No compound evidence details detected."},
    "Screenable Compounds": {"ko": "스크리닝 가능 물질", "en": "Screenable Compounds"},
    "No compounds detected.": {"ko": "감지된 물질이 없습니다.", "en": "No compounds detected."},
    "Page": {"ko": "페이지", "en": "Page"},
    "Extracted page text": {"ko": "추출된 페이지 텍스트", "en": "Extracted page text"},
    "No evidence blocks generated.": {"ko": "근거 블록이 생성되지 않았습니다.", "en": "No evidence blocks generated."},
    "No AI extracted signals to review.": {"ko": "검토할 AI 추출 신호가 없습니다.", "en": "No AI extracted signals to review."},
    "Apply Reviewer Corrections": {"ko": "검토자 수정 적용", "en": "Apply Reviewer Corrections"},
    "corrections_applied": {
        "ko": "검토자 수정이 문서 신호와 FDA 리뷰 워크시트에 적용되었습니다.",
        "en": "Reviewer corrections applied to Document Signals and FDA Review Worksheet.",
    },
    "Auto-Screened Compounds": {"ko": "자동 스크리닝 물질", "en": "Auto-Screened Compounds"},
    "ICH M7 Molecule Screening": {"ko": "ICH M7 분자 스크리닝", "en": "ICH M7 Molecule Screening"},
    "Document-linked substance": {"ko": "문서 연결 물질", "en": "Document-linked substance"},
    "Manual entry": {"ko": "직접 입력", "en": "Manual entry"},
    "using_document_structure": {"ko": "문서에서 연결된 구조를 사용합니다", "en": "Using document-linked structure for"},
    "smiles_needed": {
        "ko": "이 문서 연결 물질은 ICH M7 스크리닝 전에 SMILES 확인이 필요합니다.",
        "en": "This document-linked substance needs a SMILES before ICH M7 screening can run.",
    },
    "Example": {"ko": "예시", "en": "Example"},
    "Custom": {"ko": "직접 입력", "en": "Custom"},
    "smiles_placeholder": {"ko": "SMILES 문자열을 입력하거나 확인하세요.", "en": "Enter or confirm a SMILES string"},
    "Run Screening": {"ko": "스크리닝 실행", "en": "Run Screening"},
    "Valid": {"ko": "유효성", "en": "Valid"},
    "Conclusion": {"ko": "결론", "en": "Conclusion"},
    "Risk Score": {"ko": "위험 점수", "en": "Risk Score"},
    "ICH M7 Class": {"ko": "ICH M7 등급", "en": "ICH M7 Class"},
    "Alerts": {"ko": "경고", "en": "Alerts"},
    "ToxiGuard Platform Tools": {"ko": "ToxiGuard 플랫폼 도구", "en": "ToxiGuard Platform Tools"},
    "Tool Menu": {"ko": "도구 메뉴", "en": "Tool Menu"},
    "Pharmaceutical Equivalence Matrix": {"ko": "의약품동등성 항목 매트릭스", "en": "Pharmaceutical Equivalence Matrix"},
    "pharm_eq_title": {"ko": "의약품동등성 전체 항목 점검", "en": "Pharmaceutical Equivalence Review Inventory"},
    "pharm_eq_body": {
        "ko": "동등성 판단 항목만 정리합니다. 기준 및 시험방법의 상세 리스트는 별도 매트릭스에서 확인합니다.",
        "en": "Show only equivalence review items. Detailed specification and method lists stay in the separate matrix.",
    },
    "be_f2_title": {"ko": "Reference drug 용출률 / f2 Bootstrap", "en": "Reference Drug Dissolution / f2 Bootstrap"},
    "be_f2_body": {
        "ko": "대조약(reference drug)과 시험약(test drug)의 시간점별 용출률을 입력해 유사성인자 f2, bootstrap 신뢰구간, f2 ≥ 50 확률을 계산합니다.",
        "en": "Enter reference and test dissolution percentages by time point to calculate f2, bootstrap confidence interval, and P(f2 >= 50).",
    },
    "be_seed_from_document": {
        "ko": "문서에서 비교용출 표를 감지해 기본값으로 적용했습니다.",
        "en": "A comparative dissolution table was detected in the document and used as the starting profile.",
    },
    "be_default_profile": {
        "ko": "문서 비교용출 표가 명확하지 않아 예시 프로파일을 사용합니다. 실제 reference/test 용출률로 교체하세요.",
        "en": "No clear comparative dissolution table was detected, so an example profile is shown. Replace it with actual reference/test data.",
    },
    "Reference/Test Dissolution Data": {"ko": "대조약/시험약 용출률 데이터", "en": "Reference/Test Dissolution Data"},
    "Bootstrap Iterations": {"ko": "Bootstrap 반복 수", "en": "Bootstrap Iterations"},
    "Calculate f2 with Bootstrap": {"ko": "f2 및 Bootstrap 계산", "en": "Calculate f2 with Bootstrap"},
    "f2 Similarity Factor": {"ko": "f2 유사성인자", "en": "f2 Similarity Factor"},
    "Bootstrap 95% CI": {"ko": "Bootstrap 95% 신뢰구간", "en": "Bootstrap 95% CI"},
    "P(f2 >= 50)": {"ko": "P(f2 ≥ 50)", "en": "P(f2 >= 50)"},
    "CV Check": {"ko": "CV 점검", "en": "CV Check"},
    "FDA-style Decision": {"ko": "FDA-style 판단", "en": "FDA-style Decision"},
    "Next Action": {"ko": "다음 검토", "en": "Next Action"},
    "Dissolution Profile Summary": {"ko": "용출 프로파일 요약", "en": "Dissolution Profile Summary"},
    "Impurity Specification Assessment": {"ko": "불순물 기준 평가", "en": "Impurity Specification Assessment"},
    "Related Substances Evaluation": {"ko": "유연물질 평가", "en": "Related Substances Evaluation"},
    "related_substances_title": {"ko": "유연물질 / 분해산물 평가", "en": "Related Substance / Degradation Product Evaluation"},
    "related_substances_body": {
        "ko": "관찰값, 제안 기준, 기원, 약전/공정서 여부, ICH Q3A/Q3B/Q3C 근거, 시험방법 근거를 함께 비교합니다.",
        "en": "Compare observed levels, proposed limits, origin, compendial status, ICH Q3A/Q3B/Q3C basis, and method evidence together.",
    },
    "Genotoxicity Assessment": {"ko": "유전독성 평가", "en": "Genotoxicity Assessment"},
    "genotoxicity_title": {"ko": "ICH M7 유전독성 평가", "en": "ICH M7 Genotoxicity Assessment"},
    "genotoxicity_body": {
        "ko": "전문가 규칙, 통계 QSAR, 적용영역, 모델 검증근거, 실험/문헌 데이터를 분리해 ICH M7/OECD 기준으로 확인합니다.",
        "en": "Separate expert rules, statistical QSAR, applicability domain, model validation evidence, and experimental/literature data under ICH M7/OECD criteria.",
    },
    "Stability Shelf-Life Prediction": {"ko": "안정성 유효기간 예측", "en": "Stability Shelf-Life Prediction"},
    "stability_prediction_title": {"ko": "ICH Q1E 안정성 유효기간 예측", "en": "ICH Q1E Stability Shelf-Life Prediction"},
    "stability_prediction_body": {
        "ko": "장기보존 및 가속 안정성 데이터를 회귀 분석해 기준 초과 예상 시점과 유효기간 지지 여부를 계산합니다.",
        "en": "Use long-term and accelerated stability trends to estimate specification crossing and shelf-life support.",
    },
    "Specification / Test Method Matrix": {"ko": "기준 및 시험방법 매트릭스", "en": "Specification / Test Method Matrix"},
    "spec_matrix_title": {"ko": "시험항목별 기준 및 시험방법", "en": "Specification and Test Method by Test Item"},
    "spec_matrix_body": {
        "ko": "기준은 specification 항목에서, 시험방법은 method 항목에서 분리해 표준액/검액 농도까지 시험항목별로 정렬합니다.",
        "en": "Separate criteria from specification sections and methods from method sections, including standard/sample solution concentration.",
    },
    "test_item_total": {"ko": "시험항목", "en": "Test Items"},
    "linked_items": {"ko": "연결 완료", "en": "Linked"},
    "needs_method": {"ko": "시험방법 확인 필요", "en": "Needs Method"},
    "needs_criteria": {"ko": "기준 확인 필요", "en": "Needs Criteria"},
    "needs_source": {"ko": "근거 확인 필요", "en": "Needs Source"},
    "Filter Status": {"ko": "상태 필터", "en": "Filter Status"},
    "All Statuses": {"ko": "전체 상태", "en": "All Statuses"},
    "Linked": {"ko": "연결 완료", "en": "Linked"},
    "Needs method": {"ko": "시험방법 확인 필요", "en": "Needs method"},
    "Needs criteria": {"ko": "기준 확인 필요", "en": "Needs criteria"},
    "Needs criteria and method": {"ko": "기준 및 시험방법 확인 필요", "en": "Needs criteria and method"},
    "Needs source confirmation": {"ko": "원문 확인 필요", "en": "Needs source confirmation"},
    "No criteria/test method matrix generated.": {
        "ko": "기준 및 시험방법 매트릭스가 생성되지 않았습니다. 먼저 Document Analyzer에서 문서를 분석하세요.",
        "en": "No criteria/test method matrix generated. Analyze a document in Document Analyzer first.",
    },
    "Reference Impurity Lookup": {"ko": "참조 불순물 조회", "en": "Reference Impurity Lookup"},
    "QSAR Evidence Matrix": {"ko": "QSAR 근거 매트릭스", "en": "QSAR Evidence Matrix"},
    "Experimental Evidence Dossier": {"ko": "실험 근거 자료", "en": "Experimental Evidence Dossier"},
    "Degradation / Impurity Prediction": {"ko": "분해/불순물 예측", "en": "Degradation / Impurity Prediction"},
    "Engine Validation": {"ko": "엔진 검증", "en": "Engine Validation"},
    "Assess Impurities": {"ko": "불순물 평가", "en": "Assess Impurities"},
    "Run Evaluation": {"ko": "평가 실행", "en": "Run Evaluation"},
    "Run Genotoxicity Assessment": {"ko": "유전독성 평가 실행", "en": "Run Genotoxicity Assessment"},
    "Assessment Result": {"ko": "판정 결과", "en": "Assessment Result"},
    "Evidence Basis Matrix": {"ko": "평가 근거 매트릭스", "en": "Evidence Basis Matrix"},
    "QSAR Validation Matrix": {"ko": "QSAR 모델 검증 매트릭스", "en": "QSAR Validation Matrix"},
    "Reference Sources": {"ko": "참고 기준 출처", "en": "Reference Sources"},
    "qsar_validation_caption": {
        "ko": "ICH M7(R2)의 두 상보적 QSAR 모델 요구와 OECD QSAR 검증 원칙을 기준으로 입력자료의 완성도를 점검합니다.",
        "en": "Checks input completeness against ICH M7(R2) complementary QSAR expectations and OECD QSAR validation principles.",
    },
    "basis_caption": {
        "ko": "이 표는 결론의 근거층을 분리합니다. 실제 제출에는 약전 원문, CTD 시험방법, 검증된 QSAR 출력, 실험보고서 원문 확인이 필요합니다.",
        "en": "This table separates rationale layers. Submission use requires source monographs, CTD methods, validated QSAR outputs, and original study reports.",
    },
    "Run Shelf-Life Prediction": {"ko": "유효기간 예측 실행", "en": "Run Shelf-Life Prediction"},
    "Specification Limit (%) for this impurity": {
        "ko": "해당 불순물 기준 (%)",
        "en": "Specification Limit (%) for this impurity",
    },
    "Long-Term Data": {"ko": "장기보존 자료", "en": "Long-Term Data"},
    "Accelerated Data": {"ko": "가속 자료", "en": "Accelerated Data"},
    "Compound Name": {"ko": "물질명", "en": "Compound Name"},
    "Build Evidence Matrix": {"ko": "근거 매트릭스 생성", "en": "Build Evidence Matrix"},
    "Similarity / Analog Context": {"ko": "유사체 / Analog 정보", "en": "Similarity / Analog Context"},
    "No direct prototype evidence record found for this SMILES.": {
        "ko": "이 SMILES에 대한 직접 prototype 근거 기록이 없습니다.",
        "en": "No direct prototype evidence record found for this SMILES.",
    },
    "No prototype neighbor records available.": {"ko": "Prototype 유사체 기록이 없습니다.", "en": "No prototype neighbor records available."},
    "Parent SMILES": {"ko": "모물질 SMILES", "en": "Parent SMILES"},
    "Predict Products": {"ko": "생성물 예측", "en": "Predict Products"},
    "engine_validation_caption": {
        "ko": "이 항목은 prototype 동작 확인용 smoke test이며 공식 모델 밸리데이션 패키지가 아닙니다.",
        "en": "This is a smoke test for prototype behavior, not a formal model validation package.",
    },
    "FDA-Style Review Worksheet": {"ko": "FDA 스타일 리뷰 워크시트", "en": "FDA-Style Review Worksheet"},
    "reviewer_workspace_title": {"ko": "검토자 워크스페이스", "en": "Reviewer workspace"},
    "reviewer_workspace_body": {
        "ko": "신청 정보, eCTD 근거, CMC 검토점, ICH M7 분류, 보완사항, 최종 리뷰 문구를 정리합니다.",
        "en": "Organizes application metadata, eCTD evidence, CMC review points, ICH M7 classification, deficiencies, and final review language.",
    },
    "Recommended Action": {"ko": "권고 조치", "en": "Recommended Action"},
    "Open Deficiencies": {"ko": "열린 보완사항", "en": "Open Deficiencies"},
    "ICH M7 Items": {"ko": "ICH M7 항목", "en": "ICH M7 Items"},
    "Submission Map": {"ko": "제출자료 맵", "en": "Submission Map"},
    "Sources": {"ko": "출처", "en": "Sources"},
    "Spec Writing": {"ko": "기시법 작성", "en": "Spec Writing"},
    "CMC / Quality": {"ko": "CMC / 품질", "en": "CMC / Quality"},
    "Deficiencies": {"ko": "보완사항", "en": "Deficiencies"},
    "Integrated Assessment": {"ko": "종합 평가", "en": "Integrated Assessment"},
    "Source Crosswalk": {"ko": "출처 연결표", "en": "Source Crosswalk"},
    "Regulatory Source Library": {"ko": "규제 출처 라이브러리", "en": "Regulatory Source Library"},
    "source_library_title": {"ko": "CTD/eCTD 출처 연결표", "en": "CTD/eCTD source crosswalk"},
    "source_library_body": {
        "ko": "추출된 문서 신호를 공식 CTD, eCTD, ICH, MFDS, USP, EP 및 오픈소스 도구 출처와 연결합니다.",
        "en": "Links extracted document signals to official CTD, eCTD, ICH, MFDS, USP, EP, and open-source tooling references.",
    },
    "Regulatory Report Builder": {"ko": "규제 보고서 작성", "en": "Regulatory Report Builder"},
    "Download PDF Report": {"ko": "PDF 보고서 다운로드", "en": "Download PDF Report"},
    "pdf_payload": {"ko": "PDF payload 준비 완료", "en": "PDF payload prepared"},
}


if "ui_language" not in st.session_state:
    st.session_state.ui_language = "ko"
if "language_selector" not in st.session_state:
    st.session_state.language_selector = st.session_state.ui_language
if "workflow_selector" not in st.session_state:
    st.session_state.workflow_selector = "Document Analyzer"
if "sidebar_comment" not in st.session_state:
    st.session_state.sidebar_comment = ""


WORKFLOW_OPTIONS = [
    "Document Analyzer",
    "Molecule Screening",
    "ToxiGuard Tools",
    "FDA Review Worksheet",
    "Regulatory Sources",
    "Regulatory Report",
]

WORKFLOW_ICONS = {
    "Document Analyzer": "DOC",
    "Molecule Screening": "MOL",
    "ToxiGuard Tools": "TOOL",
    "FDA Review Worksheet": "FDA",
    "Regulatory Sources": "SRC",
    "Regulatory Report": "RPT",
}


def current_language() -> str:
    return st.session_state.get("language_selector", st.session_state.get("ui_language", "ko"))


def t(key: str) -> str:
    value = TRANSLATIONS.get(key)
    if not value:
        return key
    return value.get(current_language(), value.get("en", key))


COLUMN_LABEL_OVERRIDES = {
    "항목 / Test": {"ko": "항목 / Test", "en": "Test"},
    "세부항목 / Sub-test": {"ko": "세부항목 / Sub-test", "en": "Sub-test"},
    "기준 / Specification": {"ko": "기준 / Specification", "en": "Specification"},
    "시험방법 / Test Method": {"ko": "시험방법 / Test Method", "en": "Test Method"},
    "자료위치 / Source": {"ko": "자료위치 / Source", "en": "Source"},
    "검토메모 / Reviewer Note": {"ko": "검토메모 / Reviewer Note", "en": "Reviewer Note"},
    "시험항목 / Test Item": {"ko": "시험항목 / Test Item", "en": "Test Item"},
    "기준 / Acceptance Criteria": {"ko": "기준 / Acceptance Criteria", "en": "Acceptance Criteria"},
    "기준 출처 / Specification Source": {"ko": "기준 출처 / Specification Source", "en": "Specification Source"},
    "표준액 농도 / Standard Solution": {"ko": "표준액 농도 / Standard Solution", "en": "Standard Solution"},
    "검액 농도 / Sample Solution": {"ko": "검액 농도 / Sample Solution", "en": "Sample Solution"},
    "시험방법 출처 / Method Source": {"ko": "시험방법 출처 / Method Source", "en": "Method Source"},
    "CTD 위치 / CTD Anchor": {"ko": "CTD 위치 / CTD Anchor", "en": "CTD Anchor"},
    "상태 / Status": {"ko": "상태 / Status", "en": "Status"},
    "검토 포인트 / Reviewer Focus": {"ko": "검토 포인트 / Reviewer Focus", "en": "Reviewer Focus"},
    "동등성 항목 / Equivalence Item": {"ko": "동등성 항목 / Equivalence Item", "en": "Equivalence Item"},
    "MFDS Writing Heading": {"ko": "MFDS 작성 항목", "en": "MFDS Writing Heading"},
    "Document": {"ko": "문서", "en": "Document"},
    "Source": {"ko": "출처", "en": "Source"},
    "Type": {"ko": "파일 유형", "en": "Type"},
    "Pages": {"ko": "페이지", "en": "Pages"},
    "Characters": {"ko": "문자 수", "en": "Characters"},
    "Bytes": {"ko": "용량", "en": "Bytes"},
    "Warnings": {"ko": "경고", "en": "Warnings"},
    "Specifications": {"ko": "기준", "en": "Specifications"},
    "Test Methods": {"ko": "시험방법", "en": "Test Methods"},
    "Bioequivalence": {"ko": "생동성", "en": "Bioequivalence"},
    "Stability": {"ko": "안정성", "en": "Stability"},
    "Compounds": {"ko": "물질", "en": "Compounds"},
    "QSAR Package Status": {"ko": "QSAR 패키지 상태", "en": "QSAR Package Status"},
    "QSAR Confidence": {"ko": "QSAR 신뢰도", "en": "QSAR Confidence"},
    "Validation Criterion": {"ko": "검증 기준", "en": "Validation Criterion"},
    "Regulatory Expectation": {"ko": "규제 기대사항", "en": "Regulatory Expectation"},
    "Current Evidence": {"ko": "현재 근거", "en": "Current Evidence"},
    "Reference Source": {"ko": "참고 기준", "en": "Reference Source"},
    "Reference Focus": {"ko": "참고 기준 초점", "en": "Reference Focus"},
    "Use in Matrix": {"ko": "매트릭스 적용", "en": "Use in Matrix"},
}


VALUE_LABEL_OVERRIDES = {
    "기준 및 시험방법의 작성 범위": {"ko": "기준 및 시험방법의 작성 범위", "en": "Scope of specifications and test methods"},
    "성상, 확인시험, 순도시험, 정량법, 제제학적 시험": {
        "ko": "성상, 확인시험, 순도시험, 정량법, 제제학적 시험",
        "en": "Appearance, identification, purity, assay, and dosage-form tests",
    },
    "규격기준 및 허용기준 설정": {"ko": "규격기준 및 허용기준 설정", "en": "Acceptance criteria setting"},
    "시험방법 및 분석조건": {"ko": "시험방법 및 분석조건", "en": "Analytical procedure and conditions"},
    "시험방법 밸리데이션": {"ko": "시험방법 밸리데이션", "en": "Analytical method validation"},
    "기준 설정 근거자료": {"ko": "기준 설정 근거자료", "en": "Justification of specifications"},
    "시험성적 및 로트 분석자료": {"ko": "시험성적 및 로트 분석자료", "en": "Batch analysis and test results"},
    "유연물질, 분해산물, 잔류용매, 금속불순물": {
        "ko": "유연물질, 분해산물, 잔류용매, 금속불순물",
        "en": "Related substances, degradation products, residual solvents, and elemental impurities",
    },
    "안정성 자료와 사용기간/저장방법": {"ko": "안정성 자료와 사용기간/저장방법", "en": "Stability, shelf life, and storage"},
    "공정서 및 별규 인용": {"ko": "공정서 및 별규 인용", "en": "Compendial and in-house standards"},
    "연결 완료": {"ko": "연결 완료", "en": "Linked"},
    "시험방법 확인 필요": {"ko": "시험방법 확인 필요", "en": "Needs method"},
    "기준 확인 필요": {"ko": "기준 확인 필요", "en": "Needs criteria"},
    "기준 및 시험방법 확인 필요": {"ko": "기준 및 시험방법 확인 필요", "en": "Needs criteria and method"},
    "원문 확인 필요": {"ko": "원문 확인 필요", "en": "Needs source confirmation"},
}


SOURCE_TEXT_COLUMNS = {
    "Evidence",
    "Evidence Summary",
    "Extracted Evidence",
    "Reason",
    "Matched Terms",
    "Regulatory Basis",
    "Reviewer Note",
    "검토메모 / Reviewer Note",
}


def ui_label(value: str) -> str:
    override = COLUMN_LABEL_OVERRIDES.get(str(value))
    if override:
        return override.get(current_language(), override.get("en", str(value)))
    return _localize_display_text(str(value))


def ui_value(value, column: str | None = None):
    if not isinstance(value, str):
        return value
    if column in SOURCE_TEXT_COLUMNS:
        return value
    override = VALUE_LABEL_OVERRIDES.get(value)
    if override:
        return override.get(current_language(), override.get("en", value))
    return _localize_display_text(value)


def _localize_display_text(value: str) -> str:
    if current_language() == "ko":
        override = VALUE_LABEL_OVERRIDES.get(value)
        if override:
            return override.get("ko", value)
        return value
    if not re.search(r"[가-힣]", value or ""):
        return value
    parts = [part.strip() for part in re.split(r"\s*/\s*", value) if part.strip()]
    english_parts = [part for part in parts if not re.search(r"[가-힣]", part)]
    if english_parts:
        return english_parts[-1]
    return VALUE_LABEL_OVERRIDES.get(value, {}).get("en", value)


def ui_dataframe(data) -> pd.DataFrame:
    df = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    if df.empty:
        return df
    localized = df.copy()
    original_columns = list(localized.columns)
    for column in original_columns:
        if current_language() == "en" and column not in SOURCE_TEXT_COLUMNS:
            localized[column] = localized[column].map(lambda value: ui_value(value, column))
    localized.columns = [ui_label(column) for column in original_columns]
    return localized


def workflow_label(value: str) -> str:
    return t(value)


def option_label(value: str) -> str:
    return t(value)


def rerun_app() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def render_sidebar_menu() -> str:
    selected = st.session_state.get("workflow_selector", WORKFLOW_OPTIONS[0])
    st.caption(t("view"))
    for option in WORKFLOW_OPTIONS:
        is_selected = option == selected
        marker = "●" if is_selected else "○"
        label = f"{marker} {WORKFLOW_ICONS[option]}  {workflow_label(option)}"
        if st.button(
            label,
            key=f"sidebar_nav_{option.lower().replace(' ', '_')}",
            type="primary" if is_selected else "secondary",
            use_container_width=True,
        ):
            if not is_selected:
                st.session_state.workflow_selector = option
                rerun_app()
    return st.session_state.get("workflow_selector", WORKFLOW_OPTIONS[0])


def render_sidebar_footer() -> None:
    st.markdown(
        f"""
<div class="sidebar-dev-card">
  <strong>{t("developer_info")}</strong>
  <span>{t("developer_name")}: Young Lee</span>
  <span>{t("developer_role")}: {t("developer_role_value")}</span>
  <span>{t("developer_project")}: ToxiGuard-Platform Ver.1</span>
</div>
""",
        unsafe_allow_html=True,
    )
    st.text_area(
        t("sidebar_comment"),
        key="sidebar_comment",
        placeholder=t("sidebar_comment_placeholder"),
        height=96,
    )


def render_language_selector() -> None:
    _, right = st.columns([0.78, 0.22])
    with right:
        selected_language = st.selectbox(
            t("language"),
            LANGUAGE_OPTIONS,
            index=LANGUAGE_OPTIONS.index(current_language()),
            format_func=lambda value: LANGUAGE_LABELS[value],
            key="language_selector",
        )
        st.session_state.ui_language = selected_language


def render_header() -> None:
    st.markdown(
        f"""
<div class="tg-header">
  <p class="tg-title">ToxiGuard-Platform Ver.1</p>
  <div class="tg-subtitle">{t("subtitle")}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_status_strip() -> None:
    rdkit_status = t("rdkit_active") if RDKIT_AVAILABLE else t("fallback_mode")
    st.markdown(
        f"""
<div class="status-strip">
  <div class="status-cell"><div class="status-label">{t("engine")}</div><div class="status-value">{rdkit_status}</div></div>
  <div class="status-cell"><div class="status-label">{t("document_flow")}</div><div class="status-value">KOR/ENG OCR + CTD</div></div>
  <div class="status-cell"><div class="status-label">{t("regulatory_frame")}</div><div class="status-value">FDA-style Worksheet</div></div>
  <div class="status-cell"><div class="status-label">{t("output")}</div><div class="status-value">IR + Review Language</div></div>
</div>
""",
        unsafe_allow_html=True,
    )


def bullet_list(items: list[str], empty_text: str) -> None:
    if not items:
        st.caption(empty_text)
        return
    for item in items:
        st.write(f"- {item}")


def assessment_table(assessments: list) -> pd.DataFrame:
    rows = []
    for item in assessments:
        rows.append(
            {
                "SMILES": item.smiles,
                t("Valid"): item.valid_structure,
                t("ICH M7 Class"): item.ich_m7_class,
                t("Risk Score"): item.risk_score,
                t("Alerts"): ", ".join(alert["name"] for alert in item.alerts) or "None",
                t("Conclusion"): item.conclusion,
            }
        )
    return pd.DataFrame(rows)


def show_table(rows: list[dict], empty_text: str | None = None) -> None:
    if not rows:
        st.caption(empty_text or t("no_rows"))
        return
    st.dataframe(ui_dataframe(rows), use_container_width=True, hide_index=True)


def show_source_table(rows: list[dict], empty_text: str | None = None) -> None:
    if not rows:
        st.caption(empty_text or t("no_source_rows"))
        return
    st.dataframe(
        ui_dataframe(rows),
        use_container_width=True,
        hide_index=True,
        column_config={"URL": st.column_config.LinkColumn("URL")},
    )


def show_signal_details(summary: dict, key: str, empty_text: str) -> None:
    details = (summary.get("signal_details") or {}).get(key, [])
    if details:
        df = pd.DataFrame(details)
        df["Evidence Summary"] = df["Evidence"].apply(lambda value: " ".join(str(value).split())[:260])
        preferred = [
            "Evidence Role",
            "Evidence Summary",
            "Page",
            "Confidence",
            "Source CTD Section",
            "CTD Mapping",
            "Reason",
            "Matched Terms",
            "Regulatory Basis",
            "Evidence Type",
            "Evidence",
        ]
        columns = [col for col in preferred if col in df.columns]
        st.dataframe(ui_dataframe(df[columns]), use_container_width=True, hide_index=True)
    else:
        bullet_list(summary.get(key, []), empty_text)


def show_regulatory_sources(summary: dict | None = None, key_prefix: str = "regulatory_sources") -> None:
    summary = summary or {}
    source_tabs = st.tabs([t("Category Crosswalk"), t("Evidence Matches"), t("Source Library")])

    with source_tabs[0]:
        crosswalk = summary.get("regulatory_source_crosswalk") or build_regulatory_source_crosswalk(summary)
        show_source_table(crosswalk, t("no_source_crosswalk"))

    with source_tabs[1]:
        matches = summary.get("regulatory_source_matches") or build_regulatory_source_matches(summary)
        show_source_table(matches, t("no_evidence_matches"))

    with source_tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            category_filter = st.selectbox(
                t("Signal Category"),
                category_options(),
                format_func=lambda value: t("All") if value == "All" else CATEGORY_LABELS.get(value, value),
                key=f"{key_prefix}_category_filter",
            )
        with col2:
            source_type_filter = st.selectbox(
                t("Source Type"),
                source_type_options(),
                key=f"{key_prefix}_source_type_filter",
            )
        show_source_table(source_catalog_rows(category_filter, source_type_filter), t("no_source_filter"))


def show_project_dossier() -> None:
    project = st.session_state.get("project_dossier") or {}
    inventory = st.session_state.get("project_inventory") or []
    document_summaries = st.session_state.get("document_summaries") or []
    if not project:
        st.caption(t("No project documents analyzed."))
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("Documents"), project.get("document_count", 0))
    col2.metric(t("Project Pages"), len(project.get("pages") or []))
    col3.metric(t("Readable Characters"), f"{len(project.get('combined_text', '')):,}")
    col4.metric(t("Extraction Warnings"), len(project.get("warnings") or []))

    if inventory:
        st.markdown(f"#### {t('Uploaded Documents')}")
        st.dataframe(ui_dataframe(inventory), use_container_width=True, hide_index=True)
    if document_summaries:
        st.markdown(f"#### {t('Per-Document Signal Summary')}")
        st.dataframe(ui_dataframe(document_summaries), use_container_width=True, hide_index=True)
    for warning in project.get("warnings") or []:
        st.warning(warning)


def page_option_label(page: dict, index: int) -> str:
    document = page.get("document")
    source_page = page.get("page", index + 1)
    project_page = page.get("project_page", source_page)
    if document:
        return f"Project p.{project_page} · {document} p.{source_page}"
    return f"Page {source_page}"


def current_product_context() -> dict:
    summary = st.session_state.get("document_summary") or {}
    return summary.get("product_context") or st.session_state.get("product_context") or {}


def document_summary_has_evidence(summary: dict) -> bool:
    if not summary:
        return False
    if summary.get("product_context", {}).get("basic_info"):
        return True
    if any(summary.get(key) for key in ("specifications", "test_methods", "bioequivalence", "stability", "candidate_compounds")):
        return True
    signal_details = summary.get("signal_details") or {}
    return any(signal_details.get(key) for key in signal_details)


def upload_signature(uploaded_files: list | None) -> str:
    """Stable-enough signature for Streamlit UploadedFile selections."""
    parts = []
    for uploaded in uploaded_files or []:
        parts.append(
            f"{getattr(uploaded, 'name', 'upload')}|"
            f"{getattr(uploaded, 'type', '')}|"
            f"{getattr(uploaded, 'size', 0)}"
        )
    return "||".join(parts)


def manual_text_signature(manual_text: str) -> str:
    clean = manual_text.strip()
    if not clean:
        return ""
    digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:16]
    return f"manual|{len(clean)}|{digest}"


def reset_document_analysis_state() -> None:
    st.session_state.project_dossier = {}
    st.session_state.project_documents = []
    st.session_state.project_inventory = []
    st.session_state.document_summaries = []
    st.session_state.document_text = ""
    st.session_state.document_pages = []
    st.session_state.document_summary = None
    st.session_state.product_context = {}
    st.session_state.assessments = []
    for key in [
        "last_upload_signature",
        "last_manual_signature",
        "be_profile",
        "be_profile_note",
        "be_reported_f2",
        "be_source_hint",
        "be_profile_document_key",
        "be_result",
        "be_profile_summary",
    ]:
        st.session_state.pop(key, None)


def analyze_project_inputs(project_name: str, uploaded_files: list | None, manual_text: str) -> bool:
    documents = []
    for uploaded in uploaded_files or []:
        result = extract_document_text(uploaded.getvalue(), uploaded.type)
        documents.append(
            normalize_document_record(
                name=uploaded.name,
                content_type=uploaded.type,
                text=result.text,
                pages=result.pages,
                bytes_received=result.bytes_received,
                warnings=result.warnings,
                source="upload",
            )
        )
    if manual_text.strip():
        documents.append(manual_document_record(manual_text, t("manual_text_document")))

    if not documents:
        st.warning(t("project_empty_warning"))
        return False

    project = combine_project_documents(project_name, documents)
    text = project["combined_text"]
    summary = analyze_ctd_text(text)
    document_summaries = [
        document_signal_overview(document, analyze_ctd_text(document.get("text", "")))
        for document in documents
    ]

    st.session_state.project_name = project["project_name"]
    st.session_state.project_dossier = project
    st.session_state.project_documents = documents
    st.session_state.project_inventory = project["inventory"]
    st.session_state.document_summaries = document_summaries
    st.session_state.document_text = text
    st.session_state.document_pages = project["pages"]
    st.session_state.document_summary = summary
    st.session_state.product_context = summary.get("product_context", {})
    sync_application_profile_from_context(st.session_state.product_context)

    detected = []
    for compound in summary.get("candidate_compounds", []):
        detected.append(assess_smiles(compound["smiles"]))
    st.session_state.assessments = detected

    st.session_state.last_upload_signature = upload_signature(uploaded_files)
    st.session_state.last_manual_signature = manual_text_signature(manual_text)
    for warning in project.get("warnings") or []:
        st.warning(warning)
    return True


def show_product_context(context: dict | None = None, compact: bool = False) -> None:
    context = context or current_product_context()
    has_context = any(
        context_table(context, key)
        for key in ["basic_info", "linked_substances", "formulation", "package_storage", "review_links"]
    )
    if not has_context:
        st.caption(t("no_product_context"))
        return

    basic = context_table(context, "basic_info")
    linked = context_table(context, "linked_substances")
    formulation = context_table(context, "formulation")
    package_storage = context_table(context, "package_storage")
    links = context_table(context, "review_links")

    if compact:
        label = context.get("product_name") or context.get("active_substance") or t("linked_document_context")
        with st.expander(f"{t('linked_document_context')}: {label}", expanded=False):
            if basic:
                show_table(basic)
            if linked:
                st.markdown(f"#### {t('Linked Substances')}")
                show_table(linked)
            if formulation:
                st.markdown(f"#### {t('Formulation')}")
                show_table(formulation)
        return

    tabs = st.tabs([t("Basic Info"), t("Linked Substances"), t("Formulation"), t("Package / Storage"), t("Menu Links")])
    with tabs[0]:
        show_table(basic, t("no_basic_info"))
    with tabs[1]:
        show_table(linked, t("no_linked_substances"))
    with tabs[2]:
        show_table(formulation, t("no_formulation"))
    with tabs[3]:
        show_table(package_storage, t("no_package_storage"))
    with tabs[4]:
        show_table(links, t("no_menu_links"))


def sync_application_profile_from_context(context: dict) -> None:
    if not context:
        return
    profile = st.session_state.application_profile.copy()
    updates = {
        "product_name": context.get("product_name") or context.get("active_substance"),
        "dosage_form": context.get("dosage_form"),
        "route": context.get("route"),
    }
    changed = False
    for key, value in updates.items():
        if value and profile.get(key, "TBD") in {"", "TBD", None}:
            profile[key] = value
            changed = True
    if changed:
        st.session_state.application_profile = profile


def render_application_snapshot() -> dict:
    profile = st.session_state.application_profile
    with st.form("application_snapshot_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            application_type = st.selectbox(
                t("Application Type"),
                ["ANDA", "NDA", "IND", "BLA", "DMF"],
                index=["ANDA", "NDA", "IND", "BLA", "DMF"].index(profile.get("application_type", "ANDA")),
            )
            application_number = st.text_input(t("Application Number"), value=profile.get("application_number", "TBD"))
            product_name = st.text_input(t("Product Name"), value=profile.get("product_name", "TBD"))
        with col2:
            applicant = st.text_input(t("Applicant"), value=profile.get("applicant", "TBD"))
            dosage_form = st.text_input(t("Dosage Form"), value=profile.get("dosage_form", "TBD"))
            route = st.text_input(t("Route"), value=profile.get("route", "TBD"))
        with col3:
            review_cycle = st.selectbox(
                t("Review Cycle"),
                ["Cycle 1", "Cycle 2", "Cycle 3", "Post-Approval"],
                index=["Cycle 1", "Cycle 2", "Cycle 3", "Post-Approval"].index(profile.get("review_cycle", "Cycle 1")),
            )
            discipline_owner = st.text_input(t("Discipline Owner"), value=profile.get("discipline_owner", "Quality / Toxicology"))
            review_status = st.selectbox(
                t("Review Status"),
                ["In Review", "Information Request", "Adequate", "Not Adequate"],
                index=["In Review", "Information Request", "Adequate", "Not Adequate"].index(profile.get("review_status", "In Review")),
            )

        submitted = st.form_submit_button(t("Update Snapshot"), type="primary")

    updated = {
        "application_type": application_type,
        "application_number": application_number,
        "product_name": product_name,
        "applicant": applicant,
        "dosage_form": dosage_form,
        "route": route,
        "review_cycle": review_cycle,
        "discipline_owner": discipline_owner,
        "review_status": review_status,
    }
    if submitted:
        st.session_state.application_profile = updated
        st.success(t("snapshot_updated"))
    return updated


render_language_selector()
render_header()
render_status_strip()

with st.sidebar:
    st.subheader(t("workspace"))
    workflow = render_sidebar_menu()
    st.divider()
    st.caption(t("prototype_status"))
    st.write(t("decision_support_only"))
    st.write(t("expert_review_required"))
    render_sidebar_footer()


if "document_summary" not in st.session_state:
    st.session_state.document_summary = None
if "document_text" not in st.session_state:
    st.session_state.document_text = ""
if "document_pages" not in st.session_state:
    st.session_state.document_pages = []
if "project_name" not in st.session_state:
    st.session_state.project_name = t("project_default_name")
if "project_dossier" not in st.session_state:
    st.session_state.project_dossier = {}
if "project_inventory" not in st.session_state:
    st.session_state.project_inventory = []
if "project_documents" not in st.session_state:
    st.session_state.project_documents = []
if "document_summaries" not in st.session_state:
    st.session_state.document_summaries = []
if "product_context" not in st.session_state:
    st.session_state.product_context = {}
if "assessments" not in st.session_state:
    st.session_state.assessments = []
if "application_profile" not in st.session_state:
    st.session_state.application_profile = DEFAULT_APPLICATION_PROFILE.copy()


if workflow == "Document Analyzer":
    left, right = st.columns([0.42, 0.58], gap="large")

    with left:
        st.subheader(t("CTD Document Intake"))
        st.markdown(
            f"""
<div class="review-banner">
  <strong>{t("Project Dossier")}</strong>
  <span>{t("project_dossier_body")}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        project_name = st.text_input(t("Project Name"), value=st.session_state.project_name)
        uploaded_files = st.file_uploader(
            t("Upload CTD documents"),
            type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="project_uploads",
        )
        current_upload_signature = upload_signature(uploaded_files)
        if uploaded_files:
            st.caption(f"{t('Selected Files')}: {len(uploaded_files)}")
            for uploaded in uploaded_files:
                st.write(f"- {uploaded.name}")

        action_col, clear_col = st.columns([0.68, 0.32])
        with action_col:
            analyze_upload_clicked = st.button(
                t("Analyze Uploaded Files"),
                type="primary",
                use_container_width=True,
                disabled=not bool(uploaded_files),
            )
        with clear_col:
            clear_clicked = st.button(t("Clear Analysis"), use_container_width=True)

        if clear_clicked:
            reset_document_analysis_state()
            st.session_state.last_upload_signature = current_upload_signature
            st.success(t("analysis_cleared"))

        manual_text = st.text_area(
            t("manual_text_label"),
            height=180,
            placeholder=t("manual_text_placeholder"),
            key="manual_ctd_text",
        )
        analyze_project_clicked = st.button(t("Analyze Project"), use_container_width=True)

        auto_analyze_upload = (
            bool(uploaded_files)
            and bool(current_upload_signature)
            and not manual_text.strip()
            and current_upload_signature != st.session_state.get("last_upload_signature")
            and not clear_clicked
        )
        if auto_analyze_upload or analyze_upload_clicked or analyze_project_clicked:
            analysis_manual_text = manual_text if analyze_project_clicked else ""
            with st.spinner(t("processing_documents")):
                completed = analyze_project_inputs(project_name, uploaded_files, analysis_manual_text)
            if completed:
                st.success(t("auto_analysis_complete") if auto_analyze_upload else t("project_analysis_complete"))
                st.caption(t("analysis_persist_hint"))

    with right:
        st.subheader(t("Document Signals"))
        summary = st.session_state.document_summary
        if not summary:
            st.info(t("upload_to_begin"))
        else:
            if summary.get("language"):
                st.caption(f"{t('detected_language')}: {summary['language']}")
            profile = summary.get("document_profile") or {}
            if profile.get("source_ctd_section"):
                role_note = t("supporting_rationale_mode") if profile.get("development_mode") else t("direct_evidence_mode")
                st.caption(
                    f"{t('document_profile')}: {profile.get('source_ctd_section')} "
                    f"{profile.get('document_type', '')} · {role_note}"
                )
            st.write(summary["narrative"])
            workflow_tabs = st.tabs(
                [
                    t("Project Dossier"),
                    t("Product Context"),
                    t("Spec Table"),
                    t("Writing Structure"),
                    t("Regulatory Sources"),
                    t("Signals"),
                    t("Raw Pages"),
                    t("Evidence Blocks"),
                    t("Reviewer Correction"),
                ]
            )
            with workflow_tabs[0]:
                show_project_dossier()

            with workflow_tabs[1]:
                show_product_context(summary.get("product_context"))

            with workflow_tabs[2]:
                show_table(summary.get("specification_table", []), t("No specification table generated."))

            with workflow_tabs[3]:
                st.caption(summary.get("writing_outline", t("writing_structure_default")))
                show_table(summary.get("writing_structure", []), t("No writing structure generated."))

            with workflow_tabs[4]:
                show_regulatory_sources(summary, key_prefix="document_sources")

            with workflow_tabs[5]:
                tabs = st.tabs([t("Specifications"), t("Test Method"), t("Bioequivalence"), t("Stability"), t("Compounds")])
                with tabs[0]:
                    show_signal_details(summary, "specifications", t("No specification signals detected."))
                with tabs[1]:
                    show_signal_details(summary, "test_methods", t("No test method signals detected."))
                with tabs[2]:
                    show_signal_details(summary, "bioequivalence", t("No bioequivalence signals detected."))
                with tabs[3]:
                    show_signal_details(summary, "stability", t("No stability signals detected."))
                with tabs[4]:
                    show_signal_details(summary, "compounds", t("No compound evidence details detected."))
                    if summary["candidate_compounds"]:
                        st.markdown(f"#### {t('Screenable Compounds')}")
                        st.dataframe(ui_dataframe(summary["candidate_compounds"]), use_container_width=True, hide_index=True)
                    else:
                        st.caption(t("No compounds detected."))

            with workflow_tabs[6]:
                pages = st.session_state.document_pages or [{"page": 1, "text": st.session_state.document_text}]
                page_options = list(range(len(pages)))
                selected_index = st.selectbox(
                    t("Page"),
                    page_options,
                    format_func=lambda index: page_option_label(pages[index], index),
                )
                selected = pages[selected_index]
                st.text_area(t("Extracted page text"), value=selected.get("text", ""), height=360)

            with workflow_tabs[7]:
                blocks = summary.get("evidence_blocks", [])
                if blocks:
                    st.dataframe(ui_dataframe(blocks), use_container_width=True, hide_index=True)
                else:
                    st.caption(t("No evidence blocks generated."))

            with workflow_tabs[8]:
                correction_df = signal_details_dataframe(summary)
                if correction_df.empty:
                    st.caption(t("No AI extracted signals to review."))
                else:
                    display_cols = [
                        "Reviewer Category",
                        "Reviewer Status",
                        "Reviewer Note",
                        "Evidence",
                        "Confidence",
                        "CTD Mapping",
                        "Reason",
                        "Page",
                    ]
                    correction_df = correction_df[[col for col in display_cols if col in correction_df.columns]]
                    edited = st.data_editor(
                        correction_df,
                        use_container_width=True,
                        hide_index=True,
                        num_rows="dynamic",
                        column_config={
                            "Reviewer Category": st.column_config.SelectboxColumn(
                                "Reviewer Category",
                                options=["Specifications", "Test Methods", "Bioequivalence", "Stability", "Compounds", "Unknown"],
                            ),
                            "Reviewer Status": st.column_config.SelectboxColumn(
                                "Reviewer Status",
                                options=["AI Extracted", "Accepted", "Corrected", "Rejected"],
                            ),
                        },
                        key="reviewer_correction_editor",
                    )
                    if st.button(t("Apply Reviewer Corrections"), type="primary"):
                        st.session_state.document_summary = apply_reviewer_corrections(summary, edited)
                        st.success(t("corrections_applied"))
                        st.rerun()

            if st.session_state.assessments:
                st.subheader(t("Auto-Screened Compounds"))
                st.dataframe(assessment_table(st.session_state.assessments), use_container_width=True, hide_index=True)


elif workflow == "Molecule Screening":
    st.subheader(t("ICH M7 Molecule Screening"))
    context = current_product_context()
    show_product_context(context, compact=True)

    examples = {
        "Aniline": "c1ccc(N)cc1",
        "Nitrobenzene": "c1ccc(cc1)[N+](=O)[O-]",
        "Acetaminophen": "CC(=O)NC1=CC=C(O)C=C1",
        "Telmisartan": "CCCC1=NC2=C(N1CC3=CC=C(C=C3)C4=CC=CC=C4C(=O)O)C=C(C=C2C)C5=NC6=CC=CC=C6N5C",
    }

    linked_substances = substance_options(context)
    selected_compound = None
    if linked_substances:
        labels = [f"{item.get('Name', 'Unknown')} · {item.get('Role', 'candidate')}" for item in linked_substances]
        selected_label = st.selectbox(t("Document-linked substance"), ["Manual entry"] + labels, format_func=option_label)
        if selected_label != "Manual entry":
            selected_compound = linked_substances[labels.index(selected_label)]
            if selected_compound.get("SMILES"):
                st.info(f"{t('using_document_structure')} {selected_compound.get('Name')}.")
            else:
                st.warning(t("smiles_needed"))

    choice = st.selectbox(t("Example"), ["Custom"] + list(examples.keys()), format_func=option_label)
    if selected_compound is not None:
        default_smiles = selected_compound.get("SMILES", "")
    else:
        default_smiles = "" if choice == "Custom" else examples[choice]
    smiles = st.text_input(
        "SMILES",
        value=default_smiles,
        placeholder=t("smiles_placeholder"),
        key=f"molecule_smiles_{default_smiles[:24]}_{choice}",
    )

    if st.button(t("Run Screening"), type="primary"):
        assessment = assess_smiles(smiles)
        st.session_state.assessments = [assessment]

    if st.session_state.assessments:
        assessment = st.session_state.assessments[-1]
        col1, col2, col3 = st.columns(3)
        col1.metric(t("Risk Score"), f"{assessment.risk_score:.2f}")
        col2.metric(t("ICH M7 Class"), assessment.ich_m7_class)
        col3.metric(t("Alerts"), len(assessment.alerts))

        st.write(build_regulatory_narrative(assessment))

        if assessment.alerts:
            st.dataframe(ui_dataframe(assessment.alerts), use_container_width=True, hide_index=True)
        if assessment.experimental_reference:
            st.info(
                f"Reference: {assessment.experimental_reference['name']} - "
                f"{assessment.experimental_reference['result']}. {assessment.experimental_reference['basis']}"
            )


elif workflow == "ToxiGuard Tools":
    st.subheader(t("ToxiGuard Platform Tools"))
    context = current_product_context()
    show_product_context(context, compact=True)
    context_compound_name = primary_context_name(context)
    context_smiles = primary_context_smiles(context)
    tool = st.selectbox(
        t("Tool Menu"),
        [
            "Pharmaceutical Equivalence Matrix",
            "Specification / Test Method Matrix",
            "Related Substances Evaluation",
            "Genotoxicity Assessment",
            "Stability Shelf-Life Prediction",
            "Reference Impurity Lookup",
            "QSAR Evidence Matrix",
            "Experimental Evidence Dossier",
            "Degradation / Impurity Prediction",
            "Engine Validation",
        ],
        format_func=option_label,
    )

    if tool == "Pharmaceutical Equivalence Matrix":
        st.markdown(
            f"""
<div class="review-banner">
  <strong>{t("pharm_eq_title")}</strong>
  <span>{t("pharm_eq_body")}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        summary = st.session_state.document_summary or {}
        eq_matrix = build_pharmaceutical_equivalence_matrix(summary, context)
        if not eq_matrix.empty:
            found = int((eq_matrix["상태 / Status"] == "Evidence found").sum())
            col1, col2, col3 = st.columns(3)
            col1.metric(t("test_item_total"), len(eq_matrix))
            col2.metric(t("linked_items"), found)
            col3.metric(t("needs_source"), len(eq_matrix) - found)
            st.dataframe(ui_dataframe(eq_matrix), use_container_width=True, hide_index=True)
        else:
            st.info(t("no_rows"))

        st.divider()
        st.markdown(f"#### {t('be_f2_title')}")
        st.markdown(
            f"""
<div class="review-banner">
  <strong>{t("be_f2_title")}</strong>
  <span>{t("be_f2_body")}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        document_text_key = f"{len(st.session_state.document_text or '')}:{hash(st.session_state.document_text or '')}"
        if (
            "be_profile" not in st.session_state
            or st.session_state.get("be_profile_document_key") != document_text_key
        ):
            seeded_profile, reported_f2, source_hint = dissolution_profile_from_document_text(st.session_state.document_text or "")
            if seeded_profile.empty:
                st.session_state.be_profile = DEFAULT_DISSOLUTION_PROFILE.copy()
                st.session_state.be_profile_note = t("be_default_profile")
                st.session_state.be_reported_f2 = None
                st.session_state.be_source_hint = ""
            else:
                st.session_state.be_profile = seeded_profile
                st.session_state.be_profile_note = t("be_seed_from_document")
                st.session_state.be_reported_f2 = reported_f2
                st.session_state.be_source_hint = source_hint
            st.session_state.be_profile_document_key = document_text_key
            st.session_state.pop("be_result", None)
            st.session_state.pop("be_profile_summary", None)

        st.caption(st.session_state.get("be_profile_note", ""))
        if st.session_state.get("be_reported_f2") is not None:
            st.caption(f"Reported document f2: {st.session_state.be_reported_f2:g}")
        if st.session_state.get("be_source_hint"):
            st.caption(st.session_state.be_source_hint)

        be_profile_input = st.data_editor(
            st.session_state.be_profile,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="be_dissolution_profile_editor",
        )
        bootstrap_runs = st.slider(
            t("Bootstrap Iterations"),
            min_value=500,
            max_value=10000,
            value=2000,
            step=500,
        )
        if st.button(t("Calculate f2 with Bootstrap"), type="primary", use_container_width=True):
            try:
                st.session_state.be_profile = be_profile_input
                st.session_state.be_result = calculate_f2(be_profile_input, bootstrap_runs=bootstrap_runs)
                st.session_state.be_profile_summary = dissolution_profile_summary(be_profile_input)
            except Exception as exc:
                st.error(f"f2 calculation failed: {exc}")

        if "be_result" in st.session_state:
            be_result = st.session_state.be_result
            b1, b2, b3 = st.columns(3)
            b1.metric(t("f2 Similarity Factor"), be_result.f2)
            b2.metric(t("Bootstrap 95% CI"), f"{be_result.ci_low} - {be_result.ci_high}")
            b3.metric(t("P(f2 >= 50)"), f"{be_result.probability_f2_ge_50}%")
            if be_result.f2 >= 50 and be_result.cv_flag == "Acceptable":
                st.success(be_result.fda_decision)
            elif be_result.f2 >= 50:
                st.warning(f"{be_result.fda_decision}; {t('CV Check')}: {be_result.cv_flag}")
            else:
                st.error(be_result.fda_decision)
            st.info(f"{t('Next Action')}: {be_result.fda_next_action}")
            st.caption(be_result.method_note)

            profile_summary = st.session_state.get("be_profile_summary")
            if isinstance(profile_summary, pd.DataFrame) and not profile_summary.empty:
                st.markdown(f"##### {t('Dissolution Profile Summary')}")
                st.dataframe(ui_dataframe(profile_summary), use_container_width=True, hide_index=True)
                chart_df = profile_summary.set_index("Time (min)")[
                    ["Reference Mean (%)", "Test Mean (%)"]
                ]
                st.line_chart(chart_df)

    elif tool == "Specification / Test Method Matrix":
        st.markdown(
            f"""
<div class="review-banner">
  <strong>{t("spec_matrix_title")}</strong>
  <span>{t("spec_matrix_body")}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        summary = st.session_state.document_summary or {}
        matrix = build_test_item_matrix(summary)
        if matrix:
            total = len(matrix)
            linked = sum(1 for row in matrix if row.get("상태 / Status") == "Linked")
            method_gap = sum(1 for row in matrix if "method" in row.get("상태 / Status", "").lower())
            criteria_gap = sum(1 for row in matrix if "criteria" in row.get("상태 / Status", "").lower())
            col1, col2, col3, col4 = st.columns(4)
            col1.metric(t("test_item_total"), total)
            col2.metric(t("linked_items"), linked)
            col3.metric(t("needs_method"), method_gap)
            col4.metric(t("needs_criteria"), criteria_gap)

            statuses = [row.get("상태 / Status", "Unmapped") for row in matrix]
            selected_status = st.selectbox(
                t("Filter Status"),
                ["All Statuses"] + sorted(set(statuses)),
                format_func=option_label,
            )
            display_rows = matrix if selected_status == "All Statuses" else [row for row in matrix if row.get("상태 / Status") == selected_status]
            st.dataframe(ui_dataframe(display_rows), use_container_width=True, hide_index=True)
        else:
            st.info(t("No criteria/test method matrix generated."))

    elif tool == "Related Substances Evaluation":
        st.markdown(
            f"""
<div class="review-banner">
  <strong>{t("related_substances_title")}</strong>
  <span>{t("related_substances_body")}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        material_type = st.selectbox(
            "Material Type",
            ["Drug product", "Drug substance"],
            format_func=lambda value: "완제의약품" if current_language() == "ko" and value == "Drug product" else ("원료의약품" if current_language() == "ko" else value),
        )
        default_rows = pd.DataFrame(
            [
                {
                    "Impurity Code": "API-RS-1",
                    "Chemical Name": f"{context_compound_name} related substance",
                    "Origin": "process impurity",
                    "Observed (%)": 0.06,
                    "Specification (%)": 0.10,
                    "Concern": "document-linked API impurity control",
                },
                {
                    "Impurity Code": "GTI-1",
                    "Chemical Name": "Potential alkyl halide",
                    "Origin": "unreacted starting material",
                    "Observed (%)": 0.12,
                    "Specification (%)": 0.05,
                    "Concern": "potential mutagenic impurity",
                },
            ]
        )
        impurity_input = st.data_editor(default_rows, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button(t("Run Evaluation"), type="primary"):
            result = evaluate_related_substances(impurity_input, material_type=material_type)
            basis = build_related_substance_evidence_basis(
                impurity_input,
                compound_name=context_compound_name,
                material_type=material_type,
            )
            st.session_state.related_substance_result = result
            st.session_state.related_substance_basis = basis
        if "related_substance_result" in st.session_state:
            result_tabs = st.tabs([t("Assessment Result"), t("Evidence Basis Matrix")])
            with result_tabs[0]:
                result = st.session_state.related_substance_result
                if isinstance(result, pd.DataFrame) and not result.empty:
                    st.dataframe(ui_dataframe(result), use_container_width=True, hide_index=True)
                else:
                    st.info(t("no_rows"))
            with result_tabs[1]:
                st.caption(t("basis_caption"))
                basis = st.session_state.get("related_substance_basis", pd.DataFrame())
                if isinstance(basis, pd.DataFrame) and not basis.empty:
                    st.dataframe(ui_dataframe(basis), use_container_width=True, hide_index=True)
                else:
                    st.info(t("no_rows"))

    elif tool == "Genotoxicity Assessment":
        st.markdown(
            f"""
<div class="review-banner">
  <strong>{t("genotoxicity_title")}</strong>
  <span>{t("genotoxicity_body")}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        default_genotox_rows = pd.DataFrame(
            [
                {
                    "Compound": f"{context_compound_name} related substance",
                    "Role": "API-related impurity",
                    "SMILES": context_smiles,
                    "Endpoint": "Bacterial reverse mutation / Ames mutagenicity",
                    "Expert Rule-Based Model": "ToxiGuard prototype expert alerts",
                    "Expert Applicability Domain": "Needs confirmation against validated expert-rule system",
                    "Statistical Model": "",
                    "Statistical QSAR Result": "",
                    "Statistical Applicability Domain": "",
                    "Validation Metrics / External Predictivity": "",
                    "Mechanistic Rationale": "",
                    "Experimental / Literature Data": "",
                },
                {
                    "Compound": "Potential aromatic amine",
                    "Role": "Process impurity",
                    "SMILES": "c1ccc(N)cc1",
                    "Endpoint": "Bacterial reverse mutation / Ames mutagenicity",
                    "Expert Rule-Based Model": "ToxiGuard prototype expert alerts",
                    "Expert Applicability Domain": "In-domain for aromatic amine alert family; confirm with validated model",
                    "Statistical Model": "External statistical QSAR model needed",
                    "Statistical QSAR Result": "Positive alert expected; replace with actual model output",
                    "Statistical Applicability Domain": "Nearest aromatic amine analogs expected; confirm model AD",
                    "Validation Metrics / External Predictivity": "Vendor/model validation summary required",
                    "Mechanistic Rationale": "Aromatic amine metabolic activation concern",
                    "Experimental / Literature Data": "Representative aromatic amine Ames concern",
                },
            ]
        )
        genotox_input = st.data_editor(default_genotox_rows, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button(t("Run Genotoxicity Assessment"), type="primary"):
            genotox_result = assess_genotoxicity_table(genotox_input)
            genotox_basis = build_genotoxicity_evidence_basis(genotox_input)
            qsar_validation = build_qsar_model_validation_matrix(genotox_input)
            qsar_sources = qsar_reference_source_table()
            st.session_state.genotoxicity_tool_result = genotox_result
            st.session_state.genotoxicity_basis_result = genotox_basis
            st.session_state.qsar_validation_result = qsar_validation
            st.session_state.qsar_reference_sources = qsar_sources
        if "genotoxicity_tool_result" in st.session_state:
            result_tabs = st.tabs(
                [
                    t("Assessment Result"),
                    t("QSAR Validation Matrix"),
                    t("Evidence Basis Matrix"),
                    t("Reference Sources"),
                ]
            )
            with result_tabs[0]:
                result = st.session_state.genotoxicity_tool_result
                if isinstance(result, pd.DataFrame) and not result.empty:
                    class_counts = result["ICH M7 Class"].value_counts()
                    cols = st.columns(min(4, max(1, len(class_counts))))
                    for index, (class_name, count) in enumerate(class_counts.items()):
                        cols[index % len(cols)].metric(class_name, int(count))
                    st.dataframe(ui_dataframe(result), use_container_width=True, hide_index=True)
                else:
                    st.info(t("no_rows"))
            with result_tabs[1]:
                st.caption(t("qsar_validation_caption"))
                validation = st.session_state.get("qsar_validation_result", pd.DataFrame())
                if isinstance(validation, pd.DataFrame) and not validation.empty:
                    status_counts = validation["Status"].value_counts()
                    cols = st.columns(min(3, max(1, len(status_counts))))
                    for index, (status_name, count) in enumerate(status_counts.items()):
                        cols[index % len(cols)].metric(status_name, int(count))
                    st.dataframe(ui_dataframe(validation), use_container_width=True, hide_index=True)
                else:
                    st.info(t("no_rows"))
            with result_tabs[2]:
                st.caption(t("basis_caption"))
                basis = st.session_state.get("genotoxicity_basis_result", pd.DataFrame())
                if isinstance(basis, pd.DataFrame) and not basis.empty:
                    st.dataframe(ui_dataframe(basis), use_container_width=True, hide_index=True)
                else:
                    st.info(t("no_rows"))
            with result_tabs[3]:
                sources = st.session_state.get("qsar_reference_sources", qsar_reference_source_table())
                st.dataframe(
                    ui_dataframe(sources),
                    use_container_width=True,
                    hide_index=True,
                    column_config={"URL": st.column_config.LinkColumn("URL")},
                )

    elif tool == "Stability Shelf-Life Prediction":
        st.markdown(
            f"""
<div class="review-banner">
  <strong>{t("stability_prediction_title")}</strong>
  <span>{t("stability_prediction_body")}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        stab_spec = st.number_input(
            t("Specification Limit (%) for this impurity"),
            min_value=0.01,
            max_value=5.0,
            value=0.15,
            step=0.01,
        )
        col_long, col_accel = st.columns(2)
        with col_long:
            st.markdown(f"#### {t('Long-Term Data')}")
            long_default = pd.DataFrame(
                {
                    "Time (months)": [0, 3, 6, 9, 12, 18, 24],
                    "Impurity (%)": [0.02, 0.03, 0.04, 0.06, 0.07, 0.09, 0.11],
                }
            )
            long_df = st.data_editor(long_default, num_rows="dynamic", use_container_width=True, hide_index=True, key="long_stability_editor")
        with col_accel:
            st.markdown(f"#### {t('Accelerated Data')}")
            accel_default = pd.DataFrame(
                {
                    "Time (months)": [0, 1, 2, 3, 6],
                    "Impurity (%)": [0.02, 0.04, 0.07, 0.11, 0.18],
                }
            )
            accel_df = st.data_editor(accel_default, num_rows="dynamic", use_container_width=True, hide_index=True, key="accelerated_stability_editor")
        if st.button(t("Run Shelf-Life Prediction"), type="primary"):
            st.session_state.stability_prediction_result = predict_stability_shelf_life(long_df, accel_df, stab_spec)
        if "stability_prediction_result" in st.session_state:
            stability_result = st.session_state.stability_prediction_result
            metrics = stability_result.get("metrics", pd.DataFrame())
            if not metrics.empty:
                st.dataframe(ui_dataframe(metrics), use_container_width=True, hide_index=True)
            st.info(stability_result.get("interpretation", ""))
            long_projection = (stability_result.get("projections") or {}).get("Long-term")
            if isinstance(long_projection, pd.DataFrame) and not long_projection.empty:
                st.line_chart(
                    long_projection.set_index("Time (months)")[
                        ["Predicted Impurity (%)", "95% Upper Confidence (%)", "Specification Limit (%)"]
                    ],
                    use_container_width=True,
                )

    elif tool == "Reference Impurity Lookup":
        st.markdown(
            f"""
<div class="review-banner">
  <strong>{t("Reference Impurity Lookup")}</strong>
  <span>{'Prototype 참조 정보를 사용해 불순물 기원, 위험 관련성, 관리전략을 정리합니다.' if current_language() == 'ko' else 'Use loaded prototype references to frame likely impurity origin, risk relevance, and control strategy.'}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        compound = st.text_input(t("Compound Name"), value=context_compound_name, placeholder="Example: Acetaminophen or Telmisartan")
        refs = get_impurity_references(compound)
        st.dataframe(ui_dataframe(refs), use_container_width=True, hide_index=True)

    elif tool == "QSAR Evidence Matrix":
        st.markdown(
            f"""
<div class="review-banner">
  <strong>{t("QSAR Evidence Matrix")}</strong>
  <span>{'전문가 규칙 기반 경고, 기존 근거, 검토자 해석을 간결한 매트릭스로 분리합니다.' if current_language() == 'ko' else 'Separate expert rule-based alerts, historical evidence, and reviewer interpretation into a compact matrix.'}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        smiles = st.text_input("SMILES", value=context_smiles)
        if st.button(t("Build Evidence Matrix"), type="primary"):
            assessment = assess_smiles(smiles)
            st.session_state.assessments = [assessment]
            st.session_state.evidence_matrix = build_evidence_matrix(smiles)
        if "evidence_matrix" in st.session_state:
            st.dataframe(ui_dataframe(st.session_state.evidence_matrix), use_container_width=True, hide_index=True)
            st.write(build_regulatory_narrative(st.session_state.assessments[-1]))

    elif tool == "Experimental Evidence Dossier":
        st.markdown(
            f"""
<div class="review-banner">
  <strong>{t("Experimental Evidence Dossier")}</strong>
  <span>{'입력 구조에 대한 prototype 실험 근거와 유사체 정보를 표시합니다.' if current_language() == 'ko' else 'Show available prototype experimental evidence and similar-neighbor context for the entered structure.'}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        smiles = st.text_input("SMILES", value=context_smiles, key=f"experimental_smiles_{context_smiles[:24]}")
        evidence = get_experimental_evidence(smiles)
        if evidence:
            st.json(evidence, expanded=True)
        else:
            st.warning(t("No direct prototype evidence record found for this SMILES."))
        neighbors = get_similarity_neighbors(smiles)
        st.markdown(f"#### {t('Similarity / Analog Context')}")
        if neighbors.empty:
            st.caption(t("No prototype neighbor records available."))
        else:
            st.dataframe(ui_dataframe(neighbors), use_container_width=True, hide_index=True)

    elif tool == "Degradation / Impurity Prediction":
        st.markdown(
            f"""
<div class="review-banner">
  <strong>{t("Degradation / Impurity Prediction")}</strong>
  <span>{'Prototype 반응 규칙을 적용하고 예측 생성물을 ICH M7 엔진으로 즉시 스크리닝합니다.' if current_language() == 'ko' else 'Apply prototype reaction rules and immediately screen predicted products with the ICH M7 engine.'}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        smiles = st.text_input(t("Parent SMILES"), value=context_smiles)
        if st.button(t("Predict Products"), type="primary"):
            products = predict_degradation_products(smiles)
            st.session_state.predicted_products = products
        if "predicted_products" in st.session_state:
            st.dataframe(ui_dataframe(st.session_state.predicted_products), use_container_width=True, hide_index=True)

    elif tool == "Engine Validation":
        st.markdown(
            f"""
<div class="review-banner">
  <strong>{t("Engine Validation")}</strong>
  <span>{'참조 구조의 예상 경고 동작을 확인하는 작은 검증 패널을 실행합니다.' if current_language() == 'ko' else 'Run a small validation panel to check expected alert behavior for reference structures.'}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        validation = validate_engine()
        st.dataframe(ui_dataframe(validation), use_container_width=True, hide_index=True)
        st.caption(t("engine_validation_caption"))


elif workflow == "FDA Review Worksheet":
    st.subheader(t("FDA-Style Review Worksheet"))
    st.markdown(
        f"""
<div class="review-banner">
  <strong>{t("reviewer_workspace_title")}</strong>
  <span>{t("reviewer_workspace_body")}</span>
</div>
""",
        unsafe_allow_html=True,
    )

    profile = render_application_snapshot()
    worksheet = build_reviewer_worksheet(
        profile,
        st.session_state.document_summary,
        st.session_state.assessments,
    )
    st.session_state.worksheet = worksheet

    integrated = worksheet["integrated_assessment"]
    col1, col2, col3 = st.columns(3)
    col1.metric(t("Recommended Action"), integrated["Recommended Action"])
    col2.metric(t("Open Deficiencies"), sum(1 for item in worksheet["deficiency_tracker"] if item.get("Resolution") == "Open"))
    col3.metric(t("ICH M7 Items"), len(worksheet["ich_m7_review"]))

    st.write(worksheet["final_review_language"])

    tabs = st.tabs(
        [
            t("Submission Map"),
            t("Product Context"),
            t("Sources"),
            t("Spec Table"),
            t("Spec Writing"),
            t("CMC / Quality"),
            "ICH M7",
            t("Deficiencies"),
            t("Integrated Assessment"),
        ]
    )

    with tabs[0]:
        show_table(worksheet["submission_map"])

    with tabs[1]:
        show_product_context(worksheet.get("product_context") or current_product_context())

    with tabs[2]:
        source_tabs = st.tabs([t("Source Crosswalk"), t("Evidence Matches")])
        with source_tabs[0]:
            show_source_table(worksheet["regulatory_source_crosswalk"], t("no_source_crosswalk"))
        with source_tabs[1]:
            show_source_table(worksheet["regulatory_source_matches"], t("No evidence-to-source matches available."))

    with tabs[3]:
        show_table(worksheet["specification_table"], t("No specification table generated."))

    with tabs[4]:
        show_table(worksheet["specification_writing_structure"])

    with tabs[5]:
        show_table(worksheet["quality_assessment"])

    with tabs[6]:
        show_table(worksheet["ich_m7_review"])

    with tabs[7]:
        st.data_editor(
            pd.DataFrame(worksheet["deficiency_tracker"]),
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="deficiency_editor",
        )

    with tabs[8]:
        st.json(worksheet["integrated_assessment"], expanded=True)


elif workflow == "Regulatory Sources":
    st.subheader(t("Regulatory Source Library"))
    st.markdown(
        f"""
<div class="review-banner">
  <strong>{t("source_library_title")}</strong>
  <span>{t("source_library_body")}</span>
</div>
""",
        unsafe_allow_html=True,
    )
    show_regulatory_sources(st.session_state.document_summary, key_prefix="standalone_sources")


elif workflow == "Regulatory Report":
    st.subheader(t("Regulatory Report Builder"))
    document_summary = st.session_state.document_summary or {}
    assessments = st.session_state.assessments
    has_report_evidence = document_summary_has_evidence(document_summary)
    if not has_report_evidence:
        st.warning(
            "Document Analyzer에서 문서를 먼저 분석해야 제품 정보와 CTD 근거가 포함된 보고서가 생성됩니다."
            if current_language() == "ko"
            else "Analyze a document first in Document Analyzer to include product context and CTD evidence in the report."
        )
    worksheet = build_reviewer_worksheet(st.session_state.application_profile, document_summary, assessments)

    report_payload = {
        "application_snapshot": st.session_state.application_profile,
        "project_name": st.session_state.get("project_name", ""),
        "project_documents": st.session_state.get("project_inventory", []),
        "project_document_summaries": st.session_state.get("document_summaries", []),
        "product_context": document_summary.get("product_context", {}),
        "document_profile": document_summary.get("document_profile", {}),
        "document_narrative": document_summary.get("narrative", "No document analysis has been run."),
        "signal_details": document_summary.get("signal_details", {}),
        "evidence_blocks": document_summary.get("evidence_blocks", []),
        "specification_table": document_summary.get("specification_table", []),
        "writing_structure": document_summary.get("writing_structure", []),
        "candidate_compounds": document_summary.get("candidate_compounds", []),
        "specifications": document_summary.get("specifications", []),
        "test_methods": document_summary.get("test_methods", []),
        "bioequivalence": document_summary.get("bioequivalence", []),
        "stability": document_summary.get("stability", []),
        "bioequivalence_f2_result": vars(st.session_state.be_result) if "be_result" in st.session_state else {},
        "bioequivalence_profile_summary": (
            st.session_state.be_profile_summary.to_dict("records")
            if isinstance(st.session_state.get("be_profile_summary"), pd.DataFrame)
            else []
        ),
        "regulatory_source_crosswalk": document_summary.get("regulatory_source_crosswalk", []),
        "regulatory_source_matches": document_summary.get("regulatory_source_matches", []),
        "screening_results": assessment_table(assessments).to_dict("records") if assessments else [],
        "genotoxicity_tool_result": (
            st.session_state.genotoxicity_tool_result.to_dict("records")
            if isinstance(st.session_state.get("genotoxicity_tool_result"), pd.DataFrame)
            else []
        ),
        "qsar_validation_result": (
            st.session_state.qsar_validation_result.to_dict("records")
            if isinstance(st.session_state.get("qsar_validation_result"), pd.DataFrame)
            else []
        ),
        "qsar_reference_sources": (
            st.session_state.qsar_reference_sources.to_dict("records")
            if isinstance(st.session_state.get("qsar_reference_sources"), pd.DataFrame)
            else []
        ),
        "regulatory_narrative": "\n\n".join(build_regulatory_narrative(item) for item in assessments)
        if assessments
        else "No molecular screening results are available.",
        "fda_style_reviewer_worksheet": worksheet_tables_for_export(worksheet),
    }

    st.json(report_payload, expanded=False)

    pdf_bytes = create_pdf_report(report_payload, language=current_language())
    encoded = base64.b64encode(pdf_bytes).decode("utf-8")
    st.download_button(
        t("Download PDF Report"),
        data=pdf_bytes,
        file_name="ToxiGuard_Prototype_1_Report.pdf",
        mime="application/pdf",
        type="primary",
        disabled=not has_report_evidence and not assessments,
    )
    st.caption(f"{t('pdf_payload')} ({len(encoded)} base64 characters).")
