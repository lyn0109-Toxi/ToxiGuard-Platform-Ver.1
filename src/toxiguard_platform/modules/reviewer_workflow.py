from __future__ import annotations

import pandas as pd


def signal_details_dataframe(summary: dict) -> pd.DataFrame:
    rows = []
    for key, details in (summary.get("signal_details") or {}).items():
        for detail in details:
            row = dict(detail)
            row["Signal Key"] = key
            row["Reviewer Category"] = detail.get("Category", "")
            row["Reviewer Status"] = "AI Extracted"
            row["Reviewer Note"] = ""
            rows.append(row)
    return pd.DataFrame(rows)


def apply_reviewer_corrections(summary: dict, edited_df: pd.DataFrame) -> dict:
    category_map = {
        "Specifications": "specifications",
        "Test Methods": "test_methods",
        "Bioequivalence": "bioequivalence",
        "Stability": "stability",
        "Compounds": "compounds",
    }
    corrected = {key: [] for key in category_map.values()}

    for _, row in edited_df.iterrows():
        if str(row.get("Reviewer Status", "")).lower() == "rejected":
            continue
        category_label = str(row.get("Reviewer Category", "")).strip()
        category_key = category_map.get(category_label)
        if not category_key:
            continue
        item = row.to_dict()
        item["Category"] = category_label
        item["Reason"] = str(item.get("Reason", ""))
        if item.get("Reviewer Note"):
            item["Reason"] = f"{item['Reason']} Reviewer note: {item['Reviewer Note']}"
        corrected[category_key].append(item)

    updated = dict(summary)
    updated["signal_details"] = corrected
    updated["specifications"] = [row.get("Evidence", "") for row in corrected["specifications"] if row.get("Evidence")]
    updated["test_methods"] = [row.get("Evidence", "") for row in corrected["test_methods"] if row.get("Evidence")]
    updated["bioequivalence"] = [row.get("Evidence", "") for row in corrected["bioequivalence"] if row.get("Evidence")]
    updated["stability"] = [row.get("Evidence", "") for row in corrected["stability"] if row.get("Evidence")]
    updated["reviewer_corrected"] = True
    return updated
