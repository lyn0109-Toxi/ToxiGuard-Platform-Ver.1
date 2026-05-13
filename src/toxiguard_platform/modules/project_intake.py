"""Project-level document intake helpers."""

from __future__ import annotations

import re
from typing import Any


def normalize_document_record(
    name: str,
    content_type: str | None,
    text: str,
    pages: list[dict] | None = None,
    bytes_received: int = 0,
    warnings: list[str] | None = None,
    source: str = "upload",
) -> dict:
    """Return a consistent document record for uploaded or pasted material."""
    clean_name = _clean_document_name(name)
    normalized_pages = []
    for index, page in enumerate(pages or [{"page": 1, "text": text}], start=1):
        normalized_pages.append(
            {
                "document": clean_name,
                "page": page.get("page", index),
                "text": page.get("text", ""),
            }
        )

    return {
        "name": clean_name,
        "source": source,
        "content_type": content_type or "text/plain",
        "text": text or "",
        "pages": normalized_pages,
        "bytes_received": bytes_received,
        "warnings": warnings or [],
        "characters": len(text or ""),
    }


def manual_document_record(text: str, name: str = "Manual CTD Text") -> dict:
    """Build a normalized document record from pasted text."""
    clean_text = text or ""
    return normalize_document_record(
        name=name,
        content_type="text/plain",
        text=clean_text,
        pages=[{"page": 1, "text": clean_text}],
        bytes_received=len(clean_text.encode("utf-8")),
        warnings=[],
        source="manual",
    )


def combine_project_documents(project_name: str, documents: list[dict]) -> dict:
    """Combine multiple document records into one reviewable project dossier."""
    clean_project_name = (project_name or "ToxiGuard Project").strip()
    combined_parts: list[str] = []
    project_pages: list[dict] = []
    inventory: list[dict[str, Any]] = []
    global_page = 1

    for doc_index, document in enumerate(documents, start=1):
        name = _clean_document_name(document.get("name") or f"Document {doc_index}")
        pages = document.get("pages") or [{"document": name, "page": 1, "text": document.get("text", "")}]
        for page in pages:
            source_page = page.get("page", len(project_pages) + 1)
            page_text = page.get("text", "")
            combined_parts.append(
                f"\n--- PAGE {global_page} ---\n"
                f"[Project: {clean_project_name} | Document: {name} | Source page: {source_page}]\n"
                f"{page_text}"
            )
            project_pages.append(
                {
                    "project_page": global_page,
                    "document": name,
                    "page": source_page,
                    "text": page_text,
                }
            )
            global_page += 1

        inventory.append(
            {
                "Document": name,
                "Source": document.get("source", "upload"),
                "Type": document.get("content_type", "unknown"),
                "Pages": len(pages),
                "Characters": document.get("characters", len(document.get("text", ""))),
                "Bytes": document.get("bytes_received", 0),
                "Warnings": len(document.get("warnings") or []),
            }
        )

    return {
        "project_name": clean_project_name,
        "documents": documents,
        "document_count": len(documents),
        "combined_text": "\n".join(combined_parts).strip(),
        "pages": project_pages,
        "inventory": inventory,
        "warnings": [warning for document in documents for warning in document.get("warnings", [])],
    }


def document_signal_overview(document: dict, summary: dict) -> dict:
    """Summarize one document's extracted signal counts."""
    details = summary.get("signal_details") or {}
    return {
        "Document": document.get("name", "Document"),
        "Pages": len(document.get("pages") or []),
        "Specifications": len(details.get("specifications") or []),
        "Test Methods": len(details.get("test_methods") or []),
        "Bioequivalence": len(details.get("bioequivalence") or []),
        "Stability": len(details.get("stability") or []),
        "Compounds": len(details.get("compounds") or []),
        "Characters": document.get("characters", len(document.get("text", ""))),
    }


def _clean_document_name(name: str) -> str:
    value = re.sub(r"\s+", " ", name or "Document").strip()
    return value[:140] or "Document"
