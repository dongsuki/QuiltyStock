# GitHub Actions 자동 업로드 설정 가이드

매일 자동으로 퀄리티 분석을 실행하고 구글 시트에 업로드하는 시스템입니다.

---

## 📋 **설정 순서**

### **1단계: Google Cloud 설정** (10분)

#### 1.1 Google Cloud Console 접속
- https://console.cloud.google.com
- 프로젝트 생성: "Stock Analysis"

#### 1.2 Google Sheets API 활성화
1. 좌측 메뉴 → API 및 서비스 → 라이브러리
2. "Google Sheets API" 검색
3. **사용 설정** 클릭

#### 1.3 서비스 계정 생성 (GitHub Actions용)
1. 좌측 메뉴 → API 및 서비스 → **사용자 인증 정보**
2. **+ 사용자 인증 정보 만들기** → **서비스 계정**
3. 이름: `github-actions` 입력 → **만들기**
4. 역할: 선택 안 함 (건너뛰기)
5. **완료**

#### 1.4 서비스 계정 키 다운로드
1. 생성된 서비스 계정 클릭
2. **키** 탭 → **키 추가** → **새 키 만들기**
3. 유형: **JSON** 선택 → **만들기**
4. JSON 파일이 자동 다운로드됨 (파일명 예: `stock-analysis-xxxxx.json`)

**⚠️ 중요**: 이 JSON 파일은 절대 GitHub에 올리지 마세요!

---

### **2단계: 구글 시트 생성 및 권한 설정**

#### 2.1 구글 시트 생성
1. https://sheets.google.com
2. **새 스프레드시트** 생성
3. 이름: "Stock Quality Analysis" (원하는 이름)

#### 2.2 시트 ID 복사
URL에서 ID 부분 복사:
```
https://docs.google.com/spreadsheets/d/[이 부분이 시트 ID]/edit
```

예: `1abcDEF123xyz456ABC789`

#### 2.3 서비스 계정에 권한 부여
1. 구글 시트 우측 상단 **공유** 클릭
2. 다운로드한 JSON 파일 열기 → `client_email` 값 복사
   - 예: `github-actions@stock-analysis-xxx.iam.gserviceaccount.com`
3. **사용자 추가** 란에 붙여넣기
4. 권한: **편집자**
5. **전송** (이메일 알림 체크 해제 가능)

---

### **3단계: GitHub 설정**

#### 3.1 GitHub 리포지토리 생성
1. https://github.com/new
2. 리포지토리 이름: `stock-quality-analysis` (원하는 이름)
3. **Private** 선택 (중요!)
4. **Create repository**

#### 3.2 GitHub Secrets 설정
1. 리포지토리 페이지 → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭

**Secret 1: GOOGLE_SHEETS_CREDENTIALS**
- Name: `GOOGLE_SHEETS_CREDENTIALS`
- Value: 다운로드한 JSON 파일의 **전체 내용** 복사 & 붙여넣기
  - 메모장으로 JSON 파일 열기 → 전체 선택 → 복사
  - `{` 부터 `}` 까지 전부 포함

**Secret 2: GOOGLE_SHEET_ID**
- Name: `GOOGLE_SHEET_ID`
- Value: **2.2**에서 복사한 시트 ID
  - 예: `1abcDEF123xyz456ABC789`

---

### **4단계: GitHub에 코드 업로드**

PowerShell 또는 CMD에서:

```bash
cd c:\Users\User\고니

# Git 초기화 (처음만)
git init

# GitHub 리포지토리 연결 (본인 계정명으로 수정)
git remote add origin https://github.com/[본인계정명]/stock-quality-analysis.git

# 파일 추가
git add .

# 커밋
git commit -m "Initial commit: Stock quality analysis automation"

# GitHub에 업로드
git push -u origin main
```

---

### **5단계: GitHub Actions 실행 테스트**

#### 5.1 수동 실행
1. GitHub 리포지토리 페이지 → **Actions** 탭
2. 좌측: **Daily Stock Quality Analysis** 클릭
3. 우측: **Run workflow** → **Run workflow**

#### 5.2 실행 확인
- 약 5~10분 소요
- 진행 상황 실시간 확인 가능
- ✅ 초록색 체크 = 성공
- ❌ 빨간색 X = 실패 (로그 확인)

#### 5.3 구글 시트 확인
1. 구글 시트로 이동
2. 새 탭 생성됨: `Analysis_2025-11-27` (오늘 날짜)
3. 520개 종목 데이터 확인

---

## ⏰ **자동 실행 스케줄**

- **매일 오전 9시 (KST)** 자동 실행
- GitHub Actions가 자동으로 실행
- 컴퓨터 꺼져 있어도 됨!

---

## 🔧 **트러블슈팅**

### 문제 1: "Permission denied" 오류
**원인**: 서비스 계정이 시트 접근 권한 없음  
**해결**: **2.3** 단계 다시 확인 (공유 설정)

### 문제 2: "GOOGLE_SHEETS_CREDENTIALS not found"
**원인**: GitHub Secret 설정 오류  
**해결**: **3.2** 단계 다시 확인 (JSON 전체 복사 확인)

### 문제 3: Workflow 실행 안 됨
**원인**: `.github/workflows/` 폴더 경로 오류  
**해결**: 파일 경로 확인
```
c:\Users\User\고니\.github\workflows\daily_analysis.yml
```

---

## 📊 **결과 확인**

매일 오전 9시마다:
1. GitHub Actions가 자동 실행
2. 퀄리티 분석 수행 (520개 종목)
3. 구글 시트에 업로드
4. 새 탭 생성: `Analysis_YYYY-MM-DD`

**구글 시트 확인**: https://docs.google.com/spreadsheets/d/[본인 시트 ID]

---

## 💡 **추가 팁**

- **알림 받기**: GitHub Actions 실패 시 이메일 알림 옵션 설정 가능
- **실행 시간 변경**: `.github/workflows/daily_analysis.yml` 파일에서 `cron` 값 수정
- **데이터 보관**: GitHub에 30일간 분석 결과 파일 자동 저장
