"""
Google Sheets 업로드 스크립트 (GitHub Actions용)
매일 자동으로 퀄리티 분석 결과를 구글 시트에 업로드
"""

import os
import json
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd

# Google Sheets API 설정
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_credentials():
    """GitHub Secrets에서 credentials 가져오기"""
    creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if not creds_json:
        raise ValueError("GOOGLE_SHEETS_CREDENTIALS 환경 변수가 설정되지 않았습니다")
    
    creds_dict = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return credentials

def upload_to_sheets(spreadsheet_id, df, sheet_name='Analysis'):
    """
    데이터프레임을 구글 시트에 업로드 (덮어쓰기)
    
    Args:
        spreadsheet_id: 구글 시트 ID
        df: 업로드할 데이터프레임
        sheet_name: 시트 탭 이름 (기본: 'Analysis')
    """
    credentials = get_credentials()
    service = build('sheets', 'v4', credentials=credentials)
    
    # 1. 기존 시트가 있는지 확인
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', [])
        
        # 첫 번째 시트 사용 (또는 'Analysis' 시트 찾기)
        target_sheet = None
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                target_sheet = sheet
                break
        
        if not target_sheet:
            # 'Analysis' 시트가 없으면 첫 번째 시트 사용
            target_sheet = sheets[0]
            sheet_name = target_sheet['properties']['title']
            print(f"✓ 기존 시트 사용: {sheet_name}")
        else:
            print(f"✓ '{sheet_name}' 시트 발견")
            
    except Exception as e:
        print(f"⚠ 시트 확인 오류: {e}")
        sheet_name = 'Sheet1'  # Fallback
    
    # 2. 기존 데이터 전체 삭제 (A1부터 모든 내용)
    try:
        clear_request = service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1:ZZ100000",  # 충분히 큰 범위
            body={}
        ).execute()
        print(f"✓ 기존 데이터 삭제 완료")
    except Exception as e:
        print(f"⚠ 데이터 삭제 중 오류 (무시 가능): {e}")
    
    # 3. 새 데이터 업로드
    # 헤더 + 데이터
    values = [df.columns.tolist()] + df.values.tolist()
    
    body = {
        'values': values
    }
    
    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption='RAW',
        body=body
    ).execute()
    
    print(f"✓ {result.get('updatedCells')} 개 셀 업데이트 완료")
    return result

def calculate_scores(df):
    """
    점수 계산 함수 (generate_final_table.py 로직 재사용)
    """
    import numpy as np
    
    def z_score(series):
        return (series - series.mean()) / (series.std() + 1e-10)
    
    # 1. 수익성 점수
    profitability_cols = ['ROE', 'ROA', 'ROIC', 'Operating_Margin', 'Gross_Margin']
    profitability_scores = []
    for col in profitability_cols:
        if col in df.columns:
            df[f'Score_{col}'] = z_score(df[col].fillna(df[col].median()))
            profitability_scores.append(f'Score_{col}')
    df['Profitability_Score'] = df[profitability_scores].mean(axis=1) if profitability_scores else 0
    
    # 2. 안정성 점수
    stability_cols = ['Revenue_Stability', 'OpProfit_Stability', 'NetIncome_Stability', 
                      'EPS_Stability', 'Dividend_Stability']
    stability_scores = []
    for col in stability_cols:
        if col in df.columns:
            df[f'Score_{col}'] = z_score(df[col].fillna(0))
            stability_scores.append(f'Score_{col}')
    df['Stability_Score'] = df[stability_scores].mean(axis=1) if stability_scores else 0
    
    # 3. 자본구조 점수
    df['Score_Debt_Ratio'] = z_score(df['Debt_Ratio'].fillna(100))
    capital_scores = ['Score_Debt_Ratio']
    for col in ['Interest_Coverage', 'Current_Ratio', 'Equity_Ratio']:
        if col in df.columns:
            df[f'Score_{col}'] = z_score(df[col].fillna(df[col].median()))
            capital_scores.append(f'Score_{col}')
    df['Capital_Score'] = df[capital_scores].mean(axis=1)
    
    # 4. 개선 점수
    improvement_cols = ['ROE_Improvement', 'ROA_Improvement', 
                        'Operating_Margin_Improvement', 'Gross_Margin_Improvement']
    improvement_scores = []
    for col in improvement_cols:
        if col in df.columns:
            df[f'Score_{col}'] = z_score(df[col].fillna(0))
            improvement_scores.append(f'Score_{col}')
    df['Improvement_Score'] = df[improvement_scores].mean(axis=1) if improvement_scores else 0
    
    # 5. 회계품질 점수
    accounting_cols = ['Accruals', 'Net_Operating_Assets', 'Earnings_Smoothness']
    accounting_scores = []
    for col in accounting_cols:
        if col in df.columns:
            df[f'Score_{col}'] = z_score(df[col].fillna(0)) * -1
            accounting_scores.append(f'Score_{col}')
    df['Accounting_Score'] = df[accounting_scores].mean(axis=1) if accounting_scores else 0
    
    # 종합 점수 (가중 평균)
    df['Quality_Score_Total'] = (
        df['Profitability_Score'] * 0.30 +
        df['Stability_Score'] * 0.25 +
        df['Capital_Score'] * 0.20 +
        df['Improvement_Score'] * 0.15 +
        df['Accounting_Score'] * 0.10
    )
    
    # 백분위로 환산 (0~100)
    df['Quality_Score'] = df['Quality_Score_Total'].rank(pct=True) * 100
    
    return df

