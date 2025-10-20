"""Load financial metrics from Kaggle companyfacts.csv dataset."""
import pandas as pd
from typing import Dict, Optional
from pathlib import Path


class KaggleFinancialData:
    """Extract structured financial data from Kaggle companyfacts.csv."""
    
    def __init__(self, csv_path: str = "Data/Primary/kaggle_facts/companyfacts.csv"):
        self.csv_path = Path(csv_path)
        self._df = None
        
    def _load_data(self):
        """Lazy load the dataset."""
        if self._df is None:
            self._df = pd.read_csv(self.csv_path)
            
    def get_latest_metrics(self, cik: str, form: str = "10-K") -> Dict[str, Optional[float]]:
        """Get the most recent financial metrics for a company from their 10-K filing.
        
        Args:
            cik: Company CIK (as string, will be zero-padded to 10 digits)
            form: Filing form type (default: 10-K for annual reports)
            
        Returns:
            Dictionary with financial metrics and their values
        """
        self._load_data()
        
        # Normalize CIK
        cik_int = int(cik)
        
        # Filter for this company and form type
        company_data = self._df[(self._df['cik'] == cik_int) & (self._df['form'] == form)]
        
        if company_data.empty:
            return {}
            
        # Get the most recent filing date
        latest_date = company_data['end'].max()
        latest_data = company_data[company_data['end'] == latest_date]
        
        # Extract key metrics
        metrics = {}
        
        # Revenue
        revenue = latest_data[latest_data['companyFact'].str.contains('Revenue', case=False, na=False)]
        if not revenue.empty:
            metrics['revenue'] = float(revenue.iloc[0]['val'])
            
        # Net Income
        net_income = latest_data[latest_data['companyFact'] == 'NetIncomeLoss']
        if not net_income.empty:
            metrics['net_income'] = float(net_income.iloc[0]['val'])
            
        # Total Assets
        assets = latest_data[latest_data['companyFact'] == 'Assets']
        if not assets.empty:
            metrics['total_assets'] = float(assets.iloc[0]['val'])
            
        # Total Liabilities
        liabilities = latest_data[latest_data['companyFact'] == 'Liabilities']
        if not liabilities.empty:
            metrics['total_liabilities'] = float(liabilities.iloc[0]['val'])
            
        # Operating Cash Flow
        ocf = latest_data[latest_data['companyFact'] == 'NetCashProvidedByUsedInOperatingActivities']
        if not ocf.empty:
            metrics['operating_cash_flow'] = float(ocf.iloc[0]['val'])
            
        # Capital Expenditures (usually negative in cash flow statement)
        capex = latest_data[latest_data['companyFact'].str.contains('PaymentsToAcquirePropertyPlantAndEquipment', case=False, na=False)]
        if not capex.empty:
            metrics['capex'] = abs(float(capex.iloc[0]['val']))  # Make positive for calculation
            
        # Stockholders Equity
        equity = latest_data[latest_data['companyFact'] == 'StockholdersEquity']
        if not equity.empty:
            metrics['stockholders_equity'] = float(equity.iloc[0]['val'])
            
        return metrics
