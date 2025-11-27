import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import requests
import time
import os
from io import StringIO

# ---------------------------------------------------------
# STEP 1. 유니버스 구성 (Main 블록으로 이동)
# ---------------------------------------------------------
financial_keywords = ['은행', '보험', '증권', '금융', '캐피탈', '저축', '신용', 
                      '생명', '화재', '손해', '투자', '자산운용', '리츠', 'SPAC']

# ---------------------------------------------------------
# STEP 2. TTM 기반 21가지 퀄리티 지표 수집
# ---------------------------------------------------------
def get_quality_factors_ttm(code, name):
    """TTM 기반 21가지 퀄리티 디스크립터"""
    try:
        is_financial = any(keyword in name for keyword in financial_keywords)
        firm_code = 'A' + code
        
        # ===== 재무제표 (분기 데이터) =====
        fs_url = f"http://comp.fnguide.com/SVO2/ASP/SVD_Finance.asp?pGB=1&cID=&MenuYn=Y&ReportGB=D&NewMenuID=103&stkGb=701&gicode={firm_code}"
        fs_page = requests.get(fs_url, timeout=10)
        fs_tables = pd.read_html(StringIO(fs_page.text))
        
        # Annual Tables (for Stability) - Index 0
        income_a = fs_tables[0].set_index(fs_tables[0].columns[0]) if len(fs_tables) > 0 else None
        
        # Quarterly Tables
        income_df = fs_tables[1].set_index(fs_tables[1].columns[0]) if len(fs_tables) > 1 else None
        balance_df = fs_tables[3].set_index(fs_tables[3].columns[0]) if len(fs_tables) > 3 else None
        cashflow_df = fs_tables[5].set_index(fs_tables[5].columns[0]) if len(fs_tables) > 5 else None
        
        # ===== 재무비율 (ROIC, 이자보상배율, 성장성) =====
        ratio_url = f"http://comp.fnguide.com/SVO2/ASP/SVD_FinanceRatio.asp?pGB=1&gicode={firm_code}&cID=&MenuYn=Y&ReportGB=&NewMenuID=104&stkGb=701"
        ratio_page = requests.get(ratio_url, timeout=10)
        ratio_tables = pd.read_html(StringIO(ratio_page.text))
        ratio_df = ratio_tables[0].set_index(ratio_tables[0].columns[0]) if len(ratio_tables) > 0 else None
        
        # Helper: Get Ratio Value
        def get_ratio_value(df, row_keywords):
            if df is None: return None
            cols = df.columns
            recent_col = cols[-1] # Assume last column is recent
            for idx in df.index:
                if any(k in str(idx) for k in row_keywords):
                    try:
                        val = float(df.loc[idx, recent_col])
                        return val
                    except:
                        pass
            return None

        # ===== TTM 계산 함수 =====
        def calculate_ttm(df, row_name, num_quarters=4):
            if df is None: return None
            for idx in df.index:
                if row_name in str(idx):
                    values = []
                    for col in df.columns[:num_quarters]:
                        try:
                            val = float(df.loc[idx, col])
                            if not np.isnan(val): values.append(val)
                        except: pass
                    if len(values) >= num_quarters: return sum(values[:num_quarters])
            return None
        
        def get_quarterly_values(df, row_name, max_quarters=8):
            if df is None: return []
            for idx in df.index:
                if row_name in str(idx):
                    values = []
                    for col in df.columns[:max_quarters]:
                        try:
                            val = float(df.loc[idx, col])
                            if not np.isnan(val): values.append(val)
                        except: pass
                    return values
            return []

        # ===== 1. 수익성 (5개) - TTM 기반 =====
        profitability = {}
        ttm_revenue = calculate_ttm(income_df, '매출액')
        ttm_op_profit = calculate_ttm(income_df, '영업이익')
        ttm_net_income = calculate_ttm(income_df, '당기순이익')
        
        # Balance Sheet Items
        recent_col = None
        if balance_df is not None:
            date_cols = [c for c in balance_df.columns if '/' in str(c) and c[0].isdigit()]
            if date_cols: recent_col = date_cols[-1]
            
        def get_bs_value(keywords):
            if balance_df is None or not recent_col: return None
            for idx in balance_df.index:
                if any(k in str(idx) or str(idx) == k for k in keywords):
                    try: return float(balance_df.loc[idx, recent_col])
                    except: pass
            return None

        total_assets = get_bs_value(['자산총계', '자산'])
        total_equity = get_bs_value(['자본총계', '자본'])
        total_debt = get_bs_value(['부채총계', '부채'])
        
        # ROE, ROA
        profitability['ROE'] = (ttm_net_income / total_equity * 100) if ttm_net_income and total_equity else None
        profitability['ROA'] = (ttm_net_income / total_assets * 100) if ttm_net_income and total_assets else None
        
        # ROIC (Manual TTM Calculation for Consistency)
        # NOPAT approx = Operating Profit * (1 - Tax Rate 25%)
        # IC approx = Total Equity + Total Debt
        if ttm_op_profit and total_equity and total_debt:
            nopat = ttm_op_profit * 0.75
            invested_capital = total_equity + total_debt
            profitability['ROIC'] = (nopat / invested_capital * 100)
        else:
            profitability['ROIC'] = get_ratio_value(ratio_df, ['ROIC']) # Fallback
        
        # Margins
        profitability['Operating_Margin'] = (ttm_op_profit / ttm_revenue * 100) if ttm_op_profit and ttm_revenue else None
        ttm_cogs = calculate_ttm(income_df, '매출원가')
        profitability['Gross_Margin'] = ((ttm_revenue - ttm_cogs) / ttm_revenue * 100) if ttm_revenue and ttm_cogs else None
        
        # ===== 2. 이익안정성 (5개) - 연간 데이터 기준 =====
        earnings_stability = {}
        
        def calc_stability(df, row_keywords):
            if df is None: return 0
            cols = df.columns[-4:] if len(df.columns) >= 4 else df.columns
            vals = []
            for idx in df.index:
                if any(k in str(idx) for k in row_keywords):
                    for col in cols:
                        try: vals.append(float(df.loc[idx, col]))
                        except: pass
                    break
            if len(vals) >= 3:
                growth_rates = [(vals[i]-vals[i-1])/abs(vals[i-1]) for i in range(1, len(vals)) if vals[i-1]!=0]
                if len(growth_rates) >= 2:
                    return 1 / (np.std(growth_rates) + 0.1)
            return 0

        earnings_stability['Revenue_Stability'] = calc_stability(income_a, ['매출액'])
        earnings_stability['OpProfit_Stability'] = calc_stability(income_a, ['영업이익'])
        earnings_stability['NetIncome_Stability'] = calc_stability(income_a, ['당기순이익'])
        earnings_stability['EPS_Stability'] = calc_stability(income_a, ['EPS', '주당순이익'])
        earnings_stability['Dividend_Stability'] = calc_stability(ratio_df, ['주당배당금', 'DPS'])
        
        # ===== 3. 자본구조 (4개) =====
        capital_structure = {}
        capital_structure['Debt_Ratio'] = (total_debt / total_equity * 100) if total_debt and total_equity else 100
        
        # Interest Coverage (Manual TTM Calculation)
        # Try to fetch Interest Expense from Income Statement
        ttm_interest_expense = calculate_ttm(income_df, '이자비용')
        if not ttm_interest_expense:
             ttm_interest_expense = calculate_ttm(income_df, '금융원가') # Fallback
             
        if ttm_op_profit and ttm_interest_expense and ttm_interest_expense > 0:
            capital_structure['Interest_Coverage'] = ttm_op_profit / ttm_interest_expense
        else:
            capital_structure['Interest_Coverage'] = get_ratio_value(ratio_df, ['이자보상배율']) # Fallback
        
        current_assets = get_bs_value(['유동자산'])
        current_liabilities = get_bs_value(['유동부채'])
        capital_structure['Current_Ratio'] = (current_assets / current_liabilities * 100) if current_assets and current_liabilities else None
        capital_structure['Equity_Ratio'] = (total_equity / total_assets * 100) if total_equity and total_assets else None
        
        # ===== 4. 수익성 개선 (4개) - 분기 YoY (Ratio Page Proxy) =====
        # Note: TTM YoY requires 8 quarters, but FnGuide only provides 4-5 quarters
        # Using quarterly YoY from Ratio page as proxy
        profitability_growth = {}
        profitability_growth['ROE_Improvement'] = get_ratio_value(ratio_df, ['EPS증가율']) or 0  # Proxy using EPS Growth
        profitability_growth['ROA_Improvement'] = 0  # Not available directly
        profitability_growth['Operating_Margin_Improvement'] = get_ratio_value(ratio_df, ['영업이익증가율']) or 0  # Proxy using Op Profit Growth
        profitability_growth['Gross_Margin_Improvement'] = get_ratio_value(ratio_df, ['매출액증가율']) or 0  # Proxy using Revenue Growth
        
        # ===== 5. 회계품질 (3개) - TTM 기반 =====
        accounting_quality = {}
        ttm_operating_cf = calculate_ttm(cashflow_df, '영업활동')
        accounting_quality['Accruals'] = abs(ttm_net_income - ttm_operating_cf) / (abs(ttm_net_income) + 1) if ttm_net_income and ttm_operating_cf else 0
        
        # NOA
        cash_equiv = get_bs_value(['현금및현금성자산']) or 0
        if total_assets and total_equity and total_debt:
            # NOA = (TotalAssets - Cash) - (TotalLiab - TotalDebt)
            # TotalLiab = TotalAssets - TotalEquity
            total_liab = total_assets - total_equity
            op_assets = total_assets - cash_equiv
            op_liab = total_liab - total_debt
            accounting_quality['Net_Operating_Assets'] = (op_assets - op_liab) / total_assets
        else:
            accounting_quality['Net_Operating_Assets'] = 0
            
        # Earnings Smoothness
        ni_vals = []
        ocf_vals = []
        if income_a is not None:
            for idx in income_a.index:
                if '당기순이익' in str(idx):
                    ni_vals = [float(income_a.loc[idx, c]) for c in income_a.columns[-4:]]
                    break
        if len(fs_tables) > 4: # Annual Cashflow
            cashflow_a = fs_tables[4].set_index(fs_tables[4].columns[0])
            for idx in cashflow_a.index:
                if '영업활동' in str(idx):
                    ocf_vals = [float(cashflow_a.loc[idx, c]) for c in cashflow_a.columns[-4:]]
                    break
        
        if len(ni_vals) >= 3 and len(ocf_vals) >= 3:
            std_ni = np.std(ni_vals)
            std_ocf = np.std(ocf_vals)
            accounting_quality['Earnings_Smoothness'] = std_ni / std_ocf if std_ocf != 0 else 0
        else:
            accounting_quality['Earnings_Smoothness'] = 0
        
        result = {
            'Code': code,
            'Is_Financial': is_financial,
            **profitability,
            **earnings_stability,
            **capital_structure,
            **profitability_growth,
            **accounting_quality
        }
        return result

    except Exception as e:
        return None

