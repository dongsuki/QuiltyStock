import pandas as pd
import FinanceDataReader as fdr
import sys

def generate_table():
    try:
        df = pd.read_csv('c:/Users/User/고니/quality_analysis_all.csv')
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Merge Names
    try:
        df_krx = fdr.StockListing('KRX')
        df = pd.merge(df, df_krx[['Code', 'Name']], on='Code', how='left')
    except:
        if 'Name' not in df.columns:
            df['Name'] = df['Code']

    # Calculate Scores (Simplified for display)
    # Assuming scores are already calculated in CSV or we recalculate?
    # The CSV saved by quality_analysis_ttm.py ONLY has raw data if it crashed before final calculation.
    # So we MUST recalculate scores here.
    
    def z_score(x): 
        if x.std() == 0:
            return pd.Series([0] * len(x), index=x.index)
        return (x - x.mean()) / x.std()
    
    # 1. Profitability
    profitability_cols = ['ROE', 'ROA', 'ROIC', 'Operating_Margin', 'Gross_Margin']
    profitability_scores = []
    for col in profitability_cols:
        if col in df.columns:
            df[f'Score_{col}'] = z_score(df[col].fillna(df[col].median()))
            profitability_scores.append(f'Score_{col}')
    df['Profitability_Score'] = df[profitability_scores].mean(axis=1) if profitability_scores else 0
    
    # 2. Stability
    stability_cols = ['Revenue_Stability', 'OpProfit_Stability', 'NetIncome_Stability', 'EPS_Stability', 'Dividend_Stability']
    stability_scores = []
    for col in stability_cols:
        if col in df.columns:
            df[f'Score_{col}'] = z_score(df[col].fillna(0))
            stability_scores.append(f'Score_{col}')
    df['Stability_Score'] = df[stability_scores].mean(axis=1) if stability_scores else 0
    
    # 3. Capital
    if 'Debt_Ratio' in df.columns:
        df['Score_Debt_Ratio'] = z_score(df['Debt_Ratio'].fillna(100))
        capital_scores = ['Score_Debt_Ratio']
    else:
        capital_scores = []
    for col in ['Interest_Coverage', 'Current_Ratio', 'Equity_Ratio']:
        if col in df.columns:
            df[f'Score_{col}'] = z_score(df[col].fillna(df[col].median()))
            capital_scores.append(f'Score_{col}')
    df['Capital_Score'] = df[capital_scores].mean(axis=1) if capital_scores else 0
    
    # 4. Improvement
    improvement_cols = ['ROE_Improvement', 'ROA_Improvement', 'Operating_Margin_Improvement', 'Gross_Margin_Improvement']
    improvement_scores = []
    for col in improvement_cols:
        if col in df.columns:
            df[f'Score_{col}'] = z_score(df[col].fillna(0))
            improvement_scores.append(f'Score_{col}')
    df['Improvement_Score'] = df[improvement_scores].mean(axis=1) if improvement_scores else 0
    
    # 5. Accounting
    accounting_cols = ['Accruals', 'Net_Operating_Assets', 'Earnings_Smoothness']
    accounting_scores = []
    for col in accounting_cols:
        if col in df.columns:
            df[f'Score_{col}'] = z_score(df[col].fillna(0)) * -1
            accounting_scores.append(f'Score_{col}')
    df['Accounting_Score'] = df[accounting_scores].mean(axis=1) if accounting_scores else 0
    
    # Total Score
    df['Quality_Score_Total'] = (
        df['Profitability_Score'] * 0.30 +
        df['Stability_Score'] * 0.25 +
        df['Capital_Score'] * 0.20 +
        df['Improvement_Score'] * 0.15 +
        df['Accounting_Score'] * 0.10
    )
    df['Quality_Score'] = df['Quality_Score_Total'].rank(pct=True) * 100
    
    # Sort and Print
    df_sorted = df.sort_values('Quality_Score', ascending=False) # Remove .head(20)
    
    with open('c:/Users/User/고니/quality_analysis_full_list.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total Analyzed: {len(df)}\n")
        f.write("-" * 100 + "\n")
        f.write(f"{'Rank':<4} | {'Name':<15} | {'Code':<8} | {'Score':<6} | {'Prof':<5} | {'Stab':<5} | {'Cap':<5} | {'Imp':<5} | {'Acc':<5}\n")
        f.write("-" * 100 + "\n")
        
        for i, (_, row) in enumerate(df_sorted.iterrows()):
            name = row['Name'][:13] + '..' if len(str(row['Name'])) > 13 else str(row['Name'])
            f.write(f"{i+1:<4} | {name:<15} | {row['Code']:<8} | {row['Quality_Score']:>6.1f} | {row['Profitability_Score']:>5.1f} | {row['Stability_Score']:>5.1f} | {row['Capital_Score']:>5.1f} | {row['Improvement_Score']:>5.1f} | {row['Accounting_Score']:>5.1f}\n")
            
    print(f"Full list saved to quality_analysis_full_list.txt ({len(df)} items)")

if __name__ == "__main__":
    generate_table()