def main():
    """메인 실행 함수"""
    import FinanceDataReader as fdr
    
    print("=" * 60)
    print("Google Sheets 업로드 시작")
    print("=" * 60)
    
    # 환경 변수 확인
    spreadsheet_id = os.environ.get('GOOGLE_SHEET_ID')
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEET_ID 환경 변수가 설정되지 않았습니다")
    
    # CSV 파일 읽기
    csv_path = 'quality_analysis_all.csv'
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"{csv_path} 파일을 찾을 수 없습니다")
    
    df = pd.read_csv(csv_path)
    print(f"✓ 원본 데이터 로드: {len(df)} 개 종목")
    
    # 점수 계산
    df = calculate_scores(df)
    print(f"✓ 점수 계산 완료")
    
    # 종목명 추가
    df_krx = fdr.StockListing('KRX')
    df = df.merge(df_krx[['Code', 'Name']], on='Code', how='left')
    print(f"✓ 종목명 추가 완료")
    
    # 순위 추가
    df['Rank'] = df['Quality_Score'].rank(ascending=False, method='min').astype(int)
    df = df.sort_values('Rank')
    print(f"✓ 순위 정렬 완료")
    
    # 업로드용 컬럼 선택 및 순서 정리 (모든 지표 포함)
    upload_cols = [
        # 기본 정보 & 순위
        'Rank', 'Code', 'Name', 'Quality_Score',
        # 카테고리별 점수
        'Profitability_Score', 'Stability_Score', 'Capital_Score', 
        'Improvement_Score', 'Accounting_Score',
        # 수익성 지표 (5개)
        'ROE', 'ROA', 'ROIC', 'Operating_Margin', 'Gross_Margin',
        # 안정성 지표 (5개) - 전체
        'Revenue_Stability', 'OpProfit_Stability', 'NetIncome_Stability',
        'EPS_Stability', 'Dividend_Stability',
        # 자본구조 지표 (4개) - 전체
        'Debt_Ratio', 'Interest_Coverage', 'Current_Ratio', 'Equity_Ratio',
        # 개선 지표 (4개) - 전체
        'ROE_Improvement', 'ROA_Improvement', 
        'Operating_Margin_Improvement', 'Gross_Margin_Improvement',
        # 회계품질 지표 (3개) - 전체
        'Accruals', 'Net_Operating_Assets', 'Earnings_Smoothness'
    ]
    
    # 존재하는 컬럼만 선택
    upload_cols = [col for col in upload_cols if col in df.columns]
    df_upload = df[upload_cols].copy()
    
    # 컬럼명을 한글로 변경
    korean_names = {
        'Rank': '순위',
        'Code': '종목코드',
        'Name': '종목명',
        'Quality_Score': '종합점수',
        'Profitability_Score': '수익성점수',
        'Stability_Score': '안정성점수',
        'Capital_Score': '자본구조점수',
        'Improvement_Score': '개선점수',
        'Accounting_Score': '회계품질점수',
        'ROE': 'ROE',
        'ROA': 'ROA',
        'ROIC': 'ROIC',
        'Operating_Margin': '영업이익률',
        'Gross_Margin': '매출총이익률',
        'Revenue_Stability': '매출안정성',
        'OpProfit_Stability': '영업이익안정성',
        'NetIncome_Stability': '순이익안정성',
        'EPS_Stability': 'EPS안정성',
        'Dividend_Stability': '배당안정성',
        'Debt_Ratio': '부채비율',
        'Interest_Coverage': '이자보상배율',
        'Current_Ratio': '유동비율',
        'Equity_Ratio': '자본비율',
        'ROE_Improvement': 'ROE개선',
        'ROA_Improvement': 'ROA개선',
        'Operating_Margin_Improvement': '영업이익률개선',
        'Gross_Margin_Improvement': '매출총이익률개선',
        'Accruals': '발생액',
        'Net_Operating_Assets': '순영업자산',
        'Earnings_Smoothness': '이익평탄화'
    }
    df_upload.rename(columns=korean_names, inplace=True)
    
    # 숫자 포맷 정리 (소수점 2자리)
    for col in df_upload.columns:
        if col not in ['Rank', 'Code', 'Name'] and df_upload[col].dtype in ['float64', 'float32']:
            df_upload[col] = df_upload[col].round(2)
    
    print(f"✓ 최종 컬럼 수: {len(upload_cols)}개")
    
    # 고정된 시트 이름 사용 (날짜별 탭 생성하지 않음)
    sheet_name = 'Analysis'
    
    # 업로드 실행
    upload_to_sheets(spreadsheet_id, df_upload, sheet_name)
    
    print("=" * 60)
    print(f"✓ 업로드 완료!")
    print(f"  종목 수: {len(df_upload)}개")
    print(f"  시트명: {sheet_name}")
    print(f"  업데이트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print("=" * 60)

if __name__ == "__main__":
    main()
