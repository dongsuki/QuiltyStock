import pandas as pd
import FinanceDataReader as fdr
import sys

def screen_strategies():
    try:
        df = pd.read_csv('c:/Users/User/고니/quality_analysis_all.csv')
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Merge Names if missing
    if 'Name' not in df.columns:
        try:
            df_krx = fdr.StockListing('KRX')
            df = pd.merge(df, df_krx[['Code', 'Name']], on='Code', how='left')
        except:
            df['Name'] = df['Code']

    # Recalculate Scores (Ensure we have z-scores)
    def z_score(x): 
        if x.std() == 0: return pd.Series([0] * len(x), index=x.index)
        return (x - x.mean()) / x.std()

    # Helper to calculate sub-scores
    def calc_sub_score(df, cols):
        scores = []
        for col in cols:
            if col in df.columns:
                scores.append(z_score(df[col].fillna(0)))
        return pd.DataFrame(scores).T.mean(axis=1) if scores else pd.Series([0]*len(df))

    # 1. Profitability
    prof_cols = ['ROE', 'ROA', 'ROIC', 'Operating_Margin', 'Gross_Margin']
    df['Profitability_Score'] = calc_sub_score(df, prof_cols)

    # 2. Stability
    stab_cols = ['Revenue_Stability', 'OpProfit_Stability', 'NetIncome_Stability', 'EPS_Stability', 'Dividend_Stability']
    df['Stability_Score'] = calc_sub_score(df, stab_cols)

    # 3. Capital
    cap_cols = ['Interest_Coverage', 'Current_Ratio', 'Equity_Ratio'] # Debt Ratio is inverse, handled separately if needed but for simplicity using positive metrics
    # Note: In main script Debt_Ratio was z-scored. Here we approximate for screening.
    
    # 4. Improvement
    imp_cols = ['ROE_Improvement', 'ROA_Improvement', 'Operating_Margin_Improvement', 'Gross_Margin_Improvement']
    df['Improvement_Score'] = calc_sub_score(df, imp_cols)

    # Save to file
    with open('c:/Users/User/고니/strategy_results_utf8.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        print(f"Analyzed Universe: {len(df)} stocks")
        print("="*80)

        # Strategy 1: The Compounders
        compounders = df[(df['Profitability_Score'] > 1.0) & (df['Stability_Score'] > 0.5)].sort_values('Profitability_Score', ascending=False)
        print(f"\n[Strategy 1: Compounders (꾸준한 우량주)] - {len(compounders)} stocks")
        print("조건: 수익성 상위 16% & 이익안정성 상위 30%")
        print("-" * 80)
        print(f"{'Name':<15} | {'Code':<8} | {'Prof':<5} | {'Stab':<5} | {'ROE':<5}")
        for _, row in compounders.head(10).iterrows():
            print(f"{row['Name'][:13]:<15} | {row['Code']:<8} | {row['Profitability_Score']:>5.1f} | {row['Stability_Score']:>5.1f} | {row['ROE']:>5.1f}%")

        # Strategy 2: Turnaround Candidates
        turnarounds = df[(df['Profitability_Score'] < 0.5) & (df['Improvement_Score'] > 1.5)].sort_values('Improvement_Score', ascending=False)
        print(f"\n[Strategy 2: Turnaround (실적 턴어라운드)] - {len(turnarounds)} stocks")
        print("조건: 수익성 평균 이하 & 개선강도 최상위권")
        print("-" * 80)
        print(f"{'Name':<15} | {'Code':<8} | {'Prof':<5} | {'Imp':<5} | {'OpMargin Imp':<5}")
        for _, row in turnarounds.head(10).iterrows():
            op_imp = row.get('Operating_Margin_Improvement', 0)
            print(f"{row['Name'][:13]:<15} | {row['Code']:<8} | {row['Profitability_Score']:>5.1f} | {row['Improvement_Score']:>5.1f} | {op_imp:>5.1f}%")

        # Strategy 3: Hidden Gems
        hidden_gems = df[(df['ROIC'] > 15) & (df['Debt_Ratio'] < 100) & (df['Interest_Coverage'] > 10)].sort_values('ROIC', ascending=False)
        print(f"\n[Strategy 3: Hidden Gems (재무 우량 + 고수익)] - {len(hidden_gems)} stocks")
        print("조건: ROIC > 15% & 부채비율 < 100% & 이자보상배율 > 10배")
        print("-" * 80)
        print(f"{'Name':<15} | {'Code':<8} | {'ROIC':<5} | {'Debt':<5} | {'IntCov':<5}")
        for _, row in hidden_gems.head(10).iterrows():
            print(f"{row['Name'][:13]:<15} | {row['Code']:<8} | {row['ROIC']:>5.1f}% | {row['Debt_Ratio']:>5.0f}% | {row['Interest_Coverage']:>5.1f}")
            
        sys.stdout = sys.__stdout__
        print("Results saved to strategy_results_utf8.txt")

if __name__ == "__main__":
    screen_strategies()