# ---------------------------------------------------------
# STEP 3. 데이터 수집
# ---------------------------------------------------------
if __name__ == "__main__":
    print("1. 유니버스 구성 중... (KOSPI 500위 + KOSDAQ 200위)")
    df_kospi = fdr.StockListing('KOSPI')
    df_kosdaq = fdr.StockListing('KOSDAQ')
    
    df_kospi_top = df_kospi.sort_values('Marcap', ascending=False).head(500)
    df_kosdaq_top = df_kosdaq.sort_values('Marcap', ascending=False).head(200)
    
    df_universe = pd.concat([df_kospi_top, df_kosdaq_top]).reset_index(drop=True)
    
    target_codes = df_universe['Code'].tolist()
    print(f"-> 최종 분석 대상: {len(target_codes)}개 (KOSPI 500 + KOSDAQ 200)")

    print("2. TTM 기반 21가지 퀄리티 지표 수집 시작...")
    data_list = []
    success_count = 0
    fail_count = 0
    
    output_file = "quality_analysis_all.csv"
    
    # 기존 파일이 있으면 로드하여 중복 방지 (Resuming 기능)
    try:
        existing_df = pd.read_csv(output_file)
        processed_codes = set(existing_df['Code'].astype(str).str.zfill(6).tolist())
        print(f"-> 기존 데이터 {len(processed_codes)}개 로드됨. 이어서 작업을 시작합니다.")
    except FileNotFoundError:
        processed_codes = set()
        print(f"-> 새로운 분석 시작: {output_file}")

    for idx, code in enumerate(target_codes):
        if code in processed_codes:
            continue
            
        name = df_universe.loc[idx, 'Name']
        print(f"[{idx+1}/{len(target_codes)}] {name} ({code})", end=" ")
        
        result = get_quality_factors_ttm(code, name)
        if result:
            data_list.append(result)
            success_count += 1
            print("✓")
        else:
            fail_count += 1
            print("✗")
        
        # 10개마다 또는 마지막에 저장
        if len(data_list) >= 10 or idx == len(target_codes) - 1:
            if data_list:
                temp_df = pd.DataFrame(data_list)
                
                # 점수 계산 로직 (임시 점수 계산 - 전체 데이터가 아니므로 완벽하진 않지만 대략적인 확인용)
                # 최종 점수는 모든 데이터 수집 후 다시 계산해야 정확함
                # 여기서는 Raw Data만 저장하고, 최종 분석 시 점수 재계산 권장
                
                # CSV에 Append
                if not os.path.exists(output_file):
                    temp_df.to_csv(output_file, index=False, encoding='utf-8-sig', mode='w')
                else:
                    temp_df.to_csv(output_file, index=False, encoding='utf-8-sig', mode='a', header=False)
                
                data_list = [] # 리스트 초기화
        
        time.sleep(0.2) # 속도 약간 상향 (0.5 -> 0.2)
    
    print(f"\n수집 완료. 최종 점수 산출 및 정렬을 진행합니다...")
    
    # ---------------------------------------------------------
    # STEP 4. 신영증권 방식 퀄리티 점수 계산 (전체 데이터 로드 후 일괄 처리)
    # ---------------------------------------------------------
    if os.path.exists(output_file):
        df_final = pd.read_csv(output_file)
        # 중복 제거 (혹시 모를 중복 방지)
        df_final = df_final.drop_duplicates(subset=['Code'])
        
        # 유니버스 정보 병합 (Name 등 확인)
        # df_final에는 이미 Name이 있지만, 확실히 하기 위해
        # df_final = pd.merge(df_final, df_universe[['Code', 'Name']], on='Code', how='left') 
        
        def z_score(x): 
            if x.std() == 0:
                return pd.Series([0] * len(x), index=x.index)
            return (x - x.mean()) / x.std()
        
        # 1. 수익성 점수
        profitability_cols = ['ROE', 'ROA', 'ROIC', 'Operating_Margin', 'Gross_Margin']
        profitability_scores = []
        for col in profitability_cols:
            if col in df_final.columns:
                df_final[f'Score_{col}'] = z_score(df_final[col].fillna(df_final[col].median()))
                profitability_scores.append(f'Score_{col}')
        
        df_final['Profitability_Score'] = df_final[profitability_scores].mean(axis=1) if profitability_scores else 0
        
        # 2. 이익안정성 점수
        stability_cols = ['Revenue_Stability', 'OpProfit_Stability', 'NetIncome_Stability', 'EPS_Stability', 'Dividend_Stability']
        stability_scores = []
        for col in stability_cols:
            if col in df_final.columns:
                df_final[f'Score_{col}'] = z_score(df_final[col].fillna(0))
                stability_scores.append(f'Score_{col}')
        
        df_final['Stability_Score'] = df_final[stability_scores].mean(axis=1) if stability_scores else 0
        
        # 3. 자본구조 점수
        df_final['Score_Debt_Ratio'] = z_score(df_final['Debt_Ratio'].fillna(100))
        capital_scores = ['Score_Debt_Ratio']
        for col in ['Interest_Coverage', 'Current_Ratio', 'Equity_Ratio']:
            if col in df_final.columns:
                df_final[f'Score_{col}'] = z_score(df_final[col].fillna(df_final[col].median()))
                capital_scores.append(f'Score_{col}')
        
        df_final['Capital_Score'] = df_final[capital_scores].mean(axis=1)
        
        # 4. 수익성 개선 점수
        improvement_cols = ['ROE_Improvement', 'ROA_Improvement', 'Operating_Margin_Improvement', 'Gross_Margin_Improvement']
        improvement_scores = []
        for col in improvement_cols:
            if col in df_final.columns:
                df_final[f'Score_{col}'] = z_score(df_final[col].fillna(0))
                improvement_scores.append(f'Score_{col}')
        
        df_final['Improvement_Score'] = df_final[improvement_scores].mean(axis=1) if improvement_scores else 0
        
        # 5. 회계품질 점수
        accounting_cols = ['Accruals', 'Net_Operating_Assets', 'Earnings_Smoothness']
        accounting_scores = []
        for col in accounting_cols:
            if col in df_final.columns:
                df_final[f'Score_{col}'] = z_score(df_final[col].fillna(0)) * -1
                accounting_scores.append(f'Score_{col}')
        
        df_final['Accounting_Score'] = df_final[accounting_scores].mean(axis=1) if accounting_scores else 0
        
        # 신영증권 방식 가중 평균
        df_final['Quality_Score_Total'] = (
            df_final['Profitability_Score'] * 0.30 +
            df_final['Stability_Score'] * 0.25 +
            df_final['Capital_Score'] * 0.20 +
            df_final['Improvement_Score'] * 0.15 +
            df_final['Accounting_Score'] * 0.10
        )
        
        df_final['Quality_Score'] = df_final['Quality_Score_Total'].rank(pct=True) * 100
        
        # ---------------------------------------------------------
        # STEP 5. 결과 확인
        # ---------------------------------------------------------
        result_cols = ['Name', 'Code', 'Is_Financial', 'Quality_Score', 
                       'Profitability_Score', 'Stability_Score', 'Capital_Score', 'Improvement_Score', 'Accounting_Score']
        
        print("\n[전체 종목 분석 완료!]")
        print("데이터 기준: 2025년 Q3 TTM (최근 12개월)")
        print(df_final[result_cols].sort_values('Quality_Score', ascending=False).head(20))
        
        # CSV 저장 (최종본)
        df_final.sort_values('Quality_Score', ascending=False).to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✅ 전체 결과 저장: {output_file} ({len(df_final)}개 종목)")
    else:
        print("저장된 데이터가 없습니다.")
