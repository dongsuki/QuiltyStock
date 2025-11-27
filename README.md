# QuiltyStock - 한국 주식 퀄리티 분석 시스템

[![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-blue)](https://github.com/dongsuki/QuiltyStock/actions)
[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://www.python.org/)

매일 자동으로 한국 주식시장(KOSPI 500 + KOSDAQ 200)의 퀄리티 분석을 수행하고 구글 시트에 업로드하는 시스템입니다.

---

## 📊 **주요 기능**

### 1. **21개 퀄리티 지표 분석**
- **수익성** (5개): ROE, ROA, ROIC, 영업이익률, 매출총이익률
- **안정성** (5개): 매출/영업이익/순이익/EPS/배당 안정성
- **자본구조** (4개): 부채비율, 이자보상배율, 유동비율, 자본비율
- **개선** (4개): ROE/ROA/영업이익률/매출총이익률 개선
- **회계품질** (3개): 발생액, 순영업자산, 이익평탄화

### 2. **TTM(Trailing Twelve Months) 기반**
- 최근 12개월 실적 기반 정확한 분석
- 계절성 및 일시적 요인 제거
- 법인세 25% 적용

### 3. **자동화**
- **매일 오전 9시** GitHub Actions로 자동 실행
- 구글 시트에 자동 업로드 (날짜별 탭 생성)
- 컴퓨터 꺼져 있어도 작동

---

## 🚀 **빠른 시작**

### **1. 리포지토리 Clone**
```bash
git clone https://github.com/dongsuki/QuiltyStock.git
cd QuiltyStock
```

### **2. 패키지 설치**
```bash
pip install -r requirements.txt
```

### **3. 로컬 실행 (테스트)**
```bash
python quality_analysis_ttm.py
```

---

## 🔧 **자동화 설정 (GitHub Actions)**

상세한 설정 방법은 [`SETUP_GUIDE.md`](SETUP_GUIDE.md)를 참조하세요.

### **간단 요약**

1. **Google Cloud Console** 설정
   - 프로젝트 생성
   - Google Sheets API 활성화
   - 서비스 계정 생성 및 JSON 키 다운로드

2. **구글 시트** 생성
   - 새 스프레드시트 생성
   - 시트 ID 복사
   - 서비스 계정에 편집 권한 부여

3. **GitHub Secrets** 설정
   - `GOOGLE_SHEETS_CREDENTIALS`: JSON 파일 전체 내용
   - `GOOGLE_SHEET_ID`: 구글 시트 ID

4. **완료!**
   - 매일 오전 9시 자동 실행
   - 구글 시트에 결과 업로드

---

## 📁 **파일 구조**

```
QuiltyStock/
├── .github/
│   └── workflows/
│       └── daily_analysis.yml          # GitHub Actions 워크플로우
├── quality_analysis_ttm.py             # 메인 분석 스크립트
├── upload_to_sheets.py                 # 구글 시트 업로드
├── generate_final_table.py             # 결과 테이블 생성
├── screen_strategies.py                # 투자 전략 스크리닝
├── explain_apr_ttm.py                  # 개별 종목 상세 분석
├── requirements.txt                    # Python 패키지
├── .gitignore                          # Git 제외 파일
├── SETUP_GUIDE.md                      # 상세 설정 가이드
└── README.md                           # 이 파일
```

---

## 📈 **구글 시트 컬럼 구성**

### **기본 정보 (4개)**
- 순위, 종목코드, 종목명, 종합점수

### **카테고리 점수 (5개)**
- 수익성점수, 안정성점수, 자본구조점수, 개선점수, 회계품질점수

### **상세 지표 (21개)**
- 모든 원본 퀄리티 지표 포함
- 한글 컬럼명으로 가독성 향상

---

## 🎯 **활용 방법**

### **1. 퀄리티 스크리닝**
- 구글 시트에서 `종합점수` 기준 정렬
- 상위 50~100개 종목 추출
- 산업별, 시가총액별 분석

### **2. 투자 전략 적용**
```bash
python screen_strategies.py
```
- **Compounders**: 고수익성 + 고안정성
- **Turnaround**: 개선 중인 종목
- **Hidden Gems**: 저평가 퀄리티 종목

### **3. 개별 종목 분석**
```python
python explain_apr_ttm.py  # 에이피알 예시
```

---

## 📊 **점수 계산 방식**

### **Z-Score 표준화**
- 각 지표를 평균 0, 표준편차 1로 정규화
- 상대적 순위로 평가

### **카테고리별 점수**
- 수익성: 30%
- 안정성: 25%
- 자본구조: 20%
- 개선: 15%
- 회계품질: 10%

### **종합 점수**
- 가중 평균 후 백분위 환산 (0~100)
- 100점 = 전체 1위

---

## ⚠️ **주의사항**

### **데이터 제약**
- 우선주, 최근 상장사 등 일부 종목 제외
- 바이오텍 등 개발 단계 기업은 평가 부적합
- 금융주는 별도 분석 필요

### **분석 한계**
- 퀄리티 스크리닝은 1차 필터
- 최종 투자 판단은 추가 분석 필요
- 성장률은 분기 YoY (완전 TTM 아님)

---

## 🔄 **업데이트 주기**

- **매일 오전 9시**: 자동 분석 실행
- **보관 기간**: GitHub Actions 결과 30일
- **구글 시트**: 영구 보관 (날짜별 탭)

---

## 📝 **라이선스**

MIT License

---

## 👤 **개발자**

- GitHub: [@dongsuki](https://github.com/dongsuki)
- 문의: Issues 탭 활용

---

## 📚 **참고 자료**

- [FnGuide](http://comp.fnguide.com)
- [FinanceDataReader](https://github.com/FinanceData/FinanceDataReader)
- [Google Sheets API](https://developers.google.com/sheets/api)

---

**⭐ 이 프로젝트가 유용하다면 Star를 눌러주세요!**
