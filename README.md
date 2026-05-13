# ToxiGuard-Platform Ver.1

Streamlit-based review workspace for CTD document intelligence, ToxiGuard platform tools, ICH M7/QSAR review, pharmaceutical equivalence, f2/bootstrap dissolution comparison, and CTD-style report generation.

## Run

```bash
cd "/Users/leeyoung-nam/Desktop/ToxiGuard-Platform Ver.1"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

If your Python already has the required packages:

```bash
cd "/Users/leeyoung-nam/Desktop/ToxiGuard-Platform Ver.1"
python3 -m streamlit run streamlit_app.py
```

## Main Structure

- `streamlit_app.py`: Streamlit 실행 진입점
- `app.py`: 기존 실행 방식을 위한 호환 진입점
- `src/toxiguard_platform/app.py`: Streamlit 화면 구성
- `src/toxiguard_platform/modules/`: CTD extraction, product context, regulatory sources, ToxiGuard tools, reporting, worksheet logic
- `assets/`: 로고, 이미지, 리포트용 정적 파일
- `data/`: 샘플 데이터 또는 참조 자료
- `tests/`: 향후 Streamlit/모듈 테스트
- `scripts/validate_prototype.py`: integrated validation suite
- `validation_reports/`: generated validation reports
- `.streamlit/config.toml`: local Streamlit UI/server config

## Current Capabilities

- Multi-document project dossier intake
- Korean/English CTD document analysis
- English report mode with Korean text removed
- Specification/test method matrix
- Pharmaceutical equivalence matrix
- Reference/test dissolution f2 and bootstrap calculation
- Related substances and genotoxicity/QSAR validation matrices
- Stability shelf-life prediction
- FDA-style worksheet and CTD-style PDF report

This application is a decision-support prototype and is not a validated regulatory system.
