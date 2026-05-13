"""RDKit-first mutagenicity screening for ToxiGuard-Platform Ver.1."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


Chem = None
RDKIT_AVAILABLE = False
_RDKIT_IMPORT_ATTEMPTED = False


STRUCTURAL_ALERTS = {
    "Aromatic Amine": {
        "smarts": "[NX3;H2,H1;!$(NC=O)]-c",
        "priority": "High",
        "mechanism": "Potential metabolic activation to electrophilic nitrenium species.",
        "reference": "ICH M7(R2); Ashby-Tennant alert family",
    },
    "Nitro Aromatic": {
        "smarts": "[N+](=O)[O-]-c",
        "priority": "High",
        "mechanism": "Potential reductive activation to reactive hydroxylamine intermediates.",
        "reference": "ICH M7(R2); Kazius structural alert family",
    },
    "Alkyl Halide": {
        "smarts": "[C;!$(C=O)][Cl,Br,I]",
        "priority": "Moderate",
        "mechanism": "Potential direct alkylation concern depending on reactivity and exposure.",
        "reference": "ICH M7(R2); electrophilic alert family",
    },
    "Epoxide or Aziridine": {
        "smarts": "C1[O,N]C1",
        "priority": "Critical",
        "mechanism": "Strained ring electrophile with potential direct DNA alkylation.",
        "reference": "ICH M7(R2); direct-acting mutagen alert family",
    },
    "Azo Group": {
        "smarts": "N=N",
        "priority": "Moderate",
        "mechanism": "Potential cleavage or metabolic activation to aromatic amines.",
        "reference": "ICH M7(R2); azo structural alert family",
    },
}


EXPERIMENTAL_REFERENCES = {
    "c1ccc(N)cc1": {
        "name": "Aniline",
        "result": "POSITIVE",
        "basis": "Representative aromatic amine with known mutagenicity concern under metabolic activation.",
    },
    "c1ccc(cc1)[N+](=O)[O-]": {
        "name": "Nitrobenzene",
        "result": "POSITIVE",
        "basis": "Representative nitro aromatic alert compound.",
    },
    "CC(=O)NC1=CC=C(O)C=C1": {
        "name": "Acetaminophen",
        "result": "NEGATIVE/LOW CONCERN",
        "basis": "Common API example; route-specific impurities still require separate assessment.",
    },
}


@dataclass
class ToxicityAssessment:
    smiles: str
    valid_structure: bool
    alerts: list[dict]
    risk_score: float
    ich_m7_class: str
    conclusion: str
    experimental_reference: dict | None


def assess_smiles(smiles: str) -> ToxicityAssessment:
    """Screen a SMILES string using structural alerts and simple scoring."""
    smiles = smiles.strip()
    if not smiles:
        return ToxicityAssessment(smiles, False, [], 0.0, "Unclassified", "No SMILES was provided.", None)

    if not _load_rdkit():
        alerts = _fallback_alerts(smiles)
        return _build_assessment(smiles, True, alerts, experimental_reference=None, rdkit_mode=False)

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return ToxicityAssessment(
            smiles=smiles,
            valid_structure=False,
            alerts=[],
            risk_score=0.0,
            ich_m7_class="Invalid",
            conclusion="The SMILES string could not be parsed by RDKit.",
            experimental_reference=None,
        )

    alerts = []
    for name, alert in STRUCTURAL_ALERTS.items():
        pattern = Chem.MolFromSmarts(alert["smarts"])
        if pattern is not None and mol.HasSubstructMatch(pattern):
            alerts.append(
                {
                    "name": name,
                    "priority": alert["priority"],
                    "mechanism": alert["mechanism"],
                    "reference": alert["reference"],
                }
            )

    canonical = Chem.MolToSmiles(mol)
    reference = EXPERIMENTAL_REFERENCES.get(smiles) or EXPERIMENTAL_REFERENCES.get(canonical)
    return _build_assessment(canonical, True, alerts, reference, rdkit_mode=True)


def _fallback_alerts(smiles: str) -> list[dict]:
    checks = {
        "Aromatic Amine": bool(re.search(r"Nc|cN|c1ccc\(N\)cc1|c1cc\(N\)ccc1", smiles)),
        "Azo Group": "N=N" in smiles,
        "Nitro Aromatic": "[N+](=O)[O-]" in smiles or "N(=O)" in smiles,
        "Alkyl Halide": any(token in smiles for token in ("Cl", "Br", "I")),
        "Epoxide or Aziridine": "1OC1" in smiles or "1NC1" in smiles,
    }
    return [
        {
            "name": name,
            "priority": STRUCTURAL_ALERTS[name]["priority"],
            "mechanism": STRUCTURAL_ALERTS[name]["mechanism"],
            "reference": STRUCTURAL_ALERTS[name]["reference"],
        }
        for name, found in checks.items()
        if found
    ]


def _load_rdkit() -> bool:
    """Load RDKit only when explicitly enabled so document review never blocks on chemistry imports."""
    global Chem, RDKIT_AVAILABLE, _RDKIT_IMPORT_ATTEMPTED
    if RDKIT_AVAILABLE:
        return True
    if _RDKIT_IMPORT_ATTEMPTED or os.environ.get("TOXIGUARD_ENABLE_RDKIT") != "1":
        return False
    _RDKIT_IMPORT_ATTEMPTED = True
    try:
        from rdkit import Chem as rdkit_chem
    except Exception:
        Chem = None
        RDKIT_AVAILABLE = False
        return False
    Chem = rdkit_chem
    RDKIT_AVAILABLE = True
    return True


def _build_assessment(
    smiles: str,
    valid_structure: bool,
    alerts: list[dict],
    experimental_reference: dict | None,
    rdkit_mode: bool,
) -> ToxicityAssessment:
    priority_scores = {"Critical": 0.95, "High": 0.78, "Moderate": 0.52}
    score = max([priority_scores.get(alert["priority"], 0.35) for alert in alerts], default=0.12)

    if experimental_reference and "NEGATIVE" in experimental_reference["result"]:
        score = min(score, 0.25)
    elif experimental_reference and "POSITIVE" in experimental_reference["result"]:
        score = max(score, 0.82)

    if not alerts and experimental_reference and "NEGATIVE" in experimental_reference["result"]:
        ich_class = "Class 5"
        conclusion = "No structural alert was detected and supportive negative evidence is available."
    elif not alerts:
        ich_class = "Class 5"
        conclusion = "No structural alert was detected by the prototype screening engine."
    elif experimental_reference and "POSITIVE" in experimental_reference["result"]:
        ich_class = "Class 1"
        conclusion = "Known or reference-positive mutagenicity evidence is present."
    else:
        ich_class = "Class 3"
        conclusion = "A structural alert was detected and should be followed by expert review or confirmatory evidence."

    if not rdkit_mode:
        conclusion += " RDKit is unavailable, so this result used fallback string matching."

    return ToxicityAssessment(
        smiles=smiles,
        valid_structure=valid_structure,
        alerts=alerts,
        risk_score=round(score, 3),
        ich_m7_class=ich_class,
        conclusion=conclusion,
        experimental_reference=experimental_reference,
    )


def build_regulatory_narrative(assessment: ToxicityAssessment) -> str:
    """Generate a concise regulatory justification paragraph."""
    if not assessment.valid_structure:
        return "The submitted structure could not be evaluated because the SMILES string is invalid."

    alert_text = ", ".join(alert["name"] for alert in assessment.alerts) or "no structural alerts"
    evidence = ""
    if assessment.experimental_reference:
        evidence = (
            f" A reference entry for {assessment.experimental_reference['name']} indicates "
            f"{assessment.experimental_reference['result']}: {assessment.experimental_reference['basis']}"
        )

    return (
        f"The structure was screened with the ToxiGuard-Platform Ver.1 ICH M7 alert engine. "
        f"The assessment identified {alert_text}. The current prototype classification is "
        f"{assessment.ich_m7_class} with a risk score of {assessment.risk_score:.2f}. "
        f"{assessment.conclusion}{evidence} Final use requires qualified toxicologist review."
    )
